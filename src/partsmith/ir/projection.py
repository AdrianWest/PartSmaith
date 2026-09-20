"""Snapshot-profile 1.1 dependency projections, without orchestration."""

from dataclasses import asdict
from hashlib import sha256

from partsmith.ir.canonical import canonical_json, normalize_json
from partsmith.ir.contract import active_decisions
from partsmith.ir.errors import fail
from partsmith.ir.history import revision_chain
from partsmith.ir.model import _PROPERTY_MAPS, normalize_ir
from partsmith.ir.revised import resolve_pointer
from partsmith.ir.targets import effective_path, overlaps, owner_path


def dependency_projection(data, *, requirements, revisions, configuration):
    """Project declared engineering inputs using content references.

    configuration contains trusted non-secret pdl, release_profile, runtime,
    and exporter objects. Actual production PDL and CAD runtime checks
    remain in later phases. This function never reads environment variables.
    """
    data = normalize_ir(
        data,
        for_generation=True,
        requirements=requirements,
        revisions=revisions,
    )
    if data["schema_version"] != "1.2":
        fail("/schema_version", "IR_VERSION", "Projection requires IR 1.2")
    config = normalize_json(configuration)
    if not isinstance(config, dict) or set(config) != {
        "pdl",
        "release_profile",
        "runtime",
        "exporter",
    }:
        fail(
            "/configuration",
            "IR_REQUIREMENTS",
            "Expected complete pinned engineering configuration",
        )
    if any(
        not isinstance(value, dict) or not value for value in config.values()
    ):
        fail(
            "/configuration",
            "IR_REQUIREMENTS",
            "Configuration objects must be nonempty",
        )
    runtime = config["runtime"]
    if not all(
        isinstance(runtime.get(k), str) and runtime[k].strip()
        for k in (
            "python",
            "cadquery",
            "ocp",
            "occt",
            "generator",
            "validator",
        )
    ):
        fail(
            "/configuration/runtime",
            "IR_REQUIREMENTS",
            "All runtime and adapter versions are required",
        )
    profile = config["release_profile"]
    if not all(
        isinstance(profile.get(k), str) and profile[k].strip()
        for k in ("id", "version", "accuracy_class")
    ):
        fail(
            "/configuration/release_profile",
            "IR_REQUIREMENTS",
            "Expected a pinned release profile",
        )
    if profile["accuracy_class"] != data["model_3d"]["accuracy_class"] or (
        profile["id"] == "mvp-1" and profile["accuracy_class"] != "CLASS_A"
    ):
        fail(
            "/model_3d/accuracy_class",
            "IR_ACCURACY",
            "Model classification does not meet the release profile",
        )
    chain, _ = revision_chain(data, revisions)
    active = active_decisions(data, chain, lambda p, c, m: fail(p, c, m))
    required = sorted(
        {
            "/identity",
            *(owner_path(data, p) for p in requirements.required_paths),
        }
    )
    records = {
        (domain, r["id"]): r
        for domain in ("evidence", "standards", "overrides", "resolutions")
        for r in data[domain]
    }
    records.update(
        {("documents", r["id"]): r for r in data["source"]["documents"]}
    )
    cache, visiting = {}, set()

    def digest(domain, key):
        ref = (domain, key)
        if ref in visiting:
            fail("", "IR_CYCLE", "Cyclic content projection")
        if ref not in cache:
            visiting.add(ref)
            record = records[ref]
            if domain == "overrides":
                path = effective_path(
                    data, record["path"], record["base_revision_id"], chain
                )
                content = {
                    "path": path,
                    "value_type": record["value_type"],
                    "reason": record["reason"],
                    "new_value": project(record["new_value"], path, key),
                    "evidence": digest(
                        "evidence", record["evidence_reference"]
                    ),
                }
            elif domain == "resolutions":
                content = {
                    "target_path": effective_path(
                        data,
                        record["target_path"],
                        record["base_revision_id"],
                        chain,
                    ),
                    "decision": record["decision"],
                    "reason": record["reason"],
                    "selected_evidence": sorted(
                        digest("evidence", r)
                        for r in record["selected_evidence_ids"]
                    ),
                    "override": digest("overrides", record["override_id"])
                    if record["override_id"]
                    else None,
                }
            else:
                record = {
                    k: v
                    for k, v in record.items()
                    if k not in {"id", "acquisition_revision_id"}
                }
                if domain == "evidence":
                    record["candidate_targets"] = sorted(
                        p
                        for raw in record["candidate_targets"]
                        if (
                            p := effective_path(
                                data,
                                raw,
                                records[ref]["acquisition_revision_id"],
                                chain,
                            )
                        )
                        is not None
                    )
                content = project(record, "/" + domain)
            cache[ref] = sha256(canonical_json(content)).hexdigest()
            visiting.remove(ref)
        return cache[ref]

    def project(node, path, self_override=None):
        if isinstance(node, list):
            return [
                project(v, path + "/" + str(i), self_override)
                for i, v in enumerate(node)
            ]
        if not isinstance(node, dict):
            return node
        output = {}
        for key, value in node.items():
            child = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if path in _PROPERTY_MAPS:
                output[key] = project(value, child, self_override)
                continue
            if key == "component_id" and path == "/identity":
                continue
            if key == "timestamp" and path.endswith("/translation"):
                continue
            if key == "captured_at" and path.endswith("/revision_basis"):
                continue
            if key == "override_id" and value == self_override:
                continue
            if key == "evidence_ids":
                output[key] = [digest("evidence", ref) for ref in value]
            elif (
                key
                in {
                    "standard_id",
                    "override_id",
                    "source_document_id",
                    "document_id",
                }
                and value is not None
            ):
                domain = {
                    "standard_id": "standards",
                    "override_id": "overrides",
                    "source_document_id": "documents",
                    "document_id": "documents",
                }[key]
                output[key] = digest(domain, value)
            else:
                output[key] = project(value, child, self_override)
        return output

    inputs = {
        path: project(resolve_pointer(data, path), path) for path in required
    }
    decisions = {}
    for domain, values in active.items():
        decisions[domain] = sorted(
            digest(domain, r["id"])
            for path, r in values.items()
            if any(overlaps(owner_path(data, path), p) for p in required)
        )
    # The full audit retains excluded bodies and predecessor IDs. The active
    # projection retains the substantive disposition/rebinding, not execution.
    dispositions = []
    for r in data["revision"]["evidence_exclusions"]:
        if r["approval_state"] == "APPROVED" and any(
            any(overlaps(p, t) for p in required)
            for ref in r["replacement_evidence_ids"]
            for t in records[("evidence", ref)]["candidate_targets"]
        ):
            dispositions.append(
                {
                    "reason": r["reason"],
                    "replacements": sorted(
                        digest("evidence", ref)
                        for ref in r["replacement_evidence_ids"]
                    ),
                }
            )
    return {
        "snapshot_profile": "1.1",
        "canonical_profile": "1.0",
        "ir_schema": "1.2",
        "requirements": {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in asdict(requirements).items()
        },
        "configuration": config,
        "inputs": inputs,
        "decisions": decisions,
        "dispositions": sorted(dispositions, key=canonical_json),
        "rebindings": [
            {key: item[key] for key in ("old_path", "new_path", "reason")}
            for item in data["revision"]["target_rebindings"]
            if item["approval_state"] == "APPROVED"
            and any(
                overlaps(item["old_path"], path)
                or (
                    item["new_path"] is not None
                    and overlaps(item["new_path"], path)
                )
                for path in required
            )
        ],
    }


def dependency_hash(data, **kwargs):
    return sha256(
        canonical_json(dependency_projection(data, **kwargs))
    ).hexdigest()
