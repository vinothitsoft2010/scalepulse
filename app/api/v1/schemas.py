from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    name: str
    created_at: datetime


class RateLimitPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    request_limit: int = Field(gt=0, le=9_223_372_036_854_775_807)
    window_ms: int = Field(gt=0, le=2_147_483_647)
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class RateLimitPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_id: UUID
    tenant_id: UUID
    name: str
    request_limit: int
    window_ms: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class APIKeyCreate(BaseModel):
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, expires_at: datetime | None) -> datetime | None:
        if expires_at is not None:
            if expires_at.tzinfo is None or expires_at.utcoffset() is None:
                raise ValueError("expires_at must include a timezone")
            if expires_at <= datetime.now(UTC):
                raise ValueError("expires_at must be in the future")
        return expires_at


class APIKeyIssued(BaseModel):
    api_key_id: UUID
    tenant_id: UUID
    policy_id: UUID
    key_prefix: str
    api_key: str
    created_at: datetime
    expires_at: datetime | None
