"""@package partsmith.gui.generation
@brief Runs actual artifact generation in a supervised isolated worker.
@details The existing pipeline owns engineering transitions; completed stages
retain exact artifacts and checkpoints despite a later native failure.
"""

import json
import os
import sys
from pathlib import Path

from partsmith.persistence import ImmutableStore
from partsmith.process import run_process
from partsmith.release.workflow import BuildOrchestrator


def artifact_snapshot(session, connection, build_id, revision_id):
    """@brief Retains immutable artifact bytes from one actual attempt.
    @param session Current isolated working session.
    @param connection Worker-owned database connection.
    @param build_id Exact orchestrator-created attempt identity.
    @param revision_id Exact engineering input revision identity.
    @return Artifact reference records in deterministic stage/type order.
    @details Hash-verified byte objects remain inspectable on failed attempts.
    """
    result = []
    placement = ImmutableStore(connection).get_revision(revision_id)[
        "model_3d"
    ]["placement"]
    for row in connection.execute(
        "SELECT * FROM artifacts WHERE build_id=? "
        "ORDER BY stage,artifact_type",
        (build_id,),
    ):
        reference = session.put(bytes(row["content"]))
        if reference["$asset"] != row["sha256"]:
            raise ValueError("Generated artifact hash mismatch")
        result.append(
            {
                "type": row["artifact_type"],
                "stage": row["stage"],
                "sha256": row["sha256"],
                "reference": reference,
                "logical_path": row["logical_path"],
                "build_id": build_id,
                "revision_id": revision_id,
                "placement": placement,
            }
        )
    return result


def worker_command(directory):
    """@brief Constructs the bounded worker command for the active package.
    @param directory Authorized working-session directory.
    @return Explicit isolated Python worker argv.
    @details Resolves source and installed-wheel packages independently of cwd.
    """
    root = str(Path(__file__).resolve().parents[2])
    bootstrap = (
        "import sys;sys.path.insert(0,sys.argv.pop(1));"
        "from partsmith.gui.generation_worker import main;"
        "raise SystemExit(main(sys.argv[1]))"
    )
    return [sys.executable, "-u", "-c", bootstrap, root, str(directory)]


def generate_session(
    session, cancel, emit, *, timeout=1200, command=worker_command
):
    """@brief Starts an exact reviewed-input attempt and supervises CAD work.
    @param session Current session with explicitly approved inputs and PDL.
    @param cancel Cooperative cancellation event.
    @param emit Immutable origin/stage progress sink.
    @param timeout Maximum isolated worker lifetime.
    @param command Trusted worker argv factory, injectable for failure checks.
    @return Retained release candidate state or None after a failed attempt.
    @details The exact ordering number must match the immutable revision
    before creating a build. Native failures cannot close the desktop process.
    """
    binding = session.state.get("pdl")
    if not binding:
        raise ValueError("Select an exact compatible PDL before generation")
    revision = session.state["revision_id"]
    with session.connection() as connection:
        row = connection.execute(
            "SELECT * FROM component_heads WHERE component_id=?",
            (session.state["component_id"],),
        ).fetchone()
        if row is None or row["revision_id"] != revision:
            raise ValueError(
                "Generation requires the current reviewed input revision"
            )
        ir = ImmutableStore(connection).get_revision(revision)
        session.verify_part_number(ir)
        if ir["revision"]["evidence_review"] is None:
            raise ValueError("Inputs are not reviewed")
        build = BuildOrchestrator(connection).start(
            session.state["component_id"], supplied_reviewed_inputs=True
        )
        session.update(
            _connection=connection,
            build_id=build.id,
            release=None,
            status="generating",
        )
    session.checkpoint()
    emit("Attempt created", stage="BUILD_CREATED", build_id=build.id)
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(
            token in key.upper()
            for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")
        )
    }

    def line(origin, text):
        """@brief Dispatches immutable native stage notifications.
        @param origin stdout or stderr label.
        @param text Complete bounded output line.
        @return Whether the line was a structured stage notification.
        @details Exact attempt and revision fields reject unrelated
        notifications.
        """
        if origin != "stdout" or not text.startswith("PARTSMITH_PROGRESS "):
            return False
        event = json.loads(text.removeprefix("PARTSMITH_PROGRESS "))
        if event["build_id"] != build.id or event["revision_id"] != revision:
            raise ValueError(
                "Native progress binding differs from the active attempt"
            )
        session.refresh()
        emit(
            event["stage"],
            stage=event["stage"],
            build_id=build.id,
            payload={"artifacts": event["artifacts"]},
        )
        return True

    try:
        result = run_process(
            command(session.directory),
            log=emit,
            cancel=cancel,
            timeout=timeout,
            env=env,
            on_line=line,
            output_budget=int(session.state["budgets"]["log_bytes"]),
        )
        if result.returncode:
            raise RuntimeError(
                f"Generation worker failed ({result.returncode}); "
                "retained stages remain inspectable"
            )
        session.refresh()
        return session.state.get("release")
    finally:
        session.refresh()
