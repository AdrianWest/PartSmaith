"""

@package src.partsmith.threed.step_backend
@brief CadQuery/OCP/OCCT STEP export, deterministic normalization,
and STEP parsing/measurement (sections 146/147).
@details Provides the module implementation and public interfaces.
"""

import re
import tempfile
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import cadquery as cq

from partsmith.threed.geometry import build_solids

CADQUERY_VERSION = cq.__version__
OCP_VERSION = version("cadquery-ocp")
STEP_EXPORT_SETTINGS = {
    "unit": "MM",
    "outputUnit": "MM",
    "write_pcurves": True,
    "precision_mode": 0,
}

_TIMESTAMP_PATTERN = re.compile(rb"'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'")
_FIXED_TIMESTAMP = b"'1970-01-01T00:00:00'"
_TRANSLATOR_PATTERN = re.compile(
    rb"(Open CASCADE STEP translator \d+\.\d+) \d+((?:\.\d+)*)"
)
_ASSEMBLY_OCCURRENCE_PATTERN = re.compile(
    rb"(NEXT_ASSEMBLY_USAGE_OCCURRENCE\(')\d+(')"
)
_LENGTH_UNIT_PATTERN = re.compile(
    rb"LENGTH_UNIT\(\)\s+NAMED_UNIT\(\*\)\s+"
    rb"SI_UNIT\((\.[A-Z]+\.|\$),\.METRE\.\)"
)
_SI_PREFIX_TO_MM = {
    b".EXA.": 1e21,
    b".PETA.": 1e18,
    b".TERA.": 1e15,
    b".GIGA.": 1e12,
    b".MEGA.": 1e9,
    b".KILO.": 1e6,
    b".HECTO.": 1e5,
    b".DECA.": 1e4,
    b".DECI.": 1e2,
    b".MILLI.": 1.0,
    b".CENTI.": 10.0,
    b".MICRO.": 1e-3,
    b".NANO.": 1e-6,
    b".PICO.": 1e-9,
    b".FEMTO.": 1e-12,
    b".ATTO.": 1e-15,
    b"$": 1000.0,
}


def _normalize_step_bytes(raw: bytes) -> bytes:
    """

    @brief Strip nondeterministic OCCT export metadata from raw STEP
    bytes.
    @param raw The raw exported STEP bytes.
    @return The bytes result.
    @details Replaces the FILE_NAME creation timestamp with a fixed
    constant, and renumbers the per-export PRODUCT translator counter
    and NEXT_ASSEMBLY_USAGE_OCCURRENCE ID in first-appearance order;
    all three are OCCT session-global export state, not geometry.

    """
    normalized = _TIMESTAMP_PATTERN.sub(_FIXED_TIMESTAMP, raw)

    translator_seen: dict[bytes, int] = {}

    def _renumber_translator(match: re.Match) -> bytes:
        """

        @brief Replace one translator counter match with its
        deterministic index.
        @param match The match argument.
        @return The bytes result.
        @details Implements the documented behavior without changing
        the public contract.

        """
        prefix = match.group(1)
        suffix = match.group(2)
        index = translator_seen.setdefault(prefix, len(translator_seen) + 1)
        return b"%s %d%s" % (prefix, index, suffix)

    normalized = _TRANSLATOR_PATTERN.sub(_renumber_translator, normalized)

    assembly_seen: dict[int, int] = {}

    def _renumber_assembly(match: re.Match) -> bytes:
        """

        @brief Replace one assembly-usage-occurrence ID with a
        deterministic sequential index.
        @param match The match argument.
        @return The bytes result.
        @details Implements the documented behavior without changing
        the public contract.

        """
        index = len(assembly_seen) + 1
        assembly_seen[match.start()] = index
        return b"%s%d%s" % (match.group(1), index, match.group(2))

    return _ASSEMBLY_OCCURRENCE_PATTERN.sub(_renumber_assembly, normalized)


