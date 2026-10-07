"""@package partsmith.gui.generation_worker
@brief Executes existing deterministic services outside the desktop process.
@details Every completed stage commits exact bytes and checkpoints before
publishing progress; approval remains a separate explicit desktop action.
"""

import os
import sys

from partsmith.ir.canonical import canonical_json
from partsmith.pdl import load_pdl

from .generation import artifact_snapshot
from .session import Session


def main(directory):
    """@brief Runs one authorized isolated generation attempt.
    @param directory Parent-supplied working session directory.
    @return Zero on release-review readiness, one on service failure.
    @details Windows native failure dialogs are disabled only in this worker.
    """
    if os.name == "nt":
        import ctypes

        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
    from partsmith.kicad.runtime import native_output
    from partsmith.release.pipeline import KnownGoodReleasePipeline

    session = Session.attach(directory)
    build_id, revision_id = (
        session.state["build_id"],
        session.state["revision_id"],
    )
    binding = session.state["pdl"]
    pdl = load_pdl(binding["id"], binding["revision"])
    if pdl.data["content_sha256"] != binding["sha256"]:
        raise ValueError("Selected PDL content changed")
    with session.connection() as connection:

        def progress(stage, current_build):
            """@brief Commits and checkpoints a completed existing-service
            stage.
            @param stage Actual pipeline stage label.
            @param current_build Exact active attempt identity.
            @return None.
            @details Desktop state and service artifacts commit together.
            """
            artifacts = artifact_snapshot(
                session, connection, current_build, revision_id
            )
            session.update(
                _connection=connection,
                status="generating",
                drafts={
                    **session.state.get("drafts", {}),
                    "artifacts": artifacts,
                },
            )
            connection.commit()
            session.checkpoint()
            print(
                "PARTSMITH_PROGRESS "
                + canonical_json(
                    {
                        "stage": stage,
                        "build_id": current_build,
                        "revision_id": revision_id,
                        "artifacts": artifacts,
                    }
                ).decode(),
                flush=True,
            )
            connection.execute("BEGIN")

        try:

            def preview(kind, content):
                """@brief Retains an exact native preview bound to this
                attempt.
                @param kind SYMBOL or FOOTPRINT artifact type.
                @param content Native KiCad SVG bytes.
                @return None.
                @details Retains the exact final artifact hash; preview bytes
                have no approval authority.
                """
                previews = list(
                    session.state.get("drafts", {}).get("previews", [])
                )
                previews.append(
                    {
                        "type": kind,
                        "reference": session.put(content),
                        "build_id": build_id,
                        "revision_id": revision_id,
                        "artifact_sha256": connection.execute(
                            "SELECT sha256 FROM artifacts WHERE build_id=? "
                            "AND artifact_type=? AND stage='FINAL'",
                            (build_id, kind),
                        ).fetchone()[0],
                    }
                )
                session.update(
                    _connection=connection,
                    drafts={
                        **session.state.get("drafts", {}),
                        "previews": previews,
                    },
                )
                progress(f"{kind}_PREVIEW_READY", build_id)

            with native_output(lambda message: print(message, flush=True)):
                pipeline = KnownGoodReleasePipeline(
                    connection, progress=progress, preview=preview
                )
                candidate = pipeline.run(
                    session.state["component_id"],
                    revision_id,
                    pdl,
                    build_id=build_id,
                )
            artifacts = artifact_snapshot(
                session, connection, build_id, revision_id
            )
            session.update(
                _connection=connection,
                release={
                    "build_id": build_id,
                    "revision_id": revision_id,
                    "manifest_hash": candidate.manifest_hash,
                    "binding": candidate.binding.to_dict(),
                    "approved": False,
                },
                drafts={
                    **session.state.get("drafts", {}),
                    "artifacts": artifacts,
                },
                status="release-review-required",
            )
        except Exception as error:
            connection.rollback()
            session.refresh()
            session.update(status="failed")
            session.checkpoint()
            print(
                f"[generation] {type(error).__name__}: {error}",
                file=sys.stderr,
                flush=True,
            )
            return 1
    session.checkpoint()
    print(
        canonical_json(
            {"status": "release-review-required", "build_id": build_id}
        ).decode(),
        flush=True,
    )
    return 0
