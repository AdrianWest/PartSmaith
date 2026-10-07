"""@file verify_committed_gate_inputs.py
@brief Verifies active gate inputs against both HEAD blobs and disk bytes.
@details Consumes the hash-closeout catalog without changing manifests or
historical acceptance scope. Shared Git blobs are hashed only once.
"""

import argparse
import json
import subprocess
from hashlib import file_digest, sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """@brief Audits committed input maps and writes their exact result.
    @return Zero only when every recorded Git and disk identity matches.
    @details A receipt identifies the inspected commit. A later receipt-only
    commit does not broaden test acceptance or change the audited inputs.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closeout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    closeout = json.loads(args.closeout.read_bytes())
    git_hashes, disk_hashes, records, errors = {}, {}, 0, []
    names = closeout["verified_active_manifests"]
    for name in names:
        document = json.loads((ROOT / name).read_bytes())
        inputs = document.get("sha256", document.get("source_sha256", {}))
        for source, expected in inputs.items():
            records += 1
            if source not in git_hashes:
                blob = subprocess.check_output(
                    ["git", "show", "HEAD:" + source], cwd=ROOT
                )
                git_hashes[source] = sha256(blob).hexdigest()
                with (ROOT / source).open("rb") as stream:
                    disk_hashes[source] = file_digest(
                        stream, "sha256"
                    ).hexdigest()
            if (
                git_hashes[source] != expected
                or disk_hashes[source] != expected
            ):
                errors.append({"manifest": name, "path": source})
    if errors:
        raise ValueError("COMMITTED_INPUT_MISMATCH: " + json.dumps(errors))
    report = {
        "schema_version": "partsmith-committed-gate-inputs-1.0",
        "state": "PASS",
        "scope": "Exact input identities; no additional gate acceptance",
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "active_manifests": len(names),
        "ci_manifests": len(closeout["ci_manifests"]),
        "input_records": records,
        "unique_inputs": len(git_hashes),
        "git_blob_mismatches": 0,
        "disk_mismatches": 0,
        "verified_active_manifests": names,
    }
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", "utf-8"
    )
    print("PASS:", records, "input identities match HEAD and disk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
