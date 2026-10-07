"""@package partsmith.pcm.supply
@brief Reconstructs a locked runtime from reviewed upstream artifacts.
@details Build-time downloads are optional. Customer installation never calls
pip, Conda, a compiler, a resolver or a network service.
"""

from __future__ import annotations

import json
import tarfile
from contextlib import contextmanager
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from .bundle import PackagingPolicy, file_identity
from .package import _safe_name, _unique_names


@contextmanager
def _conda_stream(archive: ZipFile, kind: str):
    """@brief Opens one bounded Conda archive stream for producer extraction.
    @param archive Validated outer package container.
    @param kind Either pkg or info stream.
    @return Context manager yielding a streaming tar reader.
    @details zstandard is a build dependency only and is never packaged.
    """
    import zstandard

    names = [n for n in archive.namelist() if n.startswith(kind + "-")]
    if len(names) != 1 or not names[0].endswith(".tar.zst"):
        raise ValueError("BUNDLE_CONDA_STREAM_INVALID")
    with archive.open(names[0]) as compressed:
        with zstandard.ZstdDecompressor().stream_reader(compressed) as stream:
            with tarfile.open(fileobj=stream, mode="r|") as source:
                yield source


def _write_member(stream, target: Path, expected: dict) -> None:
    """@brief Writes one locked source member with bounded memory.
    @param stream Open upstream member byte stream.
    @param target Confined producer output file.
    @param expected Reviewed SHA-256 and size mapping.
    @return None.
    @details Oversized, missing or changed source bytes fail the build.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    remaining = expected["size"]
    with target.open("wb") as output:
        while remaining:
            block = stream.read(min(remaining, 1024 * 1024))
            if not block:
                raise ValueError("BUNDLE_INPUT_TRUNCATED")
            output.write(block)
            remaining -= len(block)
        if stream.read(1):
            raise ValueError("BUNDLE_INPUT_OVERSIZED")
    if file_identity(target) != expected:
        raise ValueError("BUNDLE_INPUT_MEMBER_CHANGED")


def prepare_supply(lock_path: Path, cache: Path, output: Path) -> dict:
    """@brief Fetches exact pinned upstream bytes and assembles a runtime.
    @param lock_path Reviewed production lock, including member identities.
    @param cache Local upstream artifact cache, optionally preprovisioned.
    @param output New empty producer directory.
    @return Loaded lock document for the deterministic PCM builder.
    @details Rejects existing outputs and unsafe mappings before extraction;
    artifacts are hashed before use and downloads have a sixty-second timeout.
    """
    lock = json.loads(lock_path.read_bytes())
    if lock["schema_version"] != "partsmith-production-lock-1.0":
        raise ValueError("BUNDLE_LOCK_VERSION")
    if output.exists():
        raise ValueError("BUNDLE_OUTPUT_MUST_BE_NEW")
    _unique_names(list(lock["files"]))
    PackagingPolicy().require_sizes(
        [item["size"] for item in lock["files"].values()]
    )
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True)
    for artifact_id, artifact in lock["artifacts"].items():
        _safe_name(artifact_id)
        if "/" in artifact_id or not artifact["url"].startswith("https://"):
            raise ValueError("BUNDLE_ARTIFACT_IDENTITY")
        path = cache / artifact_id
        if not path.exists():
            partial = path.with_suffix(path.suffix + ".partial")
            with urlopen(artifact["url"], timeout=60) as source:
                with partial.open("wb") as destination:
                    remaining = artifact["size"]
                    while remaining:
                        block = source.read(min(remaining, 1024 * 1024))
                        if not block:
                            raise ValueError("BUNDLE_ARTIFACT_TRUNCATED")
                        destination.write(block)
                        remaining -= len(block)
                    if source.read(1):
                        raise ValueError("BUNDLE_ARTIFACT_OVERSIZED")
            partial.replace(path)
        if file_identity(path) != {
            "sha256": artifact["sha256"],
            "size": artifact["size"],
        }:
            raise ValueError("BUNDLE_ARTIFACT_CHANGED: " + artifact_id)
        selected = {
            record["member"]: (name, record)
            for name, record in lock["files"].items()
            if record["artifact"] == artifact_id
        }
        if len(selected) != sum(
            r["artifact"] == artifact_id for r in lock["files"].values()
        ):
            raise ValueError("BUNDLE_DUPLICATE_INPUT_MEMBER")
        if artifact["kind"] == "raw":
            if set(selected) != {"."}:
                raise ValueError("BUNDLE_RAW_MAPPING")
            name, record = selected["."]
            with path.open("rb") as source:
                _write_member(
                    source,
                    output / name,
                    {k: record[k] for k in ("sha256", "size")},
                )
        elif artifact["kind"] in {"wheel", "zip"}:
            with ZipFile(path) as archive:
                _unique_names(
                    [n for n in archive.namelist() if not n.endswith("/")]
                )
                for member, (name, record) in selected.items():
                    with archive.open(member) as source:
                        _write_member(
                            source,
                            output / name,
                            {k: record[k] for k in ("sha256", "size")},
                        )
        elif artifact["kind"] == "conda":
            found = set()
            with ZipFile(path) as archive:
                for kind in ("pkg", "info"):
                    with _conda_stream(archive, kind) as members:
                        for member in members:
                            if member.name not in selected:
                                continue
                            if not member.isfile():
                                raise ValueError("BUNDLE_CONDA_LINK")
                            name, record = selected[member.name]
                            with members.extractfile(member) as source:
                                _write_member(
                                    source,
                                    output / name,
                                    {k: record[k] for k in ("sha256", "size")},
                                )
                            found.add(member.name)
            if found != set(selected):
                raise ValueError("BUNDLE_CONDA_MEMBER_MISSING")
        else:
            raise ValueError("BUNDLE_ARTIFACT_KIND")
    return lock
