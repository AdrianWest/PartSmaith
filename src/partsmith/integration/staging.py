"""@package partsmith.integration.staging
@brief Stages exact approved libraries with versioned mechanical relocations.
@details Comparator 1.0 permits only entry/unit names, symbol Footprint mapping
property insertion/relocation and model URI relocation. All other tree tokens
and STEP bytes remain exact. Native outputs are separate diagnostic evidence.
"""

import re
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp

from partsmith.integration.atomic_target import _ordinary_ancestors
from partsmith.integration.bindings import verify_files
from partsmith.integration.contracts import (
    REQUIRED_RULES,
    InstallationManifest,
    IntegrationValidationReport,
)
from partsmith.integration.errors import FailureCode, IntegrationError
from partsmith.integration.native_stage import (
    native_model_check,
    symbol_pin_records,
)
from partsmith.integration.planner import (
    MANAGED_ROOTS,
    OWNED_NAMES,
    TABLES,
    PlanningResult,
    file_inventory,
    read_project,
)
from partsmith.integration.policy import ResourcePolicy
from partsmith.integration.sexpr import Atom, children, parse, serialize
from partsmith.integration.sources import (
    ApprovedSource,
    resolve_approved_source,
    verify_source_bindings,
)
from partsmith.integration.store import IntegrationStore
from partsmith.ir.canonical import canonical_json, parse_json
from partsmith.kicad.runtime import discover_kicad
from partsmith.process import run_process
from partsmith.release.runtime_resources import runtime_resources


def resolve_sources(
    connection: sqlite3.Connection,
    expected: list[dict],
    supplied: tuple[ApprovedSource, ...],
) -> tuple[ApprovedSource, ...]:
    """@brief Re-resolves all historical approvals in the trusted database.
    @param connection Authoritative application database.
    @param expected Frozen source declarations.
    @param supplied Hash-bound source data retained by the planning caller.
    @return Fresh exact approved source packages in component order.
    @details Supplied actor text grants no authority; each build is verified.
    """
    ResourcePolicy().require_sizes(
        [
            size
            for source in supplied
            for size in [
                len(source.manifest_bytes),
                len(source.approval_bytes),
            ]
            + [len(blob) for _, _, blob in source.artifacts]
        ]
    )
    verify_source_bindings(expected, supplied)
    result = tuple(
        sorted(
            (
                resolve_approved_source(
                    connection, parse_json(s.approval_bytes)["build_id"]
                )
                for s in supplied
            ),
            key=lambda source: source.component_id,
        )
    )
    verify_source_bindings(expected, result)
    return result


def relocated(source: ApprovedSource, mapping: dict) -> tuple[list, list]:
    """@brief Applies the closed comparator-1.0 mechanical relocation rules.
    @param source Complete unchanged approved engineering package.
    @param mapping Exact frozen component entry/path declarations.
    @return Complete transformed symbol and footprint trees.
    @details Rejects unknown source grammar and ambiguous property/model nodes;
    geometry, placement, electrical fields and numeric spelling stay exact.
    """
    artifacts = {role: (path, blob) for role, path, blob in source.artifacts}
    symbol_root = parse(artifacts["symbol"][1])
    if symbol_root[0] != "kicad_symbol_lib" or (
        [node for node in symbol_root[1:] if node[0] != "symbol"]
        != [
            [Atom("version"), Atom("20231120")],
            [Atom("generator"), Atom("partsmith")],
        ]
    ):
        raise ValueError("Unsupported released symbol format")
    symbols = children(symbol_root, "symbol")
    if len(symbols) != 1 or len(symbols[0]) < 3:
        raise ValueError("Expected exactly one released symbol")
    symbol = deepcopy(symbols[0])
    original_name = symbol[1]
    if not isinstance(original_name, str):
        raise ValueError("Invalid symbol name")
    symbol[1] = mapping["symbol_name"]
    for unit in children(symbol, "symbol"):
        if not isinstance(unit[1], str) or not re.fullmatch(
            re.escape(original_name) + r"_[0-9]+_[0-9]+", unit[1]
        ):
            raise ValueError("Unsupported symbol unit identity")
        unit[1] = mapping["symbol_name"] + unit[1][len(original_name) :]
    properties = [
        p for p in children(symbol, "property") if p[1] == "Footprint"
    ]
    if len(properties) > 1:
        raise ValueError("Ambiguous footprint property")
    identifier = (
        mapping["footprint_nickname"] + ":" + mapping["footprint_name"]
    )
    if properties:
        if len(properties[0]) < 3 or not isinstance(properties[0][2], str):
            raise ValueError("Malformed footprint property")
        properties[0][2] = identifier
    else:
        symbol.insert(2, [Atom("property"), "Footprint", identifier])
    footprint = parse(artifacts["footprint"][1])
    if footprint[0] != "footprint" or not isinstance(footprint[1], str):
        raise ValueError("Invalid released footprint")
    footprint[1] = mapping["footprint_name"]
    models = children(footprint, "model")
    if len(models) != 1 or models[0][1] != artifacts["model_3d"][0]:
        raise ValueError("Invalid released STEP association")
    models[0][1] = "${KIPRJMOD}/" + mapping["model_path"]
    return symbol, footprint


