"""@package partsmith.pcm.native
@brief Verifies loaded native libraries belong to the isolated runtime.
@details Windows operating-system DLLs are permitted; customer-installed CAD,
Python and Visual C++ runtime libraries cannot satisfy bundled dependencies.
"""

import ctypes
import os
import re
import uuid
from ctypes import wintypes
from pathlib import Path


class TrustFile(ctypes.Structure):
    """@brief Declares the Windows WINTRUST_FILE_INFO ABI.
    @details Used only for read-only offline Authenticode verification.
    """

    _fields_ = [
        ("size", wintypes.DWORD),
        ("path", wintypes.LPCWSTR),
        ("file", wintypes.HANDLE),
        ("subject", ctypes.c_void_p),
    ]


class TrustData(ctypes.Structure):
    """@brief Declares the Windows WINTRUST_DATA ABI.
    @details Disables interactive UI and online certificate retrieval.
    """

    _fields_ = [
        ("size", wintypes.DWORD),
        ("policy", ctypes.c_void_p),
        ("sip", ctypes.c_void_p),
        ("ui", wintypes.DWORD),
        ("revocation", wintypes.DWORD),
        ("choice", wintypes.DWORD),
        ("file", ctypes.POINTER(TrustFile)),
        ("action", wintypes.DWORD),
        ("state", wintypes.HANDLE),
        ("url", wintypes.LPCWSTR),
        ("flags", wintypes.DWORD),
        ("context", wintypes.DWORD),
        ("signature", ctypes.c_void_p),
    ]


def signed_file(path: Path) -> bool:
    """@brief Checks a file's Authenticode signature without UI or downloads.
    @param path Exact Windows-registered system-extension binary.
    @return True only when Windows verifies its signature and trust chain.
    @details Does not change certificate, antivirus or Windows settings.
    """
    info = TrustFile(ctypes.sizeof(TrustFile), str(path), None, None)
    data = TrustData()
    data.size = ctypes.sizeof(TrustData)
    data.ui, data.choice, data.flags = 2, 1, 0x1000
    data.file = ctypes.pointer(info)
    action = (ctypes.c_ubyte * 16).from_buffer_copy(
        uuid.UUID("00aac56b-cd44-11d0-8cc2-00c04fc295ee").bytes_le
    )
    trust = ctypes.WinDLL("wintrust", use_last_error=True)
    trust.WinVerifyTrust.argtypes = [
        wintypes.HWND,
        ctypes.c_void_p,
        ctypes.POINTER(TrustData),
    ]
    trust.WinVerifyTrust.restype = ctypes.c_long
    return trust.WinVerifyTrust(None, action, ctypes.byref(data)) == 0


def registered_extensions() -> dict[Path, str]:
    """@brief Identifies signed Windows-registered AMSI provider binaries.
    @return Exact signed provider/helper paths and their classification.
    @details Allows only registered provider DLLs and the signed offreg.dll
    companion in their directory. No CAD, Python or CRT fallback is allowed.
    """
    if os.name != "nt":
        return {}
    import winreg

    result = {}
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            "SOFTWARE/Microsoft/AMSI/Providers".replace("/", "\\"),
        ) as providers:
            for index in range(min(64, winreg.QueryInfoKey(providers)[0])):
                clsid = winreg.EnumKey(providers, index)
                key = "SOFTWARE\\Classes\\CLSID\\" + clsid + "\\InProcServer32"
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as cls:
                        value, _ = winreg.QueryValueEx(cls, "")
                    path = Path(os.path.expandvars(value.strip('"'))).resolve()
                    if not path.is_file() or not signed_file(path):
                        continue
                    result[path] = "REGISTERED_SIGNED_AMSI_PROVIDER"
                    helper = path.parent / "offreg.dll"
                    if helper.is_file() and signed_file(helper):
                        result[helper] = "SIGNED_AMSI_REGISTRY_HELPER"
                except OSError:
                    continue
    except OSError:
        pass
    return result


def loaded_modules() -> tuple[Path, ...]:
    """@brief Enumerates current-process native modules using Windows APIs.
    @return Absolute loaded-module paths.
    @details Reads this process only and rejects incomplete enumeration.
    """
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModules.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HMODULE),
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    psapi.EnumProcessModules.restype = wintypes.BOOL
    psapi.GetModuleFileNameExW.argtypes = [
        wintypes.HANDLE,
        wintypes.HMODULE,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    psapi.GetModuleFileNameExW.restype = wintypes.DWORD
    process = kernel.GetCurrentProcess()
    modules = (wintypes.HMODULE * 4096)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcessModules(
        process, modules, ctypes.sizeof(modules), ctypes.byref(needed)
    ) or needed.value > ctypes.sizeof(modules):
        raise ValueError("BUNDLE_NATIVE_ENUMERATION_FAILED")
    result = []
    for handle in modules[: needed.value // ctypes.sizeof(wintypes.HMODULE)]:
        name = ctypes.create_unicode_buffer(32768)
        length = psapi.GetModuleFileNameExW(process, handle, name, len(name))
        if not length or length >= len(name) - 1:
            raise ValueError("BUNDLE_NATIVE_ENUMERATION_FAILED")
        result.append(Path(name.value).resolve())
    return tuple(sorted(result))


def verify_native_origins(root: Path) -> dict:
    """@brief Rejects native dependency fallback outside the bundled runtime.
    @param root Verified installed plugin root.
    @return Owned-library names and operating-system library count.
    @details Must run after CAD and GUI imports. Visual C++ redistributable
    libraries must be bundled even when also available under Windows.
    """
    root = root.resolve()
    windows = Path(os.environ["SystemRoot"]).resolve()
    owned, system, extensions = [], 0, []
    registered = registered_extensions()
    redistributable = re.compile(
        r"(?:msvcp|vcruntime|vcomp|concrt|vcamp|vccorlib)\d", re.I
    )
    for path in loaded_modules():
        if path.is_relative_to(root):
            owned.append(path.relative_to(root).as_posix())
        elif path.is_relative_to(windows) and not redistributable.match(
            path.name
        ):
            system += 1
        elif path in registered and not redistributable.match(path.name):
            from .bundle import file_identity

            extensions.append(
                {
                    "filename": path.name,
                    "classification": registered[path],
                    **file_identity(path),
                }
            )
        else:
            raise ValueError("BUNDLE_NATIVE_EXTERNAL_LIBRARY")
    return {
        "owned_modules": owned,
        "windows_modules": system,
        "registered_system_extensions": extensions,
    }
