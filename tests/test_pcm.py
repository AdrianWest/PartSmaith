"""@file test_pcm.py
@brief Checks deterministic PCM archives, resource ownership and runtime gates.
@details Checks installed launch isolation and deliberate optional PCB access.
"""

import ctypes
import importlib.util
import io
import json
import stat
import subprocess
import sys
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest
from jsonschema import ValidationError
from PIL import Image

from partsmith.integration.errors import IntegrationError
from partsmith.integration.policy import ResourcePolicy
from partsmith.pcm.package import (
    INVENTORY,
    build_pcm,
    collect_payload,
    json_bytes,
    repository_package,
    validate_payload,
    verify_pcm,
)
from partsmith.pcm.runtime import readiness, verify_inventory

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pcm_archive(tmp_path_factory):
    """@brief Builds a real PCM archive once for archive-boundary tests.
    @param tmp_path_factory Module-scoped isolated directory factory.
    @return Final archive path and deterministic receipt.
    @details Contains the complete declared source and engineering resources.
    """
    path = tmp_path_factory.mktemp("pcm") / "partsmith.zip"
    return path, build_pcm(ROOT, path)


def _payload(archive: Path) -> dict:
    """@brief Reads a validated fixture archive into independent bytes.
    @param archive Fixture PCM ZIP path.
    @return Member names mapped to immutable bytes.
    @details Each test mutates its own mapping without changing the fixture.
    """
    with ZipFile(archive) as source:
        return {name: source.read(name) for name in source.namelist()}


def test_deterministic_archive_and_download_separation(pcm_archive, tmp_path):
    """@brief Verifies identical archives and post-build download metadata.
    @param pcm_archive Complete archive fixture and receipt.
    @param tmp_path Destination for a second independent archive.
    @return None.
    @details ZIP timestamps, modes, ordering and extracted sizes are stable.
    """
    first, receipt = pcm_archive
    second = tmp_path / "other.zip"
    assert build_pcm(ROOT, second) == receipt
    assert first.read_bytes() == second.read_bytes()
    metadata = verify_pcm(first)
    version = metadata["versions"][0]
    assert not any(key.startswith("download_") for key in version)
    assert version["runtime"] == "ipc"
    assert version["platforms"] == ["windows"]
    assert version["kicad_version"] == version["kicad_version_max"] == "10.0.6"
    repository = repository_package(first, "https://example.invalid/pcm.zip")
    published = repository["versions"][0]
    assert (
        published["download_sha256"] == sha256(first.read_bytes()).hexdigest()
    )
    assert published["download_size"] == first.stat().st_size
    assert first.read_bytes() == second.read_bytes()


def test_source_resource_parity_and_root_layout(pcm_archive):
    """@brief Checks every source/schema/migration/asset/plugin byte.
    @param pcm_archive Complete archive fixture and receipt.
    @return None.
    @details PCM owns its namespace; portable files sit directly under plugins.
    """
    path, _ = pcm_archive
    payload = _payload(path)
    for name, data in collect_payload(ROOT).items():
        assert payload[name] == data
    assert "plugins/plugin.json" in payload
    assert "plugins/requirements.txt" in payload
    assert "plugins/entry.py" in payload
    assert "plugins/bundle.json" not in payload
    assert not any(
        Path(name).suffix.lower() in {".exe", ".dll", ".pyd", ".conda"}
        for name in payload
    )
    assert (
        payload["resources/icon.png"]
        == (ROOT / "resources/PartSmith_Logo_64x64.png").read_bytes()
    )
    with Image.open(io.BytesIO(payload["resources/icon.png"])) as icon:
        assert icon.format == "PNG" and icon.size == (64, 64)
    plugin = json.loads(payload["plugins/plugin.json"])
    for theme in ("icons-light", "icons-dark"):
        paths = plugin["actions"][0][theme]
        for size, name in zip((24, 64), paths, strict=True):
            original = (
                ROOT
                / "resources"
                / (f"PartSmith_Anvil_Icon_{size}x{size}.png")
            )
            assert payload["plugins/" + name] == original.read_bytes()
            with Image.open(io.BytesIO(payload["plugins/" + name])) as icon:
                assert icon.format == "PNG"
                assert icon.size == (size, size)
                assert icon.getbbox() is not None
    assert (
        "plugins/partsmith/integration/integration-contracts-1.0.schema.json"
        in payload
    )
    assert not any("__pycache__" in name or ".whl" in name for name in payload)


