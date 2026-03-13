"""Shared test helpers for integration unit tests."""

from unittest.mock import AsyncMock

from fast_healthchecks.models import HealthCheckResult


class CheckWithAclose:
    """Check with aclose for lifecycle tests. Implements Check protocol."""

    def __init__(
        self,
        *,
        name: str = "A",
        aclose_side_effect: BaseException | None = None,
    ) -> None:
        """Create a check with mock aclose."""
        self._name = name
        self._aclose_mock = AsyncMock(side_effect=aclose_side_effect)

    async def __call__(self) -> HealthCheckResult:
        """Return a healthy result."""
        return HealthCheckResult(name=self._name, healthy=True)

    async def aclose(self) -> None:
        """Call the mock aclose."""
        await self._aclose_mock()
