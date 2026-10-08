"""@package partsmith.release.replay
@brief Verifies offline replay closure with retained approval audit.
@details Runtime resources match the executing Python baseline.
"""

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from partsmith.footprint import FootprintContext, association_dependency_hash
from partsmith.ir import ComponentIR, RequirementsContext, canonical_json
from partsmith.ir.canonical import parse_json
from partsmith.ir.projection import release_projection
from partsmith.ir.schema import load_schema as ir_schema
from partsmith.pdl import PDL
from partsmith.pdl.schema import load_schema as pdl_schema
from partsmith.persistence import ImmutableStore
from partsmith.persistence.database import savepoint, utc_timestamp
from partsmith.persistence.release import validation_semantics_hash
from partsmith.release.bundle import (
    RevisionBundle,
    RevisionBundleService,
    _safe_path,
)
from partsmith.release.contracts import (
    ApprovalBinding,
    BundleIndex,
    EngineeringManifest,
    PostManifestReport,
)
from partsmith.release.dependencies import node_dependency
from partsmith.release.pipeline import KnownGoodReleasePipeline
from partsmith.release.reproducibility import (
    BuildConfiguration,
    build_hashes,
    comparison_report,
    digest,
)
from partsmith.release.runtime import runtime_configuration
from partsmith.release.runtime_resources import runtime_resources
from partsmith.release.schema import load_schema as release_schema
from partsmith.schema_support import (
    decimal_validator_class,
    load_packaged_schema,
)
from partsmith.symbol import SymbolContext
from partsmith.threed import ThreeDContext


@dataclass(frozen=True)
class ReplayBundle:
    index: dict
    objects: dict[str, bytes]


def _inspection_hashes(ir):
    """Sources and diagram rasters needed for retained evidence inspection."""
    required = {document["sha256"] for document in ir["source"]["documents"]}

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "image_sha256" and item is not None:
                    required.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(ir)
    if ir["build"]["ai_provider"] is not None:
        raise ValueError("Recorded provider replay objects are not supported")
    return required


def _local_resources():
    """@brief Collects exact runtime resources and local replay schemas.
    @return Mapping of portable replay paths to verified resource bytes.
    @details The executing interpreter selects the reviewed runtime baseline.
    """
    lock, constraints = runtime_resources()
    return {
        "runtime/lock.json": lock,
        "runtime/constraints.txt": constraints,
        "schemas/ir.json": canonical_json(ir_schema("1.2")),
        "schemas/pdl.json": canonical_json(pdl_schema()),
        "schemas/release.json": canonical_json(release_schema()),
        "schemas/replay.json": canonical_json(_replay_schema()),
    }


def _replay_schema():
    name = "replay-bundle-1.0.schema.json"
    return load_packaged_schema(
        "partsmith.release",
        name,
        Path(__file__).resolve().parents[3] / "schemas" / name,
    )


def _object_kind(path):
    return {
        "ir": "IR_REVISION",
        "inventory": "ACQUISITION_INVENTORY",
        "source": "SOURCE",
        "schemas": "SCHEMA",
        "runtime": "RUNTIME",
        "inputs": "FROZEN_INPUT",
        "outputs": "FINAL_OUTPUT",
        "audit": "AUDIT",
        "history": "HISTORY_INDEX",
    }[path.split("/", 1)[0]]


