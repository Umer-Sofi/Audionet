"""Pydantic request/response models for the AudioNet API.

Keeping the wire contract in one place gives us automatic validation and
OpenAPI docs, and decouples the HTTP shape from the internal dataclasses.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.protocol import MAX_PAYLOAD_BYTES


class SendRequest(BaseModel):
    """Body for ``POST /send``."""

    message: str = Field(
        ...,
        min_length=1,
        description="Text to transmit acoustically.",
        examples=["Hello"],
    )

    def encoded_length_ok(self) -> bool:
        """True if the UTF-8 payload fits in a single frame."""
        return len(self.message.encode("utf-8")) <= MAX_PAYLOAD_BYTES


class SendResponse(BaseModel):
    """Response for ``POST /send``."""

    status: str = Field(default="sent", examples=["sent"])
    base_frequency: float = Field(..., description="Chosen base frequency in Hz.")
    rationale: str = Field(..., description="Why the AI picked this channel.")
    duration_seconds: float = Field(..., description="Length of the transmission.")


class ReceivedResponse(BaseModel):
    """Response for ``GET /received``."""

    id: int = Field(default=0, description="Monotonic id; increments per new message.")
    message: str = Field(default="", description="Last decoded message ('' if none).")
    base_frequency: float | None = Field(
        default=None, description="Base frequency it arrived on, if any."
    )
    sync_score: float | None = Field(
        default=None, description="Preamble sync match quality (0..1)."
    )


class StatusResponse(BaseModel):
    """Response for ``GET /status``."""

    status: str = Field(..., examples=["Listening", "Sending", "Idle"])
