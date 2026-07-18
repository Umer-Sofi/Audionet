"""Wire protocol constants and low-level bit/byte helpers.

This module defines *what the bytes on the air mean*. It has no DSP and no I/O
so it can be imported anywhere without side effects.

Frame layout (what actually gets modulated), in transmission order::

    ┌───────────┬─────┬─────┬──────────────┬──────┬─────┐
    │ PREAMBLE  │ SFD │ LEN │   PAYLOAD    │ CRC8 │ EOF │
    │ 0101..(N) │ 1B  │ 1B  │  LEN bytes   │  1B  │ 1B  │
    └───────────┴─────┴─────┴──────────────┴──────┴─────┘

* PREAMBLE - alternating bits. Gives the receiver a steady tone-toggle to
  detect energy and lock onto the bit timing.
* SFD      - Start-Of-Frame Delimiter byte. Marks byte alignment / "here comes
  the real data".
* LEN      - number of payload bytes (0-255).
* PAYLOAD  - the UTF-8 encoded message.
* CRC8     - checksum over LEN + PAYLOAD for integrity.
* EOF      - End-Of-Frame sentinel, a final sanity check.
"""

from __future__ import annotations

# --- Framing markers --------------------------------------------------------
# 32 alternating bits. Long enough to detect + time-sync, short enough to keep
# packets quick.
PREAMBLE_BITS: list[int] = [0, 1] * 16

SFD: int = 0x7E   # 0111 1110 - start of frame delimiter
EOF: int = 0x7E   # end of frame sentinel

MAX_PAYLOAD_BYTES: int = 255  # LEN is a single byte.


# --- Bit <-> byte helpers ---------------------------------------------------
def byte_to_bits(value: int) -> list[int]:
    """Convert a single byte (0-255) to 8 bits, most-significant-bit first."""
    return [(value >> (7 - i)) & 1 for i in range(8)]


def bits_to_byte(bits: list[int]) -> int:
    """Convert 8 MSB-first bits back into a byte."""
    if len(bits) != 8:
        raise ValueError(f"expected 8 bits, got {len(bits)}")
    value = 0
    for bit in bits:
        value = (value << 1) | (bit & 1)
    return value


def bytes_to_bits(data: bytes) -> list[int]:
    """Flatten a byte string into an MSB-first bit list."""
    bits: list[int] = []
    for byte in data:
        bits.extend(byte_to_bits(byte))
    return bits


def bits_to_bytes(bits: list[int]) -> bytes:
    """Pack an MSB-first bit list into bytes. Length must be a multiple of 8."""
    if len(bits) % 8 != 0:
        raise ValueError("bit count must be a multiple of 8")
    out = bytearray()
    for i in range(0, len(bits), 8):
        out.append(bits_to_byte(bits[i : i + 8]))
    return bytes(out)


# --- Integrity check --------------------------------------------------------
def crc8(data: bytes) -> int:
    """Compute a CRC-8 checksum (polynomial 0x07, the CCITT variant).

    A CRC catches the bit errors that acoustic transmission inevitably
    introduces far better than a naive sum, while staying a single byte.
    """
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc
