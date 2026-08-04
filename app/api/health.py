"""Service liveness endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings

router = APIRouter(tags=["Service"])


class HealthResponse(BaseModel):
    """Health endpoint payload."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="Current service health", examples=["healthy"])
    service: str = Field(
        description="Stable service identifier",
        examples=["integration-definition-validator"],
    )
    version: str = Field(description="Running service version", examples=["1.0.0"])


@router.get("/health", response_model=HealthResponse, summary="Check service health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Return a deterministic liveness response without external dependencies."""

    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.service_version,
    )
