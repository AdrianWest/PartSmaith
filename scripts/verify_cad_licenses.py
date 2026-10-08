"""@file verify_cad_licenses.py
@brief Reproduces upstream DLL repair to verify original CAD vendor packages.
@details Producer-only pefile and delvewheel inspect copies without executing
native libraries. This verifies the additional CAD vendors, not a full SBOM.
"""

import argparse
import json
import re
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from delvewheel import _dll_list, _dll_utils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.bundle import file_identity  # noqa: E402
from partsmith.pcm.licensing import validate_cad_vendors  # noqa: E402
from partsmith.pcm.package import json_bytes  # noqa: E402
from partsmith.pcm.supply import _conda_stream  # noqa: E402


def verify(
    runtime: Path, cache: Path, lock_path: Path, ledger_path: Path
) -> dict:
    """@brief Verifies corresponding material and recreates all 24 DLLs.
    @param runtime Prepared production runtime directory.
    @param cache Original producer artifact cache.
    @param lock_path Current pinned runtime lock.
    @param ledger_path Reviewed additional CAD vendor ledger.
    @return Exact binary-source verification receipt.
    @details Changed packages, missing material and nonidentical repairs fail.
    Microsoft DLL bytes must also match their original bytes.
    """
    lock = json.loads(lock_path.read_bytes())
    ledger = json.loads(ledger_path.read_bytes())
    validate_cad_vendors(lock, ledger)
    if version("delvewheel") != "1.12.1" or version("pefile") != "2024.8.26":
        raise ValueError("CAD_REPAIR_TOOL_VERSION_CHANGED")
    excluded = next(
        value
        for pattern, value in _dll_list.ignore_by_abi_platform.items()
        if re.fullmatch(pattern, "cp312-win_amd64")
    )
    name_map = {
        PurePosixPath(b["original_member"]).name.lower(): b["binary"]
        for v in ledger["vendors"]
        for b in v["binaries"]
    }
    records = []
    with tempfile.TemporaryDirectory(prefix="partsmith-cad-audit-") as temp:
        working = Path(temp)
        for vendor in ledger["vendors"]:
            for entry in (
                list(vendor["build_inputs"].values())
                + vendor["sources"]
                + [{"path": p, **r} for p, r in vendor["notices"].items()]
            ):
                if file_identity(runtime / entry["path"]) != {
                    k: entry[k] for k in ("sha256", "size")
                }:
                    raise ValueError("CAD_RETAINED_MATERIAL_CHANGED")
            package = cache / vendor["package"]
            if file_identity(package) != {
                k: vendor["package_identity"][k] for k in ("sha256", "size")
            }:
                raise ValueError("CAD_ORIGINAL_PACKAGE_CHANGED")
            selected = {b["original_member"]: b for b in vendor["binaries"]}
            found = set()
            with ZipFile(package) as archive:
                with _conda_stream(archive, "pkg") as stream:
                    for member in stream:
                        if member.name not in selected:
                            continue
                        if not member.isfile():
                            raise ValueError("CAD_ORIGINAL_BINARY_NOT_REGULAR")
                        binary = selected[member.name]
                        path = working / binary["binary"]
                        path.write_bytes(stream.extractfile(member).read())
                        original = file_identity(path)
                        if original["sha256"] != binary["original_sha256"]:
                            raise ValueError("CAD_ORIGINAL_BINARY_CHANGED")
                        needed = _dll_utils.get_direct_mangleable_needed(
                            str(path), excluded, set()
                        )
                        if needed != binary["dependencies"]:
                            raise ValueError("CAD_REPAIR_DEPENDENCIES_CHANGED")
                        _dll_utils.replace_needed(
                            str(path), needed, name_map, False
                        )
                        repaired = file_identity(path)
                        installed = file_identity(runtime / binary["path"])
                        if repaired != installed or (
                            repaired["sha256"] != binary["bundled_sha256"]
                        ):
                            raise ValueError(
                                "CAD_REPAIRED_BINARY_NOT_IDENTICAL"
                            )
                        found.add(member.name)
                        records.append(
                            {
                                "path": binary["path"],
                                "vendor": vendor["name"],
                                "version": vendor["version"],
                                "original": original,
                                "repaired": repaired,
                                "installed": installed,
                                "match": "EXACT_BYTES",
                            }
                        )
            if found != set(selected):
                raise ValueError("CAD_ORIGINAL_BINARY_MISSING")
    return {
        "schema_version": "partsmith-cad-source-verification-1.0",
        "state": "PASS",
        "scope": ledger["scope"],
        "full_native_runtime_approval": False,
        "lock": file_identity(lock_path),
        "ledger": file_identity(ledger_path),
        "vendors": len(ledger["vendors"]),
        "binaries": records,
        "static_jxr": "MATCHED_FREEIMAGE_RENDERED_HOST_RECIPE",
    }


def main() -> int:
    """@brief Verifies the recorded CAD vendor material and writes a receipt.
    @return Zero after exact upstream repair reproduction succeeds.
    @details Does not update source bytes, locks or approval state.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--lock",
        type=Path,
        default=ROOT / "resources/runtime/production-lock.json",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "resources/licensing/cad-native/vendors.json",
    )
    args = parser.parse_args()
    receipt = verify(args.runtime, args.cache, args.lock, args.ledger)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json_bytes(receipt))
    print("PASS: reproduced", len(receipt["binaries"]), "additional CAD DLLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
