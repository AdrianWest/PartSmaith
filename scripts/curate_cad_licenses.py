"""@file curate_cad_licenses.py
@brief Retains verified CAD vendor sources, notices and build recipes.
@details Maintainer-only curation consumes byte-for-byte DLL repair evidence.
It does not approve the other native wheels or resolve unpinned build inputs.
"""

import argparse
import json
import shutil
import sys
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.bundle import file_identity  # noqa: E402
from partsmith.pcm.package import _safe_name, json_bytes  # noqa: E402
from partsmith.pcm.supply import _conda_stream  # noqa: E402


def retain_core_material(
    lock: dict, ledger: dict, evidence: Path, cache: Path
) -> None:
    """@brief Retains core source material and original audit tool notices.
    @param lock Mutable production input lock.
    @param ledger Mutable vendor evidence ledger.
    @param evidence Reviewed source and producer-tool plan directory.
    @param cache Producer archive cache.
    @return None.
    @details Core material is available source, not approval of cached SDK
    provenance. Every original archive and original license member is hashed.
    """
    for source in json.loads(
        (evidence / "cad-core-sources.json").read_bytes()
    ):
        path = evidence / "sources" / source["filename"]
        identity = {k: source[k] for k in ("sha256", "size")}
        if file_identity(path) != identity:
            raise ValueError("CAD_CORE_SOURCE_CHANGED")
        shutil.copyfile(path, cache / path.name)
        lock["artifacts"][path.name] = identity | {
            "kind": "raw",
            "url": source["url"],
        }
        target = "licenses/cad-native/sources/" + path.name
        lock["files"][target] = identity | {
            "artifact": path.name,
            "member": ".",
        }
        if path.name.startswith("occt"):
            name, version = "OCCT-corresponding-source", "7.9.3"
            notices = [
                "licenses/OCCT-7.9.3.txt",
                "licenses/OCCT-exception-7.9.3.txt",
            ]
            license_name = "LGPL-2.1-only WITH OCCT-exception-1.0"
        else:
            name = "OCP-" + (
                "build-recipes"
                if path.name.startswith("ocp-build")
                else "generated-source"
            )
            version = "7.9.3.1.1"
            notices = ["runtime/Lib/site-packages/cadquery_ocp/LICENSE"]
            license_name = "Apache-2.0"
        lock["components"].append(
            {
                "name": name,
                "version": version,
                "source": source["url"],
                "sha256": source["sha256"],
                "license": license_name,
                "platform": "Windows",
                "architecture": "AMD64",
                "files": sorted([target] + notices),
                "license_files": {
                    n: {k: lock["files"][n][k] for k in ("sha256", "size")}
                    for n in notices
                },
            }
        )
        ledger.setdefault("core_source_material", []).append(
            source
            | {
                "path": target,
                "scope": (
                    "Upstream declared sources and recipes; "
                    "cached SDK build inputs still unverified"
                ),
            }
        )
    for tool in json.loads((evidence / "cad-tools.json").read_bytes()):
        path = cache / Path(tool["path"]).name
        identity = {k: tool[k] for k in ("sha256", "size")}
        if file_identity(path) != identity:
            raise ValueError("CAD_REPAIR_TOOL_ARCHIVE_CHANGED")
        lock["artifacts"][path.name] = identity | {
            "kind": "raw",
            "url": tool["source"],
        }
        target = tool["path"]
        lock["files"][target] = identity | {
            "artifact": path.name,
            "member": ".",
        }
        notice_aid = "notices-" + path.name
        shutil.copyfile(path, cache / notice_aid)
        lock["artifacts"][notice_aid] = identity | {
            "kind": "wheel",
            "url": tool["source"],
        }
        notices = {}
        with ZipFile(path) as archive:
            for member in tool["original_notice_members"]:
                blob = archive.read(member)
                name = (
                    "licenses/cad-native/tools/"
                    + tool["name"]
                    + "/"
                    + Path(member).name
                )
                _safe_name(name)
                record = {
                    "sha256": sha256(blob).hexdigest(),
                    "size": len(blob),
                }
                lock["files"][name] = record | {
                    "artifact": notice_aid,
                    "member": member,
                }
                notices[name] = record
                retained = (
                    ROOT
                    / "resources/licensing/cad-native"
                    / (name.removeprefix("licenses/cad-native/"))
                )
                retained.parent.mkdir(parents=True, exist_ok=True)
                retained.write_bytes(blob)
        lock["components"].append(
            {
                "name": "cad-audit-tool-" + tool["name"],
                "version": tool["version"],
                "source": tool["source"],
                "sha256": tool["sha256"],
                "license": "MIT",
                "platform": "Windows",
                "architecture": "AMD64",
                "files": [target] + list(notices),
                "license_files": notices,
            }
        )
        ledger.setdefault("producer_tools", []).append(tool)


