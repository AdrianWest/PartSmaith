"""KiCad 10 launch-only action plugin; no PartSmith/CAD imports here."""

import json
import os
import subprocess
from pathlib import Path

import pcbnew
import wx


class PartSmithSetup(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "PartSmith Setup"
        self.category = "Board Forge Tools"
        self.description = "Launch the PartSmith wxPython setup window"
        self.show_toolbar_button = False

    def Run(self):
        try:
            config = json.loads(
                Path(__file__).with_name("launcher.json").read_text("utf-8")
            )
            python = Path(config["python"])
            if not python.is_absolute() or not python.is_file():
                raise ValueError("Invalid Python runtime")
            environment = os.environ.copy()
            for name in ("PYTHONHOME", "PYTHONPATH"):
                environment.pop(name, None)
            return subprocess.Popen(
                [str(python), "-m", "partsmith.gui"],
                cwd=Path(__file__).resolve().parent,
                env=environment,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            wx.MessageBox(
                "PartSmith could not launch. Reinstall the launch entry using "
                "the PartSmith Python 3.12 runtime with GUI dependencies.",
                "PartSmith Setup",
                wx.OK | wx.ICON_ERROR,
            )
            return None


PartSmithSetup().register()
