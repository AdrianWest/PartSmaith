"""@file audit_production_native.py
@brief Inventories native runtime binaries and records verified CAD vendors.
@details Producer-only pefile reads version resources without loading DLLs.
Binary versions are observations, not verified upstream source provenance.
"""

import argparse
import json
import sys
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.bundle import file_identity  # noqa: E402
from partsmith.pcm.licensing import validate_cad_vendors  # noqa: E402


def versions(path: Path) -> dict[str, str]:
    """@brief Reads declared PE version strings from one native binary.
    @param path Exact locked binary to inspect.
    @return FileVersion and ProductVersion when declared, otherwise empty.
    @details No native code executes; absent metadata remains unknown.
    """
    result = {}
    with pefile.PE(str(path), fast_load=True) as image:
        image.parse_data_directories(
            directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]
            ]
        )
        for group in getattr(image, "FileInfo", []):
            for info in group:
                for table in getattr(info, "StringTable", []):
                    for key, value in table.entries.items():
                        name = key.decode("utf-8", "replace")
                        if name in {"FileVersion", "ProductVersion"}:
                            result[name] = value.decode("utf-8", "replace")
    return result


def main() -> int:
    """@brief Writes exact binary identities and remaining audit obligations.
    @return Zero after every inspected binary matches the production lock.
    @details The 24 additional CAD DLLs have separate reproduced-source proof.
    Other static dependencies cannot be approved from PE metadata alone.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path("resources/runtime/production-lock.json"),
    )
    args = parser.parse_args()
    lock = json.loads(args.lock.read_bytes())
    ledger_path = Path("resources/licensing/cad-native/vendors.json")
    ledger = json.loads(ledger_path.read_bytes())
    validate_cad_vendors(lock, ledger)
    components = []
    for component in lock["components"]:
        if component["name"].startswith("cad-vendor-"):
            continue
        binaries = []
        for name in component["files"]:
            record = lock["files"][name]
            if name.startswith("licenses/") or Path(
                name
            ).suffix.lower() not in {".dll", ".pyd", ".exe"}:
                continue
            path = args.runtime / name
            identity = file_identity(path)
            if identity != {key: record[key] for key in ("size", "sha256")}:
                raise ValueError("AUDIT_INPUT_CHANGED: " + name)
            binaries.append(
                {
                    "path": name,
                    **identity,
                    "declared_pe_versions": versions(path),
                }
            )
        if binaries:
            components.append(
                {
                    "name": component["name"],
                    "version": component["version"],
                    "source": component["source"],
                    "original_archive_sha256": component["sha256"],
                    "retained_notices": component["license_files"],
                    "vendor_license_review": (
                        "ADDITIONAL_DLLS_VERIFIED_SDK_STATIC_INPUTS_PENDING"
                        if component["name"] == "cadquery-ocp"
                        else "PENDING_SOURCE_CLOSURE"
                    ),
                    "binaries": binaries,
                }
            )
    report = {
        "schema_version": "partsmith-native-license-audit-2.0",
        "state": "BLOCKED_NATIVE_SOURCE_PROVENANCE",
        "runtime_lock_sha256": file_identity(args.lock)["sha256"],
        "scope": (
            "Exact native runtime inventory and additional CAD vendor proof"
        ),
        "required_review": [
            "Identify every dynamic and static upstream vendor dependency",
            "Verify exact vendor version, source and build provenance",
            "Retain required original license and copyright notices",
            "Satisfy applicable source and redistribution obligations",
        ],
        "verified_additional_cad_vendors": {
            "state": ledger["state"],
            "ledger": ledger_path.as_posix(),
            "ledger_identity": file_identity(ledger_path),
            "vendors": len(ledger["vendors"]),
            "dynamic_dlls": 24,
            "static_dependency": "JPEG XR 1.1 in FreeImage",
            "scope": ledger["scope"],
            "receipt": (
                "docs/gates/phase-14-license-audit/cad-verification.json"
            ),
        },
        "known_gaps": [
            "OCP/OCCT cached SDK and header-only inputs are not pinned fully",
            "CasADi external source refs include master/develop/main",
            "Other native wheels need static/dynamic vendor source closure",
            "OCR GPL/LGPL libraries need corresponding source/build closure",
        ],
        "components": components,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", "utf-8"
    )
    print(
        "Inventoried",
        len(components),
        "native runtime components; 20 additional CAD vendors verified;",
        "full native source closure blocked",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