def mapped_terminals(symbol: list, footprint: list) -> int:
    """@brief Verifies exact symbol pin identities against physical pad groups.
    @param symbol Complete relocated symbol tree.
    @param footprint Complete relocated footprint tree.
    @return Verified terminal count.
    @details Repeated physical pads may share a terminal; symbol pin aliases
    and missing/extra terminal numbers fail. Geometry is compared separately.
    """
    pins = [
        pin
        for unit in children(symbol, "symbol")
        for pin in children(unit, "pin")
    ]
    numbers = []
    for pin in pins:
        fields = children(pin, "number")
        if len(fields) != 1 or len(fields[0]) < 2:
            raise ValueError("Invalid pin number")
        numbers.append(fields[0][1])
    pads = [pad[1] for pad in children(footprint, "pad") if pad[1]]
    if (
        not numbers
        or len(set(numbers)) != len(numbers)
        or (set(numbers) != set(pads))
    ):
        raise ValueError("Symbol/pad mapping mismatch")
    return len(numbers)


def planned_files(result: PlanningResult, sources: tuple) -> dict[str, bytes]:
    """@brief Constructs the complete deterministic managed file set.
    @param result Exact planning and current target snapshot.
    @param sources Fresh trusted source packages in frozen order.
    @return Managed files including both complete project-local tables.
    @details Unrelated table nodes remain structurally identical. Tables with
    no planned operation retain their original exact bytes.
    """
    original = dict(result.snapshot.objects)
    plan = result.plan.data
    objects, symbols = {}, []
    for source, mapping in zip(sources, plan["mappings"], strict=True):
        symbol, footprint = relocated(source, mapping)
        mapped_terminals(symbol, footprint)
        symbols.append(symbol)
        objects[mapping["footprint_path"]] = serialize(footprint)
        objects[mapping["model_path"]] = next(
            blob for role, _, blob in source.artifacts if role == "model_3d"
        )
    if symbols:
        objects["BFT_Symbols.kicad_sym"] = serialize(
            [
                Atom("kicad_symbol_lib"),
                [Atom("version"), Atom("20231120")],
                [Atom("generator"), Atom("partsmith")],
                *symbols,
            ]
        )
    operations = {o["path"] for o in plan["operations"]}
    for name, kind in TABLES.items():
        if name in original and name not in operations:
            objects[name] = original[name]
            continue
        tree = (
            parse(original[name])
            if name in original
            else [Atom(kind), [Atom("version"), Atom("7")]]
        )
        entries = children(tree, "lib")
        tree = [
            node
            for node in tree
            if not (
                isinstance(node, list)
                and node in entries
                and children(node, "name")[0][1] == OWNED_NAMES[name]
            )
        ]
        if sources:
            uri = (
                "BFT_Symbols.kicad_sym"
                if name == "sym-lib-table"
                else ("BFT_Footprints.pretty")
            )
            tree.append(
                [
                    Atom("lib"),
                    [Atom("name"), OWNED_NAMES[name]],
                    [Atom("type"), "KiCad"],
                    [Atom("uri"), "${KIPRJMOD}/" + uri],
                    [Atom("options"), ""],
                    [Atom("descr"), "PartSmith managed"],
                ]
            )
        objects[name] = serialize(tree)
    return objects


