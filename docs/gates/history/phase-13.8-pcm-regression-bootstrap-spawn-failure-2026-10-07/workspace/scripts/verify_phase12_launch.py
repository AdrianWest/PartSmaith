"""@file verify_phase12_launch.py
@brief Exercises the standalone entry with an explicit offline test session.
@details Runs the real wx main loop and owned viewer; no provider is contacted.
"""

import argparse
import json
import sys
import time
import traceback
from hashlib import sha256
from pathlib import Path


class EmptyCredentials:
    """@brief Supplies a credential-free launch verification adapter.
    @details The test never accesses the user's secure credential store.
    """

    provider = "Offline launch verification"

    def configured(self):
        """@brief Reports that provider processing is unavailable.
        @return False.
        @details No real credentials are read or written.
        """
        return False


def main():
    """@brief Verifies actual standalone startup, viewer reopen and cleanup.
    @return Zero after successful verification.
    @details The explicit transport supplies test data to the real frame.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.source:
        sys.path.insert(0, str(root / "src"))
    import wx

    import partsmith.gui.__main__ as entry
    import partsmith.gui.app as gui
    from partsmith.gui.session import Session

    package = Path(gui.__file__).resolve()
    assert ("site-packages" in package.parts) != args.source
    original = gui.SetupFrame
    state = {"stage": 0, "status": "RUNNING"}
    started = time.monotonic()
    timers = []
    frame = None
    viewer = None
    camera = None

    def drive():
        """@brief Advances checks while native preparation stays asynchronous.
        @return None.
        @details Failure is recorded before normal owned-child teardown.
        """
        nonlocal viewer, camera
        try:
            assert time.monotonic() - started < 120, "Launch timed out"
            if state["stage"] == 0:
                assert frame.viewer_button.IsEnabled()
                state["dpi"] = list(frame.GetDPI())
                state["content_scale_factor"] = frame.GetContentScaleFactor()
                state["display_size"] = list(wx.GetDisplaySize())
                frame.on_viewer(None)
                viewer = frame.viewer
                assert viewer is not None
                state["stage"] = 1
            elif state["stage"] in (1, 3):
                assert not viewer.failed, frame.logs.GetValue()
                if viewer.metadata is not None and viewer.frame_revision > 0:
                    assert not hasattr(viewer, "banner")
                    assert frame.banner.GetPosition() == (0, 0)
                    assert (
                        frame.banner.GetSize().width
                        == frame.GetClientSize().width
                    )
                    assert not any(
                        name == "cadquery" or name.startswith("OCP")
                        for name in sys.modules
                    )
                    if state["stage"] == 1:
                        assert viewer.symbol_panel.report is not None
                        assert viewer.symbol_panel.preview.svg is not None
                        assert all(
                            row["diagnostic"] == "MATCH"
                            for row in viewer.symbol_panel.report["mapping"]
                        )
                        viewer.review_views.SetSelection(1)
                        state["symbol_sha256"] = viewer.symbol_panel.report[
                            "artifact"
                        ]["sha256"]
                        viewer.camera["yaw"] = 65
                        camera = dict(viewer.camera)
                        viewer.Close()
                        state["stage"] = 2
                    else:
                        assert viewer.camera == camera
                        assert viewer.review_views.GetSelection() == 1
                        assert (
                            viewer.symbol_panel.report["artifact"]["sha256"]
                            == state["symbol_sha256"]
                        )
                        state["status"] = "PASS"
                        state["stage"] = 4
                        frame.session.dirty = False
                        frame.closing = True
                        frame.Close()
                        return
            elif state["stage"] == 2 and frame.viewer is None:
                assert not viewer.controller.active
                frame.on_viewer(None)
                viewer = frame.viewer
                state["stage"] = 3
            timers.append(wx.CallLater(50, drive))
        except Exception:
            state["status"] = "FAIL"
            state["error"] = traceback.format_exc()
            frame.session.dirty = False
            frame.closing = True
            frame.Close()

    def create_frame():
        """@brief Injects explicitly selected offline data into the real frame.
        @return Actual SetupFrame.
        @details Recovery dialogs and credential lookups are disabled for QA.
        """
        nonlocal frame
        session = Session.load(
            args.transport, root=root / ".tools/phase12-full/launch-sessions"
        )
        frame = original(
            store=EmptyCredentials(), session=session, recover=False
        )
        frame.replace_session(session)
        timers.append(wx.CallLater(50, drive))
        return frame

    gui.SetupFrame = create_frame
    try:
        exit_code = entry.main()
    finally:
        gui.SetupFrame = original
        for timer in timers:
            timer.Stop()
    state.update(
        package=str(package),
        working_directory=str(Path.cwd()),
        scope="Actual standalone entry/main loop; explicit offline fixture",
        source=args.source,
        exit_code=exit_code,
        seconds=round(time.monotonic() - started, 3),
        transport_sha256=sha256(args.transport.read_bytes()).hexdigest(),
        native_children_reaped=state["status"] == "PASS" and not frame,
    )
    args.output.write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(state))
    assert state["status"] == "PASS" and exit_code == 0, state
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
