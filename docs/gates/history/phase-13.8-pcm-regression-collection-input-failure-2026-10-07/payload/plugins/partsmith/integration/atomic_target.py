"""@package partsmith.integration.atomic_target
@brief Probes one NTFS junction boundary in exclusively disposable targets.
@details This feasibility helper is not a production publisher. It creates its
own new workspace, keeps complete immutable generations, and changes one mount
point using FSCTL_SET_REPARSE_POINT. Reader consistency requires one root
handle; independent path opens and KiCad caches require quiescence and refresh.
"""

from __future__ import annotations

import ctypes
import os
import re
import secrets
import stat
import struct
from contextlib import contextmanager
from ctypes import wintypes
from hashlib import sha256
from pathlib import Path

from partsmith.integration.contracts import portable_path
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.policy import ResourcePolicy

MOUNT_POINT_TAG = 0xA0000003
SET_REPARSE = 0x000900A4
GET_REPARSE = 0x000900A8
BACKUP_SEMANTICS = 0x02000000
OPEN_REPARSE_POINT = 0x00200000
SHARE_ALL = 7


class UnicodeString(ctypes.Structure):
    """@brief Matches the native counted Unicode string ABI.
    @details The backing UTF-16 buffer remains alive during NtCreateFile.
    """

    _fields_ = [
        ("length", wintypes.USHORT),
        ("maximum_length", wintypes.USHORT),
        ("buffer", wintypes.LPWSTR),
    ]


class ObjectAttributes(ctypes.Structure):
    """@brief Matches native object attributes for root-relative file opens.
    @details RootDirectory anchors each descendant to the selected directory.
    """

    _fields_ = [
        ("length", wintypes.ULONG),
        ("root", wintypes.HANDLE),
        ("name", ctypes.POINTER(UnicodeString)),
        ("attributes", wintypes.ULONG),
        ("security", ctypes.c_void_p),
        ("quality", ctypes.c_void_p),
    ]


class IoStatusBlock(ctypes.Structure):
    """@brief Reserves the native IO status union and pointer-sized result.
    @details NtCreateFile writes its operation status and information here.
    """

    _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]


class FileInformation(ctypes.Structure):
    """@brief Matches Win32 file information including stable volume/file IDs.
    @details IDs distinguish the owned junction from an unrelated replacement.
    """

    _fields_ = [
        ("attributes", wintypes.DWORD),
        ("created", wintypes.FILETIME),
        ("accessed", wintypes.FILETIME),
        ("written", wintypes.FILETIME),
        ("volume", wintypes.DWORD),
        ("size_high", wintypes.DWORD),
        ("size_low", wintypes.DWORD),
        ("links", wintypes.DWORD),
        ("index_high", wintypes.DWORD),
        ("index_low", wintypes.DWORD),
    ]


def junction_buffer(target: Path) -> bytes:
    """@brief Encodes one exact NTFS directory mount-point destination.
    @param target Absolute local generation directory.
    @return Complete REPARSE_DATA_BUFFER bytes.
    @details UTF-16 offsets are byte counts and exclude each null terminator.
    """
    display = str(target).encode("utf-16-le")
    substitute = ("\\??\\" + str(target)).encode("utf-16-le")
    payload = substitute + b"\0\0" + display + b"\0\0"
    if len(payload) + 16 > 16384:
        raise IntegrationError(FailureCode.RESOURCE_LIMIT)
    return (
        struct.pack(
            "<IHHHHHH",
            MOUNT_POINT_TAG,
            len(payload) + 8,
            0,
            0,
            len(substitute),
            len(substitute) + 2,
            len(display),
        )
        + payload
    )