def curate(evidence: Path, cache: Path, lock_path: Path) -> dict:
    """@brief Adds independently identified vendors to the production lock.
    @param evidence Directory containing original archives and repair evidence.
    @param cache Producer supply cache receiving immutable source inputs.
    @param lock_path Base production lock updated after successful curation.
    @return Vendor evidence ledger with exact binary and notice identities.
    @details Source hashes must equal original package recipes; native runtime
    bytes remain unchanged. Original notices and recipes retain their bytes.
    """
    lock = json.loads(lock_path.read_bytes())
    if any(c["name"].startswith("cad-vendor-") for c in lock["components"]):
        raise ValueError("CAD_VENDOR_SUPPLEMENT_ALREADY_PRESENT")
    vendors = json.loads((evidence / "cad-source-plan.json").read_bytes())
    ledger = {
        "schema_version": "partsmith-cad-vendors-1.0",
        "state": "ADDITIONAL_CAD_VENDORS_VERIFIED",
        "scope": "24 additional CAD DLLs and statically linked JPEG XR",
        "wheel": lock["artifacts"][
            "cadquery_ocp-7.9.3.1.1-cp312-cp312-win_amd64.whl"
        ],
        "repair_tool": {"name": "delvewheel", "version": "1.12.1"},
        "occt_binaries": {
            n: {k: r[k] for k in ("sha256", "size")}
            for n, r in lock["files"].items()
            if n.startswith("runtime/Lib/site-packages/cadquery_ocp.libs/TK")
            and n.endswith(".dll")
        },
        "vendors": [],
        "remaining_scope": [
            "OCCT and OCP header-only dependencies and cached SDK provenance",
            "Static/dynamic vendor closure in the other native runtime wheels",
        ],
    }
    cache.mkdir(parents=True, exist_ok=True)
    retained = ROOT / "resources/licensing/cad-native"

    def artifact(path: Path, url: str, kind: str) -> str:
        """@brief Records one verified original supply artifact.
        @param path Immutable artifact available in the maintainer cache.
        @param url Exact upstream retrieval URL.
        @param kind Raw or Conda extraction strategy.
        @return Artifact identifier.
        @details Rejects filename collisions with different source bytes.
        """
        name = path.name
        record = file_identity(path) | {"url": url, "kind": kind}
        if name in lock["artifacts"] and lock["artifacts"][name] != record:
            raise ValueError("CAD_SOURCE_ARTIFACT_COLLISION: " + name)
        lock["artifacts"][name] = record
        destination = cache / name
        if path.resolve() != destination.resolve():
            shutil.copyfile(path, destination)
        return name

    def member(aid: str, origin: str, target: str, blob: bytes) -> None:
        """@brief Records exact original notices, build inputs or source bytes.
        @param aid Original supply artifact identifier.
        @param origin Member inside that archive or dot for a raw artifact.
        @param target Installed license-directory destination.
        @param blob Original member bytes.
        @return None.
        @details Duplicated source ownership must retain identical bytes.
        """
        _safe_name(target)
        record = {
            "artifact": aid,
            "member": origin,
            "sha256": sha256(blob).hexdigest(),
            "size": len(blob),
        }
        if target in lock["files"] and lock["files"][target] != record:
            raise ValueError("CAD_SOURCE_MEMBER_COLLISION: " + target)
        lock["files"][target] = record
        if origin != ".":
            output = retained / target.removeprefix("licenses/cad-native/")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(blob)

    for vendor in vendors:
        name, version = vendor["name"], vendor["version"]
        package = evidence / "packages" / vendor["package"]
        aid = artifact(
            package,
            "https://conda.anaconda.org/conda-forge/win-64/" + package.name,
            "conda",
        )
        notices, owned, original_members = {}, [], {}
        with ZipFile(package) as archive:
            for kind in ("info", "pkg"):
                with _conda_stream(archive, kind) as stream:
                    for entry in stream:
                        if not entry.isfile() or not (
                            entry.name.startswith(
                                ("info/licenses/", "info/recipe/")
                            )
                            or entry.name
                            in {"info/about.json", "info/index.json"}
                        ):
                            continue
                        _safe_name(entry.name)
                        blob = stream.extractfile(entry).read()
                        target = (
                            "licenses/cad-native/"
                            + name
                            + "/"
                            + entry.name.removeprefix("info/")
                        )
                        member(aid, entry.name, target, blob)
                        owned.append(target)
                        original_members[entry.name] = {
                            "path": target,
                            **file_identity(
                                retained
                                / target.removeprefix("licenses/cad-native/")
                            ),
                        }
                        if entry.name.startswith("info/licenses/"):
                            notices[target] = {
                                k: lock["files"][target][k]
                                for k in ("sha256", "size")
                            }
        if not notices:
            raise ValueError("CAD_ORIGINAL_NOTICES_MISSING: " + name)
        sources = []
        for source in vendor["sources"]:
            if source.get("state") == "UNAVAILABLE":
                raise ValueError("CAD_CORRESPONDING_SOURCE_MISSING: " + name)
            path = evidence / "sources" / source["filename"]
            if file_identity(path) != {
                "sha256": source["sha256"],
                "size": source["size"],
            }:
                raise ValueError("CAD_CORRESPONDING_SOURCE_CHANGED: " + name)
            # Identical Microsoft redistributables have shared ownership.
            filename = (
                source["sha256"][:12]
                + "-"
                + (source["retrieval_url"].rsplit("/", 1)[-1])
            )
            shared = cache / filename
            if not shared.exists():
                shutil.copyfile(path, shared)
            source_aid = artifact(shared, source["retrieval_url"], "raw")
            target = "licenses/cad-native/sources/" + source_aid
            member(source_aid, ".", target, shared.read_bytes())
            owned.append(target)
            sources.append(
                {
                    "path": target,
                    "url": source["retrieval_url"],
                    "sha256": source["sha256"],
                    "size": source["size"],
                    "original_recipe_url": source["url"],
                }
            )
        binaries = []
        for binary in vendor["binaries"]:
            target = (
                "runtime/Lib/site-packages/cadquery_ocp.libs/"
                + binary["binary"]
            )
            if not binary["exact_repair_match"] or not (
                binary["bundled_sha256"]
                == binary["repaired_sha256"]
                == lock["files"][target]["sha256"]
            ):
                raise ValueError("CAD_ORIGINAL_BINARY_NOT_VERIFIED: " + target)
            owned.append(target)
            binaries.append(binary | {"path": target})
        selected = {
            "freeimage": "GPL-3.0-or-later",
            "freetype": "FTL",
        }.get(name, vendor["license"])
        if name == "jxrlib":
            parent = next(
                v for v in ledger["vendors"] if v["name"] == "freeimage"
            )
            owned += [b["path"] for b in parent["binaries"]]
        lock["components"].append(
            {
                "name": "cad-vendor-" + name,
                "version": version,
                "source": lock["artifacts"][aid]["url"],
                "sha256": lock["artifacts"][aid]["sha256"],
                "license": selected,
                "platform": "Windows",
                "architecture": "AMD64",
                "files": sorted(set(owned)),
                "license_files": notices,
            }
        )
        ledger["vendors"].append(
            {
                "name": name,
                "version": version,
                "build": vendor["build"],
                "package": aid,
                "package_identity": lock["artifacts"][aid],
                "declared_license": vendor["license"],
                "selected_license": selected,
                "notices": notices,
                "sources": sources,
                "build_inputs": original_members,
                "binaries": binaries,
                "linkage": "STATIC_IN_FREEIMAGE"
                if name == "jxrlib"
                else "DYNAMIC",
            }
        )
    names = [v["name"] for v in ledger["vendors"]]
    binary_names = [
        b["path"] for v in ledger["vendors"] for b in v["binaries"]
    ]
    if len(names) != 20 or len(set(binary_names)) != 24:
        raise ValueError("CAD_VENDOR_AUDIT_SCOPE_CHANGED")
    retain_core_material(lock, ledger, evidence, cache)
    lock["components"].sort(key=lambda c: c["name"].lower())
    lock["files"] = dict(sorted(lock["files"].items()))
    lock_path.write_bytes(json_bytes(lock))
    retained.mkdir(parents=True, exist_ok=True)
    (retained / "vendors.json").write_bytes(json_bytes(ledger))
    return ledger


def main() -> int:
    """@brief Freezes reviewed original vendor sources and notices.
    @return Zero after curation succeeds without changing native DLL bytes.
    @details An existing vendor supplement must not be applied twice.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()
    result = curate(args.evidence, args.cache, args.lock)
    print("Retained", len(result["vendors"]), "additional CAD vendors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
