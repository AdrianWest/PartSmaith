"""@package partsmith.path_support
@brief Identifies Windows directory junctions on supported Python versions.
@details Uses lstat reparse tags without following a junction's destination.
"""

import stat
from pathlib import Path


def is_junction(path: Path) -> bool:
    """@brief Checks whether a path is a Windows mount-point reparse entry.
    @param path Filesystem entry to inspect without following redirection.
    @return True for directory junctions or volume mount points.
    @details Works on Python 3.11 and 3.12; absent paths return False.
    Permission and other filesystem errors remain visible to the caller.
    """
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return getattr(info, "st_reparse_tag", None) == getattr(
        stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003
    )
