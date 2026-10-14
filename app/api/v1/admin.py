import hashlib
import hmac
from hmac import compare_digest
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.responses import Response

from app.api.v1.schemas import (
    APIKeyCreate,
    APIKeyIssued,
    RateLimitPolicyCreate,
    RateLimitPolicyRead,
    TenantCreate,
    TenantRead,
)
from app.core.rate_limit import RedisSlidingWindowLimiter
from app.repositories import admin as repository


async def require_admin(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    configured_token = request.app.state.settings.admin_token
    if configured_token is None or not configured_token.get_secret_value():
        raise HTTPException(status_code=503, detail="admin_api_not_configured")

    scheme, separator, provided_token = (authorization or "").partition(" ")
    expected_token = configured_token.get_secret_value()
    if (
        not separator
        or scheme.lower() != "bearer"
        or not provided_token.isascii()
        or not compare_digest(provided_token, expected_token)
    ):
        raise HTTPException(
            status_code=401,
            detail="invalid_admin_token",
            headers={"WWW-Authenticate": "Bearer"},
        )


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def get_database_engine(request: Request) -> AsyncEngine:
    engine = request.app.state.database_engine
    if engine is None:
        raise HTTPException(status_code=503, detail="database_not_configured")
    return engine


def database_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="database_unavailable")


@router.post("/tenants", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(payload: TenantCreate, request: Request) -> TenantRead:
    engine = get_database_engine(request)
    try:
        tenant = await repository.create_tenant(engine, payload.name)
    except SQLAlchemyError as error:
        raise database_unavailable() from error
    return TenantRead.model_validate(tenant)


@router.get("/tenants", response_model=list[TenantRead])
async def get_tenants(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TenantRead]:
    engine = get_database_engine(request)
    try:
        tenants = await repository.list_tenants(engine, limit, offset)
    except SQLAlchemyError as error:
        raise database_unavailable() from error
    return [TenantRead.model_validate(tenant) for tenant in tenants]


@router.post(
    "/tenants/{tenant_id}/policies",
    response_model=RateLimitPolicyRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_rate_limit_policy(
    tenant_id: UUID,
    payload: RateLimitPolicyCreate,
    request: Request,
) -> RateLimitPolicyRead:
    engine = get_database_engine(request)
    try:
        policy = await repository.create_policy(
            engine,
            tenant_id,
            payload.name,
            payload.request_limit,
            payload.window_ms,
            payload.enabled,
        )
    except repository.TenantNotFoundError as error:
        raise HTTPException(status_code=404, detail="tenant_not_found") from error
    except repository.PolicyNameConflictError as error:
        raise HTTPException(status_code=409, detail="policy_name_already_exists") from error
    except SQLAlchemyError as error:
        raise database_unavailable() from error
    return RateLimitPolicyRead.model_validate(policy)


@router.get(
    "/tenants/{tenant_id}/policies",
    response_model=list[RateLimitPolicyRead],
)
async def get_rate_limit_policies(
    tenant_id: UUID,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RateLimitPolicyRead]:
    engine = get_database_engine(request)
    try:
        policies = await repository.list_policies(engine, tenant_id, limit, offset)
    except repository.TenantNotFoundError as error:
        raise HTTPException(status_code=404, detail="tenant_not_found") from error
    except SQLAlchemyError as error:
        raise database_unavailable() from error
    return [RateLimitPolicyRead.model_validate(policy) for policy in policies]


@router.post(
    "/tenants/{tenant_id}/policies/{policy_id}/api-keys",
    response_model=APIKeyIssued,
    status_code=status.HTTP_201_CREATED,
)
async def issue_api_key(
    tenant_id: UUID,
    policy_id: UUID,
    payload: APIKeyCreate,
    request: Request,
) -> APIKeyIssued:
    engine = get_database_engine(request)
    pepper = request.app.state.settings.api_key_pepper
    if pepper is None or not pepper.get_secret_value():
        raise HTTPException(status_code=503, detail="api_key_pepper_not_configured")

    api_key = f"sp_live_{token_urlsafe(32)}"
    key_digest = hmac.new(
        pepper.get_secret_value().encode(), api_key.encode(), hashlib.sha256
    ).digest()
    try:
        key = await repository.create_api_key(
            engine,
            tenant_id,
            policy_id,
            key_digest,
            api_key[:14],
            payload.expires_at,
        )
    except repository.PolicyNotFoundError as error:
        raise HTTPException(status_code=404, detail="policy_not_found") from error
    except repository.PolicyDisabledError as error:
        raise HTTPException(status_code=409, detail="policy_disabled") from error
    except SQLAlchemyError as error:
        raise database_unavailable() from error
    return APIKeyIssued.model_validate({**key, "api_key": api_key})


@router.delete(
    "/tenants/{tenant_id}/api-keys/{api_key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_api_key(
    tenant_id: UUID,
    api_key_id: UUID,
    request: Request,
) -> Response:
    engine = get_database_engine(request)
    try:
        key_digest = await repository.revoke_api_key(engine, tenant_id, api_key_id)
    except SQLAlchemyError as error:
        raise database_unavailable() from error
    if key_digest is None:
        raise HTTPException(status_code=404, detail="api_key_not_found")

    redis_client = request.app.state.redis_client
    limiter: RedisSlidingWindowLimiter | None = request.app.state.rate_limiter
    if redis_client is None or limiter is None:
        raise HTTPException(status_code=503, detail="redis_not_configured")
    digest_hex = key_digest.hex()
    try:
        await redis_client.delete(
            limiter.api_key_cache_key(digest_hex),
            limiter.counter_key(digest_hex),
        )
    except RedisError as error:
        raise HTTPException(status_code=503, detail="redis_unavailable") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
