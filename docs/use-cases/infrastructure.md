# Onglet infrastructure — scénarios I01 à I15

Ce dossier contient les flows nécessaires au déroulé des scénarios de test de l'onglet **Infrastructure** du POC Kestra Enterprise.

## Préparation locale optionnelle

```bash
docker compose up -d mock-api
python3 scripts/validate_yaml.py
```

Importer dans Kestra les fichiers YAML du dossier :

```text
kestra/flows/infrastructure/*.yml
```

Le namespace attendu est :

```text
poc.kestra.infrastructure
```

## API mock

L'API FastAPI située dans `mock-api/` simule plusieurs SI externes utilisés par les tests infrastructure :

- CMDB ;
- ITSM / changements ;
- AAP / Ansible Automation Platform ;
- VMware / vCenter ;
- AD / LDAP ;
- SCCM ;
- tests de zones réseau ;
- opérations longues et API instable.

## Catalogue

| ID | Flow | Objectif | Preuve attendue |
|---|---|---|---|
| I01 | `I01_api_rest_interne` | Appel API REST interne | Healthcheck API et liste de serveurs mock |
| I02 | `I02_itsm_changement_mock` | Appel ITSM simulé | Création de changement mock |
| I03 | `I03_ssh_linux` | Exécution SSH Linux | Mode mock par défaut ou SSH réel avec secret |
| I04 | `I04_powershell_windows` | Exécution PowerShell Windows | Mode mock par défaut ou worker Windows |
| I05 | `I05_worker_windows_sccm` | Worker Windows SCCM | Routage worker group et déploiement SCCM mock |
| I06 | `I06_worker_linux_podman` | Worker Linux Podman | Simulation ou exécution Podman sur worker Linux |
| I07 | `I07_ansible_aap` | Appel Ansible/AAP | Lancement job template et lecture statut |
| I08 | `I08_vmware_vcenter` | Appel VMware/vCenter simulé | Création VM mock |
| I09 | `I09_ad_ldap` | Appel AD/LDAP simulé | Ajout membre dans groupe mock |
| I10 | `I10_traitement_fichier` | Traitement fichier | Génération et stockage d'un fichier |
| I11 | `I11_multi_zone_reseau` | Traitement multi-zone réseau | Vérification d'accès par zone |
| I12 | `I12_orchestration_longue_polling` | Orchestration longue | Polling jusqu'à fin d'opération |
| I13 | `I13_erreur_fournisseur_temporaire` | Erreur fournisseur temporaire | Retry réussi, statut `WARNING` attendu |
| I14 | `I14_erreur_fonctionnelle_definitive` | Erreur fonctionnelle définitive | Serveur inconnu, échec attendu |
| I15 | `I15_annulation_execution_longue` | Annulation en cours | Arrêt manuel d'une exécution longue |

## Mode opératoire testeur

Le déroulé pas-à-pas pour un testeur non spécialiste Kestra est disponible ici :

```text
docs/test-guides/infrastructure.md
```

## Points de vigilance

- Les cas I03, I04, I05 et I06 couvrent des sujets de worker spécialisé. Le mode mock permet de valider la logique sans cible réelle.
- Pour les tests réels SSH, PowerShell, SCCM et Podman, prévoir les worker groups, secrets et droits nécessaires.
- Les worker groups utilisés dans certains flows sont indicatifs : `windows`, `windows-sccm`, `linux-podman`. Ils doivent exister dans l'instance Kestra Enterprise si les branches réelles sont exécutées.
