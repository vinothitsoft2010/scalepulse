CREATE KEYSPACE IF NOT EXISTS scalepulse_dev
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE scalepulse_dev;

CREATE TABLE IF NOT EXISTS telemetry_by_tenant_bucket (
    tenant_id uuid,
    bucket_start timestamp,
    shard tinyint,
    occurred_at timestamp,
    event_id uuid,
    api_key_id uuid,
    route_template text,
    method text,
    status_code smallint,
    latency_microseconds bigint,
    request_bytes bigint,
    response_bytes bigint,
    outcome text,
    PRIMARY KEY ((tenant_id, bucket_start, shard), occurred_at, event_id)
) WITH CLUSTERING ORDER BY (occurred_at DESC, event_id ASC);

CREATE TABLE IF NOT EXISTS telemetry_by_route_bucket (
    tenant_id uuid,
    route_template text,
    bucket_start timestamp,
    shard tinyint,
    occurred_at timestamp,
    event_id uuid,
    api_key_id uuid,
    method text,
    status_code smallint,
    latency_microseconds bigint,
    request_bytes bigint,
    response_bytes bigint,
    outcome text,
    PRIMARY KEY ((tenant_id, route_template, bucket_start, shard), occurred_at, event_id)
) WITH CLUSTERING ORDER BY (occurred_at DESC, event_id ASC);
