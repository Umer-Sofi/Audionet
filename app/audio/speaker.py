"""Speaker output via sounddevice.

Responsible for exactly one thing: play a float waveform out of the laptop's
speaker and block until it finishes. All waveform *generation* happens in the
modulation layer - this file is pure I/O.
"""

from __future__ import annotations

import numpy as np
import sounddevice as sd

from app.config.settings import get_settings


def play(waveform: np.ndarray) -> None:
    """Play a mono float32 waveform and block until playback completes.

    The array is clipped to [-1, 1] as a safety net so we never send an
    out-of-range sample to the DAC.
    """
    settings = get_settings()

    audio = np.clip(waveform, -1.0, 1.0).astype(np.float32)
    sd.play(
        audio,
        samplerate=settings.sample_rate,
        device=settings.output_device,
        blocking=True,
    )
    sd.wait()
