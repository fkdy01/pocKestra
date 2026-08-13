from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from kestra_api import KestraClient  # noqa: E402


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--kestra-live",
        action="store_true",
        default=False,
        help="Exécuter les tests contre l'instance Kestra indiquée par KESTRA_URL.",
    )


@pytest.fixture(scope="session")
def live_kestra_enabled(pytestconfig: pytest.Config) -> bool:
    env_enabled = os.getenv("KESTRA_RUN_TESTS", "").strip().lower() in {"1", "true", "yes", "oui"}
    return bool(pytestconfig.getoption("--kestra-live") or env_enabled)


@pytest.fixture(scope="session")
def kestra_client(live_kestra_enabled: bool) -> KestraClient:
    if not live_kestra_enabled:
        pytest.skip("Tests Kestra live désactivés. Utiliser --kestra-live ou KESTRA_RUN_TESTS=true.")

    client = KestraClient()
    if not client.health():
        pytest.skip("Instance Kestra non joignable. Vérifier KESTRA_URL.")
    return client


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


def import_flow(kestra_client: KestraClient, repo_root: Path, relative_path: str) -> None:
    kestra_client.import_flow_file(repo_root / relative_path)


def run_and_wait(
    kestra_client: KestraClient,
    namespace: str,
    flow_id: str,
    inputs: dict[str, str] | None = None,
    timeout_seconds: int = 120,
) -> dict:
    execution_id = kestra_client.create_execution(namespace, flow_id, inputs=inputs)
    return kestra_client.wait_execution(execution_id, timeout_seconds=timeout_seconds)


def assert_state(execution: dict, expected: str) -> None:
    current = execution.get("state", {}).get("current")
    assert current == expected, f"Statut attendu {expected}, obtenu {current}. Execution: {execution.get('id')}"
