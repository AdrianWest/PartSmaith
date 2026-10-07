"""Trusted, scoped profile 1.2 release-node declarations."""

import json
from dataclasses import asdict

from partsmith.ir import RequirementsContext
from partsmith.ir.projection import release_projection
from partsmith.release.reproducibility import digest


def node_dependency(ir, pdl, revisions, configuration, kind, context):
    paths = context.required_ir_paths
    projection = release_projection(
        ir.data,
        requirements=RequirementsContext(
            kind, "1.2", pdl.data["revision"], "1.0", paths, paths
        ),
        revisions=revisions,
        configuration=configuration,
    )
    inputs = {
        key: projection[key]
        for key in (
            "inputs",
            "provenance",
            "decisions",
            "dispositions",
            "rebindings",
        )
    }
    scoped = json.loads(json.dumps(asdict(context)))
    # These are adapter-owned paths. Validation/unused CAD settings are never
    # admitted into unrelated generator dependencies.
    pdl_paths = {
        "SYMBOL": (),
        "FOOTPRINT": (
            "identity",
            "topology",
            "land_pattern",
            "sources",
        ),
        "MODEL_3D": (
            "identity",
            "mechanical",
            "model_3d",
            "reference_features",
            "coordinate_system",
        ),
    }[kind]
    if kind == "FOOTPRINT":
        # Preserve the Phase 5 consumed-configuration rule.
        scoped = {key: scoped[key] for key in ("target_format",)}
    if kind == "MODEL_3D":
        runtime = configuration["runtime"]
        scoped["runtime"] = {
            key: runtime[key]
            for key in (
                "python",
                "python_implementation",
                "python_build",
                "python_executable_sha256",
                "platform",
                "cadquery",
                "ocp",
                "occt",
                "archives",
            )
        }
        scoped["exporter"] = configuration["exporter"]
    declaration = {
        "id": f"partsmith.release.{kind.lower()}",
        "version": "1.2",
        "kind": kind,
        "required_ir_paths": list(paths),
        "required_pdl_paths": list(pdl_paths),
        "required_configuration_paths": sorted(scoped),
        "configuration_schema_version": "1.0",
    }
    projection = {
        "profile": "1.2",
        "declaration": declaration,
        "inputs": inputs,
        "pdl": {
            "id": pdl.data["id"],
            "revision": pdl.data["revision"],
            "content": {key: pdl.data[key] for key in pdl_paths},
        }
        if pdl_paths
        else None,
        "configuration": scoped,
    }
    return digest(projection), declaration | {"projection": projection}
