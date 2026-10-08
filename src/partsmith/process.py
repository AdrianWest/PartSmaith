"""@package partsmith.process
@brief Supervises bounded native processes with incremental redacted logs.
@details Pipe readers run outside the wx thread; failure preserves prior
stdout/stderr and exit status, and cancellation reaps owned child trees.
"""

import os
import signal
import subprocess
import time
from queue import Empty, Queue
from threading import Thread


def _owned_job(process):
    """@brief Assigns Windows children to an exclusively owned kill-on-close
    job.
    @param process Newly launched subprocess with no user-owned descendants.
    @return None.
    @details Closing the job reaps descendants even after the parent crashes.
    """
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        """@brief Matches the Win32 basic job limits ABI.
        @details Pointer-sized fields use the host process pointer width.
        """

        _fields_ = [
            ("process_time", ctypes.c_longlong),
            ("job_time", ctypes.c_longlong),
            ("flags", wintypes.DWORD),
            ("minimum_ws", ctypes.c_size_t),
            ("maximum_ws", ctypes.c_size_t),
            ("active", wintypes.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority", wintypes.DWORD),
            ("scheduling", wintypes.DWORD),
        ]

    class ExtendedLimits(ctypes.Structure):
        """@brief Matches the Win32 extended job limits ABI.
        @details Retains the documented IO and memory-limit field layout.
        """

        _fields_ = [
            ("basic", BasicLimits),
            ("io", ctypes.c_ulonglong * 6),
            ("process_memory", ctypes.c_size_t),
            ("job_memory", ctypes.c_size_t),
            ("peak_process", ctypes.c_size_t),
            ("peak_job", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.AssignProcessToJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
    ]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    job = kernel.CreateJobObjectW(None, None)
    limits = ExtendedLimits()
    limits.basic.flags = 0x2000
    if (
        not job
        or not kernel.SetInformationJobObject(
            job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        )
        or not kernel.AssignProcessToJobObject(
            job, wintypes.HANDLE(int(process._handle))
        )
    ):
        if job:
            kernel.CloseHandle(job)
        process.kill()
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
        raise OSError("Could not contain the native worker process tree")
    process._partsmith_job = (kernel, job)


def stop_process(process):
    """@brief Stops and reaps an exclusively owned native process tree.
    @param process Live subprocess handle owned by this operation.
    @return None.
    @details Uses hidden taskkill on Windows and a process group on POSIX.
    """
    job = getattr(process, "_partsmith_job", None)
    if job:
        job[0].CloseHandle(job[1])
        process._partsmith_job = None
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
        if process.poll() is None:
            process.kill()
    process.wait(timeout=5)


def run_process(
    command,
    *,
    log,
    cancel=None,
    timeout=120,
    cwd=None,
    env=None,
    on_line=None,
    on_start=None,
    output_budget=2 * 1024 * 1024,
    on_poll=None,
    poll_interval=0.02,
):
    """@brief Streams native output while enforcing time and byte budgets.
    @param command Explicit argv list without shell interpolation.
    @param log Redacting progress sink accepting origin-labeled messages.
    @param cancel Optional cooperative cancellation event.
    @param timeout Maximum process lifetime in seconds, or None for a stream.
    @param cwd Optional native working directory.
    @param env Explicit inherited environment with credentials removed.
    @param on_line Optional structured-output callback before log forwarding.
    @param on_start Optional trusted ownership callback for the child handle.
    @param output_budget Aggregate pipe transport byte limit.
    @param on_poll Optional trusted callback supervising ongoing operations.
    @param poll_interval Maximum seconds between supervision callbacks.
    @return CompletedProcess with captured stdout/stderr and actual exit code.
    @details Partial final lines are preserved before errors; no raw output is
    persisted by this supervisor. Owned pipes and reader threads always close.
    Streaming callers enforce operation deadlines through on_poll.
    """
    if cancel is not None and cancel.is_set():
        raise InterruptedError("Native operation cancelled before launch")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        start_new_session=os.name != "nt",
    )
    _owned_job(process)
    if on_start is not None:
        try:
            on_start(process)
        except Exception:
            stop_process(process)
            raise
    events = Queue(maxsize=256)
    stopped = False
    threads = []

    def read(stream, origin):
        """@brief Reads one bounded pipe without blocking the GUI thread.
        @param stream Owned binary stdout or stderr pipe.
        @param origin Stable stream name.
        @return None.
        @details Incremental complete lines prevent split credential leakage.
        """
        try:
            while True:
                line = stream.readline(65537)
                if not line:
                    break
                events.put((origin, line))
        finally:
            stream.close()
            events.put((origin, None))

    for origin, stream in (
        ("stdout", process.stdout),
        ("stderr", process.stderr),
    ):
        thread = Thread(
            target=read, args=(stream, origin), name="PartSmith " + origin
        )
        thread.start()
        threads.append(thread)
    output = {"stdout": [], "stderr": []}
    closed, total = set(), 0
    started = time.monotonic()
    failure = None
    capture_stopped = False
    try:
        while len(closed) < 2:
            if on_poll is not None and not stopped and process.poll() is None:
                on_poll(process)
            if (
                not stopped
                and process.poll() is None
                and (
                    (cancel is not None and cancel.is_set())
                    or (
                        timeout is not None
                        and time.monotonic() - started > timeout
                    )
                )
            ):
                failure = (
                    InterruptedError("Native operation cancelled")
                    if cancel and cancel.is_set()
                    else TimeoutError("Native operation exceeded timeout")
                )
                stop_process(process)
                stopped = True
            try:
                origin, data = events.get(timeout=poll_interval)
            except Empty:
                continue
            if data is None:
                closed.add(origin)
                continue
            total += len(data)
            if len(data) > 65536 or total > output_budget:
                capture_stopped = True
                if not stopped:
                    log("[process] OUTPUT_BUDGET: output capture stopped")
                    stop_process(process)
                    stopped = True
                    failure = ValueError(
                        "Native output exceeds configured transport budget"
                    )
                continue
            text = data.decode("utf-8", errors="replace").rstrip("\r\n")
            if capture_stopped:
                continue
            output[origin].append(text)
            try:
                handled = (
                    on_line(origin, text) if on_line is not None else False
                )
            except Exception as error:
                failure = error
                handled = False
                stop_process(process)
                stopped = True
            if not handled:
                log(f"[{origin}] {text}")
        process.wait(timeout=5)
        log(f"[process] Exit status: {process.returncode}")
        if failure:
            raise failure
        return subprocess.CompletedProcess(
            command,
            process.returncode,
            "\n".join(output["stdout"]),
            "\n".join(output["stderr"]),
        )
    finally:
        stop_process(process)
        # Drain queued events before joining blocked pipe producers.
        while any(thread.is_alive() for thread in threads):
            try:
                events.get(timeout=0.05)
            except Empty:
                pass
        for thread in threads:
            thread.join(timeout=5)
