"""LLM backend interfaces."""

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