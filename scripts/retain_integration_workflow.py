"""@file retain_integration_workflow.py
@brief Retains exact receipts from an exercised desktop target.
@details Reads the owned authority store without importing it into sessions.
The receipt proves persisted publication and preservation, not UI interactions.
"""

import argparse
import json
import sqlite3
from hashlib import sha256
from pathlib import Path

from partsmith.ir.canonical import canonical_json, parse_json


def main():
    """@brief Copies exact published contracts and ordinary project artifacts.
    @return None.
    @details Refuses an existing output and checks the expected desktop update.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--publications", type=int, choices=(2, 3), default=2)
    args = parser.parse_args()
    metadata = parse_json((args.fixture / "workflow.json").read_bytes())
    project_id = metadata["target"]["project_id"]
    connection = sqlite3.connect(
        Path(metadata["authority_database"]).as_uri() + "?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    args.output.mkdir()

    def retain(identity, destination):
        """@brief Retains and verifies one exact immutable operational object.
        @param identity Persisted SHA-256 from a trusted publication row.
        @param destination Owned ordinary evidence file.
        @return Parsed detached contract.
        @details Never grants execution authority from copied bytes.
        """
        row = connection.execute(
            "SELECT content FROM integration_objects WHERE sha256=?",
            (identity,),
        ).fetchone()
        blob = bytes(row[0])
        assert sha256(blob).hexdigest() == identity
        destination.write_bytes(blob)
        return parse_json(blob)

    publications = list(
        connection.execute(
            "SELECT p.*, a.plan_hash, a.snapshot_hash FROM "
            "integration_publications p JOIN integration_attempts a "
            "ON a.id=p.attempt_id WHERE a.project_id=? ORDER BY p.rowid",
            (project_id,),
        )
    )
    assert len(publications) == args.publications
    manifests = []
    names = ("install", "update", "portable-update")[: args.publications]
    for row, name in zip(publications, names, strict=True):
        directory = args.output / name
        directory.mkdir()
        for field, filename in (
            ("receipt_hash", "publication.json"),
            ("journal_hash", "journal.json"),
            ("plan_hash", "plan.json"),
            ("snapshot_hash", "snapshot.json"),
        ):
            retain(row[field], directory / filename)
        manifest = retain(row["manifest_hash"], directory / "manifest.json")
        manifests.append(manifest)
        decision = connection.execute(
            "SELECT * FROM integration_decisions WHERE attempt_id=?",
            (row["attempt_id"],),
        ).fetchone()
        authorization = retain(
            decision["authorization_hash"], directory / "authorization.json"
        )
        retain(decision["audit_hash"], directory / "audit.json")
        retain(
            authorization["post_manifest_check_hash"],
            directory / "post-validation.json",
        )
        retain(
            manifest["semantic_validation_hash"],
            directory / "pre-validation.json",
        )
    first = {s["component_id"]: s for s in manifests[0]["sources"]}
    updated = {s["component_id"]: s for s in manifests[-1]["sources"]}
    assert first.keys() == updated.keys() and len(first) == 2
    unchanged = [key for key in first if first[key] == updated[key]]
    assert len(unchanged) == 1
    before_mapping = next(
        m
        for m in manifests[0]["mappings"]
        if m["component_id"] == unchanged[0]
    )
    after_mapping = next(
        m
        for m in manifests[-1]["mappings"]
        if m["component_id"] == unchanged[0]
    )
    assert before_mapping == after_mapping
    project = Path(metadata["project_path"])
    retained_files = {}
    for source in project.rglob("*"):
        if not source.is_file() or source.suffix == ".lck":
            continue
        relative = source.relative_to(project)
        destination = args.output / "project" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        destination.write_bytes(data)
        retained_files[relative.as_posix()] = sha256(data).hexdigest()
    assert retained_files["acceptance.kicad_pcb"] == (
        "637069b6bbf1a01fb9f4c27e70d463ba5307a4a8f93350666f765c7a6220333e"
    )
    assert retained_files["native-roundtrip.kicad_sch"] == (
        "4640368dc64a2647891babb84d4d4420e240699ed77c290d7b21db2a04da8e6a"
    )
    connection.close()
    receipt = {
        "schema_version": "partsmith-desktop-publication-evidence-1.0",
        "target": metadata["target"],
        "publication_count": len(publications),
        "unchanged_source_and_mapping": unchanged[0],
        "files": retained_files,
        "publication_receipts": [row["receipt_hash"] for row in publications],
        "manifest_hashes": [row["manifest_hash"] for row in publications],
        "live_authority": False,
    }
    (args.output / "receipt.json").write_bytes(canonical_json(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
