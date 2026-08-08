"""Require immutable GitHub Actions and exact Docker image pins."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION = re.compile(r"(?P<action>[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)@[0-9a-f]{40}\Z")
PINNED_IMAGE = re.compile(r"(?P<repository>[^@\s]+):(?P<tag>[^@\s]+)@sha256:[0-9a-f]{64}\Z")
COMPOSE_DEFAULT = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*:-(?P<image>[^}]+)\}\Z")
EXACT_TAG = re.compile(r"v?\d+\.\d+\.\d+(?:-[A-Za-z0-9][A-Za-z0-9._-]*)?\Z")
EXACT_POSTGRES_TAG = re.compile(r"\d+\.\d+-alpine\Z")
UNSTABLE_TAG = re.compile(
    r"(?:^|[-.])(?:latest|alpha\d*|beta\d*|rc\d*|nightly|edge|dev\d*|preview\d*)(?:[-.]|$)",
    re.IGNORECASE,
)


def _mapping_values(path: Path, key: str) -> list[tuple[int, str]]:
    """Return scalar values for every matching YAML mapping key."""
    documents = list(yaml.compose_all(path.read_text(encoding="utf-8"), Loader=yaml.SafeLoader))
    values: list[tuple[int, str]] = []
    visited: set[int] = set()

    def visit(node: Node | None) -> None:
        if node is None or id(node) in visited:
            return
        visited.add(id(node))
        if isinstance(node, MappingNode):
            for key_node, value_node in node.value:
                if isinstance(key_node, ScalarNode) and key_node.value == key:
                    value = value_node.value if isinstance(value_node, ScalarNode) else "<non-scalar>"
                    values.append((value_node.start_mark.line + 1, value))
                visit(value_node)
        elif isinstance(node, SequenceNode):
            for value_node in node.value:
                visit(value_node)

    for document in documents:
        visit(document)
    return values


def _image_reference(image: str) -> str:
    """Resolve a Compose environment-variable default to its image reference.

    Returns:
        The direct or environment-default image reference.
    """
    compose_default = COMPOSE_DEFAULT.fullmatch(image)
    return compose_default.group("image") if compose_default is not None else image


def _is_pinned_image(image: str) -> bool:
    reference = _image_reference(image)
    pinned = PINNED_IMAGE.fullmatch(reference)
    if pinned is None:
        return False
    tag = pinned.group("tag")
    exact_postgres_tag = pinned.group("repository") == "postgres" and EXACT_POSTGRES_TAG.fullmatch(tag) is not None
    return (EXACT_TAG.fullmatch(tag) is not None or exact_postgres_tag) and UNSTABLE_TAG.search(tag) is None


def _record_pin(
    *,
    family: str,
    pin: str,
    reference: str,
    location: str,
    observed: dict[str, tuple[str, str, str]],
) -> str | None:
    previous = observed.setdefault(family, (pin, reference, location))
    if previous[0] != pin:
        return f"{location}: {reference} conflicts with {previous[2]}: {previous[1]}"
    return None


def _record_image_pin(
    image: str,
    location: str,
    observed: dict[str, tuple[str, str, str]],
    errors: list[str],
) -> None:
    reference = _image_reference(image)
    pinned = PINNED_IMAGE.fullmatch(reference)
    if pinned is not None:
        error = _record_pin(
            family=f"image:{pinned.group('repository')}",
            pin=reference,
            reference=image,
            location=location,
            observed=observed,
        )
        if error is not None:
            errors.append(error)


def _validate_action(
    action: str,
    location: str,
    observed: dict[str, tuple[str, str, str]],
    errors: list[str],
) -> None:
    if action.startswith("./"):
        return
    if action.startswith("docker://"):
        image = action.removeprefix("docker://")
        if _is_pinned_image(image):
            _record_image_pin(image, location, observed, errors)
        else:
            errors.append(f"{location}: {action}")
        return
    pinned = PINNED_ACTION.fullmatch(action)
    if pinned is None:
        errors.append(f"{location}: {action}")
        return
    parts = pinned.group("action").split("/", maxsplit=2)
    error = _record_pin(
        family=f"action:{'/'.join(parts[:2])}",
        pin=action.rpartition("@")[2],
        reference=action,
        location=location,
        observed=observed,
    )
    if error is not None:
        errors.append(error)


def _invalid_action_pins(repository_root: Path, observed: dict[str, tuple[str, str, str]]) -> list[str]:
    errors: list[str] = []
    github_root = repository_root / ".github"
    github_files = sorted((*github_root.rglob("*.yml"), *github_root.rglob("*.yaml")))
    if not github_files:
        errors.append("no .github/**/*.yml or .github/**/*.yaml files found")
    for github_file in github_files:
        for line_number, action in _mapping_values(github_file, "uses"):
            location = f"{github_file.relative_to(repository_root).as_posix()}:{line_number}"
            _validate_action(action, location, observed, errors)
        for line_number, image in _mapping_values(github_file, "image"):
            location = f"{github_file.relative_to(repository_root).as_posix()}:{line_number}"
            if not _is_pinned_image(image):
                errors.append(f"{location}: {image}")
            else:
                _record_image_pin(image, location, observed, errors)
        for line_number, image in _mapping_values(github_file, "container"):
            if image == "<non-scalar>":
                continue
            location = f"{github_file.relative_to(repository_root).as_posix()}:{line_number}"
            if not _is_pinned_image(image):
                errors.append(f"{location}: {image}")
            else:
                _record_image_pin(image, location, observed, errors)
    return errors


def _compose_files(repository_root: Path) -> list[Path]:
    """Return root and nested Docker Compose files without duplicates."""
    files = {
        *repository_root.glob("compose*.yml"),
        *repository_root.glob("compose*.yaml"),
        *repository_root.glob("docker-compose*.yml"),
        *repository_root.glob("docker-compose*.yaml"),
    }
    docker_root = repository_root / "docker"
    if docker_root.is_dir():
        files.update(docker_root.rglob("compose*.yml"))
        files.update(docker_root.rglob("compose*.yaml"))
    return sorted(files)


def _invalid_image_pins(repository_root: Path, observed: dict[str, tuple[str, str, str]]) -> list[str]:
    errors: list[str] = []
    for compose_file in _compose_files(repository_root):
        for line_number, image in _mapping_values(compose_file, "image"):
            location = f"{compose_file.relative_to(repository_root).as_posix()}:{line_number}"
            if not _is_pinned_image(image):
                errors.append(f"{location}: {image}")
            else:
                _record_image_pin(image, location, observed, errors)
    return errors


def invalid_dependency_pins(repository_root: Path) -> list[str]:
    """Return invalid GitHub Action and Docker image references."""
    observed: dict[str, tuple[str, str, str]] = {}
    return [*_invalid_action_pins(repository_root, observed), *_invalid_image_pins(repository_root, observed)]


def main() -> int:
    """Validate dependency references.

    Returns:
        Process exit status.
    """
    errors = invalid_dependency_pins(REPOSITORY_ROOT)
    if errors:
        sys.stderr.write(
            "GitHub Actions must use full 40-character SHAs; Docker images must use exact release tags and "
            "sha256 digests:\n"
        )
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    sys.stdout.write("GitHub Action and Docker image pins are valid.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
