"""Candidate frequency plan for the FSK modem.

A :class:`FrequencyPlan` is one concrete choice of the two tones used by binary
FSK: ``f0`` encodes bit ``0`` and ``f1`` encodes bit ``1``. We predefine a set
of *candidate base frequencies*; the AI frequency selector measures background
noise and picks the cleanest one at runtime.

Keeping this list here (data, not logic) makes it trivial to retune for
different hardware without touching the DSP or AI code.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import get_settings


@dataclass(frozen=True)
class FrequencyPlan:
    """A single binary-FSK tone pair.

    Attributes:
        base: Human-friendly label / lower tone in Hz (used for logging + AI).
        f0:   Tone for bit ``0`` (Hz).
        f1:   Tone for bit ``1`` (Hz).
    """

    base: float
    f0: float
    f1: float

    @property
    def probe_frequencies(self) -> tuple[float, float]:
        """Frequencies the environment analyzer should measure noise at."""
        return (self.f0, self.f1)

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"FreqPlan(base={self.base:.0f}Hz, f0={self.f0:.0f}, f1={self.f1:.0f})"


def candidate_plans() -> list[FrequencyPlan]:
    """Build the list of selectable tone pairs.

    Each candidate uses a different base frequency spaced across the
    near-ultrasonic band; both tones are derived from the configured
    ``freq_shift`` so the modem's frequency separation stays constant.
    """
    settings = get_settings()
    shift = settings.freq_shift

    # Base frequencies chosen to sit inside the "mostly inaudible but still
    # reproducible" band for consumer laptops. Adjust for your hardware.
    bases = [17_600.0, 18_200.0, 18_800.0, 19_400.0]

    plans: list[FrequencyPlan] = []
    for base in bases:
        f0 = base
        f1 = base + shift
        # Never exceed Nyquist (with a small guard band).
        if f1 < settings.sample_rate / 2 - 500:
            plans.append(FrequencyPlan(base=base, f0=f0, f1=f1))
    return plans


def default_plan() -> FrequencyPlan:
    """Fallback plan used before the AI has chosen anything."""
    return candidate_plans()[0]
