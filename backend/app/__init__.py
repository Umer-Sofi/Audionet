"""AudioNet backend package.

AudioNet transmits text between two laptops using (near-)ultrasonic sound.
The data path is:

    text -> bits -> packet -> FSK modulation -> speaker
    microphone -> band-pass -> FFT -> FSK demodulation -> packet -> bits -> text

Every sub-package has a single, well defined responsibility:

    config/      static + runtime configuration
    modulation/  the DSP core (FSK modem)
    audio/       hardware I/O (speaker, mic) and signal helpers (filters, FFT)
    core/        protocol, packetizer and the high level TX/RX orchestrators
    ai/          heuristic environment analysis + frequency selection
    services/    stateful application services used by the API
    api/         FastAPI routes and Pydantic schemas
"""

__version__ = "0.1.0"
