# ADR 001: Health check contract (DSN, name, lifecycle)

## Status

Accepted.

## Context

Check classes need a consistent contract for DSN handling, display names, and client lifecycle.

## Decision

- **DSN**: `fast_healthchecks.dsn` provides NewTypes (AmqpDsn, RedisDsn, etc.) for typing only. Each `HealthCheckDSN` subclass implements `parse_dsn()` and `validate_dsn()`; no shared DSN runtime logic.
- **Name**: All checks expose `_name` (str), used in `HealthCheckResult` and error reporting. `_get_check_name()` falls back to `name` or `"Check-{index}"`.
- **Lifecycle**: `ClientCachingMixin._close_client(client)` must return `Awaitable[None]` (not `None`). Per-call checks (RabbitMQ, PostgreSQL) do not use `ClientCachingMixin`.
- **Config**: Connection-based checks accept an optional `config: XConfig | None`; when `None`, config is built from `**kwargs`. Config dataclasses live in `fast_healthchecks.checks.configs`, are immutable (frozen), and provide `to_dict()` for serialization. This avoids long parameter lists and centralizes `_build_dict()` logic.
