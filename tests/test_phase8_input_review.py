"""@package tests.test_phase8_input_review
@brief Tests immutable Phase 8 evidence and inventory input review.
@details Covers review before artifacts, stale heads, authentication,
immutable proposals, rejection, and atomic rollback.
"""

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest

from partsmith.ir import ComponentIR, canonical_json
from partsmith.persistence import (
    ImmutableStore,
    Repository,
    StaleHeadError,
    database,
)
from partsmith.release import AuthenticatedPrincipal
from partsmith.release.input_review import (
    NO_HEAD_HASH,
    InputApprovalRequest,
    InputRejectionRequest,
    InputReviewProposal,
    InputReviewService,
)

ROOT = Path(__file__).resolve().parents[1]
IR_PATH = ROOT / "fixtures" / "ir" / "v1.2" / "valid" / "0402.json"


def _inventory(data: dict) -> dict:
    """@brief Builds the complete acquisition inventory for a revision.
    @param data Component IR mapping.
    @return Matching source hashes and evidence identities.
    @details Ordering follows the retained revision arrays.
    """
    return {
        "source_hashes": [
            document["sha256"] for document in data["source"]["documents"]
        ],
        "evidence_ids": [record["id"] for record in data["evidence"]],
    }


def _root_revision(component_id: str) -> dict:
    """@brief Loads an unreviewed root revision for one component.
    @param component_id Persisted component identity.
    @return Detached valid IR 1.2 root mapping.
    @details Existing synthetic approval metadata is removed for service tests.
    """
    data = json.loads(IR_PATH.read_text(encoding="utf-8"))
    data["identity"]["component_id"] = component_id
    data["revision"]["evidence_review"] = None
    return data


def _candidate(base: dict, revision_id: str = "candidate-1") -> dict:
    """@brief Creates an evidence-review-only child revision.
    @param base Exact base revision.
    @param revision_id New candidate revision identity.
    @return Detached unreviewed child mapping.
    @details Engineering content and decision history remain unchanged.
    """
    data = copy.deepcopy(base)
    data["revision"]["id"] = revision_id
    data["revision"]["parent_id"] = base["revision"]["id"]
    data["revision"]["description"] = "Pending evidence review"
    data["revision"]["evidence_review"] = None
    return data


def _proposal_fixture(connection):
    """@brief Persists one root, inventory, candidate, and proposal.
    @param connection Active migrated SQLite connection.
    @return Component, proposal request, and persisted proposal result.
    @details No build or generated artifact is created by this fixture.
    """
    component = Repository(connection).create_component(
        "Synthetic", "0402", "0402"
    )
    store = ImmutableStore(connection)
    root = _root_revision(component.id)
    inventory = _inventory(root)
    inventory_hash = store.put_inventory(inventory)
    stored_root = store.put_revision(
        root,
        inventory_sha256=inventory_hash,
        reviewed=False,
    )
    candidate = _candidate(root)
    candidate_hash = ComponentIR(candidate).sha256
    request = InputReviewProposal(
        component_id=component.id,
        base_revision_id=stored_root.revision_id,
        base_revision_hash=stored_root.canonical_sha256,
        expected_head_hash=NO_HEAD_HASH,
        candidate_revision_id=candidate["revision"]["id"],
        candidate_revision_hash=candidate_hash,
        inventory_sha256=inventory_hash,
        reason="Review retained source and evidence inventory",
    )
    result = InputReviewService(connection).propose(request, candidate)
    return component, request, result


def _approval_request(component, request, result) -> InputApprovalRequest:
    """@brief Builds an exact approval request for one proposal.
    @param component Persisted component record.
    @param request Original proposal request.
    @param result Persisted proposal result.
    @return Closed exact-hash input approval request.
    @details Reviewer identity is later checked against authentication.
    """
    return InputApprovalRequest(
        proposal_id=result.proposal_id,
        proposal_hash=result.proposal_hash,
        component_id=component.id,
        candidate_revision_id=result.candidate_revision_id,
        candidate_revision_hash=result.candidate_revision_hash,
        expected_head_hash=request.expected_head_hash,
        inventory_sha256=request.inventory_sha256,
        reviewer="reviewer-1",
        reason="Evidence inventory is complete and correct",
    )


def test_input_review_approves_before_any_artifact_exists(tmp_path):
    """@brief Verifies input approval is independent of generated artifacts.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Approval creates a reviewed child, event, and current head only.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        revision = InputReviewService(connection).approve_inputs(
            _approval_request(component, proposal, result),
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        head = connection.execute(
            "SELECT * FROM component_heads WHERE component_id = ?",
            (component.id,),
        ).fetchone()
        assert head["revision_id"] == revision.revision_id
        assert head["revision_hash"] == revision.revision_hash
        approved = ImmutableStore(connection).get_revision(
            revision.revision_id
        )
        review = approved["revision"]["evidence_review"]
        assert review["approval_state"] == "APPROVED"
        assert review["reviewer"] == "reviewer-1"
        assert approved["revision"]["parent_id"] == (
            result.candidate_revision_id
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM builds").fetchone()[0]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT status FROM review_proposals WHERE id = ?",
                (result.proposal_id,),
            ).fetchone()[0]
            == "PENDING"
        )


def test_stale_head_rejects_approval_without_partial_records(tmp_path):
    """@brief Verifies concurrent head advancement requires rereview.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details No approval event or reviewed proposal child survives failure.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        store = ImmutableStore(connection)
        candidate = store.get_revision(result.candidate_revision_id)
        inventory = store.get_inventory(proposal.inventory_sha256)
        competing = copy.deepcopy(candidate)
        competing["revision"]["id"] = "competing-reviewed"
        competing["revision"]["parent_id"] = result.candidate_revision_id
        competing["revision"]["evidence_review"] = {
            "inventory_sha256": proposal.inventory_sha256,
            "reviewed_evidence_ids": inventory["evidence_ids"],
            "reviewer": "reviewer-2",
            "timestamp": "2026-10-02T20:00:00Z",
            "approval_state": "APPROVED",
        }
        stored = store.put_revision(
            competing,
            inventory_sha256=proposal.inventory_sha256,
            reviewed=True,
        )
        store.compare_and_swap_head(component.id, stored.revision_id, None)
        before_count = connection.execute(
            "SELECT COUNT(*) FROM ir_revisions"
        ).fetchone()[0]
        with pytest.raises(StaleHeadError):
            InputReviewService(connection).approve_inputs(
                _approval_request(component, proposal, result),
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == before_count
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_events"
            ).fetchone()[0]
            == 0
        )


