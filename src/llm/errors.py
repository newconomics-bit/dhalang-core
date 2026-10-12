"""LLM-related errors."""

class LLMUnavailableError(Exception):
    """Raised when LLM backend is unavailable or request fails."""

    def __init__(self, message: str, backend: str = "unknown", original_error: Exception = None):
        super().__init__(message)
        self.backend = backend
        self.original_error = original_error

    def __str__(self) -> str:
        base = f"[{self.backend}] {super().__str__()}"
        if self.original_error:
            return f"{base} (caused by: {self.original_error})"
        return base