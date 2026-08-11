# Mode opératoire testeur — onglet infrastructure

Ce document décrit le mode opératoire détaillé pour exécuter les cas d'usage **I01 à I15** de l'onglet Infrastructure du POC Kestra Enterprise.

Il est rédigé pour un testeur qui n'est pas spécialiste Kestra. L'objectif est de lui permettre d'exécuter chaque scénario, de constater le résultat attendu et de collecter les preuves nécessaires.

## 1. Objectif du guide

Vérifier que Kestra peut orchestrer des actions représentatives d'un remplacement HPOO sur des briques infrastructure :

- appel d'API internes ;
- intégration ITSM ;
- exécution Linux par SSH ;
- exécution Windows par PowerShell ;
- worker Windows SCCM ;
- worker Linux Podman ;
- appel Ansible/AAP ;
- appel VMware/vCenter ;
- appel AD/LDAP ;
- traitement fichier ;
- multi-zone réseau ;
- orchestration longue avec polling ;
- reprise sur erreur temporaire fournisseur ;
- erreur fonctionnelle définitive ;
- annulation d'une exécution longue.

## 2. Pré-requis communs

### 2.1 Accès nécessaires

Le testeur doit disposer :

- d'un accès à l'interface Web Kestra du POC ;
- du droit de consulter le namespace `poc.kestra.infrastructure` ;
- du droit d'exécuter les flows de ce namespace ;
- du droit de consulter les logs, les outputs et le graphe d'exécution ;
- si possible, du droit de stopper une exécution pour le cas I15.

### 2.2 Flows à importer

Les flows suivants doivent être présents dans Kestra :

```text
kestra/flows/infrastructure/*.yml
```

Le namespace attendu est :

```text
poc.kestra.infrastructure
```

### 2.3 API mock

La plupart des cas s'appuient sur l'API mock fournie dans le dépôt.

Lancement local :

```bash
docker compose up -d mock-api
```

URL par défaut depuis les flows :

```text
http://mock-api:8080
```

Si Kestra n'accède pas à ce nom DNS, remplacer l'input `mock_base_url` par l'URL atteignable depuis le worker Kestra.

### 2.4 Worker groups

Certains scénarios référencent des worker groups Kestra Enterprise :

| Worker group | Usage |
|---|---|
| `windows` | Exécution PowerShell réelle |
| `windows-sccm` | Exécution SCCM réelle ou test de routage |
| `linux-podman` | Exécution Podman réelle |

Si ces worker groups n'existent pas dans l'environnement POC, exécuter les scénarios en **mode mock** lorsque le flow le permet.

## 3. Rappel pour exécuter un flow

1. ouvrir Kestra ;
2. aller dans **Flows** ;
3. sélectionner le namespace `poc.kestra.infrastructure` ;
4. ouvrir le flow demandé ;
5. cliquer sur **Execute** ;
6. renseigner les inputs indiqués dans ce guide ;
7. lancer l'exécution ;
8. ouvrir la page d'exécution ;
9. relever l'`execution.id`, le statut final, les logs et les outputs.

## 4. Convention de preuve

Pour chaque cas, collecter au minimum :

- ID du cas d'usage ;
- flow exécuté ;
- execution ID ;
- inputs utilisés ;
- statut final ;
- capture du graphe d'exécution ;
- extrait des logs montrant le résultat attendu ;
- outputs si le flow en produit ;
- commentaire OK / KO.

---
## I01 — Appel API REST interne

### Objectif

Vérifier qu'un flow Kestra peut appeler une API interne, lire un healthcheck et récupérer une liste de serveurs.

### Flow à utiliser

