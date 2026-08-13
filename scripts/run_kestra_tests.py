#!/usr/bin/env python3
"""Lance le socle de tests automatisés Kestra."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


VALIDATE_COMMAND = [sys.executable, "scripts/validate_yaml.py"]
PYTEST_COMMAND = [sys.executable, "-m", "pytest", "tests/kestra", "-v"]


def env_live_enabled() -> bool:
    return os.getenv("KESTRA_RUN_TESTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "oui",
    }


def run(command: list[str]) -> int:
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valide les YAML puis lance les smoke tests Kestra live."
    )
    parser.add_argument(
        "--kestra-live",
        action="store_true",
        help="Activer les tests contre l'instance configurée par KESTRA_URL.",
    )
    args = parser.parse_args()

    validation_status = run(VALIDATE_COMMAND)
    if validation_status != 0:
        return validation_status

    live_enabled = args.kestra_live or env_live_enabled()
    if not live_enabled:
        print(
            "[SKIP] Smoke tests Kestra live non exécutés. "
            "Utiliser --kestra-live ou KESTRA_RUN_TESTS=true.",
            flush=True,
        )
        return 0

    command = [*PYTEST_COMMAND, "--kestra-live"]
    return run(command)


if __name__ == "__main__":
    raise SystemExit(main())
