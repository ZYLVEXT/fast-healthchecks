"""DSN type aliases for type hints."""

from __future__ import annotations

from typing import TypeAlias

AmqpDsn: TypeAlias = str
KafkaDsn: TypeAlias = str
MongoDsn: TypeAlias = str
PostgresDsn: TypeAlias = str
RedisDsn: TypeAlias = str

SupportedDsns: TypeAlias = AmqpDsn | KafkaDsn | MongoDsn | PostgresDsn | RedisDsn

__all__ = (
    "AmqpDsn",
    "KafkaDsn",
    "MongoDsn",
    "PostgresDsn",
    "RedisDsn",
    "SupportedDsns",
)
