"""Integration definition validation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.rules import get_validation_service
from app.models import (
    IntegrationDefinition,
    InternalServerErrorResponse,
    RequestBodyTooLargeResponse,
    SchemaValidationErrorResponse,
    ValidationResponse,
)
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/api/v1", tags=["Validation"])


@router.post(
    "/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate an integration definition",
    responses={
        413: {
            "model": RequestBodyTooLargeResponse,
            "description": "The request body exceeds 256 KiB",
        },
        422: {
            "model": SchemaValidationErrorResponse,
            "description": "The request does not match the integration schema",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "The validation request could not be completed",
        },
    },
)
def validate_integration(
    definition: IntegrationDefinition,
    service: Annotated[ValidationService, Depends(get_validation_service)],
) -> ValidationResponse:
    """Perform static validation only; no input is stored and no API is called."""

    return service.validate(definition)
