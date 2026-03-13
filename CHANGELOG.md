## Unreleased

### Features

- **execution**: add `ProbeRunner` class — async context manager for running health checks outside of ASGI applications; supports custom `run_policy`, probe options, timeout handling, and resource cleanup via `await runner.close()`
- **execution**: add `RunPolicy` dataclass to configure probe execution — `mode` (strict/reporting), `execution` (sequential/parallel), `probe_timeout_ms`, and `health_evaluation` (all_required/partial_allowed)
- **models**: add `HealthError` exception model with structured fields: `code` (error code), `message` (human-readable), `duration_ms`, `timeout_ms`, and `meta` (additional context with automatic secret redaction)
- **checks**: add optional config object: all connection-based checks accept `config: XConfig | None` and build from `**kwargs` when `config` is None; config dataclasses in `fast_healthchecks.checks.configs`
- **url**: when `block_private_hosts=True`, resolve URL host before request and reject loopback/private IPs (SSRF and DNS rebinding protection)
- **integrations**: add `healthcheck_shutdown`, `close_probes`, `run_probe` for resource cleanup and non-ASGI usage
- **integrations**: add runner injection — all integration functions (`health()`, `healthcheck_shutdown`, `run_probe`, `ProbeAsgi`, `HealthcheckRouter`) accept optional `runner` parameter to reuse ProbeRunner instances across requests
- **errors**: add centralized error mapping via `map_exception_to_health_error()` — maps common exceptions (TimeoutError, ValueError, OSError subclasses) to `HealthError` with appropriate error codes and metadata
- **errors**: automatic secret redaction — `HealthError.meta` filters out keys matching patterns `*password*`, `*secret*`, `*token*`, `*api_key*`, `*credential*` case-insensitively
- **integrations**: add `HealthcheckRouter.close()` for FastAPI lifespan shutdown
- **probe**: add `allow_partial_failure` option (healthy when at least one check passes)
- **checks**: add `aclose()` to Redis, Kafka, Mongo, OpenSearch, RabbitMQ, URL checks for client cleanup
- **kafka**: add `from_dsn()` and client caching
- **exceptions**: introduce documented exception hierarchy (`HealthCheckError`, `HealthCheckTimeoutError`, `HealthCheckSSRFError`). Timeout and SSRF validation now raise these subclasses; `except asyncio.TimeoutError` and `except ValueError` still work. See API reference for details.
- **ci**: bump workflow uses CHANGELOG.md only; optional input `increment` (PATCH/MINOR/MAJOR); replace `## Unreleased` header before bump for custom release notes, single commit per run
- **docker**: add healthchecks to Compose services, Kafka waits for healthy Zookeeper
- **docs**: document lifecycle, probe options, DSN formats, `run_probe` usage

### Fixes

- **dsn**: replace Pydantic with plain `str` and `urlsplit` validation
- **function**: use `get_running_loop()`, honor bool return from check function
- **default_handler**: return empty body for healthy responses (minimal JSON or None for 204)
- **dependencies**: drop pydantic extra, upgrade asyncpg, psycopg, redis, aiokafka, motor, fastapi, faststream, litestar, opensearch
- **justfile**: use `docker compose --wait`, add `pytest -n auto` for parallel tests
- **examples**: use factory functions instead of module-level probe constants
- **changelog**: fix typos in previous entries

### Refactor

- **checks**: config dataclasses in `configs.py`; `ToDictMixin` / `_build_dict` use config for serialization; long parameter lists replaced by single optional config (removes need for PLR0913 noqa in check constructors)
- **integrations**: unify probe execution: `ProbeAsgi` and `run_probe` share the same check execution and timeout logic in `integrations.base`
- **tests**: integration checks use async fixtures with `await check.aclose()` in teardown; remove `PytestUnraisableExceptionWarning` suppression from conftest
- **checks**: type `healthcheck_safe` with `typing.Concatenate` and remove both `type: ignore` in `_base.py` for the decorator
- **integrations**: `HealthcheckRouter`, `health()` (FastStream/Litestar), `ProbeAsgi`, and `build_health_routes` now accept only `options: ProbeRouteOptions | None` (see Breaking changes)
- **checks**: change `checks` from Iterable to Sequence
- **ci**: add composite actions (setup-test-env, upload-coverage), remove Pydantic matrix
- **project**: development status Planning → Production/Stable, license inline in pyproject
- **lint**: satisfy TC001/TC002/TC003 (typing-only imports under `TYPE_CHECKING`)
- **dependencies**: remove unused optional extra `msgspec`, remove redundant dev dependency `greenlet`

