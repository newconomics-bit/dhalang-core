"""Mock LLM brain for testing Wayang agents."""

import json
from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def respond(self, prompt: str) -> str:
        """Generate a response for the given prompt.

        Args:
            prompt: Input prompt string.

        Returns:
            Response string from the LLM.
        """
        pass


class MockBackend(LLMBackend):
    """Mock backend that delegates to the mock_respond function."""

    def respond(self, prompt: str) -> str:
        return mock_respond(prompt)


def mock_respond(prompt: str) -> str:
    """Return mock JSON response based on keywords in prompt.

    Args:
        prompt: Input prompt string.

    Returns:
        JSON string with status, result, and notes fields.
    """
    prompt_lower = prompt.lower()

    # Security-related keywords
    if any(kw in prompt_lower for kw in ("scan", "subdomain", "security")):
        return json.dumps({
            "status": "completed",
            "result": {
                "subdomains": ["api.target.com", "dev.target.com"],
                "vulnerabilities": 2
            },
            "notes": "mock security scan"
        })

    # Code-related keywords
    if any(kw in prompt_lower for kw in ("code", "bug", "analyze", "function")):
        return json.dumps({
            "status": "completed",
            "result": {
                "file": "auth.py",
                "line": 45,
                "issue": "password not hashed",
                "severity": "high"
            },
            "notes": "mock code analysis"
        })

    # Default response
    return json.dumps({
        "status": "completed",
        "result": {
            "answer": "general response"
        },
        "notes": "mock default"
    })