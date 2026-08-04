"""Shared configuration for the API's Pydantic models."""

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """Base model with predictable, closed API schemas."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_default=True,
    )
