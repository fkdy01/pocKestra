# Onglet orchestration — scénarios F01 à F20

Ce dossier contient les flows nécessaires au déroulé des scénarios de test de l'onglet **orchestration** du POC Kestra Enterprise.

## Préparation locale optionnelle

```bash
docker compose up -d mock-api
python3 scripts/validate_yaml.py
```

Importer dans Kestra les fichiers YAML du dossier `kestra/flows/orchestration` et du sous-dossier `common`.

## API mock

L'API FastAPI située dans `mock-api/` simule un SI externe : healthcheck, echo, API instable, opération longue par polling et ticketing simple.

## Catalogue

| ID | Flow | Objectif | Preuve attendue |
|---|---|---|---|
| F01 | `F01_sequence_simple` | Flow séquentiel simple | Logs et output `resultat` |
| F02 | `F02_parametres_validation` | Inputs obligatoires/facultatifs | Branche prod réelle vs autorisée |
| F03 | `F03_conditions_switch` | If/else et switch | Branche correcte exécutée |
| F04 | `F04_boucle_liste_serveurs` | Boucle sur liste | Une itération par serveur |
| F05 | `F05_parallelisation` | Parallélisation contrôlée | Concurrence limitée |
| F06 | `F06_subflow_parametres_retour` | Subflow avec outputs | Output du sous-flow journalisé |
| F07 | `F07_subflow_erreur_reprise` | Subflow en erreur/reprise | Échec contrôlé puis succès |
| F08 | `F08_retry_backoff` | Retry constant | Succès après retries |
| F09 | `F09_timeout_tache_longue` | Timeout | Branche `errors` exécutée |
| F10 | `F10_gestion_erreur_locale` | Erreur locale non bloquante | Le flow continue |
| F11 | `F11_gestion_erreur_globale` | Erreur globale | Branche `errors` exécutée |
| F12 | `F12_reprise_manuelle` | Correction puis relance | KO puis OK |
| F13 | `F13_pause_approbation_humaine` | Pause humaine | Suspension puis reprise |
| F14 | `F14_execution_programmee` | Scheduler | Déclenchement périodique |
| F15 | `F15_execution_api_evenementielle` | API/webhook | Appel mock `/echo` |
| F16 | `F16_idempotence` | Idempotence | Même clé d'idempotence |
| F17 | `F17_compensation` | Compensation | Sous-flow compensation appelé |
| F18 | `F18_correlation_metier` | Corrélation métier | Label et ticket mock corrélés |
| F19 | `F19_secrets` | Secret non stocké en clair | Référence `secret()` |
| F20 | `F20_gros_outputs_logs` | Gros output/logs | Fichier output et taille |

## Points de vigilance

- Les flows utilisent parfois le `Process` task runner pour les scripts Shell de test : à borner par worker group, compte OS dédié et allowlist de plugins.
- Certains cas d'erreur sont volontairement en échec pour tester reprise, alerting et diagnostic.
