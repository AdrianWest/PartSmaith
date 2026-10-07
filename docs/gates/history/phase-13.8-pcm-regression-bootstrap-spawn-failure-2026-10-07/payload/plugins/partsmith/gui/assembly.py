"""@package partsmith.gui.assembly
@brief Assembles an unreviewed IR root from retained source acquisition.
@details Missing facts remain null or empty; extracted package labels do not
select a PDL or invent pins, dimensions, engineering units or approvals.
"""

import copy
from hashlib import sha256

from partsmith.ir import ComponentIR, canonical_json
from partsmith.ir.canonical import parse_json
from partsmith.ir.revised import resolve_pointer
from partsmith.ir.targets import engineering_path
from partsmith.persistence.database import utc_timestamp


def assemble_root(session, component_id, values=None, assignments=()):
    """@brief Builds a structurally valid incomplete or fielded IR root.
    @param session Session containing complete retained local extraction.
    @param component_id Persisted engineering component identity.
    @param values Explicitly entered engineering sections, not audit metadata.
    @param assignments Explicit source-to-field interpretation assignments.
    @return Unreviewed ComponentIR with complete original evidence inventory.
    @details Does not read a pre-existing fixture IR or assign implicit facts.
    """
    extraction = session.extraction()
    if extraction is None or not extraction["evidence"]:
        raise ValueError(
            "Retained source evidence is required before assembly"
        )
    evidence = copy.deepcopy(extraction["evidence"])
    document = extraction["document"]
    source_id = evidence[0]["source"]["document_id"]
    part = session.state["setup"]["part_number"]
    revision_id = evidence[0]["acquisition_revision_id"]
    data = {
        "schema_version": "1.2",
        "identity": {
            "component_id": component_id,
            "manufacturer": {"name": None, "normalized_name": None},
            "mpn": part,
            "normalized_mpn": part,
            "package_variant": None,
            "evidence_ids": [],
            "source_document_id": source_id,
            "source_revision": "UNVERSIONED",
        },
        "source": {
            "documents": [
                {
                    "id": source_id,
                    "path": f"source/{document['sha256']}.pdf",
                    "sha256": document["sha256"],
                    "revision": "UNVERSIONED",
                    "revision_basis": {
                        "kind": "content_hash",
                        "sha256": document["sha256"],
                        "captured_at": utc_timestamp(),
                    },
                }
            ]
        },
        "electrical": {},
        "pins": [],
        "package": {
            "family": None,
            "variant": None,
            "pin_count": None,
            "mechanical": {},
            "status": "MISSING",
            "evidence_ids": [],
        },
        "symbol": {"reference_prefix": None, "properties": {}},
        "footprint": {
            "land_pattern_source": None,
            "properties": {},
            "status": "MISSING",
            "evidence_ids": [],
        },
        "model_3d": {
            "required": None,
            "placement": None,
            "accuracy_class": None,
        },
        "evidence": evidence,
        "standards": [],
        "overrides": [],
        "resolutions": [],
        "validation": {"results": [], "tolerances": {}},
        "build": {
            "bft_version": "0.1.0",
            "kicad_target": "10.x",
            "pdl_revision": None,
            "ai_provider": None,
            "ai_model": None,
        },
        "revision": {
            "id": revision_id,
            "parent_id": None,
            "description": "Unreviewed local acquisition assembly",
            "active_override_ids": [],
            "active_resolution_ids": [],
            "evidence_exclusions": [],
            "target_rebindings": [],
            "evidence_review": None,
        },
    }
    supplied = parse_json(canonical_json(values or {}))
    if set(supplied) - {
        "identity",
        "electrical",
        "pins",
        "package",
        "symbol",
        "footprint",
        "model_3d",
    }:
        raise ValueError("Assembly accepts engineering sections only")
    identity = supplied.pop("identity", {})
    if set(identity) & {
        "component_id",
        "source_document_id",
        "source_revision",
        "mpn",
        "normalized_mpn",
    }:
        raise ValueError(
            "Assembly cannot replace source or component identity"
        )
    data["identity"].update(identity)
    data.update(supplied)
    for assignment in assignments:
        if set(assignment) != {
            "evidence_id",
            "paths",
            "status",
            "value",
            "reason",
        }:
            raise ValueError("Invalid explicit evidence assignment fields")
        if assignment["status"] not in {
            "DIRECT",
            "DERIVED",
            "UNKNOWN",
            "INFERRED",
            "AMBIGUOUS",
            "CONFLICTING",
        }:
            raise ValueError("Invalid evidence interpretation status")
        if not assignment["reason"].strip() or not assignment["paths"]:
            raise ValueError(
                "Assignment requires an explicit reason and target paths"
            )
        original = next(
            item
            for item in evidence
            if item["id"] == assignment["evidence_id"]
        )
        derived = copy.deepcopy(original)
        derived["candidate_targets"] = list(assignment["paths"])
        derived["interpretation"] = {
            "normalized_value": assignment["value"],
            "status": assignment["status"],
            "evidence_ids": [original["id"]],
            "derivation": assignment["reason"],
        }
        derived["extractor"] = {
            "method": "explicit-review-assignment",
            "version": "1.0",
        }
        derived["id"] = (
            "ev-assignment-" + sha256(canonical_json(derived)).hexdigest()
        )
        for path in assignment["paths"]:
            if not engineering_path(path):
                raise ValueError("Assignments must target engineering fields")
            field = resolve_pointer(data, path)
            if not isinstance(field, dict) or "evidence_ids" not in field:
                raise ValueError(
                    "Assign a fielded provenance record, not metadata"
                )
            field["evidence_ids"] = [
                derived["id"] if ref == original["id"] else ref
                for ref in field["evidence_ids"]
            ]
            if derived["id"] not in field["evidence_ids"]:
                field["evidence_ids"].append(derived["id"])
        data["evidence"].append(derived)
    return ComponentIR(data)
