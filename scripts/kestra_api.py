#!/usr/bin/env python3
"""Client REST minimal pour piloter un Kestra OSS/Enterprise depuis les tests."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
import yaml


TERMINAL_STATES = {"SUCCESS", "FAILED", "KILLED", "WARNING", "CANCELLED"}


@dataclass
class KestraConfig:
    url: str
    tenant: str = "main"
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    verify_tls: bool = True
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "KestraConfig":
        verify_value = os.getenv("KESTRA_VERIFY_TLS", "true").strip().lower()
        return cls(
            url=os.getenv("KESTRA_URL", "http://localhost:8080").rstrip("/"),
            tenant=os.getenv("KESTRA_TENANT", "main"),
            username=os.getenv("KESTRA_USERNAME") or None,
            password=os.getenv("KESTRA_PASSWORD") or None,
            api_token=os.getenv("KESTRA_API_TOKEN") or None,
            verify_tls=verify_value not in {"0", "false", "no", "non"},
            timeout_seconds=int(os.getenv("KESTRA_HTTP_TIMEOUT", "30")),
        )


class KestraApiError(RuntimeError):
    """Erreur HTTP ou fonctionnelle retournée par Kestra."""


class KestraClient:
    def __init__(self, config: Optional[KestraConfig] = None) -> None:
        self.config = config or KestraConfig.from_env()
        self.session = requests.Session()

        if self.config.api_token:
            self.session.headers.update({"Authorization": f"Bearer {self.config.api_token}"})

        if self.config.username and self.config.password:
            self.session.auth = (self.config.username, self.config.password)

    def _url(self, path: str) -> str:
        return f"{self.config.url}{path}"

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.config.timeout_seconds)
        kwargs.setdefault("verify", self.config.verify_tls)
        response = self.session.request(method, self._url(path), **kwargs)

        if response.status_code >= 400:
            raise KestraApiError(
                f"{method} {path} -> HTTP {response.status_code}: {response.text[:500]}"
            )

        return response

    def health(self) -> bool:
        """Retourne True si Kestra répond."""
        candidates = ["/health", "/api/v1/health", "/"]
        for path in candidates:
            try:
                response = self.session.get(
                    self._url(path),
                    timeout=5,
                    verify=self.config.verify_tls,
                    auth=self.session.auth,
                    headers=self.session.headers,
                )
                if response.status_code < 500:
                    return True
            except requests.RequestException:
                continue
        return False

    def create_or_update_flow_source(self, source: str) -> Dict[str, Any]:
        """Crée ou remplace un flow à partir de son YAML source."""
        flow = yaml.safe_load(source)
        if not isinstance(flow, dict):
            raise ValueError("Le YAML du flow ne contient pas un objet racine.")
        namespace = flow.get("namespace")
        flow_id = flow.get("id")
        if not namespace or not flow_id:
            raise ValueError("Le flow doit contenir les champs `id` et `namespace`.")

        headers = {"Content-Type": "application/x-yaml"}
        create_path = f"/api/v1/{self.config.tenant}/flows"
        response = self.session.post(
            self._url(create_path),
            data=source.encode("utf-8"),
            headers=headers,
            timeout=self.config.timeout_seconds,
            verify=self.config.verify_tls,
            auth=self.session.auth,
        )

        if response.status_code in {200, 201}:
            return response.json() if response.content else {"id": flow_id, "namespace": namespace}

        if response.status_code not in {400, 409, 422}:
            raise KestraApiError(
                f"POST {create_path} -> HTTP {response.status_code}: {response.text[:500]}"
            )

        update_path = f"/api/v1/{self.config.tenant}/flows/{namespace}/{flow_id}"
        update = self.session.put(
            self._url(update_path),
            data=source.encode("utf-8"),
            headers=headers,
            timeout=self.config.timeout_seconds,
            verify=self.config.verify_tls,
            auth=self.session.auth,
        )

        if update.status_code >= 400:
            raise KestraApiError(
                "Impossible de créer ou mettre à jour le flow "
                f"{namespace}/{flow_id}. Create HTTP {response.status_code}; "
                f"Update HTTP {update.status_code}: {update.text[:500]}"
            )

        return update.json() if update.content else {"id": flow_id, "namespace": namespace}

    def import_flow_file(self, path: Path) -> Dict[str, Any]:
        return self.create_or_update_flow_source(path.read_text(encoding="utf-8"))

    def import_flow_files(self, paths: Iterable[Path]) -> None:
        for path in paths:
            self.import_flow_file(path)

    def create_execution(
        self,
        namespace: str,
        flow_id: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        path = f"/api/v1/{self.config.tenant}/executions/{namespace}/{flow_id}"
        response = self.request("POST", path, data=inputs or {})
        payload = response.json()
        execution_id = payload.get("id")
        if not execution_id:
            raise KestraApiError(f"Réponse de création d'exécution sans id: {payload}")
        return execution_id

    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        path = f"/api/v1/{self.config.tenant}/executions/{execution_id}"
        return self.request("GET", path).json()

    def wait_execution(self, execution_id: str, timeout_seconds: int = 120) -> Dict[str, Any]:
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            execution = self.get_execution(execution_id)
            current = execution.get("state", {}).get("current")
            if current in TERMINAL_STATES:
                return execution
            time.sleep(2)

        raise TimeoutError(f"L'exécution {execution_id} n'est pas terminée après {timeout_seconds}s")


def load_flow_identity(path: Path) -> tuple[str, str]:
    flow = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(flow, dict) or "namespace" not in flow or "id" not in flow:
        raise ValueError(f"Flow invalide ou incomplet: {path}")
    return str(flow["namespace"]), str(flow["id"])
