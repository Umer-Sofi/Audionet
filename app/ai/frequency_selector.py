"""Heuristic frequency selector (the deciding half of the AI subsystem).

Given noise readings from :mod:`environment_analyzer`, pick the cleanest
available FSK channel. The rule is simple and explainable:

    choose the candidate plan with the lowest measured in-band noise.

Example: if 18.2 kHz is busy (noise 0.9) but 18.6 kHz is free (noise 0.1),
select 18.6 kHz.

The selector records a short human-readable rationale so the API/status can
explain *why* a channel was chosen - useful for a demo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai import environment_analyzer
from app.audio.microphone import Microphone
from app.config.frequencies import FrequencyPlan, candidate_plans, default_plan
from app.config.settings import get_settings


@dataclass
class SelectionResult:
    """The chosen channel plus an explanation of the decision."""

    plan: FrequencyPlan
    rationale: str


def select_from_readings(
    readings: list[environment_analyzer.NoiseReading],
) -> SelectionResult:
    """Choose the plan with the least in-band noise."""
    if not readings:
        return SelectionResult(plan=default_plan(), rationale="no readings; using default plan")

    best = min(readings, key=lambda r: r.noise)
    ranked = ", ".join(f"{r.plan.base:.0f}Hz={r.noise:.3f}" for r in readings)
    rationale = f"selected {best.plan.base:.0f}Hz (lowest noise). readings: {ranked}"
    return SelectionResult(plan=best.plan, rationale=rationale)


def choose_channel(mic: Microphone) -> SelectionResult:
    """Sample the mic, analyze every candidate channel, and pick the cleanest.

    This is the single entry point the transmitter calls right before sending.
    """
    settings = get_settings()
    samples = mic.latest(settings.noise_probe_seconds)
    plans = candidate_plans()
    readings = environment_analyzer.analyze(samples, plans)
    return select_from_readings(readings)
