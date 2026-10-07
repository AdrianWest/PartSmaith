"""@package partsmith.gui.artifact_scene
@brief Resolves exact active-session artifacts without wx or native imports.
@details Display readiness does not grant release approval.
"""

from partsmith.ir.canonical import canonical_json
from partsmith.persistence import ImmutableStore

from .scene import SceneSource, parse_footprint, validate_placement


def session_scene(session):
    """@brief Resolves a hash-verified bound artifact pair and placement.
    @param session Current active working session.
    @return SceneSource and exact display binding metadata.
    @details Missing or unsupported data disables the action without defaults.
    """
    artifacts = session.state.get("drafts", {}).get("artifacts", [])
    for stage in ("FINAL", "PRELIMINARY"):
        pair = {
            item["type"]: item
            for item in artifacts
            if item["stage"] == stage
            and item["type"] in {"FOOTPRINT", "MODEL_3D"}
        }
        if len(pair) != 2:
            continue
        footprint, model = pair["FOOTPRINT"], pair["MODEL_3D"]
        if (footprint["build_id"], footprint["revision_id"]) != (
            model["build_id"],
            model["revision_id"],
        ):
            raise ValueError("Viewer artifact pair has incompatible bindings")
        placement = footprint.get("placement")
        if not isinstance(placement, dict):
            raise ValueError(
                "Viewer requires retained explicit placement metadata"
            )
        validate_placement(placement)
        source = SceneSource(
            session.get(model["reference"]),
            session.get(footprint["reference"]),
            canonical_json(placement),
        )
        source.validate()
        parse_footprint(source.footprint)
        if (
            not source.step.startswith(b"ISO-10303-21;")
            or b"END-ISO-10303-21;" not in source.step
        ):
            raise ValueError("Viewer STEP is not parseable exchange content")
        binding = {
            "stage": stage,
            "build_id": model["build_id"],
            "revision_id": model["revision_id"],
            "stale": model["revision_id"] != session.state.get("revision_id"),
            "status": session.state.get("status"),
            "placement": placement,
        }
        with session.connection() as connection:
            binding["pins"] = ImmutableStore(connection).get_revision(
                model["revision_id"]
            )["pins"]
        return source, binding
    raise ValueError(
        "Viewer requires actual footprint, STEP and placement metadata"
    )
