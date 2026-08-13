from __future__ import annotations

from conftest import assert_state, import_flow, run_and_wait


def test_g02_validation_ci(kestra_client, repo_root):
    import_flow(kestra_client, repo_root, "kestra/flows/gouvernance/G02_validation_ci.yml")

    execution = run_and_wait(
        kestra_client,
        "poc.kestra.gouvernance",
        "G02_validation_ci",
        inputs={
            "mock_base_url": "http://mock-api:8080",
            "repository": "fkdy01/pocKestra",
            "branch": "main",
        },
    )

    assert_state(execution, "SUCCESS")


def test_g10_worker_group_mock(kestra_client, repo_root):
    import_flow(kestra_client, repo_root, "kestra/flows/gouvernance/G10_worker_group_zone_os.yml")

    execution = run_and_wait(
        kestra_client,
        "poc.kestra.gouvernance",
        "G10_worker_group_zone_os",
        inputs={"execution_mode": "mock"},
    )

    assert_state(execution, "SUCCESS")
