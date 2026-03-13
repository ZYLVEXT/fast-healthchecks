"""DSN NewTypes for type hints only.

These types annotate DSN strings (e.g. AmqpDsn, RedisDsn) but are not used at
runtime by check classes. Each HealthCheckDSN subclass implements its own
parse_dsn() and validate_dsn(); dsn.py provides no parsing or validation logic.
Use these types to annotate configuration or function parameters.
"""

from __future__ import annotations

from typing import NewType, TypeAlias

AmqpDsn = NewType("AmqpDsn", str)
KafkaDsn = NewType("KafkaDsn", str)
MongoDsn = NewType("MongoDsn", str)
OpenSearchDsn = NewType("OpenSearchDsn", str)
PostgresDsn = NewType("PostgresDsn", str)
RedisDsn = NewType("RedisDsn", str)

SupportedDsns: TypeAlias = AmqpDsn | KafkaDsn | MongoDsn | OpenSearchDsn | PostgresDsn | RedisDsn

__all__ = (
    "AmqpDsn",
    "KafkaDsn",
    "MongoDsn",
    "OpenSearchDsn",
    "PostgresDsn",
    "RedisDsn",
    "SupportedDsns",
)
