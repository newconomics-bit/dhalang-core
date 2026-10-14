"""Mock backend for testing."""

from .interfaces import LLMBackend


class MockBackend(LLMBackend):
    """Mock backend that returns predefined responses."""

    def respond(self, prompt: str) -> str:
        return mock_respond(prompt)


def mock_respond(prompt: str) -> str:
    """Return mock JSON response based on keywords in prompt."""
    import json

    prompt_lower = prompt.lower()

    if any(kw in prompt_lower for kw in ("scan", "subdomain", "security")):
        return json.dumps({
            "status": "completed",
            "result": {
                "subdomains": ["api.target.com", "dev.target.com"],
                "vulnerabilities": 2
            },
            "notes": "mock security scan"
        })

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

    return json.dumps({
        "status": "completed",
        "result": {
            "answer": "general response"
        },
        "notes": "mock default"
    })


__all__ = ["MockBackend", "mock_respond"]