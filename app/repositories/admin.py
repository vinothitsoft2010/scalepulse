from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine


class TenantNotFoundError(Exception):
    pass


class PolicyNameConflictError(Exception):
    pass


class PolicyNotFoundError(Exception):
    pass


class PolicyDisabledError(Exception):
    pass


async def create_tenant(engine: AsyncEngine, name: str) -> dict[str, object]:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                "INSERT INTO tenants (tenant_id, name) "
                "VALUES (:tenant_id, :name) "
                "RETURNING tenant_id, name, created_at"
            ),
            {"tenant_id": uuid4(), "name": name},
        )
        return dict(result.mappings().one())


async def list_tenants(engine: AsyncEngine, limit: int, offset: int) -> list[dict[str, object]]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT tenant_id, name, created_at FROM tenants "
                "ORDER BY created_at DESC, tenant_id LIMIT :limit OFFSET :offset"
            ),
            {"limit": limit, "offset": offset},
        )
        return [dict(row) for row in result.mappings()]


async def create_policy(
    engine: AsyncEngine,
    tenant_id: UUID,
    name: str,
    request_limit: int,
    window_ms: int,
    enabled: bool,
) -> dict[str, object]:
    async with engine.begin() as connection:
        tenant = await connection.execute(
            text("SELECT 1 FROM tenants WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        if tenant.scalar_one_or_none() is None:
            raise TenantNotFoundError

        try:
            result = await connection.execute(
                text(
                    "INSERT INTO rate_limit_policies "
                    "(policy_id, tenant_id, name, request_limit, window_ms, enabled) "
                    "VALUES (:policy_id, :tenant_id, :name, :request_limit, :window_ms, :enabled) "
                    "RETURNING policy_id, tenant_id, name, request_limit, window_ms, enabled, "
                    "created_at, updated_at"
                ),
                {
                    "policy_id": uuid4(),
                    "tenant_id": tenant_id,
                    "name": name,
                    "request_limit": request_limit,
                    "window_ms": window_ms,
                    "enabled": enabled,
                },
            )
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) == "23505":
                raise PolicyNameConflictError from error
            raise

        return dict(result.mappings().one())


async def list_policies(
    engine: AsyncEngine,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> list[dict[str, object]]:
    async with engine.connect() as connection:
        tenant = await connection.execute(
            text("SELECT 1 FROM tenants WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        if tenant.scalar_one_or_none() is None:
            raise TenantNotFoundError

        result = await connection.execute(
            text(
                "SELECT policy_id, tenant_id, name, request_limit, window_ms, enabled, "
                "created_at, updated_at FROM rate_limit_policies "
                "WHERE tenant_id = :tenant_id "
                "ORDER BY created_at DESC, policy_id LIMIT :limit OFFSET :offset"
            ),
            {"tenant_id": tenant_id, "limit": limit, "offset": offset},
        )
        return [dict(row) for row in result.mappings()]


async def create_api_key(
    engine: AsyncEngine,
    tenant_id: UUID,
    policy_id: UUID,
    key_digest: bytes,
    key_prefix: str,
    expires_at: object | None,
) -> dict[str, object]:
    async with engine.begin() as connection:
        policy = await connection.execute(
            text(
                "SELECT enabled FROM rate_limit_policies "
                "WHERE tenant_id = :tenant_id AND policy_id = :policy_id"
            ),
            {"tenant_id": tenant_id, "policy_id": policy_id},
        )
        policy_enabled = policy.scalar_one_or_none()
        if policy_enabled is None:
            raise PolicyNotFoundError
        if not policy_enabled:
            raise PolicyDisabledError

        result = await connection.execute(
            text(
                "INSERT INTO api_keys "
                "(api_key_id, tenant_id, policy_id, key_digest, key_prefix, expires_at) "
                "VALUES (:api_key_id, :tenant_id, :policy_id, :key_digest, "
                ":key_prefix, :expires_at) "
                "RETURNING api_key_id, tenant_id, policy_id, key_prefix, created_at, expires_at"
            ),
            {
                "api_key_id": uuid4(),
                "tenant_id": tenant_id,
                "policy_id": policy_id,
                "key_digest": key_digest,
                "key_prefix": key_prefix,
                "expires_at": expires_at,
            },
        )
        return dict(result.mappings().one())


async def get_rate_limit_metadata(
    engine: AsyncEngine, key_digest: bytes
) -> dict[str, object] | None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT api_keys.api_key_id::text AS api_key_id, "
                "rate_limit_policies.policy_id::text AS policy_id, "
                "rate_limit_policies.request_limit, rate_limit_policies.window_ms, "
                "rate_limit_policies.enabled, "
                "CASE WHEN api_keys.expires_at IS NULL THEN NULL "
                "ELSE floor(extract(epoch FROM api_keys.expires_at) * 1000)::bigint "
                "END AS expires_at_ms "
                "FROM api_keys "
                "JOIN rate_limit_policies ON rate_limit_policies.tenant_id = api_keys.tenant_id "
                "AND rate_limit_policies.policy_id = api_keys.policy_id "
                "WHERE api_keys.key_digest = :key_digest "
                "AND api_keys.revoked_at IS NULL "
                "AND (api_keys.expires_at IS NULL OR api_keys.expires_at > now())"
            ),
            {"key_digest": key_digest},
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None


async def revoke_api_key(engine: AsyncEngine, tenant_id: UUID, api_key_id: UUID) -> bytes | None:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                "UPDATE api_keys SET revoked_at = now() "
                "WHERE tenant_id = :tenant_id AND api_key_id = :api_key_id "
                "AND revoked_at IS NULL RETURNING key_digest"
            ),
            {"tenant_id": tenant_id, "api_key_id": api_key_id},
        )
        return result.scalar_one_or_none()
