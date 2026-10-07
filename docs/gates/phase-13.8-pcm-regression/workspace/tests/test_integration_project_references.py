"""@package tests.test_integration_project_references
@brief Refuses project references to removed managed symbols and models.
@details Tests bounded native trees against actual approved source mappings.
"""

import pytest
from phase13_support import TARGET
from phase13_support import approved_database as approved_database
from phase13_support import approved_sources as approved_sources

from partsmith.integration.errors import IntegrationError
from partsmith.integration.planner import Planner
from partsmith.integration.staging import planned_files, whole_generation


@pytest.mark.parametrize("kind", ["symbol", "footprint", "model"])
def test_removed_managed_reference_is_blocked(
    approved_database, tmp_path, kind
):
    """@brief Rejects references whose managed entry is absent from the plan.
    @param approved_database Actual approved source fixture.
    @param tmp_path Ordinary project directory.
    @param kind Native cached symbol, board footprint or STEP URI reference.
    @return None.
    @details No target or source bytes are rewritten to satisfy a removal.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    node = {
        "symbol": '(lib_id "BFT_Symbols:removed")',
        "footprint": '(footprint "BFT_Footprints:removed")',
        "model": '(model "${KIPRJMOD}/BFT_3DSTEP/removed.step")',
    }[kind]
    design = root / (
        "board.kicad_sch" if kind == "symbol" else "board.kicad_pcb"
    )
    blob = ("(design " + node + ")\n").encode()
    design.write_bytes(blob)
    planning = Planner(connection).plan(root, TARGET, builds[:2])
    objects = planned_files(planning, planning.sources)
    with pytest.raises(IntegrationError, match="SEMANTIC_CHECK_FAILED"):
        whole_generation(planning, objects)
    assert design.read_bytes() == blob


def test_valid_references_and_unrelated_text_are_retained(
    approved_database, tmp_path
):
    """@brief Preserves valid instances, user text and external libraries.
    @param approved_database Actual approved source fixture.
    @param tmp_path Ordinary project root.
    @return None.
    @details Reserved-looking free text is not treated as a library reference.
    """
    connection, builds = approved_database
    root = tmp_path / "project"
    root.mkdir()
    first = Planner(connection).plan(root, TARGET, builds[:2])
    mapping = first.plan.data["mappings"][0]
    blob = (
        '(design (text "BFT_Symbols:free user text") '
        '(footprint "Other:External") '
        '(footprint "BFT_Footprints:' + mapping["footprint_name"] + '" '
        '(model "${KIPRJMOD}/' + mapping["model_path"] + '")))\n'
    ).encode()
    (root / "board.kicad_pcb").write_bytes(blob)
    planning = Planner(connection).plan(root, TARGET, builds[:2])
    objects = planned_files(planning, planning.sources)
    assert whole_generation(planning, objects)[0]["board.kicad_pcb"] == blob