def _export_raw_step(solids: list, *, precision_mode: int = 0) -> bytes:
    """

    @brief Export a list of solids as one compound STEP file.
    @param solids The solids argument.
    @return The bytes result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    compound = cq.Compound.makeCompound(solids)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "model.step"
        if type(precision_mode) is not int or precision_mode not in {-1, 0, 1}:
            raise ValueError("Unsupported STEP precision mode")
        settings = STEP_EXPORT_SETTINGS | {"precision_mode": precision_mode}
        compound.exportStep(str(path), **settings)
        return path.read_bytes()


def _count_solids(step_bytes: bytes) -> int:
    """

    @brief Reparse STEP bytes and count its solids.
    @param step_bytes The step_bytes argument.
    @return The int result.
    @details Implements the documented behavior without changing the
    public contract.

    """
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "verify.step"
        path.write_bytes(step_bytes)
        workplane = cq.importers.importStep(str(path))
        return len(workplane.solids().vals())


def generate_step_bytes(pdl_data: dict, *, precision_mode: int = 0) -> bytes:
    """

    @brief Deterministically generate a normalized STEP artifact.
    @param pdl_data The pdl_data argument.
    @return The bytes result.
    @details Builds the section 145 solids, exports STEP, normalizes
    away nondeterministic OCCT metadata, then reparses and remeasures
    the normalized bytes to confirm the solid count is unchanged
    before returning them; raises RuntimeError if normalization
    altered geometry.

    """
    solids = build_solids(pdl_data)
    raw = _export_raw_step(solids, precision_mode=precision_mode)
    normalized = _normalize_step_bytes(raw)
    measured_count = _count_solids(normalized)
    if measured_count != len(solids):
        raise RuntimeError(
            "STEP normalization altered solid count: expected "
            f"{len(solids)}, measured {measured_count}"
        )
    return normalized


def export_step_solids(solids: list) -> bytes:
    """@brief Deterministically export supplied solids as normalized STEP.
    @param solids CadQuery solids to export.
    @return Normalized STEP artifact bytes.
    @details Uses the production normalization and verifies the parsed solid
    count, allowing reproducible Phase 7 fault fixtures.
    """
    raw = _export_raw_step(solids)
    normalized = _normalize_step_bytes(raw)
    measured_count = _count_solids(normalized)
    if measured_count != len(solids):
        raise RuntimeError(
            "STEP normalization altered solid count: expected "
            f"{len(solids)}, measured {measured_count}"
        )
    return normalized


Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class SolidMeasurement:
    """@brief One measured solid's axis-aligned bounding box.
    @details center_mm and size_mm are both model-frame mm.
    """

    center_mm: Vec3
    size_mm: Vec3
    minimum_mm: Vec3 | None = None
    maximum_mm: Vec3 | None = None

    def __post_init__(self) -> None:
        """@brief Fill bounds omitted by Phase 6-compatible callers.
        @return None.
        @details Derives axis-aligned minimum and maximum points from the
        public center/size constructor when explicit bounds are absent.
        """
        if self.minimum_mm is None:
            object.__setattr__(
                self,
                "minimum_mm",
                tuple(
                    self.center_mm[axis] - self.size_mm[axis] / 2
                    for axis in range(3)
                ),
            )
        if self.maximum_mm is None:
            object.__setattr__(
                self,
                "maximum_mm",
                tuple(
                    self.center_mm[axis] + self.size_mm[axis] / 2
                    for axis in range(3)
                ),
            )


@dataclass(frozen=True)
class StepMeasurement:
    """@brief Parsed, measured contents of a STEP artifact.
    @details solids are in the order OCP/OCCT returns them; this is
    stable for a fixed input but is not itself a semantic contract.
    """

    solids: tuple[SolidMeasurement, ...]
    length_unit_mm: float = 1.0

    @property
    def solid_count(self) -> int:
        """

        @brief Return the number of measured solids.
        @return The int result.
        @details Implements the documented behavior without changing
        the public contract.

        """
        return len(self.solids)


def measure_step(step_bytes: bytes) -> StepMeasurement:
    """

    @brief Parse STEP bytes and measure each solid's bounding box.
    @param step_bytes The step_bytes argument.
    @return The StepMeasurement result.
    @details Raises ValueError when the STEP artifact parses to zero
    solids.

    """
    unit_matches = set(_LENGTH_UNIT_PATTERN.findall(step_bytes))
    if len(unit_matches) != 1:
        raise ValueError("STEP artifact has no unique SI length unit")
    prefix = unit_matches.pop()
    try:
        length_unit_mm = _SI_PREFIX_TO_MM[prefix]
    except KeyError as error:
        raise ValueError(
            f"Unsupported STEP SI length-unit prefix: {prefix.decode()}"
        ) from error

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "measure.step"
        path.write_bytes(step_bytes)
        workplane = cq.importers.importStep(str(path))
        solids = workplane.solids().vals()
    if not solids:
        raise ValueError("STEP artifact contains no solids")
    measurements = []
    for solid in solids:
        box = solid.BoundingBox()
        center = (
            (box.xmin + box.xmax) / 2.0,
            (box.ymin + box.ymax) / 2.0,
            (box.zmin + box.zmax) / 2.0,
        )
        size = (box.xlen, box.ylen, box.zlen)
        minimum = (box.xmin, box.ymin, box.zmin)
        maximum = (box.xmax, box.ymax, box.zmax)
        measurements.append(SolidMeasurement(center, size, minimum, maximum))
    return StepMeasurement(tuple(measurements), length_unit_mm)
