"""IR 1.1 provenance and input-only generation requirements.

Contexts are supplied by trusted, versioned PDL/generator adapters, never by
the IR being validated. Phase 2 defines this protocol; later phases provide
production adapters and their mandatory input declarations.
"""

import re
from dataclasses import dataclass

from partsmith.ir.errors import Issue

UNRESOLVED = {"UNKNOWN", "INFERRED", "AMBIGUOUS", "CONFLICTING", "MISSING"}


def resolve_pointer(data, path):
    """Resolve strict RFC 6901 pointers, including escaped property names."""
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("Expected a non-root JSON Pointer")
    node = data
    for token in path[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ValueError("Invalid pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("Invalid array index")
            node = node[int(token)]
        elif isinstance(node, dict):
            node = node[token]
        else:
            raise ValueError("Pointer traverses a scalar")
    return node


@dataclass(frozen=True)
class RequirementsContext:
    """Pinned adapter declaration plus requested paths (a superset).

    mandatory_paths and zero_allowed_paths belong to the adapter/PDL, not to
    user configuration. Altering their declaration requires a version change.
    """

    artifact: str
    generator_version: str
    pdl_version: str
    rule_version: str
    mandatory_paths: tuple[str, ...]
    required_paths: tuple[str, ...]
    zero_allowed_paths: tuple[str, ...] = ()
    context_version: str = "1.0"


def _context_paths(context):
    if not isinstance(context, RequirementsContext):
        return None
    if context.context_version != "1.0" or not all(
        isinstance(value, str) and value.strip()
        for value in (
            context.artifact,
            context.generator_version,
            context.pdl_version,
            context.rule_version,
        )
    ):
        return None
    for paths in (
        context.mandatory_paths,
        context.required_paths,
        context.zero_allowed_paths,
    ):
        if not isinstance(paths, tuple) or not all(
            isinstance(path, str) and path.startswith("/") for path in paths
        ):
            return None
    if not context.mandatory_paths or not context.required_paths:
        return None
    if not set(context.mandatory_paths) <= set(context.required_paths):
        return None
    allowed = {
        "identity",
        "electrical",
        "pins",
        "package",
        "symbol",
        "footprint",
        "model_3d",
    }
    if any(
        path.split("/")[1] not in allowed
        and not path.startswith("/validation/tolerances/")
        for path in context.required_paths
    ):
        return None
    return context.required_paths


def revised_issues(data, for_generation, requirements):
    # Imported here to avoid a module initialization cycle.
    from partsmith.ir.model import _walk

    issues = []

    def add(path, code, message):
        issues.append(Issue(path, code, message))

    docs = {item["id"]: item for item in data["source"]["documents"]}
    identity = data["identity"]
    document = docs.get(identity["source_document_id"])
    if document is None or document["revision"] != identity["source_revision"]:
        add(
            "/identity/source_revision",
            "IR_IDENTITY",
            "Identity document and revision must agree",
        )
    for i, document in enumerate(data["source"]["documents"]):
        basis = document.get("revision_basis")
        if basis and (
            document["revision"] != "UNVERSIONED"
            or basis["sha256"] != document["sha256"]
        ):
            add(
                f"/source/documents/{i}/revision_basis",
                "IR_IDENTITY",
                "Unversioned basis must match the source hash",
            )

    records = {}
    paths = {}
    for domain in ("evidence", "standards", "overrides", "resolutions"):
        for i, record in enumerate(data[domain]):
            key = (domain, record["id"])
            if key in records and domain == "resolutions":
                add(
                    f"/{domain}/{i}/id",
                    "IR_DUPLICATE_ID",
                    "Duplicate record ID",
                )
            records[key] = record
            paths[key] = f"/{domain}/{i}"

    def references(node, path, owner=None):
        for location, item in _walk(node, path):
            for field, domain in (
                ("evidence_ids", "evidence"),
                ("selected_evidence_ids", "evidence"),
            ):
                for ref in item.get(field, []):
                    yield (domain, ref)
            for field, domain in (
                ("standard_id", "standards"),
                ("override_id", "overrides"),
                ("evidence_reference", "evidence"),
            ):
                ref = item.get(field)
                if ref is not None:
                    # A new value's override tag is its binding, not a
                    # recursive dependency on the containing override.
                    if (
                        owner == (domain, ref)
                        and location == path + "/new_value"
                    ):
                        continue
                    yield (domain, ref)

    graph = {}
    for key, record in records.items():
        path = paths[key]
        dependencies = set(references(record, path, key))
        # Previous override values are history, but their references still
        # must resolve structurally. They do not form active graph edges.
        if key[0] == "overrides":
            dependencies = set(
                references(record["new_value"], path + "/new_value")
            )
            dependencies.discard(key)
            dependencies.add(("evidence", record["evidence_reference"]))
        graph[key] = dependencies
        for dep in references(record, path, key):
            if dep not in records:
                add(
                    path,
                    "IR_REFERENCE",
                    "Provenance reference does not resolve",
                )
        if key[0] == "evidence" and "translation" in record:
            if (
                record["translation"]["original_text"]
                != record["extracted"]["text"]
            ):
                add(
                    path + "/translation/original_text",
                    "IR_PROVENANCE",
                    "Translation must retain the original source text",
                )

    # Iterative cycle check: large provenance chains do not exhaust recursion.
    colors = {}
    for start in graph:
        stack = [(start, False)]
        while stack:
            key, leaving = stack.pop()
            if key not in graph:
                continue
            if leaving:
                colors[key] = 2
            elif colors.get(key) == 1:
                add(paths[key], "IR_CYCLE", "Cyclic provenance dependency")
            elif colors.get(key) != 2:
                colors[key] = 1
                stack.append((key, True))
                stack.extend(
                    (dep, False) for dep in sorted(graph[key], reverse=True)
                )

    if data["schema_version"] == "1.2":
        # IR 1.2 shares source/reference checks but has versioned typed
        # overrides, active selectors, and external revision validation.
        return issues

    targets = {}
    for i, resolution in enumerate(data["resolutions"]):
        path = f"/resolutions/{i}"
        target_path = resolution["target_path"]
        selected = set(resolution["selected_evidence_ids"])
        old = set(resolution["superseded_evidence_ids"])
        if selected & old or any(
            ("evidence", ref) not in records for ref in old
        ):
            add(
                path, "IR_RESOLUTION", "Invalid superseded evidence references"
            )
        try:
            target = resolve_pointer(data, target_path)
            if not isinstance(target, dict) or not isinstance(
                target.get("status"), str
            ):
                raise ValueError
        except (KeyError, IndexError, ValueError):
            add(
                path + "/target_path",
                "IR_REFERENCE",
                "Resolution target does not resolve",
            )
            continue
        matches = selected == set(
            target.get("evidence_ids", [])
        ) and resolution["override_id"] == target.get("override_id")
        if resolution["approval_state"] == "APPROVED" or matches:
            if target_path in targets:
                add(
                    path,
                    "IR_RESOLUTION",
                    "Multiple approved resolutions for one target",
                )
            targets[target_path] = ("resolutions", resolution["id"])
            if not matches or (
                not selected and resolution["override_id"] is None
            ):
                add(
                    path,
                    "IR_RESOLUTION",
                    "Approved selection must match the current value",
                )

    for i, override in enumerate(data["overrides"]):
        try:
            target = resolve_pointer(data, override["path"])
            expected = "source_value" if "source_value" in target else "value"
            if expected not in target or any(
                expected not in override[field]
                for field in ("previous_value", "new_value")
            ):
                raise ValueError
        except (KeyError, IndexError, ValueError, TypeError):
            add(
                f"/overrides/{i}/path",
                "IR_OVERRIDE",
                "Override target/type must resolve",
            )

    if not for_generation:
        return issues
    required = _context_paths(requirements)
    if required is None:
        add(
            "",
            "IR_REQUIREMENTS",
            "A complete versioned requirements context is required",
        )
        return issues

    # Identity is always an active input. Remaining engineering roots come
    # from the adapter's mandatory declaration and requested superset.
    pending = [("/identity", identity)]
    for path in required:
        try:
            node = resolve_pointer(data, path)
            # A leaf request must not bypass the containing value's status
            # and provenance. Use the nearest enclosing engineering record.
            parent = path
            while parent:
                ancestor = resolve_pointer(data, parent)
                if isinstance(ancestor, dict) and isinstance(
                    ancestor.get("status"), str
                ):
                    path, node = parent, ancestor
                    break
                parent = parent.rpartition("/")[0]
            pending.append((path, node))
        except (KeyError, IndexError, ValueError):
            add(
                path, "IR_REQUIREMENTS", "Required input path does not resolve"
            )
    active = set()
    visited_paths = set()
    while pending:
        path, node = pending.pop()
        if path in visited_paths:
            continue
        visited_paths.add(path)
        if node is None:
            add(path, "IR_UNRESOLVED", "Required input is null")
        for location, item in _walk(node, path):
            status = item.get("status")
            if status in UNRESOLVED:
                add(location, "IR_UNRESOLVED", "Active input is unresolved")
            if "source_value" in item and (
                item["source_value"] is None or item["source_unit"] is None
            ):
                add(
                    location,
                    "IR_UNRESOLVED",
                    "Active quantity needs a value and unit",
                )
            if "value" in item and "status" in item and item["value"] is None:
                add(location, "IR_UNRESOLVED", "Active scalar value is null")
            if (
                location.startswith("/package/mechanical/")
                and "normalized_value" in item
                and (
                    item["normalized_value"] == 0
                    or item.get("normalized_min") == 0
                )
                and (
                    location not in requirements.zero_allowed_paths
                    or location.rsplit("/", 1)[-1]
                    in {"body_width", "body_length", "body_height"}
                )
            ):
                add(
                    location,
                    "IR_DIMENSION",
                    "Zero length requires a PDL optional-feature declaration",
                )
            # Evidence DIRECT is backed by its verified source document.
            evidence_interpretation = location.startswith(
                "/evidence/"
            ) and location.endswith("/interpretation")
            if (
                status == "DIRECT"
                and not evidence_interpretation
                and not item.get("evidence_ids")
            ):
                add(
                    location, "IR_PROVENANCE", "Direct value requires evidence"
                )
            if status == "DERIVED" and (
                not item.get("derivation") or not item.get("evidence_ids")
            ):
                add(
                    location,
                    "IR_PROVENANCE",
                    "Derived value requires derivation and inputs",
                )
            if status == "STANDARD" and not item.get("standard_id"):
                add(
                    location,
                    "IR_PROVENANCE",
                    "Standard value requires a versioned standard",
                )
            if status == "USER_OVERRIDE" or (
                status is not None and item.get("override_id") is not None
            ):
                override = records.get(("overrides", item.get("override_id")))
                if (
                    override is None
                    or override["approval_state"] != "APPROVED"
                    or (
                        location != override["path"]
                        and not location.startswith("/overrides/")
                    )
                    or item != override["new_value"]
                ):
                    add(
                        location,
                        "IR_OVERRIDE",
                        "Override must match approved target and new value",
                    )
            for target, key in targets.items():
                if location == target:
                    if records[key]["approval_state"] != "APPROVED":
                        add(
                            paths[key],
                            "IR_RESOLUTION",
                            "Active resolution requires approval",
                        )
                    active.add(key)
                    pending.append((paths[key], records[key]))
        for key in references(node, path):
            if key in active or key not in records:
                continue
            active.add(key)
            record = records[key]
            if key[0] == "overrides":
                if record["approval_state"] != "APPROVED":
                    add(
                        paths[key],
                        "IR_OVERRIDE",
                        "Active override must be approved",
                    )
                pending.append(
                    (paths[key] + "/new_value", record["new_value"])
                )
                evidence_key = ("evidence", record["evidence_reference"])
                if evidence_key in records:
                    pending.append(
                        (paths[evidence_key], records[evidence_key])
                    )
            else:
                pending.append((paths[key], record))
            if key[0] == "standards" and (
                record["revision"].upper() in UNRESOLVED | {"UNVERSIONED"}
                or not record["evidence_ids"]
            ):
                add(
                    paths[key],
                    "IR_PROVENANCE",
                    "Standard requires an edition and retained evidence",
                )
    return issues
