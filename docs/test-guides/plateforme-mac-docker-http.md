# Tester Kestra sur Mac avec Docker Desktop en HTTP

## Prérequis

- Docker Desktop démarré ;
- Git et Python 3 installés ;
- ports locaux `8080` et `18080` disponibles.

## Installation

1. Cloner le dépôt et se placer à sa racine.
2. Créer la configuration locale :

   ```bash
   cp config/examples/mac-docker-http.env.example .env.mac.local
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

3. Reporter la valeur générée dans `KESTRA_DB_PASSWORD`. Ne pas commiter ce fichier.
4. Démarrer la plateforme HTTP :

   ```bash
   docker compose --env-file .env.mac.local -f compose.mac-http.yml up -d --build
   docker compose --env-file .env.mac.local -f compose.mac-http.yml ps
   curl --fail http://localhost:18080/health
   curl --fail http://localhost:8080/api/v1/configs
   ```

L'UI est disponible sur `http://localhost:8080`. `KESTRA_MOCK_BASE_URL` reste
`http://mock-api:8080`, car cette URL est utilisée depuis le conteneur Kestra.

## Exécuter les tests

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
set -a
source .env.mac.local
set +a
.venv/bin/python scripts/run_kestra_tests.py --kestra-live \
  --report test-reports/mac-docker-http.md
```

Le critère est `Résultat global : OK` avec 66 scénarios automatiques prouvés.
Les cinq cas marqués manuels restent à exécuter selon les guides fonctionnels.

## Arrêt

```bash
docker compose --env-file .env.mac.local -f compose.mac-http.yml down
```

Ne pas ajouter `-v`, sauf si la suppression des données du POC est explicitement voulue.
