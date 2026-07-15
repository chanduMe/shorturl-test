from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.alias import ALIAS_PATTERN, is_reserved


class CreateUrlRequest(BaseModel):
    url: str = Field(..., description="The long URL to shorten.")
    custom_alias: str | None = Field(
        default=None,
        description="Optional custom alias (3-32 chars: letters, digits, '-', '_').",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("url must start with http:// or https://")
        if len(v) > 8192:
            raise ValueError("url is too long")
        return v

    @field_validator("custom_alias")
    @classmethod
    def validate_custom_alias(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not ALIAS_PATTERN.fullmatch(v):
            raise ValueError(
                "custom_alias must be 3-32 chars: letters, digits, '-' or '_'"
            )
        if is_reserved(v):
            raise ValueError("custom_alias is reserved")
        return v


class UrlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alias: str
    short_url: str
    long_url: str
    created_at: datetime
    access_count: int
    last_accessed_at: datetime | None = None
