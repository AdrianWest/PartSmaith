"""@package partsmith.gui.artifact_panel
@brief Displays native previews and exact bytes from the bound build attempt.
@details The existing pipeline produces and validates artifacts; this panel
does not infer engineering or release states from visual appearance.
"""

import wx
import wx.svg

from partsmith.ir.canonical import canonical_json

from .generation import generate_session


class SVGPreview(wx.Panel):
    """@brief Paints retained native KiCad SVG output for an exact artifact.
    @details Display scaling never rewrites the original artifact or SVG bytes.
    """

    def __init__(self, parent):
        """@brief Creates an empty native artifact preview surface.
        @param parent Owning artifact review panel.
        @return None.
        @details Missing previews remain explicitly unavailable.
        """
        super().__init__(parent)
        self.svg = None
        self.SetMinSize((220, 210))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, lambda event: (self.Refresh(), event.Skip()))

    def paint(self, _event):
        """@brief Paints a proportional native preview without editing bytes.
        @param _event wx paint event.
        @return None.
        @details Failure only disables the affected preview surface.
        """
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()
        if self.svg is None:
            dc.DrawText("Native preview not available", 8, 8)
            return
        width, height = self.GetClientSize()
        if width <= 0 or height <= 0:
            return
        try:
            dc.DrawBitmap(
                self.svg.ConvertToScaledBitmap((width, height)), 0, 0, True
            )
        except Exception:
            self.svg = None
            dc.DrawText("Native preview could not be displayed", 8, 8)


class ArtifactPanel(wx.Panel):
    """@brief Inspects retained artifacts and starts an explicit pipeline
    action.
    @details Failed and preliminary attempts remain inspectable and labeled.
    """

    def __init__(self, parent, owner):
        """@brief Builds paired symbol and footprint inspection controls.
        @param parent Owning notebook.
        @param owner Main frame owning the serialized service controller.
        @return None.
        @details Exact bytes and hashes appear alongside native previews.
        """
        super().__init__(parent)
        self.owner = owner
        layout = wx.BoxSizer(wx.VERTICAL)
        self.generate = wx.Button(
            self, label="Generate / Validate Reviewed Component"
        )
        layout.Add(self.generate, 0, wx.ALL, 6)
        self.summary = wx.TextCtrl(
            self, style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        self.summary.SetMinSize((-1, 70))
        layout.Add(self.summary, 0, wx.EXPAND)
        drawings = wx.BoxSizer(wx.HORIZONTAL)
        self.previews = {}
        for kind in ("SYMBOL", "FOOTPRINT"):
            preview = SVGPreview(self)
            drawings.Add(preview, 1, wx.EXPAND | wx.ALL, 4)
            self.previews[kind] = preview
        layout.Add(drawings, 1, wx.EXPAND)
        self.bytes = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        layout.Add(self.bytes, 1, wx.EXPAND)
        self.SetSizer(layout)
        self.generate.Bind(wx.EVT_BUTTON, self.on_generate)

    def refresh_session(self):
        """@brief Displays current attempt bytes and exact native preview refs.
        @return None.
        @details Stale previews are labeled and never substitute current data.
        """
        session, state = self.owner.session, self.owner.session.state
        artifacts = state.get("drafts", {}).get("artifacts", [])
        self.summary.ChangeValue(
            canonical_json(
                {
                    "status": state.get("status"),
                    "build_id": state.get("build_id"),
                    "current_revision": state.get("revision_id"),
                    "artifacts": artifacts,
                }
            ).decode()
        )
        displayed = []
        for kind in ("SYMBOL", "FOOTPRINT"):
            options = [item for item in artifacts if item["type"] == kind]
            artifact = next(
                (item for item in options if item["stage"] == "FINAL"),
                options[0] if options else None,
            )
            if artifact:
                displayed.append(
                    f"{kind} — {artifact['stage']} — {artifact['sha256']}\n"
                    + session.get(artifact["reference"]).decode("utf-8")
                )
            self.previews[kind].svg = None
        self.bytes.ChangeValue("\n\n".join(displayed))
        for preview in state.get("drafts", {}).get("previews", []):
            if preview["build_id"] == state.get("build_id") and preview[
                "revision_id"
            ] == state.get("revision_id"):
                try:
                    self.previews[
                        preview["type"]
                    ].svg = wx.svg.SVGimage.CreateFromBytes(
                        session.get(preview["reference"])
                    )
                except Exception:
                    self.owner.append_log(
                        "[artifact preview] SVG_DISPLAY_ERROR"
                    )
        for preview in self.previews.values():
            preview.Refresh()
        self.generate.Enable(
            not self.owner.job.active
            and not self.owner.actions.active
            and bool(state.get("pdl"))
            and bool(state.get("revision_id"))
        )

    def on_generate(self, _event):
        """@brief Starts generation only through the existing service adapter.
        @param _event wx button event.
        @return None.
        @details The adapter verifies current input approval before creating
        work.
        """
        try:
            self.owner.actions.start(
                self.owner.session, "generation", generate_session
            )
            self.owner.set_running(True)
        except Exception as error:
            self.owner.append_log(f"[generation] {error}")
