"""Waveform -> message decoder (the receiver's DSP brain).

This is the hardest part of an acoustic modem: the receiver captures a
continuous stream with no idea *when* a packet starts or where the bit
boundaries fall. The decoder solves three problems in order:

1. **Energy detection** - is there any FSK signal in this buffer at all?
2. **Symbol timing recovery** - find the sample offset where bit boundaries
   line up, by brute-force searching a small range of offsets and scoring each
   against the known PREAMBLE+SFD pattern.
3. **Frame decode** - once aligned, read LEN / payload / CRC via the packetizer.

The approach is intentionally non-coherent and search-based rather than a full
PLL: it is easy to understand, has no per-sample feedback loop to tune, and is
robust enough for a hackathon-grade link.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.audio import filters
from app.config.frequencies import FrequencyPlan
from app.config.settings import get_settings
from app.core import packetizer, protocol
from app.modulation import fsk

# Expected sync pattern the receiver hunts for: preamble followed by the SFD.
_SYNC_PATTERN: list[int] = protocol.PREAMBLE_BITS + protocol.byte_to_bits(protocol.SFD)


@dataclass
class DecodeResult:
    """Outcome of a decode attempt over one audio buffer."""

    message: str
    crc_ok: bool
    offset: int          # sample offset where the frame was found
    sync_score: float    # fraction of sync bits matched (0..1)


def _decode_bits_at(signal: np.ndarray, offset: int, n_bits: int, plan: FrequencyPlan) -> list[int]:
    """Demodulate ``n_bits`` symbols starting at sample ``offset``."""
    spb = get_settings().samples_per_bit
    bits: list[int] = []
    for i in range(n_bits):
        start = offset + i * spb
        block = signal[start : start + spb]
        if block.shape[0] < spb:
            break
        bits.append(fsk.demodulate_symbol(block, plan).bit)
    return bits


def _sync_score(signal: np.ndarray, offset: int, plan: FrequencyPlan) -> float:
    """Fraction of the sync pattern matched if bits start at ``offset``."""
    bits = _decode_bits_at(signal, offset, len(_SYNC_PATTERN), plan)
    if len(bits) < len(_SYNC_PATTERN):
        return 0.0
    matches = sum(1 for a, b in zip(bits, _SYNC_PATTERN) if a == b)
    return matches / len(_SYNC_PATTERN)


def _find_energy_onset(signal: np.ndarray, plan: FrequencyPlan) -> int | None:
    """Return the approximate sample index where in-band energy first appears.

    Slides a symbol-sized window across the buffer and looks for the *rising
    edge* of the FSK tone. We estimate the noise floor from a low percentile of
    all windows (robust whether the buffer is mostly silence or mostly signal),
    require a clear peak above that floor, then return the first window that
    crosses a fraction of the way from floor to peak.
    """
    spb = get_settings().samples_per_bit
    hop = max(spb // 4, 1)

    offsets: list[int] = []
    values_list: list[float] = []
    for start in range(0, signal.shape[0] - spb, hop):
        offsets.append(start)
        values_list.append(fsk.band_energy(signal[start : start + spb], plan))
    if not offsets:
        return None

    values = np.asarray(values_list)
    floor = float(np.percentile(values, 10))   # ambient noise level
    peak = float(values.max())

    # No clear signal if the peak isn't well above the noise floor.
    if peak <= max(floor * 3.0, 1e-9):
        return None

    threshold = floor + 0.3 * (peak - floor)
    for offset, value in zip(offsets, values):
        if value >= threshold:
            return offset
    return None


def decode(signal: np.ndarray, plan: FrequencyPlan) -> DecodeResult | None:
    """Attempt to decode a single frame from ``signal``.

    Returns a :class:`DecodeResult` with ``crc_ok`` indicating validity, or
    ``None`` if no plausible packet was found.
    """
    settings = get_settings()
    spb = settings.samples_per_bit

    if signal.shape[0] < len(_SYNC_PATTERN) * spb:
        return None

    # 1. Isolate the FSK band to boost SNR before anything else.
    filtered = filters.bandpass_around(signal, plan.f0, plan.f1)

    # 2. Locate where the signal energy begins.
    onset = _find_energy_onset(filtered, plan)
    if onset is None:
        return None

    # 3. Symbol timing recovery: scan a window of offsets around the onset and
    #    keep the one that best matches the known sync pattern. The search
    #    range spans a couple of symbols with a fine step.
    search_lo = max(onset - spb, 0)
    search_hi = min(onset + 3 * spb, filtered.shape[0] - len(_SYNC_PATTERN) * spb)
    if search_hi <= search_lo:
        return None
    step = max(spb // 8, 1)

    best_offset = search_lo
    best_score = 0.0
    for offset in range(search_lo, search_hi + 1, step):
        score = _sync_score(filtered, offset, plan)
        if score > best_score:
            best_score, best_offset = score, offset
            if score == 1.0:
                break

    # Require a strong sync match to avoid decoding random noise.
    if best_score < 0.85:
        return None

    # 4. Frame starts right after preamble + SFD.
    frame_offset = best_offset + len(_SYNC_PATTERN) * spb

    # Demodulate a generous number of bits (LEN + max payload + CRC + EOF),
    # bounded by what's left in the buffer.
    remaining = (filtered.shape[0] - frame_offset) // spb
    max_frame_bits = (1 + protocol.MAX_PAYLOAD_BYTES + 2) * 8
    n_bits = int(min(remaining, max_frame_bits))
    frame_bits = _decode_bits_at(filtered, frame_offset, n_bits, plan)

    parsed = packetizer.parse_after_sfd(frame_bits)
    if parsed is None:
        return None

    return DecodeResult(
        message=parsed.message,
        crc_ok=parsed.crc_ok,
        offset=best_offset,
        sync_score=best_score,
    )
