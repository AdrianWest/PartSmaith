"""@package tests.test_external_dependencies
@brief Verifies manual OCR checks and blocking desktop startup behavior.
@details Keeps KiCad and Python packages outside the manual-install checklist.
Native dialog rendering and real installed OCR are verified separately.
"""

import importlib.util
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from partsmith import external_dependencies as external
from partsmith.gui import __main__ as desktop
from partsmith.pcm import runtime

ROOT = Path(__file__).resolve().parents[1]


def test_resolution_matches_ocr_override_policy(monkeypatch, tmp_path):
    """@brief Keeps startup and extraction on the same selected OCR engine.
    @param monkeypatch Environment and executable lookup substitution helper.
    @param tmp_path Isolated simulated Windows program directory.
    @return None.
    @details A stale explicit override must not silently select another engine.
    """
    installed = tmp_path / "Tesseract-OCR/tesseract.exe"
    installed.parent.mkdir()
    installed.touch()
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.delenv("PARTSMITH_TESSERACT", raising=False)
    monkeypatch.setattr(external.shutil, "which", Mock(return_value=None))
    assert external.find_tesseract() == str(installed)
    monkeypatch.setattr(
        external.shutil, "which", Mock(return_value="path-ocr")
    )
    assert external.find_tesseract() == "path-ocr"
    monkeypatch.setenv("PARTSMITH_TESSERACT", "missing-override")
    assert external.find_tesseract() == "missing-override"
    assert external.find_tesseract("selected") == "selected"
    installed.unlink()
    monkeypatch.delenv("PARTSMITH_TESSERACT")
    monkeypatch.setattr(external.shutil, "which", Mock(return_value=None))
    assert external.find_tesseract() is None


def test_missing_engine_has_one_actionable_manual_install(monkeypatch):
    """@brief Reports the missing engine with required languages and a link.
    @param monkeypatch Executable discovery substitution helper.
    @return None.
    @details Does not inspect KiCad, pip metadata or native wheel dependencies.
    """
    monkeypatch.setattr(external, "find_tesseract", Mock(return_value=None))
    probe = Mock(side_effect=AssertionError("No executable to probe"))
    monkeypatch.setattr(external, "_probe", probe)
    (issue,) = external.check_external_dependencies()
    assert issue.code == "TESSERACT_MISSING"
    assert issue.url == external.TESSERACT_URL
    for language in external.LANGUAGES.values():
        assert language in issue.instructions
    probe.assert_not_called()


@pytest.mark.parametrize("version", ["tesseract 4.1.1", "garbage", ""])
def test_unsupported_engine_has_installer_link(monkeypatch, version):
    """@brief Rejects unsupported or unrecognized OCR versions before startup.
    @param monkeypatch Native probe substitution helper.
    @param version Simulated version output.
    @return None.
    @details Language listing cannot make an unsupported engine acceptable.
    """
    monkeypatch.setattr(external, "find_tesseract", Mock(return_value="ocr"))
    probe = Mock(return_value=version)
    monkeypatch.setattr(external, "_probe", probe)
    (issue,) = external.check_external_dependencies()
    assert issue.code == "TESSERACT_VERSION_UNSUPPORTED"
    assert issue.url == external.TESSERACT_URL
    probe.assert_called_once_with("ocr", "--version")


def test_language_links_only_list_missing_models(monkeypatch):
    """@brief Lists each absent model without repeating installed languages.
    @param monkeypatch Native probe substitution helper.
    @return None.
    @details Allows extra languages; the selected tessdata controls checks.
    """
    monkeypatch.setattr(external, "find_tesseract", Mock(return_value="ocr"))
    probe = Mock(
        side_effect=["tesseract 5.5.3\n", "Languages (2):\neng\nosd\n"]
    )
    monkeypatch.setattr(external, "_probe", probe)
    issues = external.check_external_dependencies()
    assert [issue.code for issue in issues] == [
        "OCR_LANGUAGE_MISSING_DEU",
        "OCR_LANGUAGE_MISSING_CHI_SIM",
    ]
    assert all("TESSDATA_PREFIX" in issue.instructions for issue in issues)
    assert [issue.url.rsplit("/", 1)[1] for issue in issues] == [
        "deu.traineddata",
        "chi_sim.traineddata",
    ]


