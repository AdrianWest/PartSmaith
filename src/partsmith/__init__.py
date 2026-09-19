"""PartSmith, the Board Forge Tools deterministic component builder."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("partsmith")
except PackageNotFoundError:
    # Supports source-tree execution before the project is installed.
    __version__ = "0.1.0"


__all__ = ["__version__"]
