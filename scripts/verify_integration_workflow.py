"""@file verify_integration_workflow.py
@brief Creates owned two-component workflow fixtures and compares live IPC.
@details Explicit fixture flags use shared services and current OS approval.
Native editor actions remain separately supervised.
"""

import argparse
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from partsmith.gui.session import Session
from partsmith.integration.instance_semantics import compare_instances
from partsmith.integration.ipc import (
    BoardInspection,
    FootprintInspection,
    IpcCapabilities,
    ModelInspection,
    PadInspection,
)
from partsmith.integration.native_stage import board_tree
from partsmith.integration.sexpr import Atom, children, parse, serialize
from partsmith.integration.sources import resolve_approved_source
from partsmith.integration.workflow import IntegrationWorkflow
from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.persistence import connect


def schematic(root, mappings):
    """@brief Writes a disposable native schematic using installed symbols.
    @param root Owned installed project directory.
    @param mappings Actual current installation component mappings.
    @return None.
    @details Cache names and Footprint properties bind installed entries.
    Library source bytes remain unchanged; fixture instances have fresh UUIDs.
    """
    root_id = str(uuid4())
    tree = parse(
        serialize(
            [
                Atom("kicad_sch"),
                [Atom("version"), Atom("20250114")],
                [Atom("generator"), "eeschema"],
                [Atom("uuid"), root_id],
                [Atom("paper"), "A4"],
                [Atom("lib_symbols")],
            ]
        )
    )
    cached = children(tree, "lib_symbols")[0]
    library = parse((root / "BFT_Symbols.kicad_sym").read_bytes())
    for index, mapping in enumerate(mappings):
        name = "BFT_Symbols:" + mapping["symbol_name"]
        source = next(
            s
            for s in children(library, "symbol")
            if s[1] == mapping["symbol_name"]
        )
        symbol = deepcopy(source)
        symbol[1] = name
        cached.append(symbol)
        instance_id = str(uuid4())
        x, y = str(80 + index * 40), "80"
        tree.append(
            [
                Atom("symbol"),
                [Atom("lib_id"), name],
                [Atom("at"), Atom(x), Atom(y), Atom("0")],
                [Atom("unit"), Atom("1")],
                [Atom("in_bom"), Atom("yes")],
                [Atom("on_board"), Atom("yes")],
                [Atom("dnp"), Atom("no")],
                [Atom("uuid"), instance_id],
                [
                    Atom("property"),
                    "Reference",
                    f"R{index + 1}",
                    [Atom("at"), Atom(x), Atom("75"), Atom("0")],
                    [
                        Atom("effects"),
                        [
                            Atom("font"),
                            [Atom("size"), Atom("1.27"), Atom("1.27")],
                        ],
                    ],
                ],
                [
                    Atom("property"),
                    "Value",
                    mapping["symbol_name"],
                    [Atom("at"), Atom(x), Atom("85"), Atom("0")],
                    [
                        Atom("effects"),
                        [
                            Atom("font"),
                            [Atom("size"), Atom("1.27"), Atom("1.27")],
                        ],
                    ],
                ],
                [
                    Atom("property"),
                    "Footprint",
                    "BFT_Footprints:" + (mapping["footprint_name"]),
                    [Atom("at"), Atom(x), Atom(y), Atom("0")],
                    [
                        Atom("effects"),
                        [
                            Atom("font"),
                            [Atom("size"), Atom("1.27"), Atom("1.27")],
                        ],
                        [Atom("hide"), Atom("yes")],
                    ],
                ],
                [
                    Atom("instances"),
                    [
                        Atom("project"),
                        "acceptance",
                        [
                            Atom("path"),
                            "/" + root_id,
                            [Atom("reference"), f"R{index + 1}"],
                            [Atom("unit"), Atom("1")],
                        ],
                    ],
                ],
            ]
        )
    (root / "acceptance.kicad_sch").write_bytes(serialize(tree))


