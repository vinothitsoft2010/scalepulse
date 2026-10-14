# Day 8: Data Models and Contracts

## PostgreSQL

Use relational tables for tenants, API key metadata, and rate-limit policies. Foreign keys keep keys and policies scoped to tenants; constraints reject invalid limits. Alembic records schema evolution so each environment can migrate repeatably.

## Cassandra

Cassandra is a wide-column database, not simply a generic document store. Its tables are designed around reads: recent telemetry by tenant, and recent telemetry by tenant plus route. Those query patterns justify denormalized tables. Time buckets and shards bound partition growth and spread hot tenants; their final size requires measured write volume and retention.

## Protobuf

The versioned telemetry message is an inter-service contract. Field numbers are part of the wire format and must not be reused after removal. Events carry IDs, route templates, status, timing, and byte counts, but not raw credentials or request bodies.

## Study prompts

1. Why can Cassandra duplicate the same event into more than one table?
2. What compatibility break can happen if a protobuf field number is reused?
