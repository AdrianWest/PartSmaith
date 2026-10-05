"""wxPython setup window for the Phase 9.5 processing boundary."""

from importlib.resources import files
from io import BytesIO
from pathlib import Path

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from .credentials import CredentialError, CredentialStore
from .processing import (
    JobController,
    ProcessingRequest,
    Redactor,
    process_datasheet,
)


def banner_bytes():
    resource = files("partsmith.gui").joinpath("PartSmith-Banner.png")
    if resource.is_file():
        return resource.read_bytes()
    return (
        Path(__file__).resolve().parents[3]
        / "resources"
        / "PartSmith-Banner.png"
    ).read_bytes()


class KeyDialog(wx.Dialog):
    """Every instance starts blank; saved secrets are never read here."""

    def __init__(self, parent, store):
        super().__init__(parent, title=f"Set {store.provider} API Key")
        self.store = store
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(
            wx.StaticText(self, label="Enter a new API key:"), 0, wx.ALL, 12
        )
        self.key = wx.TextCtrl(self, value="", style=wx.TE_PASSWORD)
        self.key.SetMinSize((400, -1))
        layout.Add(self.key, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        self.message = wx.StaticText(self, label="")
        self.message.SetMinSize((400, 42))
        layout.Add(self.message, 0, wx.EXPAND | wx.ALL, 12)
        layout.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALL, 12)
        self.SetSizerAndFit(layout)
        self.Bind(wx.EVT_BUTTON, self.on_save, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self.on_cancel)
        self.key.SetFocus()
        self.CentreOnParent()

    def on_save(self, _event):
        try:
            self.store.save(self.key.GetValue())
        except CredentialError as error:
            self.message.SetLabel(str(error))
            self.message.Wrap(400)
            self.Layout()
            return
        self.key.ChangeValue("")
        self.EndModal(wx.ID_OK)

    def on_cancel(self, _event):
        self.key.ChangeValue("")
        self.EndModal(wx.ID_CANCEL)


