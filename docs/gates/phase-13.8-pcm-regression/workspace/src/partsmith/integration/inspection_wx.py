"""@package partsmith.integration.inspection_wx
@brief Displays deliberate read-only PCB inspection in a separate owned window.
@details Native reads run outside the UI thread under the IPC deadline. Closing
either window invalidates the session without reconnecting.
"""

from dataclasses import asdict
from threading import Thread

import wx

from partsmith.ir.canonical import canonical_json

from .inspection import (
    InspectionController,
    InspectionOutcome,
    InspectionState,
)


class InspectionFrame(wx.Frame):
    """@brief Displays actual verified footprint reads and safe IPC failures.
    @details This window contains no engineering-edit or installation controls.
    """

    def __init__(self, parent, controller: InspectionController):
        """@brief Creates a modeless inspector for the bound session.
        @param parent Owning main frame whose destruction closes the session.
        @param controller Session-owning read-only inspection controller.
        @return None.
        @details Refresh is deliberate and disabled while its read is pending.
        """
        super().__init__(parent, title="PCB inspection", size=(760, 460))
        self._parent = parent
        self._controller = controller
        self._closed = False
        self._pending = False
        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        self._scope = wx.StaticText(panel, label="")
        self._status = wx.StaticText(panel, label="")
        self._refresh = wx.Button(panel, label="Refresh PCB inspection")
        self._rows = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self._details = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        self._details.SetMinSize((-1, 120))
        for index, (label, width) in enumerate(
            (
                ("Reference", 110),
                ("X (mm)", 120),
                ("Y (mm)", 120),
                ("Angle (degrees)", 130),
                ("Side", 90),
                ("Library footprint", 250),
            )
        ):
            self._rows.InsertColumn(index, label, width=width)
        layout.Add(self._scope, 0, wx.EXPAND | wx.ALL, 10)
        layout.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        layout.Add(self._refresh, 0, wx.ALL, 10)
        layout.Add(self._rows, 1, wx.EXPAND | wx.ALL, 10)
        layout.Add(self._details, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(layout)
        self._refresh.Bind(wx.EVT_BUTTON, self._on_refresh)
        self._rows.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        if parent is not None:
            parent.Bind(wx.EVT_WINDOW_DESTROY, self._on_parent_destroy)
        self._display(controller.snapshot)

    def _display(self, outcome: InspectionOutcome) -> None:
        """@brief Displays only safe verified content or the closed failure.
        @param outcome Immutable controller outcome.
        @return None.
        @details Failure clears rows rather than presenting stale data as live.
        """
        if self._closed:
            return
        self._rows.DeleteAllItems()
        self._details.ChangeValue("")
        self._scope.SetLabel("")
        if outcome.state == InspectionState.READY:
            inspection = outcome.inspection
            self._scope.SetLabel(inspection.capabilities.board_path)
            self._status.SetLabel(
                f"Verified {len(inspection.footprints)} footprints. "
                "Coordinates use millimetres, X right and Y up."
            )
            for index, footprint in enumerate(inspection.footprints):
                self._rows.InsertItem(index, footprint.reference)
                for column, value in enumerate(
                    (
                        footprint.x_mm,
                        footprint.y_mm,
                        footprint.orientation_degrees,
                        footprint.side,
                        footprint.library_id,
                    ),
                    1,
                ):
                    self._rows.SetItem(index, column, value)
        elif outcome.state == InspectionState.INITIAL:
            self._status.SetLabel(
                "Use Refresh to inspect the connected board."
            )
        else:
            self._status.SetLabel(
                f"PCB inspection stopped: {outcome.code} / "
                f"{outcome.reason.value}. Launch again to connect explicitly."
            )
            if outcome.state == InspectionState.FAILED and self._parent:
                self._parent.review.integration.invalidate_context(
                    outcome.reason.value
                )
        if self._controller.diagnostic_warning:
            self._status.SetLabel(
                self._status.GetLabel()
                + " Diagnostic report could not be saved."
            )
        self._refresh.Enable(
            self._controller.can_refresh and not self._pending
        )
        self.Layout()

    def _on_select(self, event):
        """@brief Shows declared-unit pad and local model details.
        @param event Actual selected footprint row event.
        @return None.
        @details Uses the last immutable read without another native call.
        """
        outcome = self._controller.snapshot
        if outcome.inspection is not None:
            self._details.ChangeValue(
                canonical_json(
                    asdict(outcome.inspection.footprints[event.GetIndex()])
                ).decode()
            )

    def _on_refresh(self, _event) -> None:
        """@brief Starts one deliberate bounded read outside the UI thread.
        @param _event Button event, unused.
        @return None.
        @details Repeated presses cannot create concurrent reads or reconnect.
        """
        if self._closed or self._pending or not self._controller.can_refresh:
            return
        self._pending = True
        self._refresh.Disable()
        self._status.SetLabel("Inspecting the connected PCB Editor...")
        Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        """@brief Runs the controller read and schedules a safe UI delivery.
        @return None.
        @details This thread never accesses wx controls. Shutdown may discard
        delivery while the adapter completes bounded worker cleanup.
        """
        outcome = self._controller.refresh()
        try:
            wx.CallAfter(self._complete, outcome)
        except RuntimeError:
            self._controller.close()

    def _complete(self, outcome: InspectionOutcome) -> None:
        """@brief Applies a read result only to this still-owned window.
        @param outcome Safe immutable completed inspection.
        @return None.
        @details Results delivered after close are ignored.
        """
        if self._closed:
            return
        self._pending = False
        self._display(outcome)

    def _on_close(self, _event) -> None:
        """@brief Closes this inspector and invalidates its IPC session.
        @param _event Window-close event, unused.
        @return None.
        @details Controller close is idempotent and performs no native writes.
        """
        self._closed = True
        self._controller.close()
        self.Destroy()

    def _on_destroy(self, event) -> None:
        """@brief Invalidates the session on direct frame destruction.
        @param event Window-destroy event propagated after handling.
        @return None.
        @details Child-control destruction cannot masquerade as frame close.
        """
        if event.GetEventObject() is self:
            self._closed = True
            self._controller.close()
        event.Skip()

    def _on_parent_destroy(self, event) -> None:
        """@brief Invalidates the session when the owning frame is destroyed.
        @param event Owning or descendant window-destroy event.
        @return None.
        @details Vetoed main-frame close does not destroy the verified session.
        """
        if event.GetEventObject() is self._parent:
            self._closed = True
            self._controller.close()
        event.Skip()
