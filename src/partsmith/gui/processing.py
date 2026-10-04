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

    def validate(self):
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


def process_datasheet(request, log, cancel):
    """Preflight only until Phase 10/11 supply extraction/interpretation."""
    request.validate()
    if cancel.is_set():
        return "cancelled"
    log(f"Datasheet: {request.datasheet}")
    log(f"Required part number: {request.part_number}")
    log("Package suffixes retained; no default package will be selected.")
    if cancel.is_set():
        return "cancelled"
    log(
        "UNAVAILABLE: PDF extraction (Phase 10) and AI interpretation "
        "(Phase 11) are not implemented. No component was built."
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
