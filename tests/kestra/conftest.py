from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
FLOW_ROOT = REPO_ROOT / "kestra" / "flows"
FLOW_CATALOG_PATH = REPO_ROOT / "tests" / "kestra" / "flow_test_catalog.yml"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from kestra_api import KestraClient  # noqa: E402

SENSITIVE_INPUT_FRAGMENTS = (
    "PASSWORD",
    "TOKEN",
    "SECRET",
    "CREDENTIAL",
    "AUTH",
    "PRIVATE_KEY",
)


def proof_inputs(inputs: dict[str, object] | None) -> dict[str, object]:
    """Conserve les inputs fictifs du POC et masque les champs sensibles."""
    def sanitize(value: object) -> object:
        if isinstance(value, dict):
            return proof_inputs(value)
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        return value

    sanitized: dict[str, object] = {}
    for key, value in (inputs or {}).items():
        if any(fragment in key.upper() for fragment in SENSITIVE_INPUT_FRAGMENTS):
            sanitized[key] = "<valeur-masquee>"
        else:
            sanitized[key] = sanitize(value)
    return sanitized


def load_flow_catalog() -> list[dict[str, Any]]:
    payload = yaml.safe_load(FLOW_CATALOG_PATH.read_text(encoding="utf-8"))
    flows = payload.get("flows") if isinstance(payload, dict) else None
    if not isinstance(flows, list):
        raise ValueError("Le catalogue doit contenir une liste `flows`.")
    return flows


def catalog_scenarios() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for flow in load_flow_catalog():
        if flow.get("automation") != "automated":
            continue
        for scenario in flow.get("scenarios", []):
            cases.append(
                {
                    "namespace": flow["namespace"],
                    "flow_id": flow["id"],
                    "scenario_id": scenario["id"],
                    "inputs": scenario.get("inputs", {}),
                    "expected_state": scenario["expected_state"],
                    "timeout_seconds": scenario.get("timeout_seconds", 120),
                }
            )
    return cases


def materialize_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    materialized = dict(inputs)
    for key, value in materialized.items():
        if value == "AUTO-UUID":
            materialized[key] = f"codex-exhaustif-{uuid4().hex}"
    return materialized


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


@pytest.fixture(scope="session")
def all_flows_imported(kestra_client: KestraClient) -> None:
    """Importe tous les flows, sous-flows communs en premier."""
    paths = sorted(
        FLOW_ROOT.rglob("*.yml"),
        key=lambda path: ("/common/" not in path.as_posix(), path.as_posix()),
    )
    for path in paths:
        kestra_client.import_flow_file(path)


def import_flow(kestra_client: KestraClient, repo_root: Path, relative_path: str) -> None:
    kestra_client.import_flow_file(repo_root / relative_path)


def run_and_wait(
    kestra_client: KestraClient,
    namespace: str,
    flow_id: str,
    inputs: dict[str, object] | None = None,
    timeout_seconds: int = 120,
    scenario_id: str = "smoke",
) -> dict:
    execution_id = kestra_client.create_execution(namespace, flow_id, inputs=inputs)
    print(
        "[KESTRA_PROOF] "
        + json.dumps(
            {
                "event": "STARTED",
                "execution_id": execution_id,
                "flow_id": flow_id,
                "inputs": proof_inputs(inputs),
                "namespace": namespace,
                "scenario_id": scenario_id,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    execution = kestra_client.wait_execution(execution_id, timeout_seconds=timeout_seconds)
    print(
        "[KESTRA_PROOF] "
        + json.dumps(
            {
                "event": "TERMINAL",
                "execution_id": execution_id,
                "flow_id": flow_id,
                "namespace": namespace,
                "scenario_id": scenario_id,
                "state": execution.get("state", {}).get("current", "INCONNU"),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return execution


def assert_state(execution: dict, expected: str, scenario_id: str = "smoke") -> None:
    current = execution.get("state", {}).get("current")
    print(
        "[KESTRA_PROOF] "
        + json.dumps(
            {
                "event": "ASSERTION",
                "execution_id": execution.get("id"),
                "expected_state": expected,
                "flow_id": execution.get("flowId"),
                "namespace": execution.get("namespace"),
                "scenario_id": scenario_id,
                "state": current or "INCONNU",
                "verdict": "OK" if current == expected else "KO",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    assert current == expected, f"Statut attendu {expected}, obtenu {current}. Execution: {execution.get('id')}"
