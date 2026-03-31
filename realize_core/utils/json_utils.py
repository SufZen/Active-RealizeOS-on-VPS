"""Shared JSON parsing utilities for LLM responses."""

import json
import re


def parse_json_response(text: str) -> dict | None:
    """
    Extract JSON from an LLM response.

    Handles:
    - Plain JSON
    - JSON wrapped in markdown code fences
    - JSON embedded in surrounding text
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None
