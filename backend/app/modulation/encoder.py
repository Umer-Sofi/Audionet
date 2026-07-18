"""Message -> waveform encoder.

Thin orchestration layer that combines the packetizer (text -> framed bits) with
the FSK modem (bits -> waveform). Kept separate from ``fsk.py`` so the raw modem
stays generic and testable.
"""

from __future__ import annotations

import numpy as np

from app.config.frequencies import FrequencyPlan
from app.core import packetizer
from app.modulation import fsk


def encode_message(
    message: str, plan: FrequencyPlan, dst: int = 0, src: int = 0
) -> np.ndarray:
    """Encode ``message`` into a playable FSK waveform using ``plan``.

    Args:
        message: text to send.
        plan:    FSK tone pair to use.
        dst:     destination address (0 = broadcast).
        src:     this device's address.

    Returns a float32 mono waveform ready to hand to the speaker.
    """
    bits = packetizer.build_frame_bits(message, dst=dst, src=src)
    return fsk.modulate_bits(bits, plan)