def whole_generation(
    result: PlanningResult, objects: dict
) -> tuple[dict, tuple]:
    """@brief Preserves mutable project files and unrelated directories.
    @param result Frozen whole-project target snapshot.
    @param objects Proposed complete managed file set.
    @return Complete file mapping and exact sorted directory inventory.
    @details Only previous managed files/directories are replaced or removed.
    """
    verify_project_references(result, objects)
    whole = dict(result.snapshot.objects)
    if result.snapshot.manifest:
        for entry in result.snapshot.manifest.data["files"]:
            whole.pop(entry["path"], None)
    whole.update(objects)
    file_inventory(whole)
    directories = {
        name
        for name in result.snapshot.directories
        if name.split("/")[0] not in MANAGED_ROOTS
    }
    for name in whole:
        directories.update(
            parent.as_posix()
            for parent in Path(name).parents
            if parent.as_posix() != "."
        )
    return whole, tuple(sorted(directories))


def verify_project_references(result: PlanningResult, objects: dict) -> None:
    """@brief Refuses removal of libraries/models referenced by project files.
    @param result Frozen complete project snapshot and proposed mappings.
    @param objects Complete proposed managed file bytes.
    @return None.
    @details Unrelated external libraries remain outside the managed namespace.
    Native schematic cache and board instances retain all user design bytes.
    """
    mappings = result.plan.data["mappings"]
    symbols = {"BFT_Symbols:" + m["symbol_name"] for m in mappings}
    footprints = {"BFT_Footprints:" + m["footprint_name"] for m in mappings}
    models = {"${KIPRJMOD}/" + m["model_path"] for m in mappings}

    def visit(node: list) -> None:
        """@brief Checks reserved project-local references recursively.
        @param node One bounded parsed native design tree node.
        @return None.
        @details Reads identifiers only; never rewrites cached design data.
        """
        for index, value in enumerate(node[1:], 1):
            if isinstance(value, list):
                visit(value)
            elif (
                isinstance(value, str)
                and not isinstance(value, Atom)
                and (
                    index == 1
                    and node[0] in {"lib_id", "symbol", "footprint", "model"}
                    or index == 2
                    and node[0] == "property"
                    and node[1] == "Footprint"
                )
            ):
                expected = None
                if value.casefold().startswith("bft_symbols:"):
                    expected = symbols
                elif value.casefold().startswith("bft_footprints:"):
                    expected = footprints
                elif (
                    value.replace("\\", "/")
                    .casefold()
                    .startswith(("${kiprjmod}/bft_3dstep/", "bft_3dstep/"))
                ):
                    expected = models
                if expected is not None and value not in expected:
                    raise IntegrationError(FailureCode.SEMANTIC_CHECK_FAILED)

    try:
        for name, blob in result.snapshot.objects:
            if name.endswith((".kicad_sch", ".kicad_pcb")):
                visit(parse(blob))
        if any(m["model_path"] not in objects for m in mappings):
            raise IntegrationError(FailureCode.SEMANTIC_CHECK_FAILED)
    except (ValueError, TypeError, IndexError) as error:
        if isinstance(error, IntegrationError):
            raise
        raise IntegrationError(FailureCode.SEMANTIC_CHECK_FAILED) from error


