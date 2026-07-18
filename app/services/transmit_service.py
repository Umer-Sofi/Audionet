"""Stateful transmit service behind ``POST /send``.

Wraps the :class:`Transmitter` and coordinates status with the receive service
so that:

* the node reports ``Sending`` while a transmission is in flight, and
* the background listener pauses decoding during that window (otherwise the
  sender would "hear" and decode its own message).

It reuses the microphone owned by the receive service so the AI can sense the
environment without opening a second input stream.
"""

from __future__ import annotations

from app.core.transmitter import Transmitter, TransmitReport
from app.services.receive_service import ReceiveService


class TransmitService:
    """Sends text messages as sound, coordinating status with receive."""

    def __init__(self, receive_service: ReceiveService) -> None:
        self._receive = receive_service
        # Share the mic so environment sensing uses the already-open stream.
        self._transmitter = Transmitter(mic=receive_service.mic)

    def send(self, message: str) -> TransmitReport:
        """Transmit ``message``; flip status to Sending for the duration."""
        self._receive.mark_sending()
        try:
            report = self._transmitter.send(message)
        finally:
            # Always restore listening even if playback raised.
            self._receive.mark_listening()
        # Clear any residual self-heard audio before we resume decoding.
        self._receive.mic.clear()
        return report