def test_rejection_retains_immutable_pending_proposal(tmp_path):
    """@brief Verifies rejection appends an event without editing proposal.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details A decided proposal cannot receive a second decision.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        row = connection.execute(
            "SELECT canonical_bytes FROM review_proposals WHERE id = ?",
            (result.proposal_id,),
        ).fetchone()
        original = bytes(row["canonical_bytes"])
        request = InputRejectionRequest(
            proposal_id=result.proposal_id,
            proposal_hash=result.proposal_hash,
            component_id=component.id,
            candidate_revision_id=result.candidate_revision_id,
            candidate_revision_hash=result.candidate_revision_hash,
            expected_head_hash=proposal.expected_head_hash,
            reviewer="reviewer-1",
            reason="Evidence needs reacquisition",
        )
        rejected = InputReviewService(connection).reject_inputs(
            request,
            AuthenticatedPrincipal("reviewer-1", "local-test"),
        )
        assert rejected.decision == "REJECT"
        persisted = connection.execute(
            "SELECT status, canonical_bytes FROM review_proposals "
            "WHERE id = ?",
            (result.proposal_id,),
        ).fetchone()
        assert persisted["status"] == "PENDING"
        assert bytes(persisted["canonical_bytes"]) == original
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM component_heads"
            ).fetchone()[0]
            == 0
        )
        with pytest.raises(ValueError, match="already has a decision"):
            InputReviewService(connection).reject_inputs(
                request,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )


def test_engineering_change_is_not_an_evidence_review_action(tmp_path):
    """@brief Verifies evidence review cannot smuggle engineering edits.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Invalid proposal writes roll back candidate and proposal records.
    """
    with database(tmp_path / "db") as connection:
        component = Repository(connection).create_component("X", "Y", "Z")
        store = ImmutableStore(connection)
        root = _root_revision(component.id)
        inventory_hash = store.put_inventory(_inventory(root))
        stored_root = store.put_revision(
            root,
            inventory_sha256=inventory_hash,
            reviewed=False,
        )
        candidate = _candidate(root)
        candidate["electrical"]["resistance"]["value"] = 22000
        candidate_hash = ComponentIR(candidate).sha256
        request = InputReviewProposal(
            component_id=component.id,
            base_revision_id=stored_root.revision_id,
            base_revision_hash=stored_root.canonical_sha256,
            expected_head_hash=NO_HEAD_HASH,
            candidate_revision_id=candidate["revision"]["id"],
            candidate_revision_hash=candidate_hash,
            inventory_sha256=inventory_hash,
            reason="Attempt engineering edit",
        )
        with pytest.raises(ValueError, match="engineering content"):
            InputReviewService(connection).propose(request, candidate)
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_proposals"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM ir_revisions").fetchone()[
                0
            ]
            == 1
        )


def test_authentication_and_proposal_hash_fail_atomically(tmp_path):
    """@brief Verifies identity and exact proposal hashes are mandatory.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Failed attempts leave the proposal undecided and head absent.
    """
    with database(tmp_path / "db") as connection:
        component, proposal, result = _proposal_fixture(connection)
        request = _approval_request(component, proposal, result)
        service = InputReviewService(connection)
        with pytest.raises(PermissionError):
            service.approve_inputs(
                request,
                AuthenticatedPrincipal("another-reviewer", "local-test"),
            )
        stale = InputApprovalRequest(
            **(request.to_dict() | {"proposal_hash": "f" * 64})
        )
        with pytest.raises(ValueError, match="proposal hash"):
            service.approve_inputs(
                stale,
                AuthenticatedPrincipal("reviewer-1", "local-test"),
            )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM review_events"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM component_heads"
            ).fetchone()[0]
            == 0
        )


def test_proposal_hash_binds_generated_identity(tmp_path):
    """@brief Verifies proposal identity participates in immutable bytes.
    @param tmp_path Pytest temporary directory.
    @return None.
    @details Persisted canonical bytes hash to the returned proposal digest.
    """
    with database(tmp_path / "db") as connection:
        _, _, result = _proposal_fixture(connection)
        row = connection.execute(
            "SELECT canonical_sha256, canonical_bytes "
            "FROM review_proposals WHERE id = ?",
            (result.proposal_id,),
        ).fetchone()
        assert sha256(bytes(row["canonical_bytes"])).hexdigest() == (
            result.proposal_hash
        )
        assert row["canonical_sha256"] == result.proposal_hash
        data = json.loads(bytes(row["canonical_bytes"]))
        assert data["proposal_id"] == result.proposal_id
        assert canonical_json(data) == bytes(row["canonical_bytes"])
