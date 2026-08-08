"""Audit the locked project dependency graph without auditing tooling packages."""

from __future__ import annotations

import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed argv execution is required for the audit tools
import tempfile
from pathlib import Path


def main() -> None:
    """Export every locked dependency group and pass it to pip-audit.

    Raises:
        RuntimeError: If the uv executable is unavailable.
    """
    uv_executable = shutil.which("uv")
    if uv_executable is None:
        msg = "uv executable was not found"
        raise RuntimeError(msg)
    with tempfile.TemporaryDirectory(prefix="fast-healthchecks-audit-") as temp_dir:
        requirements = Path(temp_dir) / "requirements.txt"
        subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - argv and executable are controlled above
            [
                uv_executable,
                "export",
                "--quiet",
                "--all-extras",
                "--all-groups",
                "--no-emit-project",
                "--no-emit-package",
                "pip",
                "--output-file",
                str(requirements),
            ],
            check=True,
        )
        subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - argv and executable are controlled above
            [
                uv_executable,
                "run",
                "pip-audit",
                "--disable-pip",
                "--require-hashes",
                "-r",
                str(requirements),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