```text
I01_api_rest_interne
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `count` | `3` |

### Étapes

1. ouvrir le flow `I01_api_rest_interne`
2. cliquer sur **Execute**
3. conserver `count=3`
4. adapter `mock_base_url` si nécessaire
5. lancer l'exécution
6. consulter les tâches `verifier_api`, `lister_serveurs` et `compte_rendu`

### Résultat attendu

Le healthcheck doit répondre avec un statut `UP`. La liste de serveurs doit contenir trois entrées issues du mock.

### Preuves à collecter

- statut final en succès
- réponse du healthcheck
- réponse de `lister_serveurs`
- log `compte_rendu`

### Critère OK / KO

Le test est **OK** si les deux appels HTTP réussissent et si la liste de serveurs est visible dans les outputs.

---
## I02 — Intégration ITSM simulée

### Objectif

Vérifier qu'un flow peut créer un changement ITSM simulé en transmettant un identifiant de corrélation.

### Flow à utiliser

```text
I02_itsm_changement_mock
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `correlation_id` | `CHG-DEMO-001` |
| `title` | `POC Kestra - changement infrastructure` |

### Étapes

1. ouvrir le flow `I02_itsm_changement_mock`
2. lancer l'exécution avec les valeurs recommandées
3. ouvrir la tâche `creer_changement`
4. vérifier la réponse HTTP
5. consulter le log `journaliser_changement`

### Résultat attendu

La réponse doit contenir un identifiant de changement de type `CHG-...` et le statut `SCHEDULED`.

### Preuves à collecter

- execution ID
- body de la réponse ITSM mock
- log montrant le changement créé
- correlation_id transmis

### Critère OK / KO

Le test est **OK** si un changement mock est créé et si l'identifiant de corrélation est conservé.

---
## I03 — Exécution SSH Linux

### Objectif

Vérifier le scénario d'exécution Linux distante. Le mode mock valide la logique sans serveur SSH réel ; le mode real teste le plugin SSH et le secret.

### Flow à utiliser

```text
I03_ssh_linux
```

### Pré-requis spécifique

Pour le mode réel, le plugin SSH doit être installé, la cible doit être joignable et le secret `POC_SSH_PRIVATE_KEY` doit être créé.

### Données de test

| Input | Valeur recommandée |
|---|---|
| `execution_mode` | `mock` |
| `host` | `srv-linux-001` |
| `username` | `ansible` |

### Étapes

1. ouvrir le flow `I03_ssh_linux`
2. exécuter une première fois avec `execution_mode=mock`
3. vérifier les logs de la tâche `ssh_mock`
4. si une cible SSH de test existe, relancer avec `execution_mode=real`
5. en mode réel, vérifier que le secret `POC_SSH_PRIVATE_KEY` est configuré
6. consulter les logs de la tâche `ssh_reel`

### Résultat attendu

En mode mock, les logs doivent afficher l'hôte et l'utilisateur. En mode réel, les commandes `hostname` et `uname -a` doivent être exécutées sur la cible.

### Preuves à collecter

- logs du mode mock
- si testé, logs du mode réel
- statut final
- secret non exposé dans les logs

### Critère OK / KO

Le test est **OK** si le mode mock fonctionne ; il est **OK complet** si le mode réel fonctionne aussi.

### Point de vigilance

Ne jamais utiliser une clé SSH personnelle ou de production pour ce test.

---
## I04 — Exécution PowerShell Windows

### Objectif

Vérifier le scénario d'exécution PowerShell. Le mode mock valide le déroulé ; le mode real doit être exécuté sur un worker Windows.

### Flow à utiliser

```text
I04_powershell_windows
```

### Pré-requis spécifique

Pour le mode réel : plugin PowerShell, PowerShell disponible sur le worker, worker group `windows` créé.

### Données de test

| Input | Valeur recommandée |
|---|---|
| `execution_mode` | `mock` |
| `target` | `win-srv-001` |

### Étapes

1. ouvrir le flow `I04_powershell_windows`
2. lancer avec `execution_mode=mock`
3. vérifier les logs `MOCK PowerShell`
4. si le worker group `windows` existe, relancer avec `execution_mode=real`
5. vérifier que la tâche réelle s'exécute sur le worker Windows
6. consulter les logs PowerShell

### Résultat attendu

Le mode mock doit afficher le nom de cible. Le mode réel doit afficher le nom du poste Windows et quelques services.

### Preuves à collecter

- logs PowerShell mock ou réel
- statut final
- worker group utilisé si visible

### Critère OK / KO