def verify_versions(result: PlanningResult) -> None:
    """@brief Requires the implemented adapter, comparator and runtime lock.
    @param result Exact frozen intended plan.
    @return None.
    @details Unsupported versions cannot reuse passing reports or relocations.
    """
    expected = {
        "adapter": "1.0",
        "serializer": "1.0",
        "comparator": "1.0",
        "kicad": "10.0.6",
        "runtime_lock_hash": sha256(runtime_resources()[0]).hexdigest(),
    }
    if result.plan.data["versions"] != expected:
        raise IntegrationError(FailureCode.INVALID_CONTRACT)


def verify_semantics(
    result: PlanningResult, sources: tuple, objects: dict[str, bytes]
) -> int:
    """@brief Compares every staged engineering token to approved originals.
    @param result Exact frozen mapping and expected target base.
    @param sources Fresh trusted complete source packages.
    @param objects Exact current managed staged bytes.
    @return Total verified symbol/physical terminals.
    @details Missing/extra entries, changed tokens, STEP or unmanaged table
    nodes fail. Previously installed unchanged components are also compared.
    """
    expected = planned_files(result, sources)
    verify_files(file_inventory(expected), objects)
    terminals = 0
    if sources:
        tree = parse(objects["BFT_Symbols.kicad_sym"])
        entries = children(tree, "symbol")
        if len(entries) != len(sources):
            raise ValueError("Packed symbol entry count")
        for source, mapping, symbol in zip(
            sources, result.plan.data["mappings"], entries, strict=True
        ):
            expected_symbol, expected_footprint = relocated(source, mapping)
            footprint = parse(objects[mapping["footprint_path"]])
            if symbol != expected_symbol or footprint != expected_footprint:
                raise ValueError("Engineering tree differs")
            terminals += mapped_terminals(symbol, footprint)
            prior = result.snapshot.manifest
            if prior and source.binding() in prior.data["sources"]:
                previous = dict(result.snapshot.objects)
                old_symbols = children(
                    parse(previous[mapping["symbol_path"]]), "symbol"
                )
                matches = [s for s in old_symbols if s[1] == symbol[1]]
                if (
                    matches != [symbol]
                    or parse(previous[mapping["footprint_path"]]) != footprint
                    or previous[mapping["model_path"]]
                    != (objects[mapping["model_path"]])
                ):
                    raise ValueError("Retained component engineering differs")
    return terminals


def quiet_log(message: str) -> None:
    """@brief Discards bounded native transport text from deterministic data.
    @param message Worker log line already bounded by the supervisor.
    @return None.
    @details Run telemetry does not enter installation generation identity.
    """


