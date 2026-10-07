"""@file verify_atomic_target.py
@brief Records a real local NTFS junction feasibility and native KiCad probe.
@details Creates exclusively disposable complete project generations. Results
cover one-root selection, bounded anchored readers, sharing, cancellation,
reverse selection and KiCad CLI library/model resolution. Production journals,
power-loss recovery and editor cache refresh remain separate gate obligations.
"""

import argparse
import json
import platform
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier

from partsmith.integration.atomic_target import AtomicTargetProbe

ROOT = Path(__file__).resolve().parents[1]
CLI = Path("C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")


def generation(name: str) -> dict[str, bytes]:
    """@brief Builds complete disposable native library/table/project fixtures.
    @param name Old or new generation label.
    @return Relative files mapped to exact generation bytes.
    @details STEP bytes remain exact; references resolve through KIPRJMOD
    within the selected root, including both project-local library tables.
    """
    entry = "Probe" + name.title()
    symbol = (ROOT / "fixtures/symbol/expected/0402.kicad_sym").read_text()
    symbol = symbol.replace("TEST-R-0402", entry)
    footprint = (
        ROOT / "fixtures/footprint/expected/0402.kicad_mod"
    ).read_text()
    footprint = footprint.replace("TEST-R-0402", entry)
    footprint = footprint.replace(
        f'(footprint "{entry}"', f'(footprint "{entry}"\n  (attr smd)', 1
    )
    model = """  (model "${KIPRJMOD}/Models/0402.step"
    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
"""
    footprint = footprint.rstrip()[:-1] + model + ")\n"
    embedded = footprint.replace(
        f'(footprint "{entry}"', f'(footprint "Probe:{entry}"', 1
    )
    embedded = embedded.replace("  (version 20240108)\n", "")
    embedded = embedded.replace("  (generator partsmith)\n", "")
    embedded = embedded.replace('"R?"', '"R1"')
    opening, rest = embedded.split("\n", 1)
    embedded = opening + '\n  (layer "F.Cu") (at 100 100)\n' + rest
    board = (
        """(kicad_pcb (version 20250114) (generator "pcbnew")
  (general (thickness 1.6)) (paper "A4")
  (layers (0 "F.Cu" signal) (31 "B.Cu" signal)
    (35 "F.Paste" user) (37 "F.SilkS" user) (39 "F.Mask" user)
    (44 "Edge.Cuts" user) (47 "F.CrtYd" user) (49 "F.Fab" user))
  (setup (pad_to_mask_clearance 0)) (net 0 "")
  (gr_rect (start 95 95) (end 105 105)
    (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts"))
"""
        + embedded
        + ")\n"
    )
    symbol_table = """(sym_lib_table (version 7)
  (lib (name "Probe") (type "KiCad")
    (uri "${KIPRJMOD}/Symbols.kicad_sym") (options "") (descr "Owned probe")))
"""
    footprint_table = """(fp_lib_table (version 7)
  (lib (name "Probe") (type "KiCad")
    (uri "${KIPRJMOD}/Footprints.pretty") (options "") (descr "Owned probe")))
"""
    symbol_table = symbol_table.replace("Owned probe", f"Owned probe {name}")
    footprint_table = footprint_table.replace(
        "Owned probe", f"Owned probe {name}"
    )
    return {
        "Symbols.kicad_sym": symbol.encode(),
        f"Footprints.pretty/{entry}.kicad_mod": footprint.encode(),
        "Models/0402.step": (
            ROOT / "fixtures/threed/expected/0402.step"
        ).read_bytes(),
        "sym-lib-table": symbol_table.encode(),
        "fp-lib-table": footprint_table.encode(),
        "probe.kicad_pcb": board.encode(),
        "probe.kicad_pro": b"{}\n",
        "probe.kicad_prl": (
            ROOT / "docs/gates/phase-13.2-atomic-default-project-local.json"
        ).read_bytes(),
    }


