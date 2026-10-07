"""@package tests.test_instance_semantics
@brief Tests instance comparison mismatch categories against approved sources.
@details Synthetic instance observations test the comparator, not live IPC.
"""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from phase13_support import TARGET
from phase13_support import approved_database as approved_database
from phase13_support import approved_sources as approved_sources

from partsmith.integration.instance_semantics import compare_instances
from partsmith.integration.ipc import (
    BoardInspection,
    FootprintInspection,
    ModelInspection,
    PadInspection,
)
from partsmith.integration.planner import Planner
from partsmith.integration.sexpr import children
from partsmith.integration.staging import relocated


@pytest.mark.parametrize("failure", [None, "pad", "model", "side", "missing"])
def test_actual_instance_comparison(approved_database, tmp_path, failure):
    """@brief Detects changed geometry, placement and missing instances.
    @param approved_database Real native approved source releases.
    @param tmp_path Disposable planning project.
    @param failure Explicit synthetic observation mutation.
    @return None.
    @details Source bytes are real, while observations are labeled test data.
    """
    connection, builds = approved_database
    planning = Planner(connection).plan(tmp_path, TARGET, builds[:2])
    instances = []
    for index, (source, mapping) in enumerate(
        zip(planning.sources, planning.plan.data["mappings"], strict=True)
    ):
        _, tree = relocated(source, mapping)
        pads = []
        for node in children(tree, "pad"):
            at = children(node, "at")[0]
            pads.append(
                PadInspection(
                    node[1], str(10 + float(at[1])), str(-20 - float(at[2]))
                )
            )
        models = []
        for node in children(tree, "model"):
            values = [
                tuple(children(children(node, tag)[0], "xyz")[0][1:])
                for tag in ("offset", "rotate", "scale")
            ]
            models.append(ModelInspection(node[1], *values, True))
        instances.append(
            FootprintInspection(
                str(index),
                "R" + str(index + 1),
                "10",
                "-20",
                "0",
                "top",
                mapping["footprint_nickname"]
                + ":"
                + mapping["footprint_name"],
                tuple(pads),
                tuple(models),
            )
        )
    if failure == "pad":
        instances[0] = replace(instances[0], pads=())
    if failure == "model":
        models = (replace(instances[0].models[0], offset_mm=("1", "0", "0")),)
        instances[0] = replace(instances[0], models=models)
    if failure == "side":
        instances[0] = replace(instances[0], side="bottom")
    if failure == "missing":
        instances.pop()
    report = compare_instances(
        BoardInspection(
            SimpleNamespace(
                board_path=str(tmp_path / "test.kicad_pcb"),
                evidence_origin="injected-test",
            ),
            tuple(instances),
        ),
        planning.sources,
        planning.plan.data["mappings"],
    )
    assert report["passed"] is (failure is None)
    assert report["installation_authority"] is False
