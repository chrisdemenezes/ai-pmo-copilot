import json
import re

_CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_structured_output(raw_output: str) -> dict:
    """Parse a JSON object from raw LLM output, tolerating markdown code fences.

    Falls back to {"structured": False, "raw_output": ...} instead of raising,
    since a model response that doesn't follow the requested JSON schema must
    not crash the calling agent.
    """
    candidate = raw_output.strip()
    fence_match = _CODE_FENCE_PATTERN.match(candidate)
    if fence_match:
        candidate = fence_match.group(1)

    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return {"structured": False, "raw_output": raw_output}

    if not isinstance(parsed, dict):
        return {"structured": False, "raw_output": raw_output}

    return {"structured": True, **parsed}
