"""Tests for Sabda Message Bus."""

import logging
from enum import Enum
import pytest

from src.sabda.models import SabdaMessage, WayangResult, WayangStatus
from src.sabda.bus import SabdaBus


# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)


class TestSabdaMessage:
    """Tests for SabdaMessage model."""

    def test_sabda_message_creation(self):
        """Test basic message creation with required fields."""
        msg = SabdaMessage(
            sender="dhalang",
            receiver="wayang-coder",
            task_type="code_generation",
            payload={"prompt": "write hello world"},
        )

        assert msg.sender == "dhalang"
        assert msg.receiver == "wayang-coder"
        assert msg.task_type == "code_generation"
        assert msg.payload == {"prompt": "write hello world"}
        assert msg.reply_to is None
        assert msg.timestamp is not None

    def test_sabda_message_with_reply_to(self):
        """Test message with reply_to field."""
        msg = SabdaMessage(
            sender="wayang-coder",
            receiver="dhalang",
            task_type="code_result",
            payload={"code": "print('hello')"},
            reply_to="original-task-123",
        )

        assert msg.reply_to == "original-task-123"

    def test_payload_default_factory(self):
        """Test payload uses default_factory, not mutable default."""
        msg1 = SabdaMessage(sender="a", receiver="b", task_type="t1")
        msg2 = SabdaMessage(sender="a", receiver="b", task_type="t2")

        # Modify payload of msg1
        msg1.payload["key"] = "value"

        # msg2 should not be affected
        assert msg2.payload == {}

    def test_sabda_message_immutable(self):
        """Test SabdaMessage is frozen (immutable)."""
        msg = SabdaMessage(sender="a", receiver="b", task_type="t")
        with pytest.raises(Exception):
            msg.sender = "changed"


class TestWayangResult:
    """Tests for WayangResult model."""

    def test_wayang_result_creation(self):
        """Test basic result creation."""
        result = WayangResult(
            agent="wayang-coder",
            status=WayangStatus.COMPLETED,
            result={"code": "print('hello')"},
        )

        assert result.agent == "wayang-coder"
        assert result.status == WayangStatus.COMPLETED
        assert result.result == {"code": "print('hello')"}
        assert result.notes is None

    def test_wayang_status_enum(self):
        """Test WayangStatus is an enum with correct values."""
        assert WayangStatus.COMPLETED == "COMPLETED"
        assert WayangStatus.FAILED == "FAILED"
        assert WayangStatus.NEED_MORE_INFO == "NEED_MORE_INFO"

    def test_wayang_status_is_enum(self):
        """Test WayangStatus is actually an Enum, not string."""
        assert isinstance(WayangStatus.COMPLETED, Enum)
        assert WayangStatus.COMPLETED.value == "COMPLETED"

    def test_result_default_factory(self):
        """Test result uses default_factory, not mutable default."""
        r1 = WayangResult(agent="a", status=WayangStatus.COMPLETED)
        r2 = WayangResult(agent="b", status=WayangStatus.COMPLETED)

        r1.result["key"] = "value"
        assert r2.result == {}

    def test_wayang_result_with_notes(self):
        """Test result with optional notes."""
        result = WayangResult(
            agent="wayang-security",
            status=WayangStatus.FAILED,
            result={},
            notes="Invalid input",
        )

        assert result.notes == "Invalid input"

    def test_wayang_result_immutable(self):
        """Test WayangResult is frozen (immutable)."""
        result = WayangResult(agent="a", status=WayangStatus.COMPLETED)
        with pytest.raises(Exception):
            result.agent = "changed"


class TestSabdaBus:
    """Tests for SabdaBus message bus."""

    def test_publish_and_get_next_single_message(self):
        """Test publish then get_next returns the message."""
        bus = SabdaBus()

        msg = SabdaMessage(
            sender="dhalang",
            receiver="wayang-coder",
            task_type="code_gen",
            payload={"prompt": "test"},
        )

        bus.publish(msg)
        received = bus.get_next("wayang-coder")

        assert received is not None
        assert received.sender == "dhalang"
        assert received.receiver == "wayang-coder"
        assert received.task_type == "code_gen"
        assert received.payload == {"prompt": "test"}

    def test_fifo_order_per_receiver(self):
        """Test messages are delivered in FIFO order per receiver."""
        bus = SabdaBus()

        # Publish multiple messages for same receiver
        for i in range(5):
            bus.publish(
                SabdaMessage(
                    sender="dhalang",
                    receiver="wayang-coder",
                    task_type=f"task_{i}",
                    payload={"seq": i},
                )
            )

        # Get messages - should be in order
        for i in range(5):
            received = bus.get_next("wayang-coder")
            assert received is not None
            assert received.task_type == f"task_{i}"
            assert received.payload == {"seq": i}

        # Queue should be empty now
        assert bus.get_next("wayang-coder") is None

    def test_separate_queues_per_receiver(self):
        """Test different receivers have independent queues."""
        bus = SabdaBus()

        bus.publish(SabdaMessage(sender="d", receiver="wayang-a", task_type="t1", payload={"v": 1}))
        bus.publish(SabdaMessage(sender="d", receiver="wayang-b", task_type="t2", payload={"v": 2}))
        bus.publish(SabdaMessage(sender="d", receiver="wayang-a", task_type="t3", payload={"v": 3}))

        # wayang-a should get t1 then t3
        a1 = bus.get_next("wayang-a")
        assert a1 is not None
        assert a1.task_type == "t1"

        a2 = bus.get_next("wayang-a")
        assert a2 is not None
        assert a2.task_type == "t3"

        # wayang-b should get t2
        b1 = bus.get_next("wayang-b")
        assert b1 is not None
        assert b1.task_type == "t2"

    def test_get_next_empty_queue_returns_none(self):
        """Test get_next returns None for empty queue."""
        bus = SabdaBus()
        result = bus.get_next("nonexistent")
        assert result is None

    def test_publish_logs_message(self, caplog):
        """Test publish logs the message details."""
        bus = SabdaBus()

        with caplog.at_level(logging.INFO):
            bus.publish(
                SabdaMessage(
                    sender="test-sender",
                    receiver="test-receiver",
                    task_type="test-task",
                )
            )

        assert "PUBLISH" in caplog.text
        assert "test-sender" in caplog.text
        assert "test-receiver" in caplog.text
        assert "test-task" in caplog.text

    def test_get_next_logs_message(self, caplog):
        """Test get_next logs the retrieved message."""
        bus = SabdaBus()

        bus.publish(
            SabdaMessage(
                sender="test-sender",
                receiver="test-receiver",
                task_type="test-task",
            )
        )

        with caplog.at_level(logging.INFO):
            bus.get_next("test-receiver")

        assert "GET_NEXT" in caplog.text
        assert "test-receiver" in caplog.text
        assert "test-sender" in caplog.text
        assert "test-task" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])