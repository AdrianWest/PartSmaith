"""@package partsmith.integration.host
@brief Binds plugin lifetime to its launching Windows KiCad process.
@details Uses retained process identity without contacting the PCB API.
"""

import ctypes
import os
from ctypes import wintypes


class _ProcessEntry(ctypes.Structure):
    """@brief Holds the documented Windows process-snapshot record.
    @details Pointer-sized fields preserve the Windows AMD64 native layout.
    """

    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class WindowsHostApi:
    """@brief Exposes read-only Windows process and window lifetime checks.
    @details Never launches, terminates, focuses or modifies an application.
    """

    def __init__(self):
        """@brief Binds pointer-safe native Windows function signatures.
        @return None.
        @details Construction is restricted to the declared Windows runtime.
        """
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        functions = (
            (
                self.kernel,
                "CreateToolhelp32Snapshot",
                [wintypes.DWORD] * 2,
                wintypes.HANDLE,
            ),
            (
                self.kernel,
                "Process32FirstW",
                [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)],
                wintypes.BOOL,
            ),
            (
                self.kernel,
                "Process32NextW",
                [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)],
                wintypes.BOOL,
            ),
            (
                self.kernel,
                "OpenProcess",
                [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD],
                wintypes.HANDLE,
            ),
            (
                self.kernel,
                "WaitForSingleObject",
                [wintypes.HANDLE, wintypes.DWORD],
                wintypes.DWORD,
            ),
            (self.kernel, "CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
            (self.user, "IsWindowVisible", [wintypes.HWND], wintypes.BOOL),
            (
                self.user,
                "GetWindowTextW",
                [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int],
                ctypes.c_int,
            ),
            (
                self.user,
                "EnumWindows",
                [self.callback_type, wintypes.LPARAM],
                wintypes.BOOL,
            ),
        )
        for library, name, arguments, result in functions:
            function = getattr(library, name)
            function.argtypes = arguments
            function.restype = result

    def processes(self) -> dict[int, tuple[int, str]]:
        """@brief Reads one bounded snapshot of process ancestry.
        @return Mapping from PID to parent PID and executable basename.
        @details Closes the snapshot handle even if enumeration fails.
        """
        snapshot = self.kernel.CreateToolhelp32Snapshot(2, 0)
        if snapshot == ctypes.c_void_p(-1).value:
            raise OSError("HOST_PROCESS_SNAPSHOT_FAILED")
        entry = _ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        result = {}
        try:
            more = self.kernel.Process32FirstW(snapshot, ctypes.byref(entry))
            while more:
                result[entry.th32ProcessID] = (
                    entry.th32ParentProcessID,
                    entry.szExeFile.lower(),
                )
                more = self.kernel.Process32NextW(
                    snapshot, ctypes.byref(entry)
                )
            return result
        finally:
            self.kernel.CloseHandle(snapshot)

    def partsmith_is_open(self) -> bool:
        """@brief Checks for a visible PartSmith window before an upgrade.
        @return True if a main or inspection window is still visible.
        @details Covers older plugin processes surviving their closed host.
        """
        found = []

        def collect(window, parameter):
            """@brief Checks a window title without changing its state.
            @param window Enumerated top-level native window handle.
            @param parameter Unused Windows callback data.
            @return True to continue enumeration.
            @details Does not expose titles in installer diagnostics.
            """
            title = ctypes.create_unicode_buffer(512)
            self.user.GetWindowTextW(window, title, len(title))
            if self.user.IsWindowVisible(window) and title.value.startswith(
                "PartSmith"
            ):
                found.append(window)
            return True

        self.user.EnumWindows(self.callback_type(collect), 0)
        return bool(found)


def find_host_pid(processes, pid):
    """@brief Finds the nearest KiCad ancestor through Python launch wrappers.
    @param processes PID-to-parent-and-name snapshot mapping.
    @param pid Starting plugin process ID.
    @return KiCad ancestor PID or None when no launching host remains.
    @details Bounds traversal and rejects cycles and unrelated KiCad instances.
    """
    visited = set()
    for _ in range(32):
        if pid in visited or pid not in processes:
            return None
        visited.add(pid)
        parent, name = processes[pid]
        if name in {"kicad.exe", "pcbnew.exe"}:
            return pid
        pid = parent
    return None


class HostLifetime:
    """@brief Retains exact host identity until plugin teardown.
    @details The process handle prevents following a later reused PID.
    """

    def __init__(self, api, pid):
        """@brief Opens a read-only synchronization handle for the host.
        @param api Native lifetime API or bounded test double.
        @param pid Exact launching KiCad ancestor PID.
        @return None.
        @details Does not inspect board contents or retain launch credentials.
        """
        self.api = api
        self.handle = api.kernel.OpenProcess(0x100000, False, pid)

    def is_alive(self) -> bool:
        """@brief Checks whether the original launching host still exists.
        @return True only while the retained host identity remains alive.
        @details Polls without waiting, reconnecting or issuing IPC requests.
        """
        if not self.handle:
            return False
        return self.api.kernel.WaitForSingleObject(self.handle, 0) == 258

    def close(self) -> None:
        """@brief Releases the retained process handle exactly once.
        @return None.
        @details Closing the handle never terminates or modifies KiCad.
        """
        if self.handle:
            self.api.kernel.CloseHandle(self.handle)
            self.handle = None


def capture_launch_host():
    """@brief Captures the host through the actual local process ancestry.
    @return HostLifetime or None for an absent host or non-Windows runtime.
    @details Handles isolated-bootstrap and Windows virtualenv redirectors.
    """
    if os.name != "nt":
        return None
    api = WindowsHostApi()
    pid = find_host_pid(api.processes(), os.getpid())
    if pid is None:
        return None
    return HostLifetime(api, pid)
