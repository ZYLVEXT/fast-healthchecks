# Fast Healthchecks

Framework-agnostic health checks with integrations for the most popular ASGI frameworks: [FastAPI](https://github.com/fastapi/fastapi) / [FastStream](https://github.com/airtai/faststream) / [Litestar](https://github.com/litestar-org/litestar) to help you implement the [Health Check API](https://microservices.io/patterns/observability/health-check-api.html) pattern.

## Documentation

- [Installation](installation.md) — install with pip, poetry, or uv; optional extras.
- [Usage](usage.md) — mount health checks per framework; examples (FastAPI, FastStream, Litestar).
- [Lifecycle and shutdown](lifecycle.md) — closing cached clients on app shutdown; [ProbeRunner](lifecycle.md#probe-runner-advanced) for advanced control.
- [Probe options](probe-options.md) — probe parameters and `build_probe_route_options`.
- [Running probes without ASGI](run-probe.md) — `run_probe` for CLI, cron, tests.
- [Configuration objects](configuration.md) — `config` argument and types in `fast_healthchecks.checks.configs`.
- [URL check and SSRF protection](ssrf.md) — `block_private_hosts` for `UrlHealthCheck`.
- [DSN formats](dsn-formats.md) — URL schemes for `from_dsn()`; PostgreSQL TLS certificate rotation.

For API reference (configs, check classes, public API boundary), see [API Reference](api.md).

## Additional Resources

- [Changelog](changelog.md) — release history and changes.
- [Style guide](style-guide.md) — code style conventions.
- [Contributing](contributing.md) — how to contribute to the project.
- [Security](security.md) — security policy and guidelines.
- [Decisions](decisions/README.md) — architectural decision records.
