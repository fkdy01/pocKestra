# POC Kestra Enterprise

Dépôt de travail pour le POC Kestra Enterprise en mode JDBC sur VM.

## Lot en cours : onglet orchestration

Ce lot couvre les cas d'usage F01 à F20 de l'onglet **orchestration**.

Arborescence :

```text
kestra/flows/orchestration/        # flows Kestra de test F01-F20
kestra/flows/orchestration/common/ # sous-flows réutilisables
docs/use-cases/orchestration.md    # scénario, objectif, attendu et preuves
mock-api/                          # API FastAPI simulant un SI externe
docker-compose.yml                 # mock API locale pour les flows HTTP
scripts/validate_yaml.py           # contrôle syntaxique YAML hors Kestra
```

Les flows utilisent le namespace `poc.kestra.orchestration` et sont volontairement pédagogiques : ils cherchent à démontrer un comportement orchestration équivalent aux patterns HPOO.
