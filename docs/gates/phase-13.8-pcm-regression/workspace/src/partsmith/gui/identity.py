"""@package partsmith.gui.identity
@brief Resolves review authority from the current operating-system session.
@details Display names, loaded audit actors and provider text never
authenticate
a reviewer; an unavailable identity blocks decisions but allows inspection.
"""

import os

from partsmith.release.contracts import AuthenticatedPrincipal


def authenticated_principal():
    """@brief Resolves the current authenticated OS principal.
    @return AuthenticatedPrincipal bound to the current process token.
    @details Windows uses the token's SID through Win32 APIs; POSIX uses UID.
    """
    if os.name != "nt":
        return AuthenticatedPrincipal(
            f"uid:{os.getuid()}", "posix-process-uid"
        )
    import ctypes
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    ]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(
        wintypes.HANDLE(-1), 8, ctypes.byref(token)
    ):
        raise PermissionError("Current OS review identity is unavailable")
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(
            token, 1, buffer, size, ctypes.byref(size)
        ):
            raise PermissionError("Current OS token identity is unavailable")
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise PermissionError("Current OS SID is unavailable")
        try:
            return AuthenticatedPrincipal(
                text.value, "windows-process-token-sid"
            )
        finally:
            kernel.LocalFree(ctypes.cast(text, ctypes.c_void_p))
    finally:
        kernel.CloseHandle(token)