def _native_check(root: Path, names: tuple[str, ...], version: str) -> dict:
    """@brief Parses every packed symbol and footprint with pinned KiCad.
    @param root Complete isolated project generation.
    @param names Exact expected entry names.
    @param version Frozen required native runtime version.
    @return Separate operational CLI receipt without deterministic authority.
    @details Round-trip and render outputs never replace engineering bytes.
    Process time, logs and descendants are bounded by resource policy 1.0.
    """
    runtime = discover_kicad(version)
    receipts = []
    if not names:
        return {"version": runtime.version, "operations": [], "entries": []}
    with TemporaryDirectory(prefix="partsmith-integration-native-") as temp:
        output = Path(temp)
        (output / "symbol-svg").mkdir()
        (output / "footprint-svg").mkdir()
        commands = [
            (
                "sym",
                "upgrade",
                "--force",
                str(root / "BFT_Symbols.kicad_sym"),
                "--output",
                str(output / "symbols"),
            ),
            (
                "sym",
                "export",
                "svg",
                str(root / "BFT_Symbols.kicad_sym"),
                "--output",
                str(output / "symbol-svg"),
                "--black-and-white",
            ),
            (
                "fp",
                "upgrade",
                "--force",
                str(root / "BFT_Footprints.pretty"),
                "--output",
                str(output / "footprints.pretty"),
            ),
            (
                "fp",
                "export",
                "svg",
                str(root / "BFT_Footprints.pretty"),
                "--output",
                str(output / "footprint-svg"),
                "--black-and-white",
            ),
        ]
        for arguments in commands:
            process = run_process(
                [str(runtime.executable), *arguments],
                log=quiet_log,
                cwd=root,
                timeout=ResourcePolicy().native_timeout_seconds,
                output_budget=ResourcePolicy().log_bytes,
            )
            if process.returncode:
                raise IntegrationError(FailureCode.NATIVE_CHECK_FAILED)
            receipts.append(
                {
                    "operation": "-".join(arguments[:2]),
                    "exit_code": 0,
                    "stdout_sha256": sha256(
                        process.stdout.encode()
                    ).hexdigest(),
                    "stderr_sha256": sha256(
                        process.stderr.encode()
                    ).hexdigest(),
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                }
            )
        original_pins = symbol_pin_records(
            parse((root / "BFT_Symbols.kicad_sym").read_bytes())
        )
        upgraded_pins = symbol_pin_records(
            parse((output / "symbols").read_bytes())
        )
        if original_pins != upgraded_pins:
            raise IntegrationError(FailureCode.SEMANTIC_CHECK_FAILED)
        for directory in ("symbol-svg", "footprint-svg"):
            rendered = {
                path.stem for path in (output / directory).rglob("*.svg")
            }
            expected = set(names)
            if directory == "symbol-svg":
                entries = children(
                    parse((root / "BFT_Symbols.kicad_sym").read_bytes()),
                    "symbol",
                )
                expected = {
                    entry[1] + "_unit" + str(unit)
                    for entry in entries
                    for unit in range(
                        1,
                        max(
                            1,
                            max(
                                int(child[1].rsplit("_", 2)[1])
                                for child in children(entry, "symbol")
                            ),
                        )
                        + 1,
                    )
                }
            if rendered != expected:
                raise IntegrationError(FailureCode.NATIVE_CHECK_FAILED)
        receipts.append(native_model_check(root, output, runtime.executable))
        ResourcePolicy().require_sizes(
            [
                path.stat().st_size
                for path in output.rglob("*")
                if path.is_file()
            ]
        )
    return {
        "version": runtime.version,
        "operations": receipts,
        "entries": list(names),
        "native_pin_semantics_preserved": True,
    }


def native_check(root: Path, names: tuple[str, ...], version: str) -> dict:
    """@brief Classifies actual bounded native failures for service callers.
    @param root Exact isolated complete stage.
    @param names Frozen declared entry names.
    @param version Exact required native runtime version.
    @return Actual separate native receipt.
    @details Missing runtimes, worker failures and CAD import errors fail
    closed without including raw transport output or local paths in errors.
    """
    try:
        return _native_check(root, names, version)
    except IntegrationError:
        raise
    except (OSError, RuntimeError, ValueError) as error:
        raise IntegrationError(FailureCode.NATIVE_CHECK_FAILED) from error


def validation_report(
    result: PlanningResult,
    objects: dict,
    terminals: int,
    manifest: InstallationManifest | None = None,
) -> IntegrationValidationReport:
    """@brief Freezes deterministic rule results after actual checks pass.
    @param result Exact frozen plan/target/source bindings.
    @param objects Final checked managed file bytes.
    @param terminals Actual verified mapping terminal count.
    @param manifest Optional separately checked finalized manifest.
    @return Acyclic pre-manifest or exact post-manifest report.
    @details Actor, time, local paths and render hashes remain outside results.
    """
    plan = result.plan.data
    return IntegrationValidationReport(
        {
            "schema_version": "1.0",
            "rule_set_version": "1.0",
            "comparator_version": plan["versions"]["comparator"],
            "phase": "POST_MANIFEST" if manifest else "PRE_MANIFEST",
            "plan_hash": result.plan.sha256,
            "manifest_hash": manifest.sha256 if manifest else None,
            **{
                key: plan[key]
                for key in ("target", "expected_base", "sources", "mappings")
            },
            "files": file_inventory(objects),
            "results": [
                {
                    "rule_id": rule,
                    "status": "PASS",
                    "applicability": "APPLICABLE",
                    "reason": {
                        "MAPPING": "Exact pin identities equal pad groups",
                        "NATIVE_PARSE": "Pinned KiCad parses every entry",
                        "PATH_RESOLUTION": "Project references resolve",
                        "SEMANTIC_PRESERVATION": "Exact comparator 1.0 trees",
                    }[rule],
                    "measurements": [
                        {
                            "name": "verified_terminals",
                            "expected": str(terminals),
                            "observed": str(terminals),
                            "tolerance": "0",
                        }
                    ]
                    if rule == "MAPPING"
                    else [],
                }
                for rule in REQUIRED_RULES
            ],
        }
    )


