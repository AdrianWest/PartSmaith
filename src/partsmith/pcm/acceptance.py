"""@package partsmith.pcm.acceptance
@brief Runs the eight-variant release corpus inside the installed runtime.
@details Uses disposable databases and native CLI validation. It never opens,
reads or changes a user's PCB, libraries or engineering approval history.
"""

from __future__ import annotations

import copy
import json
import tempfile
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from partsmith.footprint import FootprintContext, serialize_footprint
from partsmith.ir import ComponentIR
from partsmith.kicad import discover_kicad
from partsmith.pdl import load_pdl, load_release_profile
from partsmith.persistence import ImmutableStore, Repository, database
from partsmith.release.pipeline import KnownGoodReleasePipeline
from partsmith.symbol import SymbolContext, serialize_symbol
from partsmith.threed import (
    ThreeDContext,
    cross_validate_footprint_3d,
    generate_model_3d,
    validate_model_3d,
)
from partsmith.threed.geometry import build_solids
from partsmith.threed.step_backend import (
    export_step_solids,
    generate_step_bytes,
)


def generate_artifacts(ir: ComponentIR, pdl) -> tuple:
    """@brief Generates independent production artifacts with pinned contexts.
    @param ir Frozen strict component input.
    @param pdl Frozen source-backed package definition.
    @return Symbol, preliminary footprint and canonical STEP artifacts.
    @details Serializer 2.0 fixes the expanded-symbol row layout. Native
    footprint conversion is explicitly versioned by PDL 1.1.
    """
    return (
        serialize_symbol(ir, SymbolContext(serializer_version="2.0")),
        serialize_footprint(ir, pdl, FootprintContext()),
        generate_model_3d(ir, pdl, ThreeDContext()),
    )


def negative_checks(ir: ComponentIR, pdl, footprint, step) -> dict:
    """@brief Checks independently malformed artifacts for one package.
    @param ir Original reviewed corpus IR.
    @param pdl Original source-backed package definition.
    @param footprint Untampered preliminary footprint artifact.
    @param step Untampered canonical STEP artifact.
    @return Fault names mapped to the blocking rule IDs that rejected them.
    @details Covers missing terminals, offsets, dimensions, native units,
    pin maps, orientation and exposed-pad geometry where applicable.
    """
    outcomes = {}

    def reject(name: str, blob: bytes, expected: str) -> None:
        """@brief Requires a malformed STEP to fail its intended rule.
        @param name Fault identity.
        @param blob Malformed model bytes.
        @param expected Blocking rule or observable ID.
        @return None.
        @details An unrelated parse failure cannot substitute for rejection.
        """
        failed = sorted(
            r.rule_id
            for r in validate_model_3d(blob, ir, pdl)
            if r.status == "FAIL"
        )
        if expected not in failed:
            raise ValueError("CORPUS_NEGATIVE_NOT_REJECTED: " + name)
        outcomes[name] = failed

    solids = build_solids(pdl.data)
    reject("missing-terminal", export_step_solids(solids[:-1]), "solid-count")
    reject(
        "model-offset",
        export_step_solids([solid.translate((0.5, 0, 0)) for solid in solids]),
        "step-offset",
    )
    reject(
        "wrong-unit",
        step.content.replace(b".MILLI.", b".CENTI."),
        "step-unit-scale",
    )
    changed = copy.deepcopy(pdl.data)
    changed["mechanical"]["body"]["height"]["nominal_mm"] *= Decimal("1.5")
    reject("body-height", generate_step_bytes(changed), "OBS-BODY-HEIGHT")
    changed = copy.deepcopy(pdl.data)
    changed["mechanical"]["terminals"][0]["width"]["nominal_mm"] *= 2
    # Profile width is independently frozen; change that geometry too.
    for profile in changed["model_3d"].get("lead_profiles", []):
        if (
            profile["terminal_id"]
            == changed["mechanical"]["terminals"][0]["terminal_id"]
        ):
            profile["width_mm"] *= 2
    reject("terminal-width", generate_step_bytes(changed), "OBS-1-WIDTH")
    wrong_pad = footprint.content.replace(b'(pad "1"', b'(pad "WRONG"', 1)
    failed = sorted(
        r.rule_id
        for r in cross_validate_footprint_3d(wrong_pad, step.content, ir, pdl)
        if r.status == "FAIL"
    )
    if "physical-pin-count" not in failed:
        raise ValueError("CORPUS_PIN_MAP_NOT_REJECTED")
    outcomes["wrong-pad-number"] = failed
    if pdl.data["model_3d"].get("pin1_marker"):
        reject(
            "rotation",
            export_step_solids(
                [s.rotate((0, 0, 0), (0, 0, 1), 90) for s in solids]
            ),
            "pin1-index-geometry",
        )
        reject(
            "mirror",
            export_step_solids([s.mirror("YZ") for s in solids]),
            "pin1-index-geometry",
        )
    else:
        reject(
            "rotation",
            export_step_solids(
                [s.rotate((0, 0, 0), (0, 0, 1), 90) for s in solids]
            ),
            "OBS-BODY-LENGTH",
        )
    exposed = next(
        (
            t
            for t in pdl.data["topology"]["terminals"]
            if t["kind"] == "EXPOSED"
        ),
        None,
    )
    if exposed:
        changed = copy.deepcopy(pdl.data)
        dimensions = next(
            d
            for d in changed["mechanical"]["terminals"]
            if d["terminal_id"] == exposed["id"]
        )
        dimensions["length"]["nominal_mm"] *= Decimal("0.5")
        reject(
            "exposed-pad-size",
            generate_step_bytes(changed),
            "OBS-" + exposed["number"] + "-LENGTH",
        )
    return outcomes


