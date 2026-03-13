# Installation

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
