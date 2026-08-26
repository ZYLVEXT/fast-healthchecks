"""Unit tests for the dependency pin validator script."""

import pytest

import scripts.validate_dependency_pins as pins

pytestmark = pytest.mark.unit

DIGEST = "sha256:" + "a" * 64
PINNED_DEFAULT = f"redis:8.2.1@{DIGEST}"
PINNED_OVERRIDE = f"redis:9.9.9@{DIGEST}"


def test_unset_env_uses_compose_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the variable exported, the compose default is validated."""
    monkeypatch.delenv("PIN_TEST_IMAGE", raising=False)
    reference = pins._image_reference("${PIN_TEST_IMAGE:-" + PINNED_DEFAULT + "}")
    assert reference == PINNED_DEFAULT


def test_env_override_wins_over_compose_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exported variable is what Compose runs, so its value is validated."""
    monkeypatch.setenv("PIN_TEST_IMAGE", PINNED_OVERRIDE)
    reference = pins._image_reference("${PIN_TEST_IMAGE:-" + PINNED_DEFAULT + "}")
    assert reference == PINNED_OVERRIDE


def test_unpinned_env_override_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A floating env override is rejected even when the default is pinned."""
    monkeypatch.setenv("PIN_TEST_IMAGE", "redis:latest")
    assert pins._is_pinned_image("${PIN_TEST_IMAGE:-" + PINNED_DEFAULT + "}") is False


def test_empty_env_override_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Compose treats an empty value as unset for :-, and so does the validator."""
    monkeypatch.setenv("PIN_TEST_IMAGE", "")
    assert pins._is_pinned_image("${PIN_TEST_IMAGE:-" + PINNED_DEFAULT + "}") is True


@pytest.mark.parametrize(
    ("tag", "pinned"),
    [
        ("1.2.3", True),
        ("1.2.3-alpine", True),
        ("1.2.3-bookworm", True),
        ("1.2.3-management", True),
        ("1.2.3-arch", True),
        ("1.2.3-rc1", False),
        ("1.2.3-rc", False),
        ("1.2.3-dev", False),
        ("1.2.3-dev2", False),
        ("1.2.3-edge", False),
        ("1.2.3-latest", False),
        ("1.2.3-alphabuild", False),
        ("1.2.3-beta2", False),
        ("1.2.3-nightly", False),
        ("1.2.3-preview", False),
        ("latest", False),
    ],
)
def test_tag_stability(tag: str, *, pinned: bool) -> None:
    """Unstable keywords are rejected; stable suffixes like alpine/arch pass."""
    assert pins._is_pinned_image(f"repo:{tag}@{DIGEST}") is pinned
