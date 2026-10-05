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
from pathlib import Path, PurePosixPath

from partsmith.footprint import (
    FootprintContext,
    association_dependency_hash,
    footprint_dependency_hash,
    serialize_footprint,
    validate_footprint_artifact,
    validate_footprint_inputs,
)
from partsmith.footprint import (
    GeneratedArtifact as FootprintArtifact,
)
from partsmith.ir import ComponentIR, RequirementsContext, canonical_json
from partsmith.ir.projection import release_projection
from partsmith.kicad import (
    KiCadCompatibilityError,
    KiCadRuntime,
    discover_kicad,
    validate_native_artifacts,
)
from partsmith.pdl import PDL, load_release_profile, release_profile_hash
from partsmith.persistence import ImmutableStore, ReleaseStore
from partsmith.release.contracts import (
    ApprovalBinding,
    BuildState,
    EngineeringManifest,
    PostManifestReport,
    ReviewStage,
)
from partsmith.release.dependencies import node_dependency
from partsmith.release.reproducibility import (
    BuildConfiguration,
    NodeCache,
    digest,
    report_measurements,
)
from partsmith.release.runtime import runtime_configuration
from partsmith.release.workflow import BuildOrchestrator
from partsmith.symbol import (
    GeneratedArtifact as SymbolArtifact,
)
from partsmith.symbol import (
    SymbolContext,
    serialize_symbol,
    symbol_dependency_hash,
    validate_symbol_artifact,
    validate_symbol_inputs,
)
from partsmith.threed import (
    GeneratedArtifact as ModelArtifact,
)
from partsmith.threed import (
    ThreeDContext,
    cross_validate_footprint_3d,
    generate_model_3d,
    threed_dependency_hash,
    validate_model_3d,
    validate_step_artifact,
    validate_threed_inputs,
)
from partsmith.threed.step_backend import STEP_EXPORT_SETTINGS


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


def _portable_model_path(value: str) -> str:
    """@brief Validates one portable relative model association path.
    @param value Candidate slash-separated logical path.
    @return Normalized portable path.
    @details Absolute, parent-traversing, and backslash paths are rejected.
    """
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
    ):
        raise ValueError("Model path must be portable and relative")
    return path.as_posix()


def _final_footprint_dependency_hash(
    geometry_hash: str, association_hash: str, model_path: str
) -> str:
    """@brief Binds final footprint geometry and association inputs.
    @param geometry_hash Preliminary footprint dependency digest.
    @param association_hash Placement and pin-association dependency digest.
    @param model_path Portable logical STEP association path.
    @return Final-footprint dependency digest.
    @details Any geometry, placement, pin mapping, or path change invalidates
    final footprint checks and release approval.
    """
    return sha256(
        canonical_json(
            {
                "geometry": geometry_hash,
                "association": association_hash,
                "model_path": model_path,
            }
        )
    ).hexdigest()


