"""@file close_integration_gate.py
@brief Refreshes and verifies active gate input maps in dependency order.
@details Preserves historical receipts and records every changed input hash.
Gate acceptance checks must already have passed; this is hash closeout only.
"""

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date
from hashlib import sha256
from pathlib import Path, PureWindowsPath
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    """@brief Reads the exact finalized checkout file identity.
    @param path Explicit workspace file.
    @return Lowercase SHA-256.
    @details Missing files fail; no historical identity is inferred.
    """
    return sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: dict) -> None:
    """@brief Writes one UTF-8 LF closeout document.
    @param path Explicit owned receipt path.
    @param data JSON-compatible receipt mapping.
    @return None.
    @details Does not change historical source or test evidence.
    """
    path.write_text(json.dumps(data, indent=2) + "\n", "utf-8", newline="\n")


def verify_native_receipt(path: Path) -> None:
    """@brief Resolves current native receipt identities outside input maps.
    @param path Explicit finalized current-checkpoint receipt.
    @return None.
    @details Historical actor/transport identities keep their original scope;
    this verifies retained exact bytes without granting live authority.
    """
    receipt = json.loads(path.read_bytes())
    version = receipt.get("schema_version")
    if version == "partsmith-native-staging-evidence-1.0":
        for key, filename in (
            ("plan_hash", "plan.json"),
            ("manifest_hash", "manifest.json"),
            ("pre_validation_hash", "pre-validation.json"),
            ("post_validation_hash", "post-validation.json"),
        ):
            assert digest(path.parent / filename) == receipt[key]
        source = path.parent / receipt["source_database_artifact"]
        assert digest(source) == receipt["source_database_before_sha256"]
        assert digest(source) == receipt["source_database_after_sha256"]
        for run in receipt["native_runs"]:
            for operation in run["operations"]:
                for stream in ("stdout", "stderr"):
                    if stream + "_sha256" in operation:
                        assert (
                            sha256(operation[stream].encode()).hexdigest()
                            == (operation[stream + "_sha256"])
                        )
        for directory in path.parent.glob("stage-*"):
            for item in receipt["files"]:
                artifact = directory / item["path"]
                assert digest(artifact) == item["sha256"]
                assert artifact.stat().st_size == item["byte_length"]
    elif version == "partsmith-native-review-evidence-1.0":
        assert digest(path.parent / "audit.json") == receipt["audit_hash"]
        assert (
            digest(path.parent / "authorization.json")
            == receipt["authorization_hash"]
        )
        source = ROOT / "docs/gates/phase-13.4-native-staging/sources.db"
        assert digest(source) == receipt["original_database_before_sha256"]
        assert digest(source) == receipt["original_database_after_sha256"]

    elif version == "partsmith-native-publication-evidence-1.0":
        for operation, key in (
            ("install", "first_manifest_hash"),
            ("update", "updated_manifest_hash"),
            ("rollback", "rollback_manifest_hash"),
        ):
            directory = path.parent / operation
            assert digest(directory / "manifest.json") == receipt[key]
            publication = json.loads(
                (directory / "publication.json").read_bytes()
            )
            assert publication["manifest_hash"] == receipt[key]
            assert (
                digest(directory / "journal.json")
                == (publication["journal_hash"])
            )
            journal = json.loads((directory / "journal.json").read_bytes())
            assert (
                digest(directory / "authorization.json")
                == (journal["authorization_hash"])
            )
            assert (
                digest(directory / "post-validation.json")
                == (journal["post_manifest_check_hash"])
            )
            if operation in {"install", "rollback"}:
                key = (
                    "installation_receipt"
                    if operation == "install"
                    else "rollback_receipt"
                )
                assert digest(directory / "publication.json") == receipt[key]
            manifest = json.loads((directory / "manifest.json").read_bytes())
            slot = (
                path.parent
                / "managed"
                / "slots"
                / PureWindowsPath(publication["physical_slot"]).name
            )
            for item in manifest["files"]:
                artifact = slot / item["path"]
                assert digest(artifact) == item["sha256"]
                assert artifact.stat().st_size == item["byte_length"]
        source = ROOT / "docs/gates/phase-13.4-native-staging/sources.db"
        assert digest(source) == receipt["original_database_before_sha256"]
        assert digest(source) == receipt["original_database_after_sha256"]

    elif version == "partsmith-desktop-publication-evidence-1.0":
        names = ("install", "update", "portable-update")
        assert receipt["publication_count"] in (2, 3)
        for index in range(receipt["publication_count"]):
            directory = path.parent / names[index]
            assert (
                digest(directory / "publication.json")
                == (receipt["publication_receipts"][index])
            )
            assert (
                digest(directory / "manifest.json")
                == (receipt["manifest_hashes"][index])
            )
            publication = json.loads(
                (directory / "publication.json").read_bytes()
            )
            assert (
                publication["manifest_hash"]
                == (receipt["manifest_hashes"][index])
            )
            assert (
                digest(directory / "journal.json")
                == (publication["journal_hash"])
            )
            journal = json.loads((directory / "journal.json").read_bytes())
            assert (
                digest(directory / "authorization.json")
                == (journal["authorization_hash"])
            )
            assert (
                digest(directory / "post-validation.json")
                == (journal["post_manifest_check_hash"])
            )
        for name, expected in receipt["files"].items():
            assert digest(path.parent / "project" / name) == expected
        approved = path.parent / "approved-update-receipt.json"
        if approved.exists():
            identity = json.loads(approved.read_bytes())
            assert (
                digest(path.parent / "approved-components.partsmith")
                == (identity["archive_sha256"])
            )
            source = ROOT / "docs/gates/phase-13.4-native-staging/sources.db"
            assert (
                digest(source) == (identity["original_database_before_sha256"])
            )
            assert (
                digest(source) == (identity["original_database_after_sha256"])
            )

    elif version == "partsmith-native-roundtrip-evidence-1.0":
        assert receipt["status"] == "PASS"
        assert receipt["prepared_runtime"]["state"] == "READY"
        assert receipt["isolated_pcm_import"]
        for name, expected in receipt["files"].items():
            assert digest(path.parent / "relocated" / name) == expected
        assert len(receipt["commands"]) == 4
        assert all(c["exit_code"] == 0 for c in receipt["commands"])
        models = [c for c in receipt["commands"] if "solids" in c]
        assert len(models) == 2 and all(c["solids"] == 6 for c in models)

    elif version == "partsmith-pcm-acceptance-evidence-1.0":
        assert receipt["exit_code"] == 0
        origins = json.loads((path.parent / "origins.json").read_bytes())
        assert origins["isolated"] and not origins["repository_imports"]
        for name, expected in receipt["copied_input_hashes"].items():
            assert digest(path.parent / "workspace" / name) == expected
        payload = path.parent / "payload/plugins"
        inventory = json.loads((payload / "inventory.json").read_bytes())
        assert origins["version"] == inventory["version"]
        for name, identity in inventory["files"].items():
            assert digest(payload / name) == identity["sha256"]
            assert (payload / name).stat().st_size == identity["size"]
        assert origins["origins"]
        for name in origins["origins"].values():
            assert name in inventory["files"]
        suites = list(
            ET.parse(path.parent / "results.xml").getroot().iter("testsuite")
        )
        assert suites and sum(int(s.get("tests", 0)) for s in suites) > 0
        assert all(
            int(s.get(field, 0)) == 0
            for s in suites
            for field in ("failures", "errors", "skipped")
        )


