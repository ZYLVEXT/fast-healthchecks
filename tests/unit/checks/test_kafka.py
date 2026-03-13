"""Unit tests for KafkaHealthCheck."""

import asyncio
import ssl
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from aiokafka.admin import AIOKafkaAdminClient

from fast_healthchecks.checks.kafka import KafkaHealthCheck
from tests.utils import assert_check_init

pytestmark = pytest.mark.unit

test_ssl_context = ssl.create_default_context()
EXPECTED_CLIENT_CREATIONS_AFTER_RECREATE = 2
EXPECTED_LIST_TOPICS_AWAITS_AFTER_TWO_CALLS = 2


@pytest.mark.parametrize(
    ("params", "expected", "exception"),
    [
        (
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
    """KafkaHealthCheck.__init__ and to_dict match expected or raise."""
    assert_check_init(lambda: KafkaHealthCheck(**params), expected, exception)


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
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user",
                "sasl_plain_password": None,
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        (
            "KAFKA://localhost:9093",
            {"name": "Kafka"},
            {
                "bootstrap_servers": "localhost:9093",
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
            "kafka://",
            {},
            "Kafka DSN must include bootstrap servers",
            ValueError,
        ),
        (
            "http://localhost:9092",
            {},
            r"DSN scheme must be one of kafka, kafkas",
            ValueError,
        ),
        (
            "kafkas://localhost:9093",
            {},
            {
                "bootstrap_servers": "localhost:9093",
                "ssl_context": None,
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
            "kafkas://user:pass@broker:9094",
            {},
            {
                "bootstrap_servers": "broker:9094",
                "ssl_context": None,
                "security_protocol": "SASL_SSL",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user",
                "sasl_plain_password": "pass",
                "timeout": 5.0,
                "name": "Kafka",
            },
            None,
        ),
        ("", {}, "DSN cannot be empty", ValueError),
    ],
)
def test_from_dsn(
    dsn: str,
    kwargs: dict[str, Any],
    expected: dict[str, Any] | str,
    exception: type[BaseException] | None,
) -> None:
    """Test from_dsn with various DSN options."""
    assert_check_init(lambda: KafkaHealthCheck.from_dsn(dsn, **kwargs), expected, exception)


@pytest.mark.asyncio
async def test_AIOKafkaAdminClient_args_kwargs() -> None:
    """Constructor args/kwargs are passed through to AIOKafkaAdminClient."""
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
    """Same client instance is reused across __call__ invocations."""
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
    """Check returns healthy when list_topics succeeds."""
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch.object(AIOKafkaAdminClient, "start", return_value=None) as mock_start,
        patch.object(AIOKafkaAdminClient, "list_topics", return_value=None) as mock_list_topics,
    ):
        result = await health_check()
        assert result.healthy is True
        assert result.name == "Kafka"
        assert result.error is None
        mock_start.assert_called_once_with()
        mock_start.assert_awaited_once_with()
        mock_list_topics.assert_called_once_with()
        mock_list_topics.assert_awaited_once_with()


@pytest.mark.asyncio
async def test__call_does_not_restart_started_client() -> None:
    """Second call reuses started client without calling start() again."""
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch.object(AIOKafkaAdminClient, "start", new_callable=AsyncMock) as mock_start,
        patch.object(AIOKafkaAdminClient, "list_topics", new_callable=AsyncMock) as mock_list_topics,
    ):
        await health_check()
        await health_check()
        assert mock_start.await_count == 1
        assert mock_list_topics.await_count == EXPECTED_LIST_TOPICS_AWAITS_AFTER_TWO_CALLS


@pytest.mark.asyncio
async def test__call_failure() -> None:
    """Check returns unhealthy when admin client fails."""
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch.object(AIOKafkaAdminClient, "start", side_effect=Exception("Connection error")) as mock_start,
    ):
        result = await health_check()
        assert result.healthy is False
        assert result.name == "Kafka"
        assert result.error is not None
        assert "Connection error" in result.error.message
        mock_start.assert_called_once_with()
        mock_start.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_aclose_clears_client() -> None:
    """aclose() closes and clears cached client."""
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
    """aclose() when no client is safe and idempotent."""
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    await health_check.aclose()
    assert health_check._client is None


@pytest.mark.asyncio
async def test_loop_invalidation_recreates_client() -> None:
    """Client from different event loop is recreated on next __call__."""
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    real_loop = asyncio.get_running_loop()
    other_loop = object()
    with (
        patch("fast_healthchecks.checks.kafka.AIOKafkaAdminClient", spec=AIOKafkaAdminClient) as factory,
        patch(
            "fast_healthchecks.checks._base.asyncio.get_running_loop",
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
    """_ensure_client works when get_running_loop raises."""
    health_check = KafkaHealthCheck(bootstrap_servers="localhost:9092")
    with (
        patch("fast_healthchecks.checks._base.asyncio.get_running_loop", side_effect=RuntimeError),
        patch("fast_healthchecks.checks.kafka.AIOKafkaAdminClient", spec=AIOKafkaAdminClient) as factory,
        patch.object(AIOKafkaAdminClient, "start", return_value=None),
        patch.object(AIOKafkaAdminClient, "list_topics", return_value=None),
    ):
        result = await health_check()
        assert result.healthy is True
        factory.assert_called_once()
        assert health_check._client_loop is None
