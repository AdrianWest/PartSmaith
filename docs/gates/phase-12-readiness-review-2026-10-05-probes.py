"""@file audit_checks.py
@brief Independently checks gate identities and reproduces review concerns.
@details Uses temporary sessions and dummy credentials without provider calls.
"""

import argparse
import hashlib
import importlib.metadata
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests")]
if "--installed" not in sys.argv:
    sys.path.insert(0, str(ROOT / "src"))


def identities():
    """@brief Verifies recorded identities outside manifest input maps.
    @return Identity checks and package parity summary.
    @details Prior refresh records are historical, not current identities.
    """
    manifest = json.loads(
        (ROOT / "docs/gates/phase-12-artifacts.json").read_text()
    )
    checks = []

    def walk(value, location):
        """@brief Checks every explicit path and SHA-256 identity.
        @param value Nested manifest value.
        @param location Diagnostic JSON location.
        @return None.
        @details Ignores historical before/after input refresh records.
        """
        if isinstance(value, dict):
            if isinstance(value.get("path"), str) and isinstance(
                value.get("sha256"), str
            ):
                path = ROOT / value["path"]
                actual = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.is_file()
                    else None
                )
                checks.append(
                    {
                        "location": location,
                        "path": value["path"],
                        "match": actual == value["sha256"],
                    }
                )
            for key, child in value.items():
                if key not in {"sha256", "changes"}:
                    walk(child, location + "/" + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, location + "/" + str(index))

    walk(manifest, "")
    mismatches = []
    installed_mismatches = []
    installed_root = Path(
        importlib.metadata.distribution("partsmith").locate_file("partsmith")
    )
    sources = list((ROOT / "src/partsmith").rglob("*.py"))
    with zipfile.ZipFile(ROOT / manifest["wheel"]["path"]) as wheel:
        for path in sources:
            if (
                wheel.read(path.relative_to(ROOT / "src").as_posix())
                != path.read_bytes()
            ):
                mismatches.append(str(path.relative_to(ROOT)))
            installed = installed_root / path.relative_to(
                ROOT / "src/partsmith"
            )
            if (
                not installed.is_file()
                or installed.read_bytes() != path.read_bytes()
            ):
                installed_mismatches.append(str(path.relative_to(ROOT)))
        plugin = ROOT / "integrations/kicad/partsmith_setup/__init__.py"
        plugin_match = (
            wheel.read("partsmith/gui/kicad_plugin/__init__.py")
            == plugin.read_bytes()
        )
    return {
        "outside_map": checks,
        "python_files": len(sources),
        "source_wheel_mismatches": mismatches,
        "source_installed_mismatches": installed_mismatches,
        "installed_root": str(installed_root),
        "plugin_source_wheel_match": plugin_match,
    }


def checkpoint_after_commit(root):
    """@brief Injects a checkpoint error after a committed action.
    @param root Isolated temporary session storage root.
    @return Persisted data and final event showing the observed outcome.
    @details Late cancellation cannot undo the already committed history entry.
    """
    from test_desktop_review import fielded_session

    from partsmith.gui.actions import ActionController
    from partsmith.gui.review_service import DesktopReview

    session, review = fielded_session(root, review_inputs=False)
    review.propose_evidence("Independently review the complete acquisition")
    previous_revision = session.state["revision_id"]
    controller = ActionController()

    def operation(current, cancel, emit):
        """@brief Commits data before simulating late cancellation.
        @param current Temporary working session.
        @param cancel Action cancellation signal.
        @param emit Unused progress sink.
        @return Committed action identity.
        @details The update commits before the cancellation request arrives.
        """
        result = DesktopReview(current).decide_inputs(
            True, "Explicit real input approval before checkpoint failure"
        )
        cancel.set()
        return result.revision_id

    def fail_checkpoint():
        """@brief Simulates unavailable storage after the service commit.
        @return None.
        @details Raises OSError before recovery archive replacement.
        """
        raise OSError("Injected checkpoint storage failure after commit")

    session.checkpoint = fail_checkpoint
    controller.start(session, "review", operation)
    controller.thread.join(10)
    if controller.thread.is_alive():
        raise RuntimeError("Probe action did not terminate")
    events = controller.drain()
    session.refresh()
    return {
        "history": session.state["history"],
        "reviewed_revision_changed": session.state["revision_id"]
        != previous_revision,
        "persisted_status": session.state["status"],
        "events": [
            {
                "outcome": event.outcome,
                "code": event.code,
                "detail": event.detail,
                "payload": event.payload,
            }
            for event in events
        ],
    }


