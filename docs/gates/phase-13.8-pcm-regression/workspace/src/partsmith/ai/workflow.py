"""Convert candidates into unreviewed Evidence without approval authority."""

from copy import deepcopy

from partsmith.ir.schema import fragment_valid

from .contracts import digest, normalize, parse
from .errors import AIError


def candidate_evidence(request, result):
    """Retain source records and links; interpretation never mutates the IR."""
    data = result.data
    if (
        data["input_hash"] != request.input_hash
        or data["review_state"] != "UNREVIEWED"
    ):
        raise AIError("AI result differs from its unreviewed request binding.")
    fields = (
        "schema_version",
        "candidates",
        "evidence_references",
        "ambiguities",
        "conflicts",
        "confidence",
    )
    payload = {key: data[key] for key in fields}
    normalized = normalize(payload, request)
    # normalize can add independently detected issues; verify retained output.
    if digest(payload) != data["output_hash"] or normalized != payload:
        raise AIError(
            "AI result output hash differs from retained candidates."
        )
    sources = {item["id"]: item for item in request.data["evidence"]}
    evidence = []
    for candidate in normalized["candidates"]:
        item = deepcopy(sources[candidate["evidence_ids"][0]])
        value = parse(candidate["value_json"])
        item["id"] = "ev-ai-" + digest(
            {"request": data["request_id"], "candidate": candidate}
        )
        item["type"] = "AI_INTERPRETATION"
        item["interpretation"] = {
            "normalized_value": candidate["value_json"],
            "status": candidate["status"],
            "evidence_ids": candidate["evidence_ids"],
            "derivation": (
                f"{data['provider']}/{data['model']} "
                f"request {data['request_id']} "
                f"at {data['timestamp']}; input {data['input_hash']}; "
                f"output {data['output_hash']}; {candidate['rationale']}"
            ),
        }
        item["extractor"] = {
            "method": data["provider"],
            "version": data["model"],
        }
        item["confidence"] = {
            "score": candidate["confidence"],
            "basis": "AI advisory confidence; unreviewed",
        }
        item["candidate_targets"] = (
            [candidate["target_path"]] if candidate["target_path"] else []
        )
        if candidate["kind"] == "TRANSLATION":
            item["translation"] = {
                "original_text": item["extracted"]["text"],
                **value,
                "provider": data["provider"],
                "model": data["model"],
                "timestamp": data["timestamp"],
            }
        if not fragment_valid(item, {"$ref": "#/$defs/evidence"}):
            raise AIError(
                "AI candidate cannot be represented as IR 1.2 Evidence."
            )
        evidence.append(item)
    return {
        "schema_version": "ai-candidate-bundle-1.0",
        "review_state": "UNREVIEWED",
        "request": request.data,
        "result": data,
        "source_evidence": list(sources.values()),
        "candidate_evidence": evidence,
    }
