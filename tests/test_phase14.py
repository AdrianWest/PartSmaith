"""@package tests.test_phase14
@brief Checks the production closure and frozen eight-variant corpus.
@details Archive tests use an inert tiny runtime; only the installed-runtime
acceptance runner can prove the native executables work on Windows.
"""

import copy
import json
import stat
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest

from partsmith.pcm import supply
from partsmith.pcm.acceptance import run_corpus
from partsmith.pcm.bundle import (
    PackagingPolicy,
    confined_file,
    file_identity,
    validate_dependencies,
    verify_bundle,
)
from partsmith.pcm.package import collect_payload, json_bytes, verify_pcm
from partsmith.pcm.production import build_production_pcm, metadata
from partsmith.pdl import (
    PDLValidationError,
    load_pdl,
    pdl_hash,
    resolve_pdl,
    validate_pdl,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def production_archive(tmp_path_factory):
    """@brief Builds a real production-format archive with inert runtime bytes.
    @param tmp_path_factory Isolated source and runtime directory factory.
    @return Verified archive path and its independent payload mapping.
    @details Does not claim these fake native executables are runnable.
    """
    folder = tmp_path_factory.mktemp("phase14-archive")
    source, runtime = folder / "source", folder / "runtime"
    (source / "resources/runtime").mkdir(parents=True)
    runtime.mkdir()
    files = {}
    for name, blob in {
        "runtime/python.exe": b"MZ inert test interpreter",
        "runtime/python312._pth": b"upstream path file",
        "runtime/LICENSE.txt": b"CPython original notice",
        "launchers/t64.exe": b"MZ inert console launcher",
        "launchers/w64.exe": b"MZ inert GUI launcher",
        "licenses/distlib/LICENSE.txt": b"distlib original notice",
        "ocr/bin/tesseract.exe": b"MZ inert OCR executable",
        "licenses/ocr/LICENSE.txt": b"OCR original notice",
    }.items():
        path = runtime / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        files[name] = file_identity(path)
    components = []
    for name, prefix, license_path in (
        ("CPython", "runtime/", "runtime/LICENSE.txt"),
        ("distlib-launcher", "launchers/", "licenses/distlib/LICENSE.txt"),
        ("OCR", "ocr/", "licenses/ocr/LICENSE.txt"),
    ):
        components.append(
            {
                "name": name,
                "version": "1.0",
                "source": "https://example.org/",
                "sha256": "a" * 64,
                "license": "test fixture notice",
                "platform": "Windows",
                "architecture": "AMD64",
                "files": sorted(
                    {n for n in files if n.startswith(prefix)} | {license_path}
                ),
                "license_files": {license_path: files[license_path]},
            }
        )
    (source / "resources/runtime/production-lock.json").write_bytes(
        json_bytes(
            {
                "python_version": "3.12.10",
                "files": files,
                "components": components,
            }
        )
    )
    payload = collect_payload(ROOT)

    def declared_payload(root):
        """@brief Supplies the independently assembled source payload.
        @param root Inert source root containing the test lock.
        @return Fresh payload mapping.
        @details Production byte verification still runs without substitution.
        """
        assert root == source
        return payload.copy()

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "partsmith.pcm.production.collect_payload", declared_payload
        )
        archive = folder / "production.zip"
        build_production_pcm(source, runtime, archive)
    with ZipFile(archive) as package:
        members = {n: package.read(n) for n in package.namelist()}
    return archive, members


