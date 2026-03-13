# DSN formats

Checks that support `from_dsn()` accept these URL schemes:

| Check | Scheme | Example |
|-------|--------|---------|
| Redis | `redis://` | `redis://localhost:6379/0`, `redis://user:pass@host:6379` |
| MongoDB | `mongodb://` | `mongodb://localhost:27017`, `mongodb://user:pass@host/db?authSource=admin` |
| PostgreSQL | `postgresql://` | `postgresql://user:pass@localhost:5432/dbname` |
| RabbitMQ | `amqp://` | `amqp://user:pass@localhost:5672/%2F` |
| Kafka | `kafka://` | `kafka://broker1:9092,broker2:9092`, `kafka://user:pass@host:9092` |
| OpenSearch | `http://` or `https://` | `https://admin:pass@localhost:9200` |

## PostgreSQL TLS certificate rotation

PostgreSQL checks (`verify-full`, `verify-ca`) cache the SSL context. After rotating certificates, restart the process or call `fast_healthchecks.checks.postgresql.base.create_ssl_context.cache_clear()` to avoid using stale contexts.
