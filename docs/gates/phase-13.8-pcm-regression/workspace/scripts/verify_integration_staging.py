"""@file verify_integration_staging.py
@brief Records real deterministic/native staging against explicit sources.
@details Opens the supplied application database read-only and creates only
a new owned disposable project/evidence directory. Grants no authority.
"""

import argparse
import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from partsmith.integration.planner import Planner
from partsmith.integration.staging import Stager
from partsmith.ir.canonical import canonical_json


def main() -> None:
    """@brief Runs two independent native stages and retains exact receipts.
    @return None.
    @details Refuses an existing output directory and preserves source bytes.
    A passing result supplies no authorization or publication acceptance.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--build", required=True, action="append")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    database = args.database.absolute()
    before = sha256(database.read_bytes()).hexdigest()
    output = args.output.absolute()
    output.mkdir()
    project = output / "project"
    project.mkdir()
    target = {
        "project_id": "phase13-staging-evidence",
        "library_id": "bft-library",
        "scope": "project-local",
    }
    with closing(
        sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    ) as c:
        c.row_factory = sqlite3.Row
        result = Planner(c).plan(project, target, args.build)
        one = Stager(c).stage(result, output)
        two = Stager(c).stage(result, output)
        assert one.objects == two.objects
        assert one.pre == two.pre and one.post == two.post
        assert one.manifest == two.manifest
        one.recheck()
    after = sha256(database.read_bytes()).hexdigest()
    assert before == after
    (output / "sources.db").write_bytes(database.read_bytes())
    for name, contract in (
        ("plan", result.plan),
        ("manifest", one.manifest),
        ("pre-validation", one.pre),
        ("post-validation", one.post),
    ):
        (output / (name + ".json")).write_bytes(contract.canonical_bytes)
    receipt = {
        "schema_version": "partsmith-native-staging-evidence-1.0",
        "status": "PASS",
        "publication": False,
        "authorization": False,
        "source_database_before_sha256": before,
        "source_database_after_sha256": after,
        "source_database_artifact": "sources.db",
        "plan_hash": result.plan.sha256,
        "manifest_hash": one.manifest.sha256,
        "pre_validation_hash": one.pre.sha256,
        "post_validation_hash": one.post.sha256,
        "identical_clean_runs": 2,
        "native_runs": [one.native_receipt, two.native_receipt],
        "files": one.manifest.data["files"],
    }
    (output / "receipt.json").write_bytes(canonical_json(receipt))
    print(f"PASS: two native stages; manifest {one.manifest.sha256}")


if __name__ == "__main__":
    main()
