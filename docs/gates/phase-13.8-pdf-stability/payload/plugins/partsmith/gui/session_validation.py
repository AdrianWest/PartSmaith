"""@package partsmith.gui.session_validation
@brief Revalidates immutable database and active review identities on load.
@details Transport hashes alone do not authorize a saved approval label;
review decisions and current content bindings must resolve consistently.
"""

from hashlib import sha256

from partsmith.ir import ComponentIR
from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence import ImmutableStore

from .release_review import verify_current_release

HASHED_DOCUMENTS = {
    "acquisition_inventories": "sha256",
    "ir_revisions": "canonical_sha256",
    "review_proposals": "canonical_sha256",
    "review_events": "canonical_sha256",
    "build_snapshots": "input_snapshot_hash",
    "validation_results": "canonical_sha256",
    "engineering_manifests": "sha256",
    "post_manifest_reports": "sha256",
    "approval_bindings": "canonical_sha256",
    "node_cache": "content_sha256",
    "reproducibility_reports": "sha256",
}


def validate_database(session, connection):
    """@brief Validates canonical database objects and current desktop
    bindings.
    @param session Fully staged loaded session with verified CAS objects.
    @param connection Caller-owned migrated database transaction.
    @return None.
    @details Rejects corrupted historical records and forged current approval
    labels before the active session can be replaced.
    """
    from partsmith.integration.workflow import require_data_session

    require_data_session(connection)
    for table, column in HASHED_DOCUMENTS.items():
        for row in connection.execute(
            f"SELECT canonical_bytes, {column} FROM {table}"
        ):
            content = bytes(row[0])
            if (
                sha256(content).hexdigest() != row[1]
                or canonical_json(parse_json(content)) != content
            ):
                raise ValueError(
                    f"Session immutable document mismatch: {table}"
                )
            if table == "ir_revisions":
                ComponentIR(parse_json(content))
    for table in ("artifacts",):
        columns = {
            row[1] for row in connection.execute(f"PRAGMA table_info({table})")
        }
        if {"content", "sha256"} <= columns:
            for row in connection.execute(
                f"SELECT content, sha256 FROM {table}"
            ):
                if sha256(bytes(row[0])).hexdigest() != row[1]:
                    raise ValueError(
                        f"Session artifact hash mismatch: {table}"
                    )
    state, store = session.state, ImmutableStore(connection)
    if state.get("build_id"):
        build = connection.execute(
            "SELECT component_id FROM builds WHERE id=?", (state["build_id"],)
        ).fetchone()
        if build is None or build[0] != state.get("component_id"):
            raise ValueError("Session build binding does not resolve")
    for artifact in state.get("drafts", {}).get("artifacts", []):
        row = connection.execute(
            "SELECT * FROM artifacts WHERE build_id=? "
            "AND artifact_type=? AND stage=?",
            (artifact["build_id"], artifact["type"], artifact["stage"]),
        ).fetchone()
        ir = store.get_revision(artifact["revision_id"])
        if (
            row is None
            or artifact["sha256"] != row["sha256"]
            or (
                session.get(artifact["reference"]) != bytes(row["content"])
                or ir["identity"]["component_id"] != state["component_id"]
                or canonical_json(artifact.get("placement"))
                != canonical_json(ir["model_3d"]["placement"])
            )
        ):
            raise ValueError(
                "Session artifact/revision/placement binding mismatch"
            )
    if state.get("revision_id"):
        ir = store.get_revision(state["revision_id"])
        session.verify_part_number(ir)
        if ir["identity"]["component_id"] != state["component_id"]:
            raise ValueError("Session current component/revision mismatch")
        if canonical_json(state.get("drafts", {}).get("ir")) != canonical_json(
            ir
        ):
            raise ValueError(
                "Session displayed IR differs from immutable revision"
            )
        head = connection.execute(
            "SELECT * FROM component_heads WHERE component_id=?",
            (state["component_id"],),
        ).fetchone()
        if head and (
            head["revision_id"] != state["revision_id"]
            or head["revision_hash"] != ComponentIR(ir).sha256
        ):
            raise ValueError("Session current reviewed head mismatch")
        if state.get("inventory_sha256"):
            store.get_inventory(state["inventory_sha256"])
    proposal = state.get("proposal")
    if proposal:
        row = connection.execute(
            "SELECT * FROM review_proposals WHERE id=?",
            (proposal["proposal_id"],),
        ).fetchone()
        if row is None or row["canonical_sha256"] != proposal["proposal_hash"]:
            raise ValueError("Session pending proposal binding mismatch")
        candidate = store.get_revision(proposal["candidate_revision_id"])
        if (
            ComponentIR(candidate).sha256
            != proposal["candidate_revision_hash"]
        ):
            raise ValueError("Session pending candidate binding mismatch")
    release = state.get("release")
    if release:
        verify_current_release(session, connection, verify_validation=False)
    if release and release.get("approved"):
        build = connection.execute(
            "SELECT state FROM builds WHERE id=?", (release["build_id"],)
        ).fetchone()
        if build is None or build[0] != "APPROVED":
            raise ValueError(
                "Session approved label differs from build decision state"
            )
        binding = verify_current_release(
            session, connection, allow_approved=True
        )
        row = connection.execute(
            "SELECT * FROM approval_bindings WHERE build_id=?",
            (release["build_id"],),
        ).fetchone()
        if (
            row is None
            or row["release_decision_id"] != release.get("decision_id")
            or (
                bytes(row["canonical_bytes"])
                != canonical_json(binding.to_dict())
            )
        ):
            raise ValueError(
                "Session approved label has no exact decision binding"
            )
        decision = connection.execute(
            "SELECT * FROM release_decisions WHERE id=?",
            (release["decision_id"],),
        ).fetchone()
        if decision is None or decision["decision"] != "APPROVE":
            raise ValueError("Session approval decision does not resolve")
