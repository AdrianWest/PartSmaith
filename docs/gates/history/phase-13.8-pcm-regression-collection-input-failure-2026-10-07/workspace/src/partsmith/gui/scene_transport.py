"""@package partsmith.gui.scene_transport
@brief Publishes private viewer messages atomically across native processes.
@details Bounded retries tolerate brief Windows reader sharing locks.
"""

import time
from pathlib import Path


def read_message(path: Path) -> str | None:
    """@brief Reads one bounded message when the publisher has released it.
    @param path Private request or acknowledgement file.
    @return UTF-8 message, or None during absence or a transient sharing lock.
    @details Reads at most 65537 bytes and rejects oversized transport. The
    caller's supervised polling loop handles retry and operation deadlines.
    """
    try:
        with path.open("rb") as stream:
            content = stream.read(65537)
    except (FileNotFoundError, PermissionError):
        return None
    if len(content) > 65536:
        raise ValueError("VIEWER_TRANSPORT_LIMIT: message too large")
    return content.decode("utf-8")


def publish_text(path: Path, content: str) -> None:
    """@brief Atomically replaces a small private transport message.
    @param path Controller-owned destination file.
    @param content Complete UTF-8 message to publish.
    @return None.
    @details Retries transient PermissionError for at most one second because
    Windows readers can briefly prevent replacement of an existing file.
    All waits run outside the GUI thread; other I/O failures propagate.
    """
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    deadline = time.monotonic() + 1
    while True:
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.001)
