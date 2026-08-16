from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from run_kestra_tests import (
    CommandResult,
    expected_automatic_scenarios,
    parse_kestra_proofs,
    proven_scenarios,
    redact,
    render_report,
    validate_flow_catalog,
)
from conftest import materialize_inputs, proof_inputs


def test_parse_kestra_proofs_merges_started_and_terminal_events():
    output = """
[KESTRA_PROOF] {"event":"STARTED","namespace":"poc.kestra.orchestration","flow_id":"F01_sequence_simple","execution_id":"exec-123","inputs":{"demande_id":"TEST-CODEX-F01"}}
[KESTRA_PROOF] {"event":"TERMINAL","namespace":"poc.kestra.orchestration","flow_id":"F01_sequence_simple","execution_id":"exec-123","state":"SUCCESS"}
[KESTRA_PROOF] {"event":"ASSERTION","namespace":"poc.kestra.orchestration","flow_id":"F01_sequence_simple","execution_id":"exec-123","expected_state":"SUCCESS","state":"SUCCESS","verdict":"OK"}
"""

    assert parse_kestra_proofs(output) == [
        {
            "event": "ASSERTION",
            "namespace": "poc.kestra.orchestration",
            "flow_id": "F01_sequence_simple",
            "execution_id": "exec-123",
            "inputs": '{"demande_id": "TEST-CODEX-F01"}',
            "expected_state": "SUCCESS",
            "state": "SUCCESS",
            "verdict": "OK",
        }
    ]


def test_render_report_contains_results_and_structured_proof_without_secrets():
    secret = "mot-de-passe-a-ne-pas-ecrire"
    target = "https://kestra.interne.invalid:8443"
    environment = {
        "KESTRA_PASSWORD": secret,
        "KESTRA_URL": target,
    }
    validation = CommandResult(
        ["python3", "scripts/validate_yaml.py"],
        0,
        "OK: 55 flow(s) YAML valide(s).\n",
        0.5,
    )
    pytest_result = CommandResult(
        ["python3", "-m", "pytest", "tests/kestra", "--kestra-live"],
        0,
        (
            f"cible={target} secret={secret}\n"
            '[KESTRA_PROOF] {"event":"TERMINAL","namespace":"poc.kestra.orchestration",'
            '"flow_id":"F01_sequence_simple","execution_id":"exec-456","state":"SUCCESS"}\n'
            "8 passed\n"
        ),
        4.2,
    )

    report = render_report(
        generated_at=datetime(2026, 8, 13, 10, 30, tzinfo=timezone.utc),
        live_enabled=True,
        validation=validation,
        pytest_result=pytest_result,
        environment=environment,
    )

    assert "2026-08-13T10:30:00+00:00" in report
    assert "F01_sequence_simple" in report
    assert "exec-456" in report
    assert "SUCCESS" in report
    assert "Attendu" in report
    assert "Verdict" in report
    assert "Inputs utilisés" in report
    assert "Validation YAML | OK" in report
    assert secret not in report
    assert target not in report
    assert "<valeur-masquee>" in report


def test_redact_masks_authentication_and_target_values():
    environment = {
        "KESTRA_API_TOKEN": "token-test-123",
        "KESTRA_URL": "https://localhost:8443/",
    }

    result = redact(
        f"token-test-123 https://localhost:8443/ https://localhost:8443 {Path.cwd()}",
        environment,
    )

    assert "token-test-123" not in result
    assert "https://localhost:8443" not in result
    assert str(Path.cwd()) not in result
    assert "<depot-local>" in result


def test_materialize_inputs_uses_remote_mock_url(monkeypatch):
    monkeypatch.setenv("KESTRA_MOCK_BASE_URL", "https://mock.example.invalid/")

    assert materialize_inputs({"mock_base_url": "http://mock-api:8080"}) == {
        "mock_base_url": "https://mock.example.invalid"
    }


def test_render_report_is_ko_when_live_tests_produce_no_execution_proof():
    success = CommandResult(["python3"], 0, "7 passed, 7 skipped", 0.1)

    report = render_report(
        generated_at=datetime(2026, 8, 13, 10, 30, tzinfo=timezone.utc),
        live_enabled=True,
        validation=success,
        pytest_result=success,
        environment={},
    )

    assert "Résultat global : **KO**" in report
    assert "Preuves live Kestra | KO | 3" in report


def test_proof_inputs_masks_sensitive_fields_recursively():
    inputs = {
        "ticket": "TEST-123",
        "options": {
            "api_token": "secret-token",
            "mode": "mock",
        },
        "targets": [{"password": "secret-password", "host": "srv-001"}],
    }

    assert proof_inputs(inputs) == {
        "ticket": "TEST-123",
        "options": {
            "api_token": "<valeur-masquee>",
            "mode": "mock",
        },
        "targets": [{"password": "<valeur-masquee>", "host": "srv-001"}],
    }


def test_catalog_coverage_requires_every_automatic_scenario():
    catalog = [
        {
            "namespace": "poc.kestra.test",
            "id": "flow_test",
            "automation": "automated",
            "scenarios": [
                {"id": "success", "expected_state": "SUCCESS"},
                {"id": "failure", "expected_state": "FAILED"},
            ],
        }
    ]
    proofs = [
        {
            "event": "ASSERTION",
            "namespace": "poc.kestra.test",
            "flow_id": "flow_test",
            "scenario_id": "success",
            "verdict": "OK",
        }
    ]

    assert expected_automatic_scenarios(catalog) - proven_scenarios(proofs) == {
        ("poc.kestra.test", "flow_test", "failure")
    }


def test_catalog_validation_detects_an_unlisted_flow(tmp_path):
    catalog = [
        {
            "namespace": "poc.kestra.test",
            "id": "flow_a",
            "automation": "manual",
            "manual_reason": "Action humaine.",
        }
    ]
    inventory = {
        ("poc.kestra.test", "flow_a"): tmp_path / "flow_a.yml",
        ("poc.kestra.test", "flow_b"): tmp_path / "flow_b.yml",
    }

    errors = validate_flow_catalog(catalog, inventory)

    assert errors == ["Flow absent du catalogue : poc.kestra.test.flow_b."]
