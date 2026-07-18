"""High-level receiver: sound in, message out.

The transmitter's AI may pick *any* of the candidate channels, and the receiving
laptop has no side-channel telling it which. So the receiver simply tries to
decode on every candidate plan and accepts the first frame whose CRC checks
out. With only a handful of candidates this brute-force scan is cheap and keeps
the two laptops from needing to pre-agree on a frequency.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.config.frequencies import FrequencyPlan, candidate_plans
from app.modulation import decoder


@dataclass
class ReceiveReport:
    """A successfully received (CRC-valid) message."""

    message: str
    plan: FrequencyPlan
    sync_score: float
    dst: int
    src: int


class Receiver:
    """Scans an audio buffer across all candidate channels for a valid frame."""

    def __init__(self) -> None:
        self._plans: list[FrequencyPlan] = candidate_plans()

    def try_decode(self, signal: np.ndarray) -> ReceiveReport | None:
        """Return the first CRC-valid frame found in ``signal``, else ``None``.

        Channels with a structurally valid but CRC-failed frame are ignored so a
        near-miss on one channel doesn't suppress a good frame on another.
        """
        for plan in self._plans:
            result = decoder.decode(signal, plan)
            if result is not None and result.crc_ok and result.message:
                return ReceiveReport(
                    message=result.message,
                    plan=plan,
                    sync_score=result.sync_score,
                    dst=result.dst,
                    src=result.src,
                )
        return None
