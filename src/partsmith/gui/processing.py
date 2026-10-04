"""Cancellable processing boundary with thread-safe, redacted progress."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread


@dataclass(frozen=True)
class ProcessingRequest:
    datasheet: Path
    part_number: str
    use_ai: bool = False

    def validate(self):
        if type(self.use_ai) is not bool:
            raise ValueError("AI processing selection must be boolean.")
        if not self.part_number.strip():
            raise ValueError("Enter the full required part number.")
        if self.datasheet.suffix.lower() != ".pdf":
            raise ValueError("Select a PDF datasheet.")
        try:
            with self.datasheet.open("rb") as source:
                if b"%PDF-" not in source.read(1024):
                    raise ValueError("The selected file is not a PDF.")
        except OSError:
            raise ValueError("Select an existing, readable PDF.") from None


class Redactor:
    """Remove known credentials and common credential-shaped log fields."""

    def __init__(self, secrets=()):
        self.secrets = tuple(
            sorted(filter(None, secrets), key=len, reverse=True)
        )

    def __call__(self, message):
        text = str(message)
        for secret in self.secrets:
            text = text.replace(secret, "[REDACTED]")
        text = re.sub(r"\bsk-[\w-]+", "[REDACTED]", text)
        text = re.sub(r"(?i)\bbearer\s+\S+", "Bearer [REDACTED]", text)
        return re.sub(
            r"(?i)(api[_ -]?key|authorization|bft_token)"
            r"(\s*[:=]\s*)\S+",
            r"\1\2[REDACTED]",
            text,
        )


def process_datasheet(request, log, cancel, credential=None, publish=None):
    """Extract Evidence; optionally retain unreviewed AI package candidates."""
    from partsmith.extraction import (
        ExtractionCancelled,
        resolve_package,
    )
    from partsmith.extraction.isolated import extract_isolated

    request.validate()
    if cancel.is_set():
        return "cancelled"
    log(f"Datasheet: {request.datasheet}")
    log(f"Required part number: {request.part_number}")
    log("Package suffixes retained; no default package will be selected.")
    if cancel.is_set():
        return "cancelled"
    try:
        result = extract_isolated(request.datasheet, cancel=cancel, log=log)
    except ExtractionCancelled:
        return "cancelled"
    log(f"Extracted {len(result['evidence'])} unreviewed evidence records.")
    mapping = resolve_package(result, request.part_number)
    if mapping["status"] != "RESOLVED":
        log(f"BLOCKED: Package mapping is {mapping['status']}.")
    else:
        log(f"Ordering-table package: {mapping['package']}")
    if request.use_ai:
        from partsmith.ai import (
            AICancelled,
            AIRequest,
            OpenAIProvider,
            candidate_evidence,
        )
        from partsmith.ai.credentials import user_credential

        ai_request = AIRequest.from_extraction(
            result, "identify_package", request.part_number
        )
        provider = OpenAIProvider(
            credential or user_credential, cancel=cancel, log=log
        )
        try:
            bundle = candidate_evidence(
                ai_request, provider.analyze(ai_request)
            )
        except AICancelled:
            return "cancelled"
        if publish is not None:
            publish(bundle)
        count = len(bundle["candidate_evidence"])
        log(f"AI returned {count} unreviewed candidates.")
        log(
            f"Ambiguities: {len(bundle['result']['ambiguities'])}; "
            f"conflicts: {len(bundle['result']['conflicts'])}."
        )
    else:
        log("Local processing: no Evidence sent to an AI provider.")
    log(
        "UNAVAILABLE: Human review/application (Phase 12) remains required. "
        "No component was built."
    )
    return "unavailable"


Worker = Callable[[ProcessingRequest, Callable[[str], None], Event], str]


class JobController:
    """One job at a time; the GUI drains events on its own thread."""

    def __init__(self, worker: Worker = process_datasheet):
        self.worker = worker
        self.cancel_signal = Event()
        self.events = Queue()
        self.thread = None

    @property
    def active(self):
        return self.thread is not None

    def start(self, request, secrets=()):
        if self.active:
            raise ValueError("A processing job is already running.")
        request.validate()
        redact = Redactor(secrets)
        self.cancel_signal.clear()

        def log(message):
            self.events.put(("log", redact(message)))

        def run():
            try:
                log("Processing started.")
                status = self.worker(request, log, self.cancel_signal)
                if self.cancel_signal.is_set():
                    status = "cancelled"
                if status not in {"success", "cancelled", "unavailable"}:
                    raise ValueError("Invalid worker result")
            except Exception:
                # Exception text may contain credentials; never forward it.
                log("ERROR: Processing failed. Check the input and runtime.")
                status = "failed"
            log(f"Processing status: {status}.")
            self.events.put(("done", status))

        self.thread = Thread(target=run, name="PartSmith processing")
        try:
            self.thread.start()
        except Exception:
            self.thread = None
            raise RuntimeError("Could not start processing.") from None

    def cancel(self):
        if self.active and not self.cancel_signal.is_set():
            self.events.put(("log", "Cancellation requested."))
            self.cancel_signal.set()

    def drain(self):
        # Polling never blocks the GUI thread.
        if self.thread is not None and not self.thread.is_alive():
            self.thread.join()
            self.thread = None
        events = []
        while True:
            try:
                events.append(self.events.get_nowait())
            except Empty:
                return events
