# Configuration objects

Connection-based checks (Redis, Kafka, Mongo, RabbitMQ, OpenSearch, URL, PostgreSQL, Function) accept either keyword arguments or an optional `config` argument. When `config` is `None`, the check builds its config from `**kwargs`. Config types (e.g. `RedisConfig`, `UrlConfig`) are defined in `fast_healthchecks.checks.configs` and are used for typing and for `to_dict()` serialization. This keeps constructor signatures short and avoids long parameter lists. For the full list and field reference, see [API Reference — fast_healthchecks.checks.configs](api.md).
