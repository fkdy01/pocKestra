from __future__ import annotations

from typing import Any

from kestra_api import KestraClient, KestraConfig


class FakeResponse:
    def json(self) -> dict[str, str]:
        return {"id": "execution-test"}


def test_create_execution_sends_inputs_as_multipart(monkeypatch):
    client = KestraClient()
    captured: dict[str, Any] = {}

    def fake_request(method: str, path: str, **kwargs: Any) -> FakeResponse:
        captured.update({"method": method, "path": path, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(client, "request", fake_request)

    execution_id = client.create_execution(
        "poc.kestra.gouvernance",
        "G10_worker_group_zone_os",
        inputs={
            "executer_tache_worker_reelle": False,
            "metadata": {"source": "smoke-test"},
        },
    )

    assert execution_id == "execution-test"
    assert captured["method"] == "POST"
    assert captured["files"] == {
        "executer_tache_worker_reelle": (None, "false"),
        "metadata": (None, '{"source": "smoke-test"}'),
    }


def test_create_execution_without_inputs_has_no_request_body(monkeypatch):
    client = KestraClient()
    captured: dict[str, Any] = {}

    def fake_request(method: str, path: str, **kwargs: Any) -> FakeResponse:
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(client, "request", fake_request)

    client.create_execution("poc.kestra.orchestration", "F08_retry_backoff")

    assert captured == {}


def test_config_uses_ca_bundle_when_tls_verification_is_enabled(monkeypatch):
    monkeypatch.setenv("KESTRA_VERIFY_TLS", "true")
    monkeypatch.setenv("KESTRA_CA_BUNDLE", ".kestra-tls/ca.crt")

    config = KestraConfig.from_env()

    assert config.verify_tls == ".kestra-tls/ca.crt"


def test_config_can_disable_tls_verification_even_with_ca_bundle(monkeypatch):
    monkeypatch.setenv("KESTRA_VERIFY_TLS", "false")
    monkeypatch.setenv("KESTRA_CA_BUNDLE", ".kestra-tls/ca.crt")

    config = KestraConfig.from_env()

    assert config.verify_tls is False
