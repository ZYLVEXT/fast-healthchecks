<h1 align="center" style="vertical-align: middle;">
  <img src="./img/black.svg" width="30"> <strong>FastHealthcheck</strong>
</h1>

<b>Framework-agnostic health checks with integrations for the most popular ASGI frameworks: [FastAPI](https://github.com/fastapi/fastapi) / [Faststream](https://github.com/airtai/faststream) / [Litestar](https://github.com/litestar-org/litestar) to help you implement the [Health Check API](https://microservices.io/patterns/observability/health-check-api.html) pattern</b>

---

## Installation

With `pip`:
```bash
pip install fast-healthchecks
```

With `poetry`:
```bash
poetry add fast-healthchecks
```

With `uv`:
```bash
uv add fast-healthchecks
```

Backends (Redis, Kafka, Mongo, PostgreSQL, etc.) and framework integrations are optional. Install the extras you need, e.g. `pip install fast-healthchecks[redis]` or `pip install fast-healthchecks[redis,mongo,fastapi]`. See the project's `pyproject.toml` for all extra names (asyncpg, psycopg, redis, aio-pika, httpx, aiokafka, motor, fastapi, faststream, litestar, opensearch).

## Usage

The easiest way to use this package is the **`health`** function.

Create the health check endpoint dynamically using different conditions.
Each condition is a callable, and you can even have dependencies inside it:

=== "examples/probes.py"

    ```python
    {%
        include-markdown "../examples/probes.py"
    %}
    ```

=== "FastAPI"

    ```python
    {%
        include-markdown "../examples/fastapi_example/main.py"
    %}
    ```

=== "Faststream"

    ```python
    {%
        include-markdown "../examples/faststream_example/main.py"
    %}
    ```

=== "Litestar"

    ```python
    {%
        include-markdown "../examples/litestar_example/main.py"
    %}
    ```

You can find examples for each framework here:

- [FastAPI example](https://github.com/shepilov-vladislav/fast-healthchecks/tree/main/examples/fastapi_example)
- [Faststream example](https://github.com/shepilov-vladislav/fast-healthchecks/tree/main/examples/faststream_example)
- [Litestar example](https://github.com/shepilov-vladislav/fast-healthchecks/tree/main/examples/litestar_example)

## Lifecycle and shutdown

Checks that cache a client (Redis, Mongo, Kafka, OpenSearch, URL) keep one connection per instance. To close these resources on app shutdown:

- **FastAPI:** Store the router and call `await router.close()` in your [lifespan](https://fastapi.tiangolo.com/advanced/events/) context manager (after `yield`), or use `healthcheck_shutdown(probes)` and call the returned callback.
- **Litestar:** Pass the same probes to `healthcheck_shutdown(probes)` and add the returned callback to the app's `on_shutdown` list.
- **FastStream:** Register the callback returned by `healthcheck_shutdown(probes)` with your app's shutdown hooks (e.g. `@app.on_shutdown`).

Import `healthcheck_shutdown` from `fast_healthchecks.integrations.fastapi`, `fast_healthchecks.integrations.faststream`, or `fast_healthchecks.integrations.litestar`.

## Probe options

| Parameter | Description |
|-----------|-------------|
| `name` | Probe identifier (e.g. `"liveness"`, `"readiness"`, `"startup"`). |
| `checks` | List of health checks to run. |
| `summary` | Custom description for the probe (used in responses). If omitted, a default is generated from `name`. |
| `allow_partial_failure` | If `True`, probe is healthy when at least one check passes. Default: `False`. |

To customize HTTP responses, pass these to `HealthcheckRouter` / `health()`:

| Parameter | Description |
|-----------|-------------|
| `success_handler` | Handler for healthy responses. Receives `ProbeAsgiResponse`, returns response body (or `None` for empty). |
| `failure_handler` | Handler for unhealthy responses. Same signature as `success_handler`. |
| `success_status` | HTTP status for healthy (default: `200`). |
| `failure_status` | HTTP status for unhealthy (default: `503`). |
| `debug` | Include check details in responses (default: `False`). |

## Running probes without ASGI

For CLI scripts, cron jobs, or tests, use `run_probe` instead of mounting ASGI routes:

```python
import asyncio
from fast_healthchecks.integrations.base import Probe, run_probe
from fast_healthchecks.checks.function import FunctionHealthCheck

async def main():
    probe = Probe(
        name="readiness",
        checks=[FunctionHealthCheck(func=lambda: True, name="Ping")],
    )
    report = await run_probe(probe)
    print(report.healthy, report.results)

asyncio.run(main())
```

Optional parameters: `timeout` (seconds), `on_check_start`, `on_check_end` (callbacks).

## DSN formats

Checks that support `from_dsn()` accept these URL schemes:

| Check | Scheme | Example |
|-------|--------|---------|
| Redis | `redis://` | `redis://localhost:6379/0`, `redis://user:pass@host:6379` |
| MongoDB | `mongodb://` | `mongodb://localhost:27017`, `mongodb://user:pass@host/db?authSource=admin` |
| PostgreSQL | `postgresql://` | `postgresql://user:pass@localhost:5432/dbname` |
| RabbitMQ | `amqp://` | `amqp://user:pass@localhost:5672/%2F` |
| Kafka | `kafka://` | `kafka://broker1:9092,broker2:9092`, `kafka://user:pass@host:9092` |
| OpenSearch | `http://` or `https://` | `https://admin:pass@localhost:9200` |
