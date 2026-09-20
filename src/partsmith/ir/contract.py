"""IR 1.2 typed decisions, applicability, page regions, and active inputs."""

from decimal import Decimal, localcontext

from partsmith.ir.errors import Issue
from partsmith.ir.history import review_issues, revision_chain
from partsmith.ir.revised import (
    UNRESOLVED,
    _context_paths,
    resolve_pointer,
    revised_issues,
)
from partsmith.ir.schema import fragment_valid
from partsmith.ir.targets import (
    effective_path,
    engineering_path,
    overlaps,
    owner_path,
    target_schema,
)

POINTER_ERRORS = (KeyError, IndexError, TypeError, ValueError)


def record_refs(node):
    from partsmith.ir.model import _walk

    for _, record in _walk(node):
        for ref in record.get("evidence_ids", []):
            yield "evidence", ref
        for field, domain in (
            ("standard_id", "standards"),
            ("override_id", "overrides"),
        ):
            if record.get(field) is not None:
                yield domain, record[field]


def _regions(data, add):
    for i, evidence in enumerate(data["evidence"]):
        source = evidence["source"]
        region, page = source["region"], source["page_geometry"]
        if "ocr" in evidence["extractor"]["method"].lower() and region is None:
            add(
                f"/evidence/{i}/source/region",
                "IR_REGION",
                "OCR requires a localized source region",
            )
        if region is None:
            continue
        path = f"/evidence/{i}/source"
        media, crop = page["media_box"], page["crop_box"]
        if any(box[2] <= box[0] or box[3] <= box[1] for box in (media, crop)):
            add(path, "IR_REGION", "Page boxes must have positive area")
        unit = page["user_unit"]
        width, height = (
            (media[2] - media[0]) * unit,
            (media[3] - media[1]) * unit,
        )
        if (
            region["x"] < 0
            or region["y"] < 0
            or region["width"] <= 0
            or region["height"] <= 0
            or region["x"] + region["width"] > width
            or region["y"] + region["height"] > height
        ):
            add(
                path + "/region",
                "IR_REGION",
                "Region must lie inside the physical MediaBox",
            )
        render = source["render_transform"]
        if "ocr" in evidence["extractor"]["method"].lower() and render is None:
            add(
                path + "/render_transform",
                "IR_REGION",
                "OCR requires a retained pixel-to-page transform",
            )
        if render is not None:
            m = render["pixel_to_page"]
            if m[2] != [0, 0, 1] or m[0][0] * m[1][1] == m[0][1] * m[1][0]:
                add(
                    path + "/render_transform",
                    "IR_REGION",
                    "Expected an invertible affine page transform",
                )


def _history_links(data, add):
    for domain, field in (
        ("overrides", "supersedes_override_id"),
        ("resolutions", "supersedes_resolution_id"),
    ):
        records = {r["id"]: r for r in data[domain]}
        for i, record in enumerate(data[domain]):
            seen = {record["id"]}
            ref = record[field]
            while ref is not None:
                if ref in seen or ref not in records:
                    add(
                        f"/{domain}/{i}/{field}",
                        "IR_HISTORY",
                        "Dangling or cyclic decision supersession",
                    )
                    break
                seen.add(ref)
                ref = records[ref][field]
    evidence = {r["id"]: r for r in data["evidence"]}
    excluded = set()
    for i, item in enumerate(data["revision"]["evidence_exclusions"]):
        path = f"/revision/evidence_exclusions/{i}"
        record = evidence.get(item["evidence_id"])
        if record is None or record["candidate_targets"]:
            add(
                path, "IR_REVIEW", "Exclusions cannot remove assigned evidence"
            )
        if item["approval_state"] == "APPROVED":
            if item["evidence_id"] in excluded:
                add(path, "IR_REVIEW", "Duplicate approved exclusion")
            excluded.add(item["evidence_id"])
        for ref in item["replacement_evidence_ids"]:
            replacement = evidence.get(ref)
            if (
                replacement is None
                or record is None
                or ref == record["id"]
                or not replacement["candidate_targets"]
                or replacement["source"] != record["source"]
                or replacement["interpretation"]["status"]
                != record["interpretation"]["status"]
            ):
                add(
                    path,
                    "IR_REVIEW",
                    "Replacement must retain source and interpretation",
                )


