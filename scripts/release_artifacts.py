"""Build and verify reproducible release artifacts for fast-healthchecks."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess  # noqa: S404
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_DISTRIBUTION = "fast-healthchecks"
_MODULE = "fast_healthchecks"
_PROJECT_FILE = _REPOSITORY_ROOT / "pyproject.toml"
_VERSION_FILE = _REPOSITORY_ROOT / _MODULE / "__init__.py"
_STABLE_VERSION = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\Z")
_MODULE_VERSION = re.compile(r"""^__version__\s*=\s*["'](?P<version>[^"']+)["']\s*$""", re.MULTILINE)
_MIN_SDIST_MEMBER_PARTS = 2
_SDIST_TOP_LEVEL = frozenset(
    {
        ".gitignore",
        "CHANGELOG.md",
        "LICENSE",
        "PKG-INFO",
        "README.md",
        "docs",
        _MODULE,
        "pyproject.toml",
        "scripts",
        "tests",
        "zensical.toml",
    },
)


def version() -> str:
    """Return the validated release version.

    Returns:
        The canonical stable SemVer version.

    Raises:
        RuntimeError: If project and module metadata disagree.
    """
    with _PROJECT_FILE.open("rb") as project_file:
        project = tomllib.load(project_file)["project"]
    project_name = str(project["name"])
    project_version = str(project["version"])
    if project_name != _DISTRIBUTION:
        msg = f"expected project {_DISTRIBUTION!r}, found {project_name!r}"
        raise RuntimeError(msg)
    if _STABLE_VERSION.fullmatch(project_version) is None:
        msg = f"release version {project_version!r} is not canonical stable SemVer"
        raise RuntimeError(msg)
    source_versions = _MODULE_VERSION.findall(_VERSION_FILE.read_text(encoding="utf-8"))
    if source_versions != [project_version]:
        msg = f"{_VERSION_FILE.relative_to(_REPOSITORY_ROOT)} must publish __version__ = {project_version!r}"
        raise RuntimeError(msg)
    return project_version


def require_version_advance(current: str, latest: str, *, resume: bool) -> None:
    """Require a monotonic release or an exact resume.

    Raises:
        RuntimeError: If the version does not satisfy the release operation.
    """
    current_parts = tuple(int(part) for part in current.split("."))
    latest_parts = tuple(int(part) for part in latest.split("."))
    if _STABLE_VERSION.fullmatch(latest) is None:
        msg = f"latest tag {latest!r} is not canonical stable SemVer"
        raise RuntimeError(msg)
    if (resume and current_parts != latest_parts) or (not resume and current_parts <= latest_parts):
        msg = f"release version {current} must advance latest stable tag {latest}"
        raise RuntimeError(msg)


def _artifacts(dist_dir: Path) -> tuple[Path, Path]:
    wheels = tuple(dist_dir.glob("*.whl"))
    source_distributions = tuple(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(source_distributions) != 1:
        msg = f"expected one wheel and one sdist under {dist_dir}; found {len(wheels)} and {len(source_distributions)}"
        raise RuntimeError(msg)
    return wheels[0], source_distributions[0]


def _uv_executable() -> str:
    executable = shutil.which("uv")
    if executable is None:
        msg = "uv is required to build and smoke-test release artifacts"
        raise RuntimeError(msg)
    return executable


def _clear_artifacts(dist_dir: Path) -> None:
    dist_dir.mkdir(parents=True, exist_ok=True)
    normalized = _DISTRIBUTION.replace("-", "_")
    for pattern in (f"{normalized}-*.whl", f"{normalized}-*.tar.gz"):
        for artifact in dist_dir.glob(pattern):
            artifact.unlink()


def _require_wheel_inventory(members: tuple[str, ...], release_version: str) -> None:
    allowed = {_MODULE, f"{_MODULE}-{release_version}.dist-info"}
    for member in members:
        parts = PurePosixPath(member).parts
        if not parts or parts[0] not in allowed or any(part.startswith(".") for part in parts[1:]):
            msg = f"wheel contains an unexpected member: {member}"
            raise RuntimeError(msg)


def _require_sdist_inventory(members: tuple[str, ...], release_version: str) -> None:
    root = f"{_MODULE}-{release_version}"
    for member in members:
        parts = PurePosixPath(member).parts
        if (
            len(parts) < _MIN_SDIST_MEMBER_PARTS
            or parts[0] != root
            or parts[1] not in _SDIST_TOP_LEVEL
            or any(part.startswith(".") for part in parts[2:])
        ):
            msg = f"source distribution contains an unexpected member: {member}"
            raise RuntimeError(msg)


def verify(dist_dir: Path) -> None:
    """Verify versions, inventory, typing marker, and public artifact boundaries.

    Raises:
        RuntimeError: If an artifact contains an invalid or prohibited member.
    """
    release_version = version()
    wheel, source_distribution = _artifacts(dist_dir)
    with zipfile.ZipFile(wheel) as archive:
        wheel_members = tuple(archive.namelist())
    with tarfile.open(source_distribution, "r:gz") as archive:
        sdist_members = tuple(archive.getnames())
    _require_wheel_inventory(wheel_members, release_version)
    _require_sdist_inventory(sdist_members, release_version)
    if not any(member == f"{_MODULE}/py.typed" for member in wheel_members):
        msg = "wheel does not contain py.typed"
        raise RuntimeError(msg)
    if not any(member.endswith(f"/{_MODULE}/py.typed") for member in sdist_members):
        msg = "sdist does not contain py.typed"
        raise RuntimeError(msg)


def build(dist_dir: Path) -> None:
    """Build one wheel and one sdist from locked public sources."""
    version()
    _clear_artifacts(dist_dir)
    subprocess.run(  # noqa: S603
        (_uv_executable(), "build", "--no-sources", "--out-dir", str(dist_dir)),
        cwd=_REPOSITORY_ROOT,
        check=True,
    )
    verify(dist_dir)


def compare(first: Path, second: Path) -> None:
    """Require byte-identical wheel and sdist builds.

    Raises:
        RuntimeError: If names or SHA-256 digests differ.
    """
    for first_path, second_path in zip(_artifacts(first), _artifacts(second), strict=True):
        first_digest = hashlib.sha256(first_path.read_bytes()).digest()
        second_digest = hashlib.sha256(second_path.read_bytes()).digest()
        if first_path.name != second_path.name or first_digest != second_digest:
            msg = f"release artifact is not reproducible: {first_path.name}"
            raise RuntimeError(msg)


def smoke(dist_dir: Path) -> None:
    """Install the wheel without extras and verify its root import."""
    release_version = version()
    wheel, _source_distribution = _artifacts(dist_dir)
    with tempfile.TemporaryDirectory(prefix="fast-healthchecks-release-smoke-") as temporary_directory:
        environment = Path(temporary_directory) / "venv"
        subprocess.run(  # noqa: S603
            (_uv_executable(), "venv", str(environment), "--python", sys.executable),
            cwd=_REPOSITORY_ROOT,
            check=True,
        )
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(  # noqa: S603
            (_uv_executable(), "pip", "install", "--python", str(python), str(wheel)),
            cwd=_REPOSITORY_ROOT,
            check=True,
        )
        check = (
            f"import importlib.resources, {_MODULE}; "
            f"assert {_MODULE}.__version__ == {release_version!r}; "
            f"assert importlib.resources.files('{_MODULE}').joinpath('py.typed').is_file()"
        )
        subprocess.run(  # noqa: S603
            (str(python), "-I", "-c", check),
            cwd=temporary_directory,
            check=True,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "verify", "smoke"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--dist-dir", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--first", type=Path, required=True)
    compare_parser.add_argument("--second", type=Path, required=True)
    version_parser = subparsers.add_parser("version")
    version_parser.add_argument("--latest-tag")
    version_parser.add_argument("--resume", action="store_true")
    return parser


def main() -> int:
    """Run the selected release-artifact operation.

    Returns:
        Process exit status.
    """
    arguments = _parser().parse_args()
    if arguments.command == "version":
        current = version()
        if arguments.latest_tag is not None:
            require_version_advance(current, arguments.latest_tag, resume=arguments.resume)
        sys.stdout.write(f"{current}\n")
    elif arguments.command == "build":
        build(arguments.dist_dir)
    elif arguments.command == "verify":
        verify(arguments.dist_dir)
    elif arguments.command == "smoke":
        smoke(arguments.dist_dir)
    else:
        compare(arguments.first, arguments.second)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
