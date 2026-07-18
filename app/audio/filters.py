"""Digital filters used by the receiver.

The microphone captures the *entire* audible + near-ultrasonic spectrum: voices,
fans, keyboard clatter, music. Before we try to demodulate we band-pass the
signal down to just the FSK band, which dramatically improves the
signal-to-noise ratio the FFT sees.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

from app.config.settings import get_settings


def bandpass(
    signal: np.ndarray,
    low_hz: float,
    high_hz: float,
    order: int = 6,
) -> np.ndarray:
    """Apply a zero-phase Butterworth band-pass filter.

    Args:
        signal:  1-D float audio samples.
        low_hz:  lower edge of the pass band.
        high_hz: upper edge of the pass band.
        order:   filter order (steepness of the roll-off).

    Returns:
        The filtered signal, same shape as the input.

    ``sosfiltfilt`` runs the filter forwards and backwards, giving zero phase
    distortion (important - we don't want to smear the FSK symbol timing) and
    doubling the effective attenuation.
    """
    settings = get_settings()
    nyquist = settings.sample_rate / 2.0

    # Clamp to a valid normalized range (0, 1) for scipy.
    low = max(low_hz / nyquist, 1e-4)
    high = min(high_hz / nyquist, 0.999)
    if low >= high:
        raise ValueError(f"invalid band: low={low_hz} high={high_hz}")

    sos = butter(order, [low, high], btype="bandpass", output="sos")

    # filtfilt needs a signal longer than the filter's padding length.
    if signal.shape[0] <= 3 * (2 * order + 1):
        return signal
    return sosfiltfilt(sos, signal)


def bandpass_around(signal: np.ndarray, f0: float, f1: float, margin: float = 400.0) -> np.ndarray:
    """Band-pass a signal to just enclose the two FSK tones plus a margin."""
    low = min(f0, f1) - margin
    high = max(f0, f1) + margin
    return bandpass(signal, low, high)
