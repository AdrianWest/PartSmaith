"""Immutable, versioned provider requests and untrusted candidate contracts."""

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Protocol

from jsonschema import Draft202012Validator

from partsmith.extraction.coordinates import validate_region
from partsmith.ir import canonical_json
from partsmith.ir.schema import fragment_valid
from partsmith.ir.targets import target_schema

from .errors import AIError

SCHEMA_VERSION = "ai-result-1.0"
PROMPT_VERSION = "partsmith-ai-1.1"
TASKS = (
    "extract_pin_table",
    "interpret_pin_description",
    "identify_package",
    "interpret_package_drawing",
    "locate_land_pattern",
    "identify_symbol",
    "classify_conflict",
    "translate_technical_text",
    "explain_ambiguity",
)
MAX_INPUT_BYTES = 512 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024


def digest(data):
    return sha256(canonical_json(data)).hexdigest()


def parse(data):
    """Reject duplicate keys, non-finite numbers and oversized JSON."""

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise AIError("Duplicate JSON field in AI data.")
            result[key] = value
        return result

    def invalid(_):
        raise AIError("Non-finite number in AI data.")

    try:
        if len(data.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise AIError("AI data exceeds the response limit.")
        result = json.loads(
            data,
            object_pairs_hook=pairs,
            parse_constant=invalid,
            parse_float=Decimal,
        )
        canonical_json(result)
        return result
    except AIError:
        raise
    except Exception:
        raise AIError("Invalid JSON in AI data.") from None


def obj(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


STRING = {"type": "string", "minLength": 1, "maxLength": 16000}
STRINGS = {"type": "array", "items": STRING, "maxItems": 128}
CONFIDENCE = {"type": "number", "minimum": 0, "maximum": 1}
QUOTE = obj({"evidence_id": STRING, "quote": STRING})
ISSUE = obj(
    {"message": STRING, "evidence_ids": STRINGS, "candidate_ids": STRINGS}
)
CANDIDATE = obj(
    {
        "id": STRING,
        "kind": {
            "type": "string",
            "enum": ["IR_VALUE", "PACKAGE", "TRANSLATION", "EXPLANATION"],
        },
        "target_path": {"type": ["string", "null"]},
        "value_json": STRING,
        "evidence_ids": {**STRINGS, "minItems": 1},
        "supporting_quotes": {
            "type": "array",
            "items": QUOTE,
            "minItems": 1,
            "maxItems": 128,
        },
        "status": {
            "type": "string",
            "enum": ["INFERRED", "UNKNOWN", "AMBIGUOUS", "CONFLICTING"],
        },
        "rationale": STRING,
        "confidence": CONFIDENCE,
    }
)
OUTPUT_SCHEMA = obj(
    {
        "schema_version": {"type": "string", "const": SCHEMA_VERSION},
        "candidates": {"type": "array", "items": CANDIDATE, "maxItems": 128},
        "evidence_references": STRINGS,
        "ambiguities": {"type": "array", "items": ISSUE, "maxItems": 128},
        "conflicts": {"type": "array", "items": ISSUE, "maxItems": 128},
        "confidence": CONFIDENCE,
    }
)


@dataclass(frozen=True, repr=False)
class AIRequest:
    """Detached Evidence snapshot without credentials or authority fields."""

    _snapshot: bytes

    @classmethod
    def create(
        cls, task, part_number, evidence, targets=(), target_language="en"
    ):
        if task not in TASKS:
            raise AIError("Unsupported AI task.")
        if not isinstance(part_number, str) or not part_number.strip():
            raise AIError("The full part number is required.")
        if not evidence or len(evidence) > 128:
            raise AIError("Select between 1 and 128 Evidence records.")
        ids = set()
        for item in evidence:
            if not fragment_valid(item, {"$ref": "#/$defs/evidence"}):
                raise AIError("Invalid source Evidence schema.")
            if item["id"] in ids:
                raise AIError("Duplicate source Evidence identity.")
            ids.add(item["id"])
            source = item["source"]
            if source["region"] is not None:
                validate_region(source["region"], source["page_geometry"])
        if len(set(targets)) != len(targets):
            raise AIError("Duplicate AI target.")
        for path in targets:
            target_schema(path)
            prefixes = {
                "extract_pin_table": ("/pins",),
                "interpret_pin_description": ("/pins",),
                "interpret_package_drawing": ("/package/mechanical/",),
                "locate_land_pattern": ("/footprint/properties/",),
                "identify_symbol": ("/symbol/properties/",),
                "classify_conflict": ("/",),
            }.get(task, ())
            if not any(path.startswith(prefix) for prefix in prefixes):
                raise AIError("Target is outside the selected AI task.")
        if target_language not in ("en", "de", "zh-Hans"):
            raise AIError("Unsupported translation target language.")
        data = {
            "task": task,
            "part_number": part_number,
            "evidence": evidence,
            "targets": list(targets),
            "target_language": target_language,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
        }
        snapshot = canonical_json(data)
        if len(snapshot) > MAX_INPUT_BYTES:
            raise AIError("Selected Evidence exceeds the AI request limit.")
        return cls(snapshot)

    @classmethod
    def from_extraction(
        cls,
        extraction,
        task,
        part_number,
        evidence_ids=None,
        targets=(),
        target_language="en",
    ):
        records = extraction["evidence"]
        if evidence_ids is not None:
            wanted = set(evidence_ids)
            records = [item for item in records if item["id"] in wanted]
            if {item["id"] for item in records} != wanted:
                raise AIError("Selected Evidence is missing.")
        else:
            records = [
                item for item in records if item["extracted"]["text"].strip()
            ]
        document = extraction["document"]
        for record in records:
            source = record["source"]
            if (
                source["document_hash"] != document["sha256"]
                or source["page"] not in extraction["selected_pages"]
            ):
                raise AIError("Evidence differs from the selected document.")
        return cls.create(task, part_number, records, targets, target_language)

    @property
    def data(self):
        return parse(self._snapshot.decode("utf-8"))

    @property
    def input_hash(self):
        return sha256(self._snapshot).hexdigest()


@dataclass(frozen=True, repr=False)
class AIResult:
    _snapshot: bytes

    @property
    def data(self):
        return parse(self._snapshot.decode("utf-8"))

    @property
    def canonical_bytes(self):
        return self._snapshot


class AIProvider(Protocol):
    def analyze(self, request: AIRequest) -> AIResult: ...


def _no_authority(value):
    """Reject review and production control fields in candidate payloads."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {
                "approval_state",
                "approved",
                "evidence_review",
                "actor",
                "validation",
                "artifacts",
                "override_id",
                "standard_id",
            }:
                raise AIError("AI payload contains an authority field.")
            if key == "status" and item not in {
                "INFERRED",
                "UNKNOWN",
                "AMBIGUOUS",
                "CONFLICTING",
                "MISSING",
            }:
                raise AIError("AI payload claims trusted provenance.")
            _no_authority(item)
    elif isinstance(value, list):
        for item in value:
            _no_authority(item)


def _contains_order_number(text, part_number):
    hyphens = str.maketrans("−–‑", "---")
    part = part_number.strip().translate(hyphens)
    return (
        re.search(
            r"(?<![\w./+-])" + re.escape(part) + r"(?![\w./+-])",
            text.translate(hyphens),
        )
        is not None
    )


def normalize(payload, request):
    """Validate references and value types before accepting candidates."""
    if not Draft202012Validator(OUTPUT_SCHEMA).is_valid(payload):
        raise AIError("AI output does not match the candidate schema.")
    payload = parse(canonical_json(payload).decode("utf-8"))
    data = request.data
    sources = {item["id"]: item for item in data["evidence"]}
    ids = [item["id"] for item in payload["candidates"]]
    if len(ids) != len(set(ids)):
        raise AIError("Duplicate AI candidate identity.")

    def refs(values):
        if (
            len(values) != len(set(values))
            or not set(values) <= sources.keys()
        ):
            raise AIError(
                "AI output references missing or duplicate Evidence."
            )

    refs(payload["evidence_references"])
    used = set()
    for candidate in payload["candidates"]:
        refs(candidate["evidence_ids"])
        used.update(candidate["evidence_ids"])
        quoted = set()
        for quote in candidate["supporting_quotes"]:
            key = quote["evidence_id"]
            if key not in candidate["evidence_ids"] or (
                quote["quote"] not in sources[key]["extracted"]["text"]
            ):
                raise AIError(
                    "AI supporting quote differs from source Evidence."
                )
            quoted.add(key)
        if quoted != set(candidate["evidence_ids"]):
            raise AIError("Each AI source requires an exact supporting quote.")
        value = parse(candidate["value_json"])
        _no_authority(value)
        kind = candidate["kind"]
        path = candidate["target_path"]
        if kind == "IR_VALUE":
            if path not in data["targets"]:
                raise AIError("AI output targets an unrequested IR field.")
            schema, _ = target_schema(path)
            if not fragment_valid(value, schema):
                raise AIError(
                    "AI value differs from the trusted IR field schema."
                )

            # Nested provenance must belong to the requested sources.
            def nested(node, allowed=tuple(candidate["evidence_ids"])):
                if isinstance(node, dict):
                    if "evidence_ids" in node:
                        refs(node["evidence_ids"])
                        if not set(node["evidence_ids"]) <= set(allowed):
                            raise AIError("AI value has unrelated provenance.")
                    for child in node.values():
                        nested(child)
                elif isinstance(node, list):
                    for child in node:
                        nested(child)

            nested(value)
        elif path is not None:
            raise AIError("Evidence-only candidates cannot target IR fields.")
        elif kind == "PACKAGE":
            schema = obj({"part_number": STRING, "package": STRING})
            if (
                data["task"] != "identify_package"
                or not Draft202012Validator(schema).is_valid(value)
                or value["part_number"] != data["part_number"]
            ):
                raise AIError(
                    "AI package candidate differs from the full order number."
                )
            if not any(
                _contains_order_number(quote["quote"], data["part_number"])
                for quote in candidate["supporting_quotes"]
            ):
                if candidate["status"] != "CONFLICTING":
                    candidate["status"] = "UNKNOWN"
                message = (
                    "Full order number is absent from cited source quotes; "
                    "package interpretation remains unresolved."
                )
                if not any(
                    issue["message"] == message
                    and candidate["id"] in issue["candidate_ids"]
                    for issue in payload["ambiguities"]
                ):
                    payload["ambiguities"].append(
                        {
                            "message": message,
                            "candidate_ids": [candidate["id"]],
                            "evidence_ids": candidate["evidence_ids"],
                        }
                    )
        elif kind == "TRANSLATION":
            schema = obj(
                {
                    "translated_text": STRING,
                    "source_language": STRING,
                    "target_language": STRING,
                }
            )
            if (
                data["task"] != "translate_technical_text"
                or len(candidate["evidence_ids"]) != 1
                or not Draft202012Validator(schema).is_valid(value)
                or value["target_language"] != data["target_language"]
                or value["source_language"] not in ("en", "de", "zh-Hans")
            ):
                raise AIError("Invalid AI translation candidate.")
        elif (
            data["task"] not in ("explain_ambiguity", "classify_conflict")
            or not isinstance(value, str)
            or not value.strip()
        ):
            raise AIError("Invalid AI explanation candidate.")
        candidate["value_json"] = canonical_json(value).decode("utf-8")
    for field in ("ambiguities", "conflicts"):
        for issue in payload[field]:
            refs(issue["evidence_ids"])
            if (
                not set(issue["candidate_ids"]) <= set(ids)
                or not issue["evidence_ids"]
            ):
                raise AIError(
                    "AI issue has missing candidate or Evidence references."
                )
            used.update(issue["evidence_ids"])
    # The inventory may also retain consulted source records (for example,
    # ordering tables searched when the required part number is absent).
    if not used <= set(payload["evidence_references"]):
        raise AIError(
            "AI reference inventory omits candidate or issue sources."
        )
    # Independently surface disagreements, even if the provider omits them.
    groups = {}
    for item in payload["candidates"]:
        key = item["target_path"] or item["kind"]
        if item["kind"] == "TRANSLATION":
            key += ":" + item["evidence_ids"][0]
        groups.setdefault(key, []).append(item)
    for items in groups.values():
        if len({item["value_json"] for item in items}) > 1 and not any(
            set(issue["candidate_ids"]) == {item["id"] for item in items}
            for issue in payload["conflicts"]
        ):
            payload["conflicts"].append(
                {
                    "message": (
                        "Candidate values disagree; human resolution required."
                    ),
                    "candidate_ids": [item["id"] for item in items],
                    "evidence_ids": sorted(
                        {key for item in items for key in item["evidence_ids"]}
                    ),
                }
            )
    for field, status in (
        ("ambiguities", "AMBIGUOUS"),
        ("conflicts", "CONFLICTING"),
    ):
        affected = {
            key for issue in payload[field] for key in issue["candidate_ids"]
        }
        for item in payload["candidates"]:
            if item["id"] in affected:
                if status == "CONFLICTING" or item["status"] not in {
                    "UNKNOWN",
                    "CONFLICTING",
                }:
                    item["status"] = status
    if (
        not payload["candidates"]
        and not payload["ambiguities"]
        and not payload["conflicts"]
    ):
        # A well-formed empty provider result cannot silently resolve the task.
        # Retain an adapter-authored unresolved issue, without inventing facts.
        references = payload["evidence_references"] or sorted(sources)
        payload["evidence_references"] = references
        payload["ambiguities"].append(
            {
                "message": (
                    "Provider returned no candidates; "
                    "interpretation remains unresolved."
                ),
                "candidate_ids": [],
                "evidence_ids": references,
            }
        )
        payload["confidence"] = 0
    for item in payload["candidates"]:
        if item["status"] in (
            "UNKNOWN",
            "AMBIGUOUS",
            "CONFLICTING",
        ) and not any(
            item["id"] in issue["candidate_ids"]
            for issue in payload["ambiguities"] + payload["conflicts"]
        ):
            field = (
                "conflicts"
                if item["status"] == "CONFLICTING"
                else "ambiguities"
            )
            payload[field].append(
                {
                    "message": item["rationale"],
                    "candidate_ids": [item["id"]],
                    "evidence_ids": item["evidence_ids"],
                }
            )
    return payload
