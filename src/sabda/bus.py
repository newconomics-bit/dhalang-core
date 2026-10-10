"""In-memory message bus for Sabda."""

import logging
from collections import defaultdict, deque
from threading import Lock
from typing import Optional

from .models import SabdaMessage

logger = logging.getLogger(__name__)


class SabdaBus:
    """In-memory message bus with per-receiver queues.

    Uses FIFO queues per receiver to ensure message ordering.
    Thread-safe with internal locking.
    """

    def __init__(self) -> None:
        self._queues: dict[str, deque[SabdaMessage]] = defaultdict(deque)
        self._lock = Lock()

    def publish(self, message: SabdaMessage) -> None:
        """Publish a message to the receiver's queue.

        Args:
            message: The SabdaMessage to publish.
        """
        with self._lock:
            self._queues[message.receiver].append(message)
            logger.info(
                "PUBLISH | sender=%s receiver=%s task_type=%s reply_to=%s",
                message.sender,
                message.receiver,
                message.task_type,
                message.reply_to or "none",
            )

    def get_next(self, receiver: str) -> Optional[SabdaMessage]:
        """Get the next message for a receiver (FIFO).

        Args:
            receiver: The receiver identifier.

        Returns:
            The next SabdaMessage for the receiver, or None if queue is empty.
        """
        with self._lock:
            queue = self._queues.get(receiver)
            if queue and queue:
                message = queue.popleft()
                logger.info(
                    "GET_NEXT | receiver=%s sender=%s task_type=%s",
                    receiver,
                    message.sender,
                    message.task_type,
                )
                return message
            logger.info("GET_NEXT | receiver=%s queue_empty", receiver)
            return None