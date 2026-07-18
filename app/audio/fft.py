"""FFT-based frequency analysis helpers.

Two jobs:

1. Measure how much energy sits at a given frequency inside a block of samples
   (used both by the demodulator to decide '0' vs '1' and by the AI to measure
   noise).
2. Report the dominant frequency of a block (handy for diagnostics).

A Hann window is applied before every transform to reduce spectral leakage,
which matters because our FSK tones are close together.
"""

from __future__ import annotations

import numpy as np

from app.config.settings import get_settings


def _window(n: int) -> np.ndarray:
    """Hann window of length ``n`` (cached per length would be an easy win)."""
    return np.hanning(n)


def magnitude_spectrum(block: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (frequencies, magnitudes) for a real signal block.

    Uses ``numpy.fft.rfft`` since our audio is real-valued.
    """
    settings = get_settings()
    n = block.shape[0]
    windowed = block * _window(n)
    spectrum = np.fft.rfft(windowed)
    freqs = np.fft.rfftfreq(n, d=1.0 / settings.sample_rate)
    mags = np.abs(spectrum)
    return freqs, mags


def _nearest_bin(freqs: np.ndarray, target: float) -> int:
    """Index of the FFT bin closest to ``target`` Hz."""
    return int(np.argmin(np.abs(freqs - target)))


def tone_power(block: np.ndarray, frequency: float, bins: int = 1) -> float:
    """Energy at ``frequency`` in ``block``.

    ``bins`` widens the measurement by summing a few neighbouring FFT bins,
    which makes it tolerant of small frequency drift between the two laptops'
    sound cards.
    """
    freqs, mags = magnitude_spectrum(block)
    center = _nearest_bin(freqs, frequency)
    lo = max(center - bins, 0)
    hi = min(center + bins + 1, mags.shape[0])
    return float(np.sum(mags[lo:hi]))


def dominant_frequency(block: np.ndarray) -> float:
    """Frequency (Hz) of the strongest spectral component in ``block``."""
    freqs, mags = magnitude_spectrum(block)
    return float(freqs[int(np.argmax(mags))])
