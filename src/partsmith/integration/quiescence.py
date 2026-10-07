"""@package partsmith.integration.quiescence
@brief Requires explicit saved/closed managed-project writer exclusion.
@details The pinned IPC API has no verified dirty/save/close operation. Checks
read executable names only, never process arguments, tokens or private paths.
"""

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

from partsmith.integration.errors import FailureCode, IntegrationError


class ProcessEntry(ctypes.Structure):
    """@brief Matches the official PROCESSENTRY32W Toolhelp ABI.
    @details Heap identity is pointer-sized; executable names are WCHAR[260].
    """

    _fields_ = [
        ("size", wintypes.DWORD),
        ("usage", wintypes.DWORD),
        ("pid", wintypes.DWORD),
        ("heap", ctypes.c_size_t),
        ("module", wintypes.DWORD),
        ("threads", wintypes.DWORD),
        ("parent", wintypes.DWORD),
        ("priority", wintypes.LONG),
        ("flags", wintypes.DWORD),
        ("executable", wintypes.WCHAR * 260),
    ]


def require_closed_editors() -> None:
    """@brief Refuses publication while native KiCad editors/CLI are running.
    @return None.
    @details Names-only enumeration is conservative across all projects.
    It never saves/closes applications or treats absent lock markers as proof.
    """
    if os.name != "nt":
        raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessEntry),
    ]
    kernel.Process32NextW.argtypes = kernel.Process32FirstW.argtypes
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
    entry = ProcessEntry()
    entry.size = ctypes.sizeof(entry)
    try:
        success = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        if not success:
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
        while success:
            if entry.executable.casefold() in {
                "pcbnew.exe",
                "eeschema.exe",
                "kicad-cli.exe",
            }:
                raise IntegrationError(
                    FailureCode.TARGET_CONFLICT, action="close-editors"
                )
            success = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:
            raise IntegrationError(FailureCode.UNSUPPORTED_ATOMIC_INSTALL)
    finally:
        kernel.CloseHandle(snapshot)


@dataclass(frozen=True)
class ClosedProject:
    """@brief Records deliberate transient user writer-exclusion confirmation.
    @details Session loading never restores this confirmation automatically.
    """

    project_id: str
    confirmed: bool

    def require(self, target: dict) -> None:
        """@brief Verifies explicit consent and live native editor absence.
        @param target Independently selected current logical target.
        @return None.
        @details Caller promises exclusive editing for this operation; a
        cancelled or wrong-target confirmation cannot authorize publication.
        """
        if (
            self.confirmed is not True
            or self.project_id != target["project_id"]
        ):
            raise IntegrationError(
                FailureCode.TARGET_CONFLICT, action="confirm-closed-project"
            )
        require_closed_editors()
