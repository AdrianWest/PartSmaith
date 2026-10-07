"""@package partsmith.gui.placement_panel
@brief Edits exact placement drafts and submits explicit review proposals.
@details Read-only scale is preserved; preview and discard never approve IR.
"""

import wx

from .placement import PlacementDraft


class PlacementPanel(wx.Panel):
    """@brief Owns engineering controls separate from display camera state.
    @details Explicit proposal approval remains in the main input-review tab.
    """

    def __init__(self, parent, viewer):
        """@brief Builds exact XYZ position, rotation and mirror editors.
        @param parent Scrollable viewer content owner.
        @param viewer Bound placement frame.
        @return None.
        @details Initialization loads reviewed values and any matching draft.
        """
        super().__init__(parent)
        self.viewer = viewer
        self.owner = viewer.GetParent()
        self.draft = PlacementDraft(self.owner.session)
        layout = wx.BoxSizer(wx.VERTICAL)
        self.entries = {}
        grid = wx.FlexGridSizer(cols=4, hgap=5, vgap=5)
        for label in ("Placement", "X", "Y", "Z"):
            grid.Add(wx.StaticText(self, label=label))
        for key, title in (
            ("translation_mm", "Offset (mm)"),
            ("rotation_deg", "Rotation (deg)"),
            ("scale", "Scale"),
        ):
            grid.Add(wx.StaticText(self, label=title))
            self.entries[key] = []
            for _axis in range(3):
                item = wx.TextCtrl(
                    self,
                    size=(105, -1),
                    style=wx.TE_READONLY if key == "scale" else 0,
                )
                grid.Add(item)
                self.entries[key].append(item)
        layout.Add(grid, 0, wx.ALL, 4)
        self.mirrors = {}
        row = wx.WrapSizer(wx.HORIZONTAL)
        for axis in "xyz":
            item = wx.CheckBox(self, label=f"Mirror {axis.upper()}")
            self.mirrors[axis] = item
            row.Add(item, 0, wx.ALL, 5)
        layout.Add(row, 0, wx.EXPAND)
        self.reason = wx.TextCtrl(self)
        self.reason.SetHint("Reason required for explicit placement proposal")
        self.evidence = wx.TextCtrl(self)
        self.evidence.SetHint("Evidence reference for typed override")
        layout.Add(self.reason, 0, wx.EXPAND | wx.ALL, 4)
        layout.Add(self.evidence, 0, wx.EXPAND | wx.ALL, 4)
        row = wx.WrapSizer(wx.HORIZONTAL)
        self.buttons = []
        for label, callback in (
            ("Preview Draft", self.preview),
            ("Show Reviewed", self.reviewed),
            ("Discard Draft", self.discard),
            ("Propose Placement", self.propose),
        ):
            item = wx.Button(self, label=label)
            item.Bind(wx.EVT_BUTTON, callback)
            self.buttons.append(item)
            row.Add(item, 0, wx.ALL, 3)
        layout.Add(row, 0, wx.EXPAND)
        self.feedback = wx.StaticText(self)
        layout.Add(self.feedback, 0, wx.EXPAND | wx.ALL, 4)
        self.SetSizer(layout)
        self.restore()
        saved = self.owner.session.state.get("viewer", {}).get(
            "placement_form", {}
        )
        if saved.get("base_revision_id") == self.draft.revision_id:
            for key in ("translation_mm", "rotation_deg"):
                for control, value in zip(
                    self.entries[key], saved[key], strict=True
                ):
                    control.ChangeValue(value)
            for axis, control in self.mirrors.items():
                control.SetValue(saved["mirror"][axis])
            self.reason.ChangeValue(saved.get("reason", ""))
            self.evidence.ChangeValue(saved.get("evidence_reference", ""))
        for controls in self.entries.values():
            for control in controls:
                if control not in self.entries["scale"]:
                    control.Bind(wx.EVT_TEXT, self.on_form)
        for control in self.mirrors.values():
            control.Bind(wx.EVT_CHECKBOX, self.on_form)
        self.reason.Bind(wx.EVT_TEXT, self.on_form)
        self.evidence.Bind(wx.EVT_TEXT, self.on_form)
        self.feedback.SetLabel(
            "UNAPPROVED draft; " + "\n".join(self.draft.diagnostics())
        )

    def on_form(self, _event):
        """@brief Retains unfinished editor text, including invalid entries.
        @param _event wx text or mirror event.
        @return None.
        @details Raw editor text has no engineering approval authority.
        """
        session = self.owner.session
        form = {
            "base_revision_id": self.draft.revision_id,
            "translation_mm": [
                c.GetValue() for c in self.entries["translation_mm"]
            ],
            "rotation_deg": [
                c.GetValue() for c in self.entries["rotation_deg"]
            ],
            "mirror": {a: c.GetValue() for a, c in self.mirrors.items()},
            "reason": self.reason.GetValue(),
            "evidence_reference": self.evidence.GetValue(),
        }
        session.update(
            viewer={**session.state.get("viewer", {}), "placement_form": form}
        )
        self.owner.checkpoint_due = 0

    def restore(self):
        """@brief Displays retained exact values without float conversion.
        @return None.
        @details Scale and mirror state survive load, discard and reopen.
        """
        for key, controls in self.entries.items():
            for item, value in zip(
                controls, self.draft.value[key], strict=True
            ):
                item.ChangeValue(str(value))
        for axis, item in self.mirrors.items():
            item.SetValue(self.draft.value["mirror"][axis])

    def read(self):
        """@brief Captures a deliberate exact decimal draft.
        @return Supported placement mapping.
        @details Retains draft only and schedules a durable idle checkpoint.
        """
        value = self.draft.edit(
            [item.GetValue() for item in self.entries["translation_mm"]],
            [item.GetValue() for item in self.entries["rotation_deg"]],
            {axis: item.GetValue() for axis, item in self.mirrors.items()},
        )
        self.owner.checkpoint_due = 0
        return value

    def preview(self, _event):
        """@brief Previews the unapproved draft against unchanged STEP bytes.
        @param _event wx button event.
        @return None.
        @details Native display preparation remains isolated and cancellable.
        """
        try:
            value = self.read()
            self.viewer.preview_placement(value)
            self.feedback.SetLabel(
                "UNAPPROVED DRAFT\n" + "\n".join(self.draft.diagnostics())
            )
            self.feedback.Wrap(480)
        except Exception as error:
            self.owner.append_log(f"[placement draft] {error}")
            self.feedback.SetLabel(str(error))

    def reviewed(self, _event):
        """@brief Shows the reviewed transform without deleting the draft.
        @param _event wx button event.
        @return None.
        @details The underlying canonical geometry remains byte identical.
        """
        self.viewer.preview_placement(self.draft.reviewed)
        self.feedback.SetLabel(
            "REVIEWED PLACEMENT — retained artifact geometry"
        )

    def discard(self, _event):
        """@brief Restores actual reviewed placement and persists that draft.
        @param _event wx button event.
        @return None.
        @details Never resets nonunit scale, mirrors or offsets to defaults.
        """
        self.draft.discard()
        self.restore()
        self.on_form(None)
        self.reviewed(None)
        self.owner.checkpoint_due = 0

    def propose(self, _event):
        """@brief Submits a deliberate typed placement proposal on a worker.
        @param _event wx button event.
        @return None.
        @details Proposal creation does not approve inputs or release
        artifacts.
        """
        try:
            self.read()
            reason, evidence = self.reason.GetValue(), self.evidence.GetValue()
            self.owner.actions.start(
                self.owner.session,
                "placement-proposal",
                lambda session, cancel, emit: self.draft.propose(
                    reason, evidence
                ),
            )
            self.owner.set_running(True)
            self.feedback.SetLabel("Pending input review in the main window")
        except Exception as error:
            self.owner.append_log(f"[placement proposal] {error}")
