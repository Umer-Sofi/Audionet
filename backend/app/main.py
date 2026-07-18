"""AudioNet FastAPI application entry point.

Wires the services together, starts the background microphone listener on
startup, and stops it cleanly on shutdown.

Run with::

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Run the same backend on both laptops. Use ``POST /send`` on one and poll
``GET /received`` on the other.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.receive_service import ReceiveService
from app.services.transmit_service import TransmitService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create services, begin listening, and tear down on shutdown."""
    receive_service = ReceiveService()
    transmit_service = TransmitService(receive_service)

    app.state.receive_service = receive_service
    app.state.transmit_service = transmit_service

    # Begin continuous listening immediately so the node is ready to receive.
    receive_service.start()
    try:
        yield
    finally:
        receive_service.stop()


app = FastAPI(
    title="AudioNet",
    version="0.1.0",
    description="Exchange text between laptops over (near-)ultrasonic sound.",
    lifespan=lifespan,
)

# The frontend lives in a separate folder / origin, so allow browser calls.
# Permissive CORS is fine for a local demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Simple liveness/info endpoint."""
    return {
        "service": "AudioNet",
        "endpoints": "POST /send, GET /received, GET /status",
    }
