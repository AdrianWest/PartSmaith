"""@file entry.py
@brief Opens the PCM-installed action using an isolated external interpreter.
@details Board inspection is deliberate; startup does not select or read a PCB.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _save_report(report: dict) -> None:
    """@brief Writes safe operational diagnostics outside disposable paths.
    @param report Readiness and optional safe board-inspection document.
    @return None.
    @details Never receives or records launch tokens or endpoint values.
    """
    diagnostic_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    diagnostic_root /= "PartSmith/runtime"
    diagnostic_root.mkdir(parents=True, exist_ok=True)
    (diagnostic_root / "last-launch.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    """@brief Checks the managed runtime before opening the desktop action.
    @return Zero for a ready action, two when engineering readiness fails.
    @details Uses isolated installed code; PCB access requires a user action.
    """
    entry = Path(__file__).resolve()
    if not sys.flags.isolated:
        return subprocess.run(
            [sys.executable, "-I", str(entry), *sys.argv[1:]], check=False
        ).returncode
    root = entry.parent
    endpoint = os.environ.pop("KICAD_API_SOCKET", "")
    token = os.environ.pop("KICAD_API_TOKEN", "")
    sys.path.insert(0, str(root))
    from partsmith.pcm.runtime import readiness

    report = readiness(root)
    _save_report(report)
    if "--diagnostics" in sys.argv:
        print(json.dumps(report, sort_keys=True), flush=True)
        return 0 if report["state"] == "READY" else 2
    if report["state"] != "READY":
        message = "PartSmith runtime is not ready: " + report["code"]
        print(message, file=sys.stderr, flush=True)
        try:
            import wx

            app = wx.App(False)
            wx.MessageBox(message, "PartSmith runtime", wx.OK | wx.ICON_ERROR)
            del app
        except ImportError:
            pass
        return 2
    import wx

    from partsmith.gui.app import SetupFrame
    from partsmith.integration.host import capture_launch_host
    from partsmith.integration.inspection import InspectionController
    from partsmith.integration.inspection_wx import InspectionFrame
    from partsmith.integration.ipc import IpcError, connect_ipc

    app = wx.App(False)
    controller = None
    inspection = None
    host = None

    def save_inspection(snapshot: dict) -> None:
        """@brief Persists bounded safe live inspection outcomes.
        @param snapshot Closed controller report without launch secrets.
        @return None.
        @details Does not change component history or install authority.
        """
        report["ipc_inspection"] = snapshot
        _save_report(report)

    def inspect_pcb(parent) -> None:
        """@brief Opens optional inspection after deliberate board selection.
        @param parent Main frame owning the picker and inspection window.
        @return None.
        @details Keeps launch secrets in memory; failure leaves setup usable.
        """
        nonlocal controller, inspection
        if not parent or getattr(parent, "closing", False):
            return
        if inspection:
            inspection.Raise()
            return
        controller = None
        session = None
        failure_code = "IPC_CONNECTION_OR_BOARD_CHECK_FAILED"
        try:
            if not endpoint or not token:
                failure_code = "IPC_LAUNCH_CONTEXT_REQUIRED"
                raise RuntimeError(failure_code)
            with wx.FileDialog(
                parent,
                "Select the board open in this PCB Editor",
                wildcard="KiCad PCB (*.kicad_pcb)|*.kicad_pcb",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if dialog.ShowModal() != wx.ID_OK:
                    return
                expected_board = dialog.GetPath()
            if not parent or getattr(parent, "closing", False):
                return
            session = connect_ipc(endpoint, token, expected_board)
            controller = InspectionController(
                session, report_callback=save_inspection
            )
            failure_code = "GUI_ACTION_FAILED"
            inspection = InspectionFrame(parent, controller)
            inspection.Show()
        except Exception as error:
            if controller is not None:
                controller.close()
                controller = None
            elif session is not None:
                session.close()
            if inspection:
                inspection.Destroy()
            inspection = None
            if isinstance(error, IpcError):
                failure_code = "IPC_" + error.reason.value
            save_inspection({"state": "FAILED", "code": failure_code})
            if not parent or getattr(parent, "closing", False):
                return
            wx.MessageBox(
                "PCB inspection failed: " + failure_code + ".",
                "PartSmith",
                wx.OK | wx.ICON_ERROR,
                parent=parent,
            )

    try:
        if endpoint and token:
            host = capture_launch_host()
            if host is None or not host.is_alive():
                if host is not None:
                    host.close()
                    host = None
                report.update(state="CLOSED", code="KICAD_HOST_EXITED")
                _save_report(report)
                return 0
        frame = SetupFrame(
            inspect_pcb=inspect_pcb,
            host_alive=host.is_alive if host is not None else None,
        )
        frame.Show()
        app.MainLoop()
        if host is not None and not host.is_alive():
            report.update(state="CLOSED", code="KICAD_HOST_EXITED")
            _save_report(report)
        return 0
    except Exception:
        report.update(state="FAILED", code="GUI_ACTION_FAILED")
        _save_report(report)
        wx.MessageBox(
            "PartSmith action failed: GUI_ACTION_FAILED. Launch again.",
            "PartSmith",
            wx.OK | wx.ICON_ERROR,
        )
        return 2
    finally:
        if controller is not None:
            controller.close()
        if host is not None:
            host.close()


if __name__ == "__main__":
    raise SystemExit(main())