class OfflineReplayService:
    """Verify every replay object before execution; never inherit approval."""

    def __init__(self, connection, *, kicad_runtime=None):
        self.connection = connection
        self.pipeline = KnownGoodReleasePipeline(
            connection, kicad_runtime=kicad_runtime
        )

    def export(self, build_id, bundle_id, *, source_objects):
        binding_row = self.connection.execute(
            "SELECT canonical_bytes FROM approval_bindings WHERE build_id = ?",
            (build_id,),
        ).fetchone()
        if binding_row is None:
            raise ValueError("Offline release requires explicit approval")
        binding = parse_json(bytes(binding_row[0]))
        self.pipeline.release.verify_approval_binding(
            build_id,
            ApprovalBinding(
                binding["input_snapshot_hash"],
                binding["engineering_manifest_hash"],
                binding["validation_semantics_hash"],
                tuple(binding["artifact_hashes"]),
                tuple(binding["post_manifest_report_hashes"]),
            ),
            allow_approved=True,
        )
        snapshot_row = self.connection.execute(
            "SELECT * FROM build_snapshots WHERE build_id = ?", (build_id,)
        ).fetchone()
        revision = self.connection.execute(
            "SELECT id FROM ir_revisions WHERE canonical_sha256 = ?",
            (snapshot_row["ir_record_hash"],),
        ).fetchone()
        history = RevisionBundleService(self.connection).export_revisions(
            bundle_id + "-history", revision[0]
        )
        snapshot_bytes = bytes(snapshot_row["canonical_bytes"])
        snapshot = parse_json(snapshot_bytes)
        objects = dict(history.objects)
        objects["history/index.json"] = history.index.canonical_bytes
        objects["inputs/snapshot.json"] = snapshot_bytes
        config = snapshot["configuration"]
        objects["inputs/pdl.json"] = canonical_json(config["pdl"]["content"])
        objects["inputs/profile.json"] = canonical_json(
            config["release_profile"]["content"]
        )
        objects["inputs/settings.json"] = canonical_json(
            {
                "step_precision_mode": config["exporter"]["precision_mode"],
                "measurement_decimal_places": config["runtime"]["validators"][
                    "settings"
                ]["measurement_decimal_places"],
            }
        )
        objects.update(_local_resources())
        for entry in history.index.data["objects"]:
            if entry["kind"] == "IR_REVISION":
                ir = parse_json(history.objects[entry["path"]])
                for source_hash in _inspection_hashes(ir):
                    content = source_objects.get(source_hash)
                    if (
                        content is None
                        or sha256(content).hexdigest() != source_hash
                    ):
                        raise ValueError("Required source object unavailable")
                    objects[f"source/{source_hash}"] = content
        for table, path, column in (
            (
                "engineering_manifests",
                "outputs/manifest.json",
                "canonical_bytes",
            ),
        ):
            row = self.connection.execute(
                f"SELECT {column} FROM {table} WHERE build_id = ?", (build_id,)
            ).fetchone()
            objects[path] = bytes(row[0])
        for row in self.connection.execute(
            "SELECT * FROM artifacts WHERE build_id = ? AND stage = 'FINAL'",
            (build_id,),
        ):
            objects["outputs/" + _safe_path(row["logical_path"])] = bytes(
                row["content"]
            )
        for table in (
            "build_dependencies",
            "validation_results",
            "post_manifest_reports",
            "approval_bindings",
            "release_decisions",
        ):
            rows = self.connection.execute(
                f"SELECT * FROM {table} WHERE build_id = ?", (build_id,)
            ).fetchall()
            objects[f"audit/{table}.json"] = canonical_json(
                [
                    {
                        key: (
                            bytes(row[key]).hex()
                            if isinstance(row[key], bytes)
                            else row[key]
                        )
                        for key in row.keys()
                    }
                    for row in rows
                ]
            )
        index = {
            "schema_version": "1.0",
            "bundle_id": bundle_id,
            "availability": "OFFLINE_COMPLETE",
            "original_run": build_id,
            "expected": build_hashes(self.connection, build_id),
            "objects": [
                {
                    "identity": path,
                    "kind": _object_kind(path),
                    "schema_version": "1.2"
                    if path.startswith("ir/")
                    else "1.0",
                    "path": path,
                    "byte_length": len(blob),
                    "sha256": sha256(blob).hexdigest(),
                }
                for path, blob in sorted(objects.items())
            ],
        }
        bundle = ReplayBundle(index, objects)
        self._verify(bundle)
        return bundle

    def _verify(self, bundle):
        index = bundle.index
        if not decimal_validator_class()(_replay_schema()).is_valid(index):
            raise ValueError("Invalid replay index schema")
        if (
            set(index)
            != {
                "schema_version",
                "bundle_id",
                "availability",
                "original_run",
                "expected",
                "objects",
            }
            or index["schema_version"] != "1.0"
            or (index["availability"] != "OFFLINE_COMPLETE")
            or not index["bundle_id"]
        ):
            raise ValueError("Unsupported replay index")
        declared = set()
        for entry in index["objects"]:
            if set(entry) != {
                "identity",
                "kind",
                "schema_version",
                "path",
                "byte_length",
                "sha256",
            }:
                raise ValueError("Invalid replay object declaration")
            path = _safe_path(entry["path"])
            if entry["identity"] != path or entry["kind"] != _object_kind(
                path
            ):
                raise ValueError("Replay object identity or kind mismatch")
            if path != entry["path"] or path in declared:
                raise ValueError("Duplicate or noncanonical replay path")
            declared.add(path)
            blob = bundle.objects.get(path)
            if (
                not isinstance(blob, bytes)
                or len(blob) != entry["byte_length"]
                or (sha256(blob).hexdigest() != entry["sha256"])
            ):
                raise ValueError("Replay object missing or hash mismatch")
        if declared != set(bundle.objects):
            raise ValueError("Undeclared replay object")
        required = {
            "history/index.json",
            "inputs/snapshot.json",
            "inputs/pdl.json",
            "inputs/profile.json",
            "inputs/settings.json",
            "outputs/manifest.json",
            *(
                f"audit/{name}.json"
                for name in (
                    "build_dependencies",
                    "validation_results",
                    "post_manifest_reports",
                    "approval_bindings",
                    "release_decisions",
                )
            ),
        }
        if not required <= declared:
            raise ValueError("Replay closure is incomplete")
        for path, blob in _local_resources().items():
            if bundle.objects.get(path) != blob:
                raise ValueError("Replay schema or runtime lock incompatible")
        snapshot = parse_json(bundle.objects["inputs/snapshot.json"])
        config = snapshot["configuration"]
        actual_runtime = runtime_configuration(self.pipeline.kicad_runtime)
        if any(
            config["runtime"].get(key) != value
            for key, value in actual_runtime.items()
        ):
            raise ValueError("Replay runtime mismatch")
        if digest(snapshot) != index["expected"]["input_snapshot_hash"]:
            raise ValueError("Replay snapshot identity mismatch")
        pdl = PDL(parse_json(bundle.objects["inputs/pdl.json"]))
        if pdl.data != config["pdl"]["content"] or (
            parse_json(bundle.objects["inputs/profile.json"])
            != config["release_profile"]["content"]
        ):
            raise ValueError("Replay configuration binding mismatch")
        settings = BuildConfiguration(
            **json.loads(bundle.objects["inputs/settings.json"])
        )
        if settings.step_precision_mode != config["exporter"][
            "precision_mode"
        ] or (
            settings.measurement_decimal_places
            != config["runtime"]["validators"]["settings"][
                "measurement_decimal_places"
            ]
        ):
            raise ValueError("Replay effective settings mismatch")
        manifest = EngineeringManifest(
            parse_json(bundle.objects["outputs/manifest.json"])
        ).data
        if digest(manifest) != index["expected"]["engineering_manifest_hash"]:
            raise ValueError("Replay manifest identity mismatch")
        for output in manifest["outputs"].values():
            blob = bundle.objects.get("outputs/" + _safe_path(output["path"]))
            if blob is None or sha256(blob).hexdigest() != output["sha256"]:
                raise ValueError("Replay final artifact missing or corrupt")
        expected = index["expected"]
        if (
            expected["dependency_hashes"] != snapshot["dependencies"]
            or (
                expected["artifact_hashes"]
                != {
                    {
                        "symbol": "SYMBOL",
                        "footprint": "FOOTPRINT",
                        "model_3d": "MODEL_3D",
                    }[kind]: output["sha256"]
                    for kind, output in manifest["outputs"].items()
                }
            )
            or validation_semantics_hash(manifest["validation"]["results"])
            != (expected["validation_semantics_hash"])
        ):
            raise ValueError("Replay deterministic binding mismatch")
        audit = {}
        for table in (
            "validation_results",
            "post_manifest_reports",
            "approval_bindings",
            "release_decisions",
        ):
            rows = parse_json(bundle.objects[f"audit/{table}.json"])
            if not rows:
                raise ValueError("Replay audit closure is empty")
            for row in rows:
                blob = bytes.fromhex(row["canonical_bytes"])
                content_hash = row.get("canonical_sha256", row.get("sha256"))
                if (
                    content_hash is not None
                    and sha256(blob).hexdigest() != content_hash
                ):
                    raise ValueError("Replay audit content binding mismatch")
                if row["build_id"] != index["original_run"]:
                    raise ValueError("Replay audit run binding mismatch")
            audit[table] = rows
        approvals = audit["approval_bindings"]
        if len(approvals) != 1:
            raise ValueError("Replay approval binding is ambiguous")
        approval = parse_json(bytes.fromhex(approvals[0]["canonical_bytes"]))
        if any(
            approval[key] != expected[key]
            for key in (
                "input_snapshot_hash",
                "engineering_manifest_hash",
                "validation_semantics_hash",
            )
        ) or set(approval["artifact_hashes"]) != set(
            expected["artifact_hashes"].values()
        ):
            raise ValueError("Replay approval content mismatch")
        reports = audit["post_manifest_reports"]
        if set(approval["post_manifest_report_hashes"]) != {
            row["sha256"] for row in reports
        }:
            raise ValueError("Replay post-manifest report closure mismatch")
        for row in reports:
            report = PostManifestReport(
                parse_json(bytes.fromhex(row["canonical_bytes"]))
            )
            if (
                report.data["manifest_hash"]
                != expected["engineering_manifest_hash"]
            ):
                raise ValueError(
                    "Replay post-manifest report binding mismatch"
                )
        if not any(
            row["id"] == approvals[0]["release_decision_id"]
            and row["decision"] == "APPROVE"
            and row["binding_sha256"] == approvals[0]["canonical_sha256"]
            for row in audit["release_decisions"]
        ):
            raise ValueError("Replay release approval audit missing")
        history_index = BundleIndex(
            parse_json(bundle.objects["history/index.json"])
        )
        history = RevisionBundle(
            history_index,
            {
                entry["path"]: bundle.objects[entry["path"]]
                for entry in history_index.data["objects"]
            },
        )
        RevisionBundleService(self.connection)._verified_objects(history)
        for entry in history_index.data["objects"]:
            if entry["kind"] == "IR_REVISION":
                ir = ComponentIR(parse_json(history.objects[entry["path"]]))
                for source_hash in _inspection_hashes(ir.data):
                    blob = bundle.objects.get(f"source/{source_hash}")
                    if blob is None or sha256(blob).hexdigest() != source_hash:
                        raise ValueError(
                            "Replay source inspection closure missing"
                        )
        return history, pdl, settings, snapshot

    def rebuild(self, bundle):
        history, pdl, settings, snapshot = self._verify(bundle)
        # The outer savepoint rolls back a failed import or content binding.
        with savepoint(self.connection, "offline_replay_import"):
            RevisionBundleService(self.connection).import_bundle(history)
            head = history.index.data["head_revision_id"]
            ir = ImmutableStore(self.connection).get_revision(head)
            paths = (
                "/identity",
                "/electrical",
                "/pins",
                "/package",
                "/symbol",
                "/footprint",
                "/model_3d",
            )
            projected = release_projection(
                ir,
                requirements=RequirementsContext(
                    "complete-component",
                    "1.1",
                    pdl.data["revision"],
                    "1.0",
                    paths,
                    paths,
                ),
                revisions=ImmutableStore(self.connection),
                configuration=snapshot["configuration"],
            )
            if projected != {
                key: value
                for key, value in snapshot.items()
                if key != "dependencies"
            }:
                raise ValueError("Replay history does not bind frozen inputs")
            runtime = snapshot["configuration"]["runtime"]
            component_ir = ComponentIR(ir)
            dependencies = {
                name: node_dependency(
                    component_ir,
                    pdl,
                    ImmutableStore(self.connection),
                    snapshot["configuration"],
                    kind,
                    context,
                )[0]
                for name, kind, context in (
                    (
                        "symbol",
                        "SYMBOL",
                        SymbolContext(python_version=runtime["python"]),
                    ),
                    (
                        "footprint",
                        "FOOTPRINT",
                        FootprintContext(python_version=runtime["python"]),
                    ),
                    (
                        "model_3d",
                        "MODEL_3D",
                        ThreeDContext(
                            python_version=runtime["python"],
                            step_precision_mode=settings.step_precision_mode,
                        ),
                    ),
                )
            }
            dependencies["association"] = digest(
                {
                    "footprint": dependencies["footprint"],
                    "symbol": dependencies["symbol"],
                    "model_3d": dependencies["model_3d"],
                    "association": association_dependency_hash(component_ir),
                    "model_path": runtime["association"]["model_path"],
                    "finalizer_version": "1.0",
                }
            )
            if dependencies != snapshot["dependencies"]:
                raise ValueError("Replay node dependency binding mismatch")
            now = utc_timestamp()
            for entry in bundle.index["objects"]:
                self.connection.execute(
                    "INSERT INTO bundle_objects VALUES "
                    "(?, ?, 'REPLAY_OBJECT', '1.0', ?, NULL, ?, ?, ?, ?, ?)",
                    (
                        bundle.index["bundle_id"],
                        entry["path"],
                        entry["path"],
                        entry["byte_length"],
                        entry["sha256"],
                        bundle.objects[entry["path"]],
                        now,
                        now,
                    ),
                )
            self.connection.execute(
                "INSERT INTO bundle_imports VALUES "
                "(?, ?, ?, 'OFFLINE_COMPLETE', 'IMPORTED', ?, ?, ?)",
                (
                    str(uuid4()),
                    bundle.index["bundle_id"],
                    digest(bundle.index),
                    canonical_json(bundle.index),
                    now,
                    now,
                ),
            )
        candidate = self.pipeline.run(
            history.index.data["component"]["id"],
            head,
            pdl,
            configuration=settings,
            reuse=False,
            model_logical_path=snapshot["configuration"]["runtime"][
                "association"
            ]["model_path"],
        )
        report = comparison_report(
            bundle.index["expected"],
            build_hashes(self.connection, candidate.build_id),
            left_run=bundle.index["original_run"],
            right_run=candidate.build_id,
        )
        self.connection.execute(
            "INSERT INTO reproducibility_reports VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                candidate.build_id,
                report["status"],
                digest(report),
                canonical_json(report),
                utc_timestamp(),
            ),
        )
        return candidate, report
