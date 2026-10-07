"""@package partsmith.integration.ipc
@brief Binds bounded read-only IPC to an explicitly selected KiCad session.
@details Adapter 1.1 requires official kicad-python 0.8.0/API 10.0.6, exact
project/board discovery and a transient nonempty launch token. Every request
uses supervised workers; timeout, restart and context loss invalidate
the session. Credentials and token-derived hashes never enter returned records.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import re
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from importlib.metadata import version
from math import isfinite
from operator import itemgetter
from pathlib import Path
from threading import Lock
from uuid import uuid4

from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.units import (
    COORDINATE_ADAPTER_VERSION,
    UnitConversionError,
    native_angle_to_engineering,
    native_to_engineering,
)

ADAPTER_VERSION = "1.1"
SERIALIZER_VERSION = "1.0"
KICAD_VERSION = "10.0.6"
BINDING_VERSION = "0.8.0"
BINDING_API_BUILD = "10.0.6-0-gcaf7377e9c"
MAX_RECORD_BYTES = 2 * 1024 * 1024
MAX_DOCUMENTS = 128
MAX_FOOTPRINTS = 10_000
MAX_TIMEOUT_SECONDS = 15


class IpcFailureReason(StrEnum):
    """@brief Provides value-free operational IPC failure details.
    @details These details do not grant authority or change component state.
    """

    MISSING_SESSION = "MISSING_SESSION"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    MISSING_BINDING = "MISSING_BINDING"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    WRONG_BOARD = "WRONG_BOARD"
    CONTEXT_CHANGED = "CONTEXT_CHANGED"
    TOKEN_MISMATCH = "TOKEN_MISMATCH"
    DISCONNECTED = "DISCONNECTED"
    TIMEOUT = "TIMEOUT"
    OPERATION_UNAVAILABLE = "OPERATION_UNAVAILABLE"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    UNSAFE_RESPONSE = "UNSAFE_RESPONSE"
    CLOSED = "CLOSED"


class IpcError(IntegrationError):
    """@brief Exposes a stable IPC category without raw provider error text.
    @details Exception arguments, representation and chaining exclude secrets.
    """

    def __init__(self, reason: IpcFailureReason):
        """@brief Initializes a value-free read-only IPC failure.
        @param reason Closed operational failure reason.
        @return None.
        @details Never accepts endpoint, token or untrusted exception text.
        """
        if not isinstance(reason, IpcFailureReason):
            raise ValueError("Invalid IPC failure reason")
        self.reason = reason
        code = FailureCode.IPC_UNAVAILABLE
        if reason in (
            IpcFailureReason.WRONG_BOARD,
            IpcFailureReason.CONTEXT_CHANGED,
            IpcFailureReason.TOKEN_MISMATCH,
        ):
            code = FailureCode.WRONG_IPC_SESSION
        elif reason == IpcFailureReason.RESOURCE_LIMIT:
            code = FailureCode.RESOURCE_LIMIT
        super().__init__(code, action="ipc-inspect")
        self.args = (f"{code}: {reason}",)


@dataclass(frozen=True)
class IpcCapabilities:
    """@brief Records verified versions and explicit non-secret document scope.
    @details Injected backends are labeled and cannot constitute live proof.
    """

    schema_version: str
    adapter_version: str
    serializer_version: str
    coordinate_adapter: str
    kicad_version: str
    binding_version: str
    binding_api_version: str
    binding_api_build: str
    native_distance_unit: str
    engineering_distance_unit: str
    angle_unit: str
    native_frame: str
    engineering_frame: str
    engineering_convention_version: str
    board_path: str
    project_path: str
    project_name: str
    operations: tuple[str, ...]
    evidence_origin: str


@dataclass(frozen=True)
class PadInspection:
    """@brief Stores a native pad number and global engineering position.
    @details Distances are millimetres, X right and Y up at the board origin.
    """

    number: str
    x_mm: str
    y_mm: str


@dataclass(frozen=True)
class ModelInspection:
    """@brief Stores actual footprint-local 3D model placement parameters.
    @details Offsets are millimetres in KiCad model coordinates; rotations are
    degrees and scale is dimensionless. These are not board-world coordinates.
    """

    filename: str
    offset_mm: tuple[str, str, str]
    rotation_degrees: tuple[str, str, str]
    scale: tuple[str, str, str]
    visible: bool


@dataclass(frozen=True)
class FootprintInspection:
    """@brief Stores one actual footprint read in declared engineering units.
    @details Orientation/side remain explicit. This record authorizes no write.
    """

    item_id: str
    reference: str
    x_mm: str
    y_mm: str
    orientation_degrees: str
    side: str
    library_id: str = ""
    pads: tuple[PadInspection, ...] = ()
    models: tuple[ModelInspection, ...] = ()


@dataclass(frozen=True)
class BoardInspection:
    """@brief Reports an immutable bounded PCB component inspection.
    @details Discovery is repeated after reading to reject changed context.
    """

    capabilities: IpcCapabilities
    footprints: tuple[FootprintInspection, ...]

    def as_dict(self) -> dict:
        """@brief Produces a non-secret operational inspection record.
        @return Dictionary of explicit versions, scope and read results.
        @details The record contains no token, endpoint or reusable permission.
        """
        return asdict(self)


def _path(value: str | Path) -> str:
    """@brief Canonicalizes a required absolute local document path.
    @param value Declared absolute path without URI or shell expansion.
    @return Normalized absolute path for equality checks.
    @details Rejects ambiguous relative, empty and control-character inputs.
    """
    if not isinstance(value, (str, Path)):
        raise IpcError(IpcFailureReason.INVALID_ARGUMENT)
    text = str(value)
    if not text or len(text) > 4096 or any(ord(char) < 32 for char in text):
        raise IpcError(IpcFailureReason.INVALID_ARGUMENT)
    candidate = Path(text)
    if not candidate.is_absolute():
        raise IpcError(IpcFailureReason.INVALID_ARGUMENT)
    return os.path.normcase(os.path.normpath(str(candidate)))


def _text(value: str, token: str, endpoint: str) -> str:
    """@brief Checks a bounded non-secret field returned by native discovery.
    @param value Native text field selected for the operational record.
    @param token Transient token forbidden from output fields.
    @param endpoint Transient endpoint forbidden from output fields.
    @return Original safe text.
    @details Rejects controls, excess and token echoes without logging values.
    """
    if (
        not isinstance(value, str)
        or len(value) > 4096
        or token in value
        or endpoint in value
        or any(ord(char) < 32 for char in value)
    ):
        raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
    return value


def _model_vector(value) -> tuple[str, str, str]:
    """@brief Validates bounded native model vectors.
    @param value Three native numbers in declared model units.
    @return Finite decimal strings in the original declared units.
    @details Booleans, nonfinite values and unsafe magnitudes are rejected.
    """
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
    if any(
        type(v) not in (int, float) or not isfinite(v) or abs(v) > 1e9
        for v in value
    ):
        raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
    return tuple(format(Decimal(str(v)), "f") for v in value)


def _document_identity(document, token: str, endpoint: str) -> dict:
    """@brief Derives explicit board/project identity from an API document.
    @param document Official or injected document specifier.
    @param token Transient token forbidden in returned fields.
    @param endpoint Transient endpoint forbidden in returned fields.
    @return Safe normalized board/project identity dictionary.
    @details Resolves relative board names only within the absolute project.
    """
    project = _path(_text(document.project.path, token, endpoint))
    name = _text(document.project.name, token, endpoint)
    filename = _text(document.board_filename, token, endpoint)
    if not name or not filename or Path(filename).suffix != ".kicad_pcb":
        raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
    board = Path(filename)
    if not board.is_absolute():
        if board.name != filename:
            raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
        board = Path(project) / board
    board_path = _path(board)
    if _path(Path(board_path).parent) != project:
        raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
    return {
        "board_path": board_path,
        "project_path": project,
        "project_name": name,
    }


def _select_document(backend, expected_board: str, token: str, endpoint: str):
    """@brief Selects one matching PCB document from explicit discovery.
    @param backend Actual official binding backend or labeled test backend.
    @param expected_board Canonical absolute expected PCB path.
    @param token Transient launch token excluded from scope records.
    @param endpoint Transient endpoint excluded from scope records.
    @return Matching document and safe document identity.
    @details Never selects the binding's arbitrary first-board/default socket.
    """
    documents = backend.get_documents()
    if len(documents) > MAX_DOCUMENTS:
        raise IpcError(IpcFailureReason.RESOURCE_LIMIT)
    matching = []
    for document in documents:
        identity = _document_identity(document, token, endpoint)
        if identity["board_path"] == expected_board:
            matching.append((document, identity))
    if len(matching) != 1:
        raise IpcError(IpcFailureReason.WRONG_BOARD)
    return matching[0]


class _OfficialBackend:
    """@brief Adapts exactly the released official Python IPC binding.
    @details Private binding internals are pinned for receive-size and cleanup.
    """

    def __init__(self, endpoint: str, token: str, timeout_ms: int):
        """@brief Opens an explicit token-bound official client lazily.
        @param endpoint Explicit launch/selected named-pipe/socket endpoint.
        @param token Nonempty instance token retained only in this worker.
        @param timeout_ms Send/receive timeout in milliseconds.
        @return None.
        @details No default socket or token discovery is permitted.
        """
        try:
            import pynng
            from kipy import KiCad
            from kipy.board import Board
            from kipy.client import KiCadClient
            from kipy.kicad_api_version import KICAD_API_VERSION
            from kipy.proto.common import ApiStatusCode
            from kipy.proto.common.types import DocumentType
        except ImportError:
            raise IpcError(IpcFailureReason.MISSING_BINDING) from None

        class BoundedClient(KiCadClient):
            """@brief Limits received protobuf bytes before parsing.
            @details Uses pinned 0.8.0 transport connection internals only.
            """

            def _connect(self):
                """@brief Sets a receive limit immediately after connection.
                @return None.
                @details The supervisor also bounds blocking dial wall time.
                """
                super()._connect()
                self._conn.recv_max_size = 128 * 1024 * 1024

        self.binding_version = version("kicad-python")
        self.api_version = KICAD_API_VERSION
        self._client = BoundedClient(
            endpoint, "org.boardforge.partsmith", token, timeout_ms
        )
        self._kicad = KiCad.from_client(self._client)
        self._board_type = Board
        self._document_type = DocumentType.DOCTYPE_PCB
        self._status = ApiStatusCode
        self._timeout_type = pynng.exceptions.Timeout

    def _call(self, operation, *args):
        """@brief Converts native failures into closed value-free categories.
        @param operation Official binding callable to execute.
        @param args Explicit official method arguments.
        @return Actual native method result.
        @details Raw exceptions/error_message are never returned or chained.
        """
        try:
            return operation(*args)
        except Exception as error:
            code = getattr(error, "code", None)
            reason = IpcFailureReason.DISCONNECTED
            if code == self._status.AS_TOKEN_MISMATCH:
                reason = IpcFailureReason.TOKEN_MISMATCH
            elif code == self._status.AS_TIMEOUT:
                reason = IpcFailureReason.TIMEOUT
            elif code in (
                self._status.AS_UNHANDLED,
                self._status.AS_UNIMPLEMENTED,
            ):
                reason = IpcFailureReason.OPERATION_UNAVAILABLE
            else:
                chained = error
                for _ in range(4):
                    if isinstance(chained, getattr(self, "_timeout_type", ())):
                        reason = IpcFailureReason.TIMEOUT
                        break
                    chained = getattr(chained, "__context__", None)
            raise IpcError(reason) from None

    def get_version(self) -> str:
        """@brief Reads the actual connected native version.
        @return Numeric major/minor/patch version string.
        @details The transient launch token is checked by the native request.
        """
        result = self._call(self._kicad.get_version)
        return f"{result.major}.{result.minor}.{result.patch}"

    def get_documents(self):
        """@brief Enumerates open PCB documents without default selection.
        @return Actual official DocumentSpecifier sequence.
        @details No schematic IPC or design mutation is offered.
        """
        return self._call(self._kicad.get_open_documents, self._document_type)

    def get_footprints(self, document) -> list[dict]:
        """@brief Reads component instances from the explicitly selected board.
        @param document Verified matching native document specifier.
        @return Selected component fields in native units for validation.
        @details Reads only; caps component count before constructing records.
        """
        from kipy.board_types import BoardLayer

        board = self._board_type(self._client, document)
        footprints = self._call(board.get_footprints)
        if len(footprints) > MAX_FOOTPRINTS:
            raise IpcError(IpcFailureReason.RESOURCE_LIMIT)
        result = []
        detail_count = 0
        for footprint in footprints:
            pads = footprint.definition.pads
            models = footprint.definition.models
            detail_count += len(pads) + len(models)
            if detail_count > MAX_FOOTPRINTS:
                raise IpcError(IpcFailureReason.RESOURCE_LIMIT)
            side = {
                BoardLayer.BL_F_Cu: "top",
                BoardLayer.BL_B_Cu: "bottom",
            }.get(footprint.layer)
            if side is None:
                raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
            result.append(
                {
                    "item_id": footprint.id.value,
                    "reference": footprint.reference_field.text.value,
                    "x_nm": footprint.position.x,
                    "y_nm": footprint.position.y,
                    "angle": footprint.orientation.degrees,
                    "side": side,
                    "library_id": str(footprint.definition.id),
                    "pads": [
                        {
                            "number": pad.number,
                            "x_nm": pad.position.x,
                            "y_nm": pad.position.y,
                        }
                        for pad in pads
                    ],
                    "models": [
                        {
                            "filename": model.filename,
                            "offset": [
                                model.offset.x,
                                model.offset.y,
                                model.offset.z,
                            ],
                            "rotation": [
                                model.rotation.x,
                                model.rotation.y,
                                model.rotation.z,
                            ],
                            "scale": [
                                model.scale.x,
                                model.scale.y,
                                model.scale.z,
                            ],
                            "visible": model.visible,
                        }
                        for model in models
                    ],
                }
            )
        return result

    def close(self) -> None:
        """@brief Closes owned transport before the disposable worker exits.
        @return None.
        @details No session reconnect or persistent data mutation occurs.
        """
        connection = getattr(self._client, "_conn", None)
        if connection is not None:
            connection.close()


def _inspect_backend(
    backend,
    token: str,
    endpoint: str,
    expected_board: str,
    expected_scope: dict | None,
    read_components: bool,
    injected: bool,
) -> dict:
    """@brief Validates native version/context around a bounded board read.
    @param backend Official binding backend or explicitly injected test double.
    @param token Transient nonempty launch token.
    @param endpoint Transient explicit endpoint excluded from returned fields.
    @param expected_board Canonical absolute selected PCB path.
    @param expected_scope Prior verified scope or None for first discovery.
    @param read_components Whether to execute actual component inspection.
    @param injected Whether this run uses a test backend.
    @return Safe bounded operational payload without credentials.
    @details Rechecks version and document identity after component reads.
    """
    if (
        backend.binding_version != BINDING_VERSION
        or backend.api_version != BINDING_API_BUILD
        or backend.get_version() != KICAD_VERSION
    ):
        raise IpcError(IpcFailureReason.VERSION_MISMATCH)
    document, scope = _select_document(
        backend, expected_board, token, endpoint
    )
    if expected_scope is not None and scope != expected_scope:
        raise IpcError(IpcFailureReason.CONTEXT_CHANGED)
    records = []
    detail_count = 0
    if read_components:
        components = backend.get_footprints(document)
        if len(components) > MAX_FOOTPRINTS:
            raise IpcError(IpcFailureReason.RESOURCE_LIMIT)
        for component in components:
            x_mm, y_mm = native_to_engineering(
                component["x_nm"], component["y_nm"]
            )
            angle = native_angle_to_engineering(component["angle"])
            side = component["side"]
            if side not in ("top", "bottom"):
                raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
            item_id = _text(component["item_id"], token, endpoint)
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", item_id):
                raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
            records.append(
                {
                    "item_id": item_id,
                    "reference": _text(
                        component["reference"], token, endpoint
                    ),
                    "x_mm": str(x_mm),
                    "y_mm": str(y_mm),
                    "orientation_degrees": str(angle),
                    "side": side,
                }
            )
            pads = component.get("pads", [])
            models = component.get("models", [])
            if not isinstance(pads, list) or not isinstance(models, list):
                raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
            detail_count += len(pads) + len(models)
            if detail_count > MAX_FOOTPRINTS:
                raise IpcError(IpcFailureReason.RESOURCE_LIMIT)
            if not injected and not {"library_id", "pads", "models"} <= (
                component.keys()
            ):
                raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
            pad_records = []
            for pad in pads:
                x, y = native_to_engineering(pad["x_nm"], pad["y_nm"])
                pad_records.append(
                    {
                        "number": _text(pad["number"], token, endpoint),
                        "x_mm": str(x),
                        "y_mm": str(y),
                    }
                )
            model_records = []
            for model in models:
                if type(model["visible"]) is not bool:
                    raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
                model_records.append(
                    {
                        "filename": _text(model["filename"], token, endpoint),
                        "offset_mm": _model_vector(model["offset"]),
                        "rotation_degrees": _model_vector(model["rotation"]),
                        "scale": _model_vector(model["scale"]),
                        "visible": model["visible"],
                    }
                )
            records[-1].update(
                library_id=_text(
                    component.get("library_id", ""), token, endpoint
                ),
                pads=sorted(
                    pad_records,
                    key=itemgetter("number", "x_mm", "y_mm"),
                ),
                models=sorted(model_records, key=itemgetter("filename")),
            )
        if len({record["item_id"] for record in records}) != len(records):
            raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
        _, after_scope = _select_document(
            backend, expected_board, token, endpoint
        )
        if after_scope != scope or backend.get_version() != KICAD_VERSION:
            raise IpcError(IpcFailureReason.CONTEXT_CHANGED)
    operations = ["get_version", "get_api_version", "get_open_documents"]
    if read_components:
        operations.append("get_footprints")
    return {
        "capabilities": {
            "schema_version": "partsmith-ipc-capabilities-1.0",
            "adapter_version": ADAPTER_VERSION,
            "serializer_version": SERIALIZER_VERSION,
            "coordinate_adapter": COORDINATE_ADAPTER_VERSION,
            "kicad_version": KICAD_VERSION,
            "binding_version": BINDING_VERSION,
            "binding_api_version": KICAD_VERSION,
            "binding_api_build": BINDING_API_BUILD,
            "native_distance_unit": "nm",
            "engineering_distance_unit": "mm",
            "angle_unit": "degree",
            "native_frame": "native-board-origin-x-right-y-down",
            "engineering_frame": "native-board-origin-x-right-y-up",
            "engineering_convention_version": "1.1",
            **scope,
            "operations": operations,
            "evidence_origin": (
                "injected-test" if injected else "official-live-binding"
            ),
        },
        "footprints": sorted(records, key=itemgetter("item_id")),
    }


def _discard_native_output():
    """@brief Suppresses Python, CRT and Win32 worker output streams.
    @return Owned null-device text stream.
    @details Applies inside a disposable worker before provider calls.
    """
    sink = open(os.devnull, "w", encoding="utf-8")
    os.dup2(sink.fileno(), 1)
    os.dup2(sink.fileno(), 2)
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetStdHandle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
        kernel.SetStdHandle.restype = wintypes.BOOL
        handle = msvcrt.get_osfhandle(sink.fileno())
        if not kernel.SetStdHandle(-11, handle) or not kernel.SetStdHandle(
            -12, handle
        ):
            sink.close()
            raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
    return sink


def _worker(
    pipe,
    endpoint: str,
    token: str,
    expected_board: str,
    expected_scope: dict | None,
    timeout_ms: int,
    read_components: bool,
    backend_factory,
) -> None:
    """@brief Owns one disposable native IPC attempt without raw output.
    @param pipe Private in-memory result pipe to the supervisor.
    @param endpoint Explicit ephemeral native endpoint.
    @param token Explicit ephemeral native instance token.
    @param expected_board Absolute selected board identity.
    @param expected_scope Prior exact scope binding or None for discovery.
    @param timeout_ms Native transport timeout in milliseconds.
    @param read_components Whether to run component inspection.
    @param backend_factory Test injection or None for actual official binding.
    @return None.
    @details Sends only bounded JSON and closed failure reasons; no tracebacks.
    """
    sink = _discard_native_output()
    previous_output = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = sink
    backend = None
    try:
        factory = backend_factory or _OfficialBackend
        backend = factory(endpoint, token, timeout_ms)
        payload = _inspect_backend(
            backend,
            token,
            endpoint,
            expected_board,
            expected_scope,
            read_components,
            backend_factory is not None,
        )
        encoded = json.dumps({"ok": payload}).encode("utf-8")
        if len(encoded) > MAX_RECORD_BYTES:
            raise IpcError(IpcFailureReason.RESOURCE_LIMIT)
    except BaseException as error:
        reason = (
            error.reason
            if isinstance(error, IpcError)
            else (
                IpcFailureReason.UNSAFE_RESPONSE
                if isinstance(error, UnitConversionError)
                else IpcFailureReason.DISCONNECTED
            )
        )
        encoded = json.dumps({"error": str(reason)}).encode("utf-8")
    finally:
        if backend is not None:
            try:
                backend.close()
            except BaseException:
                pass
    try:
        pipe.send_bytes(encoded)
    except (BrokenPipeError, EOFError, OSError):
        pass
    finally:
        pipe.close()
        sys.stdout, sys.stderr = previous_output
        sink.close()


class IpcSession:
    """@brief Owns transient credentials for one explicitly connected instance.
    @details Serialization is forbidden. Failures close and erase credentials;
    no reconnect, design mutation or installation permission is offered.
    """

    __slots__ = (
        "_closed",
        "_endpoint",
        "_token",
        "_lock",
        "_expected_board",
        "_timeout",
        "_backend_factory",
        "_scope",
        "session_id",
        "capabilities",
    )

    def __init__(
        self,
        endpoint: str,
        token: str,
        expected_board: str | Path,
        *,
        timeout_seconds: float = 15,
        _backend_factory=None,
    ):
        """@brief Discovers a pinned instance and exact expected document.
        @param endpoint Explicit launch/selected IPC endpoint, never a default.
        @param token Nonempty transient launch/selected instance token.
        @param expected_board Absolute expected native PCB document path.
        @param timeout_seconds Deadline, at most policy 1.0's 15 seconds.
        @param _backend_factory Private labeled test injection only.
        @return None.
        @details Failure returns value-free diagnostics and cleans up.
        """
        self._closed = True
        self._endpoint = None
        self._token = None
        self._lock = Lock()
        if not endpoint or not token:
            raise IpcError(IpcFailureReason.MISSING_SESSION)
        if (
            not isinstance(endpoint, str)
            or not isinstance(token, str)
            or not endpoint.startswith("ipc://")
            or len(endpoint) > 4096
            or len(token) > 4096
            or not token.strip()
            or any(ord(char) < 32 for char in endpoint + token)
            or isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS
        ):
            raise IpcError(IpcFailureReason.INVALID_ARGUMENT)
        self._expected_board = _path(expected_board)
        if (
            not self._expected_board.endswith(".kicad_pcb")
            or token in self._expected_board
            or endpoint in self._expected_board
        ):
            raise IpcError(IpcFailureReason.INVALID_ARGUMENT)
        self._endpoint = endpoint
        self._token = token
        self._timeout = float(timeout_seconds)
        self._backend_factory = _backend_factory
        self._scope = None
        self._closed = False
        self.session_id = str(uuid4())
        result = self._request(False)
        self.capabilities = result.capabilities
        self._scope = {
            key: getattr(self.capabilities, key)
            for key in ("board_path", "project_path", "project_name")
        }

    def __repr__(self) -> str:
        """@brief Represents connection state without credentials or scope.
        @return Fixed safe state label.
        @details Endpoint and token values never enter representations.
        """
        return f"IpcSession(state={'closed' if self._closed else 'connected'})"

    def __getstate__(self):
        """@brief Refuses persistence of transient native session state.
        @return Never returns.
        @details Raises a fixed value-free TypeError for pickle/deepcopy.
        """
        raise TypeError("Transient IPC sessions cannot be serialized")

    @property
    def connected(self) -> bool:
        """@brief Reports whether the bound session remains usable.
        @return Boolean local session state.
        @details Every read still rechecks the actual native context.
        """
        return not self._closed

    def close(self) -> None:
        """@brief Invalidates the session and releases transient credentials.
        @return None.
        @details Idempotent and never invokes a native mutation or reconnect.
        """
        self._closed = True
        self._endpoint = None
        self._token = None

    def _request(self, read_components: bool) -> BoardInspection:
        """@brief Supervises one exact-bound IPC read with process cleanup.
        @param read_components Whether actual footprints must be inspected.
        @return Validated safe immutable inspection.
        @details Kills overdue workers; any failure invalidates the session.
        """
        with self._lock:
            if self._closed:
                raise IpcError(IpcFailureReason.CLOSED)
            context = multiprocessing.get_context("spawn")
            parent, child = context.Pipe(duplex=False)
            process = context.Process(
                target=_worker,
                args=(
                    child,
                    self._endpoint,
                    self._token,
                    self._expected_board,
                    self._scope,
                    max(1, int(self._timeout * 1000)),
                    read_components,
                    self._backend_factory,
                ),
                daemon=True,
            )
            started = False
            try:
                process.start()
                started = True
                child.close()
                if not parent.poll(self._timeout):
                    raise IpcError(IpcFailureReason.TIMEOUT)
                encoded = parent.recv_bytes(MAX_RECORD_BYTES)
                envelope = json.loads(encoded)
                if set(envelope) == {"error"}:
                    raise IpcError(IpcFailureReason(envelope["error"]))
                if set(envelope) != {"ok"}:
                    raise IpcError(IpcFailureReason.UNSAFE_RESPONSE)
                payload = envelope["ok"]
                capabilities = payload["capabilities"]
                capabilities["operations"] = tuple(capabilities["operations"])
                for item in payload["footprints"]:
                    item["pads"] = tuple(
                        PadInspection(**p) for p in item.get("pads", [])
                    )
                    model_records = []
                    for model in item.get("models", []):
                        for field in (
                            "offset_mm",
                            "rotation_degrees",
                            "scale",
                        ):
                            model[field] = tuple(model[field])
                        model_records.append(ModelInspection(**model))
                    item["models"] = tuple(model_records)
                result = BoardInspection(
                    IpcCapabilities(**capabilities),
                    tuple(
                        FootprintInspection(**item)
                        for item in payload["footprints"]
                    ),
                )
                if self._closed:
                    raise IpcError(IpcFailureReason.CLOSED)
                return result
            except IpcError:
                self.close()
                raise
            except BaseException:
                self.close()
                raise IpcError(IpcFailureReason.DISCONNECTED) from None
            finally:
                parent.close()
                child.close()
                if started:
                    process.join(0.2)
                    if process.is_alive():
                        process.terminate()
                        process.join(0.2)
                    if process.is_alive():
                        process.kill()
                        process.join(5)
                    if not process.is_alive():
                        process.close()

    def read_board(self) -> BoardInspection:
        """@brief Reads actual footprints from the bound expected board.
        @return Immutable version/scope/component inspection.
        @details Revalidates instance token, native version and exact context;
        changed board, restart, disconnect or timeout closes the session.
        """
        return self._request(True)


def connect_ipc(
    endpoint: str,
    token: str,
    expected_board: str | Path,
    *,
    timeout_seconds: float = 15,
) -> IpcSession:
    """@brief Connects only to the explicitly selected native PCB instance.
    @param endpoint Explicit transient launch/selected native IPC endpoint.
    @param token Explicit nonempty transient native instance token.
    @param expected_board Absolute intended PCB path.
    @param timeout_seconds Bounded native operation wall-clock deadline.
    @return Bound IpcSession after official version/document discovery.
    @details No default discovery, credential persistence or publication.
    """
    return IpcSession(
        endpoint, token, expected_board, timeout_seconds=timeout_seconds
    )