def main() -> int:
    """@brief Completes exact disk-hash refresh and executable verification.
    @return Zero after all active and CI input maps verify.
    @details Archives each changed receipt before writing and rejects cycles.
    Git-blob verification remains due after the user commits these inputs.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    stamp = date.today().isoformat()
    if not re.fullmatch(r"13(?:\.[2-8])?", args.phase):
        parser.error("Expected integration milestone 13.2–13.8 or full 13")
    seed = json.loads(
        (
            ROOT / "docs/gates/phase-13.1-hash-closeout-2026-10-06.json"
        ).read_bytes()
    )
    names = set(seed["verified_active_manifests"])
    names.update(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "docs/gates").glob("phase-13.*-artifacts.json")
    )
    if (ROOT / "docs/gates/phase-13-artifacts.json").exists():
        names.add("docs/gates/phase-13-artifacts.json")
    documents = {
        name: json.loads((ROOT / name).read_bytes()) for name in names
    }
    ci = re.findall(
        r"--manifest (docs/gates/[\w.\-]+\.json)",
        (ROOT / ".github/workflows/ci.yml").read_text("utf-8"),
    )
    if not set(ci) <= names:
        raise ValueError("CI includes a manifest outside the active catalog")
    ordered = []
    visiting = set()

    def visit(name: str) -> None:
        """@brief Orders one active receipt after its referenced receipts.
        @param name Explicit active receipt path.
        @return None.
        @details A cycle is an error rather than a repeated hash refresh.
        """
        if name in ordered:
            return
        if name in visiting:
            raise ValueError("Active input maps contain a hash cycle")
        visiting.add(name)
        inputs = documents[name].get(
            "sha256", documents[name].get("source_sha256", {})
        )
        for dependency in sorted(set(inputs) & names):
            visit(dependency)
        visiting.remove(name)
        ordered.append(name)

    for name in sorted(names):
        visit(name)
    changes = []
    receipts = []
    for name in ordered:
        path = ROOT / name
        original = path.read_bytes()
        document = documents[name]
        changed = []
        # Only this named Phase 10 map is current outside its sha256 map.
        maps = ["sha256"] if "sha256" in document else ["source_sha256"]
        for field in maps:
            for source, previous in document[field].items():
                actual = digest(ROOT / source)
                if actual != previous:
                    item = {
                        "manifest": name,
                        "field": field,
                        "path": source,
                        "previous_sha256": previous,
                        "new_sha256": actual,
                    }
                    changed.append(item)
                    document[field][source] = actual
        if changed:
            archive = (
                ROOT
                / "docs/gates/history"
                / (path.stem + f"-before-phase-{args.phase}-{stamp}.json")
            )
            if archive.exists() and archive.read_bytes() != original:
                archive = archive.with_name(
                    archive.stem
                    + "-"
                    + sha256(original).hexdigest()[:12]
                    + archive.suffix
                )
                if archive.exists() and archive.read_bytes() != original:
                    raise ValueError("Historical archive identity collision")
            archive.write_bytes(original)
            write(path, document)
            receipts.append(
                {
                    "path": name,
                    "historical_path": archive.relative_to(ROOT).as_posix(),
                    "previous_sha256": sha256(original).hexdigest(),
                    "new_sha256": digest(path),
                }
            )
            changes.extend(changed)
    commands = []
    for name in ordered:
        document = json.loads((ROOT / name).read_bytes())
        if "sha256" not in document:
            assert name == "docs/gates/phase-10-parser-fix-2026-10-04.json"
            assert all(
                digest(ROOT / source) == expected
                for source, expected in document["source_sha256"].items()
            )
            commands.append(
                {
                    "verification": "Internal exact source_sha256 check",
                    "manifest": name,
                    "exit_code": 0,
                    "output": "PASS: all current source hashes match",
                }
            )
            continue
        command = [
            sys.executable,
            "scripts/verify_phase2_manifest.py",
            "--manifest",
            name,
            "--source",
            "disk",
        ]
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=True
        )
        commands.append(
            {
                "command": " ".join(command),
                "exit_code": result.returncode,
                "output": result.stdout.strip(),
            }
        )
    current = documents[f"docs/gates/phase-{args.phase}-artifacts.json"]
    artifact = current.get("pcm_package")
    if artifact:
        archive = ROOT / artifact["path"]
        assert digest(archive) == artifact["sha256"]
        assert archive.stat().st_size == artifact["byte_length"]
        with ZipFile(archive) as package:
            assert (
                sha256(package.read("plugins/inventory.json")).hexdigest()
                == artifact["inventory_sha256"]
            )
            assert len(package.namelist()) == artifact["members"]
            icon = artifact.get("package_icon")
            if icon:
                payload = package.read(icon["path"])
                assert sha256(payload).hexdigest() == icon["sha256"]
                assert len(payload) == icon["size"]
    for name in current.get("evidence", []):
        if name.endswith("/receipt.json"):
            verify_native_receipt(ROOT / name)
    if current.get("pcm_lifecycle"):
        lifecycle = json.loads((ROOT / current["pcm_lifecycle"]).read_bytes())
        assert lifecycle["status"] == "PASS"
        assert lifecycle["archive_sha256"] == artifact["sha256"]
        assert lifecycle["inventory_sha256"] == artifact["inventory_sha256"]
        with ZipFile(ROOT / artifact["path"]) as package:
            for name, expected in lifecycle[
                "installed_payload_hashes"
            ].items():
                assert (
                    sha256(package.read("plugins/" + name)).hexdigest()
                    == expected
                )
            assert (
                sha256(package.read("resources/icon.png")).hexdigest()
                == lifecycle["package_logo_sha256"]
            )
        assert (
            len(
                {
                    lifecycle[f"authority_{boundary}_sha256"]
                    for boundary in (
                        "before_removal",
                        "after_removal",
                        "after_reinstall",
                        "after_upgrade",
                    )
                }
            )
            == 1
        )
        for name in lifecycle["observations"].values():
            assert (ROOT / name).is_file()
        managed = json.loads(
            (ROOT / lifecycle["installed_runtime"]).read_bytes()
        )
        assert managed["state"] == "READY"
        assert managed["package_version"] == artifact["version"]
        assert managed["inventory_sha256"] == artifact["inventory_sha256"]
    output = ROOT / f"docs/gates/phase-{args.phase}-hash-closeout.json"
    if output.exists():
        previous = output.read_bytes()
        historical = (
            ROOT
            / "docs/gates/history"
            / (
                output.stem
                + "-before-revalidation-"
                + stamp
                + "-"
                + sha256(previous).hexdigest()[:12]
                + ".json"
            )
        )
        if historical.exists() and historical.read_bytes() != previous:
            raise ValueError("Historical closeout identity collision")
        historical.write_bytes(previous)
    write(
        output,
        {
            "phase": args.phase,
            "date": stamp,
            "status": "HASH_CLOSEOUT_VERIFIED",
            "reason": args.reason,
            "hash_source": "disk",
            "scope": "Final inputs; historical acceptance bytes retained",
            "git_blob_verification": "Due after current inputs are committed",
            "refreshed_manifests": receipts,
            "hash_changes": changes,
            "verified_active_manifests": ordered,
            "ci_manifests": ci,
            "verification_commands": commands,
            "current_gate_outside_map_identities": "PASS",
        },
    )
    print(f"PASS: {len(ordered)} active maps; {len(changes)} refreshed hashes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
