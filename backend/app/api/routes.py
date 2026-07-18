"""FastAPI routes for AudioNet.

Three endpoints, matching the project spec:

    POST /send      - transmit a text message as sound
    GET  /received  - fetch the most recently decoded message
    GET  /status    - report Idle / Listening / Sending

Services are resolved from ``app.state`` (wired up in :mod:`app.main`) via
dependency functions, so handlers stay tiny and testable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.schemas import (
    ConfigResponse,
    ReceivedResponse,
    SendRequest,
    SendResponse,
    StatusResponse,
)
from app.config.frequencies import candidate_plans, default_plan
from app.config.settings import get_settings
from app.services.receive_service import ReceiveService
from app.services.transmit_service import TransmitService

router = APIRouter()


# --- dependency providers ---------------------------------------------------
def get_transmit_service(request: Request) -> TransmitService:
    return request.app.state.transmit_service


def get_receive_service(request: Request) -> ReceiveService:
    return request.app.state.receive_service


# --- endpoints --------------------------------------------------------------
@router.post("/send", response_model=SendResponse)
def send_message(
    body: SendRequest,
    tx: TransmitService = Depends(get_transmit_service),
) -> SendResponse:
    """Transmit ``body.message`` acoustically and report the chosen channel."""
    if not body.encoded_length_ok():
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="message too long for a single frame",
        )
    report = tx.send(body.message)
    return SendResponse(
        status="sent",
        base_frequency=report.plan.base,
        rationale=report.rationale,
        duration_seconds=round(report.duration_seconds, 3),
    )


@router.get("/received", response_model=ReceivedResponse)
def get_received(
    rx: ReceiveService = Depends(get_receive_service),
) -> ReceivedResponse:
    """Return the most recently decoded message (empty if none yet)."""
    last = rx.last_message
    if last is None:
        return ReceivedResponse(id=0, message="")
    return ReceivedResponse(
        id=last.id,
        message=last.message,
        base_frequency=last.base_frequency,
        sync_score=round(last.sync_score, 3),
    )


@router.get("/status", response_model=StatusResponse)
def get_status(
    rx: ReceiveService = Depends(get_receive_service),
) -> StatusResponse:
    """Return the coarse node status: Idle, Listening or Sending."""
    return StatusResponse(status=rx.status.value)


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """Return the real modem parameters so the UI can display them."""
    settings = get_settings()
    return ConfigResponse(
        sample_rate=settings.sample_rate,
        baud=settings.baud,
        freq_shift=settings.freq_shift,
        frequencies=[p.base for p in candidate_plans()],
        default_frequency=default_plan().base,
    )
