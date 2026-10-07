"""@package partsmith.gui.symbol_inspection
@brief Resolves actual symbol pins and their bound footprint mapping.
@details Read-only diagnostics never grant approval or substitute current IR
for generated symbol bytes. Native previews belong to final artifacts only.
"""

import json
import re
from collections import Counter
from hashlib import sha256

from partsmith.persistence.release import ReleaseStore

MAX_SYMBOL_BYTES = 1024 * 1024


def parse_symbol(content):
    """@brief Reads properties and pins from a bounded generated symbol.
    @param content Exact generated KiCad symbol library bytes.
    @return Symbol name, properties and actual pin records.
    @details Rejects malformed, inherited or multiple-component libraries;
    this inspector supports the generated single-component library profile.
    """
    if (
        not isinstance(content, bytes)
        or not 0 < len(content) <= MAX_SYMBOL_BYTES
    ):
        raise ValueError("SYMBOL_INPUT_LIMIT: missing or oversized symbol")
    stack, roots = [], []
    for token in re.findall(
        r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', content.decode("utf-8")
    ):
        if token == "(":
            if len(stack) >= 32:
                raise ValueError("SYMBOL_SYNTAX: excessive nesting")
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("SYMBOL_SYNTAX: unbalanced syntax")
            stack.pop()
        elif not stack:
            raise ValueError("SYMBOL_SYNTAX: invalid wrapper")
        elif token.startswith('"'):
            stack[-1].append(json.loads(token))
        elif '"' in token:
            raise ValueError("SYMBOL_SYNTAX: invalid quoted value")
        else:
            stack[-1].append(token)
    if (
        stack
        or len(roots) != 1
        or not roots[0]
        or roots[0][0] != "kicad_symbol_lib"
    ):
        raise ValueError("SYMBOL_SYNTAX: invalid library")
    symbols = [
        node
        for node in roots[0]
        if isinstance(node, list) and node and node[0] == "symbol"
    ]
    if (
        len(symbols) != 1
        or len(symbols[0]) < 2
        or not isinstance(symbols[0][1], str)
    ):
        raise ValueError("SYMBOL_PROFILE: expected one generated component")
    symbol = symbols[0]
    properties, pins = {}, []
    pending = [symbol]
    while pending:
        node = pending.pop()
        if not node:
            raise ValueError("SYMBOL_SYNTAX: empty node")
        if node[0] == "extends":
            raise ValueError("SYMBOL_PROFILE: inherited symbol unsupported")
        if node[0] == "property":
            if (
                len(node) < 3
                or not all(isinstance(value, str) for value in node[1:3])
                or node[1] in properties
            ):
                raise ValueError("SYMBOL_SYNTAX: invalid property")
            properties[node[1]] = node[2]
        elif node[0] == "pin":
            fields = {}
            for item in node[3:]:
                if (
                    not isinstance(item, list)
                    or not item
                    or not isinstance(item[0], str)
                    or item[0] in fields
                ):
                    raise ValueError("SYMBOL_SYNTAX: invalid pin fields")
                fields[item[0]] = item[1:]
            if (
                len(node) < 3
                or not isinstance(node[1], str)
                or any(
                    not fields.get(key) or not isinstance(fields[key][0], str)
                    for key in ("number", "name")
                )
            ):
                raise ValueError("SYMBOL_SYNTAX: incomplete pin")
            pins.append(
                {
                    "number": fields["number"][0],
                    "name": fields["name"][0],
                    "electrical_type": node[1],
                }
            )
            continue
        pending.extend(
            reversed([item for item in node[1:] if isinstance(item, list)])
        )
    if not pins:
        raise ValueError("SYMBOL_PROFILE: no generated pins")
    return {"name": symbol[1], "properties": properties, "pins": pins}


def pin_mapping(actual, reviewed, pads):
    """@brief Compares actual symbol pin data with reviewed pins and pads.
    @param actual Pins parsed from generated symbol bytes.
    @param reviewed Immutable pins from the displayed artifact revision.
    @param pads Pads parsed independently from the displayed footprint.
    @return Rows retaining actual fields and explicit mapping discrepancies.
    @details Duplicate, missing, extra and mismatched identities remain
    visible.
    """
    expected = {pin["number"]: pin for pin in reviewed}
    counts = Counter(pin["number"] for pin in actual)
    pad_counts = Counter(pad["number"] for pad in pads)
    rows = []
    for pin in actual:
        number, issues = pin["number"], []
        if counts[number] != 1:
            issues.append("Duplicate symbol pin")
        if number not in expected:
            issues.append("Pin absent from reviewed IR")
        else:
            for key in ("name", "electrical_type"):
                if pin[key] != expected[number][key]:
                    issues.append(f"{key} differs from reviewed IR")
        if not pad_counts[number]:
            issues.append("Missing footprint pad")
        elif pad_counts[number] != 1:
            issues.append("Duplicate footprint pad")
        rows.append(
            {
                **pin,
                "pad": number if pad_counts[number] else "Missing",
                "diagnostic": "; ".join(issues) or "MATCH",
            }
        )
    for number in sorted(expected.keys() - counts.keys()):
        rows.append(
            {
                "number": number,
                "name": "",
                "electrical_type": "",
                "pad": number if pad_counts[number] else "Missing",
                "diagnostic": "Reviewed pin missing from symbol",
            }
        )
    for number in sorted(pad_counts.keys() - counts.keys()):
        rows.append(
            {
                "number": "",
                "name": "",
                "electrical_type": "",
                "pad": number,
                "diagnostic": "Footprint pad missing from symbol",
            }
        )
    return rows


def bound_symbol(session, binding, pads):
    """@brief Resolves symbol bytes and previews for the displayed attempt.
    @param session Active session containing retained immutable assets.
    @param binding Displayed stage, build, revision and reviewed pins.
    @param pads Independently parsed displayed footprint pads.
    @return Detached symbol report with exact bytes, mapping and validation.
    @details Requires exact stage/build/revision and content hash agreement;
    ignores other attempts and final previews of preliminary bytes.
    """
    drafts = session.state.get("drafts", {})
    artifacts = [
        item
        for item in drafts.get("artifacts", [])
        if item["type"] == "SYMBOL"
        and all(
            item[key] == binding[key]
            for key in ("stage", "build_id", "revision_id")
        )
    ]
    if len(artifacts) != 1:
        raise ValueError(
            "Symbol unavailable for the displayed artifact binding"
        )
    artifact = artifacts[0]
    content = session.get(artifact["reference"])
    if sha256(content).hexdigest() != artifact["sha256"]:
        raise ValueError("Symbol artifact hash differs from retained bytes")
    parsed = parse_symbol(content)
    preview = None
    preview_error = None
    if binding["stage"] == "FINAL":
        for item in drafts.get("previews", []):
            if (
                item["type"] == "SYMBOL"
                and item["build_id"] == binding["build_id"]
                and item["revision_id"] == binding["revision_id"]
                and item.get("artifact_sha256", artifact["sha256"])
                == artifact["sha256"]
            ):
                try:
                    preview = session.get(item["reference"])
                except (OSError, ValueError) as error:
                    preview_error = str(error)
    with session.connection() as connection:
        results = ReleaseStore(connection).retained_validation_results(
            binding["build_id"]
        )
    return {
        **parsed,
        "artifact": dict(artifact),
        "content": content,
        "preview": preview,
        "preview_error": preview_error,
        "mapping": pin_mapping(parsed["pins"], binding["pins"], pads),
        "validation": [
            result
            for result in results
            if artifact["sha256"] in result.get("artifact_ids", [])
        ],
    }