class KnownGoodReleasePipeline:
    """@brief Runs the Phase 8 deterministic known-good component path.
    @details The pipeline stops at RELEASE review; authenticated approval is a
    separate explicit service operation.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        kicad_runtime: KiCadRuntime | None = None,
    ):
        """@brief Initializes the deterministic release pipeline.
        @param connection Migrated SQLite connection.
        @param kicad_runtime Optional pre-discovered native KiCad runtime.
        @return None.
        @details Missing target KiCad fails before any build is created.
        """
        self.connection = connection
        self.revisions = ImmutableStore(connection)
        self.release = ReleaseStore(connection)
        self.orchestrator = BuildOrchestrator(connection)
        self.kicad_runtime = kicad_runtime or discover_kicad()

    def run(
        self,
        component_id: str,
        revision_id: str,
        pdl: PDL,
        *,
        model_logical_path: str | None = None,
        configuration: BuildConfiguration | None = None,
        reuse: bool = True,
    ) -> ReleaseCandidate:
        """@brief Builds one reviewed component through release review.
        @param component_id Persisted component identity.
        @param revision_id Current reviewed IR revision identity.
        @param pdl Trusted selected package declaration.
        @param model_logical_path Optional portable final STEP path.
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
        settings = configuration or BuildConfiguration()
        runtime = runtime_configuration(self.kicad_runtime)
        symbol_context = SymbolContext(python_version=runtime["python"])
        footprint_context = FootprintContext(python_version=runtime["python"])
        threed_context = ThreeDContext(
            python_version=runtime["python"],
            step_precision_mode=settings.step_precision_mode,
        )
        model_path = _portable_model_path(
            model_logical_path
            or f"3d/{ir.data['identity']['normalized_mpn'].upper()}.step"
        )
        preliminary_dependencies = {
            "symbol": symbol_dependency_hash(ir, symbol_context),
            "footprint": footprint_dependency_hash(ir, pdl, footprint_context),
            "model_3d": threed_dependency_hash(ir, pdl, threed_context),
        }
        profile_binding = pdl.data["release_profile"]
        profile = load_release_profile(
            profile_binding["id"], profile_binding["version"]
        )
        if release_profile_hash(profile) != profile_binding["sha256"]:
            raise ValueError("Release profile hash mismatch")
        paths = (
            "/identity",
            "/electrical",
            "/pins",
            "/package",
            "/symbol",
            "/footprint",
            "/model_3d",
        )
        configuration = {
            "pdl": {
                "id": pdl.data["id"],
                "revision": pdl.data["revision"],
                "sha256": pdl.data["content_sha256"],
                "content": pdl.data,
            },
            "release_profile": {
                "id": profile_binding["id"],
                "version": profile_binding["version"],
                "sha256": profile_binding["sha256"],
                "accuracy_class": profile["required_model_accuracy"],
                "content": profile,
            },
            "runtime": runtime
            | {
                "symbol": json.loads(json.dumps(asdict(symbol_context))),
                "footprint": json.loads(json.dumps(asdict(footprint_context))),
                "model_3d": json.loads(json.dumps(asdict(threed_context))),
                "association": {"model_path": model_path, "version": "1.0"},
                "kicad_target": ir.data["build"]["kicad_target"],
                "validators": {
                    "settings": {
                        "measurement_decimal_places": (
                            settings.measurement_decimal_places
                        )
                    },
                    "input": {"id": "partsmith.ir", "version": "1.2"},
                    "artifact": {"id": "partsmith.phase8", "version": "1.0"},
                    "geometry": {"id": "partsmith.threed", "version": "1.0"},
                    "compatibility": {
                        "id": "kicad-cli",
                        "version": self.kicad_runtime.version,
                    },
                    "rules": pdl.data["validation"],
                    "ir_tolerances": ir.data["validation"]["tolerances"],
                },
                "manifest": {"schema_version": "2.0", "version": "1.1"},
            },
            "exporter": {
                "id": "cadquery.Shape.exportStep",
                "version": "2.8.0",
                **STEP_EXPORT_SETTINGS,
                "precision_mode": settings.step_precision_mode,
                "transfer_mode": "AsIs",
                "normalization": {
                    "id": "partsmith.step-metadata",
                    "version": "1.0",
                    "timestamp": "1970-01-01T00:00:00",
                    "entity_ids": "first-appearance",
                },
            },
        }
        node_records = {
            kind: node_dependency(
                ir, pdl, self.revisions, configuration, kind, context
            )
            for kind, context in (
                ("SYMBOL", symbol_context),
                ("FOOTPRINT", footprint_context),
                ("MODEL_3D", threed_context),
            )
        }
        dependencies = {
            name: node_records[kind][0]
            for name, kind in (
                ("symbol", "SYMBOL"),
                ("footprint", "FOOTPRINT"),
                ("model_3d", "MODEL_3D"),
            )
        }
        final_footprint_dependency = digest(
            {
                "footprint": dependencies["footprint"],
                "symbol": dependencies["symbol"],
                "model_3d": dependencies["model_3d"],
                "association": association_dependency_hash(ir),
                "model_path": model_path,
                "finalizer_version": "1.0",
            }
        )
        snapshot = release_projection(
            ir.data,
            requirements=RequirementsContext(
                "complete-component",
                "1.1",
                pdl.data["revision"],
                "1.0",
                paths,
                paths,
            ),
            revisions=self.revisions,
            configuration=configuration,
        )
        snapshot["dependencies"] = dependencies | {
            "association": final_footprint_dependency
        }
        snapshot_hash = self.release.put_snapshot(
            build.id,
            snapshot,
            ir_record_hash=ir.sha256,
            pdl_id=pdl.data["id"],
            pdl_revision=pdl.data["revision"],
            pdl_hash=pdl.data["content_sha256"],
        )
        cache = NodeCache(self.connection, build.id)

        def generate(kind, name, factory, producer):
            def produce():
                artifact = producer()
                if artifact.dependency_hash != preliminary_dependencies[name]:
                    raise RuntimeError(
                        "Generated dependency differs from frozen inputs"
                    )
                return {
                    "filename": artifact.filename,
                    "content_hex": artifact.content.hex(),
                    "generator_version": artifact.generator_version,
                }

            value = cache.obtain(
                kind,
                dependencies[name],
                node_records[kind][1],
                produce,
                reuse=reuse,
            )
            kwargs = {
                "artifact_type": kind,
                "filename": value["filename"],
                "content": bytes.fromhex(value["content_hex"]),
                "source_hash": ir.sha256,
                "dependency_hash": dependencies[name],
                "generator_version": value["generator_version"],
            }
            if kind == "FOOTPRINT":
                kwargs["association_dependency_hash"] = (
                    association_dependency_hash(ir)
                )
            return factory(**kwargs)

        symbol = generate(
            "SYMBOL",
            "symbol",
            SymbolArtifact,
            lambda: serialize_symbol(ir, symbol_context),
        )
        footprint = generate(
            "FOOTPRINT",
            "footprint",
            FootprintArtifact,
            lambda: serialize_footprint(ir, pdl, footprint_context),
        )
        model = generate(
            "MODEL_3D",
            "model_3d",
            ModelArtifact,
            lambda: generate_model_3d(ir, pdl, threed_context),
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
        final_value = cache.obtain(
            "ASSOCIATION",
            final_footprint_dependency,
            {"id": "partsmith.footprint.finalizer", "version": "1.0"},
            lambda: {
                "content_hex": _finalize_footprint(
                    footprint.content, model_path, ir
                ).hex()
            },
            reuse=reuse,
        )
        final_footprint = bytes.fromhex(final_value["content_hex"])
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
                dependency_hash=final_footprint_dependency,
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
        validation_dependency = digest(
            {
                "inputs": snapshot["inputs"],
                "artifacts": hashes,
                "validators": configuration["runtime"]["validators"],
                "runtime": runtime,
                "target": ir.data["build"]["kicad_target"],
            }
        )
        results = cache.obtain(
            "VALIDATION",
            validation_dependency,
            {"id": "partsmith.final-validation", "version": "1.0"},
            lambda: report_measurements(
                self._validate_final(
                    ir,
                    pdl,
                    symbol,
                    footprint,
                    model,
                    final_footprint,
                    hashes,
                    model_path,
                ),
                settings.measurement_decimal_places,
            ),
            reuse=reuse,
        )
        compatibility_result = results[-1]
        for result in results:
            result["id"] = f"{build.id}:{result['id']}"
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
                "component_identity": snapshot["inputs"]["/identity"],
                "source": {
                    "documents": list(
                        snapshot["provenance"]["documents"].values()
                    ),
                    "hashes": sorted(
                        document["sha256"]
                        for document in snapshot["provenance"][
                            "documents"
                        ].values()
                    ),
                },
                "evidence": {
                    "package": list(
                        snapshot["provenance"]["evidence"].values()
                    ),
                    "hashes": sorted(snapshot["provenance"]["evidence"]),
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
                "validation": {
                    "overall": "PASS",
                    "results": [
                        {
                            key: value
                            for key, value in result.items()
                            if key != "id"
                        }
                        for result in results
                    ],
                },
                "compatibility": {
                    "kicad": {
                        "major_version": "10",
                        "version": self.kicad_runtime.version,
                        "status": "NATIVE_VALIDATED",
                        "adapter": "kicad-cli",
                        "native_kicad_cli": True,
                        "operations": compatibility_result["measured"][
                            "operations"
                        ],
                    }
                },
                "overrides": {
                    "active_content_hashes": snapshot["decisions"]["overrides"]
                },
                "reproducibility": {
                    "build_inputs_hash": snapshot_hash,
                    "dependency_hashes": {
                        "symbol": symbol.dependency_hash,
                        "footprint": footprint.dependency_hash,
                        "association": final_footprint_dependency,
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
                        "id": f"{build.id}:phase8-manifest-integrity",
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

    def _validate_final(
        self,
        ir,
        pdl,
        symbol,
        footprint,
        model,
        final_footprint,
        hashes,
        model_path,
    ):
        """Validate the exact final bytes before recording reusable results."""
        results = []
        symbol_issues = validate_symbol_artifact(symbol, ir)
        footprint_issues = validate_footprint_artifact(
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
        )
        step_issues = validate_step_artifact(model.content, pdl)
        checks = (
            (
                "symbol-final",
                symbol_issues,
                (hashes["symbol"],),
            ),
            (
                "footprint-final",
                footprint_issues,
                (hashes["footprint"],),
            ),
            (
                "step-final",
                step_issues,
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
            data["validator"] = {"id": "partsmith.threed", "version": "1.0"}
            results.append(data)
        native_validation = None
        native_error = None
        internal_compatibility_passed = (
            ir.data["build"]["kicad_target"] == "10.x"
            and not symbol_issues
            and not footprint_issues
            and not step_issues
        )
        if internal_compatibility_passed:
            try:
                native_validation = validate_native_artifacts(
                    self.kicad_runtime,
                    target=ir.data["build"]["kicad_target"],
                    symbol_filename=symbol.filename,
                    symbol_content=symbol.content,
                    footprint_filename=footprint.filename,
                    footprint_content=final_footprint,
                    model_path=model_path,
                    model_content=model.content,
                )
            except KiCadCompatibilityError as error:
                native_error = str(error)
        compatibility_result = _validation_result(
            "kicad-native-compatibility",
            "PASS" if native_validation is not None else "FAIL",
            (
                "Native KiCad parsed, round-tripped, and rendered final bytes"
                if native_validation is not None
                else native_error
                or "Final bytes failed pre-native KiCad format validation"
            ),
            (hashes["symbol"], hashes["footprint"], hashes["model_3d"]),
            category="compatibility",
        )
        compatibility_result["validator"] = {
            "id": "kicad-cli",
            "version": self.kicad_runtime.version,
        }
        compatibility_result["measured"] = (
            {
                "target": ir.data["build"]["kicad_target"],
                "runtime_version": self.kicad_runtime.version,
                "operations": list(native_validation.operations),
            }
            if native_validation is not None
            else None
        )
        compatibility_result["expected"] = {
            "target_major": 10,
            "native_parse": True,
            "native_round_trip": True,
            "native_render": True,
        }
        results.append(compatibility_result)
        return results

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
                for path in sorted(temporary.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                    else:
                        path.rmdir()
                temporary.rmdir()
            raise
        self.orchestrator.advance(
            build_id, BuildState.EXPORTED, "Approved bytes exported"
        )