### Build / CI

- **ci**: add Dependabot, Rollback workflow, Release workflow (build and publish to PyPI), CodeQL, Dependency Review; remove 3_docs, 4_pythonpublish; update 1_test (Python 3.10–3.14 matrix, Windows + WSL, Docker Compose cache, justfile)
- **ci**: add pip-audit, split tests into imports/unit/integration, add scheduled runs
- **build**: add `.editorconfig`, `.gitattributes`; rename `.env` to `.env.example`; update `MANIFEST.in`

### Documentation

- **docs**: add CONTRIBUTING.md, SECURITY.md, docs structure (api, configuration, lifecycle, probe-options, dsn-formats, run-probe, ssrf, style-guide, decisions)
- **docs**: update README, installation, usage, changelog; single source of truth for documentation

### Breaking changes

- **integrations**: `HealthcheckRouter`, `health()` (FastStream/Litestar), `ProbeAsgi`, and `build_health_routes` now accept only `options: ProbeRouteOptions | None`. Passing `debug`, `prefix`, `success_handler`, etc. directly is no longer supported. **Migration:** build options with `build_probe_route_options(debug=..., prefix=..., ...)` and pass the result as `options=`. Example: `HealthcheckRouter(Probe(...), options=build_probe_route_options(debug=True, prefix="/health"))`.
- **models**: class `HealthcheckReport` renamed to `HealthCheckReport`. **Migration:** update imports and usages to `HealthCheckReport`.
- **probe**: type of `Probe.checks` changed from `Iterable[Check]` to `Sequence[Check]`. **Migration:** pass a list or tuple of checks, not a generator or one-shot iterable.
- **dependencies**: optional extras `pydantic` and `msgspec` removed. DSN and validation no longer use Pydantic. Minimum dependency versions updated (see pyproject.toml). **Migration:** remove `pydantic` or `msgspec` extras from your dependencies and upgrade packages to the versions specified in pyproject.toml if needed.

## 0.2.4 (2025-09-19)

### Fix

- **typing**: prevent typing from failing

## 0.2.3 (2025-09-19)

### Fix

- **all**: upgrade dependencies, make tests more stable, switch `mypy` to `ty`

## 0.2.2 (2025-04-16)

### Fix

- **all**: make PEP 561 compatible

## 0.2.1 (2025-03-07)

### Fix

- **mongo**: added multihost support for MongoDB

## 0.2.0 (2025-02-20)

### Feat

- **healthchecks**: added OpenSearch healthcheck

### Fix

- **dependencies**: upgrade github actions
- **vscode**: fixed ruff plugin setup
- **dependencies**: upgrade dependencies
- **dependencies**: upgrade pre-commit
- **docs**: typo in install commands

### Refactor

- **tests**: move `to_dict` method out of tests

## 0.1.5 (2025-01-23)

### Fix

- **redis**: added support for SSL connections

## 0.1.4 (2025-01-22)

### Fix

- **dependencies**: upgrade dependencies and pre-commit
- **mongo**: fixed Mongo check

## 0.1.3 (2024-12-10)

### Fix

- **validate_dsn**: removed dummy validation isinstance

## 0.1.2 (2024-12-10)

### Fix

- **setuptools**: included packages
- **docs**: changed logo for documentation to green color

## 0.1.1 (2024-12-09)

### Fix

- **docs**: fixed `README.md`

## 0.1.0 (2024-12-09)

### Feat

- **all**: 🚀 INIT
