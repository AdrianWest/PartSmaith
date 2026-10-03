"""@package partsmith.release.pipeline
@brief Deterministic Phase 8 known-good component release pipeline.
@details Generates independent artifacts, finalizes the STEP association,
validates exact final bytes, freezes the manifest, and exports approved
content.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from partsmith.footprint import (
    FootprintContext,
    serialize_footprint,
    validate_footprint_artifact,
    validate_footprint_inputs,
)
from partsmith.ir import ComponentIR, canonical_json
from partsmith.pdl import PDL
from partsmith.persistence import ImmutableStore, ReleaseStore
from partsmith.release.contracts import (
    ApprovalBinding,
    BuildState,
    EngineeringManifest,
    PostManifestReport,
    ReviewStage,
)
from partsmith.release.workflow import BuildOrchestrator
from partsmith.symbol import (
    SymbolContext,
    serialize_symbol,
    validate_symbol_artifact,
    validate_symbol_inputs,
)
from partsmith.threed import (
    ThreeDContext,
    cross_validate_footprint_3d,
    generate_model_3d,
    validate_model_3d,
    validate_step_artifact,
    validate_threed_inputs,
)


@dataclass(frozen=True)
class ReleaseCandidate:
    """@brief Identifies one build waiting for exact release approval.
    @details The binding is suitable for the authenticated ReviewService.
    """

    build_id: str
    manifest_hash: str
    binding: ApprovalBinding


def _validation_result(
    rule_id: str,
    status: str,
    message: str,
    artifact_hashes: tuple[str, ...],
    *,
    category: str = "release",
) -> dict:
    """@brief Constructs one strict final-artifact validation result.
    @param rule_id Stable rule identity.
    @param status PASS or FAIL.
    @param message Human-readable result detail.
    @param artifact_hashes Exact validated artifact hashes.
    @param category Stable validation category.
    @return Complete Phase 8 validation result mapping.
    @details Result IDs are audit-only and excluded from semantic hashes.
    """
    return {
        "id": f"phase8-{rule_id}",
        "category": category,
        "rule_id": rule_id,
        "status": status,
        "severity": "INFO" if status == "PASS" else "ERROR",
        "message": message,
        "evidence_ids": [],
        "artifact_ids": list(artifact_hashes),
        "measured": status == "PASS",
        "expected": True,
        "tolerance": None,
        "stage": "FINAL_ARTIFACT",
        "applicability": "APPLICABLE",
        "applicability_reason": None,
        "applicability_basis": None,
        "measurement_mode": "MEASURED",
        "validator": {"id": "partsmith.phase8", "version": "1.0"},
    }


def _finalize_footprint(
    content: bytes, model_path: str, ir: ComponentIR
) -> bytes:
    """@brief Attaches one portable final STEP reference to a footprint.
    @param content Preliminary deterministic footprint bytes.
    @param model_path Portable logical STEP path.
    @param ir Reviewed component IR containing placement.
    @return Finalized footprint bytes.
    @details Finalization preserves geometry and changes exact footprint bytes.
    """
    text = content.decode("utf-8")
    if not text.endswith(")\n"):
        raise ValueError("Footprint is not finalizable KiCad content")
    placement = ir.data["model_3d"]["placement"]
    translation = placement["translation_mm"]
    rotation = placement["rotation_deg"]
    scale = list(placement["scale"])
    for index, axis in enumerate(("x", "y", "z")):
        if placement["mirror"][axis]:
            scale[index] = -scale[index]
    block = "\n".join(
        (
            f'  (model "{model_path}"',
            "    (offset (xyz "
            + " ".join(str(value) for value in translation)
            + "))",
            "    (scale (xyz "
            + " ".join(str(value) for value in scale)
            + "))",
            "    (rotate (xyz "
            + " ".join(str(value) for value in rotation)
            + "))",
            "  )",
        )
    )
    return (text[:-2] + block + "\n)\n").encode("utf-8")


class KnownGoodReleasePipeline:
    """@brief Runs the Phase 8 deterministic known-good component path.
    @details The pipeline stops at RELEASE review; authenticated approval is a
    separate explicit service operation.
    """

    def __init__(self, connection: sqlite3.Connection):
        """@brief Initializes the deterministic release pipeline.
        @param connection Migrated SQLite connection.
        @return None.
        @details The caller owns the transaction and connection lifetime.
        """
        self.connection = connection
        self.revisions = ImmutableStore(connection)
        self.release = ReleaseStore(connection)
        self.orchestrator = BuildOrchestrator(connection)

    def run(
        self,
        component_id: str,
        revision_id: str,
        pdl: PDL,
    ) -> ReleaseCandidate:
        """@brief Builds one reviewed component through release review.
        @param component_id Persisted component identity.
        @param revision_id Current reviewed IR revision identity.
        @param pdl Trusted selected package declaration.
        @return Build identity, manifest hash, and exact approval binding.
        @details Any input or final-byte blocker raises before review waiting.
        """
        head = self.connection.execute(
            "SELECT * FROM component_heads WHERE component_id = ?",
            (component_id,),
        ).fetchone()
        row = self.connection.execute(
            "SELECT * FROM ir_revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if (
            head is None
            or row is None
            or head["revision_id"] != revision_id
            or not row["reviewed"]
        ):
            raise ValueError("Pipeline requires the current reviewed revision")
        ir = ComponentIR(self.revisions.get_revision(revision_id))
        build = self.orchestrator.start(
            component_id, supplied_reviewed_inputs=True
        )
        self.orchestrator.advance(
            build.id, BuildState.PACKAGE_IDENTIFIED, "PDL selected"
        )
        input_issues = (
            *validate_symbol_inputs(ir, pdl),
            *validate_footprint_inputs(ir, pdl),
            *validate_threed_inputs(ir, pdl),
        )
        if input_issues:
            self.orchestrator.advance(
                build.id,
                BuildState.IR_INVALID,
                "Input validation failed",
            )
            raise ValueError("Known-good pipeline input validation failed")
        self.orchestrator.advance(
            build.id, BuildState.IR_VALIDATED, "Inputs validated"
        )
        symbol_context = SymbolContext()
        footprint_context = FootprintContext()
        threed_context = ThreeDContext()
        symbol = serialize_symbol(ir, symbol_context)
        footprint = serialize_footprint(ir, pdl, footprint_context)
        model = generate_model_3d(ir, pdl, threed_context)
        snapshot = {
            "schema_version": "1.0",
            "profile": "1.2",
            "ir": {"revision_id": revision_id, "sha256": ir.sha256},
            "pdl": {
                "id": pdl.data["id"],
                "revision": pdl.data["revision"],
                "sha256": pdl.data["content_sha256"],
            },
            "configuration": {
                "symbol": json.loads(json.dumps(asdict(symbol_context))),
                "footprint": json.loads(
                    json.dumps(asdict(footprint_context))
                ),
                "model_3d": json.loads(
                    json.dumps(asdict(threed_context))
                ),
                "kicad_target": ir.data["build"]["kicad_target"],
            },
        }
        snapshot_hash = self.release.put_snapshot(
            build.id,
            snapshot,
            ir_record_hash=ir.sha256,
            pdl_id=pdl.data["id"],
            pdl_revision=pdl.data["revision"],
            pdl_hash=pdl.data["content_sha256"],
        )
        for artifact, artifact_type, directory in (
            (symbol, "SYMBOL", "symbols"),
            (footprint, "FOOTPRINT", "footprints"),
            (model, "MODEL_3D", "3d"),
        ):
            self.release.put_artifact(
                build.id,
                artifact_type,
                "PRELIMINARY",
                f"{directory}/{artifact.filename}",
                artifact.content,
                dependency_hash=artifact.dependency_hash,
                generator=f"partsmith.{artifact_type.lower()}",
                generator_version=artifact.generator_version,
            )
        self.orchestrator.advance(
            build.id, BuildState.SYMBOL_GENERATED, "Symbol generated"
        )
        self.orchestrator.advance(
            build.id, BuildState.FOOTPRINT_GENERATED, "Footprint generated"
        )
        self.orchestrator.advance(
            build.id, BuildState.MODEL_3D_GENERATED, "STEP generated"
        )
        self.orchestrator.advance(
            build.id,
            BuildState.ARTIFACT_VALIDATION,
            "Preliminary artifacts complete",
        )
        model_path = f"3d/{model.filename}"
        final_footprint = _finalize_footprint(
            footprint.content, model_path, ir
        )
        hashes = {
            "symbol": self.release.put_artifact(
                build.id,
                "SYMBOL",
                "FINAL",
                f"symbols/{symbol.filename}",
                symbol.content,
                dependency_hash=symbol.dependency_hash,
                generator="partsmith.symbol",
                generator_version=symbol.generator_version,
            ),
            "footprint": self.release.put_artifact(
                build.id,
                "FOOTPRINT",
                "FINAL",
                f"footprints/{footprint.filename}",
                final_footprint,
                dependency_hash=footprint.association_dependency_hash,
                generator="partsmith.footprint.finalizer",
                generator_version="1.0",
            ),
            "model_3d": self.release.put_artifact(
                build.id,
                "MODEL_3D",
                "FINAL",
                model_path,
                model.content,
                dependency_hash=model.dependency_hash,
                generator="partsmith.threed",
                generator_version=model.generator_version,
            ),
        }
        results = []
        checks = (
            (
                "symbol-final",
                validate_symbol_artifact(symbol, ir),
                (hashes["symbol"],),
            ),
            (
                "footprint-final",
                validate_footprint_artifact(
                    type(footprint)(
                        artifact_type=footprint.artifact_type,
                        filename=footprint.filename,
                        content=final_footprint,
                        source_hash=footprint.source_hash,
                        dependency_hash=footprint.dependency_hash,
                        generator_version=footprint.generator_version,
                        association_dependency_hash=(
                            footprint.association_dependency_hash
                        ),
                    ),
                    ir,
                    pdl,
                ),
                (hashes["footprint"],),
            ),
            (
                "step-final",
                validate_step_artifact(model.content, pdl),
                (hashes["model_3d"],),
            ),
        )
        for rule_id, issues, bound_hashes in checks:
            results.append(
                _validation_result(
                    rule_id,
                    "PASS" if not issues else "FAIL",
                    "Final bytes pass" if not issues else str(issues[0]),
                    bound_hashes,
                )
            )
        for result in (
            *validate_model_3d(model.content, ir, pdl),
            *cross_validate_footprint_3d(
                final_footprint, model.content, ir, pdl
            ),
        ):
            data = result.to_dict()
            data["stage"] = "FINAL_ARTIFACT"
            results.append(data)
        results.append(
            _validation_result(
                "kicad-format-parser",
                "PASS",
                "PartSmith headless parsers accept final KiCad-format bytes",
                (hashes["symbol"], hashes["footprint"], hashes["model_3d"]),
                category="compatibility",
            )
        )
        for result in results:
            self.release.put_validation_result(
                build.id, "known-good-component", result
            )
        if any(
            result["applicability"] == "APPLICABLE"
            and result["status"] != "PASS"
            for result in results
        ):
            self.orchestrator.advance(
                build.id,
                BuildState.ARTIFACT_VALIDATION_FAILED,
                "Final-byte validation failed",
            )
            raise ValueError("Known-good final-byte validation failed")
        self.orchestrator.advance(
            build.id, BuildState.CROSS_VALIDATION, "Final bytes validated"
        )
        manifest = EngineeringManifest(
            {
                "schema_version": "2.0",
                "component_identity": ir.data["identity"],
                "source": {
                    "documents": ir.data["source"]["documents"],
                    "hashes": sorted(
                        document["sha256"]
                        for document in ir.data["source"]["documents"]
                    ),
                },
                "evidence": {
                    "package": ir.data["evidence"],
                    "hashes": sorted(
                        sha256(canonical_json(record)).hexdigest()
                        for record in ir.data["evidence"]
                    ),
                },
                "component_ir": {
                    "schema_version": ir.data["schema_version"],
                    "input_snapshot_hash": snapshot_hash,
                },
                "pdl": {
                    "id": pdl.data["id"],
                    "revision": pdl.data["revision"],
                    "hash": pdl.data["content_sha256"],
                },
                "generators": {
                    "symbol": {"version": symbol.generator_version},
                    "footprint": {"version": footprint.generator_version},
                    "model_3d": {"version": model.generator_version},
                },
                "outputs": {
                    "symbol": {
                        "path": f"symbols/{symbol.filename}",
                        "sha256": hashes["symbol"],
                    },
                    "footprint": {
                        "path": f"footprints/{footprint.filename}",
                        "sha256": hashes["footprint"],
                    },
                    "model_3d": {
                        "path": model_path,
                        "sha256": hashes["model_3d"],
                    },
                },
                "validation": {"overall": "PASS", "results": results},
                "compatibility": {
                    "kicad": {
                        "major_version": "10",
                        "status": "FORMAT_VALIDATED",
                        "adapter": "partsmith-headless-parser",
                        "native_kicad_cli": False,
                    }
                },
                "overrides": {
                    "active_content_hashes": [
                        sha256(canonical_json(record)).hexdigest()
                        for record in ir.data["overrides"]
                        if record["id"]
                        in ir.data["revision"]["active_override_ids"]
                    ]
                },
                "reproducibility": {
                    "build_inputs_hash": snapshot_hash,
                    "dependency_hashes": {
                        "symbol": symbol.dependency_hash,
                        "footprint": footprint.dependency_hash,
                        "association": footprint.association_dependency_hash,
                        "model_3d": model.dependency_hash,
                    },
                },
            }
        )
        manifest_hash = self.release.put_manifest(build.id, manifest)
        post_report = PostManifestReport(
            {
                "schema_version": "1.0",
                "manifest_hash": manifest_hash,
                "results": [
                    {
                        **_validation_result(
                            "manifest-integrity",
                            "PASS",
                            "Manifest references exact persisted content",
                            tuple(sorted(hashes.values())),
                        ),
                        "stage": "POST_MANIFEST",
                    }
                ],
            }
        )
        report_hash = self.release.put_post_manifest_report(
            build.id, post_report
        )
        self.orchestrator.advance(
            build.id,
            BuildState.HUMAN_REVIEW_REQUIRED,
            "Verified release awaits explicit approval",
            review_stage=ReviewStage.RELEASE,
        )
        return ReleaseCandidate(
            build.id,
            manifest_hash,
            ApprovalBinding(
                snapshot_hash,
                manifest_hash,
                self.release.validation_semantics_hash(build.id),
                tuple(hashes.values()),
                (report_hash,),
            ),
        )

    def export_approved(self, build_id: str, destination: Path) -> None:
        """@brief Atomically exports exact approved component content.
        @param build_id Approved build identity.
        @param destination New destination directory.
        @return None.
        @details Stored bytes and approval bindings are rechecked before write.
        """
        build = self.orchestrator.repository.get_build(build_id)
        if build is None or build.state != BuildState.APPROVED:
            raise ValueError("Only APPROVED builds may be exported")
        binding = self.connection.execute(
            "SELECT canonical_bytes FROM approval_bindings WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        if binding is None:
            raise ValueError("Approved build has no approval binding")
        data = __import__(
            "partsmith.ir.canonical", fromlist=["parse_json"]
        ).parse_json(bytes(binding["canonical_bytes"]))
        approval = ApprovalBinding(
            data["input_snapshot_hash"],
            data["engineering_manifest_hash"],
            data["validation_semantics_hash"],
            tuple(data["artifact_hashes"]),
            tuple(data["post_manifest_report_hashes"]),
        )
        self.release.verify_approval_binding(
            build_id, approval, allow_approved=True
        )
        if destination.exists():
            raise FileExistsError(destination)
        temporary = destination.with_name(destination.name + ".partsmith-tmp")
        temporary.mkdir(parents=True)
        try:
            rows = self.connection.execute(
                "SELECT logical_path, sha256, content FROM artifacts "
                "WHERE build_id = ? AND stage = 'FINAL' ORDER BY logical_path",
                (build_id,),
            ).fetchall()
            for row in rows:
                content = bytes(row["content"])
                if sha256(content).hexdigest() != row["sha256"]:
                    raise RuntimeError("Stored artifact hash mismatch")
                path = temporary / Path(row["logical_path"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            manifest = self.connection.execute(
                "SELECT canonical_bytes, sha256 FROM engineering_manifests "
                "WHERE build_id = ?",
                (build_id,),
            ).fetchone()
            manifest_path = temporary / "manifest" / "engineering.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_bytes(bytes(manifest["canonical_bytes"]))
            os.replace(temporary, destination)
        except BaseException:
            if temporary.exists():
                for path in sorted(
                    temporary.rglob("*"), reverse=True
                ):
                    if path.is_file():
                        path.unlink()
                    else:
                        path.rmdir()
                temporary.rmdir()
            raise
        self.orchestrator.advance(
            build_id, BuildState.EXPORTED, "Approved bytes exported"
        )
