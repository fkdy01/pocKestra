# POC Kestra Enterprise

Dépôt de travail pour le POC Kestra Enterprise en mode JDBC sur VM.

Le contenu est organisé par onglet de la grille d'évaluation : orchestration, infrastructure, exploitation, gouvernance, etc.

## Structure

```text
kestra/flows/orchestration/     # flows F01 à F20
kestra/flows/infrastructure/    # flows I01 à I15
kestra/flows/exploitation/      # flows R01 à R10
docs/use-cases/                 # catalogues par famille de cas d'usage
docs/test-guides/               # modes opératoires testeur
mock-api/                       # API FastAPI de simulation
scripts/validate_yaml.py        # validation syntaxique YAML
```

## Validation locale

```bash
docker compose up -d mock-api
python3 scripts/validate_yaml.py
```
