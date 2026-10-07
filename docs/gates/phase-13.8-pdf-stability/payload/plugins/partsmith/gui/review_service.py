"""@package partsmith.gui.review_service
@brief Adapts desktop review actions to existing immutable review services.
@details Every action opens a thread-owned connection and binds exact current
revision, inventory and proposal hashes to a freshly authenticated OS actor.
"""

import copy
from dataclasses import asdict
from uuid import uuid4

from partsmith.ir import ComponentIR
from partsmith.pdl import ir_pdl_issues, load_pdl
from partsmith.persistence import ImmutableStore, Repository
from partsmith.release.input_review import (
    NO_HEAD_HASH,
    ConflictResolutionProposalRequest,
    EvidenceExclusionProposalRequest,
    InputApprovalRequest,
    InputRejectionRequest,
    InputReviewProposal,
    InputReviewService,
    OverrideProposalRequest,
    PinRemovalProposalRequest,
    PinReorderProposalRequest,
)

from .assembly import assemble_root
from .identity import authenticated_principal


class DesktopReview:
    """@brief Owns exact desktop-to-review-service request construction.
    @details Saved actors are audit data and never the current principal.
    """

    def __init__(self, session, *, identity=authenticated_principal):
        """@brief Binds one isolated working session to the review adapter.
        @param session Current working session.
        @param identity Trusted OS authentication adapter or test adapter.
        @return None.
        @details Authentication is refreshed for every proposing/deciding
        action.
        """
        self.session = session
        self.identity = identity

    def assemble(self, values=None, assignments=()):
        """@brief Registers an unreviewed root and exact acquisition inventory.
        @param values Explicit engineering sections entered by the reviewer.
        @param assignments Explicit evidence-to-field interpretation
        assignments.
        @return Registered immutable root revision.
        @details No proposal can precede this root and inventory registration.
        """
        if self.session.state.get("component_id"):
            raise ValueError(
                "Initial assembly already exists; use typed review edits"
            )
        part = self.session.state["setup"]["part_number"]
        with self.session.connection() as connection:
            component = Repository(connection).create_component("", part, "")
            ir = assemble_root(self.session, component.id, values, assignments)
            inventory = {
                "source_hashes": [
                    item["sha256"] for item in ir.data["source"]["documents"]
                ],
                "evidence_ids": [item["id"] for item in ir.data["evidence"]],
            }
            store = ImmutableStore(connection)
            inventory_hash = store.put_inventory(inventory)
            result = store.put_revision(
                ir.data, inventory_sha256=inventory_hash, reviewed=False
            )
            self.session.update(
                _connection=connection,
                component_id=component.id,
                revision_id=result.revision_id,
                inventory_sha256=inventory_hash,
                drafts={**self.session.state.get("drafts", {}), "ir": ir.data},
                status="unreviewed-ir",
            )
        return result

    def snapshot(self):
        """@brief Returns the exact current immutable engineering revision.
        @return ComponentIR or None before assembly.
        @details Opens a short-lived connection in the inspecting thread.
        """
        revision = self.session.state.get("revision_id")
        if revision is None:
            return None
        with self.session.connection() as connection:
            return ComponentIR(
                ImmutableStore(connection).get_revision(revision)
            )

    def _base(self, connection):
        """@brief Resolves the exact current revision and mutable-head binding.
        @param connection Worker-owned SQLite connection.
        @return Revision document, expected head hash and inventory digest.
        @details An unreviewed root may only enter evidence review first.
        """
        data = ImmutableStore(connection).get_revision(
            self.session.state["revision_id"]
        )
        ir = ComponentIR(data)
        head = connection.execute(
            "SELECT revision_hash FROM component_heads WHERE component_id=?",
            (self.session.state["component_id"],),
        ).fetchone()
        return (
            ir,
            head[0] if head else NO_HEAD_HASH,
            self.session.state["inventory_sha256"],
        )

    def _retain_proposal(
        self, result, expected, inventory, reason, connection=None
    ):
        """@brief Retains a pending exact-base proposal for explicit decisions.
        @param result Immutable service proposal result.
        @param expected Expected current head hash.
        @param inventory Matching acquisition inventory digest.
        @param reason Explicit proposal reason.
        @param connection Optional existing atomic review transaction.
        @return Original result.
        @details A pending proposal never advances the reviewed head.
        """
        self.session.update(
            _connection=connection,
            proposal={
                **asdict(result),
                "expected_head_hash": expected,
                "inventory_sha256": inventory,
                "reason": reason,
            },
            status="input-proposal-pending",
        )
        return result

    def propose_evidence(self, reason):
        """@brief Proposes evidence review without engineering changes.
        @param reason Explicit source-inventory review reason.
        @return Pending immutable proposal result.
        @details Root and inventory already exist before the service call.
        """
        self.identity()
        with self.session.connection() as connection:
            ir, expected, inventory = self._base(connection)
            candidate = copy.deepcopy(ir.data)
            candidate["revision"].update(
                id=str(uuid4()),
                parent_id=ir.data["revision"]["id"],
                description=reason,
                evidence_review=None,
            )
            request = InputReviewProposal(
                self.session.state["component_id"],
                ir.data["revision"]["id"],
                ir.sha256,
                expected,
                candidate["revision"]["id"],
                ComponentIR(candidate).sha256,
                inventory,
                reason,
            )
            result = InputReviewService(connection).propose(request, candidate)
            return self._retain_proposal(
                result, expected, inventory, reason, connection
            )

    def propose(self, kind, fields, reason):
        """@brief Creates a typed exact-base engineering or provenance
        proposal.
        @param kind Override, reorder, exclusion or conflict resolution action.
        @param fields Closed action-specific typed fields.
        @param reason Explicit engineering review reason.
        @return Immutable pending proposal result.
        @details Trusted path typing and historical bindings remain
        service-owned.
        """
        principal = self.identity()
        with self.session.connection() as connection:
            ir, expected, inventory = self._base(connection)
            base = {
                "component_id": self.session.state["component_id"],
                "base_revision_id": ir.data["revision"]["id"],
                "base_revision_hash": ir.sha256,
                "expected_head_hash": expected,
                "reason": reason,
            }
            service = InputReviewService(connection)
            if kind == "override":
                result = service.propose_override(
                    OverrideProposalRequest(**base, **fields), principal
                )
            elif kind == "reorder":
                fields = {
                    **fields,
                    "terminal_order": tuple(fields["terminal_order"]),
                }
                result = service.propose_pin_reorder(
                    PinReorderProposalRequest(**base, **fields), principal
                )
            elif kind == "remove":
                fields = {
                    **fields,
                    "terminal_order": tuple(fields["terminal_order"]),
                }
                result = service.propose_pin_removal(
                    PinRemovalProposalRequest(**base, **fields), principal
                )
            elif kind == "exclude":
                fields = {
                    **fields,
                    "replacement_evidence_ids": tuple(
                        fields.get("replacement_evidence_ids", [])
                    ),
                }
                result = service.propose_evidence_exclusion(
                    EvidenceExclusionProposalRequest(**base, **fields),
                    principal,
                )
            elif kind == "resolve":
                fields = {
                    **fields,
                    "selected_evidence_ids": tuple(
                        fields["selected_evidence_ids"]
                    ),
                    "superseded_evidence_ids": tuple(
                        fields["superseded_evidence_ids"]
                    ),
                }
                result = service.propose_resolution(
                    ConflictResolutionProposalRequest(**base, **fields),
                    principal,
                )
            else:
                raise ValueError("Unsupported typed desktop review operation")
            return self._retain_proposal(
                result, expected, inventory, reason, connection
            )

    def decide_inputs(self, approve, reason):
        """@brief Explicitly approves or rejects one exact pending input
        proposal.
        @param approve Whether to approve the pending input proposal.
        @param reason Required decision rationale.
        @return Immutable review decision result.
        @details Atomic commits are non-cancellable; inputs never approve
        release.
        """
        principal = self.identity()
        proposal = self.session.state.get("proposal")
        if proposal is None:
            raise ValueError("No pending input proposal")
        fields = {
            key: proposal[key]
            for key in (
                "proposal_id",
                "proposal_hash",
                "candidate_revision_id",
                "candidate_revision_hash",
                "expected_head_hash",
            )
        }
        fields.update(
            component_id=self.session.state["component_id"],
            reviewer=principal.subject,
            reason=reason,
        )
        with self.session.connection() as connection:
            service = InputReviewService(connection)
            if approve:
                result = service.approve_inputs(
                    InputApprovalRequest(
                        **fields, inventory_sha256=proposal["inventory_sha256"]
                    ),
                    principal,
                )
                ir = ImmutableStore(connection).get_revision(
                    result.revision_id
                )
            else:
                result = service.reject_inputs(
                    InputRejectionRequest(**fields), principal
                )
                ir = None
            history = list(self.session.state.get("history", []))
            history.append(
                {
                    "kind": "INPUT_APPROVE" if approve else "INPUT_REJECT",
                    "result": asdict(result),
                    "actor": principal.subject,
                    "mechanism": principal.mechanism,
                    "reason": reason,
                }
            )
            changes = {
                "proposal": None,
                "history": history,
                "status": "inputs-reviewed" if approve else "input-rejected",
            }
            if approve:
                changes.update(
                    revision_id=result.revision_id,
                    drafts={**self.session.state.get("drafts", {}), "ir": ir},
                    release=None,
                )
            self.session.update(_connection=connection, **changes)
        return result

    def bind_pdl(self, pdl_id, revision, content_hash):
        """@brief Selects an exact explicit PDL rather than a package label.
        @param pdl_id Trusted local library entry identity.
        @param revision Exact immutable library revision.
        @param content_hash Expected PDL content digest.
        @return Selected PDL after family, variant and topology checks.
        @details Unsupported or incompatible strategies remain generation
        blockers.
        """
        pdl = load_pdl(pdl_id, revision)
        if pdl.data["content_sha256"] != content_hash:
            raise ValueError("PDL content hash differs from selected binding")
        ir = self.snapshot()
        if ir is None:
            raise ValueError("Assemble component data before PDL selection")
        issues = ir_pdl_issues(ir.data, pdl.data)
        if issues:
            raise ValueError(
                "PDL incompatible: "
                + "; ".join(issue.code for issue in issues)
            )
        self.session.update(
            pdl={"id": pdl_id, "revision": revision, "sha256": content_hash},
            release=None,
        )
        return pdl
