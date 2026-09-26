"""Trusted IR 1.2 editable paths and provenance ownership, registry 1.0."""

import re

from partsmith.ir.revised import resolve_pointer
from partsmith.ir.schema import load_schema

ENGINEERING = {
    "identity",
    "electrical",
    "pins",
    "package",
    "symbol",
    "footprint",
    "model_3d",
}


def engineering_path(path):
    return isinstance(path, str) and (
        path.split("/")[1:2] in [[key] for key in ENGINEERING]
        or path.startswith("/validation/tolerances/")
    )


def owner_path(data, path):
    """Resolve a leaf to its nearest provenance record; reject metadata."""
    if not engineering_path(path):
        raise ValueError("Not an engineering input")
    resolve_pointer(data, path)
    current = path
    while current:
        node = resolve_pointer(data, current)
        if isinstance(node, dict) and (
            "status" in node or "evidence_ids" in node
        ):
            return current
        current = current.rpartition("/")[0]
    return path


def overlaps(first, second):
    return (
        first == second
        or first.startswith(second + "/")
        or second.startswith(first + "/")
    )


def target_schema(path):
    """Return the exact target schema and closed payload kind, or reject."""
    schema = load_schema("1.2")
    definitions = schema["$defs"]
    kind = None
    token = r"(?:[^~/]|~[01])+"
    if re.fullmatch(rf"/(electrical|symbol/properties)/{token}", path):
        kind = "VALUE_RECORD"
    elif re.fullmatch(
        rf"/(package/mechanical|footprint/properties|validation/tolerances)/{token}",
        path,
    ):
        kind = "QUANTITY_RECORD"
    elif path == "/pins":
        kind = "PIN_ARRAY"
    elif re.fullmatch(r"/pins/(0|[1-9][0-9]*)", path):
        kind = "PIN_RECORD"
    elif re.fullmatch(
        r"/pins/(0|[1-9][0-9]*)/(number|name|electrical_type|function|physical/topology_side)",
        path,
    ):
        kind = "STRING"
    elif re.fullmatch(
        r"/pins/(0|[1-9][0-9]*)/(active_low|flags/(exposed_pad|no_connect))",
        path,
    ):
        kind = "BOOLEAN"
    elif re.fullmatch(r"/pins/(0|[1-9][0-9]*)/physical/topology_index", path):
        kind = "NUMBER"
    elif path == "/model_3d/placement":
        kind = "PLACEMENT_RECORD"
    elif re.fullmatch(
        r"/model_3d/placement/(translation_mm|rotation_deg|scale)", path
    ):
        kind = "VEC3"
    elif re.fullmatch(
        r"/model_3d/placement/(translation_mm|rotation_deg|scale)/[012]", path
    ):
        kind = "NUMBER"
    elif path == "/model_3d/placement/mirror":
        kind = "MIRROR_RECORD"
    elif re.fullmatch(r"/model_3d/placement/mirror/[xyz]", path):
        kind = "BOOLEAN"
    elif path == "/footprint/land_pattern_source":
        kind = "STRING"
    if kind is None:
        raise ValueError("Target is not in the editable registry")
    for token in path[1:].split("/"):
        while "$ref" in schema:
            schema = definitions[schema["$ref"].rsplit("/", 1)[1]]
        token = token.replace("~1", "/").replace("~0", "~")
        if schema.get("type") == "array":
            schema = schema["items"]
        else:
            schema = schema.get("properties", {}).get(
                token, schema.get("additionalProperties")
            )
        if not isinstance(schema, dict):
            raise ValueError("Target schema is not editable")
    return schema, kind


def effective_path(data, path, base_id, chain=None):
    """Follow retained, approved target rebindings in revision order."""
    if chain is None:
        return path  # External ancestry is checked at generation, not loading.
    order = [r["revision"]["id"] for r in chain]
    if base_id not in order:
        raise ValueError("Missing binding base")
    for key in order[order.index(base_id) :]:
        matches = [
            b
            for b in data["revision"]["target_rebindings"]
            if b["approval_state"] == "APPROVED"
            and b["base_revision_id"] == key
            and (path == b["old_path"] or path.startswith(b["old_path"] + "/"))
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous rebinding")
        if matches:
            item = matches[0]
            if item["new_path"] is None:
                return None
            path = item["new_path"] + path[len(item["old_path"]) :]
    return path
