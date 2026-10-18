"""Coder Wayang agent - specializes in code analysis."""

from typing import Optional

from src.sabda.bus import SabdaBus
from src.wayang.base_wayang import Wayang
from src.llm.interfaces import LLMBackend


class CoderWayang(Wayang):
    """Wayang agent specialized for code analysis tasks."""

    def __init__(self, bus: SabdaBus, backend: Optional[LLMBackend] = None) -> None:
        super().__init__(agent_id="coder_wayang", bus=bus, backend=backend)

    # Can override gunakan_tool here if specialized behavior needed