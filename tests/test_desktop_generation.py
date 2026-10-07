"""@package tests.test_desktop_generation
@brief Verifies real isolated generation and failure-stage artifact retention.
@details Exercises native KiCad previews, child crashes, cancellation and logs.
"""

import sys
from hashlib import sha256
from pathlib import Path
from threading import Event

import pytest
from test_desktop_review import fielded_session

from partsmith.gui import generation as generation_module
from partsmith.gui.generation import generate_session
from partsmith.gui.processing import Redactor
from partsmith.gui.session import Session
from partsmith.pdl import load_pdl
from partsmith.process import run_process


def ready_session(tmp_path):
    """@brief Creates explicitly reviewed known inputs with an exact PDL.
    @param tmp_path Temporary session storage.
    @return Session eligible for generation.
    @details No release decision has been made.
    """
    session, review = fielded_session(tmp_path)
    pdl = load_pdl("synthetic-0402", "1.0")
    review.bind_pdl(
        pdl.data["id"], pdl.data["revision"], pdl.data["content_sha256"]
    )
    return session


def test_changed_ordering_number_cannot_start_a_build(tmp_path):
    """@brief Rejects a setup request for another reviewed component.
    @param tmp_path Isolated known-input session storage.
    @return None.
    @details The mismatch fails before creating an attempt or launching CAD.
    """
    session = ready_session(tmp_path)
    revision = session.state["revision_id"]
    session.update(setup={"part_number": "ANOTHER-PACKAGE-SUFFIX"})
    with pytest.raises(ValueError, match="part number differs"):
        generate_session(session, Event(), lambda *args, **kwargs: None)
    with session.connection() as connection:
        assert (
            connection.execute("SELECT count(*) FROM builds").fetchone()[0]
            == 0
        )
    assert session.state["revision_id"] == revision
    assert "build_id" not in session.state


def test_actual_pipeline_retains_exact_final_artifacts_and_native_previews(
    tmp_path,
):
    """@brief Runs real isolated CAD, KiCad and exact-byte validation.
    @param tmp_path Temporary session storage.
    @return None.
    @details Generation stops for separate explicit release review.
    """
    session = ready_session(tmp_path)
    events = []

    def emit(detail, **fields):
        """@brief Captures immutable actual-stage notifications.
        @param detail Progress message.
        @param fields Structured stage and attempt bindings.
        @return None.
        @details Does not mutate engineering state.
        """
        events.append((detail, fields))

    release = generate_session(session, Event(), emit)
    assert release["approved"] is False
    assert session.state["status"] == "release-review-required"
    assert any(
        fields.get("stage") == "SYMBOL_GENERATED" for _, fields in events
    )
    assert any("[stdout]" in detail for detail, _ in events)
    final = [
        item
        for item in session.state["drafts"]["artifacts"]
        if item["stage"] == "FINAL"
    ]
    assert {item["type"] for item in final} == {
        "SYMBOL",
        "FOOTPRINT",
        "MODEL_3D",
    }
    for item in final:
        assert (
            sha256(session.get(item["reference"])).hexdigest()
            == item["sha256"]
        )
        assert item["build_id"] == session.state["build_id"]
        assert item["revision_id"] == session.state["revision_id"]
    previews = session.state["drafts"]["previews"]
    assert {item["type"] for item in previews} == {"SYMBOL", "FOOTPRINT"}
    assert all(b"<svg" in session.get(item["reference"]) for item in previews)
    with session.connection() as connection:
        assert (
            connection.execute(
                "SELECT state FROM builds WHERE id=?", (release["build_id"],)
            ).fetchone()[0]
            == "HUMAN_REVIEW_REQUIRED"
        )


