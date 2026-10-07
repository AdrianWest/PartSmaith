"""@package tests.test_integration_ipc
@brief Exercises explicit IPC session guards and exact native unit conversions.
@details Injected backends test failure handling, bounded supervision and
redaction only. They are labeled and do not substitute for live KiCad evidence.
"""

import json
import multiprocessing
import os
import pickle
import time
from dataclasses import FrozenInstanceError, asdict
from decimal import Decimal, localcontext
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

from partsmith.integration.ipc import (
    BINDING_API_BUILD,
    IpcError,
    IpcFailureReason,
    IpcSession,
    _OfficialBackend,
)
from partsmith.integration.units import (
    NATIVE_MAX,
    NATIVE_MIN,
    UnitConversionError,
    engineering_angle_to_native,
    engineering_to_native,
    millimeters_to_nanometers,
    nanometers_to_millimeters,
    native_angle_to_engineering,
    native_to_engineering,
)

TOKEN = "synthetic-transient-token-never-record"


class FakeBackend:
    """@brief Implements a labeled synthetic backend for boundary tests.
    @details Never connects to KiCad or proves an installed/live capability.
    """

    def __init__(
        self,
        endpoint,
        token,
        timeout_ms,
        *,
        project_path,
        mode="ready",
    ):
        """@brief Builds the selected synthetic document/failure scenario.
        @param endpoint Synthetic ephemeral endpoint.
        @param token Synthetic token used to test output exclusion.
        @param timeout_ms Requested finite transport deadline.
        @param project_path Absolute synthetic project directory.
        @param mode Selected deterministic test behavior.
        @return None.
        @details Each disposable worker creates an independent fake instance.
        """
        self.endpoint = endpoint
        self.token = token
        self.timeout_ms = timeout_ms
        self.project_path = project_path
        self.mode = mode
        self.read = False
        self.binding_version = "0.8.0" if mode != "binding" else "0.7.1"
        self.api_version = BINDING_API_BUILD if mode != "api" else "10.0.5"

    def get_version(self):
        """@brief Returns a synthetic native version.
        @return Numeric version string.
        @details Wrong versions test target rejection without live discovery.
        """
        return "10.0.6" if self.mode != "version" else "10.0.5"

    def get_documents(self):
        """@brief Produces the selected explicit synthetic document set.
        @return Synthetic document specifiers.
        @details Can simulate duplicates, context changes or unrelated boards.
        """
        name = "changed" if self.mode == "context" and self.read else "board"
        document = SimpleNamespace(
            project=SimpleNamespace(path=self.project_path, name=name),
            board_filename="board.kicad_pcb",
        )
        if self.mode == "wrong":
            document.board_filename = "other.kicad_pcb"
        if self.mode == "duplicate":
            return [document, document]
        if self.mode == "none":
            return []
        if self.mode == "documents-limit":
            return [document] * 129
        if self.mode == "project-secret":
            document.project.name = self.token
        if self.mode == "relative-project":
            document.project.path = "."
        return [document]

    def get_footprints(self, document):
        """@brief Reads deterministic synthetic footprint fields or failure.
        @param document Explicit selected synthetic document.
        @return Native-unit component dictionaries.
        @details Error text echoes credentials to test suppression.
        """
        self.read = True
        if self.mode == "raw-error":
            raise RuntimeError(f"{self.endpoint}: {self.token}")
        if self.mode == "token-mismatch":
            raise IpcError(IpcFailureReason.TOKEN_MISMATCH)
        if self.mode == "unavailable":
            raise IpcError(IpcFailureReason.OPERATION_UNAVAILABLE)
        if self.mode == "hang":
            time.sleep(5)
        if self.mode == "print-secret":
            print(self.token)
            os.write(1, self.token.encode())
            os.write(2, self.endpoint.encode())
        result = {
            "item_id": "01234567-89ab-4def-8123-0123456789ab",
            "reference": self.token if self.mode == "echo" else "R1",
            "x_nm": 1_250_000,
            "y_nm": -2_500_000,
            "angle": 90.0,
            "side": "top",
        }
        if self.mode == "endpoint-echo":
            result["reference"] = self.endpoint
        if self.mode == "bad-coordinate":
            result["x_nm"] = 2**40
        if self.mode == "items-limit":
            return [result] * 10_001
        if self.mode == "duplicate-item":
            return [result, result]
        if self.mode == "oversize":
            result["reference"] = "x" * 4097
        if self.mode.startswith("detail-"):
            result.update(
                library_id="BFT_Footprints:Actual",
                pads=[{"number": "1", "x_nm": 1_000_000, "y_nm": 2_000_000}],
                models=[
                    {
                        "filename": "${KIPRJMOD}/BFT_3DSTEP/Actual.step",
                        "offset": [1.25, -2.5, 3.75],
                        "rotation": [10, 20, 30],
                        "scale": [1, 2, 3],
                        "visible": True,
                    }
                ],
            )
            if self.mode == "detail-library-echo":
                result["library_id"] = self.token
            if self.mode == "detail-pad-echo":
                result["pads"][0]["number"] = self.endpoint
            if self.mode == "detail-model-echo":
                result["models"][0]["filename"] = self.token
            if self.mode == "detail-nonfinite":
                result["models"][0]["offset"][0] = float("nan")
            if self.mode == "detail-bool":
                result["models"][0]["scale"][0] = True
            if self.mode == "detail-limit":
                result["pads"] *= 10001
            if self.mode == "detail-container":
                result["models"] = {"wrong": "container"}
        return [result]

    def close(self):
        """@brief Closes the synthetic backend without external effects.
        @return None.
        @details No native connection or persistent state exists.
        """