def active_decisions(data, chain, add):
    active = {}
    deferred = chain is None and bool(data["revision"]["target_rebindings"])
    for domain, selector, field in (
        ("overrides", "active_override_ids", "path"),
        ("resolutions", "active_resolution_ids", "target_path"),
    ):
        records = {r["id"]: r for r in data[domain]}
        selected = {}
        for key in data["revision"][selector]:
            record = records.get(key)
            if record is None or record["approval_state"] != "APPROVED":
                add(
                    "/revision/" + selector,
                    "IR_SELECTION",
                    "Active decision must resolve to an approved record",
                )
                continue
            try:
                path = effective_path(
                    data, record[field], record["base_revision_id"], chain
                )
                if path is None:
                    raise ValueError
                path = (
                    owner_path(data, path) if domain == "resolutions" else path
                )
                if path in selected or (
                    domain == "overrides"
                    and any(overlaps(path, p) for p in selected)
                ):
                    add(
                        "/revision/" + selector,
                        "IR_SELECTION",
                        "Active target decisions overlap",
                    )
                target = resolve_pointer(data, path)
                if domain == "resolutions" and not isinstance(target, dict):
                    raise ValueError
                selected[path] = record
                if (
                    domain == "overrides"
                    and not deferred
                    and target != record["new_value"]
                ):
                    add(
                        "/revision/" + selector,
                        "IR_OVERRIDE",
                        "Active override must match its target value",
                    )
            except POINTER_ERRORS:
                if not deferred:
                    add(
                        "/revision/" + selector,
                        "IR_SELECTION",
                        "Active target does not resolve",
                    )
        active[domain] = selected
    return active


def _decision_values(data, active, add, chain=None):
    from partsmith.ir.model import _walk

    for i, record in enumerate(data["overrides"]):
        path = f"/overrides/{i}"
        try:
            schema, kind = target_schema(record["path"])
            if kind != record["value_type"]:
                raise ValueError
            for field in ("previous_value", "new_value"):
                if not fragment_valid(record[field], schema):
                    raise ValueError
            # This record binding is not recursively followed while hashing.
            if (
                isinstance(record["new_value"], dict)
                and "status" in record["new_value"]
            ):
                new = record["new_value"]
                if (
                    new["status"] != "USER_OVERRIDE"
                    or new.get("override_id") != record["id"]
                ):
                    raise ValueError
        except POINTER_ERRORS:
            add(
                path,
                "IR_OVERRIDE",
                "Override must match its registered target type and binding",
            )
    selected = {r["id"]: (p, r) for p, r in active["overrides"].items()}
    for path, node in _walk(data):
        if not engineering_path(path):
            continue
        if (
            node.get("status") == "USER_OVERRIDE"
            or node.get("override_id") is not None
        ):
            binding = selected.get(node.get("override_id"))
            if binding is None:
                add(
                    path,
                    "IR_OVERRIDE",
                    "Override binding must select an active decision",
                )
            elif (
                chain is not None or not data["revision"]["target_rebindings"]
            ):
                target, record = binding
                if path == target:
                    matches = node == record["new_value"]
                elif record["value_type"] == "PIN_ARRAY" and path.startswith(
                    target + "/"
                ):
                    try:
                        matches = node == resolve_pointer(
                            record["new_value"], path[len(target) :]
                        )
                    except POINTER_ERRORS:
                        matches = False
                else:
                    matches = False
                if not matches:
                    add(
                        path,
                        "IR_OVERRIDE",
                        "Override cannot authorize another target",
                    )


def _candidate_paths(data, chain, add):
    assignments = {}
    for i, record in enumerate(data["evidence"]):
        owners = set()
        for path in record["candidate_targets"]:
            try:
                path = effective_path(
                    data, path, record["acquisition_revision_id"], chain
                )
                if path is not None:
                    owners.add(owner_path(data, path))
            except POINTER_ERRORS:
                if (
                    chain is not None
                    or not data["revision"]["target_rebindings"]
                ):
                    add(
                        f"/evidence/{i}/candidate_targets",
                        "IR_RELEVANCE",
                        "Candidate target must resolve in its revision",
                    )
        assignments[record["id"]] = owners
    return assignments


def contract_issues(data, generation, requirements, revisions):
    # Shared IR 1.1 checks deliberately stop before its old decision rules.
    issues = revised_issues(data, False, None)

    def add(path, code, message):
        issues.append(Issue(path, code, message))

    with localcontext() as context:
        context.prec = 256
        _regions(data, add)
    _history_links(data, add)
    chain = None
    if generation:
        chain, failures = revision_chain(data, revisions)
        issues.extend(failures)
        issues.extend(review_issues(data, revisions, chain))
    active = active_decisions(data, chain, add)
    _decision_values(data, active, add, chain)
    assignments = _candidate_paths(data, chain, add)
    evidence = {r["id"]: r for r in data["evidence"]}
    for i, record in enumerate(data["resolutions"]):
        selected, superseded = (
            set(record["selected_evidence_ids"]),
            set(record["superseded_evidence_ids"]),
        )
        if (
            selected & superseded
            or not (selected | superseded) <= evidence.keys()
        ):
            add(
                f"/resolutions/{i}",
                "IR_RESOLUTION",
                "Resolution evidence references must resolve and be disjoint",
            )
    for path, record in active["resolutions"].items():
        target = resolve_pointer(data, path)
        overrides = [
            r
            for p, r in active["overrides"].items()
            if owner_path(data, p) == path
        ]
        bound = next(
            (r for r in overrides if r["id"] == record["override_id"]), None
        )
        expected = (
            {bound["evidence_reference"]}
            if bound
            else set(target.get("evidence_ids", []))
        )
        if (
            set(record["selected_evidence_ids"]) != expected
            or (record["override_id"] is not None and bound is None)
            or (not expected and bound is None)
        ):
            add(
                path,
                "IR_RESOLUTION",
                "Active resolution must match selected evidence and override",
            )
        for ref in record["superseded_evidence_ids"]:
            if ref in assignments and not any(
                overlaps(path, p) for p in assignments[ref]
            ):
                add(
                    path,
                    "IR_RESOLUTION",
                    "Superseded evidence must be relevant to the target",
                )
    if not generation:
        return issues
    required = _context_paths(requirements)
    if required is None:
        add(
            "",
            "IR_REQUIREMENTS",
            "Generation requires a trusted requirements context",
        )
        return issues
    _generation(data, required, requirements, active, assignments, add)
    return issues


