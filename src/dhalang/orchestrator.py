"""Dhalang orchestrator - coordinates Wayang agents."""

import logging
import re
from typing import Optional

from src.sabda.bus import SabdaBus
from src.sabda.models import SabdaMessage, WayangResult, WayangStatus
from src.wayang.coder_wayang import CoderWayang
from src.wayang.sec_wayang import SecWayang
from src.dhalang.aggregator import Manunggal

logger = logging.getLogger(__name__)


class Dhalang:
    """Orchestrator that delegates tasks to Wayang agents and aggregates results."""

    def __init__(self) -> None:
        """Initialize Dhalang with bus and registered Wayang agents."""
        self.bus = SabdaBus()
        self.registered_wayangs: dict[str, object] = {}

        # Register default Wayang agents
        self.register_wayang(CoderWayang(self.bus))
        self.register_wayang(SecWayang(self.bus))

        self.manunggal = Manunggal()

    def register_wayang(self, wayang) -> None:
        """Register a Wayang agent.

        Args:
            wayang: Wayang instance with agent_id attribute.
        """
        self.registered_wayangs[wayang.agent_id] = wayang
        logger.info("[DHALANG] Registered wayang: %s", wayang.agent_id)

    def analisis_input(self, user_input: str) -> tuple[str, str, dict]:
        """Analyze user input to determine target Wayang, task type, and payload.

        Args:
            user_input: Raw user input string.

        Returns:
            Tuple of (target_wayang_id, task_type, payload).
        """
        input_lower = user_input.lower()

        # Security-related keywords
        if any(kw in input_lower for kw in ("scan", "subdomain", "security", "audit")):
            # Extract domain from input
            domain_match = re.search(r'(?:target\.|domain\s+|for\s+|scan\s+)([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', input_lower)
            target = domain_match.group(1) if domain_match else "target.com"
            return ("sec_wayang", "scan_subdomain", {"target": target})

        # Code-related keywords
        if any(kw in input_lower for kw in ("code", "bug", "analyze", "function")):
            # Extract file from input
            file_match = re.search(r'(?:file\s+|code\s+|in\s+)([a-zA-Z0-9._/-]+\.py)', input_lower)
            file_path = file_match.group(1) if file_match else "auth.py"
            return ("coder_wayang", "analyze_code", {"file": file_path})

        # Default to security scan
        return ("sec_wayang", "scan_subdomain", {"target": "target.com"})

    def delegasi(self, target_wayang_id: str, task_type: str, payload: dict) -> None:
        """Publish a task to the target Wayang via Sabda bus.

        Args:
            target_wayang_id: The agent_id of the target Wayang.
            task_type: Type of task to execute.
            payload: Task payload data.
        """
        message = SabdaMessage(
            sender="dhalang",
            receiver=target_wayang_id,
            task_type=task_type,
            payload=payload,
            reply_to="dhalang"
        )
        self.bus.publish(message)
        logger.info("[DHALANG] -> [%s] delegasi: task_type=%s", target_wayang_id, task_type)

    def tunggu_hasil(self) -> Optional[WayangResult]:
        """Wait for and parse result from Wayang via Sabda bus.

        Returns:
            WayangResult if message received, None otherwise.
        """
        message = self.bus.get_next("dhalang")
        if message is None:
            logger.info("[DHALANG] Tidak ada balasan dari Wayang")
            return None

        logger.info("[DHALANG] <- [%s] terima balasan", message.sender)

        # Parse payload to WayangResult
        try:
            status_str = message.payload.get("status", "completed").lower()
            status_map = {
                "completed": WayangStatus.COMPLETED,
                "failed": WayangStatus.FAILED,
                "need_more_info": WayangStatus.NEED_MORE_INFO,
            }
            status = status_map.get(status_str, WayangStatus.COMPLETED)

            return WayangResult(
                agent=message.sender,
                status=status,
                result=message.payload.get("result", {}),
                notes=message.payload.get("notes")
            )
        except Exception as e:
            logger.error("[DHALANG] Gagal parse balasan: %s", e)
            return None

    def proses(self, user_input: str) -> str:
        """Process user input through full orchestration pipeline.

        Args:
            user_input: Raw user input string.

        Returns:
            Final aggregated answer string.
        """
        logger.info("[DHALANG] Memproses input: %s", user_input)

        # Step 1: Analyze input
        target_wayang_id, task_type, payload = self.analisis_input(user_input)

        # Step 2: Delegate to Wayang
        self.delegasi(target_wayang_id, task_type, payload)

        # Step 3: Run the target Wayang to process the message
        wayang = self.registered_wayangs.get(target_wayang_id)
        if wayang and hasattr(wayang, 'jalankan'):
            wayang.jalankan()

        # Step 4: Wait for result
        result = self.tunggu_hasil()

        # Step 5: Aggregate via Manunggal
        results = [result] if result else []
        final_answer = self.manunggal.satukan(results, user_input)

        return final_answer