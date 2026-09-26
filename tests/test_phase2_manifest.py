"""Gate evidence must identify exact bytes, including line endings."""

import json
from hashlib import sha256

import pytest

from scripts.verify_phase2_manifest import verify


@pytest.mark.parametrize("replacement", [b"changed\n", b"valid\r\n", None])
def test_manifest_rejects_changed_or_missing_bytes(tmp_path, replacement):
    source = tmp_path / "input.txt"
    source.write_bytes(b"valid\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sha256": {
                    "input.txt": sha256(source.read_bytes()).hexdigest()
                },
            }
        )
    )
    assert verify(manifest, tmp_path) == []
    if replacement is None:
        source.unlink()
    else:
        source.write_bytes(replacement)
    assert verify(manifest, tmp_path) == [
        "Missing: input.txt"
        if replacement is None
        else "Hash mismatch: input.txt"
    ]


def test_manifest_rejects_paths_outside_repository(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sha256": {"../outside": "0" * 64}}))
    assert verify(manifest, tmp_path) == ["Outside repository: ../outside"]
