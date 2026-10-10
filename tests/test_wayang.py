"""Integration tests for Wayang agents."""

import logging
import pytest

from src.sabda.bus import SabdaBus
from src.sabda.models import SabdaMessage, WayangResult, WayangStatus
from src.wayang.coder_wayang import CoderWayang
from src.wayang.sec_wayang import SecWayang


# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)


class TestSecWayangIntegration:
    """Integration tests for SecWayang."""

    def test_sec_wayang_scan_subdomain(self):
        """Test SecWayang handles scan_subdomain task and returns result to dhalang."""
        bus = SabdaBus()

        # Dhalang publishes task to sec_wayang
        task = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="scan_subdomain",
            payload={"target": "target.com"},
            reply_to="dhalang"
        )
        bus.publish(task)

        # Instantiate SecWayang and run
        sec_wayang = SecWayang(bus)
        sec_wayang.jalankan()

        # Dhalang receives response
        response = bus.get_next("dhalang")

        assert response is not None
        assert response.sender == "sec_wayang"
        assert response.receiver == "dhalang"
        assert response.task_type == "result"

        # Parse payload as WayangResult
        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.agent == "sec_wayang"
        assert result.status == WayangStatus.COMPLETED
        assert "subdomains" in result.result
        assert len(result.result["subdomains"]) == 2
        assert "api.target.com" in result.result["subdomains"]
        assert "dev.target.com" in result.result["subdomains"]
        assert result.result["vulnerabilities"] == 2
        assert result.notes == "mock security scan"


class TestCoderWayangIntegration:
    """Integration tests for CoderWayang."""

    def test_coder_wayang_analyze_code(self):
        """Test CoderWayang handles analyze_code task and returns result to dhalang."""
        bus = SabdaBus()

        # Dhalang publishes task to coder_wayang
        task = SabdaMessage(
            sender="dhalang",
            receiver="coder_wayang",
            task_type="analyze_code",
            payload={"file": "auth.py"},
            reply_to="dhalang"
        )
        bus.publish(task)

        # Instantiate CoderWayang and run
        coder_wayang = CoderWayang(bus)
        coder_wayang.jalankan()

        # Dhalang receives response
        response = bus.get_next("dhalang")

        assert response is not None
        assert response.sender == "coder_wayang"
        assert response.receiver == "dhalang"
        assert response.task_type == "result"

        # Parse payload as WayangResult
        result = WayangResult(
            agent="coder_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.agent == "coder_wayang"
        assert result.status == WayangStatus.COMPLETED
        assert result.result["file"] == "auth.py"
        assert result.result["line"] == 45
        assert result.result["issue"] == "password not hashed"
        assert result.result["severity"] == "high"
        assert result.notes == "mock code analysis"


class TestWayangBaseFunctionality:
    """Tests for base Wayang functionality."""

    def test_terima_sabda_returns_none_when_empty(self):
        """Test terima_sabda returns None for empty queue."""
        bus = SabdaBus()
        sec_wayang = SecWayang(bus)

        result = sec_wayang.terima_sabda()
        assert result is None

    def test_gunakan_tool_returns_wayang_result(self):
        """Test gunakan_tool returns proper WayangResult."""
        bus = SabdaBus()
        sec_wayang = SecWayang(bus)

        result = sec_wayang.gunakan_tool("scan_subdomain", {"target": "example.com"})

        assert isinstance(result, WayangResult)
        assert result.agent == "sec_wayang"
        assert result.status == WayangStatus.COMPLETED
        assert "subdomains" in result.result

    def test_kirim_balasan_sends_to_reply_to(self):
        """Test kirim_balasan publishes to correct receiver."""
        bus = SabdaBus()
        sec_wayang = SecWayang(bus)

        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus.COMPLETED,
            result={"test": "data"},
            notes="test note"
        )

        sec_wayang.kirim_balasan(result, "dhalang")

        # Check message was published to dhalang
        response = bus.get_next("dhalang")
        assert response is not None
        assert response.sender == "sec_wayang"
        assert response.receiver == "dhalang"
        assert response.payload["result"]["test"] == "data"
        assert response.payload["notes"] == "test note"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])