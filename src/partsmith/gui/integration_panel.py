"""@package partsmith.gui.integration_panel
@brief Provides separate deliberate project-library installation controls.
@details Shared services run through the existing cancellable action worker.
Saved references are inspection data. Publication rechecks authority.
"""

import json
from pathlib import Path

import wx

from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.workflow import (
    InstallationDraft,
    IntegrationWorkflow,
)
from partsmith.ir.canonical import canonical_json

from .session import Session


def review_text(value):
    """@brief Formats detached installation review content for reading.
    @param value Frozen contract or operational inspection data.
    @return Indented JSON display text preserving decimal spelling as text.
    @details Display formatting cannot modify stored contracts or their hashes.
    """
    return json.dumps(
        json.loads(canonical_json(value), parse_float=str),
        indent=2,
        ensure_ascii=False,
    )


class IntegrationPanel(wx.Panel):
    """@brief Owns library workflow controls independent of release approval.
    @details A selected project is an explicitly registered managed copy.
    The user closes editors and reopens the stable project path after use.
    """

    def __init__(self, parent, owner):
        """@brief Builds distinct plan, check, review and publication controls.
        @param parent Owning review notebook.
        @param owner Main frame and serialized background action controller.
        @return None.
        @details Opening restores no authority or writer assertion.
        """
        super().__init__(parent)
        self.owner = owner
        self.sessions = []
        self.instance = None
        self.source_revision = None
        self.draft = None
        self.valid = False
        self.targets_data = []
        self.builds_data = []
        self.buttons = {}
        layout = wx.BoxSizer(wx.VERTICAL)
        self.status = wx.StaticText(
            self,
            label="Plan and review project libraries separately from "
            "input and component release approvals.",
        )
        self.status.Wrap(570)
        layout.Add(self.status, 0, wx.EXPAND | wx.ALL, 6)
        self.target = wx.Choice(self)
        layout.Add(self.target, 0, wx.EXPAND | wx.ALL, 6)
        self.builds = wx.CheckListBox(self)
        self.builds.SetMinSize((-1, 110))
        layout.Add(self.builds, 0, wx.EXPAND | wx.ALL, 6)
        row = wx.WrapSizer(wx.HORIZONTAL)
        for key, label in (
            ("refresh", "Refresh Sources / Projects"),
            ("add-source", "Add Approved Session"),
            ("register", "Create Managed Project Copy"),
            ("plan", "Plan / Dry Run"),
            ("stage", "Stage / Check"),
            ("inspect", "Inspect Installation"),
            ("authorize", "Authorize Exact Installation"),
            ("publish", "Publish / Update"),
            ("rollback", "Plan Rollback"),
            ("recover", "Reconcile Interrupted Publication"),
        ):
            button = wx.Button(self, label=label)
            self.buttons[key] = button
            button.Bind(wx.EVT_BUTTON, self.on_action)
            row.Add(button, 0, wx.ALL, 3)
        layout.Add(row, 0, wx.EXPAND)
        self.reason = wx.TextCtrl(self)
        self.reason.SetHint("Reason for reviewing this exact installation")
        layout.Add(self.reason, 0, wx.EXPAND | wx.ALL, 6)
        self.view = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        self.view.SetMinSize((-1, 190))
        layout.Add(self.view, 1, wx.EXPAND | wx.ALL, 6)
        self.SetSizer(layout)
        self.target.Bind(wx.EVT_CHOICE, self.on_selection)
        self.builds.Bind(wx.EVT_CHECKLISTBOX, self.on_selection)
        self.refresh_session()

    def workflow(self):
        """@brief Creates a fresh shared workflow for explicit source sessions.
        @return Workflow using the durable application authority store.
        @details Loaded sessions supply engineering data only.
        """
        return IntegrationWorkflow([self.owner.session, *self.sessions])

    def refresh_session(self):
        """@brief Invalidates live draft state after session replacement.
        @return None.
        @details Saved references remain visible without restoring permission.
        """
        signature = (
            self.owner.session.state.get("build_id"),
            self.owner.session.state.get("revision_id"),
        )
        if self.instance == self.owner.session.instance_id:
            if signature != self.source_revision:
                self.source_revision = signature
                self.on_selection(None)
                self.refresh_choices()
            return
        self.instance = self.owner.session.instance_id
        self.source_revision = signature
        self.sessions = []
        self.draft = None
        self.valid = False
        references = self.owner.session.state.get("integration")
        self.view.ChangeValue(
            "Saved references require a new plan and exact review.\n"
            + review_text(references)
            if references
            else ""
        )
        self.refresh_choices()

    def refresh_choices(self):
        """@brief Lists approved releases and registered targets.
        @return None.
        @details Fetches no artifact blobs and never selects saved authority.
        """
        try:
            selected = set(self.selected_builds())
            current = self.target.GetSelection()
            target_id = (
                self.targets_data[current]["project_id"]
                if current != wx.NOT_FOUND
                else None
            )
            workflow = self.workflow()
            self.targets_data = workflow.targets()
            self.target.Set(
                [str(Path(t["root"]).parent) for t in self.targets_data]
            )
            if self.targets_data:
                self.target.SetSelection(
                    next(
                        (
                            i
                            for i, t in enumerate(self.targets_data)
                            if t["project_id"] == target_id
                        ),
                        0,
                    )
                )
            records = {}
            for session in [self.owner.session, *self.sessions]:
                with session.connection() as connection:
                    for row in connection.execute(
                        "SELECT b.id, b.component_id, b.completed_at, "
                        "c.manufacturer, c.mpn FROM builds b "
                        "JOIN components c ON c.id=b.component_id "
                        "WHERE b.state IN ('APPROVED','EXPORTED') "
                        "ORDER BY b.created_at LIMIT 10001"
                    ):
                        records[row["id"]] = dict(row)
                        if len(records) > 10000:
                            raise IntegrationError(FailureCode.RESOURCE_LIMIT)
            self.builds_data = list(records.values())
            self.builds.Set(
                [
                    f"{r['manufacturer']} {r['mpn']} "
                    f"({r['component_id'][:8]}, release {r['id'][:8]})"
                    for r in self.builds_data
                ]
            )
            for index, row in enumerate(self.builds_data):
                self.builds.Check(index, row["id"] in selected)
        except (ValueError, OSError) as error:
            self.status.SetLabel(str(error))
        self.enable_controls(False)

    def selected_builds(self):
        """@brief Reads the explicit complete desired approved release set.
        @return Exact selected release build IDs.
        @details No source is implicitly retained or updated by this selection.
        """
        return tuple(
            self.builds_data[i]["id"] for i in self.builds.GetCheckedItems()
        )

    def selected_target(self):
        """@brief Resolves the currently explicitly selected registered target.
        @return Project/library/scope identity.
        @details Throws before an operation when no target is selected.
        """
        index = self.target.GetSelection()
        if index == wx.NOT_FOUND:
            raise ValueError("Select or create a managed project first")
        row = self.targets_data[index]
        return {key: row[key] for key in ("project_id", "library_id", "scope")}

    def enable_controls(self, busy):
        """@brief Keeps blocked inspection visible and execution deliberate.
        @param busy Whether the main action worker is running.
        @return None.
        @details GUI enablement never supplies service authorization.
        """
        for button in self.buttons.values():
            button.Enable(not busy)
        self.target.Enable(not busy)
        self.builds.Enable(not busy)
        self.reason.Enable(not busy)
        self.buttons["stage"].Enable(
            not busy
            and self.valid
            and self.draft is not None
            and self.draft.staged is None
            and not self.draft.planning.no_op
        )
        for key in ("authorize", "publish"):
            self.buttons[key].Enable(
                not busy
                and self.valid
                and self.draft is not None
                and self.draft.staged is not None
            )
        self.buttons["inspect"].Enable(not busy and self.draft is not None)

    def on_selection(self, _event):
        """@brief Invalidates draft readiness after source or target changes.
        @param _event Selection event, unused.
        @return None.
        @details Frozen content remains inspectable and the session saveable.
        """
        self.valid = False
        self.status.SetLabel(
            "Selection changed. Create a new plan before use."
        )
        self.enable_controls(False)

    def invalidate_context(self, reason):
        """@brief Blocks draft execution after loss of the bound IPC context.
        @param reason Closed operational failure reason.
        @return None.
        @details Retains frozen content for inspection and session saving.
        """
        self.valid = False
        self.status.SetLabel(
            "PCB context unavailable: " + reason + ". Create a fresh plan."
        )
        self.enable_controls(self.owner.actions.active)

    def confirm_closed(self):
        """@brief Offers closed-project confirmation or Cancel.
        @return True only for the current deliberate confirmation.
        @details Live process checks independently enforce editor closure.
        """
        with wx.GenericMessageDialog(
            self,
            "Save your schematic and PCB, then close all KiCad editors.\n"
            "Keep PartSmith open. Ensure nobody else is editing this copy.\n"
            "After publication, reopen the managed project path shown here.",
            "Closed project required",
            wx.OK | wx.CANCEL | wx.ICON_INFORMATION,
        ) as dialog:
            dialog.SetOKLabel("I saved and closed the editors")
            return dialog.ShowModal() == wx.ID_OK

    def on_action(self, event):
        """@brief Dispatches an explicit control to the shared worker.
        @param event Button event identifying the deliberate user action.
        @return None.
        @details Cancel starts no target action.
        """
        if self.owner.actions.active or self.owner.job.active:
            return
        key = next(
            k for k, b in self.buttons.items() if b is event.GetEventObject()
        )
        if key == "refresh":
            self.on_selection(None)
            self.refresh_choices()
            return
        arguments = {}
        try:
            if key == "add-source":
                with wx.FileDialog(
                    self,
                    "Select approved component session",
                    wildcard="PartSmith session (*.partsmith)|*.partsmith",
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                ) as dialog:
                    if dialog.ShowModal() != wx.ID_OK:
                        return
                    arguments["archive"] = Path(dialog.GetPath())
            elif key == "register":
                with wx.FileDialog(
                    self,
                    "Select saved original KiCad project",
                    wildcard="KiCad project (*.kicad_pro)|*.kicad_pro",
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                ) as dialog:
                    if dialog.ShowModal() != wx.ID_OK:
                        return
                    arguments["original"] = Path(dialog.GetPath()).parent
                with wx.DirDialog(
                    self,
                    "Select parent for a new managed copy",
                    style=wx.DD_DIR_MUST_EXIST,
                ) as dialog:
                    if dialog.ShowModal() != wx.ID_OK:
                        return
                    parent = Path(dialog.GetPath())
                with wx.TextEntryDialog(
                    self,
                    "New managed project folder name",
                    "Managed copy",
                    value="PartSmithProject",
                ) as dialog:
                    if dialog.ShowModal() != wx.ID_OK:
                        return
                    name = dialog.GetValue()
                from partsmith.integration.contracts import portable_path

                portable_path(name)
                if "/" in name:
                    raise ValueError("Enter one new folder name")
                arguments["workspace"] = parent / name
            elif key not in {"inspect", "stage", "authorize", "publish"}:
                arguments["target"] = self.selected_target()
            if key in {"register", "publish", "recover"}:
                if not self.confirm_closed():
                    self.status.SetLabel("Cancelled. Project files unchanged.")
                    return
            if key == "plan":
                arguments["builds"] = self.selected_builds()
            if key == "authorize":
                arguments["reason"] = self.reason.GetValue()
            if key in {"rollback", "recover"}:
                with wx.TextEntryDialog(
                    self,
                    "Prior manifest SHA-256 (empty for initial tables)"
                    if key == "rollback"
                    else "Unfinished attempt ID",
                    "Plan rollback" if key == "rollback" else "Reconcile",
                ) as dialog:
                    if dialog.ShowModal() != wx.ID_OK:
                        return
                    arguments["reference"] = dialog.GetValue().strip() or None
            self.start_action(key, arguments)
        except (ValueError, OSError) as error:
            self.status.SetLabel(str(error))

    def start_action(self, key, arguments):
        """@brief Starts one serialized action with captured arguments.
        @param key Explicit chosen workflow control.
        @param arguments Captured UI values, excluding credentials.
        @return None.
        @details Worker code never reads wx controls or closes native editors.
        """
        workflow = self.workflow()
        draft = self.draft

        def operation(session, cancel, emit):
            """@brief Executes the shared service in the worker thread.
            @param session Current source session for saved references only.
            @param cancel Cooperative signal respecting publication boundaries.
            @param emit Existing redacted progress callback.
            @return Actual service result or checked draft.
            @details Authority never enters the saved component database.
            """
            if key == "add-source":
                return Session.load(arguments["archive"])
            if key == "register":
                return workflow.register(
                    arguments["original"],
                    arguments["workspace"],
                    confirmed=True,
                )
            if key == "plan":
                result = workflow.plan(
                    arguments["target"], arguments["builds"]
                )
            elif key == "rollback":
                result = workflow.rollback_plan(
                    arguments["target"], arguments["reference"]
                )
            elif key == "stage":
                result = workflow.stage(draft)
            elif key == "inspect":
                return workflow.inspect(draft)
            elif key == "authorize":
                return workflow.authorize(
                    draft, arguments["reason"], cancel=cancel
                )
            elif key == "publish":
                return workflow.publish(draft, confirmed=True, cancel=cancel)
            elif key == "recover":
                return workflow.recover(
                    arguments["target"], arguments["reference"], confirmed=True
                )
            else:
                raise ValueError("Unknown installation action")
            session.update(integration=result.references())
            return result

        self.status.SetLabel("Running " + key + "…")
        self.owner.actions.start(
            self.owner.session, "integration-" + key, operation
        )
        self.owner.set_running(True)

    def progress(self, progress):
        """@brief Displays the actual outcome without restoring authority.
        @param progress Bound immutable action progress event.
        @return None.
        @details Failures keep prior content inspectable and block publication.
        """
        if not progress.stage.startswith("integration-"):
            return
        if progress.outcome in {"failed", "cancelled"}:
            self.valid = False
            self.status.SetLabel(progress.detail)
        elif progress.outcome == "success":
            result = progress.payload
            if isinstance(result, InstallationDraft):
                self.draft = result
                self.valid = True
                self.view.ChangeValue(
                    review_text(
                        result.planning.dry_run()
                        if result.staged is None
                        else {
                            "plan": result.planning.plan.data,
                            "manifest": result.staged.manifest.data,
                            "pre_validation": result.staged.pre.data,
                            "post_validation": result.staged.post.data,
                        }
                    )
                )
                self.status.SetLabel(
                    "Already installed; no changes needed."
                    if result.planning.no_op
                    else "Checked stage requires exact installation review."
                    if result.staged
                    else "Plan ready for staging and checks."
                )
            elif isinstance(result, Session):
                self.sessions.append(result)
                self.valid = False
                self.refresh_choices()
                self.status.SetLabel("Approved source session loaded as data.")
            elif isinstance(result, dict):
                self.view.ChangeValue(review_text(result))
                if result.get("blocking_codes"):
                    self.valid = False
                    self.status.SetLabel(
                        "Installation blocked: "
                        + ", ".join(result["blocking_codes"])
                        + ". Create a fresh plan."
                    )
            elif isinstance(result, tuple):
                self.refresh_choices()
                self.target.SetSelection(
                    next(
                        i
                        for i, t in enumerate(self.targets_data)
                        if t["project_id"] == result[0]["project_id"]
                    )
                )
                self.valid = False
                self.status.SetLabel("Managed project: " + result[1])
            else:
                self.status.SetLabel(
                    result.outcome
                    + (
                        "; " + ", ".join(result.warnings)
                        if result.warnings
                        else ""
                    )
                )
                if getattr(result, "committed", False) or result.outcome in {
                    "CANCELLED",
                    "RECOVERY_REQUIRED",
                }:
                    self.valid = False
                if getattr(result, "committed", False):
                    self.view.AppendText(
                        "\nReopen the selected managed project."
                    )
        self.enable_controls(self.owner.actions.active)
