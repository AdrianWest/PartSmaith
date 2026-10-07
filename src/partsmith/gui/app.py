"""@package partsmith.gui.app
@brief Hosts durable acquisition, evidence, input and exact release review.
@details Native work is isolated and the owned modeless viewer separates
display state and unapproved placement drafts from engineering decisions.
"""

from importlib.resources import files
from io import BytesIO
from pathlib import Path
from time import monotonic
from uuid import uuid4

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from .actions import ActionController
from .credentials import CredentialError, CredentialStore
from .processing import (
    JobController,
    ProcessingRequest,
    Redactor,
    process_datasheet,
)
from .session import Session


def banner_bytes(name="PartSmith-Banner3.png"):
    """@brief Reads the packaged setup banner.
    @return bytes containing the PNG image.
    @param name Exact packaged banner resource name.
    @details Falls back to the source resource independent of cwd.
    """
    resource = files("partsmith.gui").joinpath(name)
    if resource.is_file():
        return resource.read_bytes()
    return (
        Path(__file__).resolve().parents[3] / "resources" / name
    ).read_bytes()


class KeyDialog(wx.Dialog):
    """Every instance starts blank; saved secrets are never read here."""

    def __init__(self, parent, store):
        """@brief Initializes the wx window and its owned controls.
        @param parent Owning wx window.
        @param store Secure credential adapter.
        @return None.
        @details Binds GUI events and retains the owning application state.
        """
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
        """@brief Stores the newly entered API key.
        @param _event wx event; unused.
        @return None.
        @details Store failure retains the dialog; success clears input.
        """
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
        """@brief Cancels this dialog or processing operation.
        @param _event wx event; unused.
        @return None.
        @details Requests cleanup without exporting a saved credential.
        """
        self.key.ChangeValue("")
        self.EndModal(wx.ID_CANCEL)