class Banner(wx.Panel):
    """Fit the original banner without distorting it."""

    def __init__(self, parent):
        super().__init__(parent)
        self.image = wx.Image(BytesIO(banner_bytes()), wx.BITMAP_TYPE_PNG)
        if not self.image.IsOk():
            raise RuntimeError("The packaged banner could not be loaded.")
        self.SetMinSize((-1, 1))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, self.resize)

    def resize(self, event):
        width = self.GetClientSize().width
        height = max(
            1, round(width * self.image.GetHeight() / self.image.GetWidth())
        )
        if self.GetMinSize().height != height:
            self.SetMinSize((-1, height))
            self.GetParent().Layout()
        self.Refresh()
        event.Skip()

    def paint(self, _event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.Colour(255, 255, 255)))
        dc.Clear()
        width, height = self.GetClientSize()
        scale = width / self.image.GetWidth()
        if scale <= 0:
            return
        w = max(1, round(self.image.GetWidth() * scale))
        h = max(1, round(self.image.GetHeight() * scale))
        bitmap = wx.Bitmap(self.image.Scale(w, h, wx.IMAGE_QUALITY_HIGH))
        dc.DrawBitmap(bitmap, (width - w) // 2, (height - h) // 2, True)


class SetupFrame(wx.Frame):
    def __init__(self, store=None, worker=None):
        super().__init__(None, title="PartSmith Setup", size=(840, 860))
        self.SetMinSize((620, 740))
        self.store = store or CredentialStore()
        self.job = JobController() if worker is None else JobController(worker)
        if worker is None:
            self.job.worker = lambda request, log, cancel: process_datasheet(
                request,
                log,
                cancel,
                self.store.read_for_processing,
                lambda bundle: self.job.events.put(("candidates", bundle)),
            )
        self.ai_candidates = None
        self.redact = Redactor()
        self.closing = False
        self.starting = False
        root = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)
        self.banner = Banner(root)
        outer.Add(self.banner, 0, wx.EXPAND)
        panel = ScrolledPanel(root)
        outer.Add(panel, 1, wx.EXPAND)
        root.SetSizer(outer)
        layout = wx.BoxSizer(wx.VERTICAL)
        credentials = wx.BoxSizer(wx.HORIZONTAL)
        self.key_button = wx.Button(panel, label="Set AI API Key")
        self.key_status = wx.StaticText(panel)
        credentials.Add(self.key_button, 0, wx.RIGHT, 12)
        credentials.Add(self.key_status, 1, wx.ALIGN_CENTER_VERTICAL)
        layout.Add(credentials, 0, wx.EXPAND | wx.ALL, 12)
        self.file_button = wx.Button(panel, label="Select Datasheet")
        layout.Add(self.file_button, 0, wx.LEFT | wx.RIGHT, 12)
        self.source = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self.source.SetHint("Select a local PDF datasheet")
        layout.Add(self.source, 0, wx.EXPAND | wx.ALL, 12)
        layout.Add(
            wx.StaticText(panel, label="Required Part Number"),
            0,
            wx.LEFT | wx.RIGHT,
            12,
        )
        self.part = wx.TextCtrl(panel)
        self.part.SetHint("Full manufacturer part number, including suffixes")
        layout.Add(self.part, 0, wx.EXPAND | wx.ALL, 12)
        self.ai_enabled = wx.CheckBox(
            panel, label="Send selected Evidence to OpenAI for interpretation"
        )
        layout.Add(self.ai_enabled, 0, wx.LEFT | wx.RIGHT, 12)
        from partsmith.ai.openai import MODEL

        disclosure = self.ai_disclosure = wx.StaticText(
            panel,
            label=(
                f"OpenAI / {MODEL}: selected extracted text and provenance; "
                "local OCR. "
                "store=false; provider retention follows account terms. "
                "API charges paid to OpenAI. Candidates require human review."
            ),
        )
        disclosure.Wrap(550)
        layout.Add(disclosure, 0, wx.EXPAND | wx.ALL, 12)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        self.start = wx.Button(panel, label="Start")
        self.cancel = wx.Button(panel, label="Cancel")
        controls.Add(self.start, 0, wx.RIGHT, 8)
        controls.Add(self.cancel)
        self.status = wx.StaticText(panel, label="Ready")
        controls.Add(self.status, 1, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 12)
        layout.Add(controls, 0, wx.EXPAND | wx.ALL, 12)
        layout.Add(
            wx.StaticText(panel, label="Processing Log"),
            0,
            wx.LEFT | wx.RIGHT,
            12,
        )
        self.logs = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        self.logs.SetMinSize((-1, 160))
        layout.Add(self.logs, 1, wx.EXPAND | wx.ALL, 12)
        panel.SetSizer(layout)
        panel.SetupScrolling(scroll_x=False)
        self.refresh_credentials()
        self.set_running(False)
        self.key_button.Bind(wx.EVT_BUTTON, self.on_key)
        self.file_button.Bind(wx.EVT_BUTTON, self.on_file)
        self.start.Bind(wx.EVT_BUTTON, self.on_start)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.poll, self.timer)
        self.timer.Start(75)
        self.Centre()

    def refresh_credentials(self):
        try:
            configured = self.store.configured()
        except CredentialError:
            state = "secure store unavailable"
        else:
            state = "configured" if configured else "not configured"
        self.key_status.SetLabel(f"{self.store.provider}: {state}")

    def set_running(self, running):
        for control in (
            self.start,
            self.key_button,
            self.file_button,
            self.part,
            self.ai_enabled,
        ):
            control.Enable(not running)
        self.cancel.Enable(running)

    def append_log(self, message):
        self.logs.AppendText(self.redact(message) + "\n")

    def on_key(self, _event):
        if self.job.active:
            return
        with KeyDialog(self, self.store) as dialog:
            dialog.ShowModal()
        self.refresh_credentials()

    def on_file(self, _event):
        if self.job.active:
            return
        with wx.FileDialog(
            self,
            "Select PDF Datasheet",
            wildcard="PDF datasheets (*.pdf)|*.pdf",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.source.ChangeValue(dialog.GetPath())

    def on_start(self, _event):
        if self.job.active or self.starting:
            return
        self.starting = True
        request = ProcessingRequest(
            Path(self.source.GetValue()),
            self.part.GetValue(),
            self.ai_enabled.GetValue(),
        )
        try:
            request.validate()
            try:
                key = self.store.read_for_processing()
            except CredentialError:
                if request.use_ai:
                    raise
                key = None
            self.redact = Redactor((key,))
            self.set_running(True)
            self.status.SetLabel("Running")
            self.ai_candidates = None
            self.job.start(request, secrets=(key,))
        except (ValueError, CredentialError, RuntimeError) as error:
            self.set_running(False)
            self.append_log(str(error))
            self.status.SetLabel("Could not start")
        finally:
            self.starting = False

    def on_cancel(self, _event):
        self.job.cancel()
        self.cancel.Disable()
        self.status.SetLabel("Cancelling…")

    def poll(self, _event):
        if self.starting:
            return
        for kind, message in self.job.drain():
            if kind == "log":
                self.append_log(message)
            elif kind == "candidates":
                self.ai_candidates = message
            else:
                self.status.SetLabel(message.capitalize())
        if not self.job.active:
            if self.closing:
                self.timer.Stop()
                self.Destroy()
            else:
                self.set_running(False)

    def on_close(self, event):
        if self.job.active:
            self.closing = True
            self.on_cancel(None)
            if event.CanVeto():
                event.Veto()
                return
        self.timer.Stop()
        event.Skip()
