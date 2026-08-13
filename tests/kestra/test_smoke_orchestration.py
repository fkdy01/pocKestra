from __future__ import annotations

from conftest import assert_state, import_flow, run_and_wait


def test_f01_sequence_simple(kestra_client, repo_root):
    import_flow(kestra_client, repo_root, "kestra/flows/orchestration/F01_sequence_simple.yml")

    execution = run_and_wait(
        kestra_client,
        "poc.kestra.orchestration",
        "F01_sequence_simple",
        inputs={"demande_id": "TEST-CODEX-F01"},
    )

    assert_state(execution, "SUCCESS")


def test_f08_retry_backoff(kestra_client, repo_root):
    import_flow(kestra_client, repo_root, "kestra/flows/orchestration/F08_retry_backoff.yml")

    execution = run_and_wait(
        kestra_client,
        "poc.kestra.orchestration",
        "F08_retry_backoff",
    )

    assert_state(execution, "SUCCESS")
