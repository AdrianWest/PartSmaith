"""Versioned Component IR loading, normalization, validation, and hashing."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

from partsmith.ir.canonical import canonical_json, normalize_json, parse_json
from partsmith.ir.errors import IRValidationError, Issue, fail, pointer
from partsmith.ir.schema import schema_issues
from partsmith.ir.units import normalize_quantity

UNRESOLVED = {"UNKNOWN", "INFERRED", "AMBIGUOUS", "CONFLICTING", "MISSING"}
_PROPERTY_MAPS = {
    "/electrical",
    "/package/mechanical",
    "/symbol/properties",
    "/footprint/properties",
    "/validation/tolerances",
}


def _walk(value, path=""):
    if isinstance(value, dict):
        # Map keys are engineering names, not record fields. A property
        # named "status" or "source_unit" must not impersonate metadata.
        if path not in _PROPERTY_MAPS:
            yield path, value
        for key, child in value.items():
            yield from _walk(child, pointer(path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, pointer(path, index))


def _portable_path(value: str, path: str) -> str:
    value = value.replace("\\", "/")
    parts = value.split("/")
    if value.startswith("/") or ":" in value or ".." in parts:
        fail(path, "IR_PATH", "Expected a portable relative logical path")
    result = str(PurePosixPath(value))
    if result == ".":
        fail(path, "IR_PATH", "Expected a nonempty file path")
    return result


def normalize_ir(
    data: dict,
    *,
    for_generation: bool = False,
    requirements=None,
    revisions=None,
) -> dict:
    """Return a validated copy. Candidate statuses remain explicit.

    for_generation blocks unresolved provenance, but does not certify PDL,
    geometry, KiCad compatibility, or grant IR_VALIDATED/APPROVED state.
    """
    result = normalize_json(data)
    issues = schema_issues(result)
    if issues:
        raise IRValidationError(issues)
    revised = result["schema_version"] in {"1.1", "1.2"}
    for index, document in enumerate(result["source"]["documents"]):
        document["path"] = _portable_path(
            document["path"], f"/source/documents/{index}/path"
        )
    for path, item in _walk(result):
        if "source_unit" not in item:
            continue
        if revised and (
            item["source_value"] is None or item["source_unit"] is None
        ):
            item["normalized_value"] = None
            item["normalized_unit"] = None
            continue
        for source, target in (
            ("source_value", "normalized_value"),
            ("source_min", "normalized_min"),
            ("source_max", "normalized_max"),
        ):
            if source not in item:
                if target in item:
                    fail(
                        path,
                        "IR_DIMENSION",
                        "Normalized bound has no source bound",
                    )
                continue
            value, unit = normalize_quantity(item[source], item["source_unit"])
            if target in item and item[target] != value:
                fail(
                    pointer(path, target),
                    "IR_UNIT",
                    "Normalized value contradicts source",
                )
            if "normalized_unit" in item and item["normalized_unit"] != unit:
                fail(
                    pointer(path, "normalized_unit"),
                    "IR_UNIT",
                    "Normalized unit contradicts source",
                )
            item[target] = value
            item["normalized_unit"] = unit
        if (
            "source_min" in item
            and not item["source_min"]
            <= item["source_value"]
            <= item["source_max"]
        ):
            fail(
                path, "IR_DIMENSION", "Expected minimum <= nominal <= maximum"
            )
    issues = schema_issues(result) + _semantic_issues(
        result, for_generation and not revised
    )
    if result["schema_version"] == "1.2":
        from partsmith.ir.contract import contract_issues

        issues += contract_issues(
            result, for_generation, requirements, revisions
        )
    elif revised:
        from partsmith.ir.revised import revised_issues

        issues += revised_issues(result, for_generation, requirements)
    if issues:
        raise IRValidationError(issues)
    return result


def _semantic_issues(data, for_generation):
    issues = []

    def add(path, code, message):
        issues.append(Issue(path, code, message))

    def index(records, path):
        result = {}
        for i, record in enumerate(records):
            if record["id"] in result:
                add(f"{path}/{i}/id", "IR_DUPLICATE_ID", "Duplicate record ID")
            result[record["id"]] = record
        return result

    documents = index(data["source"]["documents"], "/source/documents")
    evidence = index(data["evidence"], "/evidence")
    standards = index(data["standards"], "/standards")
    overrides = index(data["overrides"], "/overrides")
    for i, item in enumerate(data["evidence"]):
        document = documents.get(item["source"]["document_id"])
        if (
            document is None
            or document["sha256"] != item["source"]["document_hash"]
        ):
            add(
                f"/evidence/{i}/source",
                "IR_REFERENCE",
                "Source document/hash does not resolve",
            )
    for path, item in _walk(data):
        for evidence_id in item.get("evidence_ids", []):
            if evidence_id not in evidence:
                add(
                    path, "IR_REFERENCE", "Evidence reference does not resolve"
                )
        if "standard_id" in item and item["standard_id"] not in standards:
            add(path, "IR_REFERENCE", "Standard reference does not resolve")
        if (
            item.get("override_id") is not None
            and item["override_id"] not in overrides
        ):
            add(path, "IR_REFERENCE", "Override reference does not resolve")
        if not for_generation:
            continue
        status = item.get("status")
        if status in UNRESOLVED:
            add(
                path,
                "IR_UNRESOLVED",
                "Unresolved evidence cannot enter generation",
            )
        if (
            "value" in item
            and item["value"] is None
            and "evidence_ids" in item
        ):
            add(
                path,
                "IR_UNRESOLVED",
                "Null engineering value cannot enter generation",
            )
        if "evidence_ids" not in item or status is None:
            continue
        if status in {"DIRECT", "DERIVED"} and not item["evidence_ids"]:
            add(path, "IR_PROVENANCE", "Engineering value requires evidence")
        if status == "DERIVED" and not item.get("derivation"):
            add(path, "IR_PROVENANCE", "Derived value requires a derivation")
        if status == "STANDARD" and item.get("standard_id") not in standards:
            add(
                path,
                "IR_PROVENANCE",
                "Standard value requires a standard reference",
            )
        if status == "USER_OVERRIDE":
            override = overrides.get(item.get("override_id"))
            if override is None or override["approval_state"] != "APPROVED":
                add(
                    path,
                    "IR_PROVENANCE",
                    "User value requires an approved override",
                )
    for i, override in enumerate(data["overrides"]):
        if override["evidence_reference"] not in evidence:
            add(
                f"/overrides/{i}",
                "IR_REFERENCE",
                "Override evidence does not resolve",
            )
        if for_generation and override["approval_state"] != "APPROVED":
            add(f"/overrides/{i}", "IR_UNRESOLVED", "Override is not approved")

    numbers = set()
    positions = set()
    for i, pin in enumerate(data["pins"]):
        if pin["number"] in numbers:
            add(
                f"/pins/{i}/number", "IR_PIN_DUPLICATE", "Duplicate pin number"
            )
        numbers.add(pin["number"])
        position = (
            pin["physical"]["topology_side"],
            pin["physical"]["topology_index"],
        )
        if position in positions:
            add(
                f"/pins/{i}/physical",
                "IR_TOPOLOGY",
                "Duplicate physical pin position",
            )
        positions.add(position)
    package = data["package"]
    if package["pin_count"] != len(data["pins"]):
        add(
            "/package/pin_count",
            "IR_TOPOLOGY",
            "Pin count disagrees with pin records",
        )
    if package["variant"] != data["identity"]["package_variant"]:
        add("/package/variant", "IR_IDENTITY", "Package variants disagree")
    for name, dimension in package["mechanical"].items():
        if dimension["normalized_value"] is None:
            continue
        if dimension["normalized_unit"] != "mm":
            add(
                f"/package/mechanical/{name}",
                "IR_UNIT",
                "Mechanical lengths must use mm",
            )
        if (
            dimension["normalized_value"] < 0
            or dimension.get("normalized_min", 1) < 0
            or (
                data["schema_version"] == "1.0"
                and (
                    dimension["normalized_value"] == 0
                    or dimension.get("normalized_min", 1) == 0
                )
            )
        ):
            add(
                f"/package/mechanical/{name}",
                "IR_DIMENSION",
                "Mechanical lengths must be positive",
            )
    for domain in ("footprint", "validation"):
        field = "properties" if domain == "footprint" else "tolerances"
        for name, quantity in data[domain][field].items():
            if (
                quantity["normalized_value"] is not None
                and quantity["normalized_value"] < 0
            ):
                add(
                    f"/{domain}/{field}/{name}",
                    "IR_DIMENSION",
                    "Distances/tolerances cannot be negative",
                )
    transform = data["model_3d"]["placement"]
    if any(scale <= 0 for scale in transform["scale"]):
        add(
            "/model_3d/placement/scale",
            "IR_TRANSFORM",
            "Scale must be positive; use explicit mirror flags",
        )
    return issues


def validate_ir(
    data: dict,
    *,
    for_generation: bool = False,
    requirements=None,
    revisions=None,
) -> tuple[Issue, ...]:
    """Return stable diagnostics without promoting review/build state."""
    try:
        normalize_ir(
            data,
            for_generation=for_generation,
            requirements=requirements,
            revisions=revisions,
        )
    except IRValidationError as error:
        return error.issues
    return ()


def canonical_ir(data: dict) -> bytes:
    return canonical_json(normalize_ir(data))


def ir_hash(data: dict) -> str:
    return sha256(canonical_ir(data)).hexdigest()


@dataclass(frozen=True, init=False)
class ComponentIR:
    """Immutable normalized IR; data access returns a detached JSON tree."""

    canonical_bytes: bytes

    def __init__(self, data: dict):
        object.__setattr__(self, "canonical_bytes", canonical_ir(data))

    @classmethod
    def from_json(cls, text: str | bytes) -> "ComponentIR":
        return cls(parse_json(text))

    @classmethod
    def from_file(cls, path: str | Path) -> "ComponentIR":
        return cls.from_json(Path(path).read_bytes())

    @property
    def data(self) -> dict:
        return parse_json(self.canonical_bytes)

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()
