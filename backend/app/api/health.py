import logging
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str = "labelsure-api"
    version: str = "0.3.0"
    database: Literal["connected", "unavailable"]
    phase: int = 3


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health(request: Request):
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Database readiness check failed")
        return JSONResponse(status_code=503, content=HealthResponse(
            status="degraded", database="unavailable"
        ).model_dump())
    return HealthResponse(status="ok", database="connected")
