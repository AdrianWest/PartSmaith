"""Attach explicit supporting translations without replacing source text."""

from copy import deepcopy
from datetime import datetime


def attach_translation(evidence, translation):
    fields = {
        "original_text",
        "translated_text",
        "source_language",
        "target_language",
        "provider",
        "model",
        "timestamp",
    }
    if set(translation) != fields or not all(
        isinstance(value, str) and value.strip()
        for value in translation.values()
    ):
        raise ValueError("Translation requires explicit text and provenance.")
    if translation["original_text"] != evidence["extracted"]["text"]:
        raise ValueError(
            "Translation original text differs from retained source."
        )
    if (
        translation["provider"] == "manual"
        and translation["model"] != "not_applicable"
    ):
        raise ValueError("Manual translation model must be not_applicable.")
    try:
        stamp = datetime.fromisoformat(
            translation["timestamp"].replace("Z", "+00:00")
        )
        if stamp.tzinfo is None:
            raise ValueError()
    except ValueError:
        raise ValueError(
            "Translation timestamp requires a timezone."
        ) from None
    result = deepcopy(evidence)
    result["translation"] = deepcopy(translation)
    return result
