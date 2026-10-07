"""@package partsmith.gui.component_panel
@brief Presents exact assembly, typed proposals and explicit input decisions.
@details Decimal numeric text reaches existing immutable services through a
serialized background action; loaded actor names never authenticate review.
"""

import wx

from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.pdl import list_pdls, load_pdl

from .identity import authenticated_principal
from .review_service import DesktopReview


class ComponentPanel(wx.Panel):
    """@brief Separates engineering drafts from approved input history.
    @details Saved reviewer display data cannot authenticate an action.
    """

    def __init__(self, parent, owner):
        """@brief Builds exact engineering and typed review controls.
        @param parent Owning review notebook.
        @param owner Main frame owning session and action controller.
        @return None.
        @details Services require reasons before proposals or decisions.
        """
        super().__init__(parent)
        self.owner = owner
        layout = wx.BoxSizer(wx.VERTICAL)
        self.actor = wx.StaticText(self)
        layout.Add(self.actor, 0, wx.EXPAND | wx.ALL, 6)
        self.snapshot = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        layout.Add(self.snapshot, 1, wx.EXPAND)
        self.editor = wx.TextCtrl(
            self, value="{}", style=wx.TE_MULTILINE | wx.HSCROLL
        )
        self.editor.SetMinSize((-1, 120))
        label = wx.StaticText(
            self,
            label="Initial engineering sections or typed proposal fields "
            "(JSON; exact decimals)",
        )
        label.Wrap(560)
        layout.Add(label, 0, wx.EXPAND | wx.ALL, 6)
        layout.Add(self.editor, 1, wx.EXPAND)
        self.reason = wx.TextCtrl(self)
        self.reason.SetHint("Explicit proposal or decision reason")
        layout.Add(self.reason, 0, wx.EXPAND | wx.ALL, 6)
        buttons = wx.WrapSizer(wx.HORIZONTAL)
        self.assemble = wx.Button(self, label="Assemble Unreviewed IR")
        self.evidence = wx.Button(self, label="Propose Evidence Review")
        self.kind = wx.Choice(
            self,
            choices=["override", "reorder", "remove", "exclude", "resolve"],
        )
        self.kind.SetSelection(0)
        self.propose = wx.Button(self, label="Propose Typed Edit")
        self.approve = wx.Button(self, label="Approve Inputs")
        self.reject = wx.Button(self, label="Reject Inputs")
        for control in (
            self.assemble,
            self.evidence,
            self.kind,
            self.propose,
            self.approve,
            self.reject,
        ):
            buttons.Add(control, 0, wx.ALL, 4)
        layout.Add(buttons, 0, wx.EXPAND | wx.ALL, 6)
        self.pdls = list_pdls()
        self.pdl = wx.Choice(
            self,
            choices=[
                f"{identity} @ {revision}" for identity, revision in self.pdls
            ],
        )
        self.pdl.SetSelection(wx.NOT_FOUND)
        self.pdl.SetToolTip(
            "Choose an exact PDL; a package label is not a library binding"
        )
        layout.Add(self.pdl, 0, wx.EXPAND | wx.ALL, 6)
        self.binding = wx.StaticText(
            self, label="PDL not selected; generation blocked"
        )
        layout.Add(self.binding, 0, wx.EXPAND | wx.ALL, 6)
        self.SetSizer(layout)
        self.assemble.Bind(wx.EVT_BUTTON, self.on_assemble)
        self.evidence.Bind(wx.EVT_BUTTON, self.on_evidence)
        self.propose.Bind(wx.EVT_BUTTON, self.on_propose)
        self.approve.Bind(wx.EVT_BUTTON, lambda event: self.decide(True))
        self.reject.Bind(wx.EVT_BUTTON, lambda event: self.decide(False))
        self.pdl.Bind(wx.EVT_CHOICE, self.on_pdl)
        self.editor.Bind(wx.EVT_TEXT, self.on_draft)
        self.reason.Bind(wx.EVT_TEXT, self.on_draft)
        self.kind.Bind(wx.EVT_CHOICE, self.on_draft)

    def on_draft(self, _event):
        """@brief Retains unfinished exact review form text for recovery.
        @param _event wx form edit event.
        @return None.
        @details Draft text has no review authority and no authenticated actor.
        """
        from time import monotonic

        if self.owner.job.active or self.owner.actions.active:
            return
        drafts = {
            **self.owner.session.state.get("drafts", {}),
            "review_form": {
                "text": self.editor.GetValue(),
                "reason": self.reason.GetValue(),
                "kind": self.kind.GetStringSelection(),
            },
        }
        self.owner.session.update(drafts=drafts)
        self.owner.checkpoint_due = monotonic() + 0.75

    def refresh_session(self):
        """@brief Displays retained data and refreshes current OS identity.
        @return None.
        @details Missing identity blocks decisions while preserving inspection.
        """
        try:
            principal = authenticated_principal()
            self.actor.SetLabel(
                f"Authenticated reviewer: {principal.subject} "
                f"({principal.mechanism})"
            )
            authenticated = True
        except PermissionError:
            self.actor.SetLabel(
                "OS review identity unavailable; decisions disabled"
            )
            authenticated = False
        state = self.owner.session.state
        form = state.get("drafts", {}).get("review_form", {})
        self.editor.ChangeValue(form.get("text", "{}"))
        self.reason.ChangeValue(form.get("reason", ""))
        self.kind.SetStringSelection(form.get("kind", "override"))
        self.snapshot.ChangeValue(
            canonical_json(
                {
                    "ir": state.get("drafts", {}).get("ir"),
                    "proposal": state.get("proposal"),
                    "review_history": state.get("history", []),
                }
            ).decode()
        )
        busy = self.owner.job.active or self.owner.actions.active
        self.assemble.Enable(not busy and "component_id" not in state)
        for control in (self.evidence, self.propose):
            control.Enable(
                not busy and authenticated and "component_id" in state
            )
        for control in (self.approve, self.reject):
            control.Enable(
                not busy and authenticated and bool(state.get("proposal"))
            )
        self.pdl.Enable(not busy and "component_id" in state)
        self.binding.SetLabel(
            canonical_json(state.get("pdl")).decode()
            if state.get("pdl")
            else "PDL not selected; generation blocked"
        )

    def run(self, stage, operation):
        """@brief Dispatches one serialized existing-service operation.
        @param stage User action name.
        @param operation Callable accepting a DesktopReview adapter.
        @return None.
        @details Failures produce redacted progress without GUI state advances.
        """
        try:
            if self.owner.job.active or self.owner.actions.active:
                raise ValueError("Another session action is running")
            self.owner.actions.start(
                self.owner.session,
                stage,
                lambda session, cancel, emit: operation(
                    DesktopReview(session)
                ),
            )
            self.owner.set_running(True)
            self.refresh_session()
        except Exception as error:
            self.owner.append_log(f"[{stage}] {error}")

    def on_assemble(self, _event):
        """@brief Registers explicitly entered initial engineering sections.
        @param _event wx button event.
        @return None.
        @details Missing facts remain null or empty without fixture
        substitution.
        """
        try:
            values = parse_json(self.editor.GetValue())
            assignments = values.pop("assignments", [])
            self.run(
                "assembly", lambda review: review.assemble(values, assignments)
            )
        except Exception as error:
            self.owner.append_log(f"[assembly] {error}")

    def on_evidence(self, _event):
        """@brief Proposes evidence-only review against the persisted root.
        @param _event wx button event.
        @return None.
        @details Does not change entered engineering content.
        """
        reason = self.reason.GetValue()
        self.run(
            "evidence review", lambda review: review.propose_evidence(reason)
        )

    def on_propose(self, _event):
        """@brief Dispatches exact typed fields without accepting audit
        metadata.
        @param _event wx button event.
        @return None.
        @details Numeric text retains Decimal precision through the service.
        """
        try:
            fields = parse_json(self.editor.GetValue())
            kind, reason = (
                self.kind.GetStringSelection(),
                self.reason.GetValue(),
            )
            self.run(
                "typed proposal",
                lambda review: review.propose(kind, fields, reason),
            )
        except Exception as error:
            self.owner.append_log(f"[typed proposal] {error}")

    def decide(self, approve):
        """@brief Explicitly decides the exact pending input proposal.
        @param approve Whether the user selected Approve Inputs.
        @return None.
        @details Release approval remains a separate later operation.
        """
        reason = self.reason.GetValue()
        self.run(
            "input decision",
            lambda review: review.decide_inputs(approve, reason),
        )

    def on_pdl(self, _event):
        """@brief Binds the explicitly selected exact local PDL revision.
        @param _event wx choice event.
        @return None.
        @details Family, variant and topology are service-checked.
        """
        index = self.pdl.GetSelection()
        if index == wx.NOT_FOUND:
            return
        identity, revision = self.pdls[index]
        pdl = load_pdl(identity, revision)
        self.run(
            "PDL selection",
            lambda review: review.bind_pdl(
                identity, revision, pdl.data["content_sha256"]
            ),
        )