def session(tmp_path, mode="ready"):
    """@brief Constructs one explicitly labeled injected IPC test session.
    @param tmp_path Absolute disposable test project root.
    @param mode Selected fake behavior.
    @return Session after synthetic boundary discovery.
    @details Does not create PCB files or a live native IPC connection.
    """
    return IpcSession(
        "ipc://synthetic-selected-instance",
        TOKEN,
        tmp_path / "board.kicad_pcb",
        timeout_seconds=5,
        _backend_factory=partial(
            FakeBackend, project_path=str(tmp_path), mode=mode
        ),
    )


def test_explicit_scope_and_safe_immutable_inspection(tmp_path):
    """@brief Verifies explicit component reads and operational record safety.
    @param tmp_path Disposable explicit project identity.
    @return None.
    @details Injected evidence is labeled; credentials cannot enter records.
    """
    connected = session(tmp_path)
    try:
        result = connected.read_board()
        assert result.capabilities.evidence_origin == "injected-test"
        assert result.capabilities.binding_api_build == BINDING_API_BUILD
        assert Path(result.capabilities.board_path).name == "board.kicad_pcb"
        assert "get_footprints" in result.capabilities.operations
        assert result.footprints[0].x_mm == "1.25"
        assert result.footprints[0].y_mm == "2.5"
        assert result.footprints[0].orientation_degrees == "90.0"
        serialized = json.dumps(result.as_dict())
        assert TOKEN not in serialized
        assert "ipc://" not in serialized
        assert TOKEN not in repr(connected)
        assert not hasattr(connected, "__dict__")
        with pytest.raises(TypeError, match="cannot be serialized"):
            pickle.dumps(connected)
        with pytest.raises(FrozenInstanceError):
            result.capabilities.board_path = "other"
        assert TOKEN not in repr(asdict(result.capabilities))
    finally:
        connected.close()


@pytest.mark.parametrize(
    "mode",
    [
        "library-echo",
        "pad-echo",
        "model-echo",
        "nonfinite",
        "bool",
        "limit",
        "container",
    ],
)
def test_detail_fields_fail_closed(tmp_path, mode):
    """@brief Rejects unsafe nested pad and model fields.
    @param tmp_path Disposable synthetic selected project.
    @param mode Invalid nested response scenario.
    @return None.
    @details Injected negative evidence cannot replace real native acceptance.
    """
    connected = session(tmp_path, "detail-" + mode)
    with pytest.raises(IpcError) as error:
        connected.read_board()
    assert TOKEN not in str(error.value)
    assert error.value.reason == (
        IpcFailureReason.RESOURCE_LIMIT
        if mode == "limit"
        else IpcFailureReason.UNSAFE_RESPONSE
    )
    assert not connected.connected


def test_declared_model_units_and_immutable_details(tmp_path):
    """@brief Preserves explicit local model parameters and global pad units.
    @param tmp_path Disposable synthetic selected project.
    @return None.
    @details Nonzero injected vectors test conversion and immutability only.
    """
    connected = session(tmp_path, "detail-ready")
    result = connected.read_board().footprints[0]
    assert result.pads[0].y_mm == "-2"
    assert result.models[0].offset_mm == ("1.25", "-2.5", "3.75")
    assert result.models[0].rotation_degrees == ("10", "20", "30")
    with pytest.raises(FrozenInstanceError):
        result.models[0].filename = "changed"
    connected.close()


