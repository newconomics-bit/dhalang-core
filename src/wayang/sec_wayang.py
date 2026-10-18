"""Security Wayang agent - specializes in security scanning."""

import json
import logging
from typing import Optional

from src.sabda.bus import SabdaBus
from src.sabda.models import WayangResult, WayangStatus
from src.wayang.base_wayang import Wayang, build_prompt
from src.llm.interfaces import LLMBackend
from src.llm.mock_backend import mock_respond
from src.llm.parse import parse_llm_response

logger = logging.getLogger(__name__)


class SecWayang(Wayang):
    """Wayang agent specialized for security scanning tasks."""

    def __init__(self, bus: SabdaBus, backend=None) -> None:
        super().__init__(agent_id="sec_wayang", bus=bus, backend=backend)

    def gunakan_tool(self, task_type: str, payload: dict) -> WayangResult:
        """Execute task, with chain delegation for security_audit."""
        if task_type == "security_audit":
            # Chain delegation to coder_wayang for code analysis
            target = payload.get("file", "auth.py")
            coder_result = self.delegasi_ke("coder_wayang", "analyze_code", {"file": target})

            # Run our own security scan with structured prompt
            security_prompt = build_prompt("scan_subdomain", {"target": payload.get('target', 'target.com')})
            if self.backend is not None:
                security_json = self.backend.respond(security_prompt)
            else:
                security_json = mock_respond(security_prompt)
            security_result = parse_llm_response(security_json, self.agent_id)

            # Combine results
            combined_result = {
                "security": security_result.result if security_result else {},
                "code_analysis": coder_result.result if coder_result else {},
            }

            notes_parts = []
            if security_result and security_result.notes:
                notes_parts.append(f"Security: {security_result.notes}")
            if coder_result and coder_result.notes:
                notes_parts.append(f"Code: {coder_result.notes}")

            return WayangResult(
                agent=self.agent_id,
                status=WayangStatus.COMPLETED,
                result=combined_result,
                notes="; ".join(notes_parts) if notes_parts else "security audit with code analysis"
            )

        # Default behavior for other task types
        return super().gunakan_tool(task_type, payload)
