"""Install the coverage subprocess startup hook into the active environment."""

from __future__ import annotations

import sysconfig
from pathlib import Path

HOOK = "import importlib.util; importlib.util.find_spec('coverage') and __import__('coverage').process_startup()\n"


def main() -> None:
    """Write an optional coverage startup hook to the active site-packages."""
    hook_path = Path(sysconfig.get_paths()["purelib"]) / "coverage_subprocess.pth"
    hook_path.write_text(HOOK)
    print(f"Installed coverage subprocess hook at {hook_path}")


if __name__ == "__main__":
    main()