class Banner(wx.Panel):
    """Fit the original banner without distorting it."""

    def __init__(self, parent, name="PartSmith-Banner3.png", log=None):
        """@brief Initializes the wx window and its owned controls.
        @param parent Owning wx window.
        @param name Exact banner resource name.
        @param log Optional main-window log callback for resource failure.
        @return None.
        @details Binds GUI events and retains the owning application state.
        """
        super().__init__(parent)
        self.error = None
        try:
            self.image = wx.Image(
                BytesIO(banner_bytes(name)), wx.BITMAP_TYPE_PNG
            )
            if not self.image.IsOk():
                raise ValueError("Unreadable banner")
        except Exception:
            self.image = None
            self.error = f"Banner unavailable: {name}; setup remains usable"
            if log is not None:
                log(self.error)
        self.SetMinSize((-1, 1))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.scaled_banner = None
        self.scaled_banner_key = None
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_SIZE, self.resize)
        if hasattr(wx, "EVT_DPI_CHANGED"):
            self.Bind(wx.EVT_DPI_CHANGED, self.resize)

    def resize(self, event):
        """@brief Updates banner height to match its original aspect ratio.
        @param event wx event to propagate or veto.
        @return None.
        @details Relayouts the parent after a client-width change.
        """
        width = self.GetClientSize().width
        if width <= 0 or self.image is None:
            event.Skip()
            return
        height = max(
            1, round(width * self.image.GetHeight() / self.image.GetWidth())
        )
        if self.GetMinSize().height != height:
            self.SetMinSize((-1, height))
            self.GetParent().Layout()
        self.Refresh()
        event.Skip()

    def paint(self, _event):
        """@brief Draws the complete setup banner.
        @param _event wx event; unused.
        @return None.
        @details Scales proportionally in a temporary buffered paint context.
        """
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.Colour(255, 255, 255)))
        dc.Clear()
        width, height = self.GetClientSize()
        if self.image is None:
            return
        scale = width / self.image.GetWidth()
        if scale <= 0:
            return
        w = max(1, round(self.image.GetWidth() * scale))
        h = max(1, round(self.image.GetHeight() * scale))
        bitmap = self.display_bitmap(w)
        dc.DrawBitmap(bitmap, (width - w) // 2, (height - h) // 2, True)

    def display_bitmap(self, width, scale_factor=None):
        """@brief Builds a cached high-quality bitmap for the actual display
        DPI.
        @param width Logical full client width.
        @param scale_factor Optional explicit DPI scale for display
        verification.
        @return Proportional bitmap using the complete loaded source image.
        @details No crop, fixed ratio or fallback banner is introduced.
        """
        factor = (
            self.GetContentScaleFactor()
            if scale_factor is None
            else scale_factor
        )
        key = (width, factor)
        if self.scaled_banner_key != key:
            physical_width = max(1, round(width * factor))
            physical_height = max(
                1,
                round(
                    physical_width
                    * self.image.GetHeight()
                    / self.image.GetWidth()
                ),
            )
            self.scaled_banner = wx.Bitmap(
                self.image.Scale(
                    physical_width, physical_height, wx.IMAGE_QUALITY_HIGH
                )
            )
            self.scaled_banner.SetScaleFactor(factor)
            self.scaled_banner_key = key
        return self.scaled_banner


class SetupFrame(wx.Frame):
    def __init__(
        self,
        store=None,
        worker=None,
        session=None,
        recover=True,
        inspect_pcb=None,
        host_alive=None,
    ):
        """@brief Initializes the wx window and its owned controls.
        @param store Secure credential adapter.
        @param worker Optional cancellable processing worker.
        @param session Optional isolated working session.
        @param recover Whether to offer the last recovery checkpoint.
        @param inspect_pcb Optional explicit PCB-inspection callback.
        @param host_alive Optional read-only launching-host lifetime callback.
        @return None.
        @details Binds GUI events without invoking optional PCB inspection.
        """
        super().__init__(None, title="PartSmith Setup", size=(840, 860))
        self.SetMinSize((620, 740))
        self.store = store or CredentialStore()
        self.session = session or Session()
        self.actions = ActionController()
        self.after_save = None
        self.checkpoint_due = None
        self.log_budget_exceeded = False
        self.job = JobController() if worker is None else JobController(worker)
        if worker is None:
            self.job.worker = self.process_session
        self.ai_candidates = None
        self.redact = Redactor()
        self.closing = False
        self.close_requested = False
        self.running = None
        self.starting = False
        self.prototype = None
        self.prototype_camera = None
        self.viewer = None
        self.pending_session = None
        self.pending_viewer_camera = None
        self.inspect_pcb = inspect_pcb
        self.host_alive = host_alive
        self.host_exited = False
        root = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)
        self.banner = Banner(root)
        outer.Add(self.banner, 0, wx.EXPAND)
        panel = ScrolledPanel(root)
        outer.Add(panel, 1, wx.EXPAND)
        root.SetSizer(outer)
        frame_layout = wx.BoxSizer(wx.VERTICAL)
        frame_layout.Add(root, 1, wx.EXPAND)
        self.SetSizer(frame_layout)
        layout = wx.BoxSizer(wx.VERTICAL)
        credentials = wx.BoxSizer(wx.HORIZONTAL)
        self.key_button = wx.Button(panel, label="Set AI API Key")
        self.key_status = wx.StaticText(panel)
        credentials.Add(self.key_button, 0, wx.RIGHT, 12)
        credentials.Add(self.key_status, 1, wx.ALIGN_CENTER_VERTICAL)
        layout.Add(credentials, 0, wx.EXPAND | wx.ALL, 12)
        session_controls = wx.BoxSizer(wx.HORIZONTAL)
        self.save_button = wx.Button(panel, label="Save Session")
        self.load_button = wx.Button(panel, label="Load Session")
        self.clear_button = wx.Button(panel, label="New / Clear Component")
        self.budget_button = wx.Button(panel, label="Resource Limits")
        for button in (
            self.save_button,
            self.load_button,
            self.clear_button,
            self.budget_button,
        ):
            session_controls.Add(button, 0, wx.RIGHT, 8)
        layout.Add(session_controls, 0, wx.EXPAND | wx.ALL, 12)
        if inspect_pcb is not None:
            self.inspect_button = wx.Button(panel, label="Inspect PCB...")
            self.inspect_button.Bind(wx.EVT_BUTTON, self.on_inspect_pcb)
            layout.Add(
                self.inspect_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12
            )
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
        acquisition = wx.BoxSizer(wx.HORIZONTAL)
        self.pages = wx.TextCtrl(panel, value="All Pages")
        self.dpi = wx.SpinCtrl(panel, min=72, max=600, initial=200)
        self.ocr_force = wx.CheckBox(panel, label="Force OCR")
        self.ocr_languages = wx.TextCtrl(panel, value="eng,deu,chi_sim")
        for title, control in (
            ("Pages", self.pages),
            ("DPI", self.dpi),
            ("OCR languages", self.ocr_languages),
        ):
            acquisition.Add(
                wx.StaticText(panel, label=title),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                4,
            )
            acquisition.Add(control, 1, wx.RIGHT, 8)
        acquisition.Add(self.ocr_force, 0, wx.ALIGN_CENTER_VERTICAL)
        layout.Add(acquisition, 0, wx.EXPAND | wx.ALL, 12)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        self.start = wx.Button(panel, label="Start")
        self.cancel = wx.Button(panel, label="Cancel")
        controls.Add(self.start, 0, wx.RIGHT, 8)
        controls.Add(self.cancel)
        self.status = wx.StaticText(panel, label="Ready")
        controls.Add(self.status, 1, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 12)
        layout.Add(controls, 0, wx.EXPAND | wx.ALL, 12)
        self.viewer_button = wx.Button(panel, label="Open 3D Placement Viewer")
        self.viewer_button.Disable()
        layout.Add(self.viewer_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        from .review_panel import ReviewPanel

        self.review = ReviewPanel(panel, self)
        layout.Add(self.review, 1, wx.EXPAND | wx.ALL, 12)
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
        if self.banner.error is not None:
            self.append_log(self.banner.error)
        self.refresh_credentials()
        self.set_running(False)
        self.key_button.Bind(wx.EVT_BUTTON, self.on_key)
        self.file_button.Bind(wx.EVT_BUTTON, self.on_file)
        self.start.Bind(wx.EVT_BUTTON, self.on_start)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.viewer_button.Bind(wx.EVT_BUTTON, self.on_viewer)
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_session)
        self.load_button.Bind(wx.EVT_BUTTON, self.on_load_session)
        self.clear_button.Bind(wx.EVT_BUTTON, self.on_clear_session)
        self.budget_button.Bind(wx.EVT_BUTTON, self.on_budgets)
        self.part.Bind(wx.EVT_TEXT, self.on_setup_changed)
        self.ai_enabled.Bind(wx.EVT_CHECKBOX, self.on_setup_changed)
        self.pages.Bind(wx.EVT_TEXT, self.on_setup_changed)
        self.ocr_languages.Bind(wx.EVT_TEXT, self.on_setup_changed)
        self.dpi.Bind(wx.EVT_SPINCTRL, self.on_setup_changed)
        self.ocr_force.Bind(wx.EVT_CHECKBOX, self.on_setup_changed)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.poll, self.timer)
        self.timer.Start(75)
        self.Centre()
        if recover:
            wx.CallAfter(self.offer_recovery)

    def on_inspect_pcb(self, event):
        """@brief Runs PCB inspection only after the user presses its button.
        @param event Deliberate inspection-button event.
        @return None.
        @details The launcher owns board selection and transient IPC lifetime.
        """
        if self.inspect_pcb is not None:
            self.inspect_pcb(self)

    def process_session(self, request, log, cancel):
        """@brief Processes an immutable source and retains all local results.
        @param request User acquisition request.
        @param log Redacted progress callback.
        @param cancel Cooperative cancellation event.
        @return Processing operational status.
        @details Session connections are opened only in this worker thread.
        """
        session = self.session
        session.busy = True
        try:
            snapshot = session.acquire(request.datasheet)
            retained = ProcessingRequest(snapshot, request.part_number, False)
            from .evidence import parse_pages

            setup = session.state["setup"]
            acquisition_id = str(uuid4())
            options = {
                "pages": parse_pages(setup.get("pages", "All Pages")),
                "dpi": int(setup.get("dpi", 200)),
                "force_ocr": setup.get("force_ocr", False),
                "language_hints": setup.get("ocr_languages", ["eng"]),
                "acquisition_revision_id": acquisition_id,
                "output_budget": int(session.state["budgets"]["log_bytes"]),
            }
            session.update(acquisition_id=acquisition_id)
            return process_datasheet(
                retained,
                log,
                cancel,
                self.store.read_for_processing,
                lambda bundle: self.job.events.put(("candidates", bundle)),
                session.retain_extraction,
                options,
            )
        finally:
            session.busy = False

    def on_setup_changed(self, _event):
        """@brief Retains unfinished setup edits for save and recovery.
        @param _event wx edit event.
        @return None.
        @details An assembled component's ordering number is immutable in
        setup. Another component starts through the unsaved-work transition.
        """
        if self.job.active or self.actions.active:
            return
        if self.session.state.get("component_id"):
            bound = self.session.state["drafts"]["ir"]["identity"]["mpn"]
            if self.part.GetValue() != bound:
                self.part.ChangeValue(bound)
                self.append_log(
                    "Use New / Clear Component before changing the required "
                    "part number. The current component identity is retained."
                )
        self.session.update(
            setup={
                "source_path": self.source.GetValue(),
                "part_number": self.part.GetValue(),
                "use_ai": self.ai_enabled.GetValue(),
                "pages": self.pages.GetValue(),
                "dpi": self.dpi.GetValue(),
                "force_ocr": self.ocr_force.GetValue(),
                "ocr_languages": [
                    item.strip()
                    for item in self.ocr_languages.GetValue().split(",")
                    if item.strip()
                ],
            }
        )

        self.checkpoint_due = monotonic() + 0.75

    def choose_save(self, continuation=None):
        """@brief Starts a durable save before an optional transition.
        @param continuation Optional callback after successful save.
        @return Whether a save was started.
        @details Cancelled chooser or failed save retains the current session.
        """
        if self.job.active or self.actions.active:
            return False
        with wx.FileDialog(
            self,
            "Save PartSmith Session",
            wildcard="PartSmith session (*.partsmith)|*.partsmith",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return False
            destination = Path(dialog.GetPath())
        self.on_setup_changed(None)
        self.session.update(logs=self.logs.GetValue().splitlines())
        if self.viewer:
            self.session.update(
                viewer={
                    **self.session.state.get("viewer", {}),
                    "camera": dict(self.viewer.camera),
                }
            )
        self.after_save = continuation

        def save(session, cancel, emit):
            """@brief Saves setup or unfinished work on a background worker.
            @param session Current isolated session.
            @param cancel Cancellation event.
            @param emit Progress callback.
            @return Saved archive path.
            @details Source bytes are acquired before the first setup save.
            """
            selected = session.state["setup"].get("source_path")
            if selected:
                session.acquire(Path(selected))
            session.save(destination, checkpoint=True)
            session.dirty = False
            emit("Session saved")
            return str(destination)

        self.actions.start(self.session, "save", save)
        self.set_running(True)
        return True

    def on_save_session(self, _event):
        """@brief Saves the current setup or unfinished engineering session.
        @param _event wx button event.
        @return None.
        @details No processing or approval is initiated by saving.
        """
        self.choose_save()

    def transition(self, continuation):
        """@brief Applies the Save, Discard, Cancel unsaved-work policy.
        @param continuation Transition to perform after the chosen policy.
        @return None.
        @details Save must finish successfully before replacement or close.
        """
        if self.job.active or self.actions.active:
            return
        self.capture_viewer()
        if not self.session.dirty:
            continuation()
            return
        with wx.GenericMessageDialog(
            self,
            "Save changes to the current session?",
            "Unsaved work",
            wx.YES_NO | wx.CANCEL,
        ) as dialog:
            dialog.SetYesNoCancelLabels("Save", "Discard", "Cancel")
            choice = dialog.ShowModal()
        if choice == wx.ID_YES:
            self.choose_save(continuation)
        elif choice == wx.ID_NO:
            continuation()

    def capture_viewer(self):
        """@brief Retains changed display state before unsaved-work choices.
        @return None.
        @details Identical camera state does not dirty a saved session again.
        """
        if self.viewer:
            from partsmith.ir.canonical import canonical_json

            saved = self.session.state.get("viewer", {})
            camera = dict(self.viewer.camera)
            if canonical_json(saved.get("camera")) != canonical_json(camera):
                self.session.update(viewer={**saved, "camera": camera})

    def replace_session(self, session):
        """@brief Displays an already validated fresh operational session.
        @param session Loaded or newly created isolated session.
        @return None.
        @details Loading never runs providers, generation, or approvals.
        """
        if self.viewer:
            self.pending_session = session
            self.set_running(True)
            self.viewer.Close()
            return
        self.session = session
        self.log_budget_exceeded = False
        setup = session.state.get("setup", {})
        self.source.ChangeValue(setup.get("source_path", ""))
        self.part.ChangeValue(setup.get("part_number", ""))
        self.part.Enable(
            not self.running and "component_id" not in session.state
        )
        self.part.SetToolTip(
            "Use New / Clear Component to process another ordering number"
            if "component_id" in session.state
            else "Full manufacturer part number, including package suffixes"
        )
        self.ai_enabled.SetValue(setup.get("use_ai", False))
        self.pages.ChangeValue(setup.get("pages", "All Pages"))
        self.dpi.SetValue(int(setup.get("dpi", 200)))
        self.ocr_force.SetValue(setup.get("force_ocr", False))
        self.ocr_languages.ChangeValue(
            ",".join(setup.get("ocr_languages", ["eng", "deu", "chi_sim"]))
        )
        self.ai_candidates = session.state.get("ai")
        self.logs.ChangeValue("\n".join(session.state.get("logs", [])))
        self.status.SetLabel(session.state.get("status", "setup").capitalize())
        self.review.refresh_session()
        self.refresh_viewer()

    def refresh_viewer(self):
        """@brief Updates eligibility for the current actual artifact pair.
        @return None.
        @details Failed validation does not block inspection of parseable data.
        """
        from .placement_viewer import session_scene

        try:
            session_scene(self.session)
            ready = True
        except (ValueError, OSError, KeyError):
            ready = False
        self.viewer_button.Enable(ready and not self.closing)
        if self.viewer and not self.viewer.closing:
            self.viewer.mark_current(self.session)

    def on_viewer(self, _event):
        """@brief Opens or foregrounds the active session's modeless viewer.
        @param _event wx button event.
        @return None.
        @details Main inspection, logs and exact asset bindings remain
        available.
        """
        if self.viewer:
            if not self.viewer.closing:
                self.viewer.Show()
                self.viewer.Raise()
            return
        try:
            from .placement_viewer import PlacementFrame, session_scene

            source, binding = session_scene(self.session)
            instance = self.session.instance_id
            self.viewer = PlacementFrame(
                self,
                source=source,
                binding=binding,
                camera=self.session.state.get("viewer", {}).get("camera"),
                log=self.append_log,
                on_closed=lambda camera: self.on_viewer_closed(
                    instance, camera
                ),
            )
            self.viewer.Show()
        except Exception as error:
            self.append_log(f"[placement viewer] {error}")

    def on_viewer_closed(self, instance, camera):
        """@brief Retains display state after the owned viewer releases
        workers.
        @param instance Originating operational session identity.
        @param camera Display-only camera snapshot.
        @return None.
        @details Superseded callbacks cannot rewrite a loaded session.
        """
        self.viewer = None
        if self.actions.active or self.job.active:
            self.pending_viewer_camera = (instance, camera)
            return
        if (
            instance == self.session.instance_id
            and not self.closing
            and self.pending_session is None
        ):
            self.session.update(
                viewer={
                    **self.session.state.get("viewer", {}),
                    "camera": camera,
                }
            )
        if self.pending_session is not None:
            session, self.pending_session = self.pending_session, None
            self.replace_session(session)
            self.set_running(False)

    def send_ai(self, request):
        """@brief Runs a deliberately selected AI request in a worker.
        @param request Exact validated request shown in the disclosure preview.
        @return None.
        @details Local evidence remains available after provider failure.
        """
        if not self.ai_enabled.GetValue():
            raise ValueError(
                "Enable the OpenAI disclosure checkbox before sending"
            )
        if self.job.active or self.actions.active:
            raise ValueError("Another session action is running")
        key = self.store.read_for_processing()
        self.redact = self.session.redact = Redactor((key,))

        def interpret(session, cancel, emit):
            """@brief Retains an unreviewed result for the exact AI request.
            @param session Working session with retained local evidence.
            @param cancel Cooperative cancellation event.
            @param emit Redacted service progress callback.
            @return Unreviewed provider candidate bundle.
            @details The immutable request contains no credential fields.
            """
            from partsmith.ai import OpenAIProvider, candidate_evidence

            provider = OpenAIProvider(lambda: key, cancel=cancel, log=emit)
            bundle = candidate_evidence(request, provider.analyze(request))
            history = list(session.state.get("history", []))
            history.append(
                {
                    "kind": "AI_REQUEST",
                    "sha256": request.input_hash,
                    "request": session.put(request._snapshot),
                }
            )
            session.update(ai=bundle, history=history, status="ai-unreviewed")
            return bundle

        self.actions.start(self.session, "AI interpretation", interpret)
        self.set_running(True)

    def load_path(self, path):
        """@brief Starts fully staged archive validation on a worker.
        @param path User-selected archive or offered recovery checkpoint.
        @return None.
        @details Failed loads leave the existing working session intact.
        """
        self.actions.start(
            self.session,
            "load",
            lambda session, cancel, emit: Session.load(
                path, root=session.storage
            ),
        )
        self.set_running(True)

    def on_load_session(self, _event):
        """@brief Applies unsaved policy before opening the archive chooser.
        @param _event wx load button event.
        @return None.
        @details Cancel preserves current work before any replacement chooser.
        """
        self.transition(self.choose_load_session)

    def choose_load_session(self):
        """@brief Chooses an archive then applies unsaved-work policy.
        @return None.
        @details Cancelling either chooser preserves the current session.
        """
        if self.job.active or self.actions.active:
            return
        with wx.FileDialog(
            self,
            "Load PartSmith Session",
            wildcard="PartSmith session (*.partsmith)|*.partsmith",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        self.load_path(path)

    def on_clear_session(self, _event):
        """@brief Creates a fresh component session after unsaved policy.
        @param _event wx button event.
        @return None.
        @details Previously saved historical identities are never rewound.
        """
        self.transition(
            lambda: self.replace_session(Session(self.session.storage))
        )

    def offer_recovery(self):
        """@brief Offers last good recovery data without automatic actions.
        @return None.
        @details A declined checkpoint leaves setup ready for new work.
        """
        path = self.session.storage / "recovery.partsmith"
        if path.exists():
            with wx.GenericMessageDialog(
                self,
                "Recover the last unfinished session?",
                "Session recovery",
                wx.YES_NO,
            ) as dialog:
                if dialog.ShowModal() == wx.ID_YES:
                    self.load_path(path)

    def on_budgets(self, _event):
        """@brief Edits the recorded session resource budgets.
        @param _event wx button event.
        @return None.
        @details Rejects invalid or excessive limits without changing state.
        """
        from partsmith.ir.canonical import canonical_json, parse_json

        with wx.TextEntryDialog(
            self,
            "Byte budgets and object-count limit (JSON)",
            "Resource Limits",
            canonical_json(self.session.state["budgets"]).decode(),
            style=wx.OK | wx.CANCEL | wx.TE_MULTILINE,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                try:
                    self.session.update(budgets=parse_json(dialog.GetValue()))
                    self.checkpoint_due = monotonic() + 0.75
                    self.log_budget_exceeded = False
                except Exception as error:
                    self.append_log(f"[resource limits] {error}")

    def refresh_credentials(self):
        """@brief Displays secure-store availability.
        @return None.
        @details Only configuration state is displayed, never the secret value.
        """
        try:
            configured = self.store.configured()
        except CredentialError:
            state = "secure store unavailable"
        else:
            state = "configured" if configured else "not configured"
        self.key_status.SetLabel(f"{self.store.provider}: {state}")

    def set_running(self, running):
        """@brief Updates controls for the processing busy state.
        @param running Whether processing is active.
        @return None.
        @details Disables mutable setup controls while retaining cancellation.
        """
        if running == self.running:
            return
        self.running = running
        self.review.integration.enable_controls(running)
        for control in (
            self.start,
            self.key_button,
            self.file_button,
            self.part,
            self.ai_enabled,
            self.save_button,
            self.load_button,
            self.clear_button,
            self.pages,
            self.dpi,
            self.ocr_force,
            self.ocr_languages,
            self.review.send,
            self.budget_button,
        ):
            control.Enable(not running)
        self.part.Enable(
            not running and "component_id" not in self.session.state
        )
        self.part.SetToolTip(
            "Use New / Clear Component to process another ordering number"
            if "component_id" in self.session.state
            else "Full manufacturer part number, including package suffixes"
        )
        self.cancel.Enable(running)
        for control in (
            self.review.release.approve,
            self.review.release.reject,
            self.review.release.reason,
        ):
            if running:
                control.Disable()
        if not running:
            self.review.release.refresh_session()
        if self.viewer and getattr(self.viewer, "editor", None):
            for controls in self.viewer.editor.entries.values():
                for control in controls:
                    if control not in self.viewer.editor.entries["scale"]:
                        control.Enable(not running)
            for control in [
                *self.viewer.editor.buttons,
                *self.viewer.editor.mirrors.values(),
                self.viewer.editor.reason,
                self.viewer.editor.evidence,
            ]:
                control.Enable(not running)
            if self.viewer.editor.draft.revision_id != self.session.state.get(
                "revision_id"
            ):
                self.viewer.editor.buttons[-1].Disable()
        if running:
            self.review.artifacts.generate.Disable()
        else:
            self.review.artifacts.refresh_session()
        if running:
            for control in (
                self.review.component.assemble,
                self.review.component.evidence,
                self.review.component.propose,
                self.review.component.approve,
                self.review.component.reject,
                self.review.component.pdl,
                self.review.component.editor,
                self.review.component.reason,
            ):
                control.Disable()
        else:
            self.review.component.editor.Enable()
            self.review.component.reason.Enable()
            self.review.component.refresh_session()

    def append_log(self, message):
        """@brief Appends one credential-redacted progress message.
        @param message Progress message to redact.
        @return None.
        @details Called on the wx thread; the shared log remains read-only.
        """
        text = self.redact(message) + "\n"
        budget = self.session.state["budgets"]["log_bytes"]
        if (
            len(self.logs.GetValue().encode()) + len(text.encode())
            > budget - 1024
        ):
            if not self.log_budget_exceeded:
                self.logs.AppendText(
                    "[LOG_BUDGET] Capture stopped at the configured "
                    "limit; active work cancellation requested.\n"
                )
                self.log_budget_exceeded = True
                self.job.cancel()
                self.actions.cancel.set()
            return
        self.logs.AppendText(text)

    def on_prototype(self, _event):
        """@brief Opens or foregrounds the known-fixture rendering experiment.
        @param _event wx button event.
        @return None.
        @details The modeless window cannot use or mutate extracted sessions.
        """
        if self.closing:
            return
        if self.prototype:
            if not self.prototype.closing:
                self.prototype.Show()
                self.prototype.Raise()
            return
        try:
            from .viewer_prototype import PrototypeFrame

            self.prototype = PrototypeFrame(
                self,
                camera=self.prototype_camera,
                log=self.append_log,
                on_closed=self.on_prototype_closed,
            )
            self.prototype.Show()
        except Exception:
            self.append_log("12.1 prototype unavailable: VIEWER_INIT_ERROR")

    def on_prototype_closed(self, camera):
        """@brief Retains camera state after prototype resource cleanup.
        @param camera Display-only camera snapshot.
        @return None.
        @details Does not alter processing status, candidates or source data.
        """
        self.prototype_camera = camera
        self.prototype = None
        self.append_log(
            "12.1 prototype closed: workers and display resources released"
        )

    def on_key(self, _event):
        """@brief Opens a blank API-key configuration dialog.
        @param _event wx event; unused.
        @return None.
        @details Does not open the dialog during processing.
        """
        if self.job.active:
            return
        with KeyDialog(self, self.store) as dialog:
            dialog.ShowModal()
        self.refresh_credentials()

    def on_file(self, _event):
        """@brief Applies unsaved policy before selecting another component.
        @param _event wx source button event.
        @return None.
        @details Cancel preserves current work before the source chooser.
        """
        self.transition(self.choose_datasheet)

    def choose_datasheet(self):
        """@brief Selects a local datasheet path.
        @return None.
        @details Cancelled selection leaves the current path unchanged.
        """
        if self.job.active:
            return
        with wx.FileDialog(
            self,
            "Select PDF Datasheet",
            wildcard="PDF datasheets (*.pdf)|*.pdf",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                path = dialog.GetPath()

                def acquire():
                    """@brief Begins a new explicit source acquisition.
                    @return None.
                    @details Previous source bytes remain in the old session.
                    """
                    self.replace_session(Session())
                    self.source.ChangeValue(path)
                    self.on_setup_changed(None)

                acquire()

    def on_start(self, _event):
        """@brief Validates setup and starts cancellable processing.
        @param _event wx event; unused.
        @return None.
        @details A bound ordering number cannot be changed by re-extraction.
        New / Clear Component applies Save, Discard, Cancel before replacement.
        """
        if self.job.active or self.actions.active or self.starting:
            return
        self.starting = True
        request = ProcessingRequest(
            self.session.directory / "source.pdf"
            if "source" in self.session.state
            else Path(self.source.GetValue()),
            self.part.GetValue(),
            self.ai_enabled.GetValue(),
        )
        try:
            request.validate()
            if self.session.state.get("component_id"):
                ir = self.session.state["drafts"]["ir"]
                if request.part_number != ir["identity"]["mpn"]:
                    raise ValueError(
                        "Use New / Clear Component before changing the "
                        "required part number"
                    )
                self.session.verify_part_number(ir)
            self.on_setup_changed(None)
            try:
                key = self.store.read_for_processing()
            except CredentialError:
                if request.use_ai:
                    self.append_log(
                        "AI credential unavailable; local extraction "
                        "continues. Selected AI requests require a key."
                    )
                key = None
            self.redact = self.session.redact = Redactor((key,))
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
        """@brief Cancels this dialog or processing operation.
        @param _event wx event; unused.
        @return None.
        @details Requests cleanup without exporting a saved credential.
        """
        self.job.cancel()
        self.actions.cancel.set()
        self.cancel.Disable()
        self.status.SetLabel("Cancelling…")

    def poll(self, _event):
        """@brief Dispatches processing results and waits for safe teardown.
        @param _event wx event; unused.
        @return None.
        @details Host exit requests recovery and asynchronous owned cleanup.
        """
        if self.host_alive is not None and not self.host_exited:
            if not self.host_alive():
                self.close_for_host_exit()
                if not self or self.IsBeingDeleted():
                    return
        if self.starting:
            return
        for progress in self.actions.drain():
            if progress.instance != self.session.instance_id or (
                self.actions.binding is not None
                and (progress.action, progress.instance, progress.revision)
                != self.actions.binding
            ):
                continue
            self.append_log(
                f"[{progress.stage}/{progress.outcome}] {progress.detail}"
            )
            self.review.integration.progress(progress)
            if progress.outcome == "success":
                if progress.stage == "load":
                    self.replace_session(progress.payload)
                elif progress.stage == "save" and self.after_save:
                    continuation, self.after_save = self.after_save, None
                    wx.CallAfter(continuation)
                self.review.refresh_session()
                self.refresh_viewer()
                self.status.SetLabel(
                    self.session.state.get("status", "completed").capitalize()
                )
            elif progress.outcome in {"failed", "cancelled"}:
                self.after_save = None
                self.review.refresh_session()
                self.refresh_viewer()
            elif progress.payload is not None:
                self.review.artifacts.refresh_session()
                self.refresh_viewer()
        for kind, message in self.job.drain():
            if kind == "log":
                self.append_log(message)
            elif kind == "candidates":
                self.ai_candidates = message
                self.session.update(ai=message)
            else:
                self.status.SetLabel(message.capitalize())
                self.session.update(
                    status=message, logs=self.logs.GetValue().splitlines()
                )
                self.review.refresh_session()
                self.actions.start(
                    self.session,
                    "checkpoint",
                    lambda session, cancel, emit: None,
                )
        if not self.job.active and not self.actions.active:
            if self.pending_session is not None:
                return
            if self.pending_viewer_camera:
                instance, camera = self.pending_viewer_camera
                self.pending_viewer_camera = None
                self.on_viewer_closed(instance, camera)
            if self.close_requested:
                self.close_requested = False
                self.checkpoint_due = None
                wx.CallAfter(lambda: self.transition(self.close_saved))
                return
            if (
                self.checkpoint_due is not None
                and monotonic() >= self.checkpoint_due
            ):
                self.checkpoint_due = None
                self.actions.start(
                    self.session,
                    "checkpoint",
                    lambda session, cancel, emit: None,
                )
            if self.closing:
                if not self.prototype and not self.viewer:
                    self.timer.Stop()
                    self.Destroy()
            else:
                self.set_running(False)

    def close_for_host_exit(self):
        """@brief Closes with the launching editor without an unsaved prompt.
        @return None.
        @details Cancels workers, retains recovery and dismisses owned dialogs.
        """
        if self.host_exited:
            return
        self.host_exited = True
        self.closing = True
        self.close_requested = False
        self.after_save = None
        self.checkpoint_due = None
        if self.job.active or self.actions.active:
            self.on_cancel(None)
        elif self.session.dirty:
            self.actions.start(
                self.session, "checkpoint", lambda session, cancel, emit: None
            )
        for window in wx.GetTopLevelWindows():
            parent = window.GetParent()
            while parent is not None and parent is not self:
                parent = parent.GetParent()
            if (
                parent is self
                and isinstance(window, wx.Dialog)
                and window.IsModal()
            ):
                window.EndModal(wx.ID_CANCEL)
        self.Close()

    def on_close(self, event):
        """@brief Cancels owned work before destroying the main window.
        @param event wx event to propagate or veto.
        @return None.
        @details Waits for processing and viewer cleanup through timer events.
        """
        if not self.closing:
            if event.CanVeto():
                event.Veto()
            if self.job.active or self.actions.active:
                self.close_requested = True
                self.on_cancel(None)
            else:
                self.transition(self.close_saved)
            return
        if self.prototype:
            self.prototype.Close()
        if self.viewer:
            self.viewer.Close()
        if (
            self.job.active
            or self.actions.active
            or self.prototype
            or self.viewer
        ):
            self.closing = True
            if self.job.active or self.actions.active:
                self.on_cancel(None)
            if event.CanVeto():
                event.Veto()
                return
        self.timer.Stop()
        event.Skip()

    def close_saved(self):
        """@brief Closes after a completed Save or explicit Discard choice.
        @return None.
        @details The normal close handler still waits for viewer cleanup.
        """
        self.closing = True
        self.checkpoint_due = None
        self.Close()
