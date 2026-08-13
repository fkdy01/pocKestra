#!/usr/bin/env python3
"""Lance le socle de tests automatisés Kestra."""

from __future__ import annotations

import subprocess
import sys


COMMANDS = [
    [sys.executable, "scripts/validate_yaml.py"],
    [sys.executable, "-m", "pytest", "tests/kestra", "-v"],
]


def main() -> int:
    for command in COMMANDS:
        print("+", " ".join(command))
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
