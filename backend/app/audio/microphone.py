"""Continuous microphone capture into a thread-safe ring buffer.

The receiver needs to listen *forever* without blocking the web server, so we
open a non-blocking ``sounddevice.InputStream`` whose callback appends captured
frames into a fixed-size circular buffer. Consumers (the receiver loop, the AI
analyzer) can grab a snapshot of recent audio at any time.

Only this file talks to the input device.
"""

from __future__ import annotations

import threading

import numpy as np
import sounddevice as sd

from app.config.settings import get_settings


class Microphone:
    """A continuously-recording mic backed by a numpy ring buffer."""

    def __init__(self) -> None:
        settings = get_settings()
        self._fs = settings.sample_rate
        self._capacity = int(settings.ring_buffer_seconds * self._fs)
        self._buffer = np.zeros(self._capacity, dtype=np.float32)
        self._write = 0            # next write index
        self._filled = 0           # how many valid samples are stored
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    # --- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        """Open the input stream and begin recording."""
        if self._stream is not None:
            return
        settings = get_settings()
        self._stream = sd.InputStream(
            samplerate=self._fs,
            channels=1,
            dtype="float32",
            device=settings.input_device,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop and close the input stream."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    # --- capture callback ---------------------------------------------------
    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        """sounddevice callback - runs on the audio thread, keep it cheap."""
        if status:  # over/underflows etc. Non-fatal; we just keep going.
            pass
        mono = indata[:, 0]
        with self._lock:
            for chunk_start in range(0, mono.shape[0], self._capacity):
                chunk = mono[chunk_start : chunk_start + self._capacity]
                n = chunk.shape[0]
                end = self._write + n
                if end <= self._capacity:
                    self._buffer[self._write : end] = chunk
                else:  # wrap around
                    first = self._capacity - self._write
                    self._buffer[self._write :] = chunk[:first]
                    self._buffer[: n - first] = chunk[first:]
                self._write = end % self._capacity
                self._filled = min(self._filled + n, self._capacity)

    # --- readers ------------------------------------------------------------
    def snapshot(self) -> np.ndarray:
        """Return a copy of the buffered audio in chronological order."""
        with self._lock:
            if self._filled < self._capacity:
                return self._buffer[: self._filled].copy()
            # Buffer full: reorder so oldest sample comes first.
            return np.concatenate(
                (self._buffer[self._write :], self._buffer[: self._write])
            )

    def latest(self, seconds: float) -> np.ndarray:
        """Return (a copy of) the most recent ``seconds`` of audio."""
        n = int(seconds * self._fs)
        data = self.snapshot()
        return data[-n:] if data.shape[0] > n else data

    def clear(self) -> None:
        """Discard all buffered audio (used after a successful decode)."""
        with self._lock:
            self._buffer.fill(0.0)
            self._write = 0
            self._filled = 0
