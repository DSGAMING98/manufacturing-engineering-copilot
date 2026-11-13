"""One-command CPU verification used by CI and release checks."""
from __future__ import annotations

import subprocess
import sys


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def main() -> None:
    run("-m", "unittest", "discover", "-s", "tests", "-q")
    run("-m", "phase5.benchmark")
    run("-m", "phase6.release_checks", "--git-only")
    print("Observed-data prototype verification: PASS")


if __name__ == "__main__":
    main()
