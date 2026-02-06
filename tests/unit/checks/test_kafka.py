import asyncio
import ssl
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from aiokafka.admin import AIOKafkaAdminClient

from fast_healthchecks.checks.kafka import KafkaHealthCheck

pytestmark = pytest.mark.unit

test_ssl_context = ssl.create_default_context()
EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE = 2


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
            {},
            "missing 1 required keyword-only argument: 'bootstrap_servers'",
            TypeError,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": None,
                "security_protocol": "PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "BROKEN",
            },
            "Invalid security protocol: BROKEN",
            ValueError,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SSL",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SSL",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "PLAINTEXT",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_PLAINTEXT",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "BROKEN",
            },
            "Invalid SASL mechanism: BROKEN",
            ValueError,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "PLAIN",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "GSSAPI",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "GSSAPI",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "SCRAM-SHA-256",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "SCRAM-SHA-256",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "SCRAM-SHA-512",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "SCRAM-SHA-512",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
                "sasl_plain_password": "password",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
                "sasl_plain_password": "password",
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
                "sasl_plain_password": "password",
                "timeout": 1.5,
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
                "sasl_plain_password": "password",
                "timeout": 1.5,
                "name": "Kafka",
            },
            None,
        ),
        (
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
                "sasl_plain_password": "password",
                "timeout": 1.5,
                "name": "Test",
            },
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": test_ssl_context,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "OAUTHBEARER",
                "sasl_plain_username": "user",
                "sasl_plain_password": "password",
                "timeout": 1.5,
                "name": "Test",
            },
            None,
        ),
    ],
)
def test__init(params: dict[str, Any], expected: dict[str, Any] | str, exception: type[BaseException] | None) -> None:
    if exception is not None and isinstance(expected, str):
        with pytest.raises(exception, match=expected):
            KafkaHealthCheck(**params)
    else:
        obj = KafkaHealthCheck(**params)
        assert obj.to_dict() == expected


@pytest.mark.parametrize(
    ("dsn", "kwargs", "expected", "exception"),
    [
        (
            "kafka://localhost:9092",
            {},
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": None,
                "security_protocol": "PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": None,
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            "kafka://user:password@localhost:9092",
            {"security_protocol": "SASL_PLAINTEXT", "timeout": 1.5, "name": "Test"},
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": None,
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user",
                "sasl_plain_password": "password",
                "timeout": 1.5,
                "name": "Test",
            },
            None,
        ),
        (
            "kafka://user@localhost:9092",
            {},
            {
                "bootstrap_servers": "localhost:9092",
                "ssl_context": None,
                "security_protocol": "PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user",
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            "kafka://",
            {},
            "Kafka DSN must include bootstrap servers",
            ValueError,
        ),
        (
            "http://localhost:9092",
            {},
            "Kafka DSN must start with kafka://",
            ValueError,
        ),
    ],
)
def test_from_dsn(
    dsn: str,
    kwargs: dict[str, Any],
    expected: dict[str, Any] | str,
    exception: type[BaseException] | None,
) -> None:
    if exception is not None and isinstance(expected, str):
        with pytest.raises(exception, match=expected):
            KafkaHealthCheck.from_dsn(dsn, **kwargs)
    else:
        obj = KafkaHealthCheck.from_dsn(dsn, **kwargs)
        assert obj.to_dict() == expected


@pytest.mark.asyncio
async def test_AIOKafkaAdminClient_args_kwargs() -> None:
    health_check = KafkaHealthCheck(
        bootstrap_servers="localhost:9092",
        ssl_context=test_ssl_context,
        security_protocol="SASL_SSL",
        sasl_mechanism="OAUTHBEARER",
        sasl_plain_username="user",
        sasl_plain_password="password",
        timeout=1.5,
    )
    with patch("fast_healthchecks.checks.kafka.AIOKafkaAdminClient", spec=AIOKafkaAdminClient) as mock:
        await health_check()
        mock.assert_called_once_with(
            bootstrap_servers="localhost:9092",
            client_id="fast_healthchecks",
            request_timeout_ms=1.5 * 1000,
            ssl_context=test_ssl_context,
            security_protocol="SASL_SSL",
            sasl_mechanism="OAUTHBEARER",
            sasl_plain_username="user",
            sasl_plain_password="password",
        )


