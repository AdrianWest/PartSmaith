"""@package partsmith.integration.inspection
@brief Controls deliberate read-only inspection of a bound IPC session.
@details No reconnect, native edit, planning or publication operation exists.
Failures invalidate the session; safe reports contain actual inspected data or
a closed failure code. Diagnostic persistence cannot reclassify a native read.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock

from .errors import FailureCode
from .ipc import BoardInspection, IpcError, IpcFailureReason, IpcSession


class InspectionState(StrEnum):
    """@brief Names the current operational read-only inspection state.
    @details States are separate from engineering and installation state.
    """

    INITIAL = "INITIAL"
    READY = "READY"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class InspectionOutcome:
    """@brief Retains one immutable safe inspection outcome.
    @details Only verified reads include a board result; failures clear it.
    """

    state: InspectionState
    code: str
    reason: IpcFailureReason | None
    sequence: int
    session_id: str
    inspection: BoardInspection | None

    def as_dict(self) -> dict:
        """@brief Produces safe operational data for display or diagnostics.
        @return Independent dictionary without endpoint, token or authority.
        @details Existing immutable IPC records preserve their evidence origin.
        """
        return {
            "schema_version": "partsmith-ipc-inspection-1.0",
            "state": self.state.value,
            "code": self.code,
            "reason": self.reason.value if self.reason else None,
            "sequence": self.sequence,
            "session_id": self.session_id,
            "inspection": (
                self.inspection.as_dict() if self.inspection else None
            ),
        }


class InspectionController:
    """@brief Owns an explicitly supplied IPC session and deliberate refreshes.
    @details Reads are serialized, while close immediately invalidates the
    underlying session. Late results cannot replace the closed outcome.
    The session contains credentials; this controller cannot be serialized.
    """

    def __init__(
        self,
        session: IpcSession,
        *,
        report_callback: Callable[[dict], None] | None = None,
    ):
        """@brief Wraps a verified session without performing an implicit read.
        @param session Already bound read-only IPC session owned by the caller.
        @param report_callback Optional writer of safe outcome data.
        @return None.
        @details Ownership transfers to this controller, including final close.
        """
        if report_callback is not None and not callable(report_callback):
            raise ValueError("Invalid inspection report callback")
        self._session = session
        self._report_callback = report_callback
        self._state_lock = Lock()
        self._read_lock = Lock()
        self._report_lock = Lock()
        self._diagnostic_warning = None
        self._outcome = InspectionOutcome(
            InspectionState.INITIAL,
            "NOT_INSPECTED",
            None,
            0,
            session.session_id,
            None,
        )

    def __repr__(self) -> str:
        """@brief Represents only the safe controller state.
        @return Fixed controller name with the operational state.
        @details Does not expose the underlying session or document scope.
        """
        return f"InspectionController(state={self.snapshot.state.value})"

    def __getstate__(self):
        """@brief Refuses persistence of a live inspection controller.
        @return Never returns.
        @details Raises a fixed error without representing the live session.
        """
        raise TypeError("Transient IPC inspection cannot be serialized")

    @property
    def snapshot(self) -> InspectionOutcome:
        """@brief Returns the latest immutable operational outcome.
        @return InspectionOutcome with verified content or a safe failure.
        @details Merely inspecting state never reads or reconnects to KiCad.
        """
        with self._state_lock:
            return self._outcome

    @property
    def can_refresh(self) -> bool:
        """@brief Reports whether a deliberate read can still be attempted.
        @return True only for the initial or successfully inspected session.
        @details Failed or closed sessions require a separate explicit launch.
        """
        return self.snapshot.state in (
            InspectionState.INITIAL,
            InspectionState.READY,
        )

    @property
    def diagnostic_warning(self) -> str | None:
        """@brief Reports diagnostic persistence independently of native reads.
        @return A fixed warning code or None.
        @details Writer exception text is never returned, logged or chained.
        """
        with self._state_lock:
            return self._diagnostic_warning

    def _notify(self, outcome: InspectionOutcome) -> None:
        """@brief Sends current safe data to the optional diagnostic writer.
        @param outcome Immutable completed operation to report.
        @return None.
        @details Serialized reporting prevents a late read overwriting close.
        Callback failure leaves the native outcome and session state unchanged.
        """
        if self._report_callback is None:
            return
        with self._report_lock:
            with self._state_lock:
                if self._outcome is not outcome:
                    return
            warning = None
            try:
                self._report_callback(outcome.as_dict())
            except Exception:
                warning = "DIAGNOSTIC_WRITE_FAILED"
            with self._state_lock:
                if self._outcome is outcome:
                    self._diagnostic_warning = warning

    def refresh(self) -> InspectionOutcome:
        """@brief Deliberately re-reads the verified native board context.
        @return Immutable actual read result or a closed safe failure.
        @details The adapter enforces worker deadlines and context checks.
        Failure closes the session and stays recorded without automatic retry.
        """
        with self._read_lock:
            if not self.can_refresh:
                return self.snapshot
            inspection = None
            state = InspectionState.READY
            code = "READY"
            reason = None
            try:
                inspection = self._session.read_board()
            except IpcError as error:
                state = InspectionState.FAILED
                code = error.code.value
                reason = error.reason
                self._session.close()
            except Exception:
                state = InspectionState.FAILED
                code = FailureCode.IPC_UNAVAILABLE.value
                reason = IpcFailureReason.DISCONNECTED
                self._session.close()
            with self._state_lock:
                if self._outcome.state == InspectionState.CLOSED:
                    return self._outcome
                outcome = InspectionOutcome(
                    state,
                    code,
                    reason,
                    self._outcome.sequence + 1,
                    self._outcome.session_id,
                    inspection,
                )
                self._outcome = outcome
            self._notify(outcome)
            return outcome

    def close(self) -> None:
        """@brief Immediately invalidates the owned session and clears content.
        @return None.
        @details Idempotent, with no reconnect or native mutation. Any pending
        adapter worker completes bounded cleanup; its late result is discarded.
        """
        with self._state_lock:
            if self._outcome.state == InspectionState.CLOSED:
                return
            self._session.close()
            outcome = InspectionOutcome(
                InspectionState.CLOSED,
                FailureCode.IPC_UNAVAILABLE.value,
                IpcFailureReason.CLOSED,
                self._outcome.sequence + 1,
                self._outcome.session_id,
                None,
            )
            self._outcome = outcome
        self._notify(outcome)
