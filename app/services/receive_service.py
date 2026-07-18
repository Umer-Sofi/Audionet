"""Stateful receive service: owns the mic and the background listening loop.

This is the long-lived object behind ``GET /received`` and ``GET /status``. It:

* owns the shared :class:`Microphone` (also used by the transmitter's AI),
* runs a background thread that repeatedly scans recent audio for a valid
  frame, and
* holds the node's coarse status and the most recently decoded message.

State is guarded by a lock because the audio callback, the listener thread and
the FastAPI request handlers all touch it.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum

from app.audio.microphone import Microphone
from app.config.settings import get_settings
from app.core.receiver import Receiver


class Status(str, Enum):
    """Coarse node state exposed by the API."""

    IDLE = "Idle"
    LISTENING = "Listening"
    SENDING = "Sending"


@dataclass
class ReceivedMessage:
    """The last successfully received message and how it arrived."""

    message: str
    base_frequency: float
    sync_score: float


class ReceiveService:
    """Continuously listens for AudioNet frames on a background thread."""

    def __init__(self) -> None:
        self.mic = Microphone()
        self._receiver = Receiver()
        self._lock = threading.Lock()
        self._status: Status = Status.IDLE
        self._last: ReceivedMessage | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    # --- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        """Start recording and the background listen loop.

        A microphone failure (e.g. permission not yet granted) is non-fatal:
        the server still boots so ``/send`` works and status simply stays
        ``Idle`` until the mic becomes available.
        """
        if self._running:
            return
        try:
            self.mic.start()
        except Exception as exc:  # noqa: BLE001 - surface, don't crash startup
            print(f"[audionet] microphone unavailable, not listening: {exc}")
            self._set_status(Status.IDLE)
            return
        self._running = True
        self._set_status(Status.LISTENING)
        self._thread = threading.Thread(target=self._loop, name="audionet-rx", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the listen loop and release the mic."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.mic.stop()
        self._set_status(Status.IDLE)

    # --- background loop ----------------------------------------------------
    def _loop(self) -> None:
        settings = get_settings()
        poll = settings.receive_poll_interval
        stop_event = threading.Event()
        while self._running:
            # Don't try to decode our own outgoing transmission.
            if self.status is not Status.SENDING:
                signal = self.mic.snapshot()
                report = self._receiver.try_decode(signal)
                if report is not None:
                    with self._lock:
                        self._last = ReceivedMessage(
                            message=report.message,
                            base_frequency=report.plan.base,
                            sync_score=report.sync_score,
                        )
                    # Drop the consumed audio so we don't re-decode it.
                    self.mic.clear()
            stop_event.wait(poll)

    # --- thread-safe state accessors ---------------------------------------
    def _set_status(self, status: Status) -> None:
        with self._lock:
            self._status = status

    def mark_sending(self) -> None:
        """Called by the transmit service around a send."""
        self._set_status(Status.SENDING)

    def mark_listening(self) -> None:
        self._set_status(Status.LISTENING if self._running else Status.IDLE)

    @property
    def status(self) -> Status:
        with self._lock:
            return self._status

    @property
    def last_message(self) -> ReceivedMessage | None:
        with self._lock:
            return self._last