def installation_manifest(
    result: PlanningResult, objects: dict, report: IntegrationValidationReport
) -> InstallationManifest:
    """@brief Binds the fixed generation to its actual deterministic checks.
    @param result Exact frozen proposed plan.
    @param objects Complete checked managed content.
    @param report Actual passing pre-manifest report.
    @return Exact immutable installation generation manifest.
    @details Hash dependencies remain acyclic and contain no operational roots.
    """
    plan = result.plan.data
    return InstallationManifest(
        {
            "schema_version": "1.0",
            "plan_hash": result.plan.sha256,
            **{
                key: plan[key]
                for key in (
                    "target",
                    "expected_base",
                    "sources",
                    "mappings",
                    "versions",
                )
            },
            "files": file_inventory(objects),
            "required_checks": [
                {"rule_id": rule, "report_hash": report.sha256}
                for rule in REQUIRED_RULES
            ],
            "semantic_validation_hash": report.sha256,
        }
    )


@dataclass(frozen=True)
class StageResult:
    """@brief Retains exact staged content and its immutable validation DAG.
    @details An isolated stage grants no publication authority.
    """

    planning: PlanningResult
    root: Path
    objects: tuple[tuple[str, bytes], ...]
    manifest: InstallationManifest
    pre: IntegrationValidationReport
    post: IntegrationValidationReport
    native_receipt: dict

    def recheck(self) -> dict[str, bytes]:
        """@brief Reloads all stage files and verifies the complete inventory.
        @return Detached exact managed byte mapping.
        @details Mutable project bytes must also equal their planned snapshot.
        """
        actual, directories = read_project(self.root)
        original, expected_directories = whole_generation(
            self.planning, dict(self.objects)
        )
        verify_files(file_inventory(original), actual)
        if directories != expected_directories:
            raise IntegrationError(FailureCode.TAMPERED_SOURCE)
        managed = {name: actual[name] for name, _ in self.objects}
        verify_files(self.manifest.data["files"], managed)
        return managed


