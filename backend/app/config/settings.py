"""Central runtime configuration for AudioNet.

All tunable numbers live here so the rest of the codebase never hard-codes a
sample rate or baud rate. Values can be overridden with environment variables
(prefix ``AUDIONET_``) or a local ``.env`` file, which is handy when the two
laptops have different audio hardware.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    The defaults target *near-ultrasonic* transmission (~18-19 kHz): high
    enough to be (mostly) inaudible, low enough that typical laptop
    speakers/mics can still reproduce and capture it.
    """

    model_config = SettingsConfigDict(
        env_prefix="AUDIONET_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Audio hardware -----------------------------------------------------
    sample_rate: int = 48_000        # Hz. 48 kHz => Nyquist 24 kHz, room for 19 kHz.
    input_device: int | None = None  # sounddevice device index, None = default.
    output_device: int | None = None

    # --- FSK modem ----------------------------------------------------------
    baud: int = 50                   # symbols (bits) per second. Lower = robust.
    amplitude: float = 0.6           # output waveform amplitude in [0, 1].
    freq_shift: float = 600.0        # Hz between the '0' tone and the '1' tone.

    # --- Receiver -----------------------------------------------------------
    ring_buffer_seconds: float = 12.0    # how much audio the mic keeps in memory.
    receive_poll_interval: float = 0.35  # how often the RX loop scans the buffer.

    # --- AI frequency selection --------------------------------------------
    # Window (in seconds) of mic audio the environment analyzer inspects.
    noise_probe_seconds: float = 0.75

    @property
    def samples_per_bit(self) -> int:
        """Number of audio samples that make up one FSK symbol (one bit)."""
        return int(round(self.sample_rate / self.baud))


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton so every module shares the same config."""
    return Settings()
