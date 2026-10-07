"""@file test_ipc_inspection.py
@brief Checks deliberate reads, safe failures and owned-session close behavior.
@details Injected session results remain explicitly labeled test evidence.
"""

import json
import pickle
from threading import Event, Thread

import pytest

from partsmith.integration.inspection import (
    InspectionController,
    InspectionState,
)
from partsmith.integration.ipc import (
    BoardInspection,
    FootprintInspection,
    IpcCapabilities,
    IpcError,
    IpcFailureReason,
    IpcSession,
)


def _board(reference="R1"):
    """@brief Supplies a safely labeled immutable inspection test result.
    @param reference Footprint reference for the selected deliberate read.
    @return BoardInspection with explicit injected-test origin.
    @details This result cannot constitute live native-operation evidence.
    """
    capabilities = IpcCapabilities(
        schema_version="partsmith-ipc-capabilities-1.0",
        adapter_version="1.0",
        serializer_version="1.0",
        coordinate_adapter="kicad-pcb-units-1.0",
        kicad_version="10.0.6",
        binding_version="0.8.0",
        binding_api_version="10.0.6",
        binding_api_build="10.0.6-0-gcaf7377e9c",
        native_distance_unit="nm",
        engineering_distance_unit="mm",
        angle_unit="degree",
        native_frame="native-board-origin-x-right-y-down",
        engineering_frame="native-board-origin-x-right-y-up",
        engineering_convention_version="1.1",
        board_path="C:/owned/board.kicad_pcb",
        project_path="C:/owned",
        project_name="board",
        operations=("version", "open-pcb-documents", "footprint-inspection"),
        evidence_origin="injected-test",
    )
    return BoardInspection(
        capabilities,
        (
            FootprintInspection(
                "test-item", reference, "1.25", "-2", "90", "F"
            ),
        ),
    )


class _Session(IpcSession):
    """@brief Supplies controller tests with an explicitly injected session.
    @details No transport, token or endpoint exists in this test subclass.
    """

    def __init__(self, results):
        """@brief Retains declared read results without native connection.
        @param results Ordered safe results or injected failures.
        @return None.
        @details Counts expose unintended retries or cleanup omissions.
        """
        self.session_id = "11111111-1111-4111-8111-111111111111"
        self.results = iter(results)
        self.read_count = 0
        self.close_count = 0
        self._closed = False

    def read_board(self):
        """@brief Returns the next deliberately requested test result.
        @return Injected immutable BoardInspection.
        @details Declared failures are raised without a native transport.
        """
        self.read_count += 1
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        """@brief Records cleanup and invalidates this injected session.
        @return None.
        @details No external process or native mutation is invoked.
        """
        self.close_count += 1
        self._closed = True


def test_construction_and_snapshot_do_not_implicitly_read():
    """@brief Requires a deliberate refresh for the first inspection.
    @return None.
    @details Observing controller state grants no native read or permission.
    """
    session = _Session([_board()])
    controller = InspectionController(session)
    assert controller.snapshot.state == InspectionState.INITIAL
    assert controller.snapshot.inspection is None
    assert controller.can_refresh
    assert session.read_count == 0


def test_refresh_reads_current_components_and_reports_safe_independent_data():
    """@brief Refreshes the same session and exposes the current actual read.
    @return None.
    @details Callback mutation cannot alter retained immutable data.
    """
    reports = []
    session = _Session([_board("R1"), _board("R2")])
    controller = InspectionController(session, report_callback=reports.append)
    first = controller.refresh()
    second = controller.refresh()
    assert first.inspection.footprints[0].reference == "R1"
    assert second.inspection.footprints[0].reference == "R2"
    assert second.sequence == session.read_count == 2
    assert second.state == InspectionState.READY
    assert (
        second.as_dict()["inspection"]["capabilities"]["evidence_origin"]
        == "injected-test"
    )
    reports[-1]["inspection"]["footprints"][0]["reference"] = "tampered"
    assert controller.snapshot.inspection.footprints[0].reference == "R2"
    assert controller.diagnostic_warning is None


