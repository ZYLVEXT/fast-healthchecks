## 1.1.2 (2026-08-24)

### Fixes

- **dependencies**: support redis-py 8.x while retaining compatibility with 7.x

### Build

- **toolchain**: refresh GitHub Actions, uv, build, lint, typing, documentation, and locked development dependencies
- **quality**: document retained Ruff suppressions and focus Codacy on production sources

## 1.1.1 (2026-08-08)

### Fixes

- **postgresql**: honor SQLAlchemy asyncpg `ssl` DSN options, while rejecting conflicting `ssl` and `sslmode` values

## 1.1.0 (2026-08-08)

### Features

- **performance**: keep root imports lazy, skip body serialization for `204`, avoid disabled-log payloads, and remove scheduler hops from sequential probes
- **execution**: move probe execution and lifecycle ownership into the framework-neutral core and use direct sequential execution
- **lifecycle**: retain only resource-owning checks, deduplicate shared checks, and consolidate transport cleanup into one grace period
- **release**: add immutable tag-bound tests, reproducible artifacts, CycloneDX SBOMs, build attestations, Trusted Publishing, and guarded documentation deployment

### Fixes

- **security**: redact nested sensitive metadata and validate every URL redirect against the SSRF policy
- **postgresql**: preserve native asyncpg `sslmode` behavior and allow `verify-full` without a client certificate
- **docker**: make published service ports configurable through `.env` and keep CI connection settings aligned
- **ci**: stop printing credential-bearing DSNs in workflow logs
- **ci**: restore example service configuration in the cross-platform unit matrix and limit collection to unit tests
- **packaging**: make the Psycopg extra self-contained across supported operating systems
- **testing**: remove scheduler-sensitive timing margins from function-check tests
- **lifecycle**: close FastAPI example routers and temporary test files when setup or execution fails
- **docs**: align public API, lifecycle, execution, TLS, and test-matrix documentation with runtime behavior

### Build

- **packaging**: migrate builds to Hatchling with explicit wheel and source-distribution contents
- **testing**: enforce 100% branch coverage across import, integration, and unit suites
- **testing**: migrate integration event loops to the pytest-asyncio loop-factory hook
- **toolchain**: refresh build, lint, typing, test, and documentation tools and migrate repository hooks and CI from pre-commit to prek

## 1.0.0 (2026-03-13)

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
