from __future__ import annotations

from uuid import uuid4

from conftest import assert_state, import_flow, run_and_wait


def test_i01_api_rest_interne(kestra_client, repo_root):
    import_flow(kestra_client, repo_root, "kestra/flows/infrastructure/I01_api_rest_interne.yml")

    execution = run_and_wait(
        kestra_client,
        "poc.kestra.infrastructure",
        "I01_api_rest_interne",
        inputs={"mock_base_url": "http://mock-api:8080", "count": "2"},
    )

    assert_state(execution, "SUCCESS")


def test_i13_erreur_fournisseur_temporaire(kestra_client, repo_root):
    import_flow(kestra_client, repo_root, "kestra/flows/infrastructure/I13_erreur_fournisseur_temporaire.yml")

    execution = run_and_wait(
        kestra_client,
        "poc.kestra.infrastructure",
        "I13_erreur_fournisseur_temporaire",
        inputs={
            "mock_base_url": "http://mock-api:8080",
            "key": f"codex-i13-{uuid4().hex}",
        },
        timeout_seconds=180,
    )

    assert_state(execution, "WARNING")