def crashing_model(directory):
    """@brief Constructs a worker that crashes during the native model stage.
    @param directory Authorized working-session directory.
    @return Explicit fault-injected Python worker argv.
    @details Earlier real symbol and footprint stages still commit normally.
    """
    root = str(Path(generation_module.__file__).resolve().parents[2])
    code = (
        "import sys,os;sys.path.insert(0,sys.argv[1]);"
        "import partsmith.release.pipeline as p;"
        "p.generate_model_3d=lambda *args:os._exit(70);"
        "from partsmith.gui.generation_worker import main;"
        "raise SystemExit(main(sys.argv[2]))"
    )
    return [sys.executable, "-u", "-c", code, root, str(directory)]


def test_native_crash_preserves_completed_stages_and_unfinished_save(tmp_path):
    """@brief Checks a hard CAD child crash leaves prior exact artifacts.
    @param tmp_path Temporary session storage.
    @return None.
    @details Main-session inspection and source-independent recovery remain
    usable.
    """
    session = ready_session(tmp_path)
    with pytest.raises(RuntimeError, match="70"):
        generate_session(
            session,
            Event(),
            lambda *args, **kwargs: None,
            command=crashing_model,
        )
    artifacts = session.state["drafts"]["artifacts"]
    assert {item["type"] for item in artifacts} == {"SYMBOL", "FOOTPRINT"}
    assert session.state.get("release") is None
    archive = tmp_path / "failed.partsmith"
    session.save(archive)
    loaded = Session.load(archive, root=tmp_path / "recovered")
    assert loaded.state["build_id"] == session.state["build_id"]
    assert loaded.state["drafts"]["artifacts"] == artifacts
    assert not loaded.busy


def test_cancel_after_completed_stage_reaps_worker_and_retains_attempt(
    tmp_path,
):
    """@brief Cancels an actual generation between committed stages.
    @param tmp_path Temporary session storage.
    @return None.
    @details Operational cancellation does not invent an engineering state.
    """
    session = ready_session(tmp_path)
    cancel = Event()

    def emit(detail, **fields):
        """@brief Requests cancellation after the first actual artifact commit.
        @param detail Progress detail.
        @param fields Stage and attempt identities.
        @return None.
        @details Completed artifact bytes remain retained.
        """
        if fields.get("stage") == "SYMBOL_GENERATED":
            cancel.set()

    with pytest.raises(InterruptedError):
        generate_session(session, cancel, emit)
    assert session.state["build_id"]
    assert any(
        item["type"] == "SYMBOL"
        for item in session.state["drafts"]["artifacts"]
    )
    assert session.state.get("release") is None


def test_incremental_stdout_stderr_partial_failure_and_redaction():
    """@brief Checks pre-failure output and final partial lines survive safely.
    @return None.
    @details Both stream origins and actual exit status are retained redacted.
    """
    secret = "dummy-credential-12.5"
    messages = []
    redact = Redactor((secret,))
    result = run_process(
        [
            sys.executable,
            "-u",
            "-c",
            f"import sys; print('stdout {secret}',flush=True);"
            "sys.stderr.write('stderr before failure\\n');sys.stderr.flush();"
            f"sys.stdout.write('final partial {secret}');sys.exit(23)",
        ],
        log=lambda message: messages.append(redact(message)),
    )
    assert result.returncode == 23
    assert secret not in str(messages)
    assert any(
        "[stderr] stderr before failure" in message for message in messages
    )
    assert any("final partial [REDACTED]" in message for message in messages)
    assert messages[-1].endswith("Exit status: 23")


def test_process_timeout_and_oversized_output_are_bounded():
    """@brief Verifies timeout and aggregate pipe-output budgets.
    @return None.
    @details Readers, pipes and owned process trees are reaped on failure.
    """
    with pytest.raises(TimeoutError):
        run_process(
            [sys.executable, "-c", "import time;time.sleep(20)"],
            log=lambda _: None,
            timeout=0.2,
        )
    with pytest.raises(ValueError, match="budget"):
        run_process(
            [sys.executable, "-u", "-c", "print('x'*70000,flush=True)"],
            log=lambda _: None,
            output_budget=1000,
        )