@pytest.mark.parametrize(
    "version", ["tesseract 5.5.3", "tesseract v5.5.0.20241111"]
)
def test_ready_ocr_allows_extra_languages_and_whitespace(monkeypatch, version):
    """@brief Accepts a working Tesseract 5 with all mandatory language data.
    @param monkeypatch Native probe substitution helper.
    @param version Upstream or Windows installer version banner.
    @return None.
    @details Startup does not constrain optional languages or patch versions.
    """
    monkeypatch.setattr(external, "find_tesseract", Mock(return_value="ocr"))
    monkeypatch.setattr(
        external,
        "_probe",
        Mock(
            side_effect=[
                version,
                "Languages:\neng\n deu \nchi_sim\nosd",
            ]
        ),
    )
    assert external.check_external_dependencies() == ()


@pytest.mark.parametrize(
    "error",
    [
        OSError("private-path"),
        subprocess.CalledProcessError(1, "private-command"),
        subprocess.TimeoutExpired("private-command", 10),
    ],
)
def test_probe_failures_are_safe_and_actionable(monkeypatch, error):
    """@brief Converts native launch and timeout failures into safe guidance.
    @param monkeypatch Native probe substitution helper.
    @param error Simulated native execution failure containing private text.
    @return None.
    @details Exception text and subprocess output never reach the dialog.
    """
    monkeypatch.setattr(external, "find_tesseract", Mock(return_value="ocr"))
    monkeypatch.setattr(external, "_probe", Mock(side_effect=error))
    (issue,) = external.check_external_dependencies()
    assert issue.code == "TESSERACT_UNAVAILABLE"
    assert issue.url == external.TESSERACT_URL
    assert "private-" not in json.dumps(asdict(issue))


def test_native_probe_is_bounded_noninteractive_and_inherits_models(
    monkeypatch,
):
    """@brief Keeps manual prerequisite discovery local and bounded.
    @param monkeypatch Process creation substitution helper.
    @return None.
    @details Inherited language selection matches subsequent OCR operations.
    """
    run = Mock(return_value=SimpleNamespace(stdout="tesseract 5.5.3"))
    monkeypatch.setattr(external.subprocess, "run", run)
    monkeypatch.setenv("TESSDATA_PREFIX", "selected-models")
    assert external._probe("ocr", "--version") == "tesseract 5.5.3"
    args, options = run.call_args
    assert args == (["ocr", "--version"],)
    assert options["stdin"] == subprocess.DEVNULL
    assert options["timeout"] == 10
    assert options["check"] is True
    assert not options.get("shell")
    assert "env" not in options


def test_readiness_reports_manual_issues_before_engineering_imports(
    monkeypatch, tmp_path
):
    """@brief Exposes actionable OCR errors without probing KiCad for the list.
    @param monkeypatch Runtime boundary substitution helper.
    @param tmp_path Isolated installed payload root.
    @return None.
    @details Managed Python packages retain their separate readiness path.
    """
    monkeypatch.setattr(runtime.sys, "version_info", (3, 11, 5))
    monkeypatch.setattr(
        runtime.platform, "system", Mock(return_value="Windows")
    )
    monkeypatch.setattr(
        runtime.platform, "machine", Mock(return_value="AMD64")
    )
    monkeypatch.setattr(runtime, "verify_inventory", Mock(return_value={}))
    monkeypatch.setattr(external, "find_tesseract", Mock(return_value=None))
    packages = Mock(side_effect=AssertionError("Not a manual package check"))
    monkeypatch.setattr(runtime, "version", packages)
    report = runtime.readiness(tmp_path)
    assert report["code"] == "EXTERNAL_DEPENDENCIES_MISSING"
    assert report["external_dependencies"][0]["url"] == external.TESSERACT_URL
    packages.assert_not_called()