def native_checks(probe: AtomicTargetProbe, name: str, output: Path) -> dict:
    """@brief Runs real KiCad CLI library, table and model-resolution probes.
    @param probe Disposable target currently selecting the named generation.
    @param name Expected old or new generation label.
    @param output Fresh owned output directory outside immutable generations.
    @return Native command receipts and output artifact hashes.
    @details Fixed argument vectors have bounded deadlines and no shell; SVG
    names prove library selection and PCB exports resolve the exact model path.
    """
    output.mkdir()
    for directory in ("symbol", "footprint"):
        (output / directory).mkdir()
    commands = [
        [
            str(CLI),
            "sym",
            "export",
            "svg",
            "--output",
            str(output / "symbol"),
            str(probe.link / "Symbols.kicad_sym"),
        ],
        [
            str(CLI),
            "fp",
            "export",
            "svg",
            "--output",
            str(output / "footprint"),
            str(probe.link / "Footprints.pretty"),
        ],
        [
            str(CLI),
            "pcb",
            "drc",
            "--format",
            "json",
            "--output",
            str(output / "drc.json"),
            str(probe.link / "probe.kicad_pcb"),
        ],
        [
            str(CLI),
            "pcb",
            "export",
            "step",
            "--force",
            "--output",
            str(output / "board.step"),
            str(probe.link / "probe.kicad_pcb"),
        ],
    ]
    receipts = []
    for command in commands:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        receipts.append(
            {
                "arguments": command[1:],
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        if result.returncode:
            raise RuntimeError("Native target-resolution probe failed")
    expected = "Probe" + name.title()
    for folder in ("symbol", "footprint"):
        svgs = list((output / folder).rglob("*.svg"))
        if not svgs or not any(
            expected.casefold() in svg.stem.casefold() for svg in svgs
        ):
            raise RuntimeError("Native SVG did not resolve the intended entry")
    drc = json.loads((output / "drc.json").read_bytes())
    library_errors = [
        item
        for item in drc.get("violations", [])
        if item.get("type")
        in {"lib_footprint_issues", "lib_footprint_mismatch"}
    ]
    if library_errors:
        raise RuntimeError("Native PCB library-table resolution failed")
    if not (output / "board.step").is_file():
        raise RuntimeError("Native STEP model export is missing")
    import cadquery as cq

    model_solids = len(
        cq.importers.importStep(str(probe.link / "Models/0402.step"))
        .solids()
        .vals()
    )
    exported_solids = len(
        cq.importers.importStep(str(output / "board.step")).solids().vals()
    )
    if exported_solids != model_solids + 1:
        raise RuntimeError("Native export did not resolve all model solids")
    return {
        "commands": receipts,
        "library_table_violations": library_errors,
        "source_model_solids": model_solids,
        "exported_board_and_model_solids": exported_solids,
        "artifacts": {
            file.relative_to(output).as_posix(): sha256(
                file.read_bytes()
            ).hexdigest()
            for file in sorted(output.rglob("*"))
            if file.is_file()
        },
    }


def stress(probe: AtomicTargetProbe) -> dict:
    """@brief Records bounded anchored concurrent reads during real switches.
    @param probe Disposable target with old and new complete generations.
    @return Reader counts, switch counts and observed exact inventory labels.
    @details Every file of each snapshot is opened relative to one root handle.
    Worker exceptions or inventories outside the declared complete sets fail.
    """
    barrier = Barrier(5)
    expected = probe.inventories

    def reader():
        """@brief Takes 40 complete snapshots through opened generation roots.
        @return Observed generation labels.
        @details Native descendant opens stay anchored for the entire snapshot.
        """
        barrier.wait(timeout=10)
        observed = []
        for _ in range(40):
            with probe.reader() as handle:
                selected = probe.api.final_path(handle).name
                hashes = {
                    path: sha256(
                        probe.api.read_relative(handle, path)
                    ).hexdigest()
                    for path in expected[selected]
                }
                if hashes != expected[selected]:
                    raise RuntimeError("Reader saw an incomplete generation")
                observed.append(selected)
        return observed

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(reader) for _ in range(4)]
        barrier.wait(timeout=10)
        current = probe.current
        for _ in range(80):
            new = "new" if current == "old" else "old"
            probe.switch(new, expected=current)
            current = new
        observed = [
            name for future in futures for name in future.result(timeout=30)
        ]
    return {
        "readers": 4,
        "snapshots": len(observed),
        "switches": 80,
        "observed": {
            name: observed.count(name) for name in sorted(set(observed))
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def run(workspace: Path) -> dict:
    """@brief Proves selection, complete reads, rollback and native access.
    @param workspace Absent absolute exclusively disposable workspace.
    @return Structured feasibility evidence and support restrictions.
    @details Leaves an owned old-generation project openable for editor probes;
    closes the junction only after the caller finishes any retained workspace.
    """
    probe = AtomicTargetProbe(
        workspace, {name: generation(name) for name in ("old", "new")}, "old"
    )
    outputs = workspace / "native-output"
    outputs.mkdir()
    try:
        elevated = probe.api.is_elevated()
        if elevated:
            raise RuntimeError("Feasibility must run without elevation")
        version = subprocess.run(
            [str(CLI), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout.strip()
        if version != "10.0.6":
            raise RuntimeError("Unvalidated KiCad patch for this target probe")
        old = native_checks(probe, "old", outputs / "old")
        with probe.reader() as root_handle:
            before = {
                path: sha256(
                    probe.api.read_relative(root_handle, path)
                ).hexdigest()
                for path in probe.inventories["old"]
            }
            probe.switch("new", expected="old")
            anchored = {
                path: sha256(
                    probe.api.read_relative(root_handle, path)
                ).hexdigest()
                for path in probe.inventories["old"]
            }
        if anchored != before:
            raise RuntimeError("Open root failed to retain its old generation")
        new = native_checks(probe, "new", outputs / "new")
        probe.switch("old", expected="new")
        rollback = native_checks(probe, "old", outputs / "rollback")
        if probe.switch("old", expected="old"):
            raise RuntimeError(
                "Exact repeat did not remain an idempotent no-op"
            )
        cancellation = not probe.switch("new", expected="old", cancel=True)
        with probe.api.directory(probe.link, reparse=True, share=1) as handle:
            payload = probe.api.reparse(handle)
            try:
                probe.switch("new", expected="old")
            except OSError as error:
                sharing_error = error.winerror
            else:
                raise RuntimeError(
                    "Required sharing-conflict probe did not fail"
                )
            if probe.api.reparse(handle) != payload or sharing_error != 32:
                raise RuntimeError(
                    "Sharing failure changed the active payload"
                )
        concurrency = stress(probe)
        if any(
            probe._inventory(path) != probe.inventories[name]
            for name, path in probe.generations.items()
        ):
            raise RuntimeError(
                "Publication or native inspection mutated generation bytes"
            )
        tables_changed = all(
            probe.inventories["old"][name] != probe.inventories["new"][name]
            for name in ("sym-lib-table", "fp-lib-table")
        )
        if not tables_changed:
            raise RuntimeError(
                "Required complete table-change fixture is absent"
            )
        return {
            "status": "PASS_FEASIBILITY_ONLY",
            "platform": platform.platform(),
            "python": platform.python_version(),
            "elevated": elevated,
            "kicad_version": version,
            "cli_sha256": sha256(CLI.read_bytes()).hexdigest(),
            "native_default_local_settings_sha256": sha256(
                (
                    ROOT
                    / "docs/gates/phase-13.2-atomic-default-project-local.json"
                ).read_bytes()
            ).hexdigest(),
            "workspace": str(workspace),
            "active_project": str(probe.link / "probe.kicad_pcb"),
            "volume": probe.volume,
            "junction_file_id": probe.link_identity,
            "boundary": "One FSCTL_SET_REPARSE_POINT on the owned junction",
            "reader_boundary": (
                "One opened root plus NtCreateFile RootDirectory"
            ),
            "before_and_after_switch_anchored_hashes_equal": anchored
            == before,
            "complete_generation_inventories": probe.inventories,
            "both_library_table_bytes_changed": tables_changed,
            "native": {"old": old, "new": new, "rollback": rollback},
            "cancelled_before_switch": cancellation,
            "sharing_failure_winerror": sharing_error,
            "concurrent_readers": concurrency,
            "restrictions": [
                "New owned project root on the same fixed NTFS volume",
                "Existing directories and foreign reparses are not adopted",
                "Libraries, tables and references stay inside the generation",
                "Generation files stay immutable and contain no reparses",
                "Editors must quiesce and explicitly refresh libraries",
                "External writers and remote/removable volumes unsupported",
                "No production authorization, journal or power-loss proof",
            ],
        }
    except BaseException:
        probe.close()
        raise


def main() -> int:
    """@brief Writes feasibility evidence from a fresh disposable target.
    @return Zero only after required real local and native checks succeed.
    @details An explicit workspace is retained for follow-up editor checks;
    the default is cleaned after removing its junction directly.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    if args.workspace:
        evidence = run(args.workspace.absolute())
    else:
        with tempfile.TemporaryDirectory(
            prefix="partsmith-atomic-native-"
        ) as name:
            workspace = Path(name) / "owned"
            evidence = run(workspace)
            (workspace / "active").rmdir()
            evidence["workspace_retained"] = False
    evidence.setdefault("workspace_retained", True)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "concurrency": evidence["concurrent_readers"],
                "evidence": str(args.evidence),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