class WindowsFiles:
    """@brief Wraps bounded Win32 calls used by the disposable prototype.
    @details Calls use explicit Unicode paths and native handles.
    """

    def __init__(self):
        """@brief Loads explicit Win32 signatures on the supported OS.
        @return None.
        @details Other platforms fail with UNSUPPORTED_ATOMIC_INSTALL.
        """
        if os.name != "nt":
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.native = ctypes.WinDLL("ntdll", use_last_error=True)
        signatures = {
            "CreateFileW": (
                [
                    wintypes.LPCWSTR,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.HANDLE,
                ],
                wintypes.HANDLE,
            ),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
            "DeviceIoControl": (
                [
                    wintypes.HANDLE,
                    wintypes.DWORD,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.c_void_p,
                ],
                wintypes.BOOL,
            ),
            "GetFileInformationByHandle": (
                [wintypes.HANDLE, ctypes.POINTER(FileInformation)],
                wintypes.BOOL,
            ),
            "GetFileSizeEx": (
                [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)],
                wintypes.BOOL,
            ),
            "ReadFile": (
                [
                    wintypes.HANDLE,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.c_void_p,
                ],
                wintypes.BOOL,
            ),
            "GetVolumePathNameW": (
                [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD],
                wintypes.BOOL,
            ),
            "GetVolumeInformationW": (
                [
                    wintypes.LPCWSTR,
                    wintypes.LPWSTR,
                    wintypes.DWORD,
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.POINTER(wintypes.DWORD),
                    wintypes.LPWSTR,
                    wintypes.DWORD,
                ],
                wintypes.BOOL,
            ),
            "GetDriveTypeW": ([wintypes.LPCWSTR], wintypes.UINT),
            "GetFinalPathNameByHandleW": (
                [
                    wintypes.HANDLE,
                    wintypes.LPWSTR,
                    wintypes.DWORD,
                    wintypes.DWORD,
                ],
                wintypes.DWORD,
            ),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        self.native.NtCreateFile.argtypes = [
            ctypes.POINTER(wintypes.HANDLE),
            wintypes.DWORD,
            ctypes.POINTER(ObjectAttributes),
            ctypes.POINTER(IoStatusBlock),
            ctypes.c_void_p,
            wintypes.ULONG,
            wintypes.ULONG,
            wintypes.ULONG,
            wintypes.ULONG,
            ctypes.c_void_p,
            wintypes.ULONG,
        ]
        self.native.NtCreateFile.restype = wintypes.LONG
        self.native.RtlNtStatusToDosError.argtypes = [wintypes.LONG]
        self.native.RtlNtStatusToDosError.restype = wintypes.ULONG

    @contextmanager
    def directory(self, path: Path, *, reparse=False, write=False, share=7):
        """@brief Opens and closes one directory or mount-point handle.
        @param path Explicit absolute directory path.
        @param reparse Opens the reparse object instead of its destination.
        @param write Requests reparse-update access when true.
        @param share Exact Win32 sharing mask.
        @return Context-managed native directory handle.
        @details Sharing and access errors are returned before any update.
        """
        flags = BACKUP_SEMANTICS | (OPEN_REPARSE_POINT if reparse else 0)
        access = 0x40000000 if write else 0x80000000
        handle = self.kernel.CreateFileW(
            str(path), access, share, None, 3, flags, None
        )
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield handle
        finally:
            self.kernel.CloseHandle(handle)

    def reparse(self, handle, data: bytes | None = None) -> bytes:
        """@brief Gets or replaces one reparse payload through its handle.
        @param handle Open reparse-object directory handle.
        @param data Exact replacement buffer, or None to read.
        @return Raw readback bytes, or empty bytes after an update.
        @details A replacement uses exactly one FSCTL_SET_REPARSE_POINT call.
        """
        count = wintypes.DWORD()
        output = ctypes.create_string_buffer(16384) if data is None else None
        source = (
            ctypes.create_string_buffer(data) if data is not None else None
        )
        success = self.kernel.DeviceIoControl(
            handle,
            GET_REPARSE if data is None else SET_REPARSE,
            source,
            len(data) if data is not None else 0,
            output,
            16384 if output is not None else 0,
            ctypes.byref(count),
            None,
        )
        if not success:
            raise ctypes.WinError(ctypes.get_last_error())
        return output.raw[: count.value] if output is not None else b""

    def identity(self, handle) -> tuple[int, int, int]:
        """@brief Gets the stable volume and file ID of an opened directory.
        @param handle Open directory handle.
        @return Volume serial and high/low file-index components.
        @details Replacement of the owned junction is detected independently.
        """
        information = FileInformation()
        if not self.kernel.GetFileInformationByHandle(
            handle, ctypes.byref(information)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return (
            information.volume,
            information.index_high,
            information.index_low,
        )

    def volume(self, path: Path) -> dict:
        """@brief Requires one local fixed NTFS volume for the probe.
        @param path Existing absolute directory.
        @return Filesystem, volume serial and drive-type evidence.
        @details Remote, removable and other filesystems are unsupported.
        """
        root = ctypes.create_unicode_buffer(1024)
        filesystem = ctypes.create_unicode_buffer(128)
        serial, maximum, flags = (wintypes.DWORD() for _ in range(3))
        if not self.kernel.GetVolumePathNameW(str(path), root, len(root)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.kernel.GetVolumeInformationW(
            root.value,
            None,
            0,
            ctypes.byref(serial),
            ctypes.byref(maximum),
            ctypes.byref(flags),
            filesystem,
            len(filesystem),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        kind = self.kernel.GetDriveTypeW(root.value)
        if filesystem.value != "NTFS" or kind != 3:
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        return {
            "filesystem": filesystem.value,
            "serial": serial.value,
            "drive_type": kind,
        }

    def final_path(self, handle) -> Path:
        """@brief Resolves a followed root handle to its actual generation.
        @param handle Open root directory handle.
        @return Exact absolute generation directory path.
        @details This is evidence; descendant reads use RootDirectory handles.
        """
        buffer = ctypes.create_unicode_buffer(4096)
        length = self.kernel.GetFinalPathNameByHandleW(
            handle, buffer, len(buffer), 0
        )
        if not length or length >= len(buffer):
            raise OSError("Could not resolve the opened generation root")
        return Path(buffer.value.removeprefix("\\\\?\\"))

    def is_elevated(self) -> bool:
        """@brief Queries the actual process token elevation state.
        @return True only when the current process has an elevated token.
        @details Does not request, enable or modify any Windows privilege.
        """
        security = ctypes.WinDLL("advapi32", use_last_error=True)
        security.OpenProcessToken.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        security.OpenProcessToken.restype = wintypes.BOOL
        security.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        security.GetTokenInformation.restype = wintypes.BOOL
        token = wintypes.HANDLE()
        if not security.OpenProcessToken(
            wintypes.HANDLE(-1), 0x0008, ctypes.byref(token)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            elevated, count = wintypes.DWORD(), wintypes.DWORD()
            if not security.GetTokenInformation(
                token,
                20,
                ctypes.byref(elevated),
                ctypes.sizeof(elevated),
                ctypes.byref(count),
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            return bool(elevated.value)
        finally:
            self.kernel.CloseHandle(token)

    def read_relative(self, root_handle, path: str) -> bytes:
        """@brief Reads a bounded file relative to one opened generation root.
        @param root_handle Followed directory handle anchoring the generation.
        @param path Portable descendant file path.
        @return Exact file bytes from the selected generation.
        @details NtCreateFile RootDirectory prevents repeated junction lookup.
        Generation content must be exclusively owned and contain no reparses.
        """
        name = portable_path(path).replace("/", "\\")
        text = ctypes.create_unicode_buffer(name)
        encoded_length = len(name.encode("utf-16-le"))
        string = UnicodeString(
            encoded_length,
            encoded_length + 2,
            ctypes.cast(text, wintypes.LPWSTR),
        )
        attributes = ObjectAttributes(
            ctypes.sizeof(ObjectAttributes),
            root_handle,
            ctypes.pointer(string),
            0x40,
            None,
            None,
        )
        handle, status_block = wintypes.HANDLE(), IoStatusBlock()
        status = self.native.NtCreateFile(
            ctypes.byref(handle),
            0x00100001,
            ctypes.byref(attributes),
            ctypes.byref(status_block),
            None,
            0x80,
            SHARE_ALL,
            1,
            0x20 | 0x40 | 0x00200000,
            None,
            0,
        )
        if status < 0:
            raise ctypes.WinError(self.native.RtlNtStatusToDosError(status))
        try:
            length = ctypes.c_longlong()
            if not self.kernel.GetFileSizeEx(handle, ctypes.byref(length)):
                raise ctypes.WinError(ctypes.get_last_error())
            ResourcePolicy().require_sizes([length.value])
            output = bytearray()
            while len(output) < length.value:
                chunk = ctypes.create_string_buffer(
                    min(1024 * 1024, length.value - len(output))
                )
                count = wintypes.DWORD()
                if not self.kernel.ReadFile(
                    handle, chunk, len(chunk), ctypes.byref(count), None
                ):
                    raise ctypes.WinError(ctypes.get_last_error())
                if not count.value:
                    raise OSError(
                        "Generation file changed during anchored read"
                    )
                output.extend(chunk.raw[: count.value])
            return bytes(output)
        finally:
            self.kernel.CloseHandle(handle)


def _ordinary_ancestors(path: Path) -> None:
    """@brief Refuses roots or ancestors containing foreign reparse objects.
    @param path Existing lexical absolute directory.
    @return None.
    @details No reparse is followed while validating ownership containment.
    """
    for entry in (path, *path.parents):
        info = entry.lstat()
        if not stat.S_ISDIR(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)


class AtomicTargetProbe:
    """@brief Owns disposable complete generations and one active junction.
    @details Creation requires an absent workspace. No existing project,
    ordinary target directory or imported junction is adopted or replaced.
    """

    def __init__(self, workspace: Path, generations: dict, initial: str):
        """@brief Creates fresh generations and the exclusively owned junction.
        @param workspace Absent absolute disposable workspace.
        @param generations Names mapped to complete relative-path byte sets.
        @param initial Existing generation name selected initially.
        @return None.
        @details Uses no privilege adjustment, elevation, shell or rename gap.
        """
        self.api = WindowsFiles()
        workspace = Path(workspace)
        if (
            not workspace.is_absolute()
            or workspace == Path(workspace.anchor)
            or ".." in workspace.parts
            or workspace.drive.startswith("\\")
        ):
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        _ordinary_ancestors(workspace.parent)
        if workspace.exists() or workspace.is_symlink():
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        if initial not in generations or len(generations) < 2:
            raise ValueError(
                "The probe requires at least two complete generations"
            )
        ResourcePolicy().require_sizes(
            [
                len(blob)
                for files in generations.values()
                for blob in files.values()
            ]
        )
        self.volume = self.api.volume(workspace.parent)
        self.workspace = workspace
        self.owner = secrets.token_hex(16)
        self.marker = workspace / ".atomic-probe-owner"
        self.link = workspace / "active"
        self.generations, self.inventories = {}, {}
        workspace.mkdir()
        self.marker.write_text(self.owner, encoding="ascii")
        for name, files in generations.items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", name):
                raise ValueError("Invalid probe generation name")
            ResourcePolicy().require_sizes(
                [len(blob) for blob in files.values()]
            )
            target = workspace / name
            target.mkdir()
            for relative, blob in sorted(files.items()):
                path = target / portable_path(relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(blob)
            self.generations[name] = target
            self.inventories[name] = self._inventory(target)
        self.link.mkdir()
        self.current = initial
        with self.api.directory(self.link, reparse=True, write=True) as handle:
            self.api.reparse(
                handle, junction_buffer(self.generations[initial])
            )
            self.link_identity = self.api.identity(handle)
            self._require_target(handle, initial)

    def _inventory(self, target: Path) -> dict[str, str]:
        """@brief Hashes the owned inventory without following reparses.
        @param target Existing owned generation directory.
        @return Sorted relative file names mapped to SHA-256 identities.
        @details Reparse descendants and volume changes make the probe fail.
        """
        if target.parent != self.workspace or target == self.link:
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        _ordinary_ancestors(target)
        if self.api.volume(target) != self.volume:
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        paths = []
        for parent, directories, names in os.walk(target, followlinks=False):
            for name in [*directories, *names]:
                path = Path(parent) / name
                if getattr(path.lstat(), "st_file_attributes", 0) & (
                    stat.FILE_ATTRIBUTE_REPARSE_POINT
                ):
                    raise IntegrationError(
                        FailureCode.UNSUPPORTED_ATOMIC_INSTALL
                    )
            for name in names:
                path = Path(parent) / name
                paths.append(path)
        ResourcePolicy().require_sizes([path.stat().st_size for path in paths])
        files = {
            path.relative_to(target).as_posix(): sha256(
                path.read_bytes()
            ).hexdigest()
            for path in paths
        }
        return dict(sorted(files.items()))

    def _require_target(self, handle, name: str) -> None:
        """@brief Requires the exact owned mount-point payload and destination.
        @param handle Open reparse-object handle.
        @param name Expected generation name.
        @return None.
        @details Tags, both path spellings and complete raw bytes must match.
        """
        if self.api.reparse(handle) != junction_buffer(self.generations[name]):
            raise IntegrationError(FailureCode.TARGET_CONFLICT)

    def switch(self, new: str, *, expected: str, cancel=False) -> bool:
        """@brief Repoints the owned junction after exact base/content checks.
        @param new Intended complete generation name.
        @param expected Exact current generation name.
        @param cancel Cancels before the sole reparse replacement call.
        @return True after a switch, False for cancellation or an exact no-op.
        @details This is a feasibility operation with no production journal.
        Sharing failures leave the old payload intact; rollback uses this same
        operation in reverse. Concurrent external writers are unsupported.
        """
        if new not in self.generations or expected not in self.generations:
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        _ordinary_ancestors(self.workspace)
        if self.marker.read_text("ascii") != self.owner:
            raise IntegrationError(FailureCode.TARGET_CONFLICT)
        for name in (expected, new):
            if (
                self._inventory(self.generations[name])
                != self.inventories[name]
            ):
                raise IntegrationError(FailureCode.TAMPERED_SOURCE)
        with self.api.directory(self.link, reparse=True, write=True) as handle:
            if self.api.identity(handle) != self.link_identity:
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
            self._require_target(handle, expected)
            if cancel or new == expected:
                return False
            self.api.reparse(handle, junction_buffer(self.generations[new]))
            self._require_target(handle, new)
            self.current = new
            return True

    @contextmanager
    def reader(self):
        """@brief Anchors all reads in one opened complete-generation root.
        @return Context-managed followed root directory handle.
        @details Sharing permits retargeting while old roots stay open.
        A root handle remains selected until the caller explicitly reopens it.
        """
        with self.api.directory(self.link) as handle:
            target = self.api.final_path(handle)
            if target not in self.generations.values():
                raise IntegrationError(FailureCode.TARGET_CONFLICT)
            name = next(
                key
                for key, value in self.generations.items()
                if value == target
            )
            if self._inventory(target) != self.inventories[name]:
                raise IntegrationError(FailureCode.TAMPERED_SOURCE)
            yield handle

    def close(self) -> None:
        """@brief Removes the owned junction before disposable tree cleanup.
        @return None.
        @details Never recursively traverses a junction or deletes generations.
        The caller retains responsibility for its disposable workspace.
        """
        if self.link.exists():
            with self.api.directory(self.link, reparse=True) as handle:
                if self.api.identity(handle) != self.link_identity:
                    raise IntegrationError(FailureCode.TARGET_CONFLICT)
                self._require_target(handle, self.current)
            self.link.rmdir()
