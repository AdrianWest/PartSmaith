"""@package partsmith.gui.review_panel
@brief Provides evidence, conflicts, component and artifact review tabs.
@details Virtual evidence rows retain large local collections; source images
are loaded on demand by content hash and bounded before display.
"""

from threading import Thread

import wx

from partsmith.ai.contracts import TASKS
from partsmith.ir.canonical import canonical_json

from .evidence import evidence_overlay, selected_request


class EvidenceList(wx.ListCtrl):
    """@brief Displays retained evidence through virtual rows.
    @details Selection retains immutable identities rather than row authority.
    """

    def __init__(self, parent):
        """@brief Creates a virtual multi-selection evidence list.
        @param parent Owning evidence tab.
        @return None.
        @details Avoids allocating one native widget for every evidence record.
        """
        super().__init__(parent, style=wx.LC_REPORT | wx.LC_VIRTUAL)
        self.records = []
        for index, title in enumerate(
            ("Page", "Type", "Status", "Original text")
        ):
            self.InsertColumn(index, title, width=(50, 90, 100, 360)[index])

    def OnGetItemText(self, item, column):
        """@brief Reads one immutable display row on demand.
        @param item Virtual row index.
        @param column Requested display column.
        @return Plain text for the requested cell.
        @details List text is shortened; requests retain original text.
        """
        record = self.records[item]
        return (
            str(record["source"]["page"]),
            record["type"],
            record["interpretation"]["status"],
            record["extracted"]["text"].replace("\n", " ")[:180],
        )[column]

    def selected_ids(self):
        """@brief Collects deliberately selected evidence identities.
        @return List of original evidence record IDs.
        @details No default first-record subset is inferred.
        """
        result = []
        index = self.GetFirstSelected()
        while index != -1:
            result.append(self.records[index]["id"])
            index = self.GetNextSelected(index)
        return result


class SourceImage(wx.Panel):
    """@brief Draws the retained page image with its source-region overlay.
    @details Proportional scaling uses the original image pixel coordinates.
    """

    def __init__(self, parent):
        """@brief Creates a source page viewport.
        @param parent Owning evidence panel.
        @return None.
        @details Keeps one derived image in memory with no source eviction.
        """
        super().__init__(parent)
        self.image = None
        self.region = None
        self.SetMinSize((-1, 240))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, lambda event: (self.Refresh(), event.Skip()))

    def paint(self, _event):
        """@brief Paints the original page and exact mapped source region.
        @param _event wx paint event.
        @return None.
        @details A red outline identifies evidence on the displayed source.
        """
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()
        if self.image is None:
            return
        width, height = self.GetClientSize()
        scale = min(
            width / self.image.GetWidth(), height / self.image.GetHeight()
        )
        if scale <= 0:
            return
        w, h = (
            max(1, round(self.image.GetWidth() * scale)),
            max(1, round(self.image.GetHeight() * scale)),
        )
        dc.DrawBitmap(
            wx.Bitmap(self.image.Scale(w, h, wx.IMAGE_QUALITY_HIGH)), 0, 0
        )
        if self.region:
            dc.SetPen(wx.Pen(wx.Colour(220, 35, 35), 2))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(
                *(
                    round(float(self.region[key]) * scale)
                    for key in ("x", "y", "width", "height")
                )
            )


