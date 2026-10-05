"""Offline reuse of immutable, validated AI candidates; no credentials."""

from dataclasses import dataclass

from partsmith.ir import canonical_json

from .contracts import AIResult, digest
from .errors import AIError
from .openai import ProviderConfig
from .workflow import candidate_evidence


@dataclass(frozen=True, repr=False)
class RecordedProvider:
    """Replay the original result envelope without a new inference claim."""

    result: AIResult

    def analyze(self, request):
        data = self.result.data
        expected = ProviderConfig().engineering_inputs
        if (
            data["engineering_inputs"] != expected
            or data["provider"] != expected["provider"]
            or data["model"] != expected["model"]
        ):
            raise AIError(
                "Recorded provider version differs from this adapter."
            )
        key = digest({"input_hash": request.input_hash, **expected})
        if data["cache_key"] != key:
            raise AIError(
                "Recorded provider result has a different cache binding."
            )
        candidate_evidence(request, self.result)
        return AIResult(canonical_json(data))
