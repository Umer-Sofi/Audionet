"""High-level transmitter: message in, sound out.

Ties the AI channel selection, the encoder and the speaker together into a
single ``send`` call. Stateless apart from the mic handle it uses to sense the
environment.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai import frequency_selector
from app.audio import speaker
from app.audio.microphone import Microphone
from app.config.frequencies import FrequencyPlan
from app.config.settings import get_settings
from app.modulation import encoder


@dataclass
class TransmitReport:
    """What happened during a send - surfaced to the API for the demo."""

    message: str
    plan: FrequencyPlan
    rationale: str
    duration_seconds: float


class Transmitter:
    """Encodes a message and plays it through the speaker."""

    def __init__(self, mic: Microphone) -> None:
        # The mic is shared with the receiver; the transmitter only reads it to
        # let the AI sense noise before choosing a channel.
        self._mic = mic

    def send(self, message: str) -> TransmitReport:
        """Choose the cleanest channel, modulate ``message`` and play it."""
        # 1. AI picks the least-noisy channel right now.
        selection = frequency_selector.choose_channel(self._mic)
        plan = selection.plan

        # 2. Text -> framed bits -> FSK waveform.
        waveform = encoder.encode_message(message, plan)

        # 3. Play it out of the speaker (blocks until finished).
        speaker.play(waveform)

        duration = waveform.shape[0] / get_settings().sample_rate
        return TransmitReport(
            message=message,
            plan=plan,
            rationale=selection.rationale,
            duration_seconds=duration,
        )
