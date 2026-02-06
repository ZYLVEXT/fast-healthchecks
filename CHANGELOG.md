## Unreleased

### Feat

- **integrations**: add `healthcheck_shutdown`, `close_probes`, `run_probe` for resource cleanup and non-ASGI usage
- **integrations**: add `HealthcheckRouter.close()` for FastAPI lifespan shutdown
- **probe**: add `allow_partial_failure` option (healthy when at least one check passes)
- **checks**: add `aclose()` to Redis, Kafka, Mongo, OpenSearch, URL checks for client cleanup
- **kafka**: add `from_dsn()` and client caching
- **ci**: add pip-audit job, split tests into imports/unit/integration, add scheduled runs
- **ci**: add workflow inputs for bump (increment, release_notes)
- **docker**: add healthchecks to Compose services, Kafka waits for healthy Zookeeper
- **docs**: document lifecycle, probe options, DSN formats, `run_probe` usage

### Fix

- **dsn**: replace Pydantic with plain `str` and `urlsplit` validation
- **function**: use `get_running_loop()`, honor bool return from check function
- **default_handler**: return empty body for healthy responses
- **dependencies**: drop pydantic extra, upgrade asyncpg, psycopg, redis, aiokafka, motor, fastapi, faststream, litestar, opensearch
- **makefile**: use `docker compose --wait`, add `pytest -n auto` for parallel tests
- **examples**: use factory functions instead of module-level probe constants
- **changelog**: fix typos in previous entries

### Refactor

- **checks**: change `checks` from Iterable to Sequence
- **ci**: add composite actions (setup-test-env, upload-coverage), remove Pydantic matrix
- **project**: development status Planning → Production/Stable, license inline in pyproject

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