def changed_part_number(root):
    """@brief Starts a different ordering number in an assembled session.
    @param root Temporary local acquisition and component storage.
    @return Actual GUI session identities and received worker request.
    @details Uses the real Start callback with a dummy processing worker.
    """
    import wx
    from test_desktop_review import fielded_session

    from partsmith.gui.app import SetupFrame
    from partsmith.gui.credentials import CredentialStore
    from partsmith.pdl import resolve_pdl

    class Backend:
        """@brief Supplies a credential-free test store.
        @details No operating-system credential is read or changed.
        """

        def get_password(self, service, account):
            """@brief Returns no credential.
            @param service Unused service identity.
            @param account Unused account identity.
            @return None.
            @details Keeps this probe offline.
            """
            return None

    requests = []
    confirmations = []

    def worker(request, log, cancel):
        """@brief Records the actual processing request without extraction.
        @param request Actual request made by the Start callback.
        @param log Unused redacted progress callback.
        @param cancel Unused cancellation signal.
        @return Successful operational status.
        @details Makes no provider or native CAD calls.
        """
        requests.append(request.part_number)
        return "success"

    def transition(continuation):
        """@brief Records whether Start invokes the unsaved-work policy.
        @param continuation Pending new-component operation.
        @return None.
        @details Does not invoke the pending transition.
        """
        confirmations.append("unsaved-policy-called")

    session, review = fielded_session(root)
    pdl = resolve_pdl("chip_resistor", "0402", {"1", "2"})
    review.bind_pdl(
        pdl.data["id"], pdl.data["revision"], pdl.data["content_sha256"]
    )
    original_revision = session.state["revision_id"]
    original_component = session.state["component_id"]
    original_part = review.snapshot().data["identity"]["mpn"]
    app = wx.App(False)
    frame = SetupFrame(
        store=CredentialStore(Backend()),
        worker=worker,
        session=session,
        recover=False,
    )
    frame.timer.Stop()
    frame.transition = transition
    frame.part.SetValue("DIFFERENT-ORDERING-NUMBER")
    frame.on_start(None)
    frame.job.thread.join(10)
    frame.job.drain()
    frame.set_running(False)
    result = {
        "worker_requests": requests,
        "unsaved_policy_calls": confirmations,
        "setup_part": session.state["setup"]["part_number"],
        "reviewed_part": review.snapshot().data["identity"]["mpn"],
        "original_part": original_part,
        "same_component": original_component == session.state["component_id"],
        "same_reviewed_revision": original_revision
        == session.state["revision_id"],
        "session_dirty": session.dirty,
        "generation_enabled": frame.review.artifacts.generate.IsEnabled(),
    }
    frame.Destroy()
    wx.Yield()
    app.Destroy()
    return result


def main():
    """@brief Writes exact independent review observations.
    @return None.
    @details Temporary sessions are deleted only within their known root.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import partsmith
    from partsmith.release.schema import load_schema

    definitions = list(load_schema()["$defs"])
    with tempfile.TemporaryDirectory(
        prefix="partsmith-gate12-review-"
    ) as directory:
        root = Path(directory)
        result = {
            "identities": identities(),
            "checkpoint_after_commit": checkpoint_after_commit(
                root / "checkpoint"
            ),
            "changed_part_number": changed_part_number(root / "part"),
        }
    result["package"] = str(Path(partsmith.__file__).resolve())
    result["phase8_schema_definitions"] = definitions
    destination = args.output
    destination.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "identity_count": len(result["identities"]["outside_map"]),
                "identity_mismatches": [
                    item
                    for item in result["identities"]["outside_map"]
                    if not item["match"]
                ],
                "source_wheel_mismatches": result["identities"][
                    "source_wheel_mismatches"
                ],
                "source_installed_mismatches": result["identities"][
                    "source_installed_mismatches"
                ],
                "plugin_match": result["identities"][
                    "plugin_source_wheel_match"
                ],
                "checkpoint_after_commit": result["checkpoint_after_commit"],
                "changed_part_number": result["changed_part_number"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
