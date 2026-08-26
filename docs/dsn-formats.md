# DSN formats

Checks that support `from_dsn()` accept these URL schemes:

| Check | Scheme | Example |
|-------|--------|---------|
| Redis | `redis://` | `redis://localhost:6379/0`, `redis://user:pass@host:6379` |
| MongoDB | `mongodb://` or `mongodb+srv://` | `mongodb://localhost:27017`, `mongodb://user:pass@host/db?authSource=admin&tls=true` |
| PostgreSQL | `postgresql://` | `postgresql://user:pass@localhost:5432/dbname` |
| RabbitMQ | `amqp://` | `amqp://user:pass@localhost:5672/%2F` |
| Kafka | `kafka://` | `kafka://broker1:9092,broker2:9092`, `kafka://user:pass@host:9092` |
| OpenSearch | `http://` or `https://` | `https://admin:pass@localhost:9200` |

## OpenSearch TLS

An `https://` DSN enables TLS with certificate verification: `verify_certs=True` is the parsed default, matching the opensearch-py driver. To connect to an HTTPS endpoint without verification (e.g. a self-signed development cluster), pass `verify_certs=False` explicitly to `from_dsn()` or set a CA bundle with `ca_certs`. Plain `http://` DSNs do not use TLS and ignore `verify_certs`.

## MongoDB TLS

The `tls` (or legacy `ssl`) query option controls TLS explicitly; without it, `mongodb+srv://` enables TLS — matching PyMongo — and plain `mongodb://` leaves the driver default. `tlsCAFile` (or legacy `ssl_ca_certs`) sets the CA bundle. Parsed values are forwarded to the Motor client as `tls`/`tlsCAFile`. Note that the check connects to the parsed host/port directly, so `mongodb+srv` SRV record resolution is not performed; only its TLS default applies.

Certificate paths in DSN query options (`tlsCAFile`, PostgreSQL `sslrootcert`/`sslcert`/`sslkey`, Redis `ssl_ca_certs`) are read from the local filesystem. DSNs are trusted configuration: do not build them from untrusted input.

## PostgreSQL TLS

The asyncpg check forwards `disable`, `allow`, `prefer`, `require`, `verify-ca`, and `verify-full` to asyncpg when no certificate files are configured, preserving the driver's native SSL-mode behavior. `verify-full` validates the server certificate and hostname; it does not require a client certificate.

Raw asyncpg/libpq URLs select the mode with `sslmode=require`. SQLAlchemy asyncpg URLs commonly
use `postgresql+asyncpg://...?...&ssl=require`; the asyncpg check accepts that `ssl` spelling as a
compatibility alias. When both `ssl` and `sslmode` are present they must be identical, otherwise DSN
validation fails closed.

`sslrootcert` configures the CA used to verify the server. `sslcert` and `sslkey` are optional client-authentication material and must form a usable certificate chain. A key without a certificate is rejected.

### Certificate rotation

PostgreSQL checks (`verify-full`, `verify-ca`) cache the SSL context. After rotating certificates, restart the process or call `fast_healthchecks.checks.postgresql.base.create_ssl_context.cache_clear()` to avoid using stale contexts.