@pytest.mark.parametrize(
    "case",
    ["missing", "changed", "extra", "escape", "icon_missing", "icon_changed"],
)
def test_inventory_rejects_changed_or_escaping_members(pcm_archive, case):
    """@brief Rejects omissions, tampering, unexpected members and traversal.
    @param pcm_archive Complete archive fixture and receipt.
    @param case Selected malformed archive boundary.
    @return None.
    @details Failure precedes extraction or resource loading.
    """
    payload = _payload(pcm_archive[0])
    if case == "missing":
        del payload["plugins/requirements.txt"]
    elif case == "changed":
        payload["plugins/requirements.txt"] += b"\nchanged"
    elif case == "extra":
        payload["plugins/credentials.json"] = b"{}"
    elif case == "icon_missing":
        del payload["resources/icon.png"]
    elif case == "icon_changed":
        payload["resources/icon.png"] += b"changed"
    else:
        payload["plugins/../outside"] = b"escape"
    with pytest.raises(ValueError):
        validate_payload(payload)


def test_repository_listing_icon_without_package_download(pcm_archive):
    """@brief Verifies the PCM repository supplies the exact listing logo.
    @param pcm_archive Complete archive fixture and receipt.
    @return None.
    @details The separate resources ZIP uses KiCad's package-ID/icon.png path,
    is hash-bound in repository metadata and repeats deterministically.
    """
    spec = importlib.util.spec_from_file_location(
        "pcm_builder", ROOT / "scripts/build_pcm.py"
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    path, _ = pcm_archive
    builder.write_repository_fixture(path, "http://127.0.0.1:8765")
    resources = path.parent / "resources.zip"
    first = resources.read_bytes()
    with ZipFile(resources) as source:
        assert source.namelist() == ["com.boardforgetools.partsmith/icon.png"]
        assert (
            source.read(source.namelist()[0])
            == (ROOT / "resources/PartSmith_Logo_64x64.png").read_bytes()
        )
    repository = json.loads((path.parent / "repository.json").read_bytes())
    assert repository["resources"]["sha256"] == sha256(first).hexdigest()
    assert repository["resources"]["url"] == (
        "http://127.0.0.1:8765/resources.zip"
    )
    builder.write_repository_fixture(path, "http://127.0.0.1:8765")
    assert resources.read_bytes() == first


@pytest.mark.parametrize("case", ["unknown", "download", "versions", "scope"])
def test_closed_archive_and_plugin_registration(pcm_archive, case):
    """@brief Rejects extensible upstream-schema gaps in the owned contract.
    @param pcm_archive Complete archive fixture and receipt.
    @param case Unsupported metadata or IPC registration change.
    @return None.
    @details Recomputes inventory when testing a semantically wrong plugin.
    """
    payload = _payload(pcm_archive[0])
    metadata = json.loads(payload["metadata.json"])
    if case == "unknown":
        metadata["unknown"] = True
    elif case == "download":
        metadata["versions"][0]["download_size"] = 1
    elif case == "versions":
        metadata["versions"].append(dict(metadata["versions"][0]))
    else:
        plugin = json.loads(payload["plugins/plugin.json"])
        plugin["actions"][0]["scopes"] = ["schematic"]
        payload["plugins/plugin.json"] = json_bytes(plugin)
        inventory = json.loads(payload[INVENTORY])
        data = payload["plugins/plugin.json"]
        inventory["files"]["plugin.json"] = {
            "sha256": sha256(data).hexdigest(),
            "size": len(data),
        }
        payload[INVENTORY] = json_bytes(inventory)
    payload["metadata.json"] = json_bytes(metadata)
    with pytest.raises((ValueError, ValidationError)):
        validate_payload(payload)


def test_installed_inventory_and_missing_resource(pcm_archive, tmp_path):
    """@brief Checks installed resource identities independent of the checkout.
    @param pcm_archive Complete archive fixture and receipt.
    @param tmp_path Isolated installed package directory.
    @return None.
    @details Bytecode is disposable while resource omissions block readiness.
    """
    with ZipFile(pcm_archive[0]) as archive:
        archive.extractall(tmp_path)
    root = tmp_path / "plugins"
    assert (
        verify_inventory(root)["identifier"] == "com.boardforgetools.partsmith"
    )
    (root / "partsmith/persistence/001_initial.sql").unlink()
    with pytest.raises(ValueError, match="PCM_RESOURCE_MISSING"):
        verify_inventory(root)


def test_python310_is_rejected_before_resource_or_native_import(monkeypatch):
    """@brief Rejects unsupported Python before touching resource/CAD code.
    @param monkeypatch Interpreter-state test helper.
    @return None.
    @details A missing package root cannot obscure the interpreter error.
    """
    monkeypatch.setattr(sys, "version_info", (3, 10, 11))
    result = readiness(Path("does-not-exist"))
    assert result["state"] == "FAILED"
    assert result["code"] == "PYTHON_311_REQUIRED"


def test_entry_isolates_pythonpath_and_removes_tokens_before_checks(tmp_path):
    """@brief Verifies launch isolation and earliest credential-env clearing.
    @param tmp_path Fixture source tree with a safe diagnostic readiness stub.
    @return None.
    @details The child observes no launch secrets even during failed readiness.
    """
    entry = tmp_path / "entry.py"
    entry.write_bytes(
        (ROOT / "integrations/kicad/partsmith_ipc/entry.py").read_bytes()
    )
    package = tmp_path / "partsmith/pcm"
    package.mkdir(parents=True)
    (package.parent / "__init__.py").write_text("")
    (package / "__init__.py").write_text("")
    (package / "runtime.py").write_text(
        "import os, sys\n"
        "def readiness(root):\n"
        " assert sys.flags.isolated\n"
        " assert 'KICAD_API_TOKEN' not in os.environ\n"
        " assert 'KICAD_API_SOCKET' not in os.environ\n"
        " return {'state':'FAILED','code':'SAFE_STUB'}\n"
    )
    import os

    child = subprocess.run(
        [sys.executable, str(entry), "--diagnostics"],
        stdin=subprocess.DEVNULL,
        env=os.environ
        | {
            "PYTHONPATH": "untrusted-path",
            "KICAD_API_TOKEN": "secret-do-not-record",
            "KICAD_API_SOCKET": "private-do-not-record",
            "LOCALAPPDATA": str(tmp_path / "data"),
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert child.returncode == 2
    assert json.loads(child.stdout) == {"state": "FAILED", "code": "SAFE_STUB"}
    assert "secret-do-not-record" not in child.stdout + child.stderr
    report = tmp_path / "data/PartSmith/runtime/last-launch.json"
    assert json.loads(report.read_bytes())["code"] == "SAFE_STUB"


def test_failure_reports_never_serialize_dependency_exception(
    monkeypatch, tmp_path
):
    """@brief Ensures diagnostic failures emit codes without external messages.
    @param monkeypatch Runtime-boundary substitution helper.
    @param tmp_path Unrelated package root.
    @return None.
    @details Safe codes do not expose credentials embedded in provider errors.
    """
    from partsmith.pcm import runtime

    def system():
        """@brief Selects the supported OS for the failure-boundary check.
        @return Windows platform name.
        @details Does not query the execution host.
        """
        return "Windows"

    def machine():
        """@brief Selects the supported machine for the failure-boundary check.
        @return AMD64 architecture name.
        @details Does not query the execution host.
        """
        return "AMD64"

    monkeypatch.setattr(runtime.platform, "system", system)
    monkeypatch.setattr(runtime.platform, "machine", machine)
    monkeypatch.setattr(sys, "version_info", (3, 11, 5))
    result = readiness(tmp_path)
    assert result["code"] == "PCM_RESOURCE_CHECK_FAILED"
    assert "Exception" not in json.dumps(result)


@pytest.mark.parametrize(
    "name",
    [
        "plugins/AUX.txt",
        "plugins/file.",
        "plugins/file ",
        "plugins/a?b",
        "plugins/NUL/data",
        "plugins/COM1.py",
    ],
)
def test_windows_nonportable_names_are_rejected(pcm_archive, name):
    """@brief Rejects Windows device aliases and invalid path components.
    @param pcm_archive Complete archive fixture and receipt.
    @param name Nonportable archive member to inject.
    @return None.
    @details Validation fails before metadata parsing or payload extraction.
    """
    payload = _payload(pcm_archive[0])
    payload[name] = b"bad"
    with pytest.raises(ValueError, match="portable Windows"):
        validate_payload(payload)


def test_case_aliases_and_file_directory_collisions(pcm_archive):
    """@brief Rejects members that overwrite under Windows extraction rules.
    @param pcm_archive Complete archive fixture and receipt.
    @return None.
    @details Checks case aliases and an ancestor declared as a regular file.
    """
    payload = _payload(pcm_archive[0])
    payload["plugins/ENTRY.py"] = b"alias"
    with pytest.raises(ValueError, match="case-aliased"):
        validate_payload(payload)
    del payload["plugins/ENTRY.py"]
    payload["plugins/partsmith"] = b"file"
    with pytest.raises(ValueError, match="file/directory"):
        validate_payload(payload)


def test_archive_preflight_bounds_and_compression(tmp_path, monkeypatch):
    """@brief Applies limits and owned compression policy before reading data.
    @param tmp_path Isolated malformed archive directory.
    @param monkeypatch Resource-policy substitution helper.
    @return None.
    @details Tiny bounds prove the verifier rejects before member allocation.
    """
    from partsmith.pcm import package

    path = tmp_path / "oversized.zip"
    with ZipFile(path, "w") as archive:
        info = ZipInfo("metadata.json")
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, b"larger-than-eight-bytes")

    def bounded_policy():
        """@brief Applies a tiny bound to prove archive preflight order.
        @return ResourcePolicy with an eight-byte per-object limit.
        @details Leaves all other policy bounds at the frozen defaults.
        """
        return ResourcePolicy(object_bytes=8)

    def forbidden_read(self, name, pwd=None):
        """@brief Fails if preflight attempts to allocate a member body.
        @param name Requested ZIP member name.
        @param pwd Optional archive credential.
        @return None; always raises AssertionError.
        @details This callback must never run for the oversized fixture.
        """
        raise AssertionError("member read occurred before preflight")

    monkeypatch.setattr(package, "ResourcePolicy", bounded_policy)
    monkeypatch.setattr(ZipFile, "read", forbidden_read)
    with pytest.raises(IntegrationError):
        verify_pcm(path)
    monkeypatch.undo()
    compressed = tmp_path / "compressed.zip"
    with ZipFile(compressed, "w", compression=ZIP_DEFLATED) as archive:
        info = ZipInfo("metadata.json")
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        info.compress_type = ZIP_DEFLATED
        archive.writestr(info, b"{}")
    with pytest.raises(ValueError):
        verify_pcm(compressed)


@pytest.mark.parametrize(
    "case",
    [
        "startup",
        "startup_missing",
        "host_missing",
        "host_dead",
        "host_exit",
        "missing",
        "cancel",
        "connect",
        "controller",
        "inspector",
        "gui",
        "ok",
        "reuse",
    ],
)
def test_entry_selection_failure_codes_and_session_cleanup(monkeypatch, case):
    """@brief Checks direct startup and deliberate optional inspection cleanup.
    @param monkeypatch Module and launch-environment substitution helper.
    @param case Startup, optional inspection, cancellation or failure scenario.
    @return None.
    @details GUI doubles test orchestration; desktop proof is separate.
    """
    from partsmith.integration.ipc import IpcError, IpcFailureReason
    from partsmith.pcm import runtime

    spec = importlib.util.spec_from_file_location(
        "pcm_entry_under_test",
        ROOT / "integrations/kicad/partsmith_ipc/entry.py",
    )
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)
    entry.sys = SimpleNamespace(
        flags=SimpleNamespace(isolated=1), path=[], argv=["entry.py"]
    )
    reports = []
    calls = []
    ui = {}

    def ready(root):
        """@brief Supplies safe readiness while checking early env removal.
        @param root Installed plugin path selected by the action.
        @return Safe READY diagnostic mapping.
        @details Does not initialize CAD or access persistent user data.
        """
        assert "KICAD_API_TOKEN" not in entry.os.environ
        assert "KICAD_API_SOCKET" not in entry.os.environ
        return {"state": "READY", "code": "READY"}

    def save(report):
        """@brief Captures safe diagnostic snapshots without filesystem writes.
        @param report Current safe launch document.
        @return None.
        @details Copies documents so later mutations cannot alter assertions.
        """
        reports.append(json.loads(json.dumps(report)))

    def show():
        """@brief Supplies a no-op visible-window boundary.
        @return None.
        @details Records main-frame visibility before any board access.
        """
        calls.append("show")

    def window_handle():
        """@brief Supplies the visible-frame native-handle boundary.
        @return One as an inert handle fixture.
        @details Does not create or access any native desktop window.
        """
        return 1

    def visible(handle):
        """@brief Models an already-visible setup frame.
        @param handle Exact inert main-frame handle.
        @return True for this orchestration-only GUI fixture.
        @details Real Windows visibility has separate installed GUI evidence.
        """
        assert handle == 1
        return True

    def native_library(name):
        """@brief Supplies only the expected visibility API boundary.
        @param name Windows library requested by the entry point.
        @return Object exposing the inert visibility callback.
        @details Rejects any unrelated native API access in this unit test.
        """
        assert name == "user32"
        return SimpleNamespace(IsWindowVisible=visible)

    if entry.os.name == "nt":
        monkeypatch.setattr(ctypes, "WinDLL", native_library)

    def loop():
        """@brief Finishes the fake desktop action event loop.
        @return None.
        @details Startup must not select, connect, inspect or refresh a board.
        """
        assert calls == ["show"]
        if case not in {"startup", "startup_missing", "host_exit"}:
            ui["inspect"](ui["frame"])
        if case == "reuse":
            ui["inspect"](ui["frame"])

    def app(redirect):
        """@brief Supplies a bounded application double.
        @param redirect Requested wx output-redirection choice.
        @return Object exposing the event-loop boundary.
        @details Does not open a native desktop window.
        """
        return SimpleNamespace(MainLoop=loop)

    def modal():
        """@brief Returns the selected board-picker result.
        @return One for selection or zero for cancellation.
        @details The cancellation case must not create an IPC session.
        """
        calls.append("picker")
        return 0 if case == "cancel" else 1

    def selected_path():
        """@brief Supplies the deliberate board path unchanged.
        @return Exact selected board path string.
        @details No implicit document selection is permitted.
        """
        return "C:/owned/selected.kicad_pcb"

    @contextmanager
    def dialog(*args, **kwargs):
        """@brief Supplies a board-picker context without native controls.
        @param args Positional wx dialog construction arguments.
        @param kwargs Named wx dialog construction arguments.
        @return Context yielding the deliberate selection boundary.
        @details Dialog ownership ends before session connection begins.
        """
        yield SimpleNamespace(ShowModal=modal, GetPath=selected_path)

    def message(*args, **kwargs):
        """@brief Captures safe GUI diagnostic display.
        @param args Message-box positional arguments.
        @param kwargs Message-box named arguments.
        @return None.
        @details Provider exception text never reaches the displayed message.
        """
        assert "secret-do-not-record" not in str(args)

    def close():
        """@brief Records transient session cleanup.
        @return None.
        @details Called exactly once when a session was created.
        """
        calls.append("closed")

    def connect(endpoint, token, expected_board):
        """@brief Checks exact transient handoff and deliberate selected board.
        @param endpoint Explicit private launch endpoint.
        @param token Explicit transient launch token.
        @param expected_board Exact deliberate board selection.
        @return Session double exposing cleanup.
        @details Never records endpoint or token in the call trace.
        """
        assert endpoint == "private-do-not-record"
        assert token == "secret-do-not-record"
        assert expected_board == selected_path()
        calls.append("connect")
        if case == "connect":
            raise IpcError(IpcFailureReason.WRONG_BOARD)
        return SimpleNamespace(close=close)

    def controller(session, report_callback):
        """@brief Supplies inspection lifecycle behavior for the entry.
        @param session Connected session owned by the controller.
        @param report_callback Safe inspection report callback.
        @return Controller double with refresh and close boundaries.
        @details Controller implementation has its own executable tests.
        """

        def refresh():
            """@brief Rejects any automatic component inspection.
            @return None.
            @details Only the inspector's deliberate Refresh button may read.
            """
            pytest.fail("Entry must not refresh the board automatically")

        if case == "controller":
            raise RuntimeError("secret-do-not-record")
        return SimpleNamespace(refresh=refresh, close=session.close)

    def frame(inspect_pcb, host_alive, recover):
        """@brief Supplies a visible frame or unrelated GUI failure.
        @return Frame double exposing Show.
        @param inspect_pcb Deliberate callback registered without invocation.
        @param host_alive Exact launching-host lifetime callback.
        @param recover Normal startup's deliberate session-recovery behavior.
        @details Raw failure messages must not be persisted by the action.
        """
        if case == "gui":
            raise RuntimeError("secret-do-not-record")
        assert recover is True
        ui["inspect"] = inspect_pcb
        ui["frame"] = SimpleNamespace(Show=show, GetHandle=window_handle)
        return ui["frame"]

    def raise_inspector():
        """@brief Records reuse of the existing optional inspector.
        @return None.
        @details A second button click must not reconnect or select a board.
        """
        calls.append("raised")

    def inspector(parent, inspection_controller):
        """@brief Supplies the read-only inspector display boundary.
        @param parent Main setup frame.
        @param inspection_controller Controller owning the explicit session.
        @return Inspector window double exposing Show.
        @details Does not create or reconnect an IPC session.
        """
        if case == "inspector":
            raise RuntimeError("secret-do-not-record")
        return SimpleNamespace(Show=show, Raise=raise_inspector)

    monkeypatch.setattr(runtime, "readiness", ready)
    monkeypatch.setattr(entry, "_save_report", save)
    monkeypatch.setenv("KICAD_API_SOCKET", "private-do-not-record")
    monkeypatch.setenv("KICAD_API_TOKEN", "secret-do-not-record")
    if case in {"missing", "startup_missing"}:
        monkeypatch.delenv("KICAD_API_TOKEN")
    monkeypatch.setitem(
        sys.modules,
        "wx",
        SimpleNamespace(
            App=app,
            FileDialog=dialog,
            MessageBox=message,
            OK=1,
            ICON_ERROR=2,
            FD_OPEN=4,
            FD_FILE_MUST_EXIST=8,
            ID_OK=1,
        ),
    )
    monkeypatch.setitem(
        sys.modules, "partsmith.gui.app", SimpleNamespace(SetupFrame=frame)
    )
    monkeypatch.setattr(
        "partsmith.integration.host.capture_launch_host",
        lambda: (
            None
            if case == "host_missing"
            else SimpleNamespace(
                is_alive=lambda: (
                    case != "host_dead"
                    and (case != "host_exit" or "show" not in calls)
                ),
                close=lambda: None,
            )
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "partsmith.integration.inspection",
        SimpleNamespace(InspectionController=controller),
    )
    monkeypatch.setitem(
        sys.modules,
        "partsmith.integration.inspection_wx",
        SimpleNamespace(InspectionFrame=inspector),
    )
    monkeypatch.setattr("partsmith.integration.ipc.connect_ipc", connect)
    result = entry.main()
    assert result == (2 if case == "gui" else 0)
    assert "secret-do-not-record" not in json.dumps(reports)
    assert calls.count("closed") == (
        1 if case in {"controller", "inspector", "ok", "reuse"} else 0
    )
    assert "private-do-not-record" not in json.dumps(reports)
    if case in {"host_missing", "host_dead", "host_exit"}:
        assert calls == (["show"] if case == "host_exit" else [])
        assert reports[-1] == {"state": "CLOSED", "code": "KICAD_HOST_EXITED"}
    if case in {"startup", "startup_missing"}:
        assert calls == ["show"]
        assert reports[-1] == {"state": "READY", "code": "READY"}
    if case == "missing":
        assert "picker" not in calls
        assert reports[-1]["state"] == "READY"
        assert reports[-1]["ipc_inspection"]["code"] == (
            "IPC_LAUNCH_CONTEXT_REQUIRED"
        )
    elif case == "cancel":
        assert "connect" not in calls
    elif case == "connect":
        assert reports[-1]["ipc_inspection"]["code"] == "IPC_WRONG_BOARD"
    elif case == "controller":
        assert reports[-1]["ipc_inspection"]["code"] == (
            "IPC_CONNECTION_OR_BOARD_CHECK_FAILED"
        )
    elif case == "inspector":
        assert reports[-1]["ipc_inspection"]["code"] == "GUI_ACTION_FAILED"
    elif case == "gui":
        assert reports[-1]["code"] == "GUI_ACTION_FAILED"
    elif case == "reuse":
        assert calls.count("picker") == 1
        assert calls.count("connect") == 1
        assert calls.count("raised") == 1
