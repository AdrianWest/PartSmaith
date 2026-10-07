"""@file build_pcm.py
@brief Builds a deterministic customer PCM ZIP and local repository fixtures.
@details Does not invoke a PartSmith package build backend or pip installation.
"""

import argparse
import json
import stat
import sys
from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.package import (  # noqa: E402
    IDENTIFIER,
    PCM_ICON,
    VERSION,
    build_pcm,
    json_bytes,
    repository_package,
)


def write_repository_fixture(
    archive: Path, base_url: str, previous_archives: tuple[Path, ...] = ()
) -> None:
    """@brief Writes a schema-tested local configured-repository fixture.
    @param archive Final PCM archive in the fixture directory.
    @param base_url Explicit HTTP base URL serving the fixture directory.
    @param previous_archives Frozen prior archives retained for update tests.
    @return None.
    @details Uses fixed update timestamps, a listing-icon resource ZIP and
    post-archive hash identities. The listing icon loads before installation.
    """
    url = base_url.rstrip("/") + "/"
    package = repository_package(archive, url + archive.name)
    for previous in previous_archives:
        old = repository_package(previous, url + previous.name)
        package["versions"].extend(old["versions"])
    packages = json_bytes({"packages": [package]})
    repository = {
        "$schema": "https://go.kicad.org/pcm/schemas/v2",
        "schema_version": 2,
        "name": "PartSmith owned local acceptance fixture",
        "packages": {
            "url": url + "packages.json",
            "sha256": sha256(packages).hexdigest(),
            "update_timestamp": 1791244800,
            "update_time_utc": "2026-10-06 00:00:00",
        },
    }
    with ZipFile(archive) as source:
        schema = json.loads(
            source.read("plugins/partsmith/pcm/schemas/pcm.v2.schema.json")
        )
        if PCM_ICON in source.namelist():
            resources_path = archive.parent / "resources.zip"
            with ZipFile(
                resources_path, "w", compression=ZIP_STORED
            ) as resources:
                info = ZipInfo(IDENTIFIER + "/icon.png", (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                resources.writestr(info, source.read(PCM_ICON))
            repository["resources"] = {
                "url": url + resources_path.name,
                "sha256": sha256(resources_path.read_bytes()).hexdigest(),
                "update_timestamp": 1791244800,
                "update_time_utc": "2026-10-06 00:00:00",
            }
    for value, definition in (
        (json.loads(packages), "PackageArray"),
        (repository, "Repository"),
    ):
        Draft7Validator(
            {
                "$ref": "#/definitions/" + definition,
                "definitions": schema["definitions"],
            }
        ).validate(value)
    (archive.parent / "packages.json").write_bytes(packages)
    (archive.parent / "repository.json").write_bytes(json_bytes(repository))


def main() -> int:
    """@brief Builds the requested release archive and reviewable metadata.
    @return Zero after all schema and inventory checks pass.
    @details Download metadata is emitted alongside, never inside, the ZIP.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("dist/partsmith-pcm.zip")
    )
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--url")
    parser.add_argument("--repository-url")
    parser.add_argument(
        "--previous-archive", type=Path, action="append", default=[]
    )
    args = parser.parse_args()
    archive = args.output.resolve()
    report = build_pcm(ROOT, archive, args.version)
    url = args.url or archive.as_uri()
    metadata = repository_package(archive, url)
    archive.with_suffix(".package.json").write_bytes(json_bytes(metadata))
    packages = {"packages": [metadata]}
    archive.with_suffix(".packages.json").write_bytes(json_bytes(packages))
    archive.with_suffix(".receipt.json").write_bytes(json_bytes(report))
    if args.repository_url:
        write_repository_fixture(
            archive, args.repository_url, tuple(args.previous_archive)
        )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
