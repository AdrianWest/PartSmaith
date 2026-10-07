"""@package partsmith.integration.workflow
@brief Shares deliberate installation actions between desktop and headless use.
@details Authority lives outside archived component sessions. Draft restoration
never restores a principal, closed-editor assertion or publication permission.
"""

from contextlib import ExitStack, closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from partsmith.gui.identity import authenticated_principal
from partsmith.gui.session import user_root
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.planner import Planner, PlanningResult
from partsmith.integration.publication import Publisher
from partsmith.integration.quiescence import ClosedProject
from partsmith.integration.review import IntegrationReview
from partsmith.integration.sources import SourceCatalog
from partsmith.integration.staging import Stager, StageResult
from partsmith.integration.store import IntegrationStore
from partsmith.integration.target import OwnedTarget
from partsmith.persistence import connect, migrate

EXECUTION_TABLES = (
    "integration_targets",
    "integration_heads",
    "integration_attempts",
    "integration_events",
    "integration_decisions",
    "integration_publications",
)


def require_data_session(connection) -> None:
    """@brief Rejects installation execution records in a component session.
    @param connection Migrated component working database or archive copy.
    @return None.
    @details Immutable engineering approval data remains valid source data;
    imported target/decision/journal execution rows cannot become authority.
    """
    for table in EXECUTION_TABLES:
        if connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
            raise ValueError("Session contains installation execution records")


@dataclass(frozen=True)
class InstallationDraft:
    """@brief Holds a process-local proposed operation without live authority.
    @details Persisted references are inspection hints, not this live object.
    """

    planning: PlanningResult
    attempt_id: str | None = None
    staged: StageResult | None = None
    intent: str = "PUBLISH"
    rollback_origin: str | None = None

    def references(self) -> dict:
        """@brief Returns the closed data-only session extension.
        @return Versioned target and draft object references.
        @details Neither actors, paths, tokens nor writer assertions are saved.
        """
        return {
            "schema_version": "partsmith-session-integration-1.0",
            "project_id": self.planning.plan.data["target"]["project_id"],
            "drafts": [
                {
                    "attempt_id": self.attempt_id,
                    "plan_hash": self.planning.plan.sha256,
                    "manifest_hash": self.staged.manifest.sha256
                    if self.staged
                    else None,
                }
            ],
        }


