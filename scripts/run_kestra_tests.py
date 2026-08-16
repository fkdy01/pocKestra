#!/usr/bin/env python3
"""Valide le POC, exécute pytest et produit un rapport de preuve Markdown."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


VALIDATE_COMMAND = [sys.executable, "scripts/validate_yaml.py"]
PYTEST_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "tests/kestra",
    "-v",
    "--capture=tee-sys",
]
DEFAULT_REPORT_DIR = Path("test-reports")
FLOW_ROOT = Path("kestra/flows")
FLOW_CATALOG_PATH = Path("tests/kestra/flow_test_catalog.yml")
PROOF_PREFIX = "[KESTRA_PROOF] "
MAX_OUTPUT_CHARACTERS = 30_000
LIVE_PROOF_MISSING_EXIT_CODE = 3
SENSITIVE_ENV_FRAGMENTS = (
    "PASSWORD",
    "TOKEN",
    "SECRET",
    "CREDENTIAL",
    "AUTH",
    "PRIVATE_KEY",
)


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    output: str
    duration_seconds: float
    executed: bool = True


def env_live_enabled() -> bool:
    return os.getenv("KESTRA_RUN_TESTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "oui",
    }


def values_to_redact(environment: Mapping[str, str]) -> list[str]:
    values: set[str] = set()
    for name, value in environment.items():
        if not value:
            continue
        if name in {"KESTRA_URL", "KESTRA_MOCK_BASE_URL"} or any(
            fragment in name.upper() for fragment in SENSITIVE_ENV_FRAGMENTS
        ):
            values.add(value)
            if name in {"KESTRA_URL", "KESTRA_MOCK_BASE_URL"}:
                values.add(value.rstrip("/"))
    return sorted(values, key=len, reverse=True)


def redact(text: str, environment: Mapping[str, str] | None = None) -> str:
    """Masque les valeurs sensibles connues avant écriture sur disque."""
    safe = text.replace(str(Path.cwd()), "<depot-local>")
    for value in values_to_redact(environment or os.environ):
        if value:
            safe = safe.replace(value, "<valeur-masquee>")
    return safe


def run(command: Sequence[str], environment: Mapping[str, str] | None = None) -> CommandResult:
    """Exécute une commande en conservant une sortie utilisable comme preuve."""
    started_at = datetime.now().astimezone()
    printable_command = " ".join(command)
    print("+", printable_command, flush=True)
    completed = subprocess.run(
        list(command),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=dict(environment) if environment is not None else None,
    )
    duration = (datetime.now().astimezone() - started_at).total_seconds()
    safe_output = redact(completed.stdout or "", environment)
    if safe_output:
        print(safe_output, end="" if safe_output.endswith("\n") else "\n", flush=True)
    return CommandResult(list(command), completed.returncode, safe_output, duration)


def skipped_result(command: Sequence[str], reason: str) -> CommandResult:
    return CommandResult(list(command), 0, reason, 0.0, executed=False)


def parse_kestra_proofs(output: str) -> list[dict[str, str]]:
    """Extrait et consolide les preuves émises par les fixtures live."""
    by_execution: dict[str, dict[str, str]] = {}
    without_execution: list[dict[str, str]] = []
    for line in output.splitlines():
        marker_at = line.find(PROOF_PREFIX)
        if marker_at < 0:
            continue
        payload = line[marker_at + len(PROOF_PREFIX) :].strip()
        try:
            proof = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(proof, dict):
            continue
        normalized = {
            str(key): (
                json.dumps(value, ensure_ascii=False, sort_keys=True)
                if isinstance(value, (dict, list))
                else str(value)
            )
            for key, value in proof.items()
            if value is not None
        }
        execution_id = normalized.get("execution_id")
        if execution_id:
            by_execution.setdefault(execution_id, {}).update(normalized)
        else:
            without_execution.append(normalized)
    return [*by_execution.values(), *without_execution]


def load_flow_catalog(path: Path = FLOW_CATALOG_PATH) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    flows = payload.get("flows") if isinstance(payload, dict) else None
    if not isinstance(flows, list):
        raise ValueError(f"{path} doit contenir une liste `flows`.")
    return flows


def discover_flow_inventory(root: Path = FLOW_ROOT) -> dict[tuple[str, str], Path]:
    inventory: dict[tuple[str, str], Path] = {}
    for path in sorted(root.rglob("*.yml")):
        flow = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(flow, dict) or not flow.get("namespace") or not flow.get("id"):
            raise ValueError(f"Flow sans namespace ou id : {path}")
        key = (str(flow["namespace"]), str(flow["id"]))
        if key in inventory:
            raise ValueError(f"Flow dupliqué dans l'inventaire : {key[0]}.{key[1]}")
        inventory[key] = path
    return inventory


def validate_flow_catalog(
    catalog: list[dict[str, Any]],
    inventory: Mapping[tuple[str, str], Path],
) -> list[str]:
    errors: list[str] = []
    catalog_keys: list[tuple[str, str]] = []
    for index, flow in enumerate(catalog, start=1):
        namespace = flow.get("namespace")
        flow_id = flow.get("id")
        if not namespace or not flow_id:
            errors.append(f"Entrée {index} sans namespace ou id.")
            continue
        key = (str(namespace), str(flow_id))
        catalog_keys.append(key)
        automation = flow.get("automation")
        if automation not in {"automated", "manual"}:
            errors.append(f"{key[0]}.{key[1]} : automation invalide.")
        if automation == "manual" and not flow.get("manual_reason"):
            errors.append(f"{key[0]}.{key[1]} : justification manuelle absente.")
        if automation == "automated":
            scenarios = flow.get("scenarios")
            if not isinstance(scenarios, list) or not scenarios:
                errors.append(f"{key[0]}.{key[1]} : aucun scénario automatique.")
                continue
            scenario_ids = [scenario.get("id") for scenario in scenarios]
            if None in scenario_ids or len(scenario_ids) != len(set(scenario_ids)):
                errors.append(f"{key[0]}.{key[1]} : scénarios sans id ou dupliqués.")
            for scenario in scenarios:
                if not scenario.get("expected_state"):
                    errors.append(
                        f"{key[0]}.{key[1]}/{scenario.get('id', '?')} : état attendu absent."
                    )

    duplicates = sorted({key for key in catalog_keys if catalog_keys.count(key) > 1})
    errors.extend(f"Entrée dupliquée : {namespace}.{flow_id}." for namespace, flow_id in duplicates)
    catalog_set = set(catalog_keys)
    inventory_set = set(inventory)
    errors.extend(
        f"Flow absent du catalogue : {namespace}.{flow_id}."
        for namespace, flow_id in sorted(inventory_set - catalog_set)
    )
    errors.extend(
        f"Flow absent du dépôt : {namespace}.{flow_id}."
        for namespace, flow_id in sorted(catalog_set - inventory_set)
    )
    return errors


def expected_automatic_scenarios(catalog: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    return {
        (str(flow["namespace"]), str(flow["id"]), str(scenario["id"]))
        for flow in catalog
        if flow.get("automation") == "automated"
        for scenario in flow.get("scenarios", [])
    }


def proven_scenarios(proofs: list[dict[str, str]]) -> set[tuple[str, str, str]]:
    return {
        (proof["namespace"], proof["flow_id"], proof["scenario_id"])
        for proof in proofs
        if proof.get("event") == "ASSERTION"
        and proof.get("verdict") == "OK"
        and proof.get("namespace")
        and proof.get("flow_id")
        and proof.get("scenario_id")
    }


def proof_by_scenario(
    proofs: list[dict[str, str]],
) -> dict[tuple[str, str, str], dict[str, str]]:
    result: dict[tuple[str, str, str], dict[str, str]] = {}
    for proof in proofs:
        if proof.get("event") != "ASSERTION":
            continue
        key = (proof.get("namespace", ""), proof.get("flow_id", ""), proof.get("scenario_id", ""))
        result[key] = proof
    return result


def command_for_report(command: Sequence[str]) -> str:
    normalized = list(command)
    if normalized and Path(normalized[0]).name.startswith("python"):
        normalized[0] = "python3"
    return " ".join(normalized)


def status_label(result: CommandResult) -> str:
    if not result.executed:
        return "NON EXÉCUTÉ"
    return "OK" if result.returncode == 0 else "KO"


def bounded_output(output: str) -> str:
    if len(output) <= MAX_OUTPUT_CHARACTERS:
        return output.strip() or "(aucune sortie)"
    removed = len(output) - MAX_OUTPUT_CHARACTERS
    return (
        output[: MAX_OUTPUT_CHARACTERS // 2]
        + f"\n\n... {removed} caractères retirés du rapport ...\n\n"
        + output[-MAX_OUTPUT_CHARACTERS // 2 :]
    ).strip()


def markdown_cell(value: str | None) -> str:
    return (value or "—").replace("|", "\\|").replace("\n", " ")


def render_report(
    *,
    generated_at: datetime,
    live_enabled: bool,
    validation: CommandResult,
    pytest_result: CommandResult,
    environment: Mapping[str, str] | None = None,
    catalog: list[dict[str, Any]] | None = None,
    inventory: Mapping[tuple[str, str], Path] | None = None,
    catalog_errors: Sequence[str] = (),
) -> str:
    safe_validation_output = redact(validation.output, environment)
    safe_pytest_output = redact(pytest_result.output, environment)
    proofs = parse_kestra_proofs(safe_pytest_output)
    catalog = catalog or []
    inventory = inventory or {}
    expected_scenarios = expected_automatic_scenarios(catalog)
    observed_scenarios = proven_scenarios(proofs)
    missing_scenarios = expected_scenarios - observed_scenarios
    live_proof_ok = not live_enabled or (
        bool(expected_scenarios) and not missing_scenarios and not catalog_errors
    )
    overall_ok = (
        validation.returncode == 0
        and pytest_result.returncode == 0
        and not catalog_errors
        and live_proof_ok
    )
    overall_status = "OK" if overall_ok else "KO"
    live_status = "activés" if live_enabled else "désactivés (tests unitaires et skips uniquement)"

    lines = [
        "# Rapport automatisé des tests Kestra",
        "",
        f"- Horodatage : `{generated_at.isoformat(timespec='seconds')}`",
        f"- Résultat global : **{overall_status}**",
        f"- Tests live Kestra : **{live_status}**",
        f"- Flows inventoriés : **{len(inventory)}**",
        f"- Scénarios automatiques attendus : **{len(expected_scenarios)}**",
        f"- Scénarios automatiques prouvés : **{len(observed_scenarios & expected_scenarios)}**",
        "- Cible Kestra : valeur volontairement non consignée",
        "- Secrets et valeurs d'authentification : valeurs masquées avant écriture",
        "",
        "## Synthèse",
        "",
        "| Étape | Statut | Code retour | Durée |",
        "|---|---:|---:|---:|",
        f"| Validation YAML | {status_label(validation)} | {validation.returncode} | {validation.duration_seconds:.2f} s |",
        f"| pytest | {status_label(pytest_result)} | {pytest_result.returncode} | {pytest_result.duration_seconds:.2f} s |",
        f"| Preuves live Kestra | {'OK' if live_proof_ok else 'KO'} | {'—' if live_proof_ok else LIVE_PROOF_MISSING_EXIT_CODE} | — |",
        "",
        "## Preuves d'exécution Kestra",
        "",
    ]

    if proofs:
        lines.extend(
            [
                "| Namespace | Flow | Inputs utilisés | ID d'exécution | Attendu | Observé | Verdict |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for proof in proofs:
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_cell(proof.get("namespace")),
                        markdown_cell(proof.get("flow_id")),
                        markdown_cell(proof.get("inputs")),
                        markdown_cell(proof.get("execution_id")),
                        markdown_cell(proof.get("expected_state")),
                        markdown_cell(proof.get("state") or proof.get("event")),
                        markdown_cell(proof.get("verdict")),
                    ]
                )
                + " |"
            )
    elif live_enabled:
        lines.append("Aucune preuve structurée n'a été collectée. Consulter la sortie pytest ci-dessous.")
    else:
        lines.append("Non applicable : les tests live n'étaient pas activés.")

    lines.extend(["", "## Matrice exhaustive des flows", ""])
    if catalog_errors:
        lines.append("Le catalogue exhaustif est invalide :")
        lines.append("")
        lines.extend(f"- {error}" for error in catalog_errors)
        lines.append("")

    if catalog:
        proofs_by_case = proof_by_scenario(proofs)
        lines.extend(
            [
                "| Domaine | Flow | Type | Scénario | YAML | Mode | Exécution | Attendu | Observé | Verdict / justification |",
                "|---|---|---|---|---|---|---|---|---|---|",
            ]
        )
        for flow in catalog:
            namespace = str(flow.get("namespace", ""))
            flow_id = str(flow.get("id", ""))
            domain = namespace.rsplit(".", 1)[-1] if namespace else "—"
            flow_type = "support" if flow.get("support_flow") else "cas d'usage"
            yaml_status = "OK" if validation.returncode == 0 else "KO global"
            if flow.get("automation") == "manual":
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            markdown_cell(domain),
                            markdown_cell(flow_id),
                            flow_type,
                            "manuel",
                            yaml_status,
                            "MANUEL",
                            "NON EXÉCUTÉ",
                            "—",
                            "—",
                            markdown_cell(str(flow.get("manual_reason", "Justification absente"))),
                        ]
                    )
                    + " |"
                )
                continue

            for scenario in flow.get("scenarios", []):
                scenario_id = str(scenario.get("id", ""))
                proof = proofs_by_case.get((namespace, flow_id, scenario_id), {})
                if proof:
                    execution = proof.get("execution_id", "—")
                    observed = proof.get("state", "—")
                    verdict = proof.get("verdict", "—")
                elif live_enabled:
                    execution = "NON EXÉCUTÉ"
                    observed = "—"
                    verdict = "KO — preuve absente"
                else:
                    execution = "NON EXÉCUTÉ"
                    observed = "—"
                    verdict = "NON TESTÉ"
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            markdown_cell(domain),
                            markdown_cell(flow_id),
                            flow_type,
                            markdown_cell(scenario_id),
                            yaml_status,
                            "AUTO",
                            markdown_cell(execution),
                            markdown_cell(str(scenario.get("expected_state", "—"))),
                            markdown_cell(observed),
                            markdown_cell(verdict),
                        ]
                    )
                    + " |"
                )
    else:
        lines.append("Catalogue exhaustif indisponible.")

    for title, result, output in (
        ("Validation syntaxique YAML", validation, safe_validation_output),
        ("Tests pytest", pytest_result, safe_pytest_output),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                f"Commande : `{command_for_report(result.command)}`",
                "",
                f"Statut : **{status_label(result)}** (code `{result.returncode}`)",
                "",
                "~~~text",
                bounded_output(output),
                "~~~",
            ]
        )

    lines.extend(
        [
            "",
            "## Lecture du résultat",
            "",
            "- `OK` prouve que la commande concernée a réussi.",
            "- Un test `SKIPPED` ne prouve pas une exécution dans Kestra.",
            "- Une ligne dans « Preuves d'exécution Kestra » provient d'une exécution réellement créée par le smoke test.",
            "- Ce rapport textuel complète, mais ne remplace pas, les captures demandées aux testeurs manuels.",
            "",
        ]
    )
    return "\n".join(lines)


def default_report_path(generated_at: datetime) -> Path:
    stamp = generated_at.strftime("%Y%m%d-%H%M%S")
    return DEFAULT_REPORT_DIR / f"kestra-tests-{stamp}.md"


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valide les YAML, lance pytest et génère un rapport Markdown expurgé."
    )
    parser.add_argument(
        "--kestra-live",
        action="store_true",
        help="Activer les tests contre l'instance configurée par KESTRA_URL.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Chemin du rapport Markdown (défaut : test-reports/kestra-tests-<horodatage>.md).",
    )
    args = parser.parse_args()

    generated_at = datetime.now().astimezone()
    report_path = args.report or default_report_path(generated_at)
    live_enabled = args.kestra_live or env_live_enabled()
    environment = dict(os.environ)

    try:
        catalog = load_flow_catalog()
        inventory = discover_flow_inventory()
        catalog_errors = validate_flow_catalog(catalog, inventory)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        catalog = []
        inventory = {}
        catalog_errors = [str(exc)]

    validation = run(VALIDATE_COMMAND, environment)
    pytest_command = [*PYTEST_COMMAND, *(["--kestra-live"] if live_enabled else [])]
    if validation.returncode == 0:
        pytest_result = run(pytest_command, environment)
    else:
        pytest_result = skipped_result(
            pytest_command,
            "pytest non exécuté car la validation YAML a échoué.",
        )

    report = render_report(
        generated_at=generated_at,
        live_enabled=live_enabled,
        validation=validation,
        pytest_result=pytest_result,
        environment=environment,
        catalog=catalog,
        inventory=inventory,
        catalog_errors=catalog_errors,
    )
    write_report(report_path, report)
    print(f"[REPORT] Rapport Markdown généré : {report_path}", flush=True)

    if validation.returncode != 0:
        return validation.returncode
    if pytest_result.returncode != 0:
        return pytest_result.returncode
    if catalog_errors:
        return 4
    if live_enabled and (
        expected_automatic_scenarios(catalog)
        - proven_scenarios(parse_kestra_proofs(pytest_result.output))
    ):
        return LIVE_PROOF_MISSING_EXIT_CODE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