class ReviewPanel(wx.Notebook):
    """@brief Hosts the shared session's review surfaces.
    @details Reviewer operations are forwarded to main-frame service adapters.
    """

    def __init__(self, parent, owner):
        """@brief Builds inspection tabs around retained session data.
        @param parent Owning scrollable panel.
        @param owner Main frame owning session and action controller.
        @return None.
        @details The panel grants no approval merely by opening a tab.
        """
        super().__init__(parent)
        self.owner = owner
        self.extracted = None
        self.metadata_binding = None
        self.image_binding = None
        self.image_sequence = 0
        from .image_loader import ImageLoader

        self.image_loader = ImageLoader(
            lambda binding, result, error: wx.CallAfter(
                self.show_image, binding, result, error
            )
        )
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)
        self.SetMinSize((-1, 580))
        evidence = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        self.summary = wx.StaticText(evidence, label="No retained extraction")
        layout.Add(self.summary, 0, wx.EXPAND | wx.ALL, 6)
        self.evidence = EvidenceList(evidence)
        self.evidence.SetMinSize((-1, 150))
        layout.Add(self.evidence, 1, wx.EXPAND)
        self.original = wx.TextCtrl(
            evidence, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.original.SetMinSize((-1, 100))
        layout.Add(self.original, 0, wx.EXPAND)
        self.image = SourceImage(evidence)
        layout.Add(self.image, 1, wx.EXPAND)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        self.task = wx.Choice(evidence, choices=list(TASKS))
        self.task.SetSelection(2)
        self.targets = wx.TextCtrl(evidence)
        self.targets.SetHint("Trusted target paths, comma separated")
        self.preview = wx.Button(evidence, label="Preview AI Request")
        self.send = wx.Button(evidence, label="Send Selected Evidence")
        for control in (self.task, self.targets, self.preview, self.send):
            controls.Add(
                control,
                1 if control is self.targets else 0,
                wx.EXPAND | wx.RIGHT,
                4,
            )
        layout.Add(controls, 0, wx.EXPAND | wx.ALL, 6)
        self.request_info = wx.StaticText(
            evidence, label="No AI request selected"
        )
        layout.Add(self.request_info, 0, wx.EXPAND | wx.ALL, 6)
        evidence.SetSizer(layout)
        self.AddPage(evidence, "Evidence")
        self.text_tabs = {}
        for title in (
            "Conflicts",
            "Component Data",
            "Symbol / Footprint",
            "Validation / Release",
        ):
            if title == "Component Data":
                from .component_panel import ComponentPanel

                tab = ComponentPanel(self, owner)
                self.component = tab
            elif title == "Symbol / Footprint":
                from .artifact_panel import ArtifactPanel

                tab = ArtifactPanel(self, owner)
                self.artifacts = tab
            elif title == "Validation / Release":
                from .release_panel import ReleasePanel

                tab = ReleasePanel(self, owner)
                self.release = tab
            else:
                tab = wx.TextCtrl(
                    self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
                )
            self.AddPage(tab, title)
            self.text_tabs[title] = tab
        self.evidence.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_evidence)
        from .integration_panel import IntegrationPanel

        self.integration = IntegrationPanel(self, owner)
        self.AddPage(self.integration, "Project Libraries")
        self.preview.Bind(wx.EVT_BUTTON, self.on_preview)
        self.send.Bind(wx.EVT_BUTTON, self.on_send)

    def refresh_session(self):
        """@brief Displays a detached retained session snapshot.
        @return None.
        @details Provider ambiguities and conflicts remain unreviewed.
        """
        session = self.owner.session
        self.integration.refresh_session()
        self.extracted = session.display_extraction()
        if self.extracted is None and session.state.get("extraction"):
            binding = (
                session.instance_id,
                session.state["extraction"]["$asset"],
            )
            if binding != self.metadata_binding:
                self.metadata_binding = binding

                def metadata():
                    """@brief Prepares retained metadata outside the wx thread.
                    @return None.
                    @details Superseded instance results cannot change the
                    view.
                    """
                    session.extraction()
                    wx.CallAfter(self.metadata_ready, binding)

                Thread(
                    target=metadata,
                    name="PartSmith evidence metadata",
                    daemon=True,
                ).start()
        self.evidence.records = (
            self.extracted["evidence"] if self.extracted else []
        )
        self.evidence.SetItemCount(len(self.evidence.records))
        self.evidence.Refresh()
        if self.extracted:
            document = self.extracted["document"]
            self.summary.SetLabel(
                f"{document['page_count']} pages; selected "
                f"{self.extracted['selected_pages']}; "
                f"{len(self.evidence.records)} local records; UNREVIEWED"
            )
        else:
            self.summary.SetLabel("No retained extraction")
        self.original.ChangeValue("")
        self.image.image, self.image.region = None, None
        self.image.Refresh()
        self.text_tabs["Conflicts"].ChangeValue(
            canonical_json(
                session.state.get("ai", {"status": "No provider results"})
            ).decode()
        )
        self.component.refresh_session()
        self.artifacts.refresh_session()
        self.release.refresh_session()

    def on_evidence(self, event):
        """@brief Displays original text, provenance and page-region overlay.
        @param event Evidence selection event.
        @return None.
        @details Failing image inspection leaves evidence and saving usable.
        """
        record = self.evidence.records[event.GetIndex()]
        self.original.ChangeValue(canonical_json(record).decode())
        self.image_sequence += 1
        self.image_binding = (
            self.owner.session.instance_id,
            self.image_sequence,
        )
        self.image.image, self.image.region = None, None
        self.image.Refresh()
        try:
            render, region = evidence_overlay(self.extracted, record)
            if render:
                reference = self.extracted["assets"][render["image_sha256"]]
                budget = self.owner.session.state["budgets"][
                    "image_cache_bytes"
                ]
                if (
                    int(render["width_px"]) * int(render["height_px"]) * 4
                    > budget
                ):
                    raise ValueError(
                        "Page image exceeds display-cache budget; "
                        "re-extract at lower DPI"
                    )
                self.image.region = region
                self.image_loader.request(
                    self.image_binding,
                    self.owner.session,
                    reference,
                    (render["width_px"], render["height_px"]),
                    budget,
                )
            else:
                self.image.image, self.image.region = None, None
            self.image.Refresh()
        except Exception as error:
            self.owner.append_log(f"[evidence image] {error}")

    def metadata_ready(self, binding):
        """@brief Refreshes evidence only for the current prepared snapshot.
        @param binding Originating immutable session and extraction identities.
        @return None.
        @details Closing or replaced views discard asynchronous results.
        """
        if (
            self
            and binding == self.metadata_binding
            and binding[0] == self.owner.session.instance_id
        ):
            self.refresh_session()

    def show_image(self, binding, result, error):
        """@brief Allocates only a validated RGB wx display image on the GUI.
        @param binding Originating instance and latest selection identity.
        @param result Bounded width, height and decoded RGB bytes or None.
        @param error Safe error detail to pass through main-window redaction.
        @return None.
        @details Stale selection/session results are discarded before display.
        """
        if (
            not self
            or binding != self.image_binding
            or binding[0] != self.owner.session.instance_id
        ):
            return
        if error:
            self.owner.append_log(f"[evidence image] {error}")
            return
        width, height, rgb = result
        self.image.image = wx.Image(width, height, rgb)
        self.image.Refresh()

    def on_destroy(self, event):
        """@brief Releases the disposable display loader with its owner.
        @param event wx window-destroy event.
        @return None.
        @details Pending decodes cannot publish into a destroyed review window.
        """
        if event.GetEventObject() is self:
            self.image_loader.close()
        event.Skip()

    def request(self):
        """@brief Validates the exact selected AI request.
        @return Immutable AIRequest.
        @details Oversized requests remain locally inspectable in full.
        """
        targets = tuple(
            path.strip()
            for path in self.targets.GetValue().split(",")
            if path.strip()
        )
        return selected_request(
            self.owner.session,
            self.task.GetStringSelection(),
            self.evidence.selected_ids(),
            targets,
        )

    def on_preview(self, _event):
        """@brief Displays provider, model, record count and request bytes.
        @param _event wx button event.
        @return None.
        @details This action makes no provider call.
        """
        from partsmith.ai.openai import MODEL

        try:
            request = self.request()
            self.request_info.SetLabel(
                f"OpenAI / {MODEL}: {len(request.data['evidence'])} "
                f"records; {len(request._snapshot)} canonical bytes / 524288; "
                "store=false; account retention and API charges apply"
            )
        except Exception as error:
            self.request_info.SetLabel(str(error))
            self.owner.append_log(f"[AI selection] {error}")

    def on_send(self, _event):
        """@brief Sends the deliberate selection through the provider adapter.
        @param _event wx button event.
        @return None.
        @details Request limits and disclosure are displayed before dispatch.
        """
        self.on_preview(None)
        try:
            request = self.request()
            self.owner.send_ai(request)
        except Exception as error:
            self.owner.append_log(f"[AI selection] {error}")
