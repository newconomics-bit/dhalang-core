"""Coder Wayang agent - specializes in code analysis."""

from src.sabda.bus import SabdaBus
from src.wayang.base_wayang import Wayang


class CoderWayang(Wayang):
    """Wayang agent specialized for code analysis tasks."""

    def __init__(self, bus: SabdaBus) -> None:
        super().__init__(agent_id="coder_wayang", bus=bus)

    # Can override gunakan_tool here if specialized behavior needed