"""Independent review probes; no network or real credentials."""

import json
from decimal import Decimal
from pathlib import Path

from test_ai import FakeTransport, package_payload, response

from partsmith.ai import AIRequest, OpenAIProvider, candidate_evidence
from partsmith.ai.contracts import normalize

ROOT = Path(__file__).resolve().parents[1]


def source():
    item = json.loads(
        (ROOT / "fixtures/ir/v1.2/valid/0402.json").read_text("utf-8")
    )["evidence"][0]
    item["extracted"]["text"] = (
        "Order number TEST-QFN-16R; Package QFN-16. Width 3 mm."
    )
    item["interpretation"] = {"normalized_value": None, "status": "UNKNOWN"}
    return item


def test_missing_full_order_number_cannot_be_inferred():
    request = AIRequest.create(
        "identify_package", "ABSENT-TSSOP-28R", [source()]
    )
    payload = package_payload(request)
    payload["candidates"][0]["value_json"] = json.dumps(
        {"part_number": "ABSENT-TSSOP-28R", "package": "TSSOP-28"}
    )
    normalized = normalize(payload, request)
    assert not any(
        c["status"] == "INFERRED" for c in normalized["candidates"]
    ), (
        "An absent order number was accepted as an inferred package "
        "without an issue"
    )
    assert normalized["ambiguities"] or normalized["conflicts"]


def test_exact_request_binding_survives_provider_validation():
    item = source()
    item["extracted"]["value"] = Decimal("0.9876543210987654321")
    request = AIRequest.create("identify_package", "TEST-QFN-16R", [item])
    provider = OpenAIProvider(
        lambda: "dummy-review-key",
        transport=FakeTransport(response(package_payload(request))),
    )
    result = provider.analyze(request)
    assert result.data["input_hash"] == request.input_hash, (
        "Provider revalidation changed the immutable request hash"
    )
    candidate_evidence(request, result)
