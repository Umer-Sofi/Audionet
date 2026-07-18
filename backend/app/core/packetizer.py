"""Build and parse AudioNet frames.

The packetizer sits between *text* and *bits*. It turns a message into the
framed bit sequence described in :mod:`app.core.protocol`, and reverses the
process on receive while validating length, checksum and framing markers.

It deliberately knows nothing about audio or FSK - it only shuffles bits.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core import protocol


@dataclass
class ParsedPacket:
    """Result of parsing a candidate bitstream after the SFD."""

    dst: int
    src: int
    message: str
    payload: bytes
    crc_ok: bool


def build_frame_bits(message: str, dst: int, src: int) -> list[int]:
    """Encode a text message into the full framed bit sequence to modulate.

    Args:
        message: the text to send.
        dst:     destination address (0 = broadcast).
        src:     this device's address.

    Returns the concatenation of preamble + SFD + DST + SRC + LEN + payload +
    CRC + EOF as a flat list of 0/1 ints.
    """
    payload = message.encode("utf-8")
    if len(payload) > protocol.MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"message too long: {len(payload)} bytes "
            f"(max {protocol.MAX_PAYLOAD_BYTES})"
        )

    length = len(payload)
    dst &= 0xFF
    src &= 0xFF
    # CRC covers dst + src + length + payload so all header fields are protected.
    crc = protocol.crc8(bytes([dst, src, length]) + payload)

    bits: list[int] = []
    bits.extend(protocol.PREAMBLE_BITS)
    bits.extend(protocol.byte_to_bits(protocol.SFD))
    bits.extend(protocol.byte_to_bits(dst))
    bits.extend(protocol.byte_to_bits(src))
    bits.extend(protocol.byte_to_bits(length))
    bits.extend(protocol.bytes_to_bits(payload))
    bits.extend(protocol.byte_to_bits(crc))
    bits.extend(protocol.byte_to_bits(protocol.EOF))
    return bits


# Number of framing/sync bits the receiver must line up before the payload.
SYNC_BITS = len(protocol.PREAMBLE_BITS) + 8  # preamble + SFD


def parse_after_sfd(bits: list[int]) -> ParsedPacket | None:
    """Parse a bitstream that begins immediately *after* the SFD byte.

    ``bits`` should start at the DST field. Returns a :class:`ParsedPacket` on a
    structurally valid frame (CRC may still be flagged bad), or ``None`` if
    there simply are not enough bits to contain a complete frame.
    """
    # Need at least DST + SRC + LEN to read the length.
    if len(bits) < 24:
        return None

    dst = protocol.bits_to_byte(bits[0:8])
    src = protocol.bits_to_byte(bits[8:16])
    length = protocol.bits_to_byte(bits[16:24])

    # Bits required for DST + SRC + LEN + payload + CRC + EOF.
    need = 24 + length * 8 + 8 + 8
    if len(bits) < need:
        return None

    idx = 24
    payload_bits = bits[idx : idx + length * 8]
    idx += length * 8
    crc_rx = protocol.bits_to_byte(bits[idx : idx + 8])
    idx += 8
    eof_rx = protocol.bits_to_byte(bits[idx : idx + 8])

    payload = protocol.bits_to_bytes(payload_bits) if length else b""
    crc_calc = protocol.crc8(bytes([dst, src, length]) + payload)
    crc_ok = (crc_rx == crc_calc) and (eof_rx == protocol.EOF)

    try:
        message = payload.decode("utf-8")
    except UnicodeDecodeError:
        # Corrupted payload that happens to pass structural checks.
        message = ""
        crc_ok = False

    return ParsedPacket(dst=dst, src=src, message=message, payload=payload, crc_ok=crc_ok)