class IntegrationWorkflow:
    """@brief Coordinates explicit source, target and installation actions.
    @details Each action owns thread-local connections. No component BuildState
    or source approval is changed by installation decisions or publication.
    """

    def __init__(
        self,
        sessions,
        *,
        directory=None,
        principal_provider=authenticated_principal,
    ):
        """@brief Selects sources and durable installation authority.
        @param sessions Current or validated loaded component sessions.
        @param directory Application-owned authority directory override.
        @param principal_provider Trusted live process authentication adapter.
        @return None.
        @details Test overrides must be application-owned ordinary directories.
        """
        self.sessions = tuple(sessions)
        self.directory = (
            Path(directory)
            if directory
            else (user_root().parent / "integration")
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "authority.sqlite"
        if any(
            s.database.absolute() == self.database.absolute()
            for s in self.sessions
        ):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        self.principal_provider = principal_provider
        with closing(connect(self.database)) as connection:
            migrate(connection)
            connection.commit()

    @contextmanager
    def services(self):
        """@brief Opens fresh authority and selected component connections.
        @return Authority connection and bounded fresh source catalog.
        @details Source connections cannot write installation authority. All
        connections close in the calling worker thread, even after failure.
        """
        with ExitStack() as stack:
            connection = stack.enter_context(closing(connect(self.database)))
            sources = []
            for session in self.sessions:
                stack.enter_context(session.lock)
                source = stack.enter_context(session.connection())
                require_data_session(source)
                sources.append(source)
            yield connection, SourceCatalog(tuple(sources))

    def targets(self) -> list[dict]:
        """@brief Lists explicitly registered application targets.
        @return Data-only logical IDs, scope and managed project paths.
        @details Listing never restores a writer assertion or publishes.
        """
        with closing(connect(self.database)) as connection:
            records = [
                dict(row)
                for row in connection.execute(
                    "SELECT project_id, library_id, scope, root "
                    "FROM integration_targets ORDER BY created_at LIMIT 10001"
                )
            ]
            if len(records) > 10000:
                raise IntegrationError(FailureCode.RESOURCE_LIMIT)
            return records

    def register(self, original: Path, workspace: Path, *, confirmed: bool):
        """@brief Deliberately registers a saved/closed project copy.
        @param original Explicit ordinary source project directory.
        @param workspace Absent destination for the managed project container.
        @param confirmed Fresh user saved/closed/exclusive-use confirmation.
        @return Registered logical target and stable managed project path.
        @details Original files stay unchanged. Editors are closed by the user.
        """
        target = {
            "project_id": str(uuid4()),
            "library_id": "bft-library",
            "scope": "project-local",
        }
        with self.services() as (connection, _):
            owned = OwnedTarget.create(
                connection,
                target,
                original,
                workspace,
                ClosedProject(target["project_id"], confirmed),
            )
            return target, str(owned.link)

    def plan(self, target: dict, builds: tuple[str, ...]) -> InstallationDraft:
        """@brief Produces a pure complete desired-source dry run.
        @param target Independently selected registered logical target.
        @param builds Explicit complete set of desired approved releases.
        @return In-memory draft without a saved attempt or decision.
        @details Rechecks current target and freshly resolves source approvals.
        """
        with self.services() as (connection, sources):
            owned = OwnedTarget(connection, target)
            planning = Planner(connection, sources).plan(
                owned.current(), target, builds
            )
            return InstallationDraft(planning)

    def rollback_plan(self, target: dict, origin: str | None):
        """@brief Creates a new deliberate draft for historical restoration.
        @param target Explicit registered target.
        @param origin Prior manifest or None for initial copied tables.
        @return Fresh rollback draft requiring staging and a new approval.
        @details Current mutable project bytes remain the rollback snapshot.
        """
        with self.services() as (connection, sources):
            owned = OwnedTarget(connection, target)
            planning = Publisher(
                connection, self.principal_provider, source_connection=sources
            ).rollback_plan(owned, origin)
            return InstallationDraft(
                planning, intent="ROLLBACK", rollback_origin=origin
            )

    def stage(self, draft: InstallationDraft) -> InstallationDraft:
        """@brief Persists one checked complete isolated generation.
        @param draft Fresh plan with no existing saved attempt.
        @return New staged draft with exact reports and attempt identity.
        @details Staging grants no approval and changes no project target.
        """
        if draft.attempt_id or draft.planning.no_op:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        with self.services() as (connection, sources):
            parent = self.directory / "staging"
            parent.mkdir(exist_ok=True)
            stager = Stager(connection, sources)
            staged = stager.stage(draft.planning, parent)
            attempt = IntegrationStore(connection).save_plan(
                draft.planning.plan, draft.planning.snapshot.document
            )
            stager.save(attempt, staged)
            connection.commit()
            return InstallationDraft(
                draft.planning,
                attempt,
                staged,
                draft.intent,
                draft.rollback_origin,
            )

    def inspect(self, draft: InstallationDraft) -> dict:
        """@brief Shows frozen bindings and current blocking reasons.
        @param draft Existing planned or staged draft.
        @return Detached read-only review information.
        @details Inspection stays available after context changes.
        """
        if draft.staged is None:
            return draft.planning.dry_run()
        with self.services() as (connection, sources):
            target = draft.planning.plan.data["target"]
            return IntegrationReview(
                connection, self.principal_provider, source_connection=sources
            ).inspect(
                draft.attempt_id,
                draft.staged,
                target=target,
                root=draft.planning.snapshot.root,
            )

    def authorize(self, draft: InstallationDraft, reason: str, *, cancel=None):
        """@brief Records a fresh exact installation approval.
        @param draft Existing checked proposed generation.
        @param reason Explicit user installation review reason.
        @param cancel Optional cooperative cancellation signal.
        @return Durable exact decision, separate from publication status.
        @details Input and component release approvals remain separate actions.
        """
        if draft.staged is None:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        with self.services() as (connection, sources):
            return IntegrationReview(
                connection, self.principal_provider, source_connection=sources
            ).decide(
                draft.attempt_id,
                draft.staged,
                "APPROVE",
                reason,
                target=draft.planning.plan.data["target"],
                root=draft.planning.snapshot.root,
                cancel=cancel,
            )

    def publish(
        self, draft: InstallationDraft, *, confirmed: bool, cancel=None
    ):
        """@brief Executes a deliberate checked publish, update or rollback.
        @param draft Exact checked and actually approved attempt.
        @param confirmed Fresh saved/closed/exclusive-use confirmation.
        @param cancel Optional cooperative cancellation signal.
        @return Actual committed/cancelled/recovery outcome.
        @details No saved session field can supply confirmation or a principal.
        """
        if draft.staged is None:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        with self.services() as (connection, sources):
            target = draft.planning.plan.data["target"]
            owned = OwnedTarget(connection, target)
            return Publisher(
                connection, self.principal_provider, source_connection=sources
            ).publish(
                draft.attempt_id,
                draft.staged,
                owned,
                ClosedProject(target["project_id"], confirmed),
                cancel=cancel,
                intent=draft.intent,
                rollback_origin=draft.rollback_origin,
            )

    def recover(self, target: dict, attempt: str, *, confirmed: bool):
        """@brief Reconciles an explicitly selected unfinished trusted attempt.
        @param target Registered logical target selected independently.
        @param attempt Actual pending attempt in the durable authority store.
        @param confirmed Fresh saved/closed/exclusive-use confirmation.
        @return Truthful old/new reconciliation outcome without switching.
        @details Requires current source approvals and fresh OS authentication.
        """
        with self.services() as (connection, sources):
            owned = OwnedTarget(connection, target)
            return Publisher(
                connection, self.principal_provider, source_connection=sources
            ).recover(
                attempt, owned, ClosedProject(target["project_id"], confirmed)
            )
