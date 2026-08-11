# Onglet gouvernance — scénarios G01 à G10

Ce dossier contient les flows nécessaires au déroulé des scénarios de test de l'onglet **Gouvernance** du POC Kestra Enterprise.

## Préparation locale optionnelle

```bash
docker compose up -d mock-api
python3 scripts/validate_yaml.py
```

Importer dans Kestra les fichiers YAML du dossier :

```text
kestra/flows/gouvernance/*.yml
```

Le namespace attendu est :

```text
poc.kestra.gouvernance
```

## API mock

L'API FastAPI située dans `mock-api/` simule les fonctions de gouvernance utilisées par les tests :

- contrôle RBAC ;
- contrôle service account ;
- audit ;
- promotion et rollback ;
- contrôle tenant / namespace ;
- décision de worker group.

## Catalogue

| ID | Flow | Objectif | Preuve attendue |
|---|---|---|---|
| G01 | `G01_flow_source_git` | Flow source dans Git | URL repo, commit et chemin du flow visibles dans logs/outputs |
| G02 | `G02_validation_ci` | Validation CI | Quality gate OK/KO et blocage si KO |
| G03 | `G03_deploiement_dev_recette_prod` | Promotion dev -> recette -> prod | Production bloquée sans approbation, promotion tracée avec approbation |
| G04 | `G04_prod_readonly` | Production read-only | Modification directe UI refusée en prod |
| G05 | `G05_rollback_applicatif` | Rollback applicatif | Retour à version précédente tracé |
| G06 | `G06_separation_client_admin` | Séparation client/admin | Actions admin refusées au profil client |
| G07 | `G07_service_account_pipeline` | Service account CI/CD | Périmètre d'action du compte technique vérifié |
| G08 | `G08_audit_modification_flow` | Audit modification flow | Événement d'audit publié |
| G09 | `G09_multi_tenant_namespace` | Tenant / namespace | Accès namespace autorisé ou refusé selon tenant |
| G10 | `G10_worker_group_zone_os` | Worker group par zone/OS | Décision de routage worker group visible |

## Mode opératoire testeur

Le déroulé pas-à-pas pour un testeur non spécialiste Kestra est disponible ici :

```text
docs/test-guides/gouvernance.md
```

## Points de vigilance

- Ces flows ne remplacent pas la configuration réelle RBAC/SSO/tenants de Kestra Enterprise : ils fournissent des scénarios de test et des preuves.
- Les cas G06, G07 et G09 doivent ensuite être rejoués avec de vrais profils Kestra lorsque l'IAM/SSO est disponible.
- Le worker group `linux-outils` du cas G10 est optionnel : l'input `executer_tache_worker_reelle` doit rester à `false` si ce worker group n'existe pas.
