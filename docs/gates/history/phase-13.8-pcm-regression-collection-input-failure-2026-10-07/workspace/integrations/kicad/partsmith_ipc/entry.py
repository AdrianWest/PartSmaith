"""@file entry.py
@brief Opens the PCM-installed action using an isolated external interpreter.
@details Runtime failure is explicit; package/environment updates own no data.
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
    @details Uses a fixed isolated bootstrap and installed source root.
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
    from partsmith.integration.inspection import InspectionController
    from partsmith.integration.inspection_wx import InspectionFrame

    from partsmith.gui.app import SetupFrame
    from partsmith.integration.ipc import IpcError, connect_ipc

    app = wx.App(False)
    if not endpoint or not token:
        report.update(state="FAILED", code="IPC_LAUNCH_CONTEXT_REQUIRED")
        _save_report(report)
        wx.MessageBox(
            "Launch PartSmith from the PCB Editor action.",
            "PartSmith",
            wx.OK | wx.ICON_ERROR,
        )
        return 2
    with wx.FileDialog(
        None,
        "Select the board open in this PCB Editor",
        wildcard="KiCad PCB (*.kicad_pcb)|*.kicad_pcb",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return 0
        expected_board = dialog.GetPath()
    session = None
    controller = None
    failure_code = "IPC_CONNECTION_OR_BOARD_CHECK_FAILED"
    try:
        session = connect_ipc(endpoint, token, expected_board)
        del token
        del endpoint

        def save_inspection(snapshot: dict) -> None:
            """@brief Persists bounded safe live inspection outcomes.
            @param snapshot Closed controller report without launch secrets.
            @return None.
            @details Does not change component history or install authority.
            """
            report["ipc_inspection"] = snapshot
            _save_report(report)

        controller = InspectionController(
            session, report_callback=save_inspection
        )
        outcome = controller.refresh()
        if outcome.state != "READY":
            report.update(state="FAILED", code="IPC_INITIAL_INSPECTION_FAILED")
            _save_report(report)
            return 2
        failure_code = "GUI_ACTION_FAILED"
        frame = SetupFrame()
        inspection = InspectionFrame(frame, controller)
        frame.Show()
        inspection.Show()
        app.MainLoop()
        return 0
    except Exception as error:
        if isinstance(error, IpcError):
            failure_code = "IPC_" + error.reason.value
        report.update(state="FAILED", code=failure_code)
        _save_report(report)
        wx.MessageBox(
            "PartSmith action failed: " + failure_code + ". Launch again.",
            "PartSmith",
            wx.OK | wx.ICON_ERROR,
        )
        return 2
    finally:
        if controller is not None:
            controller.close()
        elif session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