def prepare(args):
    """@brief Publishes one owned fixture using the production shared service.
    @param args Explicit source database, builds and absent output directory.
    @return None.
    @details Original source database and project stay unchanged.
    """
    output = args.output.absolute()
    output.mkdir()
    session = Session(output / "sessions")
    source_hash = sha256(args.database.read_bytes()).hexdigest()
    with closing(connect(args.database)) as source:
        with closing(connect(session.database)) as destination:
            source.backup(destination)
            destination.execute(
                "CREATE TABLE desktop_session "
                "(id INTEGER PRIMARY KEY,data BLOB)"
            )
            destination.execute(
                "INSERT INTO desktop_session VALUES (1,?)",
                (canonical_json(session.state),),
            )
            destination.commit()
    archive = output / "approved-components.partsmith"
    session.save(archive)
    original = output / "original"
    original.mkdir()
    (original / "acceptance.kicad_pro").write_bytes(b"{}")
    workflow = IntegrationWorkflow([session])
    target, link = workflow.register(
        original, output / "managed", confirmed=True
    )
    draft = workflow.stage(workflow.plan(target, tuple(args.build[:2])))
    decision = workflow.authorize(draft, "Review owned two-component workflow")
    result = workflow.publish(draft, confirmed=True)
    assert result.committed
    root = Path(link)
    footprints = [
        parse((root / m["footprint_path"]).read_bytes())
        for m in draft.staged.manifest.data["mappings"]
    ]
    (root / "acceptance.kicad_pcb").write_bytes(
        serialize(board_tree(footprints))
    )
    schematic(root, draft.staged.manifest.data["mappings"])
    session.update(integration=draft.references())
    session.save(output / "saved-draft.partsmith")
    for name, contract in (
        ("plan", draft.planning.plan),
        ("manifest", draft.staged.manifest),
        ("authorization", decision.authorization),
        ("audit", decision.audit),
        ("pre-validation", draft.staged.pre),
        ("post-validation", draft.staged.post),
    ):
        (output / (name + ".json")).write_bytes(contract.canonical_bytes)
    assert sha256(args.database.read_bytes()).hexdigest() == source_hash
    (output / "workflow.json").write_bytes(
        canonical_json(
            {
                "target": target,
                "project_path": link,
                "source_archive": str(archive),
                "source_database_sha256": source_hash,
                "builds": args.build,
                "authority_database": str(workflow.database),
                "installation_receipt": result.receipt_hash,
            }
        )
    )
    print(str(root / "acceptance.kicad_pro"))


def compare(args):
    """@brief Compares separately captured actual native IPC instance records.
    @param args Owned fixture directory and safe live diagnostic record.
    @return None.
    @details Rejects injected evidence and requires the exact selected project.
    """
    metadata = parse_json((args.output / "workflow.json").read_bytes())
    record = parse_json(args.live_record.read_bytes())
    inspection = record["ipc_inspection"]["inspection"]
    capabilities = IpcCapabilities(**inspection["capabilities"])
    assert capabilities.evidence_origin == "official-live-binding"
    expected_board = args.expected_board or (
        Path(metadata["project_path"]) / "acceptance.kicad_pcb"
    )
    assert Path(capabilities.board_path).resolve() == expected_board.resolve()
    footprints = []
    for item in inspection["footprints"]:
        item["pads"] = tuple(PadInspection(**p) for p in item["pads"])
        item["models"] = tuple(ModelInspection(**m) for m in item["models"])
        footprints.append(FootprintInspection(**item))
    manifest_path = args.manifest or (args.output / "manifest.json")
    manifest = parse_json(manifest_path.read_bytes())
    with closing(connect(args.database)) as connection:
        sources = sorted(
            (
                resolve_approved_source(connection, b)
                for b in (args.build or metadata["builds"][:2])
            ),
            key=lambda s: s.component_id,
        )
    result = compare_instances(
        BoardInspection(capabilities, tuple(footprints)),
        sources,
        manifest["mappings"],
    )
    (args.output / "instance-comparison.json").write_bytes(
        canonical_json(result)
    )
    assert result["passed"], result
    print("Actual native instance comparison PASS")


def main():
    """@brief Runs deliberate owned fixture preparation or live comparison.
    @return None.
    @details Existing fixtures are never overwritten by preparation.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build", action="append", default=[])
    parser.add_argument("--publish-fixture", action="store_true")
    parser.add_argument("--live-record", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expected-board", type=Path)
    args = parser.parse_args()
    if args.live_record:
        compare(args)
    else:
        assert args.publish_fixture and len(args.build) == 3
        prepare(args)


if __name__ == "__main__":
    main()
