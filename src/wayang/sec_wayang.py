"""Security Wayang agent - specializes in security scanning."""

from src.sabda.bus import SabdaBus
from src.wayang.base_wayang import Wayang


class SecWayang(Wayang):
    """Wayang agent specialized for security scanning tasks."""

    def __init__(self, bus: SabdaBus) -> None:
        super().__init__(agent_id="sec_wayang", bus=bus)

    # Can override gunakan_tool here if specialized behavior needed