Le test est **OK** si le mode mock fonctionne ; il est **OK complet** si la branche réelle fonctionne sur worker Windows.

### Point de vigilance

Ce test ne doit pas être exécuté sur un serveur Windows de production sans validation.

---
## I05 — Worker Windows SCCM

### Objectif

Vérifier le routage prévu vers un worker Windows SCCM et la création d'un déploiement SCCM simulé.

### Flow à utiliser

```text
I05_worker_windows_sccm
```

### Pré-requis spécifique

Le worker group `windows-sccm` doit exister si la validation de routage est bloquante.

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `collection` | `POC-COLLECTION` |
| `package` | `POC-PACKAGE` |

### Étapes

1. vérifier que le worker group `windows-sccm` existe ou décider de traiter le test comme un test de conception
2. ouvrir le flow `I05_worker_windows_sccm`
3. lancer l'exécution
4. ouvrir la tâche `creer_deploiement_sccm_mock`
5. vérifier la réponse du mock SCCM

### Résultat attendu

La réponse doit contenir un identifiant de déploiement `SCCM-...` et le statut `CREATED`.

### Preuves à collecter

- réponse SCCM mock
- statut final
- preuve du worker group si disponible

### Critère OK / KO

Le test est **OK** si le déploiement mock est créé et si le routage worker group est conforme à la conception.

### Point de vigilance

Si le worker group n'existe pas encore, noter le test `OK avec réserve` ou `Non testé` selon la règle de campagne.

---
## I06 — Worker Linux Podman

### Objectif

Vérifier la capacité à exécuter une commande sur worker Linux et, si disponible, à appeler Podman.

### Flow à utiliser

```text
I06_worker_linux_podman
```

### Pré-requis spécifique

Pour le mode réel : Podman installé sur le worker et worker group `linux-podman` disponible.

### Données de test

| Input | Valeur recommandée |
|---|---|
| `image` | `alpine:3.20` |
| `use_podman` | `false` |

### Étapes

1. ouvrir le flow `I06_worker_linux_podman`
2. lancer avec `use_podman=false`
3. vérifier les logs de simulation
4. si Podman est disponible, relancer avec `use_podman=true`
5. vérifier que le worker group `linux-podman` est utilisé
6. consulter les logs de la commande Podman

### Résultat attendu

En mode mock, le flow doit confirmer la simulation. En mode réel, la commande `podman run` doit afficher `podman ok`.

### Preuves à collecter

- logs du mode mock
- logs Podman si testé
- statut final
- worker utilisé si visible

### Critère OK / KO

Le test est **OK** si le mode mock passe ; **OK complet** si Podman réel passe.

---
## I07 — Appel Ansible/AAP

### Objectif

Vérifier qu'un flow peut lancer un job template AAP simulé puis lire son statut.

### Flow à utiliser

```text
I07_ansible_aap
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `template_id` | `42` |
| `inventory` | `poc-inventory` |

### Étapes

1. ouvrir le flow `I07_ansible_aap`
2. lancer avec les valeurs recommandées
3. vérifier la tâche `lancer_job`
4. attendre la tâche `attendre_traitement`
5. vérifier la tâche `lire_statut_job`
6. consulter le compte-rendu

### Résultat attendu

Le job mock doit être lancé avec un identifiant `AAP-...` puis retourner un statut `successful`.

### Preuves à collecter

- body de lancement du job
- body de statut du job
- log final

### Critère OK / KO

Le test est **OK** si le job mock est lancé et si son statut est lu.

---
## I08 — Appel VMware/vCenter simulé

### Objectif

Vérifier qu'un flow peut demander la création d'une VM via une API fournisseur simulée.

### Flow à utiliser

```text
I08_vmware_vcenter
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `vm_name` | `poc-vm-001` |
| `template` | `rhel9-small` |

### Étapes

1. ouvrir le flow `I08_vmware_vcenter`
2. lancer avec les valeurs recommandées
3. ouvrir la tâche `creer_vm_mock`
4. vérifier le body de réponse
5. consulter l'output `vm_response`

### Résultat attendu

