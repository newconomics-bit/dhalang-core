"""LLM response parsing utilities."""

import json
import logging
import re
from typing import Any, Optional

from src.sabda.models import WayangResult, WayangStatus

logger = logging.getLogger(__name__)


def parse_llm_response(
    response_text: str,
    agent_id: str,
) -> WayangResult:
    """Parse LLM response text into WayangResult with fallback strategies.

    Args:
        response_text: Raw response text from LLM.
        agent_id: Agent identifier for the result.

    Returns:
        WayangResult with parsed data or error status.
    """
    # Strategy (a): Try direct JSON parse
    try:
        response_data = json.loads(response_text)
        return _build_result(agent_id, response_data)
    except json.JSONDecodeError:
        pass

    # Strategy (b): Strip markdown fences (```json ... ```)
    cleaned = _strip_markdown_fences(response_text)
    if cleaned != response_text:
        try:
            response_data = json.loads(cleaned)
            return _build_result(agent_id, response_data)
        except json.JSONDecodeError:
            pass

    # Strategy (c): Extract first JSON object with regex
    extracted = _extract_first_json_object(response_text)
    if extracted:
        try:
            response_data = json.loads(extracted)
            return _build_result(agent_id, response_data)
        except json.JSONDecodeError:
            pass

    # Strategy (d): All failed - return FAILED result
    preview = response_text[:200].replace("\n", " ")
    logger.warning("LLM returned unparseable output: %s", preview)
    return WayangResult(
        agent=agent_id,
        status=WayangStatus.FAILED,
        result={},
        notes=f"LLM returned unparseable output: {preview}"
    )


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from text."""
    # Remove ```json ... ``` or ``` ... ```
    pattern = r"^```(?:json)?\s*(.*?)\s*```$"
    match = re.search(pattern, text.strip(), re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _extract_first_json_object(text: str) -> Optional[str]:
    """Extract the first JSON object from text using regex."""
    # Find first { ... } balanced object
    # Simple approach: find first { and matching }
    brace_count = 0
    start_idx = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif ch == "}":
            if brace_count > 0:
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    return text[start_idx:i+1]
    return None


def _build_result(agent_id: str, response_data: dict) -> WayangResult:
    """Build WayangResult from parsed response data."""
    status_str = response_data.get("status", "completed").lower()
    status_map = {
        "completed": WayangStatus.COMPLETED,
        "failed": WayangStatus.FAILED,
        "need_more_info": WayangStatus.NEED_MORE_INFO,
    }
    status = status_map.get(status_str, WayangStatus.COMPLETED)

    return WayangResult(
        agent=agent_id,
        status=status,
        result=response_data.get("result", {}),
        notes=response_data.get("notes")
    )