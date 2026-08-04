"""Validation rule discovery endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import RulesResponse
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/api/v1", tags=["Validation"])


def get_validation_service() -> ValidationService:
    """Construct the stateless validation orchestrator for a request."""

    return ValidationService()


@router.get("/rules", response_model=RulesResponse, summary="List validation rules")
def list_rules(
    service: Annotated[ValidationService, Depends(get_validation_service)],
) -> RulesResponse:
    """Describe every rule currently evaluated by the service."""

    return RulesResponse(rules=service.list_rules())