@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("binding", IpcFailureReason.VERSION_MISMATCH),
        ("api", IpcFailureReason.VERSION_MISMATCH),
        ("version", IpcFailureReason.VERSION_MISMATCH),
        ("wrong", IpcFailureReason.WRONG_BOARD),
        ("duplicate", IpcFailureReason.WRONG_BOARD),
        ("none", IpcFailureReason.WRONG_BOARD),
        ("documents-limit", IpcFailureReason.RESOURCE_LIMIT),
        ("project-secret", IpcFailureReason.UNSAFE_RESPONSE),
        ("relative-project", IpcFailureReason.INVALID_ARGUMENT),
    ],
)
def test_discovery_fails_closed(tmp_path, mode, reason):
    """@brief Rejects unsupported versions or ambiguous/wrong project context.
    @param tmp_path Expected disposable project root.
    @param mode Injected discovery failure scenario.
    @param reason Expected stable failure detail.
    @return None.
    @details Error text never echoes synthetic credentials or server text.
    """
    with pytest.raises(IpcError) as captured:
        session(tmp_path, mode)
    assert captured.value.reason == reason
    assert TOKEN not in str(captured.value)
    assert TOKEN not in repr(captured.value)


@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("context", IpcFailureReason.CONTEXT_CHANGED),
        ("raw-error", IpcFailureReason.DISCONNECTED),
        ("token-mismatch", IpcFailureReason.TOKEN_MISMATCH),
        ("unavailable", IpcFailureReason.OPERATION_UNAVAILABLE),
        ("echo", IpcFailureReason.UNSAFE_RESPONSE),
        ("endpoint-echo", IpcFailureReason.UNSAFE_RESPONSE),
        ("bad-coordinate", IpcFailureReason.UNSAFE_RESPONSE),
        ("items-limit", IpcFailureReason.RESOURCE_LIMIT),
        ("duplicate-item", IpcFailureReason.UNSAFE_RESPONSE),
        ("oversize", IpcFailureReason.UNSAFE_RESPONSE),
    ],
)
def test_read_failures_invalidate_without_reconnection(tmp_path, mode, reason):
    """@brief Invalidates operational state on restart/context/read failures.
    @param tmp_path Expected disposable project root.
    @param mode Injected component inspection failure.
    @param reason Expected stable safe failure detail.
    @return None.
    @details A later request cannot reconnect or reuse cleared credentials.
    """
    connected = session(tmp_path, mode)
    with pytest.raises(IpcError) as captured:
        connected.read_board()
    assert captured.value.reason == reason
    assert TOKEN not in repr(captured.value)
    assert not connected.connected
    assert connected._token is None
    assert connected._endpoint is None
    with pytest.raises(IpcError) as closed:
        connected.read_board()
    assert closed.value.reason == IpcFailureReason.CLOSED


def test_timeout_terminates_owned_worker(tmp_path):
    """@brief Bounds a hung binding call and cleans up its disposable worker.
    @param tmp_path Expected disposable project root.
    @return None.
    @details A fake stall proves cleanup without supplying live timing.
    """
    connected = session(tmp_path, "hang")
    existing = {child.pid for child in multiprocessing.active_children()}
    connected._timeout = 0.2
    started = time.monotonic()
    with pytest.raises(IpcError) as captured:
        connected.read_board()
    assert captured.value.reason == IpcFailureReason.TIMEOUT
    assert time.monotonic() - started < 2
    assert not connected.connected
    assert {
        child.pid for child in multiprocessing.active_children()
    } == existing


def test_provider_output_does_not_escape_worker(tmp_path, capfd):
    """@brief Suppresses provider stdout that could echo transient credentials.
    @param tmp_path Expected disposable project root.
    @param capfd Captured parent/child file-descriptor output fixture.
    @return None.
    @details Operational records remain available without retaining raw output.
    """
    connected = session(tmp_path, "print-secret")
    try:
        connected.read_board()
    finally:
        connected.close()
    captured = capfd.readouterr()
    assert TOKEN not in captured.out + captured.err
    assert "ipc://" not in captured.out + captured.err


@pytest.mark.parametrize(
    ("endpoint", "token"),
    [
        ("", TOKEN),
        ("ipc://selected", ""),
        ("ipc://selected", "  "),
        ("default", TOKEN),
        ("ipc://selected\n", TOKEN),
    ],
)
def test_missing_or_unsafe_session_arguments(tmp_path, endpoint, token):
    """@brief Refuses absent or unsafe connection input before native calls.
    @param tmp_path Expected disposable project root.
    @param endpoint Candidate explicit endpoint.
    @param token Candidate transient token.
    @return None.
    @details No arbitrary native socket discovery is performed.
    """
    with pytest.raises(IpcError):
        IpcSession(endpoint, token, tmp_path / "board.kicad_pcb")


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), 16])
def test_deadline_validation(tmp_path, timeout):
    """@brief Requires an effective finite bounded native operation deadline.
    @param tmp_path Expected disposable project root.
    @param timeout Invalid deadline input.
    @return None.
    @details Validation occurs before starting a native worker.
    """
    with pytest.raises(IpcError):
        IpcSession(
            "ipc://selected",
            TOKEN,
            tmp_path / "board.kicad_pcb",
            timeout_seconds=timeout,
        )


