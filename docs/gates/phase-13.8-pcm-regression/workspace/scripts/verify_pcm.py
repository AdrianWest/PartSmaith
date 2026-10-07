"""@file verify_pcm.py
@brief Verifies PCM inventory and isolated offline resource loading.
@details Readiness may be verified separately against the real managed runtime.
"""

import argparse
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.package import (  # noqa: E402
    collect_payload,
    json_bytes,
    verify_pcm,
)

BOOTSTRAP = """
import json, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
import partsmith
assert Path(partsmith.__file__).resolve().is_relative_to(root)
from partsmith.pcm.runtime import verify_inventory
inventory = verify_inventory(root)
from partsmith.gui.scene import fixture_source
from importlib.resources import files
assert files('partsmith.persistence').joinpath('001_initial.sql').read_bytes()
assert files('partsmith.pdl').joinpath('pdl-1.0.schema.json').read_bytes()
assert files('partsmith.integration').joinpath(
    'integration-contracts-1.0.schema.json').read_bytes()
assert files('partsmith.release').joinpath(
    'runtime-constraints.txt').read_bytes()
fixture = fixture_source()
assert fixture.step and fixture.footprint and fixture.placement
print(json.dumps({'state': 'OFFLINE_PAYLOAD_VERIFIED',
                  'members': len(inventory['files'])}))
"""


def main() -> int:
    """@brief Verifies final archive bytes, parity and isolated imports.
    @return Zero on complete source/payload verification.
    @details Child cwd has no checkout; isolated Python uses supplied payload.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    metadata = verify_pcm(archive)
    expected = collect_payload(ROOT)
    with ZipFile(archive) as source:
        for name, blob in expected.items():
            if source.read(name) != blob:
                raise ValueError("PCM source/resource parity failed")
        with TemporaryDirectory(prefix="partsmith-pcm-verify-") as directory:
            temporary = Path(directory)
            source.extractall(temporary / "payload")
            unrelated = temporary / "unrelated"
            unrelated.mkdir()
            child = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    BOOTSTRAP,
                    str(temporary / "payload/plugins"),
                ],
                cwd=unrelated,
                check=True,
                capture_output=True,
                text=True,
                timeout=90,
            )
    report = {
        "state": "OFFLINE_PAYLOAD_VERIFIED",
        "version": metadata["versions"][0]["version"],
        "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "source_resource_parity": True,
        "isolated": json.loads(child.stdout),
        "engineering_readiness_claim": False,
    }
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_bytes(json_bytes(report))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
