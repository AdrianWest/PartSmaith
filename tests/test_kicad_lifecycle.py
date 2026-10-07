"""@file test_kicad_lifecycle.py
@brief Checks host identity and retained native process handles.
@details Covers launch wrappers, process exit and unrelated KiCad instances.
"""

import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from partsmith.integration.host import (
    HostLifetime,
    WindowsHostApi,
    find_host_pid,
)


@pytest.mark.parametrize("name", ["kicad.exe", "pcbnew.exe"])
def test_host_ancestry_skips_python_wrappers(name):
    """@brief Resolves the nearest host through isolated Python wrappers.
    @param name Supported KiCad executable basename.
    @return None.
    @details A separate running KiCad instance cannot become the launch host.
    """
    processes = {
        10: (20, "python.exe"),
        20: (30, "pythonw.exe"),
        30: (40, "pythonw.exe"),
        40: (1, name),
        50: (1, "kicad.exe"),
    }
    assert find_host_pid(processes, 10) == 40
    assert find_host_pid(processes, 99) is None


def test_ancestry_rejects_cycles_and_unrelated_kicad():
    """@brief Rejects cyclic ancestry and another unrelated KiCad process.
    @return None.
    @details Lookup never searches globally for a convenient running host.
    """
    assert (
        find_host_pid({1: (2, "python.exe"), 2: (1, "pythonw.exe")}, 1) is None
    )
    assert (
        find_host_pid({1: (0, "python.exe"), 2: (0, "kicad.exe")}, 1) is None
    )


def test_lifetime_detects_original_host_loss():
    """@brief Invalidates lifetime when the original host process exits.
    @return None.
    @details Closing is idempotent and never reopens a recycled process PID.
    """
    state = {"wait": 258}
    closed = []
    api = SimpleNamespace(
        kernel=SimpleNamespace(
            OpenProcess=lambda access, inherit, pid: 101,
            WaitForSingleObject=lambda handle, timeout: state["wait"],
            CloseHandle=closed.append,
        ),
    )
    lifetime = HostLifetime(api, 40)
    assert lifetime.is_alive()
    state["wait"] = 0
    assert not lifetime.is_alive()
    lifetime.close()
    lifetime.close()
    assert closed == [101]
    assert not lifetime.is_alive()


@pytest.mark.skipif(os.name != "nt", reason="Windows native process handles")
def test_native_process_handle_survives_only_until_exit():
    """@brief Verifies real Windows snapshot and synchronization behavior.
    @return None.
    @details An owned child exits normally; the retained handle signals exit.
    """
    api = WindowsHostApi()
    assert os.getpid() in api.processes()
    child = subprocess.Popen(
        [sys.executable, "-I", "-c", "import sys; sys.stdin.read()"],
        stdin=subprocess.PIPE,
    )
    lifetime = HostLifetime(api, child.pid)
    try:
        assert lifetime.is_alive()
        child.stdin.close()
        child.wait(timeout=10)
        assert not lifetime.is_alive()
    finally:
        lifetime.close()
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
