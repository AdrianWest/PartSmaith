"""@file curate_production_packages.py
@brief Freezes source-backed package definitions and corresponding IR inputs.
@details Maintainer curation is separate from tests; frozen goldens never
refresh themselves. Rendering choices are recorded separately from drawings.
"""

import copy
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.ir import ComponentIR  # noqa: E402
from partsmith.ir.canonical import canonical_json  # noqa: E402
from partsmith.pdl import PDL, pdl_hash  # noqa: E402
from partsmith.pdl.profiles import (  # noqa: E402
    load_release_profile,
    release_profile_hash,
)


def quantity(value: float, source: str, limits=None) -> dict:
    """@brief Records a fixed or source-bounded model dimension.
    @param value Selected nominal dimension in millimeters.
    @param source Manufacturer or explicit rendering-policy source ID.
    @param limits Optional minimum and maximum from the source.
    @return PDL dimension mapping.
    @details Fixed rendering choices have equal bounds rather than tolerances.
    """
    lo, hi = limits or (value, value)
    return {
        "nominal_mm": value,
        "minimum_mm": lo,
        "maximum_mm": hi,
        "source_ids": [source],
    }


def terminals(config: dict) -> list[dict]:
    """@brief Places physical terminals from the cited top-view numbering.
    @param config Frozen source-backed package configuration.
    @return Terminal records with anchors, pad centers and cardinal rotations.
    @details Exposed pads are distinct terminals; QFN-16 uses EP as an explicit
    unnumbered thermal-pad alias and QFN-24 retains drawing terminal 25.
    """
    count = config["peripheral_count"]
    pitch = config["pitch_mm"]
    x, y, _ = config["body_mm"]
    radial = config["terminal_radial_mm"]
    pad_r = config["pad_center_radial_mm"]
    rows = []
    if count == 2:
        positions = [
            ("west", 0, -(x - radial) / 2, 0, -pad_r, 0, 180),
            ("east", 0, (x - radial) / 2, 0, pad_r, 0, 0),
        ]
    elif count == 3:
        positions = [
            (
                "west",
                0,
                -(x + radial) / 2,
                pitch,
                -pad_r,
                config["sot_pad_pitch_mm"] / 2,
                180,
            ),
            (
                "west",
                1,
                -(x + radial) / 2,
                -pitch,
                -pad_r,
                -config["sot_pad_pitch_mm"] / 2,
                180,
            ),
            ("east", 0, (x + radial) / 2, 0, pad_r, 0, 0),
        ]
    elif config["lead_strategy"] == "GULL_WING":
        half = count // 2
        positions = []
        for i in range(half):
            offset = (half - 1) / 2 * pitch - i * pitch
            positions.append(
                ("west", i, -(x + radial) / 2, offset, -pad_r, offset, 180)
            )
        for i in range(half):
            offset = -(half - 1) / 2 * pitch + i * pitch
            positions.append(
                ("east", i, (x + radial) / 2, offset, pad_r, offset, 0)
            )
    else:
        per_side = count // 4
        positions = []
        for side in ("west", "south", "east", "north"):
            for i in range(per_side):
                offset = (per_side - 1) / 2 * pitch - i * pitch
                if side == "west":
                    point = (-(x - radial) / 2, offset, -pad_r, offset, 180)
                elif side == "south":
                    point = (-offset, -(y - radial) / 2, -offset, -pad_r, 270)
                elif side == "east":
                    point = ((x - radial) / 2, -offset, pad_r, -offset, 0)
                else:
                    point = (offset, (y - radial) / 2, offset, pad_r, 90)
                positions.append((side, i, *point))
    for index, (side, slot, px, py, lx, ly, rotation) in enumerate(positions):
        rows.append(
            {
                "number": str(index + 1),
                "side": side,
                "slot": slot,
                "center": [px, py, config["terminal_height_mm"] / 2],
                "pad_center": [lx, ly],
                "rotation": rotation,
            }
        )
    if "exposed_size_mm" in config:
        rows.append(
            {
                "number": "EP" if count == 16 else "25",
                "side": "center",
                "slot": 0,
                "center": [0, 0, config["terminal_height_mm"] / 2],
                "pad_center": [0, 0],
                "rotation": 0,
            }
        )
    return rows


