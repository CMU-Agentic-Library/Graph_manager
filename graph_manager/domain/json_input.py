"""Strict JSON parsing for model proposals."""

import json

from .models import ProposalValidationError, ValidationIssue
from .submission import USE_SUBMIT_TOOLS


def parse_json_object(raw_text: str) -> dict:
    """Parse one JSON object, rejecting duplicate keys and NaN or Infinity."""

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise ValueError(f"nonfinite JSON number: {token}")

    try:
        value = json.loads(
            raw_text, object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        message = f"{exc}. {USE_SUBMIT_TOOLS}"
        raise ProposalValidationError([ValidationIssue("$", "json_syntax", message)]) from exc
    if not isinstance(value, dict):
        raise ProposalValidationError(
            [ValidationIssue("$", "object_expected", "proposal must be a JSON object")]
        )
    return value