@pytest.mark.parametrize("reason", list(IpcFailureReason))
def test_closed_failure_reasons_clear_rows_and_prevent_reconnect(reason):
    """@brief Preserves each safe IPC failure instead of retrying implicitly.
    @param reason Closed operational adapter failure.
    @return None.
    @details A previous successful result is removed from the active outcome.
    """
    session = _Session([_board(), IpcError(reason), _board("forbidden-retry")])
    controller = InspectionController(session)
    controller.refresh()
    failed = controller.refresh()
    assert failed.state == InspectionState.FAILED
    assert failed.reason == reason
    assert failed.code == IpcError(reason).code.value
    assert failed.inspection is None
    assert not controller.can_refresh
    assert session.close_count == 1
    assert controller.refresh() is failed
    assert session.read_count == 2


def test_untrusted_failure_text_never_enters_reports_or_representations():
    """@brief Converts unexpected failures into value-free diagnostics.
    @return None.
    @details Provider strings cannot escape this safe boundary.
    """
    private = "ipc://private-endpoint secret-native-token"
    reports = []
    session = _Session([RuntimeError(private)])
    controller = InspectionController(session, report_callback=reports.append)
    failed = controller.refresh()
    assert failed.reason == IpcFailureReason.DISCONNECTED
    assert private not in json.dumps(reports) + repr(controller) + repr(failed)
    assert session.close_count == 1


def _failing_writer(_report):
    """@brief Injects diagnostic persistence failure with unsafe external text.
    @param _report Safe operational dictionary, unused.
    @return Never returns.
    @details The exception text must not appear in retained inspection state.
    """
    raise OSError("secret-native-token private-endpoint")


def test_diagnostic_failure_preserves_success_and_connected_session():
    """@brief Separates successful native reads from report persistence.
    @return None.
    @details Failed diagnostics show a fixed warning without changing the read.
    """
    session = _Session([_board()])
    controller = InspectionController(session, report_callback=_failing_writer)
    outcome = controller.refresh()
    assert outcome.state == InspectionState.READY
    assert outcome.inspection == _board()
    assert controller.diagnostic_warning == "DIAGNOSTIC_WRITE_FAILED"
    assert session.connected
    assert session.close_count == 0
    assert "secret-native-token" not in json.dumps(outcome.as_dict())


def test_close_clears_data_and_is_idempotent():
    """@brief Invalidates the owned session when either UI owner closes.
    @return None.
    @details Repeated close/refresh cannot reconnect or duplicate cleanup.
    """
    reports = []
    session = _Session([_board()])
    controller = InspectionController(session, report_callback=reports.append)
    controller.refresh()
    controller.close()
    controller.close()
    assert controller.snapshot.state == InspectionState.CLOSED
    assert controller.snapshot.reason == IpcFailureReason.CLOSED
    assert controller.snapshot.inspection is None
    assert controller.snapshot.sequence == 2
    assert session.close_count == 1
    assert controller.refresh() is controller.snapshot
    assert session.read_count == 1
    assert reports[-1]["state"] == "CLOSED"


class _PendingSession(_Session):
    """@brief Delays a test read to exercise controller close during work.
    @details Test synchronization has a bounded wait and no native subprocess.
    """

    def __init__(self):
        """@brief Prepares explicit bounded read/close synchronization.
        @return None.
        @details Signals allow the test to close before read delivery.
        """
        super().__init__([_board()])
        self.started = Event()
        self.release = Event()

    def read_board(self):
        """@brief Waits for a bounded release before returning test content.
        @return Injected immutable BoardInspection.
        @details This fixture returns after its session was closed.
        """
        self.started.set()
        assert self.release.wait(2)
        return super().read_board()


def test_close_during_pending_read_discards_late_result_and_report():
    """@brief Prevents a completed worker from reviving a closed inspector.
    @return None.
    @details Close returns before the pending read is released by the fixture.
    """
    reports = []
    session = _PendingSession()
    controller = InspectionController(session, report_callback=reports.append)
    worker = Thread(target=controller.refresh)
    worker.start()
    assert session.started.wait(2)
    controller.close()
    assert not session.connected
    session.release.set()
    worker.join(2)
    assert not worker.is_alive()
    assert controller.snapshot.state == InspectionState.CLOSED
    assert controller.snapshot.inspection is None
    assert reports == [controller.snapshot.as_dict()]


