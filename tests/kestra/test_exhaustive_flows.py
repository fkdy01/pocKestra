from __future__ import annotations

import pytest
import yaml

from conftest import (
    FLOW_ROOT,
    assert_state,
    catalog_scenarios,
    load_flow_catalog,
    materialize_inputs,
    run_and_wait,
)


CASES = catalog_scenarios()


def test_flow_catalog_is_exhaustive():
    catalog = load_flow_catalog()
    catalog_keys = [(flow["namespace"], flow["id"]) for flow in catalog]
    assert len(catalog_keys) == len(set(catalog_keys)), "Doublon dans le catalogue exhaustif."

    repository_keys = []
    for path in sorted(FLOW_ROOT.rglob("*.yml")):
        flow = yaml.safe_load(path.read_text(encoding="utf-8"))
        repository_keys.append((flow["namespace"], flow["id"]))

    assert set(catalog_keys) == set(repository_keys)
    assert len(catalog_keys) == len(repository_keys)

    for flow in catalog:
        assert flow.get("automation") in {"automated", "manual"}
        if flow["automation"] == "manual":
            assert flow.get("manual_reason")
        else:
            assert flow.get("scenarios")


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=[f"{case['flow_id']}--{case['scenario_id']}" for case in CASES],
)
def test_flow_scenario_exhaustif(kestra_client, all_flows_imported, case):
    inputs = materialize_inputs(case["inputs"])
    execution = run_and_wait(
        kestra_client,
        case["namespace"],
        case["flow_id"],
        inputs=inputs,
        timeout_seconds=case["timeout_seconds"],
        scenario_id=case["scenario_id"],
    )
    assert_state(execution, case["expected_state"], scenario_id=case["scenario_id"])
