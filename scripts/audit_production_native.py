"""@file audit_production_native.py
@brief Inventories native wheel binaries without claiming license approval.
@details Producer-only pefile reads version resources without loading DLLs.
Binary versions are observations, not verified upstream source provenance.
"""

import argparse
import json
from pathlib import Path

import pefile

from partsmith.pcm.bundle import file_identity


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
    @details Every native wheel remains pending vendor-level review, including
    static dependencies that PE filename/version metadata cannot enumerate.
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
    components = []
    for component in lock["components"]:
        binaries = []
        for name in component["files"]:
            record = lock["files"][name]
            if not record["artifact"].endswith(".whl") or Path(
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
                    "vendor_license_review": "PENDING",
                    "binaries": binaries,
                }
            )
    report = {
        "schema_version": "partsmith-native-license-audit-1.0",
        "state": "PENDING_VENDOR_AUDIT",
        "runtime_lock_sha256": file_identity(args.lock)["sha256"],
        "scope": "Exact native wheel binary inventory; no license approval",
        "required_review": [
            "Identify every dynamic and static upstream vendor dependency",
            "Verify exact vendor version, source and build provenance",
            "Retain required original license and copyright notices",
            "Satisfy applicable source and redistribution obligations",
        ],
        "known_gap": (
            "cadquery_ocp.libs contains FreeImage, FreeType, OpenEXR/Imath, "
            "LibRaw and codec binaries without a complete vendor notice set"
        ),
        "components": components,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", "utf-8"
    )
    print(
        "Inventoried", len(components), "native wheels; vendor audit pending"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
