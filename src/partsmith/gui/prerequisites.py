"""@package partsmith.gui.prerequisites
@brief Displays missing manual OCR prerequisites with clickable install links.
@details A blocking dialog appears before the main frame or session recovery.
Links open only when clicked; installation is always a deliberate user action.
"""

import wx
import wx.adv

from partsmith.external_dependencies import ExternalDependencyIssue


class MissingDependenciesDialog(wx.Dialog):
    """@brief Lists the manual prerequisites preventing application startup.
    @details Scrolls on smaller displays and retains native clickable links.
    """

    def __init__(
        self,
        issues: tuple[ExternalDependencyIssue, ...],
        parent=None,
        host_alive=None,
    ):
        """@brief Builds an error dialog containing only missing manual items.
        @param issues Verified external prerequisite issues for this launch.
        @param parent Optional owning window; startup normally has no frame.
        @param host_alive Optional launching KiCad process lifetime callback.
        @return None.
        @details Does not open a browser or run an installer during creation.
        """
        super().__init__(
            parent,
            title="PartSmith - Required software is missing",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        layout = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self,
            label="PartSmith cannot start until these items are installed:",
        )
        heading.SetFont(heading.GetFont().Bold())
        layout.Add(heading, 0, wx.ALL, 16)
        content = wx.ScrolledWindow(self)
        content.SetScrollRate(0, 12)
        rows = wx.BoxSizer(wx.VERTICAL)
        for issue in issues:
            name = wx.StaticText(content, label=issue.name)
            name.SetFont(name.GetFont().Bold())
            rows.Add(name, 0, wx.TOP | wx.BOTTOM, 6)
            description = wx.StaticText(
                content, label=issue.reason + "\n" + issue.instructions
            )
            description.Wrap(560)
            rows.Add(description, 0, wx.BOTTOM, 8)
            link = wx.adv.HyperlinkCtrl(
                content, label="Get " + issue.name, url=issue.url
            )
            rows.Add(link, 0, wx.BOTTOM, 18)
        content.SetSizer(rows)
        layout.Add(content, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 16)
        footer = wx.StaticText(
            self, label="Install the listed items, then restart PartSmith."
        )
        layout.Add(footer, 0, wx.ALL, 16)
        close = wx.Button(self, wx.ID_OK, "Close PartSmith")
        close.SetDefault()
        layout.Add(
            close, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16
        )
        self.SetSizer(layout)
        self.SetMinSize((640, 340))
        self.SetSize((660, min(720, 230 + 150 * len(issues))))
        self.CentreOnScreen()
        self.host_alive = host_alive
        self.timer = wx.Timer(self)
        if host_alive is not None:
            self.Bind(wx.EVT_TIMER, self._check_host, self.timer)
            self.timer.Start(250)

    def _check_host(self, _event):
        """@brief Closes the startup error if its launching host has exited.
        @param _event Native timer event; unused.
        @return None.
        @details Prevents an error popup from outliving the KiCad process.
        """
        if not self.host_alive():
            self.stop_monitoring()
            if self.IsModal():
                self.EndModal(wx.ID_CANCEL)

    def stop_monitoring(self):
        """@brief Stops the owned timer before destroying the error dialog.
        @return None.
        @details Safe whether monitoring was enabled or has already stopped.
        """
        self.timer.Stop()


def show_missing_dependencies(
    issues: tuple[ExternalDependencyIssue, ...], parent=None, host_alive=None
) -> None:
    """@brief Presents clickable manual-install guidance and waits for close.
    @param issues Missing or unusable external prerequisites for this launch.
    @param parent Optional parent window.
    @param host_alive Optional launching KiCad process lifetime callback.
    @return None.
    @details The caller must own a wx.App and stop startup after this dialog.
    """
    with MissingDependenciesDialog(issues, parent, host_alive) as dialog:
        try:
            dialog.ShowModal()
        finally:
            dialog.stop_monitoring()