def package_document(config: dict, policy_hash: str) -> tuple[dict, list]:
    """@brief Creates one PDL 1.1 definition with complete citation bindings.
    @param config Frozen manufacturer facts and explicit model choices.
    @param policy_hash SHA-256 of the complete frozen packages input file.
    @return Validated PDL document and terminal placements.
    @details Observables cover every measured terminal dimension and position.
    """
    data = json.loads(
        (ROOT / "pdl/entries/synthetic-0402@1.0.json").read_bytes()
    )
    profile = load_release_profile("mvp-1", "1.1")
    sid, mid = "SRC-MANUFACTURER", "SRC-MODEL-POLICY"
    data.update(
        schema_version="1.1",
        id=config["pdl_id"],
        revision="1.0",
        effective_date="2026-10-07",
        validation_status="APPROVED",
    )
    data["release_profile"] = {
        "id": "mvp-1",
        "version": "1.1",
        "sha256": release_profile_hash(profile),
    }
    rows = terminals(config)
    exposed = int("exposed_size_mm" in config)
    data["identity"] = {
        "family": config["family"],
        "variant": config["variant"],
        "scope": "MANUFACTURER_SPECIFIC",
        "manufacturer": config["manufacturer"],
        "manufacturer_package_code": config["package_code"],
        "peripheral_lead_count": config["peripheral_count"],
        "exposed_terminal_count": exposed,
        "pin_count": len(rows),
    }
    data["mechanical"]["body"] = {
        key: quantity(
            config["body_mm"][i],
            sid if i < 2 else mid,
            config["body_limits_mm"][i],
        )
        for i, key in enumerate(("length", "width", "height"))
    }
    radial = config["terminal_radial_mm"]
    width = config["terminal_width_mm"]
    height = config["terminal_height_mm"]
    dims = []
    profiles = []
    for row in rows:
        if row["side"] == "center":
            size = [config["exposed_size_mm"]] * 2 + [height]
        else:
            size = [radial, width, height]
            if row["rotation"] in (90, 270):
                size[:2] = [width, radial]
        dims.append(
            {
                "terminal_id": "T-" + row["number"],
                **{
                    key: quantity(size[i], mid)
                    for i, key in enumerate(("length", "width", "height"))
                },
            }
        )
        if config["lead_strategy"] == "GULL_WING":
            t = config["metal_thickness_mm"]
            a, b = -radial / 2, radial / 2
            points = [
                [a, height / 2],
                [a + radial * 0.2, height / 2],
                [b - radial * 0.35, -height / 2 + t],
                [b, -height / 2 + t],
                [b, -height / 2],
                [b - radial * 0.5, -height / 2],
                [a + radial * 0.08, height / 2 - t],
                [a, height / 2 - t],
            ]
            profiles.append(
                {
                    "terminal_id": "T-" + row["number"],
                    "points_mm": points,
                    "width_mm": width,
                    "rotation_deg": row["rotation"],
                }
            )
        elif config["lead_strategy"] == "END_TERMINATIONS":
            top = config["top_contact_mm"]
            bottom = config["bottom_contact_mm"]
            profiles.append(
                {
                    "terminal_id": "T-" + row["number"],
                    "points_mm": [
                        [radial / 2 - bottom, -height / 2],
                        [radial / 2, -height / 2],
                        [radial / 2, height / 2],
                        [radial / 2 - top, height / 2],
                    ],
                    "width_mm": width,
                    "rotation_deg": row["rotation"],
                }
            )
    data["mechanical"]["terminals"] = dims
    data["mechanical"]["terminal"] = {
        k: dims[0][k] for k in ("length", "width", "height")
    }
    data["topology"] = {
        "pitch_mm": config["pitch_mm"],
        "numbering": "COUNTER_CLOCKWISE" if len(rows) > 3 else "LINEAR",
        "pin1_location": "WEST",
        "stagger": False,
        "sides": {
            s: sum(r["side"] == s for r in rows)
            for s in ("north", "east", "south", "west", "center")
        },
        "terminals": [
            {
                "id": "T-" + r["number"],
                "number": r["number"],
                "kind": "EXPOSED" if r["side"] == "center" else "PERIPHERAL",
                "side": r["side"],
                "topology_index": r["slot"],
                "group_id": "G-" + r["number"],
            }
            for r in rows
        ],
    }
    groups = []
    for r in rows:
        size = (
            [config["exposed_size_mm"]] * 2
            if r["side"] == "center"
            else [config["pad_radial_mm"], config["pad_width_mm"]]
        )
        if r["rotation"] in (90, 270):
            size.reverse()
        groups.append(
            {
                "id": "G-" + r["number"],
                "terminal_number": r["number"],
                "shapes": [
                    {
                        "id": "PAD-" + r["number"],
                        "shape": "RECT",
                        "center_mm": r["pad_center"],
                        "size_mm": size,
                    }
                ],
            }
        )
    data["land_pattern"] = {
        "source": "MANUFACTURER_RECOMMENDED",
        "groups": groups,
        "non_electrical_features": [],
    }
    data["model_3d"] = {
        "body_strategy": "CHIP_BODY" if len(rows) == 2 else "MOLDED_BODY",
        "lead_strategy": config["lead_strategy"],
        "marker_strategy": "NONE",
        "lead_profiles": profiles,
        "geometry_basis": config["model_choices"],
    }
    x, y, z = config["body_mm"]
    body_top = z + config["body_bottom_mm"]
    if len(rows) > 2:
        data["model_3d"].update(
            marker_strategy="PIN1_RECESS",
            pin1_marker={
                "center_mm": [-x * 0.35, y * 0.35, body_top - 0.06],
                "radius_mm": min(0.15, x / 20),
                "depth_mm": 0.06,
            },
        )
    refs = [
        r
        for r in data["reference_features"]
        if r["kind"] not in {"TERMINAL_ANCHOR", "PIN1_ANCHOR"}
    ]
    refs[0]["anchor_mm"] = [0, 0, z / 2 + config["body_bottom_mm"]]
    for r in rows:
        refs.append(
            {
                "id": "TERMINAL-" + r["number"],
                "kind": "TERMINAL_ANCHOR",
                "terminal_id": "T-" + r["number"],
                "anchor_mm": r["center"],
                "representation": "MEASURED",
                "applicability": "REQUIRED",
            }
        )
    refs.append(
        {
            "id": "PIN1",
            "kind": "PIN1_ANCHOR",
            "terminal_id": "T-1",
            "anchor_mm": rows[0]["center"],
            "representation": "DECLARED_ONLY",
            "applicability": "REQUIRED",
        }
    )
    data["reference_features"] = refs
    data["allowed_symmetries"][0]["terminal_mapping"] = {
        "T-" + r["number"]: "T-" + r["number"] for r in rows
    }
    obs = [
        o
        for o in data["required_observables"]
        if o["feature_id"] in {"BODY-EXTENT", "LAND-EXTENT", "PIN1"}
    ]
    for r in rows:
        for kind in ("POSITION", "LENGTH", "WIDTH", "HEIGHT"):
            obs.append(
                {
                    "id": "OBS-" + r["number"] + "-" + kind,
                    "kind": kind,
                    "feature_id": "TERMINAL-" + r["number"],
                    "measurement_mode": "MEASURED",
                    "tolerance_id": "POSITION"
                    if kind == "POSITION"
                    else "BODY",
                }
            )
    data["required_observables"] = obs
    source = config["source"]
    data["sources"] = [
        {
            "id": sid,
            "organization": config["manufacturer"],
            "document": Path(source["file"]).name,
            "revision": source["revision"],
            "reference": source["url"],
            "access_date": "2026-10-07",
            "section": f"PDF page {source['page']}",
            "table_or_figure": source["figure"],
            "content_sha256": source["sha256"],
        },
        {
            "id": mid,
            "organization": "Board Forge Tools",
            "document": "Representative model choices and source facts",
            "revision": "1.0",
            "reference": "fixtures/production/packages.json",
            "access_date": "2026-10-07",
            "section": config["variant"],
            "table_or_figure": "model_choices and geometry values",
            "content_sha256": policy_hash,
        },
    ]
    data["change_history"] = [
        {
            "revision": "1.0",
            "date": "2026-10-07",
            "description": "Manufacturer-backed Phase 14 package corpus",
            "source_ids": [sid, mid],
        }
    ]
    data["content_sha256"] = pdl_hash(data)
    PDL.from_json(json.dumps(data))
    return data, rows