def _generation(data, required, requirements, active, assignments, add):
    from partsmith.ir.model import _walk

    records = {
        (domain, r["id"]): r
        for domain in ("evidence", "standards", "overrides", "resolutions")
        for r in data[domain]
    }
    pending = []
    required_owners = set()
    for path in ("/identity", *required):
        try:
            path = owner_path(data, path)
            pending.append((path, resolve_pointer(data, path)))
            required_owners.add(path)
        except POINTER_ERRORS:
            add(
                path,
                "IR_REQUIREMENTS",
                "Required engineering target is absent",
            )
    selected_overrides = set()
    for path, record in active["overrides"].items():
        if any(overlaps(owner_path(data, path), p) for p in required_owners):
            selected_overrides.add(record["id"])
            pending.append(
                (f"/overrides/{record['id']}/new_value", record["new_value"])
            )
            pending.append(
                (
                    f"/evidence/{record['evidence_reference']}",
                    records[("evidence", record["evidence_reference"])],
                )
            )
    for evidence_id, paths in assignments.items():
        for path in paths:
            if not any(overlaps(path, p) for p in required_owners):
                continue
            evidence = records[("evidence", evidence_id)]
            if evidence["interpretation"]["status"] in UNRESOLVED:
                resolution = active["resolutions"].get(path)
                if (
                    resolution is None
                    or evidence_id not in resolution["superseded_evidence_ids"]
                ):
                    add(
                        path,
                        "IR_CONFLICT",
                        "Unresolved candidate requires a resolution",
                    )
    seen = set()
    while pending:
        path, node = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        if node is None:
            add(path, "IR_UNRESOLVED", "Required input is null")
        for location, item in _walk(node, path):
            status = item.get("status")
            if status in UNRESOLVED:
                add(location, "IR_UNRESOLVED", "Selected input is unresolved")
            if (
                "source_value" in item
                and (
                    item["source_value"] is None or item["source_unit"] is None
                )
            ) or (
                "value" in item and "status" in item and item["value"] is None
            ):
                add(
                    location,
                    "IR_UNRESOLVED",
                    "Required value and units must be concrete",
                )
            is_evidence = location.startswith(
                "/evidence/"
            ) and location.endswith("/interpretation")
            if (
                status == "DIRECT"
                and not is_evidence
                and not item.get("evidence_ids")
            ):
                add(
                    location,
                    "IR_PROVENANCE",
                    "Direct engineering data needs evidence",
                )
            if status == "DERIVED" and (
                not item.get("derivation") or not item.get("evidence_ids")
            ):
                add(
                    location,
                    "IR_PROVENANCE",
                    "Derived data needs retained inputs and derivation",
                )
            if status == "STANDARD" and not item.get("standard_id"):
                add(
                    location,
                    "IR_PROVENANCE",
                    "Standard data needs a versioned standard",
                )
            if (
                status == "USER_OVERRIDE"
                and item.get("override_id") not in selected_overrides
            ):
                add(
                    location,
                    "IR_OVERRIDE",
                    "Active input must bind an approved selected override",
                )
            if location.startswith("/package/mechanical/") and (
                item.get("normalized_value") == Decimal(0)
                or item.get("normalized_min") == Decimal(0)
            ):
                if (
                    location not in requirements.zero_allowed_paths
                    or location.rsplit("/", 1)[-1]
                    in {"body_width", "body_length", "body_height"}
                ):
                    add(
                        location,
                        "IR_DIMENSION",
                        "Zero requires a declared optional feature",
                    )
            if engineering_path(location):
                for ref in item.get("evidence_ids", []):
                    if not any(
                        overlaps(location, p) for p in assignments.get(ref, ())
                    ):
                        add(
                            location,
                            "IR_RELEVANCE",
                            "Selected evidence lacks a compatible target",
                        )
        for domain, ref in record_refs(node):
            record = records.get((domain, ref))
            if record is None:
                continue  # Common structural validator supplies the error.
            if domain == "overrides":
                if ref not in selected_overrides:
                    add(
                        path,
                        "IR_OVERRIDE",
                        "Inactive override cannot support generation",
                    )
                continue
            if domain == "standards" and (
                record["revision"].upper() in UNRESOLVED | {"UNVERSIONED"}
                or not record["evidence_ids"]
            ):
                add(
                    path,
                    "IR_PROVENANCE",
                    "Standard needs an edition and retained evidence",
                )
            pending.append((f"/{domain}/{ref}", record))
