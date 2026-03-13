"""Shared test helpers: assert_check_init, create_temp_files, SSL paths, redact/validate_url_ssrf."""

import atexit
import os
import shutil
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

__all__ = (
    "SSLCERT_NAME",
    "SSLKEY_NAME",
    "SSLROOTCERT_NAME",
    "assert_check_init",
    "create_temp_files",
)


def assert_check_init(
    create_check: Callable[[], Any],
    expected: dict[str, Any] | str,
    exception: type[BaseException] | None,
) -> None:
    """Run create_check and assert to_dict equals expected or raises exception."""
    if exception is not None:
        assert isinstance(expected, str)
        with pytest.raises(exception, match=expected):
            create_check()
    else:
        assert create_check().to_dict() == expected


SSLCERT_NAME = "cert.crt"
SSLKEY_NAME = "key.key"
SSLROOTCERT_NAME = "ca.crt"
TEST_CERT_LOCATION = Path(__file__).parent / "certs"

SSL_FILES_MAP = {
    SSLCERT_NAME: TEST_CERT_LOCATION / SSLCERT_NAME,
    SSLKEY_NAME: TEST_CERT_LOCATION / SSLKEY_NAME,
    SSLROOTCERT_NAME: TEST_CERT_LOCATION / SSLROOTCERT_NAME,
}


temp_dir = Path(tempfile.gettempdir()) / f"fast_healthchecks-{os.getpid()}"
temp_dir.mkdir(parents=True, exist_ok=True)
atexit.register(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

TEST_SSLCERT = quote(str(temp_dir / SSLCERT_NAME))
TEST_SSLKEY = quote(str(temp_dir / SSLKEY_NAME))
TEST_SSLROOTCERT = quote(str(temp_dir / SSLROOTCERT_NAME))


def _try_rmdir(path: Path) -> bool:
    """Remove directory; return False on OSError.

    Returns:
        True if removed, False on OSError.
    """
    try:
        path.rmdir()
    except OSError:
        return False
    else:
        return True


def _remove_empty_parents(p: Path, boundary: Path) -> None:
    """Remove empty parent directories up to boundary."""
    parent = p.parent
    while parent != boundary and boundary in parent.parents and parent.exists():
        if not _try_rmdir(parent):
            break
        parent = parent.parent


@contextmanager
def create_temp_files(temp_file_paths: list[str]) -> Generator[None, None, None]:
    """Create temp files from paths; yield; then unlink and clean empty parents."""
    paths = [Path(temp_file_path) for temp_file_path in temp_file_paths]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.name in SSL_FILES_MAP:
            shutil.copyfile(SSL_FILES_MAP[path.name], path)
        else:
            with path.open("w") as f:
                f.write("Temporary content.")
                f.flush()

    yield

    for path in paths:
        path.unlink(missing_ok=True)

    for path in paths:
        _remove_empty_parents(path, temp_dir)
