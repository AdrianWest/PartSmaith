"""@file curate_production_lock.py
@brief Records reviewed local producer artifacts and exact runtime members.
@details This maintainer command creates a draft lock. Release evidence must
still validate the native closure, license notices and installed runtime.
"""

import argparse
import json
import shutil
import sys
from email.parser import BytesParser
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partsmith.pcm.bundle import file_identity  # noqa: E402
from partsmith.pcm.package import json_bytes  # noqa: E402


def wheel_target(member: str) -> str:
    """@brief Maps wheel purelib and platlib data into isolated site-packages.
    @param member Original wheel member path.
    @return Portable installed runtime path.
    @details Other wheel data remains under its declared data directory.
    """
    parts = member.split("/")
    if parts[0].endswith(".data") and parts[1] in {"purelib", "platlib"}:
        member = "/".join(parts[2:])
    return "runtime/Lib/site-packages/" + member


def main() -> int:
    """@brief Freezes upstream identities and retained license texts.
    @return Zero after writing a draft lock with complete file ownership.
    @details Requires provisioned pinned wheels and the Conda producer cache;
    resolves wheel download identities through the official PyPI JSON API.
    Reuses raw notices only when an existing reviewed lock binds exact bytes.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheels", type=Path, required=True)
    parser.add_argument("--ocr", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifacts, files, components = {}, {}, []
    reviewed_artifacts = (
        json.loads(args.output.read_bytes())["artifacts"]
        if args.output.is_file()
        else {}
    )

    def artifact(path: Path, url: str, kind: str) -> str:
        """@brief Retains one immutable producer archive identity.
        @param path Available reviewed archive.
        @param url Official source URL for clean producer reconstruction.
        @param kind Wheel, zip, conda or raw extraction strategy.
        @return Artifact basename used in file mappings.
        @details Copies only when the destination differs from the input.
        """
        name = path.name
        artifacts[name] = file_identity(path) | {"url": url, "kind": kind}
        target = args.cache / name
        if path.resolve() != target.resolve():
            shutil.copyfile(path, target)
        return name

    def member(aid: str, origin: str, target: str, blob: bytes) -> None:
        """@brief Adds one original member and its intended installed path.
        @param aid Retained artifact identifier.
        @param origin Member path inside the original artifact.
        @param target Portable isolated runtime destination.
        @param blob Exact upstream bytes.
        @return None.
        @details Identical namespace members may share ownership; changed
        collisions fail instead of silently replacing installed bytes.
        """
        if target in files:
            if files[target]["sha256"] == sha256(blob).hexdigest():
                return
            raise ValueError("Duplicate installed runtime path: " + target)
        files[target] = {
            "artifact": aid,
            "member": origin,
            "sha256": sha256(blob).hexdigest(),
            "size": len(blob),
        }

    def component(
        name: str,
        ver: str,
        aid: str,
        license_name: str,
        owned: list[str],
        licenses: list[str],
    ) -> None:
        """@brief Records a dependency and its retained notices.
        @param name Component name.
        @param ver Exact upstream version.
        @param aid Retained archive identity.
        @param license_name Upstream license expression or declaration.
        @param owned Installed files owned by this component.
        @param licenses Retained upstream license and notice paths.
        @return None.
        @details Every component must have nonempty license text coverage.
        """
        if not licenses or not license_name:
            raise ValueError("Missing license: " + name)
        components.append(
            {
                "name": name,
                "version": ver,
                "source": artifacts[aid]["url"],
                "sha256": artifacts[aid]["sha256"],
                "license": str(license_name),
                "platform": "Windows",
                "architecture": "AMD64",
                "files": sorted(set(owned) | set(licenses)),
                "license_files": {
                    n: {k: files[n][k] for k in ("sha256", "size")}
                    for n in sorted(licenses)
                },
            }
        )

    args.cache.mkdir(parents=True, exist_ok=True)
    python = args.cache / "python-3.12.10-embed-amd64.zip"
    aid = artifact(
        python,
        "https://www.python.org/ftp/python/3.12.10/" + python.name,
        "zip",
    )
    with ZipFile(python) as archive:
        owned = []
        for n in archive.namelist():
            if n.endswith("/"):
                continue
            target = "runtime/" + n
            member(aid, n, target, archive.read(n))
            owned.append(target)
    component(
        "CPython", "3.12.10", aid, "PSF-2.0", owned, ["runtime/LICENSE.txt"]
    )
    distlib = args.cache / "distlib-0.4.0-py2.py3-none-any.whl"
    with urlopen("https://pypi.org/pypi/distlib/0.4.0/json", timeout=60) as r:
        url = next(
            f["url"]
            for f in json.load(r)["urls"]
            if f["filename"] == distlib.name
        )
    aid = artifact(distlib, url, "wheel")
    with ZipFile(distlib) as archive:
        owned = []
        for n, target in {
            "distlib/t64.exe": "launchers/t64.exe",
            "distlib/w64.exe": "launchers/w64.exe",
            "distlib-0.4.0.dist-info/LICENSE.txt": (
                "licenses/distlib/LICENSE.txt"
            ),
        }.items():
            member(aid, n, target, archive.read(n))
            owned.append(target)
    component(
        "distlib-launcher",
        "0.4.0",
        aid,
        "PSF-2.0",
        owned,
        ["licenses/distlib/LICENSE.txt"],
    )
    proxy = None
    for path in sorted(args.wheels.glob("*.whl")):
        if path.name.startswith(("pip-", "distlib-")):
            continue
        with ZipFile(path) as archive:
            meta = BytesParser().parsebytes(
                archive.read(
                    next(
                        n
                        for n in archive.namelist()
                        if n.endswith(".dist-info/METADATA")
                    )
                )
            )
            name, ver = meta["Name"], meta["Version"]
            with urlopen(
                f"https://pypi.org/pypi/{name}/{ver}/json", timeout=60
            ) as r:
                upstream = next(
                    f
                    for f in json.load(r)["urls"]
                    if f["filename"] == path.name
                )
            if file_identity(path)["sha256"] != upstream["digests"]["sha256"]:
                raise ValueError("Wheel differs from PyPI identity: " + name)
            aid = artifact(path, upstream["url"], "wheel")
            owned, licenses = [], []
            for n in archive.namelist():
                if n.endswith("/") or n.endswith((".pyc", ".pyo")):
                    continue
                target = wheel_target(n)
                member(aid, n, target, archive.read(n))
                owned.append(target)
                lowered = n.lower()
                if any(s in lowered for s in ("license", "copying", "notice")):
                    licenses.append(target)
            license_name = meta["License-Expression"] or meta["License"]
            if not license_name:
                license_name = next(
                    (
                        c.rsplit(" :: ", 1)[-1]
                        for c in meta.get_all("Classifier", [])
                        if c.startswith("License ::")
                    ),
                    None,
                )
            if name == "cadquery-ocp-proxy":
                proxy = (name, ver, aid, license_name, owned)
            else:
                component(name, ver, aid, license_name, owned, licenses)
        print("Pinned", name, ver, flush=True)
    if proxy:
        component(*proxy, ["runtime/Lib/site-packages/cadquery_ocp/LICENSE"])
    for path in sorted((args.ocr / "conda-meta").glob("*.json")):
        record = json.loads(path.read_bytes())
        base = Path(record["link"]["source"])
        about = json.loads((base / "info/about.json").read_bytes())
        owned = []
        retained = []
        for n in record["files"]:
            if n.startswith("Library/bin/") and n.endswith((".dll", ".exe")):
                retained.append(
                    (n, "ocr/bin/" + n.removeprefix("Library/bin/"))
                )
            data_path = n.removeprefix("Library/")
            if data_path.startswith("share/tessdata/"):
                leaf = data_path.removeprefix("share/tessdata/")
                if leaf in {
                    "eng.traineddata",
                    "deu.traineddata",
                    "chi_sim.traineddata",
                    "configs/tsv",
                }:
                    retained.append((n, "ocr/tessdata/" + leaf))
        # Empty dependency metapackages contribute no shipped runtime bytes.
        if not retained:
            continue
        source = base.parent / (base.name + ".conda")
        aid = artifact(source, record["url"], "conda")
        if artifacts[aid]["sha256"] != record["sha256"]:
            raise ValueError("Conda source hash drift")
        licenses = []
        for license_path in sorted((base / "info/licenses").rglob("*")):
            if license_path.is_file():
                n = license_path.relative_to(base).as_posix()
                target = (
                    "licenses/ocr/"
                    + record["name"]
                    + "/"
                    + n.removeprefix("info/licenses/")
                )
                retained.append((n, target))
                licenses.append(target)
        for n, target in retained:
            member(aid, n, target, (base / n).read_bytes())
            owned.append(target)
        component(
            "ocr-" + record["name"],
            record["version"],
            aid,
            about["license"],
            owned,
            licenses,
        )
    for name, ver, license_name, url in (
        (
            "OCCT",
            "7.9.3",
            "LGPL-2.1-only WITH OCCT-exception-1.0",
            "https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_9_3/LICENSE_LGPL_21.txt",
        ),
        (
            "OCCT-exception",
            "7.9.3",
            "OCCT-exception-1.0",
            "https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/V7_9_3/OCCT_LGPL_EXCEPTION.txt",
        ),
        (
            "CasADi-license",
            "3.8.1",
            "LGPL-3.0-or-later",
            "https://raw.githubusercontent.com/casadi/casadi/3.8.1/LICENSE.txt",
        ),
        (
            "GPL-license",
            "3.0",
            "GPL-3.0-only",
            "https://www.gnu.org/licenses/gpl-3.0.txt",
        ),
    ):
        local = args.cache / (name + "-" + ver + ".txt")
        reviewed = reviewed_artifacts.get(local.name, {})
        if not (
            local.is_file()
            and reviewed.get("url") == url
            and file_identity(local)
            == {k: reviewed.get(k) for k in ("sha256", "size")}
        ):
            with urlopen(url, timeout=60) as response:
                local.write_bytes(response.read())
        aid = artifact(local, url, "raw")
        target = "licenses/" + local.name
        member(aid, ".", target, local.read_bytes())
        component(name, ver, aid, license_name, [target], [target])
    # The binding's Apache notice does not replace the OCCT engine license.
    # CasADi's wheel retains solver notices but omits its own LGPL text.
    for item in components:
        normalized = item["name"].lower().replace("_", "-")
        extra = []
        if normalized == "cadquery-ocp":
            extra = [
                "licenses/OCCT-7.9.3.txt",
                "licenses/OCCT-exception-7.9.3.txt",
            ]
        elif normalized == "casadi":
            extra = [
                "licenses/CasADi-license-3.8.1.txt",
                "licenses/GPL-license-3.0.txt",
            ]
        for target in extra:
            item["files"].append(target)
            item["license_files"][target] = {
                k: files[target][k] for k in ("sha256", "size")
            }
        item["files"] = sorted(set(item["files"]))
    lock = {
        "schema_version": "partsmith-production-lock-1.0",
        "platform": "Windows",
        "architecture": "AMD64",
        "python_version": "3.12.10",
        "artifacts": artifacts,
        "components": sorted(components, key=lambda c: c["name"].lower()),
        "files": dict(sorted(files.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json_bytes(lock))
    print("Recorded", len(files), "files and", len(components), "components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
