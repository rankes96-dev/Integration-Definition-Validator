"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _cors_origins_from_environment() -> tuple[str, ...]:
    raw_value = os.getenv("CORS_ALLOWED_ORIGINS", "")
    return tuple(origin.strip() for origin in raw_value.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings that can be safely shared by application instances."""

    service_name: str = "integration-definition-validator"
    service_version: str = "1.0.0"
    max_request_body_bytes: int = 256 * 1024
    cors_allowed_origins: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return immutable application settings read from the environment."""

    return Settings(cors_allowed_origins=_cors_origins_from_environment())
