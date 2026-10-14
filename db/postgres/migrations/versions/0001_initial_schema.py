"""Create tenant, API key, and rate-limit policy tables."""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tenants (
            tenant_id uuid PRIMARY KEY,
            name text NOT NULL CHECK (length(trim(name)) > 0),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE rate_limit_policies (
            policy_id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL REFERENCES tenants (tenant_id),
            name text NOT NULL CHECK (length(trim(name)) > 0),
            request_limit bigint NOT NULL CHECK (request_limit > 0),
            window_ms integer NOT NULL CHECK (window_ms > 0),
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, policy_id),
            UNIQUE (tenant_id, name)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE api_keys (
            api_key_id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL REFERENCES tenants (tenant_id),
            policy_id uuid NOT NULL,
            key_digest bytea NOT NULL UNIQUE CHECK (octet_length(key_digest) = 32),
            key_prefix text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz,
            revoked_at timestamptz,
            FOREIGN KEY (tenant_id, policy_id)
                REFERENCES rate_limit_policies (tenant_id, policy_id),
            CHECK (expires_at IS NULL OR expires_at > created_at)
        )
        """
    )
    op.execute("CREATE INDEX api_keys_tenant_id_idx ON api_keys (tenant_id)")
    op.execute(
        "CREATE INDEX api_keys_active_tenant_idx ON api_keys (tenant_id, api_key_id) "
        "WHERE revoked_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE api_keys")
    op.execute("DROP TABLE rate_limit_policies")
    op.execute("DROP TABLE tenants")