def write_archive(path: Path, members: dict) -> None:
    """@brief Writes independently altered regular-file ZIP members.
    @param path Destination archive.
    @param members Name-to-byte payload mapping.
    @return None.
    @details Uses stored members so failures test their intended boundary.
    """
    with ZipFile(path, "w", compression=ZIP_STORED) as package:
        for name, blob in members.items():
            info = ZipInfo(name)
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            package.writestr(info, blob)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-runtime",
        "corrupt-runtime",
        "license-changed",
        "undeclared",
        "registration",
        "dependency-coverage",
        "unknown-dependency-field",
        "unknown-descriptor-field",
        "traversal",
        "case-alias",
    ],
)
def test_production_archive_fails_closed(production_archive, tmp_path, fault):
    """@brief Rejects corrupt or inconsistent executable PCM payloads.
    @param production_archive Original production-format archive and members.
    @param tmp_path Independent tampered archive destination.
    @param fault Selected archive fault.
    @return None.
    @details Structural tests repair inventory hashes so integrity failures
    cannot hide weakened registration, descriptor or ownership validation.
    """
    members = production_archive[1].copy()
    if fault == "missing-runtime":
        del members["plugins/runtime/python.exe"]
    elif fault == "corrupt-runtime":
        members["plugins/runtime/python.exe"] += b"corrupt"
    elif fault == "license-changed":
        members["plugins/runtime/LICENSE.txt"] += b"removed attribution"
    elif fault == "undeclared":
        members["plugins/runtime/foreign.pyd"] = b"foreign"
    elif fault in {"traversal", "case-alias"}:
        name = (
            "plugins/../outside"
            if fault == "traversal"
            else "Plugins/entry.py"
        )
        members[name] = b"wrong"
    else:
        target = "plugins/plugin.json"
        if fault == "registration":
            document = json.loads(members[target])
            document["actions"][0]["scopes"] = ["schematic"]
        elif fault == "unknown-descriptor-field":
            target = "plugins/bundle.json"
            document = json.loads(members[target])
            document["fallback_python"] = "system"
        else:
            target = "plugins/dependencies.json"
            document = json.loads(members[target])
            if fault == "dependency-coverage":
                document["components"][0]["files"].remove("runtime/python.exe")
            else:
                document["components"][0]["fallback"] = True
        members[target] = json_bytes(document)
        inventory = json.loads(members["plugins/inventory.json"])
        inventory["files"][target.removeprefix("plugins/")] = {
            "sha256": sha256(members[target]).hexdigest(),
            "size": len(members[target]),
        }
        if target.endswith("dependencies.json"):
            descriptor = json.loads(members["plugins/bundle.json"])
            descriptor["dependency_manifest_sha256"] = sha256(
                members[target]
            ).hexdigest()
            members["plugins/bundle.json"] = json_bytes(descriptor)
            inventory["files"]["bundle.json"] = {
                "sha256": sha256(members["plugins/bundle.json"]).hexdigest(),
                "size": len(members["plugins/bundle.json"]),
            }
        members["plugins/inventory.json"] = json_bytes(inventory)
        for _ in range(10):
            size = sum(map(len, members.values()))
            members["metadata.json"] = json_bytes(metadata("0.2.0", size))
            if size == sum(map(len, members.values())):
                break
    path = tmp_path / "bad.zip"
    write_archive(path, members)
    with pytest.raises(ValueError):
        verify_pcm(path)


def test_installed_bundle_and_notice_coverage(production_archive, tmp_path):
    """@brief Verifies byte ownership and original license identities.
    @param production_archive Original verified production-format archive.
    @param tmp_path Fresh extraction directory.
    @return None.
    @details Interpreter checks remain explicitly disabled for inert fixtures.
    """
    for name, blob in production_archive[1].items():
        if name.startswith("plugins/"):
            path = tmp_path / name.removeprefix("plugins/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
    assert (
        verify_bundle(tmp_path, interpreter=False)["python_version"]
        == "3.12.10"
    )
    bytecode = tmp_path / "unowned.pyc"
    bytecode.write_bytes(b"unverified compiled application code")
    with pytest.raises(ValueError, match="BYTECODE_FORBIDDEN"):
        verify_bundle(tmp_path, interpreter=False)
    bytecode.unlink()
    manifest = json.loads((tmp_path / "dependencies.json").read_bytes())
    inventory = json.loads((tmp_path / "inventory.json").read_bytes())
    bad = copy.deepcopy(manifest)
    bad["components"][0]["license_files"] = {}
    with pytest.raises(ValueError, match="LICENSE_MISSING"):
        validate_dependencies(bad, inventory["files"])
    (tmp_path / "runtime/LICENSE.txt").write_bytes(b"altered license")
    with pytest.raises(ValueError, match="RESOURCE_CHANGED"):
        verify_bundle(tmp_path, interpreter=False)


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "C:/escape",
        "a\\b",
        "aux.txt",
        "dir/CON",
        "dir/ads:x",
        "dir/trailing.",
        "dir/trailing ",
        "./file",
        "/absolute",
    ],
)
def test_installed_paths_are_portable_and_confined(tmp_path, name):
    """@brief Rejects Windows aliases and escaping owned paths.
    @param tmp_path Intended installed root.
    @param name Unsafe relative inventory name.
    @return None.
    @details No path is opened or created by the rejected lookup.
    """
    with pytest.raises(ValueError, match="UNSAFE_PATH"):
        confined_file(tmp_path, name)


def test_producer_download_has_a_hard_size_bound(tmp_path, monkeypatch):
    """@brief Rejects an oversized upstream response before cache publication.
    @param tmp_path Independent producer cache and output.
    @param monkeypatch Upstream response substitution helper.
    @return None.
    @details A declared one-byte artifact cannot consume unbounded disk.
    """
    lock = tmp_path / "lock.json"
    lock.write_bytes(
        json_bytes(
            {
                "schema_version": "partsmith-production-lock-1.0",
                "files": {},
                "artifacts": {
                    "input.txt": {
                        "url": "https://example.org/input",
                        "kind": "raw",
                        "size": 1,
                        "sha256": sha256(b"x").hexdigest(),
                    }
                },
            }
        )
    )

    def response(url, timeout):
        """@brief Supplies a malicious oversized HTTPS body.
        @param url Requested producer artifact URL.
        @param timeout Producer request timeout.
        @return Bounded in-memory test response.
        @details No network request is performed.
        """
        return BytesIO(b"x" * 4096)

    monkeypatch.setattr(supply, "urlopen", response)
    with pytest.raises(ValueError, match="ARTIFACT_OVERSIZED"):
        supply.prepare_supply(lock, tmp_path / "cache", tmp_path / "output")
    assert not (tmp_path / "cache/input.txt").exists()
    assert (tmp_path / "cache/input.txt.partial").stat().st_size == 1
    with pytest.raises(ValueError, match="RESOURCE_LIMIT"):
        PackagingPolicy().require_sizes([3 * 1024**3 + 1])


