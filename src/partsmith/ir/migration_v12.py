"""Explicit IR 1.1 to 1.2 migration preserving historical records."""

from hashlib import sha256

from partsmith.ir.canonical import canonical_json, normalize_json
from partsmith.ir.errors import IRValidationError, Issue
from partsmith.ir.migration import MigrationResult
from partsmith.ir.model import ComponentIR


def migrate_v1_1_to_v1_2(ir, supplied_evidence):
    """Supply revision, accuracy, evidence additions, and decisions.

    Evidence additions are keyed by ID and contain acquisition revision,
    candidate targets, and complete converted source coordinates. Decisions and
    validation results are complete records retaining their original content.
    Missing information yields issues; the input is never mutated or fetched.
    """
    original = ir if isinstance(ir, ComponentIR) else ComponentIR(ir)
    data = original.data
    supplied = normalize_json(supplied_evidence)
    issues = []

    def add(path, message):
        issues.append(Issue(path, "IR_MIGRATION", message))

    allowed = {
        "reason",
        "revision",
        "accuracy_class",
        "evidence",
        "overrides",
        "resolutions",
        "validation_results",
    }
    if not isinstance(supplied, dict) or set(supplied) - allowed:
        add("", "Expected explicit migration evidence fields")
        supplied = {}
    if data["schema_version"] != "1.1":
        add("/schema_version", "Migration requires IR 1.1; migrate 1.0 first")
        data.setdefault("resolutions", [])
    if (
        not isinstance(supplied.get("reason"), str)
        or not supplied["reason"].strip()
    ):
        add("/reason", "Record the migration evidence basis")
    revision = supplied.get("revision")
    if (
        not isinstance(revision, dict)
        or revision.get("id") == data["revision"]["id"]
    ):
        add(
            "/revision",
            "Supply a new IR 1.2 import revision and review bindings",
        )
    else:
        data["revision"] = revision
    if "accuracy_class" not in supplied:
        add(
            "/model_3d/accuracy_class",
            "Supply an evidence-backed accuracy classification",
        )
    else:
        data["model_3d"]["accuracy_class"] = supplied["accuracy_class"]
    evidence = supplied.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {
        r["id"] for r in data["evidence"]
    }:
        add(
            "/evidence",
            "Supply relevance and coordinates for every evidence record",
        )
        evidence = {}
    for i, record in enumerate(data["evidence"]):
        update = evidence.get(record["id"])
        if not isinstance(update, dict) or set(update) != {
            "acquisition_revision_id",
            "candidate_targets",
            "source",
        }:
            add(
                f"/evidence/{i}",
                "Expected acquisition revision, targets and converted source",
            )
            continue
        source = update["source"]
        if not isinstance(source, dict) or any(
            source.get(k) != record["source"].get(k)
            for k in ("document_id", "document_hash", "page")
        ):
            add(
                f"/evidence/{i}/source",
                "Migration cannot change source identity or page",
            )
            continue
        record.update(update)
    for domain, supplied_key in (
        ("overrides", "overrides"),
        ("resolutions", "resolutions"),
        ("results", "validation_results"),
    ):
        old = (
            data["validation"]["results"]
            if domain == "results"
            else data[domain]
        )
        replacements = supplied.get(supplied_key, [] if not old else None)
        if (
            not isinstance(replacements, list)
            or not all(isinstance(r, dict) for r in replacements)
            or len(replacements) != len(old)
            or {r.get("id") for r in replacements if isinstance(r, dict)}
            != {r["id"] for r in old}
        ):
            add(
                "/" + supplied_key,
                "Supply revised records without dropping history",
            )
            continue
        for previous in old:
            replacement = next(
                r for r in replacements if r.get("id") == previous["id"]
            )
            # New fields add context; they cannot change engineering data.
            if any(
                replacement.get(k) != value for k, value in previous.items()
            ):
                add(
                    "/" + supplied_key,
                    "Migration cannot rewrite retained content",
                )
        if domain == "results":
            data["validation"]["results"] = replacements
        else:
            data[domain] = replacements
    data["schema_version"] = "1.2"
    migrated = None
    if not issues:
        try:
            migrated = ComponentIR(data)
        except IRValidationError as error:
            issues.extend(error.issues)
    history = canonical_json(
        {
            "migration": "component-ir/1.1-to-1.2",
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
