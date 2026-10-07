"""@package partsmith.integration.native_stage
@brief Verifies native project-relative STEP resolution in disposable boards.
@details Diagnostic boards/exports never become replacement library artifacts.
Exact model solids and volume verify the native exporter loaded every source.
"""

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy
from partsmith.integration.sexpr import Atom, children, parse, serialize
from partsmith.process import run_process


def quiet(message: str) -> None:
    """@brief Keeps supervised CLI text outside deterministic reports.
    @param message Bounded native transport text.
    @return None.
    @details Command status and CAD readback determine the actual outcome.
    """


def symbol_pin_records(library: list) -> dict:
    """@brief Reads engineering pin fields independent of native formatting.
    @param library Bounded parsed packed symbol library.
    @return Entry names mapped to complete sorted pin engineering records.
    @details Native defaults and grouping do not waive changed pin semantics.
    """
    entries = {}

    def visit(tree, unit=(1, 1)):
        """@brief Collects all pins with their unit and body-style association.
        @param tree Current symbol subtree.
        @param unit Default unit and representation for directly defined pins.
        @return Complete pin engineering tuples.
        @details Decimal equality tolerates numeric spelling only.
        """
        records = []
        for node in tree:
            if not isinstance(node, list):
                continue
            if node[0] == "symbol":
                suffix = node[1].rsplit("_", 2)
                records.extend(visit(node, tuple(map(int, suffix[-2:]))))
            elif node[0] == "pin":
                records.append(
                    (
                        unit,
                        node[1],
                        node[2],
                        children(node, "name")[0][1],
                        children(node, "number")[0][1],
                        tuple(Decimal(v) for v in children(node, "at")[0][1:]),
                        Decimal(children(node, "length")[0][1]),
                    )
                )
        return records

    for symbol in children(library, "symbol"):
        entries[symbol[1]] = sorted(visit(symbol), key=str)
    return entries


def board_tree(footprints: list[list]) -> list:
    """@brief Builds an explicitly disposable native model-resolution board.
    @param footprints Exact installed footprint trees copied for instances.
    @return Complete native KiCad board tree.
    @details Only diagnostic instance fields are added; library trees stay
    unchanged. The native export excludes the diagnostic board body.
    """
    board = parse(b"""(kicad_pcb (version 20250114) (generator "pcbnew")
      (general (thickness 1.6)) (paper "A4")
      (layers (0 "F.Cu" signal) (31 "B.Cu" signal)
        (35 "F.Paste" user) (37 "F.SilkS" user) (39 "F.Mask" user)
        (44 "Edge.Cuts" user) (47 "F.CrtYd" user) (49 "F.Fab" user))
      (setup (pad_to_mask_clearance 0)) (net 0 "")
      (gr_rect (start 95 95) (end 105 105)
        (stroke (width 0.05) (type default)) (fill none)
        (layer "Edge.Cuts")))""")
    for index, original in enumerate(footprints):
        footprint = deepcopy(original)
        footprint[1] = "BFT_Footprints:" + footprint[1]
        footprint = [
            node
            for node in footprint
            if not (
                isinstance(node, list) and node[0] in {"version", "generator"}
            )
        ]
        footprint.extend(
            [
                [Atom("layer"), "F.Cu"],
                [Atom("at"), Atom(str(98 + index * 2)), Atom("100")],
                [Atom("attr"), Atom("smd")],
            ]
        )
        for field in children(footprint, "fp_text"):
            if field[1] == "reference":
                field[2] = f"R{index + 1}"
        board.append(footprint)
    return board


def native_model_check(root: Path, output: Path, executable: Path) -> dict:
    """@brief Exports a disposable board and verifies every unchanged STEP.
    @param root Exact complete staged generation.
    @param output Owned diagnostic output directory outside the stage.
    @param executable Pinned verified KiCad CLI executable.
    @return Operational receipt with native CAD solid and volume readback.
    @details KIPRJMOD resolves from the copied diagnostic project. Missing
    models cannot pass through a CLI warning: solids/volume must match sources.
    """
    import cadquery

    diagnostic = output / "project"
    diagnostic.mkdir()
    footprints = []
    expected_solids, expected_volume = 0, Decimal("0")
    for path in sorted((root / "BFT_Footprints.pretty").glob("*.kicad_mod")):
        tree = parse(path.read_bytes())
        model = children(tree, "model")[0]
        relative = model[1].removeprefix("${KIPRJMOD}/")
        if relative == model[1]:
            raise IntegrationError(FailureCode.PATH_CONFLICT)
        source = root / relative
        blob = source.read_bytes()
        destination = diagnostic / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(blob)
        shape = cadquery.importers.importStep(str(source)).val()
        expected_solids += len(shape.Solids())
        scale = children(children(model, "scale")[0], "xyz")[0][1:]
        factor = abs(Decimal(scale[0]) * Decimal(scale[1]) * Decimal(scale[2]))
        expected_volume += Decimal(str(shape.Volume())) * factor
        footprints.append(tree)
    board = diagnostic / "native-models.kicad_pcb"
    board.write_bytes(serialize(board_tree(footprints)))
    board.with_suffix(".kicad_pro").write_bytes(b"{}")
    exported = output / "native-board.step"
    result = run_process(
        [
            str(executable),
            "pcb",
            "export",
            "step",
            "--no-board-body",
            "--force",
            "--output",
            str(exported),
            str(board),
        ],
        log=quiet,
        cwd=diagnostic,
        timeout=ResourcePolicy().native_timeout_seconds,
        output_budget=ResourcePolicy().log_bytes,
    )
    if result.returncode or not exported.is_file():
        raise IntegrationError(FailureCode.NATIVE_CHECK_FAILED)
    ResourcePolicy().require_sizes([exported.stat().st_size])
    shape = cadquery.importers.importStep(str(exported)).val()
    observed_solids = len(shape.Solids())
    observed_volume = Decimal(str(shape.Volume()))
    if observed_solids != expected_solids or abs(
        observed_volume - expected_volume
    ) > Decimal("0.00001"):
        raise IntegrationError(FailureCode.NATIVE_CHECK_FAILED)
    return {
        "operation": "pcb-export-step",
        "exit_code": 0,
        "expected_solids": expected_solids,
        "observed_solids": observed_solids,
        "expected_volume_mm3": str(expected_volume),
        "observed_volume_mm3": str(observed_volume),
        "tolerance_mm3": "0.00001",
    }
