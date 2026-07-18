"""Heuristic environment analyzer (no machine learning).

"AI" here means a smart, explainable heuristic - not a model. The analyzer
listens to a short window of microphone audio and measures how much energy is
sitting at each candidate FSK frequency. A quiet frequency is a good channel;
a busy one will corrupt our tones.

This is the sensing half of the AI subsystem; :mod:`frequency_selector` is the
deciding half.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.audio import fft
from app.config.frequencies import FrequencyPlan


@dataclass
class NoiseReading:
    """Measured background noise for one candidate frequency plan."""

    plan: FrequencyPlan
    noise: float          # combined ambient energy at f0 and f1 (lower = better)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.plan.base:.0f}Hz -> noise={self.noise:.4f}"


def measure_noise(samples: np.ndarray, plan: FrequencyPlan) -> float:
    """Measure ambient energy at a plan's two tones over ``samples``.

    The window is split into several blocks and averaged so a single transient
    (a cough, a key click) doesn't dominate the estimate.
    """
    if samples.shape[0] == 0:
        return 0.0

    n_blocks = 6
    block_len = max(samples.shape[0] // n_blocks, 1)
    readings: list[float] = []
    for i in range(n_blocks):
        block = samples[i * block_len : (i + 1) * block_len]
        if block.shape[0] < block_len:
            break
        power = fft.tone_power(block, plan.f0, bins=2) + fft.tone_power(block, plan.f1, bins=2)
        readings.append(power)

    return float(np.mean(readings)) if readings else 0.0


def analyze(samples: np.ndarray, plans: list[FrequencyPlan]) -> list[NoiseReading]:
    """Return a noise reading for every candidate plan, ordered as given."""
    return [NoiseReading(plan=p, noise=measure_noise(samples, p)) for p in plans]