def component_document(config: dict, pdl: dict, rows: list) -> dict:
    """@brief Creates a fully source-bound IR for one production golden.
    @param config Frozen package source and model choices.
    @param pdl Validated pinned package definition.
    @param rows Explicit physical terminal placements.
    @return Validated Component IR 1.2 input.
    @details Electrical entries come from the cited pin table; unspecified
    transistor functions remain passive rather than inferred digital behavior.
    """
    data = json.loads((ROOT / "fixtures/ir/v1.2/valid/0402.json").read_bytes())
    source = config["source"]
    identity = data["identity"]
    identity.update(
        manufacturer={
            "name": config["manufacturer"],
            "normalized_name": config["manufacturer"].lower(),
        },
        mpn=config["mpn"],
        normalized_mpn=config["mpn"],
        package_variant=config["variant"],
        source_revision=source["revision"],
    )
    data["source"]["documents"][0].update(
        path=source["file"],
        sha256=source["sha256"],
        revision=source["revision"],
    )
    policy_hash = sha256(
        (ROOT / "fixtures/production/packages.json").read_bytes()
    ).hexdigest()
    data["source"]["documents"].append(
        {
            "id": "D-MODEL",
            "path": "fixtures/production/packages.json",
            "sha256": policy_hash,
            "revision": "1.0",
        }
    )
    data["electrical"] = {}
    prototype = data["pins"][0]
    pins = []
    for i, r in enumerate(rows):
        pin = copy.deepcopy(prototype)
        pin.update(
            number=r["number"],
            name=config["pin_names"][i],
            electrical_type=config["pin_types"][i],
            function=config["pin_names"][i],
            active_low=(
                config["variant"] == "TSSOP-16"
                and config["pin_names"][i] in {"SRCLR", "OE"}
            ),
        )
        pin["physical"] = {
            "topology_side": r["side"],
            "topology_index": r["slot"],
        }
        pin["flags"] = {
            "exposed_pad": r["side"] == "center",
            "no_connect": config["pin_types"][i] == "no_connect",
        }
        pins.append(pin)
    data["pins"] = pins
    data["package"].update(
        family=config["family"], variant=config["variant"], pin_count=len(rows)
    )
    for i, name in enumerate(("body_length", "body_width", "body_height")):
        data["package"]["mechanical"][name] = {
            "source_value": config["body_mm"][i],
            "source_unit": "mm",
            "status": "DIRECT",
            "evidence_ids": ["E-001"],
        }
    data["symbol"]["reference_prefix"] = (
        "R" if len(rows) == 2 else "Q" if len(rows) == 3 else "U"
    )
    evidence = data["evidence"][0]
    evidence["type"] = "MANUFACTURER_DRAWING_AND_PIN_TABLE"
    evidence["source"].update(
        document_hash=source["sha256"], page=source["page"]
    )
    evidence["extracted"]["text"] = (
        source["figure"]
        + "; explicit model choices: "
        + config["model_choices"]
    )
    evidence["extractor"] = {
        "method": "reviewed-package-corpus",
        "version": "1.0",
    }
    evidence["confidence"]["basis"] = (
        "Frozen drawing, pin table and explicit model choices"
    )
    evidence["candidate_targets"] = [
        "/identity",
        "/package",
        "/footprint",
        "/model_3d/placement",
        *[f"/pins/{i}" for i in range(len(pins))],
        *[
            "/package/mechanical/" + name
            for name in ("body_length", "body_width", "body_height")
        ],
    ]
    model_evidence = copy.deepcopy(evidence)
    model_evidence["id"] = "E-MODEL"
    model_evidence["type"] = "EXPLICIT_MODEL_CHOICE"
    model_evidence["source"].update(
        document_id="D-MODEL", document_hash=policy_hash, page=1
    )
    model_evidence["extracted"]["text"] = config["model_choices"]
    model_evidence["candidate_targets"] = [
        "/package/mechanical/body_height",
    ]
    data["package"]["mechanical"]["body_height"]["evidence_ids"] = ["E-MODEL"]
    data["evidence"].append(model_evidence)
    for evidence_id, page_key, paths in (
        ("E-PINS", "pin_page", [f"/pins/{i}" for i in range(len(pins))]),
        ("E-LAND", "land_page", ["/footprint"]),
    ):
        cited = copy.deepcopy(evidence)
        cited["id"] = evidence_id
        cited["source"]["page"] = source.get(page_key, source["page"])
        cited["candidate_targets"] = paths
        cited["extracted"]["text"] = source["figure"]
        data["evidence"].append(cited)
    for pin in pins:
        pin["evidence_ids"] = ["E-PINS"]
    data["footprint"]["evidence_ids"] = ["E-LAND"]
    inventory = {
        "source_hashes": [d["sha256"] for d in data["source"]["documents"]],
        "evidence_ids": [e["id"] for e in data["evidence"]],
    }
    data["revision"]["evidence_review"].update(
        inventory_sha256=sha256(canonical_json(inventory)).hexdigest(),
        reviewed_evidence_ids=inventory["evidence_ids"],
    )
    data["revision"]["description"] = (
        "Manufacturer-backed Phase 14 corpus input"
    )
    data["build"]["pdl_revision"] = pdl["revision"]
    ComponentIR.from_json(json.dumps(data))
    return data


def main() -> int:
    """@brief Writes the explicitly curated eight-variant PDL and IR corpus.
    @return Zero when every source hash and strict input validates.
    @details Source documents must already be frozen; no download occurs here.
    """
    path = ROOT / "fixtures/production/packages.json"
    policy_hash = sha256(path.read_bytes()).hexdigest()
    configs = json.loads(path.read_bytes())["packages"]
    ir_root = ROOT / "fixtures/production/ir"
    ir_root.mkdir(parents=True, exist_ok=True)
    for config in configs:
        source = config["source"]
        if (
            sha256((ROOT / source["file"]).read_bytes()).hexdigest()
            != source["sha256"]
        ):
            raise ValueError("Manufacturer source changed")
        pdl, rows = package_document(config, policy_hash)
        ir = component_document(config, pdl, rows)
        for target, value in (
            (ROOT / "pdl/entries" / (config["pdl_id"] + "@1.0.json"), pdl),
            (ir_root / (config["variant"] + ".json"), ir),
        ):
            target.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        print("Validated", config["variant"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