def run_corpus(corpus: Path, *, freeze: bool = False) -> dict:
    """@brief Validates every required variant through the release pipeline.
    @param corpus Exact packaged or producer corpus directory.
    @param freeze Maintainer-only creation of new golden reference bytes.
    @return Per-variant source, golden, negative and native validation receipt.
    @details Uses reviewed test inputs in a disposable store and leaves builds
    awaiting review; this test never grants an engineering release approval.
    """
    configs = json.loads((corpus / "packages.json").read_bytes())["packages"]
    required = set(load_release_profile("mvp-1", "1.1")["production_variants"])
    if (
        len(configs) != len(required)
        or {c["variant"] for c in configs} != required
    ):
        raise ValueError("CORPUS_REQUIRED_VARIANTS_MISSING")
    runtime = discover_kicad()
    golden_path = corpus / "golden.json"
    goldens = (
        {} if freeze else json.loads(golden_path.read_bytes())["variants"]
    )
    report = {
        "schema_version": "partsmith-phase14-corpus-1.0",
        "state": "PASS",
        "kicad": runtime.version,
        "variants": {},
    }
    for config in configs:
        variant = config["variant"]
        source = config["source"]
        pdf = corpus / "sources" / Path(source["file"]).name
        if sha256(pdf.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("CORPUS_MANUFACTURER_SOURCE_CHANGED")
        pdl = load_pdl(config["pdl_id"], "1.0")
        ir = ComponentIR.from_file(corpus / "ir" / (variant + ".json"))
        artifacts = generate_artifacts(ir, pdl)
        repeated = generate_artifacts(ir, pdl)
        if [a.content for a in artifacts] != [a.content for a in repeated]:
            raise ValueError("CORPUS_BYTES_NOT_REPRODUCIBLE")
        symbol, footprint, step = artifacts
        measured = (
            *validate_model_3d(step.content, ir, pdl),
            *cross_validate_footprint_3d(
                footprint.content, step.content, ir, pdl
            ),
        )
        if any(r.status == "FAIL" for r in measured):
            raise ValueError("CORPUS_CLASS_A_FAILED: " + variant)
        negatives = negative_checks(ir, pdl, footprint, step)
        with tempfile.TemporaryDirectory(
            prefix="partsmith-corpus-"
        ) as temporary:
            with database(Path(temporary) / "test.sqlite3") as connection:
                component = Repository(connection).create_component(
                    config["manufacturer"], config["mpn"], variant
                )
                data = ir.data
                data["identity"]["component_id"] = component.id
                store = ImmutableStore(connection)
                inventory = store.put_inventory(
                    {
                        "source_hashes": [
                            d["sha256"] for d in data["source"]["documents"]
                        ],
                        "evidence_ids": [e["id"] for e in data["evidence"]],
                    }
                )
                revision = store.put_revision(
                    data, inventory_sha256=inventory, reviewed=True
                )
                store.compare_and_swap_head(
                    component.id, revision.revision_id, None
                )
                candidate = KnownGoodReleasePipeline(connection).run(
                    component.id, revision.revision_id, pdl
                )
                final = connection.execute(
                    "SELECT artifact_type, logical_path, sha256, content "
                    "FROM artifacts "
                    "WHERE build_id = ? AND stage = 'FINAL'",
                    (candidate.build_id,),
                ).fetchall()
                native = connection.execute(
                    "SELECT canonical_bytes FROM validation_results "
                    "WHERE build_id = ? "
                    "AND rule_id = 'kicad-native-compatibility'",
                    (candidate.build_id,),
                ).fetchone()
                if (
                    not native
                    or json.loads(bytes(native[0]))["status"] != "PASS"
                ):
                    raise ValueError("CORPUS_NATIVE_KICAD_FAILED")
        records = {}
        golden_root = corpus / "golden" / variant
        if freeze:
            golden_root.mkdir(parents=True, exist_ok=True)
        for row in final:
            name = Path(row["logical_path"]).name
            blob = bytes(row["content"])
            record = {"filename": name, "sha256": sha256(blob).hexdigest()}
            records[row["artifact_type"]] = record
            if freeze:
                (golden_root / name).write_bytes(blob)
            elif (
                records[row["artifact_type"]]
                != goldens[variant][row["artifact_type"]]
                or (golden_root / name).read_bytes() != blob
            ):
                raise ValueError("CORPUS_FROZEN_GOLDEN_CHANGED: " + variant)
        if set(records) != {"SYMBOL", "FOOTPRINT", "MODEL_3D"}:
            raise ValueError("CORPUS_FINAL_ARTIFACTS_MISSING")
        goldens[variant] = records
        report["variants"][variant] = {
            "state": "PASS",
            "manufacturer": config["manufacturer"],
            "source_sha256": source["sha256"],
            "pdl_sha256": pdl.sha256,
            "artifacts": records,
            "negative_cases": negatives,
            "reproducibility": "EXACT_BYTES",
            "native_compatibility": "PASS",
            "measured_rules": [
                r.rule_id for r in measured if r.measurement_mode == "MEASURED"
            ],
            "accuracy_class": "CLASS_A",
            "model_choices": config["model_choices"],
        }
    if freeze:
        golden_path.write_text(
            json.dumps(
                {
                    "schema_version": "partsmith-golden-corpus-1.0",
                    "variants": goldens,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    plugin_root = Path(__file__).resolve().parents[2]
    if (plugin_root / "bundle.json").is_file():
        from .native import verify_native_origins

        report["native_libraries"] = verify_native_origins(plugin_root)
    return report
