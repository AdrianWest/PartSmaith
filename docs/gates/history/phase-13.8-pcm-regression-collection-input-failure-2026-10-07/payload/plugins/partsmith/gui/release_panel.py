"""@package partsmith.gui.release_panel
@brief Displays exact validation results and explicit final release decisions.
@details Approval is bound to the current revision, actual artifacts, manifest
and post-manifest checks, using a freshly authenticated OS principal.
"""

import wx

from .identity import authenticated_principal
from .release_review import decide_release, release_report


class ReleasePanel(wx.Panel):
    """@brief Hosts final validation, blockers and separate release review.
    @details Opening this panel never creates a decision.
    """

    def __init__(self, parent, owner):
        """@brief Builds final review content and explicit decision controls.
        @param parent Main review notebook.
        @param owner Main frame owning the session action controller.
        @return None.
        @details Current actor identity is obtained from the OS, not transport.
        """
        super().__init__(parent)
        self.owner = owner
        layout = wx.BoxSizer(wx.VERTICAL)
        self.actor = wx.StaticText(self)
        layout.Add(self.actor, 0, wx.EXPAND | wx.ALL, 5)
        self.content = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        layout.Add(self.content, 1, wx.EXPAND)
        self.reason = wx.TextCtrl(self)
        self.reason.SetHint("Reason for the separate release decision")
        layout.Add(self.reason, 0, wx.EXPAND | wx.ALL, 5)
        row = wx.WrapSizer(wx.HORIZONTAL)
        self.approve = wx.Button(self, label="Approve Exact Release")
        self.reject = wx.Button(self, label="Reject Release")
        self.inspect = wx.Button(self, label="Inspect Symbol / Footprint")
        self.viewer = wx.Button(self, label="Open 3D Placement Viewer")
        for item in (self.approve, self.reject, self.inspect, self.viewer):
            row.Add(item, 0, wx.ALL, 3)
        layout.Add(row, 0, wx.EXPAND)
        self.SetSizer(layout)
        self.approve.Bind(wx.EVT_BUTTON, lambda event: self.decide(True))
        self.reject.Bind(wx.EVT_BUTTON, lambda event: self.decide(False))
        self.inspect.Bind(
            wx.EVT_BUTTON, lambda event: owner.review.SetSelection(3)
        )
        self.viewer.Bind(wx.EVT_BUTTON, owner.on_viewer)
        self.reason.Bind(wx.EVT_TEXT, self.on_reason)

    def on_reason(self, _event):
        """@brief Retains unfinished release rationale for Save/recovery.
        @param _event wx text edit event.
        @return None.
        @details Draft rationale has no decision authority.
        """
        session = self.owner.session
        session.update(
            drafts={
                **session.state.get("drafts", {}),
                "release_reason": self.reason.GetValue(),
            }
        )
        self.owner.checkpoint_due = 0

    def refresh_session(self):
        """@brief Displays actual bound validation and exact review blockers.
        @return None.
        @details All mutable release controls disable during a service action.
        """
        session = self.owner.session
        try:
            principal = authenticated_principal()
            self.actor.SetLabel(
                f"Authenticated release reviewer: {principal.subject}"
            )
            authenticated = True
        except PermissionError as error:
            self.actor.SetLabel(str(error))
            authenticated = False
        report = release_report(session)
        self.report = report
        lines = [
            f"Build: {report['build_id']}",
            f"Reviewed revision: {report['revision_id']}",
            "",
        ]
        release = session.state.get("release") or {}
        lines.append(
            "Release decision: "
            + (
                "APPROVED"
                if release.get("approved")
                else "REJECTED"
                if session.state.get("status") == "release-rejected"
                else "Explicit release review required"
            )
        )
        lines.append("Blockers: " + ("; ".join(report["blockers"]) or "None"))
        lines.extend(["", "Final artifact checks:"])
        for result in report.get("validation", []):
            lines.append(
                f"{result['status']}  {result['rule_id']}: "
                f"{result.get('message', '')}"
            )
            if result["status"] == "FAIL":
                lines.append(
                    f"  Expected: {result.get('expected')} / "
                    f"measured: {result.get('measured')}"
                )
        for post in report.get("post_manifest_reports", []):
            lines.extend(["", "Post-manifest checks:"])
            for result in post.get("results", []):
                lines.append(
                    f"{result['status']}  {result['rule_id']}: "
                    f"{result.get('message', '')}"
                )
        lines.extend(["", "Exact approval binding:"])
        for key, value in release.get("binding", {}).items():
            lines.append(f"{key}: {value}")
        self.content.ChangeValue("\n".join(lines))
        busy = self.owner.actions.active or self.owner.job.active
        pending = bool(session.state.get("release")) and report.get(
            "review_required", False
        )
        self.approve.Enable(
            authenticated and pending and not busy and not report["blockers"]
        )
        self.reject.Enable(authenticated and pending and not busy)
        self.reason.Enable(not busy)
        self.reason.ChangeValue(
            session.state.get("drafts", {}).get("release_reason", "")
        )

    def decide(self, approve):
        """@brief Runs a deliberate separate release decision on a worker.
        @param approve Whether the user chose explicit release approval.
        @return None.
        @details The service rechecks all exact bindings inside its
        transaction.
        """
        reason = self.reason.GetValue()
        try:
            self.owner.actions.start(
                self.owner.session,
                "release-review",
                lambda session, cancel, emit: decide_release(
                    session, approve, reason
                ),
            )
            self.owner.set_running(True)
        except Exception as error:
            self.owner.append_log(f"[release review] {error}")
