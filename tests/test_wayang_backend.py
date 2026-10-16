"""Tests for Wayang backend injection and integration."""

import json
import pytest

from src.llm.interfaces import LLMBackend
from src.sabda.bus import SabdaBus
from src.sabda.models import SabdaMessage, WayangResult, WayangStatus
from src.wayang.coder_wayang import CoderWayang
from src.wayang.sec_wayang import SecWayang
from src.dhalang import Dhalang


class FakeBackend(LLMBackend):
    """Fake backend that returns controlled JSON responses for testing."""

    def __init__(self, response_data: dict = None):
        self.response_data = response_data or {
            "status": "completed",
            "result": {"marker": "fake"},
            "notes": "fake backend"
        }

    def respond(self, prompt: str) -> str:
        import json
        return json.dumps(self.response_data)


class TestWayangBackendInjection:
    """Tests for backend injection into Wayang agents."""

    def test_sec_wayang_with_injected_backend(self):
        """Test SecWayang uses injected backend instead of mock_respond."""
        bus = SabdaBus()
        fake_backend = FakeBackend({
            "status": "completed",
            "result": {"marker": "fake", "security": "test"},
            "notes": "injected backend test"
        })

        sec_wayang = SecWayang(bus, backend=fake_backend)

        # Verify backend was injected
        assert sec_wayang.backend is fake_backend

        # Send a message and process
        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="scan_subdomain",
            payload={"target": "test.com"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        # Get response
        response = bus.get_next("dhalang")
        assert response is not None

        # Parse result
        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        # Verify it used the fake backend (contains our marker)
        assert "marker" in result.result
        assert result.result["marker"] == "fake"
        assert result.notes == "injected backend test"

    def test_sec_wayang_without_backend_falls_back_to_mock(self):
        """Test SecWayang falls back to mock_respond when no backend injected."""
        bus = SabdaBus()

        # No backend injected
        sec_wayang = SecWayang(bus, backend=None)

        # Verify backend is None
        assert sec_wayang.backend is None

        # Send a message and process
        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="scan_subdomain",
            payload={"target": "test.com"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        # Get response
        response = bus.get_next("dhalang")
        assert response is not None

        # Parse result
        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        # Verify it used mock_respond (contains mock data)
        assert "subdomains" in result.result
        assert "api.target.com" in result.result["subdomains"]
        assert "dev.target.com" in result.result["subdomains"]
        assert result.notes == "mock security scan"

    def test_coder_wayang_with_injected_backend(self):
        """Test CoderWayang uses injected backend."""
        bus = SabdaBus()
        fake_backend = FakeBackend({
            "status": "completed",
            "result": {"marker": "fake", "file": "test.py"},
            "notes": "fake coder backend"
        })

        coder_wayang = CoderWayang(bus, backend=fake_backend)

        # Verify backend was injected
        assert coder_wayang.backend is fake_backend

        # Send a message and process
        msg = SabdaMessage(
            sender="dhalang",
            receiver="coder_wayang",
            task_type="analyze_code",
            payload={"file": "test.py"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        coder_wayang.jalankan()

        # Get response
        response = bus.get_next("dhalang")
        assert response is not None

        # Parse result
        result = WayangResult(
            agent="coder_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        # Verify it used the fake backend
        assert "marker" in result.result
        assert result.result["marker"] == "fake"
        assert result.notes == "fake coder backend"


class TestDhalangBackendIntegration:
    """Tests for Dhalang with injected backend end-to-end."""

    def test_dhalang_with_fake_backend_end_to_end(self):
        """Test Dhalang with injected fake backend processes end-to-end."""
        fake_backend = FakeBackend({
            "status": "completed",
            "result": {"marker": "fake", "end_to_end": True},
            "notes": "e2e fake backend"
        })

        dhalang = Dhalang(backend=fake_backend)

        # Verify backend is set
        assert dhalang.backend is fake_backend

        # Verify wayangs got the backend injected
        sec_wayang = dhalang.registered_wayangs["sec_wayang"]
        coder_wayang = dhalang.registered_wayangs["coder_wayang"]
        assert sec_wayang.backend is fake_backend
        assert coder_wayang.backend is fake_backend

        # Process a request
        result = dhalang.proses("Cek subdomain test.com")

        # Verify the fake backend was used (contains our marker)
        assert "marker" in result
        assert "fake" in result
        assert "end_to_end" in result

    def test_dhalang_default_backend_is_mock(self):
        """Test Dhalang without explicit backend uses mock (fallback)."""
        dhalang = Dhalang()

        # Should have a backend (mock)
        assert dhalang.backend is not None

        # Process a request - should work with mock
        result = dhalang.proses("Cek subdomain test.com")

        # Should contain mock data
        assert "api.target.com" in result
        assert "dev.target.com" in result
        assert "mock security scan" in result


class TestSecurityAuditWithBackend:
    """Tests for security_audit chain delegation with backend."""

    def test_security_audit_chain_uses_backend(self):
        """Test security_audit chain delegation uses injected backend for both agents."""
        bus = SabdaBus()
        fake_backend = FakeBackend({
            "status": "completed",
            "result": {"marker": "fake"},
            "notes": "fake backend"
        })

        sec_wayang = SecWayang(bus, backend=fake_backend)
        coder_wayang = CoderWayang(bus, backend=fake_backend)

        # Wire peers manually for this test
        sec_wayang.peers = {"coder_wayang": coder_wayang}
        coder_wayang.peers = {"sec_wayang": sec_wayang}

        # Send security_audit task
        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="security_audit",
            payload={"target": "test.com", "file": "test.py"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        # Get response
        response = bus.get_next("dhalang")
        assert response is not None

        # Parse result
        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        # Verify combined result contains both security and code_analysis
        assert "security" in result.result
        assert "code_analysis" in result.result
        # Both should have the fake marker
        assert result.result["security"].get("marker") == "fake"
        assert result.result["code_analysis"].get("marker") == "fake"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])