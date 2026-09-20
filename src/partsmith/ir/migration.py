"""Explicit, evidence-supplied migration; no inferred engineering defaults."""

from dataclasses import dataclass
from hashlib import sha256

from partsmith.ir.canonical import canonical_json, normalize_json
from partsmith.ir.errors import IRValidationError, Issue
from partsmith.ir.model import ComponentIR


@dataclass(frozen=True)
class MigrationResult:
    ir: ComponentIR | None
    history: bytes
    issues: tuple[Issue, ...]


def migrate_v1_0_to_v1_1(ir, supplied_evidence) -> MigrationResult:
    """Return a new immutable IR and canonical audit history, or stable issues.

    supplied_evidence accepts source_document_id, document_revisions (complete
    revision/revision_basis pairs keyed by document ID), land_pattern_source,
    placement (complete convention-1.1 record), standards (complete records
    keyed by ID), and reason. Supplied records are validated, never fetched.
    A placement and reason are mandatory because 1.0 did not define its frame.
    """
    original = ir if isinstance(ir, ComponentIR) else ComponentIR(ir)
    issues = []
    data = original.data
    supplied = normalize_json(supplied_evidence)

    def add(path, message):
        issues.append(Issue(path, "IR_MIGRATION", message))

    if data["schema_version"] != "1.0":
        add("/schema_version", "Migration requires an IR 1.0 source")
    allowed = {
        "source_document_id",
        "document_revisions",
        "land_pattern_source",
        "placement",
        "standards",
        "reason",
    }
    if not isinstance(supplied, dict) or set(supplied) - allowed:
        add("", "Expected supported, explicit migration evidence fields")
        supplied = {}
    for field in ("document_revisions", "standards"):
        if field in supplied and not isinstance(supplied[field], dict):
            add("/" + field, "Expected records keyed by source ID")
            supplied[field] = {}
    if (
        not isinstance(supplied.get("reason"), str)
        or not supplied["reason"].strip()
    ):
        add("/reason", "Record the migration evidence basis")
    docs = data["source"]["documents"]
    doc_ids = {doc["id"] for doc in docs}
    doc_id = supplied.get("source_document_id")
    if doc_id is None and len(docs) == 1:
        doc_id = docs[0]["id"]
    if not isinstance(doc_id, str) or doc_id not in doc_ids:
        add(
            "/identity/source_document_id",
            "Identify the authoritative source document",
        )
    else:
        data["identity"]["source_document_id"] = doc_id
    for doc in docs:
        update = supplied.get("document_revisions", {}).get(doc["id"])
        if update is not None:
            if not isinstance(update, dict) or set(update) - {
                "revision",
                "revision_basis",
            }:
                add(
                    "/source/documents",
                    "Expected revision and optional revision_basis only",
                )
            elif (
                doc.get("revision")
                and update.get("revision", doc["revision"]) != doc["revision"]
            ):
                add(
                    "/source/documents",
                    "Supplied revision conflicts with retained source",
                )
            else:
                doc.update(update)
        if not doc.get("revision"):
            add(
                "/source/documents",
                "Missing source revision requires evidence",
            )
        if doc["id"] == doc_id and doc.get("revision"):
            old = data["identity"].get("source_revision")
            if old and old != doc["revision"]:
                add(
                    "/identity/source_revision",
                    "Identity and document revisions conflict",
                )
            data["identity"]["source_revision"] = doc["revision"]
    source = data["footprint"]["land_pattern_source"]
    selected = supplied.get("land_pattern_source")
    if source == "MANUFACTURER":
        if selected is not None and selected != "MANUFACTURER_RECOMMENDED":
            add(
                "/footprint/land_pattern_source",
                "Source category conflicts with manufacturer evidence",
            )
        selected = "MANUFACTURER_RECOMMENDED"
    elif source == "STANDARD" and selected not in (
        "IPC_DERIVED",
        "PDL_DERIVED",
    ):
        add(
            "/footprint/land_pattern_source",
            "Identify IPC versus PDL derivation",
        )
    elif source == "USER_OVERRIDE" and selected not in (
        "MANUFACTURER_RECOMMENDED",
        "IPC_DERIVED",
        "PDL_DERIVED",
    ):
        add(
            "/footprint/land_pattern_source",
            "Recover the underlying source category",
        )
    data["footprint"]["land_pattern_source"] = selected
    if not isinstance(supplied.get("placement"), dict):
        add(
            "/model_3d/placement",
            "Supply evidence-backed convention 1.1 placement",
        )
    else:
        data["model_3d"]["placement"] = supplied["placement"]
    for index, standard in enumerate(data["standards"]):
        replacement = supplied.get("standards", {}).get(standard["id"])
        if (
            not isinstance(replacement, dict)
            or replacement.get("id") != standard["id"]
        ):
            add(
                f"/standards/{index}",
                "Supply a complete structured standard record",
            )
        elif any(
            replacement.get(field) != standard[field]
            for field in ("revision", "reference")
        ):
            add(
                f"/standards/{index}",
                "Standard revision/reference conflicts with retained evidence",
            )
        else:
            data["standards"][index] = replacement
    data["schema_version"] = "1.1"
    data["resolutions"] = []
    migrated = None
    if not issues:
        try:
            migrated = ComponentIR(data)
        except IRValidationError as error:
            issues.extend(error.issues)
    history = canonical_json(
        {
            "migration": "component-ir/1.0-to-1.1",
            "migration_version": "1.0",
            "source_ir_hash": original.sha256,
            "target_ir_hash": migrated.sha256 if migrated else None,
            "supplied_evidence_hash": sha256(
                canonical_json(supplied_evidence)
            ).hexdigest(),
            "reason": supplied.get("reason"),
            "status": "FAILED" if issues else "COMPLETE",
        }
    )
    return MigrationResult(migrated, history, tuple(sorted(set(issues))))
