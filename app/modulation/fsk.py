"""The FSK modem primitives (the DSP heart of AudioNet).

Binary Frequency Shift Keying (BFSK):

    bit 0  ->  tone at f0
    bit 1  ->  tone at f1

This module knows how to:

* turn a bit list into a **phase-continuous** sine waveform (modulate), and
* decide whether a single symbol-length block of audio is a 0 or a 1, using an
  FFT tone-power comparison (demodulate a symbol).

Phase continuity matters: if we naively concatenated independent sine segments
the phase would jump at each bit boundary, producing audible clicks and
spectral splatter that leaks between the two tones. Building one continuous
phase accumulator avoids this entirely.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.audio import fft
from app.config.frequencies import FrequencyPlan
from app.config.settings import get_settings


@dataclass
class SymbolDecision:
    """The demodulator's verdict for one symbol window."""

    bit: int         # 0 or 1
    p0: float        # measured power at f0
    p1: float        # measured power at f1

    @property
    def confidence(self) -> float:
        """Relative separation of the two tone powers in [0, 1]."""
        total = self.p0 + self.p1
        return abs(self.p1 - self.p0) / total if total > 0 else 0.0

    @property
    def energy(self) -> float:
        """Total in-band energy - used to tell signal from silence."""
        return self.p0 + self.p1


def modulate_bits(bits: list[int], plan: FrequencyPlan) -> np.ndarray:
    """Modulate a bit list into a float32 waveform in [-amplitude, amplitude].

    Args:
        bits: list of 0/1.
        plan: which tone pair (f0/f1) to use.

    Returns:
        1-D float32 numpy array of ``len(bits) * samples_per_bit`` samples.
    """
    settings = get_settings()
    spb = settings.samples_per_bit
    fs = settings.sample_rate

    # Instantaneous frequency for every output sample.
    freq_per_sample = np.empty(len(bits) * spb, dtype=np.float64)
    for i, bit in enumerate(bits):
        f = plan.f1 if bit else plan.f0
        freq_per_sample[i * spb : (i + 1) * spb] = f

    # Integrate frequency -> continuous phase -> sine. This guarantees no phase
    # discontinuity at bit boundaries.
    phase = np.cumsum(2.0 * np.pi * freq_per_sample / fs)
    waveform = np.sin(phase).astype(np.float32)

    waveform *= settings.amplitude
    _apply_edge_fade(waveform, spb)
    return waveform


def _apply_edge_fade(waveform: np.ndarray, spb: int) -> None:
    """Fade the very start and end in/out to avoid speaker click transients."""
    fade = min(spb // 2, waveform.shape[0] // 2)
    if fade <= 0:
        return
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
    waveform[:fade] *= ramp
    waveform[-fade:] *= ramp[::-1]


def demodulate_symbol(block: np.ndarray, plan: FrequencyPlan) -> SymbolDecision:
    """Decide 0 vs 1 for a single symbol-length ``block`` using an FFT.

    We measure the power at f0 and at f1 and pick whichever is stronger. This
    is classic *non-coherent* FSK detection: it needs no carrier phase
    recovery, which is exactly what we want for cheap acoustic links.
    """
    p0 = fft.tone_power(block, plan.f0, bins=1)
    p1 = fft.tone_power(block, plan.f1, bins=1)
    bit = 1 if p1 >= p0 else 0
    return SymbolDecision(bit=bit, p0=p0, p1=p1)


def band_energy(block: np.ndarray, plan: FrequencyPlan) -> float:
    """Total energy in the FSK band for a block (0 for silence)."""
    return fft.tone_power(block, plan.f0, bins=1) + fft.tone_power(block, plan.f1, bins=1)
