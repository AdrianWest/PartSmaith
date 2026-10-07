"""@package partsmith.gui.placement_viewer
@brief Displays the exact symbol, footprint, STEP and placement from the
active session.
@details The owned modeless window retains independent camera/UI state and
labels preliminary, failed and stale artifact bindings explicitly.
"""

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from partsmith.ir.canonical import canonical_json

from .artifact_scene import session_scene  # noqa: F401
from .scene import SceneSource, validate_placement
from .scene_controller import SceneController
from .viewer_prototype import PrototypeFrame


class PlacementFrame(PrototypeFrame):
    """@brief Owns the active session's placement inspection window.
    @details The client area holds the scene and scrollable controls without
    a banner.
    """

    def __init__(
        self, parent, *, source, binding, camera=None, log=None, on_closed=None
    ):
        """@brief Opens the actual bound scene using the proven isolated
        backend.
        @param parent Main application owner.
        @param source Required exact active-session SceneSource.
        @param binding Exact stage, build, revision and placement metadata.
        @param camera Retained display-only camera.
        @param log Main-window redacted log callback.
        @param on_closed Callback after display/native worker cleanup.
        @return None.
        @details Never substitutes the prototype fixture for unavailable data.
        """
        super().__init__(
            parent,
            source=source,
            camera=camera,
            log=log,
            on_closed=on_closed,
            controller_factory=lambda snapshot: SceneController(
                snapshot,
                mesh_budget=int(parent.session.state["budgets"]["mesh_bytes"]),
            ),
        )
        self.SetTitle("PartSmith 3D Placement Viewer")
        self.binding = binding
        self.source = source
        label = "STALE — " if binding["stale"] else ""
        self.notice.SetLabel(
            f"{label}{binding['stage']} / {binding['status']}\n"
            f"Build {binding['build_id']} / "
            f"revision {binding['revision_id']}\n"
            "Inspection does not grant release approval."
        )
        old = self.GetSizer()
        children = list(self.GetChildren())
        self.SetSizer(None, deleteOld=False)
        self.review_views = wx.Notebook(self)
        self.scroll = ScrolledPanel(self.review_views)
        for child in children:
            child.Reparent(self.scroll)
        self.scroll.SetSizer(old)
        from .inspection import InspectionPanel

        self.inspection = InspectionPanel(self.scroll, self)
        old.Add(self.inspection, 0, wx.EXPAND | wx.ALL, 6)
        from .placement_panel import PlacementPanel

        try:
            self.editor = PlacementPanel(self.scroll, self)
            old.Add(self.editor, 0, wx.EXPAND | wx.ALL, 6)
        except ValueError as error:
            self.editor = None
            self.log(
                f"[placement editor] {error}; artifact inspection retained"
            )
            old.Add(
                wx.StaticText(self.scroll, label=str(error)),
                0,
                wx.EXPAND | wx.ALL,
                6,
            )
        self.scroll.SetupScrolling(scroll_x=False)
        from .symbol_panel import SymbolInspectionPanel

        self.symbol_panel = SymbolInspectionPanel(self.review_views, self)
        self.review_views.AddPage(self.scroll, "3D / Footprint")
        self.review_views.AddPage(self.symbol_panel, "Symbol / Pin Mapping")
        selection = self.camera.get("review_tab", 0)
        self.review_views.SetSelection(selection if selection in (0, 1) else 0)
        self.review_views.Bind(
            wx.EVT_NOTEBOOK_PAGE_CHANGED, self.select_review
        )
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self.review_views, 1, wx.EXPAND)
        self.SetSizer(outer)
        self.Layout()

    def mark_current(self, session):
        """@brief Labels retained artifact bindings against current session
        state.
        @param session Current session after a service boundary.
        @return None.
        @details New inputs/attempts do not silently replace an open scene.
        """
        stale = self.binding["revision_id"] != session.state.get(
            "revision_id"
        ) or (self.binding["build_id"] != session.state.get("build_id"))
        self.binding["stale"] = stale
        self.symbol_panel.mark_current(stale)
        label = "STALE — " if stale else ""
        self.notice.SetLabel(
            f"{label}{self.binding['stage']} / {session.state.get('status')}\n"
            f"Build {self.binding['build_id']} / "
            f"revision {self.binding['revision_id']}\n"
            "Inspection does not grant release approval."
        )

    def select_review(self, event):
        """@brief Retains the selected inspection page as display-only state.
        @param event Viewer notebook page-change event.
        @return None.
        @details Save/load and close/reopen preserve the page without approval.
        """
        self.camera["review_tab"] = event.GetSelection()
        event.Skip()

    def preview_placement(self, placement):
        """@brief Reprepares a display-only transform of unchanged STEP bytes.
        @param placement Supported exact draft or reviewed transform.
        @return None.
        @details Previous native workers cancel asynchronously; source hashes,
        current IR and release decisions remain untouched.
        """
        validate_placement(placement)
        if self.closing:
            return
        self.controller.close()
        self.retiring.append(self.controller)
        source = SceneSource(
            self.source.step, self.source.footprint, canonical_json(placement)
        )
        self.controller = SceneController(
            source,
            mesh_budget=int(
                self.GetParent().session.state["budgets"]["mesh_bytes"]
            ),
        )
        self.failed = False
        self.metadata = None
        self.frame_revision = 0
        self.viewport.bitmap = None
        self.status.SetLabel("Preparing explicit placement preview…")
        self.controller.start()
        self.request_frame()

    def reset_camera(self, _event):
        """@brief Fits the default isometric view without changing placement.
        @param _event wx reset button event.
        @return None.
        @details Independent layer selection and engineering metadata persist.
        """
        self.inspection.preset("Isometric")
