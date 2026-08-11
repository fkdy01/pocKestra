# Mode opératoire testeur — onglet gouvernance

Ce document décrit le mode opératoire détaillé pour exécuter les cas d'usage **G01 à G10** de l'onglet Gouvernance du POC Kestra Enterprise.

Il est rédigé pour un testeur qui n'est pas spécialiste Kestra.

## 1. Objectif du guide

Vérifier que le POC Kestra démontre les principes de gouvernance nécessaires au remplacement HPOO : source Git, validation CI, promotion, production read-only, rollback, séparation client/admin, comptes de service, audit, isolation tenant/namespace et worker groups.

## 2. Pré-requis communs

Le testeur doit disposer d'un accès à Kestra, du droit d'exécuter les flows du namespace `poc.kestra.gouvernance`, et du droit de consulter logs et outputs.

Importer les flows :

```text
kestra/flows/gouvernance/*.yml
```

Lancer le mock si nécessaire :

```bash
docker compose up -d mock-api
```

URL par défaut du mock :

```text
http://mock-api:8080
```

Pour chaque test, collecter l'ID du cas, le flow, l'execution ID, les inputs, le statut final, les logs et les outputs.

---

## G01 — Flow source dans Git

**Objectif :** relier une exécution Kestra au fichier YAML source.

**Flow :** `G01_flow_source_git`

**Inputs recommandés :**

| Input | Valeur |
|---|---|
| `repository_url` | `https://github.com/fkdy01/pocKestra` |
| `commit_sha` | SHA du commit testé ou `A_RENSEIGNER` |
| `flow_path` | `kestra/flows/gouvernance/G01_flow_source_git.yml` |

**Étapes :** ouvrir le flow, cliquer sur **Execute**, renseigner les inputs, lancer l'exécution, puis consulter logs et outputs.

**Résultat attendu :** `source_trace` contient le repo, le commit et le chemin du flow.

**OK / KO :** OK si le testeur peut retrouver précisément la source Git du flow exécuté.

---

## G02 — Validation CI

**Objectif :** vérifier qu'un quality gate CI peut autoriser ou bloquer une promotion.

**Flow :** `G02_validation_ci`

Exécuter deux scénarios :

| Scénario | `quality_gate` | Attendu |
|---|---|---|
| CI OK | `pass` | Succès |
| CI KO | `fail` | Échec contrôlé |

**Preuves :** statut final, logs, output `pipeline_report`.

**OK / KO :** OK si `pass` autorise et `fail` bloque explicitement.

---

## G03 — Promotion dev -> recette -> prod

**Objectif :** vérifier que la production nécessite une approbation.

**Flow :** `G03_deploiement_dev_recette_prod`

Exécuter trois scénarios :

| Environnement | Approbation | Attendu |
|---|---|---|
| `recette` | `false` | Succès |
| `prod` | `false` | Échec |
| `prod` | `true` | Succès |

**Preuves :** statut final, output `promotion`, log de promotion ou message d'échec.

**OK / KO :** OK si la prod sans approbation est bloquée et si la prod approuvée est tracée.

---

## G04 — Production read-only

**Objectif :** refuser une modification directe depuis l'UI en production.

**Flow :** `G04_prod_readonly`

**Inputs :** `environnement=prod`, `modification_directe_ui=true`.

**Résultat attendu :** l'exécution échoue avec le message `Production read-only : modification directe UI interdite`.

**Preuves :** statut en échec attendu et log de refus.

**OK / KO :** OK si le refus est explicite.

---

## G05 — Rollback applicatif

**Objectif :** tracer un retour à une version précédente.

**Flow :** `G05_rollback_applicatif`

**Inputs :** `application=poc-kestra`, `version_actuelle=1.1.0`, `version_cible=1.0.0`, `motif=Incident après mise en production`.

**Résultat attendu :** le flow se termine en succès et l'output `rollback_trace` contient la version source, la version cible et le motif.

**OK / KO :** OK si le rollback est tracé de manière exploitable.

---

## G06 — Séparation client / administration

**Objectif :** démontrer qu'un profil client ne peut pas réaliser une action admin.

**Flow :** `G06_separation_client_admin`

Scénarios :

| Profil | Action | Attendu |
|---|---|---|
| `client` | `execute_flow` | Succès |
| `client` | `manage_rbac` | Échec |
| `admin` | `manage_rbac` | Succès |

**OK / KO :** OK si les actions admin sont refusées au profil client et autorisées au profil admin.

---

## G07 — Service account pipeline

**Objectif :** vérifier que le compte technique CI/CD a un périmètre limité.

**Flow :** `G07_service_account_pipeline`

Scénarios :

| Service account | Opération | Attendu |
|---|---|---|
| `svc-kestra-cicd` | `deploy_flow` | Succès |
| `svc-kestra-cicd` | `delete_tenant` | Échec |
| `svc-kestra-cicd` | `manage_secrets` | Échec |

**OK / KO :** OK si le compte technique peut déployer mais ne peut pas administrer les tenants ou secrets.

---

## G08 — Audit modification flow

**Objectif :** vérifier qu'une action sensible produit une trace d'audit.

**Flow :** `G08_audit_modification_flow`

**Inputs :** `actor=testeur.poc`, `action=update_flow`, `target_flow=poc.kestra.gouvernance.G08_audit_modification_flow`.

**Résultat attendu :** l'output `audit_event` contient un `audit_id`, l'acteur, l'action, la cible et l'execution ID.

**OK / KO :** OK si la trace est complète.

---

## G09 — Multi-tenant / namespace

**Objectif :** démontrer l'isolation logique des tenants.

**Flow :** `G09_multi_tenant_namespace`

Scénarios :

| Tenant | Namespace | Attendu |
|---|---|---|
| `client-a` | `poc.kestra.client-a` | Succès |
| `client-a` | `poc.kestra.client-b` | Échec |
| `admin` | `poc.kestra.client-b` | Succès |

**OK / KO :** OK si un tenant ne peut agir que dans son namespace, sauf profil admin.

---

## G10 — Worker group par zone / OS

**Objectif :** vérifier la décision de worker group selon la zone et l'OS.

**Flow :** `G10_worker_group_zone_os`

**Inputs recommandés :** `zone=outils`, `os_cible=linux`, `executer_tache_worker_reelle=false`.

**Résultat attendu :** l'output `worker_group_decision` contient un worker group de type `linux-outils`.

**Point de vigilance :** laisser `executer_tache_worker_reelle=false` si le worker group `linux-outils` n'existe pas dans le POC.

**OK / KO :** OK si la décision de routage est visible et cohérente.

---

## Synthèse de fin de campagne

| ID | Statut | Execution ID | Preuve | Commentaire |
|---|---|---|---|---|
| G01 |  |  |  |  |
| G02 |  |  |  |  |
| G03 |  |  |  |  |
| G04 |  |  |  |  |
| G05 |  |  |  |  |
| G06 |  |  |  |  |
| G07 |  |  |  |  |
| G08 |  |  |  |  |
| G09 |  |  |  |  |
| G10 |  |  |  |  |
