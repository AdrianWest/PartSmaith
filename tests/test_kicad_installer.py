"""@file test_kicad_installer.py
@brief Checks local installation, retained backups and transactional rollback.
@details Uses isolated KiCad directories and the real verified PCM package.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from partsmith.pcm.package import IDENTIFIER, VERSION, build_pcm
from partsmith.pcm.runtime import verify_inventory

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "local_kicad_installer", ROOT / "scripts/install_kicad.py"
)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


@pytest.fixture(scope="module")
def archive(tmp_path_factory):
    """@brief Builds one real PCM archive for installation scenarios.
    @param tmp_path_factory Isolated module-level artifact directory factory.
    @return Verified current development PCM archive path.
    @details No installed user package or configuration is accessed.
    """
    path = tmp_path_factory.mktemp("installer") / "partsmith.zip"
    build_pcm(ROOT, path)
    return path


@pytest.fixture
def target(tmp_path):
    """@brief Prepares isolated existing KiCad data and another package.
    @param tmp_path Isolated installation fixture directory.
    @return Settings and third-party root paths.
    @details Unknown registry fields and other package files must survive.
    """
    settings = tmp_path / "settings"
    third_party = tmp_path / "KiCad space/3rdparty"
    settings.mkdir()
    other = third_party / "plugins/other_package"
    other.mkdir(parents=True)
    (other / "keep.txt").write_bytes(b"another package's original bytes")
    (settings / "kicad_common.json").write_text(
        json.dumps({"api": {"interpreter_path": sys.executable}}),
        encoding="utf-8",
    )
    (settings / "installed_packages.json").write_text(
        json.dumps(
            {
                "unknown_setting": "preserve",
                "packages": [
                    {
                        "package": {"identifier": "other.package"},
                        "pinned": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return settings, third_party


def seed_old_plugin(third_party):
    """@brief Creates old installer-owned payload and resource markers.
    @param third_party Isolated KiCad content root.
    @return Old plugin and resource directory paths.
    @details The registration explicitly identifies the directory as owned.
    """
    plugin = third_party / "plugins" / INSTALLER.DIRECTORY
    resources = third_party / "resources" / INSTALLER.DIRECTORY
    plugin.mkdir(parents=True)
    resources.mkdir(parents=True)
    (plugin / "plugin.json").write_text(
        json.dumps({"identifier": IDENTIFIER}), encoding="utf-8"
    )
    (plugin / "old.txt").write_bytes(b"old plugin bytes")
    (resources / "icon.png").write_bytes(b"old icon bytes")
    return plugin, resources


@pytest.mark.parametrize("environment", [None, {"vars": None}, {"vars": {}}])
def test_default_installation_paths_accept_null_variables(
    target, monkeypatch, environment
):
    """@brief Resolves KiCad's default root with unset environment preferences.
    @param target Isolated settings and third-party fixture paths.
    @param monkeypatch Documents path and environment substitution helper.
    @param environment KiCad's omitted or nullable environment settings.
    @return None.
    @details Real KiCad writes null for the unused custom variables setting.
    """
    settings, _ = target
    (settings / "kicad_common.json").write_text(
        json.dumps({"environment": environment}), encoding="utf-8"
    )
    documents = settings / "Documents"
    monkeypatch.delenv("KICAD10_3RD_PARTY", raising=False)
    monkeypatch.setattr(INSTALLER, "documents_directory", lambda: documents)
    assert INSTALLER.installation_paths(settings) == (
        settings,
        documents / "KiCad/10.0/3rdparty",
    )


def test_upgrade_preserves_other_packages_and_retains_backup(archive, target):
    """@brief Verifies an upgrade publishes only owned paths and registration.
    @param archive Real verified PCM package.
    @param target Isolated settings and third-party paths.
    @return None.
    @details Backups live outside recursive KiCad plugin discovery.
    """
    settings, third_party = target
    plugin, resources = seed_old_plugin(third_party)
    registry = settings / "installed_packages.json"
    before = registry.read_bytes()
    report = INSTALLER.install_archive(archive, settings, third_party)
    assert verify_inventory(plugin)["version"] == VERSION
    assert not (plugin / "old.txt").exists()
    backup = Path(report["backup"])
    assert not backup.is_relative_to(third_party)
    assert (backup / "previous-plugin/old.txt").read_bytes() == (
        b"old plugin bytes"
    )
    assert (backup / "previous-resources/icon.png").read_bytes() == (
        b"old icon bytes"
    )
    assert (backup / "installed_packages.before.json").read_bytes() == before
    assert (third_party / "plugins/other_package/keep.txt").read_bytes() == (
        b"another package's original bytes"
    )
    after = json.loads(registry.read_bytes())
    assert after["unknown_setting"] == "preserve"
    assert after["packages"][0] == json.loads(before)["packages"][0]
    assert after["packages"][1]["current_version"] == VERSION
    assert (resources / "icon.png").read_bytes() != b"old icon bytes"


def test_registry_commit_failure_restores_prior_bytes(
    archive, target, monkeypatch
):
    """@brief Proves a failed final registry commit restores both old payloads.
    @param archive Real verified PCM package.
    @param target Isolated settings and third-party paths.
    @param monkeypatch Final filesystem commit substitution helper.
    @return None.
    @details Prior registration and other packages remain unchanged.
    """
    settings, third_party = target
    plugin, resources = seed_old_plugin(third_party)
    registry = settings / "installed_packages.json"
    before = registry.read_bytes()
    common = settings / "kicad_common.json"
    preferences = common.read_bytes()
    original = Path.replace

    def reject_commit(path, destination):
        """@brief Fails only publication of the final PCM registration.
        @param path Source path being replaced.
        @param destination Requested destination path.
        @return Original replacement result for non-commit moves.
        @details Rollback moves retain their real filesystem behavior.
        """
        if destination == registry:
            raise OSError("Simulated registry commit failure")
        return original(path, destination)

    monkeypatch.setattr(Path, "replace", reject_commit)
    with pytest.raises(OSError, match="Simulated registry"):
        INSTALLER.install_archive(
            archive,
            settings,
            third_party,
            python_interpreter=Path("C:/KiCad/bin/python.exe"),
        )
    assert registry.read_bytes() == before
    assert (plugin / "old.txt").read_bytes() == b"old plugin bytes"
    assert (resources / "icon.png").read_bytes() == b"old icon bytes"
    assert not (plugin / "inventory.json").exists()
    assert common.read_bytes() == preferences


def test_install_selects_bundled_python_with_preference_backup(
    archive, target
):
    """@brief Migrates the IPC interpreter while preserving other preferences.
    @param archive Real verified PCM package.
    @param target Isolated settings and third-party paths.
    @return None.
    @details The exact original settings remain available in the backup.
    """
    settings, third_party = target
    common = settings / "kicad_common.json"
    original = {
        "api": {
            "interpreter_path": "C:/old/python.exe",
            "enable_server": True,
        },
        "unknown": {"preserve": True},
    }
    common.write_text(json.dumps(original), encoding="utf-8")
    before = common.read_bytes()
    interpreter = Path("C:/KiCad space/bin/python.exe")
    report = INSTALLER.install_archive(
        archive, settings, third_party, python_interpreter=interpreter
    )
    after = json.loads(common.read_bytes())
    assert after == original | {
        "api": original["api"] | {"interpreter_path": str(interpreter)}
    }
    assert (
        Path(report["backup"]) / "kicad_common.before.json"
    ).read_bytes() == before


def test_concurrent_preferences_change_is_preserved(archive, target):
    """@brief Rejects stale preference bytes before changing the installation.
    @param archive Real verified PCM package.
    @param target Isolated settings and third-party paths.
    @return None.
    @details A concurrent writer's settings and the old plugin both survive.
    """
    settings, third_party = target
    plugin, _ = seed_old_plugin(third_party)
    common = settings / "kicad_common.json"
    concurrent = b'{"concurrent": true}'
    with pytest.raises(RuntimeError, match="preferences changed"):
        INSTALLER.install_archive(
            archive,
            settings,
            third_party,
            python_interpreter=Path("C:/KiCad/bin/python.exe"),
            before_publish=lambda: common.write_bytes(concurrent),
        )
    assert common.read_bytes() == concurrent
    assert (plugin / "old.txt").read_bytes() == b"old plugin bytes"


def test_concurrent_registry_change_is_preserved(archive, target):
    """@brief Rejects a changed registry before publishing new payload files.
    @param archive Real verified PCM package.
    @param target Isolated settings and third-party paths.
    @return None.
    @details Does not overwrite another writer's intervening update.
    """
    settings, third_party = target
    plugin, _ = seed_old_plugin(third_party)
    registry = settings / "installed_packages.json"
    concurrent = b'{"packages": [], "concurrent": true}'
    with pytest.raises(RuntimeError, match="changed during staging"):
        INSTALLER.install_archive(
            archive,
            settings,
            third_party,
            before_publish=lambda: registry.write_bytes(concurrent),
        )
    assert registry.read_bytes() == concurrent
    assert (plugin / "old.txt").read_bytes() == b"old plugin bytes"


def test_unowned_directory_is_rejected(archive, target):
    """@brief Refuses to replace a directory identifying another plugin.
    @param archive Real verified PCM package.
    @param target Isolated settings and third-party paths.
    @return None.
    @details The conflicting directory and registry retain their exact bytes.
    """
    settings, third_party = target
    plugin, _ = seed_old_plugin(third_party)
    (plugin / "plugin.json").write_bytes(b'{"identifier": "not.partsmith"}')
    with pytest.raises(ValueError, match="not the PartSmith"):
        INSTALLER.install_archive(archive, settings, third_party)
    assert (plugin / "old.txt").read_bytes() == b"old plugin bytes"


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher")
def test_batch_dry_run_preserves_python_override(target):
    """@brief Verifies a dry run leaves old IPC preferences and files intact.
    @param target Isolated settings and third-party paths.
    @return None.
    @details No payload, backup, registry or environment is changed.
    """
    settings, third_party = target
    common = settings / "kicad_common.json"
    common.write_bytes(b'{"api":{"interpreter_path":"C:/old312/python.exe"}}')
    before = {path: path.read_bytes() for path in settings.iterdir()}
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/install_production.ps1"),
            "-SettingsDir",
            str(settings),
            "-ThirdPartyDir",
            str(third_party),
            "-DryRun",
        ],
        cwd=settings,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert {path: path.read_bytes() for path in settings.iterdir()} == before
    assert "KiCad IPC interpreter:" in result.stdout
    assert "Dry run: no installation files changed." in result.stdout
    assert not (third_party / "plugins" / INSTALLER.DIRECTORY).exists()
    assert not (third_party.parent / "PartSmith-install-backups").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher")
@pytest.mark.parametrize("launcher", ["development", "production"])
def test_batch_installs_from_another_working_directory(
    archive, target, launcher
):
    """@brief Executes the batch launcher against isolated KiCad directories.
    @param archive Real verified PCM package.
    @param target Isolated settings and third-party paths containing spaces.
    @param launcher Development batch or production PowerShell entry point.
    @return None.
    @details Uses the real repository environment and installer entry point.
    """
    settings, third_party = target
    command = (
        [
            "cmd.exe",
            "/d",
            "/c",
            str(ROOT / "install_partsmith.bat"),
            "--no-pause",
            "--archive",
            str(archive),
            "--settings-dir",
            str(settings),
            "--third-party-dir",
            str(third_party),
        ]
        if launcher == "development"
        else [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/install_production.ps1"),
            "-Archive",
            str(archive),
            "-SettingsDir",
            str(settings),
            "-ThirdPartyDir",
            str(third_party),
        ]
    )
    result = subprocess.run(
        command,
        cwd=settings,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    plugin = third_party / "plugins" / INSTALLER.DIRECTORY
    assert verify_inventory(plugin)["version"] == VERSION
    assert "Installed PartSmith " + VERSION in result.stdout
    if launcher == "production":
        command[command.index("-Archive")] = "-Uninstall"
        command.remove(str(archive))
        removed = subprocess.run(
            command,
            cwd=settings,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert removed.returncode == 0, removed.stdout + removed.stderr
        assert not plugin.exists()
        assert (third_party / "plugins/other_package/keep.txt").is_file()
