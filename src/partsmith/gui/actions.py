"""@package partsmith.gui.actions
@brief Serializes desktop service actions outside the wx event thread.
@details Events bind operational instances and revisions; committed actions
retain their actual outcome even if cancellation arrives after the commit.
"""

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread
from uuid import uuid4


@dataclass(frozen=True)
class Progress:
    """@brief Carries one immutable action progress snapshot.
    @details Engineering state is owned by services rather than this event.
    """

    action: str
    instance: str
    revision: str | None
    stage: str
    outcome: str
    detail: str = ""
    code: str | None = None
    build_id: str | None = None
    payload: object = None


class ActionController:
    """@brief Supervises one session action at a time.
    @details A worker owns all database connections and snapshots state only
    at consistent boundaries; callbacks are queued for the wx thread.
    """

    def __init__(self):
        """@brief Initializes an idle action controller.
        @return None.
        @details Cancellation is cooperative at service-defined boundaries.
        """
        self.thread = None
        self.cancel = Event()
        self.events = Queue()
        self.binding = None

    @property
    def active(self):
        """@brief Reports whether an owned worker remains active.
        @return Boolean active state.
        @details Finished workers are reaped by drain on the wx thread.
        """
        return self.thread is not None

    def start(self, session, stage, operation):
        """@brief Starts one serialized background service operation.
        @param session Current isolated working session.
        @param stage Human-readable operation name.
        @param operation Callable accepting session, cancellation and emit.
        @return None.
        @details Refuses concurrent actions and retains failure checkpoints.
        """
        if self.active or session.busy:
            raise ValueError("A session action is already running")
        action = str(uuid4())
        instance = session.instance_id
        revision = session.state.get("revision_id")
        self.binding = (action, instance, revision)
        logs = list(session.state.get("logs", []))
        self.cancel.clear()
        session.busy = True

        def emit(
            detail,
            *,
            stage=stage,
            outcome="progress",
            code=None,
            build_id=None,
            payload=None,
        ):
            """@brief Queues a redacted immutable service progress event.
            @param detail Message emitted by the service.
            @param stage Concrete pipeline stage name.
            @param outcome Operational event outcome.
            @param code Optional stable diagnostic code.
            @param build_id Optional persisted attempt identity.
            @param payload Immutable result snapshot for the GUI.
            @return None.
            @details Never touches a wx control from the worker thread.
            """
            redacted = session.redact(detail)
            logs.append(f"[{stage}/{outcome}] {redacted}")
            self.events.put(
                Progress(
                    action,
                    instance,
                    revision,
                    stage,
                    outcome,
                    redacted,
                    code,
                    build_id,
                    payload,
                )
            )

        def run():
            """@brief Executes the action and retains its actual result.
            @return None.
            @details Successful service results survive later log/checkpoint
            failures and cancellation. Recovery failures are separate warnings.
            """
            try:
                emit("Started")
                try:
                    result = operation(session, self.cancel, emit)
                except Exception as error:
                    emit(
                        str(error),
                        outcome="cancelled"
                        if self.cancel.is_set()
                        else "failed",
                        code=type(error).__name__,
                    )
                    try:
                        session.update(
                            status="cancelled"
                            if self.cancel.is_set()
                            else "failed",
                            logs=logs,
                        )
                        session.checkpoint()
                    except Exception:
                        emit(
                            "Last good checkpoint retained",
                            code="CHECKPOINT_ERROR",
                        )
                else:
                    if stage not in {"load", "save"}:
                        try:
                            session.update(logs=logs)
                        except Exception as error:
                            emit(
                                f"Action completed; log persistence failed: "
                                f"{error}",
                                outcome="warning",
                                code="LOG_PERSISTENCE_ERROR",
                            )
                    target = result if stage == "load" else session
                    try:
                        target.checkpoint()
                    except Exception as error:
                        warning = (
                            f"Recovery checkpoint failed: {error}. "
                            "Last good checkpoint retained; "
                            "committed work remains in the working session."
                        )
                        emit(
                            warning,
                            outcome="warning",
                            code="CHECKPOINT_ERROR",
                        )
                        try:
                            target.update(
                                logs=[
                                    *target.state.get("logs", []),
                                    target.redact(warning),
                                ]
                            )
                        except Exception:
                            emit(
                                "Recovery warning could not be persisted",
                                outcome="warning",
                                code="LOG_PERSISTENCE_ERROR",
                            )
                        if stage == "checkpoint":
                            emit(
                                "Recovery checkpoint was not written",
                                outcome="failed",
                                code="CHECKPOINT_ERROR",
                            )
                            return
                    emit("Completed", outcome="success", payload=result)
            finally:
                session.busy = False

        self.thread = Thread(target=run, name="PartSmith " + stage)
        try:
            self.thread.start()
        except BaseException:
            self.thread = None
            session.busy = False
            raise

    def drain(self):
        """@brief Reaps completed workers and collects pending events.
        @return List of immutable Progress records.
        @details Never blocks the wx event thread waiting for active work.
        """
        if self.thread is not None and not self.thread.is_alive():
            self.thread.join()
            self.thread = None
        events = []
        while True:
            try:
                events.append(self.events.get_nowait())
            except Empty:
                return events