def test_controller_refuses_serialization_of_live_session():
    """@brief Excludes a live controller from archives and saved-session data.
    @return None.
    @details The fixed exception represents neither credentials nor document.
    """
    controller = InspectionController(_Session([_board()]))
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(controller)


def test_invalid_callback_fails_without_a_native_read():
    """@brief Rejects unsupported diagnostic callbacks before session use.
    @return None.
    @details Failure never invokes or reconnects to the session.
    """
    session = _Session([_board()])
    with pytest.raises(ValueError, match="Invalid inspection report callback"):
        InspectionController(session, report_callback="invalid")
    assert session.read_count == 0


class _WindowDouble:
    """@brief Models window ownership without creating a native GUI surface.
    @details Real wx event handlers operate against this minimal state fixture.
    """

    def __init__(self, controller):
        """@brief Initializes safe close/delivery observation.
        @param controller Injected session-owning inspection controller.
        @return None.
        @details The parent is a Python identity sentinel, with no wx wrapper.
        """
        self._controller = controller
        self._closed = False
        self._pending = True
        self._parent = object()
        self.destroyed = False
        self.delivered = []

    def Destroy(self):
        """@brief Records deliberate child-window destruction.
        @return None.
        @details Creates or destroys no real GUI window.
        """
        self.destroyed = True

    def _display(self, outcome):
        """@brief Records a UI delivery without native controls.
        @param outcome Safe completed controller outcome.
        @return None.
        @details Late deliveries must never reach this method after close.
        """
        self.delivered.append(outcome)


class _DestroyEvent:
    """@brief Models the identity and propagation of a destroy event.
    @details Descendant identities must not invalidate an unrelated owner.
    """

    def __init__(self, origin):
        """@brief Records the explicit event origin.
        @param origin Python identity representing the destroyed object.
        @return None.
        @details No native window or event is allocated.
        """
        self.origin = origin
        self.skipped = False

    def GetEventObject(self):
        """@brief Returns the identity of the destroyed event origin.
        @return Fixture object identity.
        @details Access never invokes a destroyed wx wrapper.
        """
        return self.origin

    def Skip(self):
        """@brief Records normal event propagation.
        @return None.
        @details The event handler must not swallow unrelated destroy events.
        """
        self.skipped = True


def test_inspector_close_closes_session_and_discards_ui_delivery():
    """@brief Checks real wx close/delivery handlers without opening a window.
    @return None.
    @details Late asynchronous results cannot use destroyed native controls.
    """
    from partsmith.integration.inspection_wx import InspectionFrame

    session = _Session([_board()])
    controller = InspectionController(session)
    outcome = controller.refresh()
    window = _WindowDouble(controller)
    InspectionFrame._on_close(window, None)
    InspectionFrame._complete(window, outcome)
    assert window.destroyed and window._closed
    assert window.delivered == []
    assert session.close_count == 1


def test_parent_destroy_closes_session_without_accessing_deleted_wrappers():
    """@brief Checks parent destruction and repeated cleanup safely.
    @return None.
    @details Stored identity avoids GetParent on an already destroyed child.
    """
    from partsmith.integration.inspection_wx import InspectionFrame

    session = _Session([])
    controller = InspectionController(session)
    window = _WindowDouble(controller)
    child_event = _DestroyEvent(object())
    InspectionFrame._on_parent_destroy(window, child_event)
    assert child_event.skipped and session.close_count == 0
    parent_event = _DestroyEvent(window._parent)
    InspectionFrame._on_parent_destroy(window, parent_event)
    InspectionFrame._on_parent_destroy(window, parent_event)
    assert parent_event.skipped and window._closed
    assert session.close_count == 1


def test_direct_inspector_destroy_ignores_control_descendants():
    """@brief Closes only for destruction of the inspector itself.
    @return None.
    @details Destroying a control cannot invalidate the native session.
    """
    from partsmith.integration.inspection_wx import InspectionFrame

    session = _Session([])
    controller = InspectionController(session)
    window = _WindowDouble(controller)
    child_event = _DestroyEvent(object())
    InspectionFrame._on_destroy(window, child_event)
    assert child_event.skipped and session.close_count == 0
    frame_event = _DestroyEvent(window)
    InspectionFrame._on_destroy(window, frame_event)
    assert frame_event.skipped and window._closed
    assert session.close_count == 1
