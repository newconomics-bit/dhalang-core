"""Ollama LLM backend implementation."""

import logging
from typing import Optional

import requests

from .errors import LLMUnavailableError
from .interfaces import LLMBackend

logger = logging.getLogger(__name__)


class OllamaBackend(LLMBackend):
    """Ollama backend for LLM inference via /api/chat endpoint."""

    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        temperature: float = 0.5,
        timeout: int = 60,
    ) -> None:
        """Initialize Ollama backend.

        Args:
            model: Model name (e.g., "qwen2.5:14b").
            host: Ollama server URL (default: http://localhost:11434).
            temperature: Sampling temperature (default: 0.5).
            timeout: Request timeout in seconds (default: 60).
        """
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self._api_url = f"{self.host}/api/chat"

    def respond(self, prompt: str) -> str:
        """Send prompt to Ollama and return response content.

        Args:
            prompt: Input prompt string.

        Returns:
            Response content from Ollama.

        Raises:
            LLMUnavailableError: If request fails, times out, or returns non-200.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        try:
            logger.debug("Ollama request: model=%s, prompt_len=%d", self.model, len(prompt))
            response = requests.post(
                self._api_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Parse Ollama /api/chat response format
            message = data.get("message", {})
            content = message.get("content", "")

            if not content:
                logger.warning("Ollama returned empty content: %s", data)
                return ""

            logger.debug("Ollama response received, content_len=%d", len(content))
            return content

        except requests.exceptions.Timeout as e:
            raise LLMUnavailableError(
                f"Request timed out after {self.timeout}s",
                backend="ollama",
                original_error=e,
            )
        except requests.exceptions.ConnectionError as e:
            raise LLMUnavailableError(
                f"Cannot connect to Ollama at {self.host}",
                backend="ollama",
                original_error=e,
            )
        except requests.exceptions.HTTPError as e:
            raise LLMUnavailableError(
                f"Ollama returned HTTP error: {e.response.status_code}",
                backend="ollama",
                original_error=e,
            )
        except requests.exceptions.RequestException as e:
            raise LLMUnavailableError(
                f"Request failed: {e}",
                backend="ollama",
                original_error=e,
            )
        except ValueError as e:
            raise LLMUnavailableError(
                f"Failed to parse Ollama response as JSON: {e}",
                backend="ollama",
                original_error=e,
            )