@pytest.mark.parametrize(
    ("x", "y", "native"),
    [
        ("0", "0", (0, 0)),
        ("1", "2", (1_000_000, -2_000_000)),
        ("-0.000001", "0.000001", (-1, -1)),
        ("2147.483647", "2147.483648", (NATIVE_MAX, NATIVE_MIN)),
    ],
)
def test_exact_coordinate_roundtrip(x, y, native):
    """@brief Verifies exact scale, native limits and explicit Y inversion.
    @param x Engineering positive-right mm fixture.
    @param y Engineering positive-up mm fixture.
    @param native Expected signed native nanometer pair.
    @return None.
    @details Caller decimal precision cannot change the conversion result.
    """
    with localcontext() as context:
        context.prec = 3
        assert engineering_to_native(x, y) == native
        assert native_to_engineering(*native) == (Decimal(x), Decimal(y))


@pytest.mark.parametrize(
    "value",
    [0.1, True, "NaN", "Infinity", "0.0000001", "2147.483648"],
)
def test_coordinate_precision_and_range_fail(value):
    """@brief Rejects floating, nonfinite, sub-nanometer or overflow inputs.
    @param value Invalid engineering distance fixture.
    @return None.
    @details Conversion cannot silently truncate or approximate dimensions.
    """
    with pytest.raises(UnitConversionError):
        millimeters_to_nanometers(value)


@pytest.mark.parametrize("value", [NATIVE_MIN - 1, NATIVE_MAX + 1, True, 1.0])
def test_native_coordinate_limits(value):
    """@brief Enforces actual signed native coordinates at the read boundary.
    @param value Invalid native scalar fixture.
    @return None.
    @details Oversized protobuf int64 values cannot enter engineering records.
    """
    with pytest.raises(UnitConversionError):
        nanometers_to_millimeters(value)


@pytest.mark.parametrize("angle", ["0", "90", "180", "270", "-90", "0.1"])
def test_degree_orientation_roundtrip(angle):
    """@brief Preserves physical degree orientation across the Y-down boundary.
    @param angle Exact cardinal or fractional engineering angle.
    @return None.
    @details Native positive 90 degrees maps positive X toward negative Y.
    """
    native = engineering_angle_to_native(angle)
    assert native_angle_to_engineering(native) == Decimal(angle)
    if angle == "90":
        assert engineering_to_native("0", "1") == (0, -1_000_000)


def test_unrepresentable_native_angles_fail():
    """@brief Rejects angles that cannot preserve exact decimal identity.
    @return None.
    @details Neither float conversion nor nonfinite reads silently approximate.
    """
    with pytest.raises(UnitConversionError):
        engineering_angle_to_native("0.123456789123456789")
    with pytest.raises(UnitConversionError):
        native_angle_to_engineering(float("inf"))


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (1, IpcFailureReason.TOKEN_MISMATCH),
        (2, IpcFailureReason.TIMEOUT),
        (3, IpcFailureReason.OPERATION_UNAVAILABLE),
        (4, IpcFailureReason.OPERATION_UNAVAILABLE),
        (5, IpcFailureReason.DISCONNECTED),
    ],
)
def test_native_status_mapping_excludes_raw_error_text(code, reason):
    """@brief Maps official status categories without exposing provider values.
    @param code Synthetic numeric status assigned to the pinned API category.
    @param reason Expected value-free operational reason.
    @return None.
    @details Executes adapter translation only, without fake live capability.
    """
    backend = _OfficialBackend.__new__(_OfficialBackend)
    backend._status = SimpleNamespace(
        AS_TOKEN_MISMATCH=1, AS_TIMEOUT=2, AS_UNHANDLED=3, AS_UNIMPLEMENTED=4
    )

    def failing_call():
        """@brief Raises a raw synthetic provider error containing a token.
        @return Never returns.
        @details Only the closed status category may leave the adapter wrapper.
        """
        error = RuntimeError(TOKEN)
        error.code = code
        raise error

    with pytest.raises(IpcError) as captured:
        backend._call(failing_call)
    assert captured.value.reason == reason
    assert TOKEN not in str(captured.value)
    assert captured.value.__suppress_context__
    assert captured.value.__cause__ is None
