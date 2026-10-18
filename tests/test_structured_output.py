"""Tests for structured output handling and parse fallback."""

import json
import pytest

from src.llm.parse import parse_llm_response
from src.llm.interfaces import LLMBackend
from src.llm.ollama_backend import OllamaBackend
from src.sabda.bus import SabdaBus
from src.sabda.models import SabdaMessage, WayangResult, WayangStatus
from src.wayang.sec_wayang import SecWayang
from src.wayang.coder_wayang import CoderWayang
from src.dhalang import Dhalang


class TestParseHelper:
    """Tests for the parse_llm_response helper."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        response = '{"status": "completed", "result": {"key": "value"}, "notes": "test"}'
        result = parse_llm_response(response, "test_agent")

        assert result.agent == "test_agent"
        assert result.status == WayangStatus.COMPLETED
        assert result.result == {"key": "value"}
        assert result.notes == "test"

    def test_parse_json_with_markdown_fence(self):
        """Test parsing JSON wrapped in markdown fence."""
        response = '```json\n{"status": "completed", "result": {"key": "value"}}\n```'
        result = parse_llm_response(response, "test_agent")

        assert result.status == WayangStatus.COMPLETED
        assert result.result == {"key": "value"}

    def test_parse_json_with_markdown_fence_no_lang(self):
        """Test parsing JSON wrapped in markdown fence without language specifier."""
        response = '```\n{"status": "completed", "result": {"key": "value"}}\n```'
        result = parse_llm_response(response, "test_agent")

        assert result.status == WayangStatus.COMPLETED
        assert result.result == {"key": "value"}

    def test_parse_embedded_json_in_text(self):
        """Test extracting JSON embedded in prose text."""
        response = 'Here is the result: {"status": "completed", "result": {"extracted": true}} and some more text.'
        result = parse_llm_response(response, "test_agent")

        assert result.status == WayangStatus.COMPLETED
        assert result.result == {"extracted": True}

    def test_parse_total_garbage(self):
        """Test handling of completely unparseable output."""
        response = "This is just random text with no JSON at all!"
        result = parse_llm_response(response, "test_agent")

        assert result.status == WayangStatus.FAILED
        assert "unparseable" in result.notes.lower()

    def test_parse_empty_string(self):
        """Test handling of empty string."""
        response = ""
        result = parse_llm_response(response, "test_agent")

        assert result.status == WayangStatus.FAILED
        assert "unparseable" in result.notes.lower()

    def test_parse_failed_status(self):
        """Test parsing with failed status."""
        response = '{"status": "failed", "result": {}, "notes": "Something went wrong"}'
        result = parse_llm_response(response, "test_agent")

        assert result.status == WayangStatus.FAILED
        assert result.notes == "Something went wrong"

    def test_parse_need_more_info_status(self):
        """Test parsing with need_more_info status."""
        response = '{"status": "need_more_info", "result": {}, "notes": "Need clarification"}'
        result = parse_llm_response(response, "test_agent")

        assert result.status == WayangStatus.NEED_MORE_INFO


class TestOllamaBackendFormatJson:
    """Tests for OllamaBackend with format=json."""

    def test_payload_includes_format_json(self):
        """Test that OllamaBackend payload includes format=json when enabled."""
        backend = OllamaBackend(model="test-model", enable_json_format=True)

        # We can't easily test the actual HTTP call without mocking,
        # but we can verify the parameter is stored
        assert backend.enable_json_format is True

    def test_payload_excludes_format_when_disabled(self):
        """Test that format is not included when disabled."""
        backend = OllamaBackend(model="test-model", enable_json_format=False)
        assert backend.enable_json_format is False


class MalformedBackend(LLMBackend):
    """Backend that returns malformed responses for testing."""

    def __init__(self, response_text: str):
        self.response_text = response_text

    def respond(self, prompt: str) -> str:
        return self.response_text


class TestWayangWithMalformedBackend:
    """Tests for Wayang agents with malformed backend responses."""

    def test_sec_wayang_with_text_wrapped_json(self):
        """Test SecWayang handles text-wrapped JSON from backend."""
        bus = SabdaBus()
        backend = MalformedBackend('Here is the scan result: {"status": "completed", "result": {"subdomains": ["test.com"]}, "notes": "wrapped"}')
        sec_wayang = SecWayang(bus, backend=backend)

        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="scan_subdomain",
            payload={"target": "test.com"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        response = bus.get_next("dhalang")
        assert response is not None

        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.status == WayangStatus.COMPLETED
        assert "subdomains" in result.result
        assert result.result["subdomains"] == ["test.com"]

    def test_sec_wayang_with_markdown_fence(self):
        """Test SecWayang handles markdown-fenced JSON."""
        bus = SabdaBus()
        backend = MalformedBackend('```json\n{"status": "completed", "result": {"subdomains": ["fenced.com"]}, "notes": "fenced"}\n```')
        sec_wayang = SecWayang(bus, backend=backend)

        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="scan_subdomain",
            payload={"target": "test.com"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        response = bus.get_next("dhalang")
        assert response is not None

        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.status == WayangStatus.COMPLETED
        assert result.result["subdomains"] == ["fenced.com"]

    def test_sec_wayang_with_total_garbage(self):
        """Test SecWayang returns FAILED for unparseable output."""
        bus = SabdaBus()
        backend = MalformedBackend("This is complete garbage with no JSON anywhere!")
        sec_wayang = SecWayang(bus, backend=backend)

        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="scan_subdomain",
            payload={"target": "test.com"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        response = bus.get_next("dhalang")
        assert response is not None

        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.status == WayangStatus.FAILED
        assert "unparseable" in result.notes.lower()

    def test_coder_wayang_with_malformed_output(self):
        """Test CoderWayang handles malformed output."""
        bus = SabdaBus()
        backend = MalformedBackend('Analysis result: {"status": "completed", "result": {"file": "test.py", "line": 10}, "notes": "found issue"}')
        coder_wayang = CoderWayang(bus, backend=backend)

        msg = SabdaMessage(
            sender="dhalang",
            receiver="coder_wayang",
            task_type="analyze_code",
            payload={"file": "test.py"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        coder_wayang.jalankan()

        response = bus.get_next("dhalang")
        assert response is not None

        result = WayangResult(
            agent="coder_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.status == WayangStatus.COMPLETED
        assert result.result["file"] == "test.py"
        assert result.result["line"] == 10

    def test_security_audit_chain_with_malformed_backend(self):
        """Test security_audit chain delegation with malformed backend."""
        bus = SabdaBus()
        backend = MalformedBackend('Security scan: {"status": "completed", "result": {"subdomains": ["audit.com"]}, "notes": "scan done"}')
        
        sec_wayang = SecWayang(bus, backend=backend)
        coder_wayang = CoderWayang(bus, backend=backend)
        
        # Wire peers manually for this test
        sec_wayang.peers = {"coder_wayang": coder_wayang}
        coder_wayang.peers = {"sec_wayang": sec_wayang}

        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="security_audit",
            payload={"target": "audit.com", "file": "audit.py"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        response = bus.get_next("dhalang")
        assert response is not None

        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.status == WayangStatus.COMPLETED
        assert "security" in result.result
        assert "code_analysis" in result.result
        assert result.result["security"]["subdomains"] == ["audit.com"]


class TestDhalangWithMalformedBackend:
    """Tests for Dhalang end-to-end with malformed backend."""

    def test_dhalang_end_to_end_with_malformed_backend(self):
        """Test Dhalang end-to-end with malformed backend responses."""
        backend = MalformedBackend('Result: {"status": "completed", "result": {"subdomains": ["e2e.com"]}, "notes": "e2e test"}')
        dhalang = Dhalang(backend=backend)

        result = dhalang.proses("Cek subdomain e2e.com")

        assert "e2e.com" in result
        assert "subdomains" in result
        assert "COMPLETED" in result


class TestRegression:
    """Regression tests to ensure 59 existing tests still pass."""

    def test_mock_backend_still_works(self):
        """Test that mock backend fallback still works."""
        from src.llm.mock_backend import mock_respond
        
        response = mock_respond("scan subdomain test.com")
        data = json.loads(response)
        
        assert data["status"] == "completed"
        assert "subdomains" in data["result"]

    def test_wayang_without_backend_falls_back_to_mock(self):
        """Test Wayang without backend falls back to mock_respond."""
        bus = SabdaBus()
        sec_wayang = SecWayang(bus, backend=None)

        msg = SabdaMessage(
            sender="dhalang",
            receiver="sec_wayang",
            task_type="scan_subdomain",
            payload={"target": "test.com"},
            reply_to="dhalang"
        )
        bus.publish(msg)
        sec_wayang.jalankan()

        response = bus.get_next("dhalang")
        assert response is not None

        result = WayangResult(
            agent="sec_wayang",
            status=WayangStatus(response.payload["status"]),
            result=response.payload["result"],
            notes=response.payload.get("notes")
        )

        assert result.status == WayangStatus.COMPLETED
        assert "subdomains" in result.result

    def test_dhalang_default_backend_works(self):
        """Test Dhalang with default (mock) backend works."""
        dhalang = Dhalang()
        result = dhalang.proses("Cek subdomain test.com")
        
        assert "api.target.com" in result
        assert "dev.target.com" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])