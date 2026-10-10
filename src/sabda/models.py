"""Data models for Sabda Message Bus."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class WayangStatus(str, Enum):
    """Status enum for Wayang execution results."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEED_MORE_INFO = "NEED_MORE_INFO"


class SabdaMessage(BaseModel):
    """Message contract for inter-agent communication."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sender: str
    receiver: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reply_to: Optional[str] = None


class WayangResult(BaseModel):
    """Result contract from Wayang agent execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent: str
    status: WayangStatus
    result: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None