@pytest.mark.parametrize("missing", [True, False])
def test_standalone_blocks_recovery_until_manual_prerequisites_ready(
    monkeypatch, missing
):
    """@brief Blocks the main frame until manually installed OCR is ready.
    @param monkeypatch GUI and prerequisite substitution helper.
    @param missing Whether manual software is absent for this launch.
    @return None.
    @details No recovery or setup frame is constructed while errors are shown.
    """
    issues = (external._engine_issue("TESSERACT_MISSING", "Not installed."),)
    monkeypatch.setattr(
        external,
        "check_external_dependencies",
        Mock(return_value=issues if missing else ()),
    )
    show = Mock()
    frame = Mock()
    app = Mock()
    monkeypatch.setitem(sys.modules, "wx", SimpleNamespace(App=app))
    monkeypatch.setitem(
        sys.modules,
        "partsmith.gui.prerequisites",
        SimpleNamespace(show_missing_dependencies=show),
    )
    monkeypatch.setitem(
        sys.modules, "partsmith.gui.app", SimpleNamespace(SetupFrame=frame)
    )
    assert desktop.main() == (2 if missing else 0)
    if missing:
        show.assert_called_once_with(issues)
        frame.assert_not_called()
        app.return_value.MainLoop.assert_not_called()
    else:
        show.assert_not_called()
        frame.return_value.Show.assert_called_once()
        app.return_value.MainLoop.assert_called_once()


@pytest.mark.parametrize("case", ["normal", "host-exited", "diagnostics"])
def test_ipc_manual_dialog_lifetime_and_diagnostics(monkeypatch, case):
    """@brief Preserves host lifetime and noninteractive diagnostic behavior.
    @param monkeypatch Entry point, environment and GUI substitution helper.
    @param case Interactive close, host exit or diagnostic-only launch.
    @return None.
    @details Host ownership is lifetime monitoring, not installation detection.
    """
    from partsmith.integration import host

    spec = importlib.util.spec_from_file_location(
        "external_entry_test",
        ROOT / "integrations/kicad/partsmith_ipc/entry.py",
    )
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    entry.sys = SimpleNamespace(
        flags=SimpleNamespace(isolated=1),
        path=[],
        argv=["entry.py"]
        + (["--diagnostics"] if case == "diagnostics" else []),
        stderr=sys.stderr,
    )
    issue = external._engine_issue("TESSERACT_MISSING", "Not installed.")
    report = {
        "state": "FAILED",
        "code": "EXTERNAL_DEPENDENCIES_MISSING",
        "external_dependencies": [asdict(issue)],
    }
    monkeypatch.setattr(runtime, "readiness", Mock(return_value=report))
    save = Mock()
    monkeypatch.setattr(entry, "_save_report", save)
    owner = Mock()
    owner.is_alive.side_effect = [True, case != "host-exited"]
    capture = Mock(return_value=owner)
    monkeypatch.setattr(host, "capture_launch_host", capture)
    monkeypatch.setenv("KICAD_API_SOCKET", "private-endpoint")
    monkeypatch.setenv("KICAD_API_TOKEN", "private-token")
    app = Mock()
    show = Mock()
    monkeypatch.setitem(sys.modules, "wx", SimpleNamespace(App=app))
    monkeypatch.setitem(
        sys.modules,
        "partsmith.gui.prerequisites",
        SimpleNamespace(show_missing_dependencies=show),
    )
    assert entry.main() == (0 if case == "host-exited" else 2)
    assert "KICAD_API_TOKEN" not in entry.os.environ
    if case == "diagnostics":
        app.assert_not_called()
        capture.assert_not_called()
        show.assert_not_called()
    else:
        show.assert_called_once_with((issue,), host_alive=owner.is_alive)
        owner.close.assert_called_once()
    if case == "host-exited":
        assert report["code"] == "KICAD_HOST_EXITED"