La réponse doit contenir un identifiant `VM-...`, le nom de VM demandé et le statut `PROVISIONED`.

### Preuves à collecter

- réponse de création VM
- output `vm_response`
- statut final

### Critère OK / KO

Le test est **OK** si la VM simulée est créée et si les paramètres sont repris correctement.

---
## I09 — Appel AD/LDAP simulé

### Objectif

Vérifier qu'un flow peut demander l'ajout d'un utilisateur dans un groupe AD simulé.

### Flow à utiliser

```text
I09_ad_ldap
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `group` | `GG-POC-Kestra-Test` |
| `user` | `user.demo` |

### Étapes

1. ouvrir le flow `I09_ad_ldap`
2. lancer avec les valeurs recommandées
3. ouvrir la tâche `ajouter_membre`
4. vérifier la réponse
5. consulter l'output `ad_response`

### Résultat attendu

La réponse doit indiquer le groupe, l'utilisateur et le statut `ADDED`.

### Preuves à collecter

- réponse AD mock
- output `ad_response`
- statut final

### Critère OK / KO

Le test est **OK** si l'ajout mock est tracé avec le bon utilisateur et le bon groupe.

---
## I10 — Traitement fichier

### Objectif

Vérifier qu'un flow peut générer un fichier, le stocker dans le stockage interne Kestra et en mesurer la taille.

### Flow à utiliser

```text
I10_traitement_fichier
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `server` | `srv-001` |

### Étapes

1. ouvrir le flow `I10_traitement_fichier`
2. lancer avec `server=srv-001`
3. ouvrir les outputs de `generer_fichier`
4. repérer `inventory.txt`
5. vérifier la tâche `mesurer_fichier`
6. consulter le log de compte-rendu

### Résultat attendu

Le fichier `inventory.txt` doit être produit. Sa taille doit être supérieure à zéro et son URI doit être visible.

### Preuves à collecter

- URI du fichier
- taille du fichier
- extrait du fichier si consultable
- statut final

### Critère OK / KO

Le test est **OK** si le fichier est généré, stocké et mesuré.

---
## I11 — Traitement multi-zone réseau

### Objectif

Vérifier que le flow permet de tester les accès par zone réseau et de distinguer les zones autorisées/interdites.

### Flow à utiliser

```text
I11_multi_zone_reseau
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `zone` | `outils puis interdite` |

### Étapes

1. ouvrir le flow `I11_multi_zone_reseau`
2. lancer une première fois avec `zone=outils`
3. constater un retour autorisé
4. relancer avec `zone=interdite`
5. constater le code 403 ou la réponse d'interdiction
6. collecter les deux résultats

### Résultat attendu

`zone=outils` doit retourner une réponse autorisée. `zone=interdite` doit retourner une interdiction, sans empêcher la collecte de la réponse grâce à `allowFailed=true`.

### Preuves à collecter

- résultat zone autorisée
- résultat zone interdite
- code HTTP observé
- log `evaluer_reponse`

### Critère OK / KO

Le test est **OK** si les deux situations sont distinguées clairement.

---
## I12 — Orchestration longue avec polling

### Objectif

Vérifier qu'un flow peut créer une opération longue et interroger régulièrement son statut.

### Flow à utiliser

```text
I12_orchestration_longue_polling
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `resource` | `long-op-001` |

### Étapes

1. ouvrir le flow `I12_orchestration_longue_polling`
2. lancer avec les valeurs recommandées
3. vérifier la création de l'opération
4. suivre les trois itérations de polling
5. consulter les logs `log_statut`
6. vérifier le compte-rendu final

### Résultat attendu

Le mock doit retourner une opération `OP-...`. Après plusieurs lectures, le statut doit passer à `DONE`.

### Preuves à collecter

- identifiant d'opération
- logs de polling
- statut final
- durée approximative

### Critère OK / KO

Le test est **OK** si le polling est visible et si le statut final `DONE` est observé.

---
## I13 — Erreur fournisseur temporaire

### Objectif

Vérifier qu'un flow sait rejouer automatiquement un appel fournisseur temporairement indisponible.

