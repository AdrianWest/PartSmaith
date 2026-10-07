"""@package partsmith.gui.release_review
@brief Adapts explicit release review to exact existing service bindings.
@details Input approval never grants release approval. Saved approval labels
are rechecked against retained objects, current heads and immutable decisions.
"""

from hashlib import sha256

from partsmith.ir.canonical import parse_json
from partsmith.persistence import ImmutableStore
from partsmith.persistence.release import ReleaseStore
from partsmith.release.contracts import ApprovalBinding
from partsmith.release.workflow import ReviewService

from .identity import authenticated_principal


def binding_document(value):
    """@brief Constructs the existing exact content approval contract.
    @param value Closed retained binding mapping.
    @return ApprovalBinding with immutable hash arrays.
    @details Normal contract validation rejects malformed digest sets.
    """
    return ApprovalBinding(
        **{
            **value,
            "artifact_hashes": tuple(value["artifact_hashes"]),
            "post_manifest_report_hashes": tuple(
                value["post_manifest_report_hashes"]
            ),
        }
    )


def verify_current_release(
    session, connection, *, allow_approved=False, verify_validation=True
):
    """@brief Rechecks exact current-head, artifact and service bindings.
    @param session Current operational session.
    @param connection Caller-owned read/review transaction.
    @param allow_approved Permit verifying an already approved retained build.
    @param verify_validation Require passing release validation for approval.
    @return Existing ApprovalBinding after complete verification.
    @details Retained CAS objects must equal the service's final artifact
    bytes;
    stale revisions or altered artifacts cannot inherit an approval label.
    """
    release = session.state.get("release")
    if not release:
        raise ValueError("No validated release candidate")
    head = connection.execute(
        "SELECT * FROM component_heads WHERE component_id=?",
        (session.state["component_id"],),
    ).fetchone()
    if (
        head is None
        or head["revision_id"] != release["revision_id"]
        or (
            release["revision_id"] != session.state["revision_id"]
            or release["build_id"] != session.state["build_id"]
        )
    ):
        raise ValueError(
            "Release candidate differs from the current reviewed head"
        )
    session.verify_part_number(
        ImmutableStore(connection).get_revision(release["revision_id"])
    )
    snapshot = connection.execute(
        "SELECT * FROM build_snapshots WHERE build_id=?",
        (release["build_id"],),
    ).fetchone()
    if snapshot is None or snapshot["ir_record_hash"] != head["revision_hash"]:
        raise ValueError(
            "Release snapshot differs from the current reviewed IR"
        )
    pdl = session.state.get("pdl", {})
    if (
        snapshot["pdl_id"],
        snapshot["pdl_revision"],
        snapshot["pdl_hash"],
    ) != (pdl.get("id"), pdl.get("revision"), pdl.get("sha256")):
        raise ValueError("Release snapshot differs from the selected PDL")
    retained = {
        item["type"]: item
        for item in session.state.get("drafts", {}).get("artifacts", [])
        if item["stage"] == "FINAL" and item["build_id"] == release["build_id"]
    }
    rows = connection.execute(
        "SELECT * FROM artifacts WHERE build_id=? AND stage='FINAL'",
        (release["build_id"],),
    ).fetchall()
    if len(rows) != 3 or len(retained) != 3:
        raise ValueError("Exact final artifacts are incomplete")
    for row in rows:
        item = retained[row["artifact_type"]]
        content = session.get(item["reference"])
        if item["revision_id"] != release["revision_id"] or (
            sha256(content).hexdigest() != row["sha256"]
            or item["sha256"] != row["sha256"]
            or content != bytes(row["content"])
        ):
            raise ValueError(
                "Retained final artifact differs from release binding"
            )
    binding = binding_document(release["binding"])
    if verify_validation:
        ReleaseStore(connection).verify_approval_binding(
            release["build_id"], binding, allow_approved=allow_approved
        )
    return binding


def release_report(session):
    """@brief Reads exact validation, manifest and blocking review content.
    @param session Current operational session.
    @return Detached report mapping for the final review screen.
    @details No decision is made by inspecting or opening the review screen.
    """
    build = session.state.get("build_id")
    report = {
        "build_id": build,
        "revision_id": session.state.get("revision_id"),
        "release": session.state.get("release"),
        "blockers": [],
    }
    if not build:
        report["blockers"] = [
            "Generate and validate explicitly reviewed inputs first"
        ]
        return report
    with session.connection() as connection:
        store = ReleaseStore(connection)
        row = connection.execute(
            "SELECT state FROM builds WHERE id=?", (build,)
        ).fetchone()
        transition = connection.execute(
            "SELECT review_stage FROM build_state_transitions "
            "WHERE build_id=? ORDER BY id DESC LIMIT 1",
            (build,),
        ).fetchone()
        report["review_required"] = bool(
            row
            and row[0] == "HUMAN_REVIEW_REQUIRED"
            and transition
            and transition[0] == "RELEASE"
        )
        report["validation"] = store.retained_validation_results(build)
        row = connection.execute(
            "SELECT canonical_bytes FROM engineering_manifests "
            "WHERE build_id=?",
            (build,),
        ).fetchone()
        report["manifest"] = parse_json(row[0]) if row else None
        report["post_manifest_reports"] = [
            parse_json(row[0])
            for row in connection.execute(
                "SELECT canonical_bytes FROM post_manifest_reports "
                "WHERE build_id=?",
                (build,),
            )
        ]
        try:
            verify_current_release(session, connection, allow_approved=True)
        except (ValueError, RuntimeError, KeyError) as error:
            report["blockers"].append(str(error))
    return report


def decide_release(
    session, approve, reason, *, identity=authenticated_principal
):
    """@brief Explicitly approves or rejects a bound release atomically.
    @param session Current isolated operational session.
    @param approve Deliberate approval or rejection choice.
    @param reason Required decision rationale.
    @param identity Trusted current OS authentication adapter.
    @return Immutable existing service decision identity.
    @details Saved/display actors are never used as authenticated principals;
    committed release state and audit history persist in the same transaction.
    """
    principal = identity()
    release = session.state.get("release")
    if not release:
        raise ValueError("No release candidate to review")
    if not reason.strip():
        raise ValueError("Release decision requires a reason")
    with session.connection() as connection:
        binding = verify_current_release(
            session, connection, verify_validation=approve
        )
        service = ReviewService(connection)
        if approve:
            decision = service.approve(
                release["build_id"],
                principal.subject,
                reason,
                binding,
                principal,
            )
        else:
            decision = service.reject(
                release["build_id"], principal.subject, reason, principal
            )
        history = [
            *session.state.get("history", []),
            {
                "kind": "RELEASE_APPROVE" if approve else "RELEASE_REJECT",
                "decision_id": decision,
                "actor": principal.subject,
                "mechanism": principal.mechanism,
                "reason": reason,
                "binding": binding.to_dict(),
            },
        ]
        session.update(
            _connection=connection,
            release={**release, "approved": approve, "decision_id": decision},
            status="release-approved" if approve else "release-rejected",
            history=history,
        )
    return decision
