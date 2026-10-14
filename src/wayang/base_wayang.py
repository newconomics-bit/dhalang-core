"""Base Wayang agent class."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.sabda.models import SabdaMessage, WayangResult, WayangStatus
from src.sabda.bus import SabdaBus
from src.llm.interfaces import LLMBackend
from src.llm.mock_backend import mock_respond

logger = logging.getLogger(__name__)


class Wayang(ABC):
    """Abstract base class for Wayang agents."""

    def __init__(self, agent_id: str, bus: SabdaBus, backend: Optional[LLMBackend] = None) -> None:
        """Initialize Wayang agent.

        Args:
            agent_id: Unique identifier for this agent.
            bus: SabdaBus instance for message communication.
            backend: Optional LLM backend. If None, falls back to mock_respond.
        """
        self.agent_id = agent_id
        self.bus = bus
        self.peers: dict[str, "Wayang"] = {}
        self.backend = backend

    def terima_sabda(self) -> Optional[SabdaMessage]:
        """Receive next message from bus for this agent.

        Returns:
            SabdaMessage if available, None if queue is empty.
        """
        return self.bus.get_next(self.agent_id)

    def gunakan_tool(self, task_type: str, payload: dict) -> WayangResult:
        """Execute task using LLM backend (or mock fallback) and parse result.

        Args:
            task_type: Type of task to execute.
            payload: Task payload data.

        Returns:
            WayangResult with parsed response.
        """
        # Build prompt from task_type and payload
        prompt = f"{task_type} {json.dumps(payload)}"

        # Call LLM backend or mock fallback
        if self.backend is not None:
            response_json = self.backend.respond(prompt)
        else:
            response_json = mock_respond(prompt)

        # Parse JSON response
        try:
            response_data = json.loads(response_json)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse mock response: %s", e)
            return WayangResult(
                agent=self.agent_id,
                status=WayangStatus.FAILED,
                result={},
                notes=f"JSON parse error: {e}"
            )

        # Map status string to enum
        status_str = response_data.get("status", "completed").lower()
        status_map = {
            "completed": WayangStatus.COMPLETED,
            "failed": WayangStatus.FAILED,
            "need_more_info": WayangStatus.NEED_MORE_INFO,
        }
        status = status_map.get(status_str, WayangStatus.COMPLETED)

        return WayangResult(
            agent=self.agent_id,
            status=status,
            result=response_data.get("result", {}),
            notes=response_data.get("notes")
        )

    def kirim_balasan(self, result: WayangResult, reply_to: str) -> None:
        """Send result back to requester via bus.

        Args:
            result: WayangResult to send.
            reply_to: The original sender's agent_id (from SabdaMessage.reply_to).
        """
        if not reply_to:
            logger.warning("No reply_to specified, cannot send response")
            return

        # Create response message
        response = SabdaMessage(
            sender=self.agent_id,
            receiver=reply_to,
            task_type="result",
            payload={
                "status": result.status.value,
                "result": result.result,
            },
            reply_to=reply_to
        )

        # Add notes to payload if present
        if result.notes:
            response.payload["notes"] = result.notes

        self.bus.publish(response)
        logger.info("[%s] -> [%s] balasan terkirim", self.agent_id, reply_to)

    def jalankan(self) -> None:
        """Main loop: receive messages, process, send responses.

        Continues until no more messages in queue.
        """
        logger.info("[%s] memulai loop", self.agent_id)

        while True:
            message = self.terima_sabda()
            if message is None:
                logger.info("[%s] antrian kosong, berhenti", self.agent_id)
                break

            logger.info(
                "[%s] <- [%s] terima: task_type=%s",
                self.agent_id,
                message.sender,
                message.task_type
            )

            result = self.gunakan_tool(message.task_type, message.payload)
            self.kirim_balasan(result, message.reply_to or message.sender)

    def delegasi_ke(self, target_id: str, task_type: str, payload: dict):
        """Delegate a task to another Wayang agent via Sabda bus.

        Args:
            target_id: The agent_id of the target Wayang.
            task_type: Type of task to execute.
            payload: Task payload data.

        Returns:
            WayangResult from the target agent, or None if no response.
        """
        # Publish SabdaMessage via bus (respecting protocol)
        message = SabdaMessage(
            sender=self.agent_id,
            receiver=target_id,
            task_type=task_type,
            payload=payload,
            reply_to=self.agent_id
        )
        self.bus.publish(message)
        logger.info("[%s] -> [%s] delegasi: task_type=%s", self.agent_id, target_id, task_type)

        # NOTE: sinkron peer-drain, diganti async runner di fase real-LLM
        target_wayang = self.peers.get(target_id)
        if target_wayang:
            target_wayang.jalankan()

        # Wait for response from target via our own queue
        response = self.bus.get_next(self.agent_id)
        if response is None:
            logger.info("[%s] <- [%s] tidak ada balasan", self.agent_id, target_id)
            return None

        logger.info("[%s] <- [%s] terima balasan", self.agent_id, response.sender)

        # Parse payload to WayangResult
        try:
            status_str = response.payload.get("status", "completed").lower()
            status_map = {
                "completed": WayangStatus.COMPLETED,
                "failed": WayangStatus.FAILED,
                "need_more_info": WayangStatus.NEED_MORE_INFO,
            }
            status = status_map.get(status_str, WayangStatus.COMPLETED)

            return WayangResult(
                agent=response.sender,
                status=status,
                result=response.payload.get("result", {}),
                notes=response.payload.get("notes")
            )
        except Exception as e:
            logger.error("[%s] Gagal parse balasan dari [%s]: %s", self.agent_id, target_id, e)
            return None