def test_full_eight_variant_frozen_release_corpus():
    """@brief Checks all frozen manufacturer-backed outputs through KiCad.
    @return None.
    @details Exercises measured CLASS_A rules, independent malformed models,
    exact-byte regeneration and the mandatory native release pipeline.
    """
    report = run_corpus(ROOT / "fixtures/production")
    assert report["state"] == "PASS"
    assert len(report["variants"]) == 8
    for result in report["variants"].values():
        assert result["accuracy_class"] == "CLASS_A"
        assert result["reproducibility"] == "EXACT_BYTES"
        assert result["native_compatibility"] == "PASS"
        assert len(result["negative_cases"]) >= 7
        assert result["measured_rules"]
    with pytest.raises(PDLValidationError, match="PDL_AMBIGUOUS"):
        resolve_pdl("chip_resistor", "0402", {"1", "2"})


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate-profile",
        "unknown-terminal",
        "flat-profile",
        "outside-marker",
        "missing-marker",
        "oversized-profile",
    ],
)
def test_production_geometry_declarations_fail_closed(fault):
    """@brief Rejects invalid frozen geometry before invoking the CAD kernel.
    @param fault Independent malformed PDL 1.1 declaration.
    @return None.
    @details Repairs the PDL hash so semantic and resource checks are tested.
    """
    data = load_pdl("ti-soic8", "1.0").data
    model = data["model_3d"]
    if fault == "duplicate-profile":
        model["lead_profiles"].append(copy.deepcopy(model["lead_profiles"][0]))
    elif fault == "unknown-terminal":
        data["mechanical"]["terminals"][0]["terminal_id"] = "UNKNOWN"
    elif fault == "flat-profile":
        model["lead_profiles"][0]["points_mm"] = [[i, 0] for i in range(4)]
    elif fault == "outside-marker":
        model["pin1_marker"]["center_mm"][0] = 50
    elif fault == "missing-marker":
        del model["pin1_marker"]
    else:
        model["lead_profiles"][0]["points_mm"] *= 100
    data["content_sha256"] = pdl_hash(data)
    assert validate_pdl(data)


def test_native_runtime_rejects_external_cad_and_redistributables(
    tmp_path, monkeypatch
):
    """@brief Rejects process-native fallback outside the owned runtime.
    @param tmp_path Independent Windows and runtime origin fixture.
    @param monkeypatch Current-process module enumeration substitution.
    @return None.
    @details Preinstalled Visual C++ cannot substitute for bundled libraries.
    """
    from partsmith.pcm import native

    root = tmp_path / "bundle"
    windows = tmp_path / "Windows"
    root.mkdir()
    windows.mkdir()
    monkeypatch.setenv("SystemRoot", str(windows))
    paths = [root / "runtime/python312.dll", windows / "System32/kernel32.dll"]

    def modules():
        """@brief Supplies process-module origin fixtures.
        @return Current immutable module-path sequence.
        @details Does not call Windows APIs during portable source tests.
        """
        return tuple(paths)

    monkeypatch.setattr(native, "loaded_modules", modules)
    registered = {}

    def extensions():
        """@brief Supplies the independently registered provider paths.
        @return Exact approved test provider mapping.
        @details No signature or registry result is inferred from a directory.
        """
        return registered

    monkeypatch.setattr(native, "registered_extensions", extensions)
    assert native.verify_native_origins(root)["windows_modules"] == 1
    for external in (
        tmp_path / "preinstalled/OCP.pyd",
        windows / "System32/msvcp140.dll",
    ):
        paths.append(external)
        with pytest.raises(ValueError, match="NATIVE_EXTERNAL_LIBRARY"):
            native.verify_native_origins(root)
        paths.pop()
    provider = tmp_path / "registered/provider.dll"
    provider.parent.mkdir()
    provider.write_bytes(b"registered signed provider fixture")
    registered[provider] = "REGISTERED_SIGNED_AMSI_PROVIDER"
    paths.append(provider)
    assert native.verify_native_origins(root)["registered_system_extensions"]
    for unexpected in (
        provider.parent / "OCP.dll",
        provider.parent / "msvcp140.dll",
    ):
        paths.append(unexpected)
        if unexpected.name == "msvcp140.dll":
            registered[unexpected] = "SIGNED_AMSI_REGISTRY_HELPER"
        with pytest.raises(ValueError, match="NATIVE_EXTERNAL_LIBRARY"):
            native.verify_native_origins(root)
        paths.pop()
        registered.pop(unexpected, None)
