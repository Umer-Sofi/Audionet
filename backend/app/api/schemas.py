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
    to: int = Field(
        default=0,
        ge=0,
        le=255,
        description="Destination device address. 0 = broadcast to everyone.",
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
    to: int = Field(..., description="Destination address used (0 = broadcast).")
    source: int = Field(..., description="This device's address (the sender).")


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
    source: int | None = Field(default=None, description="Sender's device address.")
    to: int | None = Field(default=None, description="Address it was sent to (0 = broadcast).")


class StatusResponse(BaseModel):
    """Response for ``GET /status``."""

    status: str = Field(..., examples=["Listening", "Sending", "Idle"])


class ConfigResponse(BaseModel):
    """Response for ``GET /config`` - real modem parameters for the UI."""

    sample_rate: int = Field(..., description="Audio sample rate in Hz.")
    baud: int = Field(..., description="Symbols per second (bit rate).")
    freq_shift: float = Field(..., description="Hz between the '0' and '1' tones.")
    frequencies: list[float] = Field(..., description="Candidate base frequencies (Hz).")
    default_frequency: float = Field(..., description="Default base frequency (Hz).")
    device_address: int = Field(..., description="This node's device address (1-255).")
    device_name: str = Field(..., description="This node's display name.")


class DeviceRequest(BaseModel):
    """Body for ``POST /device`` - set this node's identity."""

    address: int = Field(..., ge=1, le=255, description="This device's address (1-255).")
    name: str | None = Field(default=None, description="Optional display name.")


class DeviceResponse(BaseModel):
    """Response describing this node's identity."""

    address: int = Field(..., description="This device's address.")
    name: str = Field(..., description="This device's display name.")