class Stager:
    """@brief Builds complete isolated generations without changing targets.
    @details Source approvals are freshly resolved; no generator is rerun.
    """

    def __init__(self, connection: sqlite3.Connection, source_connection=None):
        """@brief Binds the stager to an authoritative caller-owned database.
        @param connection Migrated application database.
        @param source_connection Separate trusted component source catalog.
        @return None.
        @details Construction opens no transaction and writes no content.
        """
        self.connection = connection
        self.source_connection = source_connection or connection

    def stage(self, result: PlanningResult, parent: Path) -> StageResult:
        """@brief Stages and validates one exact complete proposed generation.
        @param result Frozen non-no-op planning result.
        @param parent Existing explicit application-owned staging parent.
        @return Verified immutable manifest and separate operational stage.
        @details Failures retain the isolated stage for inspection. Target and
        source store bytes remain untouched; publication is a separate action.
        """
        if result.no_op:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        verify_versions(result)
        result.snapshot.recheck()
        _ordinary_ancestors(parent.absolute())
        sources = resolve_sources(
            self.source_connection, result.plan.data["sources"], result.sources
        )
        try:
            objects = planned_files(result, sources)
            terminals = verify_semantics(result, sources, objects)
            root = Path(mkdtemp(prefix="stage-", dir=parent.absolute()))
            whole, directories = whole_generation(result, objects)
            for name in directories:
                (root / name).mkdir(parents=True, exist_ok=True)
            for name, blob in sorted(whole.items()):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(blob)
            names = tuple(
                m["symbol_name"] for m in result.plan.data["mappings"]
            )
            receipt = native_check(
                root, names, result.plan.data["versions"]["kicad"]
            )
            actual, _ = read_project(root)
            verify_files(file_inventory(whole), actual)
            actual_managed = {name: actual[name] for name in objects}
            verify_semantics(result, sources, actual_managed)
            pre = validation_report(result, actual_managed, terminals)
            manifest = installation_manifest(result, actual_managed, pre)
            verify_files(manifest.data["files"], actual_managed)
            post = validation_report(
                result, actual_managed, terminals, manifest
            )
            staged = StageResult(
                result,
                root,
                tuple(sorted(objects.items())),
                manifest,
                pre,
                post,
                receipt,
            )
            staged.recheck()
            result.snapshot.recheck()
            return staged
        except IntegrationError:
            raise
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise IntegrationError(
                FailureCode.SEMANTIC_CHECK_FAILED
            ) from error

    def revalidate(self, staged: StageResult) -> None:
        """@brief Freshly checks sources, semantics, native data and reports.
        @param staged Exact proposed isolated generation and stored reports.
        @return None.
        @details Imported PASS text cannot substitute for these actual checks.
        This operation grants no approval and changes no target or store data.
        """
        verify_versions(staged.planning)
        sources = resolve_sources(
            self.source_connection,
            staged.planning.plan.data["sources"],
            staged.planning.sources,
        )
        objects = staged.recheck()
        try:
            terminals = verify_semantics(staged.planning, sources, objects)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise IntegrationError(
                FailureCode.SEMANTIC_CHECK_FAILED
            ) from error
        native_check(
            staged.root,
            tuple(
                m["symbol_name"] for m in staged.planning.plan.data["mappings"]
            ),
            staged.planning.plan.data["versions"]["kicad"],
        )
        if staged.pre != validation_report(
            staged.planning, objects, terminals
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        if staged.manifest != installation_manifest(
            staged.planning, objects, staged.pre
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        if staged.post != validation_report(
            staged.planning, objects, terminals, staged.manifest
        ):
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        staged.recheck()

    def save(self, attempt_id: str, staged: StageResult) -> None:
        """@brief Explicitly retains checked content for one persisted plan.
        @param attempt_id Existing exact planned attempt.
        @param staged Fully checked isolated generation.
        @return None.
        @details Savepoints retain caller transaction ownership. A stored
        manifest is data until a trusted review/publication service acts.
        """
        from partsmith.persistence.database import savepoint

        staged.recheck()
        row = self.connection.execute(
            "SELECT plan_hash, snapshot_hash FROM integration_attempts "
            "WHERE id=?",
            (attempt_id,),
        ).fetchone()
        if row is None or row[0] != staged.planning.plan.sha256:
            raise IntegrationError(FailureCode.INVALID_CONTRACT)
        if (
            row["snapshot_hash"]
            != sha256(
                canonical_json(staged.planning.snapshot.document)
            ).hexdigest()
        ):
            raise IntegrationError(FailureCode.STALE_BASE)
        if not self.connection.in_transaction:
            self.connection.execute("BEGIN")
        store = IntegrationStore(self.connection)
        with savepoint(self.connection, "integration_stage"):
            source_hashes = store.retain_sources(staged.planning.sources)
            children_hashes = (
                source_hashes
                + tuple(
                    store.put("artifact", blob) for _, blob in staged.objects
                )
                + (
                    store.put_contract(staged.pre),
                    store.put_contract(staged.post),
                )
            )
            identity = store.put_contract(staged.manifest)
            store.reference(identity, children_hashes)
            store.event(attempt_id, "STAGED", identity)
