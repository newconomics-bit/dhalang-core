"""Tests for LLM backends."""

import json
import pytest
from unittest.mock import Mock, patch

from src.llm.interfaces import LLMBackend
from src.llm.mock_backend import MockBackend, mock_respond
from src.llm.ollama_backend import OllamaBackend
from src.llm.errors import LLMUnavailableError
from src.llm.factory import get_backend


class TestMockBackend:
    """Tests for MockBackend."""

    def test_respond_security_keywords(self):
        """Test MockBackend returns valid JSON for security keywords."""
        backend = MockBackend()
        response = backend.respond("scan subdomain example.com")
        data = json.loads(response)

        assert data["status"] == "completed"
        assert "subdomains" in data["result"]
        assert "api.target.com" in data["result"]["subdomains"]
        assert "dev.target.com" in data["result"]["subdomains"]
        assert data["result"]["vulnerabilities"] == 2
        assert data["notes"] == "mock security scan"

    def test_respond_code_keywords(self):
        """Test MockBackend returns valid JSON for code keywords."""
        backend = MockBackend()
        response = backend.respond("analyze code in auth.py")
        data = json.loads(response)

        assert data["status"] == "completed"
        assert data["result"]["file"] == "auth.py"
        assert data["result"]["line"] == 45
        assert data["result"]["issue"] == "password not hashed"
        assert data["result"]["severity"] == "high"
        assert data["notes"] == "mock code analysis"

    def test_respond_default(self):
        """Test MockBackend returns default for unknown keywords."""
        backend = MockBackend()
        response = backend.respond("random unknown request")
        data = json.loads(response)

        assert data["status"] == "completed"
        assert data["result"]["answer"] == "general response"
        assert data["notes"] == "mock default"

    def test_implements_interface(self):
        """Test MockBackend implements LLMBackend interface."""
        backend = MockBackend()
        assert isinstance(backend, LLMBackend)


class TestGetBackend:
    """Tests for get_backend factory function."""

    def test_get_mock_backend(self):
        """Test get_backend returns MockBackend for 'mock'."""
        backend = get_backend({"backend": "mock"})
        assert isinstance(backend, MockBackend)

    def test_get_ollama_backend_instantiate_only(self):
        """Test get_backend returns OllamaBackend instance without network call."""
        backend = get_backend({"backend": "ollama", "model": "test-model"})
        assert isinstance(backend, OllamaBackend)
        assert backend.model == "test-model"
        assert backend.host == "http://localhost:11434"
        assert backend.temperature == 0.5

    def test_get_unknown_backend_fallback_to_mock(self):
        """Test get_backend falls back to MockBackend for unknown backend."""
        backend = get_backend({"backend": "salah"})
        assert isinstance(backend, MockBackend)

    def test_get_backend_none_config_fallback(self):
        """Test get_backend with None config falls back to mock."""
        backend = get_backend(None)
        assert isinstance(backend, MockBackend)


class TestOllamaBackend:
    """Tests for OllamaBackend with fake transport."""

    def test_respond_success(self):
        """Test OllamaBackend.respond with successful mocked response."""
        backend = OllamaBackend(model="test-model", temperature=0.7)

        mock_response = {
            "message": {
                "content": '{"status": "completed", "result": {"test": "data"}, "notes": "test"}'
            }
        }

        with patch("src.llm.ollama_backend.requests.post") as mock_post:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_post.return_value = mock_response_obj

            response = backend.respond("test prompt")

            assert response == '{"status": "completed", "result": {"test": "data"}, "notes": "test"}'
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "test-model"
            assert call_args[1]["json"]["options"]["temperature"] == 0.7

    def test_respond_timeout_raises_error(self):
        """Test OllamaBackend.respond raises LLMUnavailableError on timeout."""
        backend = OllamaBackend(model="test-model")

        with patch("src.llm.ollama_backend.requests.post") as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

            with pytest.raises(LLMUnavailableError) as exc_info:
                backend.respond("test prompt")

            assert "timed out" in str(exc_info.value)
            assert exc_info.value.backend == "ollama"

    def test_respond_connection_error_raises_error(self):
        """Test OllamaBackend.respond raises LLMUnavailableError on connection error."""
        backend = OllamaBackend(model="test-model")

        with patch("src.llm.ollama_backend.requests.post") as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.ConnectionError("Cannot connect")

            with pytest.raises(LLMUnavailableError) as exc_info:
                backend.respond("test prompt")

            assert "Cannot connect" in str(exc_info.value)
            assert exc_info.value.backend == "ollama"

    def test_respond_http_error_raises_error(self):
        """Test OllamaBackend.respond raises LLMUnavailableError on HTTP error."""
        backend = OllamaBackend(model="test-model")

        with patch("src.llm.ollama_backend.requests.post") as mock_post:
            import requests
            mock_response = Mock()
            http_error = requests.exceptions.HTTPError("404 Not Found")
            http_error.response = mock_response
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = http_error
            mock_post.return_value = mock_response

            with pytest.raises(LLMUnavailableError) as exc_info:
                backend.respond("test prompt")

            assert "HTTP error" in str(exc_info.value)
            assert exc_info.value.backend == "ollama"

    def test_respond_invalid_json_raises_error(self):
        """Test OllamaBackend.respond raises LLMUnavailableError on invalid JSON."""
        backend = OllamaBackend(model="test-model")

        with patch("src.llm.ollama_backend.requests.post") as mock_post:
            mock_response_obj = Mock()
            mock_response_obj.json.side_effect = ValueError("Invalid JSON")
            mock_response_obj.raise_for_status.return_value = None
            mock_post.return_value = mock_response_obj

            with pytest.raises(LLMUnavailableError) as exc_info:
                backend.respond("test prompt")

            assert "parse" in str(exc_info.value).lower()
            assert exc_info.value.backend == "ollama"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])