@pytest.mark.asyncio
async def test_AIOKafkaAdminClient_reused_between_calls() -> None:
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch("fast_healthchecks.checks.kafka.AIOKafkaAdminClient", spec=AIOKafkaAdminClient) as factory,
        patch.object(AIOKafkaAdminClient, "start", return_value=None),
        patch.object(AIOKafkaAdminClient, "list_topics", return_value=None),
    ):
        await health_check()
        await health_check()
        factory.assert_called_once_with(
            bootstrap_servers="localhost:9092",
            client_id="fast_healthchecks",
            request_timeout_ms=5000,
            ssl_context=None,
            security_protocol="PLAINTEXT",
            sasl_mechanism="PLAIN",
            sasl_plain_username=None,
            sasl_plain_password=None,
        )


@pytest.mark.asyncio
async def test__call_success() -> None:
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch.object(AIOKafkaAdminClient, "start", return_value=None) as mock_start,
        patch.object(AIOKafkaAdminClient, "list_topics", return_value=None) as mock_list_topics,
    ):
        result = await health_check()
        assert result.healthy is True
        assert result.name == "Kafka"
        assert result.error_details is None
        mock_start.assert_called_once_with()
        mock_start.assert_awaited_once_with()
        mock_list_topics.assert_called_once_with()
        mock_list_topics.assert_awaited_once_with()


@pytest.mark.asyncio
async def test__call_failure() -> None:
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch.object(AIOKafkaAdminClient, "start", side_effect=Exception("Connection error")) as mock_start,
    ):
        result = await health_check()
        assert result.healthy is False
        assert result.name == "Kafka"
        assert "Connection error" in str(result.error_details)
        mock_start.assert_called_once_with()
        mock_start.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch("fast_healthchecks.checks.kafka.AIOKafkaAdminClient", spec=AIOKafkaAdminClient) as factory,
        patch.object(AIOKafkaAdminClient, "start", return_value=None),
        patch.object(AIOKafkaAdminClient, "list_topics", return_value=None),
        patch.object(AIOKafkaAdminClient, "close", new_callable=AsyncMock),
    ):
        await health_check()
        assert health_check._client is not None
        await health_check.aclose()
        assert health_check._client is None
        assert health_check._client_loop is None
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_aclose_idempotent_when_no_client() -> None:
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    real_loop = asyncio.get_running_loop()
    other_loop = object()
    with (
        patch("fast_healthchecks.checks.kafka.AIOKafkaAdminClient", spec=AIOKafkaAdminClient) as factory,
        patch(
            "fast_healthchecks.checks.kafka.asyncio.get_running_loop",
            side_effect=[real_loop, real_loop, other_loop, other_loop],
        ),
        patch.object(AIOKafkaAdminClient, "start", return_value=None),
        patch.object(AIOKafkaAdminClient, "list_topics", return_value=None),
        patch.object(AIOKafkaAdminClient, "close", new_callable=AsyncMock),
    ):
        await health_check()
        await health_check()
        assert factory.call_count == EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE


@pytest.mark.asyncio
async def test_get_client_with_no_running_loop() -> None:
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch("fast_healthchecks.checks.kafka.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.kafka.AIOKafkaAdminClient", spec=AIOKafkaAdminClient) as factory,
        patch.object(AIOKafkaAdminClient, "start", return_value=None),
        patch.object(AIOKafkaAdminClient, "list_topics", return_value=None),
    ):
        result = await health_check()
        assert result.healthy is True
        factory.assert_called_once()
        assert health_check._client_loop is None