### Flow à utiliser

```text
I13_erreur_fournisseur_temporaire
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `key` | `infra-provider-demo` |

### Étapes

1. ouvrir le flow `I13_erreur_fournisseur_temporaire`
2. lancer avec les valeurs recommandées
3. observer les premières tentatives en erreur HTTP 503
4. attendre les retries
5. vérifier le succès final
6. consulter le log final

### Résultat attendu

Le mock échoue temporairement puis réussit. Le flow doit finir en succès après retry.

### Preuves à collecter

- nombre de tentatives
- logs de retry
- réponse finale
- statut final

### Critère OK / KO

Le test est **OK** si les retries sont visibles et si l'exécution finit en succès.

---
## I14 — Erreur fonctionnelle définitive

### Objectif

Vérifier qu'une erreur fonctionnelle non récupérable est clairement tracée.

### Flow à utiliser

```text
I14_erreur_fonctionnelle_definitive
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` |
| `server` | `srv-inconnu` |

### Étapes

1. ouvrir le flow `I14_erreur_fonctionnelle_definitive`
2. lancer avec `server=srv-inconnu`
3. constater l'échec de `rechercher_serveur`
4. ouvrir la branche `errors`
5. vérifier le message fonctionnel

### Résultat attendu

Le serveur inconnu doit générer un échec. La branche d'erreur doit écrire que le serveur est introuvable ou non éligible.

### Preuves à collecter

- statut final en erreur attendue
- message HTTP 404
- log d'erreur fonctionnelle
- inputs utilisés

### Critère OK / KO

Le test est **OK** si l'erreur est explicite et qualifiée comme fonctionnelle.

### Point de vigilance

Ce cas doit être noté OK même si le statut final est en erreur, car l'erreur est attendue.

---
## I15 — Annulation d'une exécution longue

### Objectif

Vérifier qu'un testeur peut arrêter une exécution longue et retrouver les traces nécessaires.

### Flow à utiliser

```text
I15_annulation_execution_longue
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `duree_secondes` | `120` |

### Étapes

1. ouvrir le flow `I15_annulation_execution_longue`
2. lancer avec `duree_secondes=120`
3. attendre que la tâche `traitement_long` démarre
4. depuis la page d'exécution, utiliser l'action d'arrêt/kill/cancel disponible dans l'interface
5. confirmer l'arrêt si demandé
6. consulter le statut final et les logs

### Résultat attendu

L'exécution doit être arrêtée manuellement avant les 120 secondes. La page d'exécution doit permettre d'identifier l'arrêt et les traces associées.

### Preuves à collecter

- statut après arrêt
- heure de début et d'arrêt
- logs avant arrêt
- preuve de l'action d'annulation

### Critère OK / KO

Le test est **OK** si l'exécution peut être arrêtée et si l'état final est compréhensible par le testeur.

### Point de vigilance

Ne pas lancer ce test avec une durée très longue sans accord de l'administrateur POC.

---

## Synthèse de fin de campagne infrastructure

À la fin des tests I01 à I15, compléter le tableau suivant dans le compte-rendu de POC.

| ID | Statut | Execution ID | Preuve collectée | Commentaire |
|---|---|---|---|---|
| I01 |  |  |  |  |
| I02 |  |  |  |  |
| I03 |  |  |  |  |
| I04 |  |  |  |  |
| I05 |  |  |  |  |
| I06 |  |  |  |  |
| I07 |  |  |  |  |
| I08 |  |  |  |  |
| I09 |  |  |  |  |
| I10 |  |  |  |  |
| I11 |  |  |  |  |
| I12 |  |  |  |  |
| I13 |  |  |  |  |
| I14 |  |  |  |  |
| I15 |  |  |  |  |

## Anomalies à remonter

Pour toute anomalie, relever :

- l'ID du use case ;
- le flow exécuté ;
- l'execution ID ;
- l'heure de début et de fin ;
- les inputs utilisés ;
- le statut final ;
- le message d'erreur ;
- une capture des logs ;
- le worker concerné si visible ;
- le comportement attendu ;
- le comportement observé.
