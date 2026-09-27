"""Immutable PDL loading, canonicalization, hashing, and validation."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from partsmith.ir.canonical import canonical_json, normalize_json, parse_json
from partsmith.ir.errors import Issue
from partsmith.pdl.errors import PDLValidationError
from partsmith.pdl.profiles import load_release_profile, release_profile_hash
from partsmith.pdl.schema import schema_issues


def pdl_hash(data: dict) -> str:
    """Hash canonical PDL content without its self-declared hash field."""
    content = normalize_json(data)
    content.pop("content_sha256", None)
    return sha256(canonical_json(content)).hexdigest()


def _semantic_issues(data: dict) -> list[Issue]:
    issues = []

    def add(path: str, code: str, message: str) -> None:
        issues.append(Issue(path, code, message))

    identity = data["identity"]
    terminals = data["topology"]["terminals"]
    groups = data["land_pattern"]["groups"]
    expected = (
        identity["peripheral_lead_count"] + identity["exposed_terminal_count"]
    )
    if identity["pin_count"] != expected:
        add(
            "/identity/pin_count",
            "PDL_TOPOLOGY",
            "Pin count must equal peripheral plus exposed terminals",
        )
    if identity["pin_count"] != len(terminals):
        add(
            "/topology/terminals",
            "PDL_TOPOLOGY",
            "Terminal records must match pin count",
        )

    terminal_ids = [item["id"] for item in terminals]
    terminal_numbers = [item["number"] for item in terminals]
    if len(set(terminal_ids)) != len(terminal_ids):
        add("/topology/terminals", "PDL_DUPLICATE_ID", "Duplicate terminal ID")
    if len(set(terminal_numbers)) != len(terminal_numbers):
        add(
            "/topology/terminals",
            "PDL_TOPOLOGY",
            "Different terminals cannot share a number",
        )
    peripheral = sum(item["kind"] == "PERIPHERAL" for item in terminals)
    exposed = sum(item["kind"] == "EXPOSED" for item in terminals)
    if peripheral != identity["peripheral_lead_count"]:
        add(
            "/identity/peripheral_lead_count",
            "PDL_TOPOLOGY",
            "Peripheral count disagrees with terminal map",
        )
    if exposed != identity["exposed_terminal_count"]:
        add(
            "/identity/exposed_terminal_count",
            "PDL_TOPOLOGY",
            "Exposed count disagrees with terminal map",
        )

    side_counts = {
        side: sum(item["side"] == side for item in terminals)
        for side in ("north", "east", "south", "west", "center")
    }
    if data["topology"]["sides"] != side_counts:
        add(
            "/topology/sides",
            "PDL_TOPOLOGY",
            "Side counts disagree with terminal map",
        )

    topology = data["topology"]
    if len(terminals) > 1 and topology["pitch_mm"] is None:
        add(
            "/topology/pitch_mm",
            "PDL_TOPOLOGY",
            "Multi-terminal packages require a pitch",
        )
    pin1 = next((item for item in terminals if item["number"] == "1"), None)
    pin1_location = topology["pin1_location"].lower()
    if pin1 is not None and pin1_location in side_counts:
        if pin1_location != pin1["side"]:
            add(
                "/topology/pin1_location",
                "PDL_TOPOLOGY",
                "Pin-1 location disagrees with terminal 1 side",
            )
    if topology["numbering"] == "LINEAR":
        numeric_numbers = [
            int(item["number"])
            for item in terminals
            if item["number"].isdigit()
        ]
        if len(numeric_numbers) == len(
            terminals
        ) and numeric_numbers != sorted(numeric_numbers):
            add(
                "/topology/terminals",
                "PDL_TOPOLOGY",
                "Linear terminal numbering must be ascending",
            )
    if not topology["stagger"]:
        slots = [(item["side"], item["topology_index"]) for item in terminals]
        if len(set(slots)) != len(slots):
            add(
                "/topology/terminals",
                "PDL_TOPOLOGY",
                "Non-staggered terminals cannot share a side/index slot",
            )

    group_ids = [item["id"] for item in groups]
    group_numbers = [item["terminal_number"] for item in groups]
    if len(set(group_ids)) != len(group_ids):
        add("/land_pattern/groups", "PDL_DUPLICATE_ID", "Duplicate group ID")
    if sorted(group_numbers) != sorted(terminal_numbers):
        add(
            "/land_pattern/groups",
            "PDL_TOPOLOGY",
            "Each terminal requires exactly one conductive pad group",
        )
    terminal_groups = {item["number"]: item["group_id"] for item in terminals}
    for index, group in enumerate(groups):
        if terminal_groups.get(group["terminal_number"]) != group["id"]:
            add(
                f"/land_pattern/groups/{index}",
                "PDL_TOPOLOGY",
                "Terminal and pad group bindings disagree",
            )
    shape_ids = [shape["id"] for group in groups for shape in group["shapes"]]
    if len(set(shape_ids)) != len(shape_ids):
        add(
            "/land_pattern/groups",
            "PDL_DUPLICATE_ID",
            "Pad shape IDs must be globally unique",
        )

    terminal_id_set = set(terminal_ids)
    for index, symmetry in enumerate(data["allowed_symmetries"]):
        matrix = symmetry["matrix"]
        if matrix[3] != [0, 0, 0, 1]:
            add(
                f"/allowed_symmetries/{index}/matrix",
                "PDL_TOPOLOGY",
                "Symmetry matrix must be affine",
            )
        if any(matrix[row][3] != 0 for row in range(3)):
            add(
                f"/allowed_symmetries/{index}/matrix",
                "PDL_TOPOLOGY",
                "Symmetry matrix cannot translate the package reference "
                "center",
            )
        determinant = (
            matrix[0][0]
            * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
            - matrix[0][1]
            * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
            + matrix[0][2]
            * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
        )
        if abs(determinant) != 1:
            add(
                f"/allowed_symmetries/{index}/matrix",
                "PDL_TOPOLOGY",
                "Symmetry matrix must preserve or mirror scale",
            )
        for row in range(3):
            if sum(matrix[row][column] ** 2 for column in range(3)) != 1:
                add(
                    f"/allowed_symmetries/{index}/matrix",
                    "PDL_TOPOLOGY",
                    "Symmetry matrix rows must preserve length",
                )
        for first in range(3):
            for second in range(first + 1, 3):
                if (
                    sum(
                        matrix[first][column] * matrix[second][column]
                        for column in range(3)
                    )
                    != 0
                ):
                    add(
                        f"/allowed_symmetries/{index}/matrix",
                        "PDL_TOPOLOGY",
                        "Symmetry matrix rows must be orthogonal",
                    )
        if set(symmetry["terminal_mapping"]) != terminal_id_set:
            add(
                f"/allowed_symmetries/{index}/terminal_mapping",
                "PDL_TOPOLOGY",
                "Symmetry mapping must cover every terminal",
            )

    source_ids = {item["id"] for item in data["sources"]}
    if len(source_ids) != len(data["sources"]):
        add("/sources", "PDL_DUPLICATE_ID", "Duplicate source ID")
    for domain in ("body", "terminal"):
        for name, dimension in data["mechanical"][domain].items():
            if not (
                dimension["minimum_mm"]
                <= dimension["nominal_mm"]
                <= dimension["maximum_mm"]
            ):
                add(
                    f"/mechanical/{domain}/{name}",
                    "PDL_DIMENSION",
                    "Expected minimum <= nominal <= maximum",
                )
            if not set(dimension["source_ids"]) <= source_ids:
                add(
                    f"/mechanical/{domain}/{name}/source_ids",
                    "PDL_REFERENCE",
                    "Dimension source does not resolve",
                )
    for index, change in enumerate(data["change_history"]):
        if not set(change["source_ids"]) <= source_ids:
            add(
                f"/change_history/{index}/source_ids",
                "PDL_REFERENCE",
                "Change-history source does not resolve",
            )
    if data["change_history"][-1]["revision"] != data["revision"]:
        add(
            "/change_history",
            "PDL_REVISION",
            "Latest history record must describe this revision",
        )

    feature_ids = [item["id"] for item in data["reference_features"]]
    if len(set(feature_ids)) != len(feature_ids):
        add(
            "/reference_features",
            "PDL_DUPLICATE_ID",
            "Duplicate reference feature ID",
        )
    features_by_id = {item["id"]: item for item in data["reference_features"]}
    for index, feature in enumerate(data["reference_features"]):
        if (
            feature["terminal_id"] is not None
            and feature["terminal_id"] not in terminal_ids
        ):
            add(
                f"/reference_features/{index}/terminal_id",
                "PDL_REFERENCE",
                "Reference feature terminal does not resolve",
            )

    terminal_id_set = set(terminal_ids)
    symmetry_ids = [item["id"] for item in data["allowed_symmetries"]]
    if len(set(symmetry_ids)) != len(symmetry_ids):
        add("/allowed_symmetries", "PDL_DUPLICATE_ID", "Duplicate symmetry ID")
    for index, symmetry in enumerate(data["allowed_symmetries"]):
        mapping = symmetry["terminal_mapping"]
        if set(mapping) != terminal_id_set or sorted(
            mapping.values()
        ) != sorted(terminal_id_set):
            add(
                f"/allowed_symmetries/{index}/terminal_mapping",
                "PDL_TOPOLOGY",
                "Symmetry mapping must be a complete terminal bijection",
            )

    tolerance_ids = set(data["validation"]["tolerances"])
    observable_ids = set()
    for index, observable in enumerate(data["required_observables"]):
        if observable["id"] in observable_ids:
            add(
                f"/required_observables/{index}/id",
                "PDL_DUPLICATE_ID",
                "Duplicate observable ID",
            )
        observable_ids.add(observable["id"])
        feature = features_by_id.get(observable["feature_id"])
        if feature is None:
            add(
                f"/required_observables/{index}/feature_id",
                "PDL_REFERENCE",
                "Observable feature does not resolve",
            )
        elif feature["applicability"] == "ABSENT":
            add(
                f"/required_observables/{index}/feature_id",
                "PDL_TOPOLOGY",
                "Observable cannot reference an absent feature",
            )
        elif (
            observable["measurement_mode"] == "MEASURED"
            and feature["representation"] == "DECLARED_ONLY"
        ):
            add(
                f"/required_observables/{index}/measurement_mode",
                "PDL_TOPOLOGY",
                "Measured observable requires a measured feature",
            )
        if observable["tolerance_id"] not in tolerance_ids:
            add(
                f"/required_observables/{index}/tolerance_id",
                "PDL_REFERENCE",
                "Observable tolerance does not resolve",
            )

    if data["content_sha256"] != pdl_hash(data):
        add(
            "/content_sha256",
            "PDL_HASH",
            "Declared content hash does not match canonical PDL content",
        )
    return issues


def normalize_pdl(data: dict) -> dict:
    """Return a validated normalized PDL copy."""
    result = normalize_json(data)
    issues = schema_issues(result)
    if not issues:
        issues.extend(_semantic_issues(result))
        profile_ref = result["release_profile"]
        try:
            profile = load_release_profile(
                profile_ref["id"], profile_ref["version"]
            )
            if release_profile_hash(profile) != profile_ref["sha256"]:
                issues.append(
                    Issue(
                        "/release_profile/sha256",
                        "PDL_PROFILE",
                        "Release profile hash does not match",
                    )
                )
            if result["identity"]["variant"] not in {
                profile["bootstrap_variant"],
                *profile["production_variants"],
            }:
                issues.append(
                    Issue(
                        "/identity/variant",
                        "PDL_PROFILE",
                        "Package variant is outside the release profile",
                    )
                )
        except PDLValidationError as error:
            issues.extend(error.issues)
    if issues:
        raise PDLValidationError(issues)
    return result


def validate_pdl(data: dict) -> tuple[Issue, ...]:
    """Return stable diagnostics for one PDL entry."""
    try:
        normalize_pdl(data)
    except PDLValidationError as error:
        return error.issues
    return ()


def canonical_pdl(data: dict) -> bytes:
    """Return canonical bytes including the verified declared hash."""
    return canonical_json(normalize_pdl(data))


@dataclass(frozen=True, init=False)
class PDL:
    """Immutable normalized PDL; data access returns a detached tree."""

    canonical_bytes: bytes

    def __init__(self, data: dict):
        object.__setattr__(self, "canonical_bytes", canonical_pdl(data))

    @classmethod
    def from_json(cls, text: str | bytes) -> "PDL":
        return cls(parse_json(text))

    @classmethod
    def from_file(cls, path: str | Path) -> "PDL":
        return cls.from_json(Path(path).read_bytes())

    @property
    def data(self) -> dict:
        return parse_json(self.canonical_bytes)

    @property
    def sha256(self) -> str:
        return self.data["content_sha256"]
