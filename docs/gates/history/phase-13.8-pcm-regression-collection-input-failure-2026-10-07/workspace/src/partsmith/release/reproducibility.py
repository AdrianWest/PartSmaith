"""Build configuration, verified reuse, and reproducibility audits."""

import sqlite3
from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256

from partsmith.ir import canonical_json
from partsmith.ir.canonical import parse_json
from partsmith.persistence.database import utc_timestamp


def digest(value) -> str:
    return sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class BuildConfiguration:
    """Trusted effective settings; callers cannot narrow node declarations."""

    step_precision_mode: int = 0
    measurement_decimal_places: int = 12

    def __post_init__(self):
        if type(self.step_precision_mode) is not int or (
            self.step_precision_mode not in {-1, 0, 1}
        ):
            raise ValueError("Unsupported STEP precision mode")
        if type(self.measurement_decimal_places) is not int or not (
            6 <= self.measurement_decimal_places <= 15
        ):
            raise ValueError("Measurement reporting precision must be 6–15")

    def to_dict(self):
        return asdict(self)


class NodeCache:
    """Rehash every retained value before reuse; corrupt cache fails closed."""

    def __init__(self, connection: sqlite3.Connection, build_id: str):
        self.connection = connection
        self.build_id = build_id

    def obtain(self, kind, dependency, declaration, producer, *, reuse=True):
        row = (
            self.connection.execute(
                "SELECT * FROM node_cache WHERE node_kind = ? "
                "AND dependency_hash = ?",
                (kind, dependency),
            ).fetchone()
            if reuse
            else None
        )
        if row is not None:
            blob = bytes(row["canonical_bytes"])
            if sha256(blob).hexdigest() != row["content_sha256"]:
                raise RuntimeError(f"Cached {kind} content hash mismatch")
            value = parse_json(blob)
            action = "REUSE"
        else:
            value = producer()
            blob = canonical_json(value)
            content_hash = sha256(blob).hexdigest()
            existing = self.connection.execute(
                "SELECT content_sha256, canonical_bytes FROM node_cache "
                "WHERE node_kind = ? AND dependency_hash = ?",
                (kind, dependency),
            ).fetchone()
            if (
                existing is not None
                and sha256(bytes(existing[1])).hexdigest() != existing[0]
            ):
                raise RuntimeError(f"Cached {kind} content hash mismatch")
            if existing is not None and existing[0] != content_hash:
                raise RuntimeError(
                    f"Nondeterministic {kind} for pinned inputs"
                )
            self.connection.execute(
                "INSERT OR IGNORE INTO node_cache VALUES (?, ?, ?, ?, ?)",
                (kind, dependency, content_hash, blob, utc_timestamp()),
            )
            action = "REVALIDATE" if kind == "VALIDATION" else "GENERATE"
        now = utc_timestamp()
        self.connection.execute(
            "INSERT INTO build_dependencies "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.build_id,
                kind,
                dependency,
                action,
                declaration["id"],
                declaration["version"],
                canonical_json(declaration),
                now,
                now,
            ),
        )
        return value


def report_measurements(results: list[dict], places: int) -> list[dict]:
    """Versioned diagnostic formatting; pass/fail decisions remain measured."""

    def format_value(value):
        if isinstance(value, (float, Decimal)):
            return round(Decimal(str(value)), places)
        if isinstance(value, dict):
            return {key: format_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [format_value(item) for item in value]
        return value

    return [
        result | {"measured": format_value(result["measured"])}
        for result in results
    ]


def build_hashes(connection, build_id: str) -> dict:
    """Read verified deterministic content separately from truthful run IDs."""
    snapshot = connection.execute(
        "SELECT input_snapshot_hash, canonical_bytes FROM build_snapshots "
        "WHERE build_id = ?",
        (build_id,),
    ).fetchone()
    manifest = connection.execute(
        "SELECT * FROM engineering_manifests WHERE build_id = ?", (build_id,)
    ).fetchone()
    if snapshot is None or manifest is None:
        raise ValueError("Build is incomplete")
    if sha256(bytes(snapshot[1])).hexdigest() != snapshot[0] or (
        sha256(bytes(manifest["canonical_bytes"])).hexdigest()
        != manifest["sha256"]
    ):
        raise RuntimeError("Stored deterministic content hash mismatch")
    artifacts = {}
    for row in connection.execute(
        "SELECT * FROM artifacts WHERE build_id = ? AND stage = 'FINAL'",
        (build_id,),
    ):
        if sha256(bytes(row["content"])).hexdigest() != row["sha256"]:
            raise RuntimeError("Stored artifact content hash mismatch")
        artifacts[row["artifact_type"]] = row["sha256"]
    from partsmith.persistence import ReleaseStore

    return {
        "input_snapshot_hash": snapshot[0],
        "artifact_hashes": artifacts,
        "dependency_hashes": parse_json(bytes(snapshot[1]))["dependencies"],
        "validation_semantics_hash": ReleaseStore(
            connection
        ).validation_semantics_hash(build_id),
        "engineering_manifest_hash": manifest["sha256"],
    }


def comparison_report(left: dict, right: dict, *, left_run, right_run) -> dict:
    if set(left) != set(right) or set(left) != {
        "input_snapshot_hash",
        "artifact_hashes",
        "dependency_hashes",
        "validation_semantics_hash",
        "engineering_manifest_hash",
    }:
        raise ValueError("Comparison requires complete deterministic hashes")
    matches = {key: left[key] == right[key] for key in left}
    return {
        "schema_version": "1.0",
        "stage": "REPRODUCIBILITY",
        "status": "PASS" if all(matches.values()) else "FAIL",
        "left": left,
        "right": right,
        "matches": matches,
        "audit": {
            "left_run": left_run,
            "right_run": right_run,
            "compared_at": utc_timestamp(),
        },
    }
