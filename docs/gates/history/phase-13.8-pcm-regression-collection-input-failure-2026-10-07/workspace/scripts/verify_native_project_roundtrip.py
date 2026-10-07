"""@file verify_native_project_roundtrip.py
@brief Verifies native saved designs after relocation.
@details Uses an explicit isolated PCM runtime and actual CLI exports.
No checkout imports, editor writes or publication authority are supplied.
"""

import argparse
import json
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path


def main():
    """@brief Retains relocated native files, exports and exact resource proof.
    @return None.
    @details Requires two symbols and six real model solids in both locations.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = args.payload.resolve()
    assert sys.flags.isolated
    sys.path.insert(0, str(payload))
    import cadquery

    import partsmith
    from partsmith.integration.sexpr import children, parse
    from partsmith.kicad import discover_kicad
    from partsmith.pcm.runtime import readiness

    assert Path(partsmith.__file__).resolve().is_relative_to(payload)
    runtime = readiness(payload)
    assert runtime["state"] == "READY"
    args.output.mkdir()
    relocated = args.output / "relocated"
    relocated.mkdir()
    identities = {}
    for source in args.project.rglob("*"):
        relative = source.relative_to(args.project)
        if (
            not source.is_file()
            or source.suffix == ".lck"
            or any(p.endswith("-backups") for p in relative.parts)
        ):
            continue
        destination = relocated / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        identities[relative.as_posix()] = sha256(
            source.read_bytes()
        ).hexdigest()
        assert (
            sha256(destination.read_bytes()).hexdigest()
            == (identities[relative.as_posix()])
        )
    library = parse((relocated / "BFT_Symbols.kicad_sym").read_bytes())
    symbols = children(library, "symbol")
    assert len(symbols) == 2
    schematic = parse((relocated / "acceptance.kicad_sch").read_bytes())
    assert str(children(schematic, "version")[0][1]) == "20260306"
    cache = children(children(schematic, "lib_symbols")[0], "symbol")
    assert len(cache) == 2 and len(children(schematic, "symbol")) == 2

    def pins(tree):
        """@brief Reads exact native pin names and numbers recursively.
        @param tree Native library or cached symbol subtree.
        @return Sorted pin name and number tuples.
        @details This check complements full staging and IPC geometry checks.
        """
        result = []
        for node in tree:
            if not isinstance(node, list):
                continue
            if node[0] == "pin":
                result.append(
                    (
                        children(node, "name")[0][1],
                        children(node, "number")[0][1],
                    )
                )
            else:
                result.extend(pins(node))
        return sorted(result)

    for symbol in symbols:
        cached = next(s for s in cache if s[1].split(":")[1] == symbol[1])
        assert pins(cached) == pins(symbol)
    observed_pins = {s[1]: pins(s) for s in cache}
    assert (
        sum(
            name == "Revised_terminal"
            for records in observed_pins.values()
            for name, _ in records
        )
        == 1
    )
    executable = discover_kicad().executable
    commands = []
    for label, project in (("saved", args.project), ("relocated", relocated)):
        for operation, options in (
            ("schematic-svg", ["sch", "export", "svg"]),
            ("board-step", ["pcb", "export", "step", "--no-board-body"]),
        ):
            output = args.output / (label + "-" + operation)
            design = project / (
                "acceptance.kicad_sch"
                if operation == "schematic-svg"
                else "acceptance.kicad_pcb"
            )
            command = [
                str(executable),
                *options,
                "--output",
                str(output),
                str(design),
            ]
            result = subprocess.run(
                command,
                cwd=project,
                capture_output=True,
                timeout=120,
                check=True,
            )
            for name in ("stdout", "stderr"):
                (
                    args.output / (label + "-" + operation + "." + name)
                ).write_bytes(getattr(result, name))
            receipt = {"command": command, "exit_code": result.returncode}
            if operation == "board-step":
                shape = cadquery.importers.importStep(str(output)).val()
                assert len(shape.Solids()) == 6
                assert abs(shape.Volume() - 0.39) < 0.00001
                receipt.update(solids=6, volume_mm3=shape.Volume())
            else:
                assert list(output.glob("*.svg"))
            commands.append(receipt)
    (args.output / "receipt.json").write_text(
        json.dumps(
            {
                "schema_version": "partsmith-native-roundtrip-evidence-1.0",
                "status": "PASS",
                "prepared_runtime": runtime,
                "isolated_pcm_import": True,
                "pin_records": observed_pins,
                "files": identities,
                "commands": commands,
                "desktop_claim": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("PASS: saved and relocated native symbols and six STEP solids")


if __name__ == "__main__":
    main()
