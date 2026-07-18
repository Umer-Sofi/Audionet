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

    message: str
    payload: bytes
    crc_ok: bool


def build_frame_bits(message: str) -> list[int]:
    """Encode a text message into the full framed bit sequence to modulate.

    Returns the concatenation of preamble + SFD + LEN + payload + CRC + EOF as
    a flat list of 0/1 ints.
    """
    payload = message.encode("utf-8")
    if len(payload) > protocol.MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"message too long: {len(payload)} bytes "
            f"(max {protocol.MAX_PAYLOAD_BYTES})"
        )

    length = len(payload)
    # CRC covers the length byte + payload so both are protected.
    crc = protocol.crc8(bytes([length]) + payload)

    bits: list[int] = []
    bits.extend(protocol.PREAMBLE_BITS)
    bits.extend(protocol.byte_to_bits(protocol.SFD))
    bits.extend(protocol.byte_to_bits(length))
    bits.extend(protocol.bytes_to_bits(payload))
    bits.extend(protocol.byte_to_bits(crc))
    bits.extend(protocol.byte_to_bits(protocol.EOF))
    return bits


# Number of framing/sync bits the receiver must line up before the payload.
SYNC_BITS = len(protocol.PREAMBLE_BITS) + 8  # preamble + SFD


def parse_after_sfd(bits: list[int]) -> ParsedPacket | None:
    """Parse a bitstream that begins immediately *after* the SFD byte.

    ``bits`` should start at the LEN field. Returns a :class:`ParsedPacket` on a
    structurally valid frame (CRC may still be flagged bad), or ``None`` if
    there simply are not enough bits to contain a complete frame.
    """
    if len(bits) < 8:
        return None

    length = protocol.bits_to_byte(bits[0:8])

    # Bits required for LEN + payload + CRC (+ EOF).
    need = 8 + length * 8 + 8 + 8
    if len(bits) < need:
        return None

    idx = 8
    payload_bits = bits[idx : idx + length * 8]
    idx += length * 8
    crc_rx = protocol.bits_to_byte(bits[idx : idx + 8])
    idx += 8
    eof_rx = protocol.bits_to_byte(bits[idx : idx + 8])

    payload = protocol.bits_to_bytes(payload_bits) if length else b""
    crc_calc = protocol.crc8(bytes([length]) + payload)
    crc_ok = (crc_rx == crc_calc) and (eof_rx == protocol.EOF)

    try:
        message = payload.decode("utf-8")
    except UnicodeDecodeError:
        # Corrupted payload that happens to pass structural checks.
        message = ""
        crc_ok = False

    return ParsedPacket(message=message, payload=payload, crc_ok=crc_ok)
