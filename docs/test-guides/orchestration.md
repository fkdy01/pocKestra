# Mode opératoire testeur — onglet orchestration

Ce document décrit le mode opératoire détaillé pour exécuter les cas d'usage **F01 à F20** de l'onglet orchestration du POC Kestra Enterprise.

Il est rédigé pour un testeur qui n'est pas spécialiste Kestra. Les termes Kestra utilisés sont limités au strict nécessaire.

## 1. Objectif du guide

L'objectif est de vérifier que Kestra couvre les principaux comportements d'orchestration attendus en remplacement d'HPOO :

- enchaînement de tâches ;
- saisie et validation de paramètres ;
- conditions et routage ;
- boucles ;
- parallélisation ;
- sous-flows ;
- reprises sur erreur ;
- retries ;
- timeouts ;
- pauses humaines ;
- déclenchement planifié ou par API ;
- idempotence ;
- compensation ;
- corrélation métier ;
- secrets ;
- gros outputs et logs.

Chaque cas doit être exécuté, observé et documenté avec une preuve.

## 2. Pré-requis communs

### 2.1 Accès nécessaires

Le testeur doit disposer :

- d'un accès à l'interface Web Kestra du POC ;
- du droit de consulter le namespace `poc.kestra.orchestration` ;
- du droit d'exécuter les flows de ce namespace ;
- du droit de consulter les logs et outputs d'exécution ;
- si possible, du droit de relancer une exécution avec de nouveaux paramètres.

### 2.2 Flows à importer

Les flows suivants doivent être présents dans Kestra :

```text
kestra/flows/orchestration/*.yml
kestra/flows/orchestration/common/*.yml
```

Le namespace attendu est :

```text
poc.kestra.orchestration
```

### 2.3 API mock

Certains cas utilisent une API de test locale :

- F15 — appel API / événement ;
- F18 — corrélation métier avec création de ticket mock.

Si le POC utilise le `docker-compose.yml` fourni dans le dépôt, lancer le mock avec :

```bash
docker compose up -d mock-api
```

URL par défaut depuis les flows :

```text
http://mock-api:8080
```

Si Kestra n'accède pas à ce nom DNS, remplacer l'input `mock_base_url` par l'URL atteignable depuis le worker Kestra, par exemple :

```text
http://<adresse-du-mock>:8080
```

### 2.4 Vérification préalable côté Kestra

Avant de commencer les tests :

1. ouvrir l'interface Kestra ;
2. aller dans **Flows** ;
3. sélectionner ou rechercher le namespace `poc.kestra.orchestration` ;
4. vérifier que les flows F01 à F20 sont visibles ;
5. vérifier que les sous-flows suivants sont visibles :
   - `common_controle_serveur` ;
   - `common_operation_fragile` ;
   - `common_compensation`.

### 2.5 Comment exécuter un flow dans l'interface

Pour chaque cas :

1. aller dans **Flows** ;
2. rechercher le flow par son identifiant, par exemple `F01_sequence_simple` ;
3. ouvrir le flow ;
4. cliquer sur **Execute** ;
5. saisir les inputs indiqués dans ce guide ;
6. lancer l'exécution ;
7. ouvrir la page de l'exécution ;
8. relever :
   - le statut final ;
   - les tâches exécutées ;
   - les logs ;
   - les outputs lorsque présents ;
   - l'identifiant d'exécution.

Les libellés exacts peuvent varier selon la version de Kestra, mais les actions attendues restent : ouvrir le flow, exécuter, consulter l'exécution, logs et outputs.

### 2.6 Convention de résultat

| Résultat | Signification |
|---|---|
| OK | Le comportement attendu est obtenu. |
| OK avec réserve | Le comportement est obtenu mais une limite est notée. |
| KO | Le comportement attendu n'est pas obtenu. |
| Non testé | Le test n'a pas été exécuté. |

---

## F01 — Flow séquentiel simple

### Objectif

Vérifier qu'un flow Kestra peut exécuter plusieurs tâches dans l'ordre, produire des logs et exposer un output final.

### Flow à utiliser

```text
F01_sequence_simple
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `demande_id` | `DEMO-001` |

### Étapes

1. ouvrir le flow `F01_sequence_simple` ;
2. cliquer sur **Execute** ;
3. conserver la valeur `DEMO-001` pour `demande_id` ;
4. lancer l'exécution ;
5. attendre la fin de l'exécution ;
6. ouvrir les logs ;
7. ouvrir les outputs de l'exécution.

### Résultat attendu

Le flow doit se terminer en succès. Les tâches suivantes doivent apparaître comme exécutées :

1. `reception` ;
2. `traitement` ;
3. `compte_rendu`.

Les logs doivent montrer :

```text
Réception de la demande DEMO-001
Compte-rendu = Traitement terminé pour DEMO-001
```

L'output `resultat` doit contenir :

```text
Traitement terminé pour DEMO-001
```

### Preuves à collecter

- capture du statut final en succès ;
- capture ou extrait des logs ;
- capture de l'output `resultat`.

### Critère OK / KO

Le test est **OK** si les trois tâches sont exécutées dans l'ordre, si le statut final est en succès et si l'output `resultat` est visible.

---

## F02 — Paramètres obligatoires, facultatifs et validation simple

### Objectif

Vérifier la saisie d'inputs obligatoires/facultatifs et le comportement différent selon les paramètres.

### Flow à utiliser

```text
F02_parametres_validation
```

### Données de test nominales

| Input | Valeur |
|---|---|
| `serveur` | `srv-test-001` |
| `environnement` | `dev` |
| `dry_run` | `true` |

### Données de test de protection production

| Input | Valeur |
|---|---|
| `serveur` | `srv-prod-001` |
| `environnement` | `prod` |
| `dry_run` | `false` |

### Étapes — test nominal

1. ouvrir le flow `F02_parametres_validation` ;
2. cliquer sur **Execute** ;
3. renseigner `serveur=srv-test-001` ;
4. sélectionner `environnement=dev` ;
5. conserver `dry_run=true` ;
6. lancer l'exécution ;
7. consulter les logs.

### Résultat attendu — test nominal

Le flow doit se terminer en succès. Le log doit indiquer :

```text
Exécution autorisée.
```

Le contexte affiché doit contenir :

```text
serveur=srv-test-001, environnement=dev, dry_run=true
```

### Étapes — test protection production

1. relancer le flow ;
2. renseigner `serveur=srv-prod-001` ;
3. sélectionner `environnement=prod` ;
4. sélectionner `dry_run=false` ;
5. lancer l'exécution ;
6. consulter les logs.

### Résultat attendu — test protection production

Le flow doit se terminer en succès mais suivre la branche de protection production. Le log doit indiquer :

```text
Action réelle en production : validation externe requise.
```

### Preuves à collecter

- une preuve pour le scénario nominal ;
- une preuve pour le scénario production ;
- les inputs utilisés pour chaque exécution.

### Critère OK / KO

Le test est **OK** si les deux scénarios exécutent des branches différentes selon les paramètres.

---

## F03 — Conditions if/else et routage switch

### Objectif

Vérifier qu'un flow peut prendre une décision selon un booléen puis router le traitement selon une action.

### Flow à utiliser

```text
F03_conditions_switch
```

### Jeux de données

| Scénario | `urgent` | `action` | Logs attendus |
|---|---:|---|---|
| Normal démarrage | `false` | `start` | `Traitement normal` puis `Démarrage demandé` |
| Urgent arrêt | `true` | `stop` | `Traitement prioritaire activé` puis `Arrêt demandé` |
| Normal statut | `false` | `status` | `Traitement normal` puis `Statut demandé` |

### Étapes

Pour chaque scénario du tableau :

1. ouvrir le flow `F03_conditions_switch` ;
2. cliquer sur **Execute** ;
3. saisir les valeurs `urgent` et `action` ;
4. lancer l'exécution ;
5. consulter les logs ;
6. noter quelle branche a été exécutée.

### Résultat attendu

Chaque combinaison doit produire les deux logs attendus :

- un log de priorité ;
- un log d'action.

### Preuves à collecter

- une preuve par scénario ;
- capture des logs montrant la branche exécutée ;
- statut final en succès.

### Critère OK / KO

Le test est **OK** si les trois scénarios routent vers la bonne branche.

---

## F04 — Boucle sur une liste de serveurs

### Objectif

Vérifier que Kestra peut répéter une action pour chaque élément d'une liste.

### Flow à utiliser

```text
F04_boucle_liste_serveurs
```

### Données de test

| Input | Valeur |
|---|---|
| `serveurs` | `srv-001`, `srv-002`, `srv-003` |

### Étapes

1. ouvrir le flow `F04_boucle_liste_serveurs` ;
2. cliquer sur **Execute** ;
3. conserver la liste par défaut ou saisir une liste de trois serveurs ;
4. lancer l'exécution ;
5. consulter les logs de la tâche `journaliser_serveur`.

### Résultat attendu

Le flow doit se terminer en succès. Les logs doivent contenir une ligne par serveur, par exemple :

```text
Traitement du serveur srv-001
Traitement du serveur srv-002
Traitement du serveur srv-003
```

### Preuves à collecter

- statut final ;
- logs montrant les trois itérations ;
- nombre d'itérations constaté.

### Critère OK / KO

Le test est **OK** si chaque serveur de la liste est traité exactement une fois.

---

## F05 — Parallélisation contrôlée

### Objectif

Vérifier que Kestra peut traiter une liste en parallèle tout en limitant la concurrence.

### Flow à utiliser

```text
F05_parallelisation
```

### Données de test

| Input | Valeur |
|---|---|
| `serveurs` | `srv-001`, `srv-002`, `srv-003`, `srv-004` |
La limite de concurrence est fixée à `2` dans le flow, car Kestra 1.3 attend un
entier statique pour `concurrencyLimit`.

### Étapes

1. ouvrir le flow `F05_parallelisation` ;
2. cliquer sur **Execute** ;
3. conserver la liste par défaut ;
4. vérifier que `concurrencyLimit` vaut `2` dans la source du flow ;
5. lancer l'exécution ;
6. consulter les tâches enfants de `traitements_paralleles` ;
7. vérifier les logs `Début` et `Fin` de chaque serveur.

### Résultat attendu

Le flow doit se terminer en succès. Quatre serveurs doivent être traités. La concurrence doit être limitée à deux traitements simultanés.

### Preuves à collecter

- statut final ;
- logs `Début` / `Fin` ;
- vue des tâches ou chronologie montrant plusieurs traitements et la limite de concurrence.

### Critère OK / KO

Le test est **OK** si les quatre serveurs sont traités et si l'exécution respecte la limite de concurrence configurée.

### Point de vigilance

Ce cas utilise une tâche Shell avec le runner `Process`. Le worker qui exécute le test doit donc autoriser ce type de tâche.

---

## F06 — Subflow avec paramètres et retour de résultat

### Objectif

Vérifier qu'un flow parent peut appeler un sous-flow, lui transmettre un paramètre et récupérer un output.

### Flows à utiliser

```text
F06_subflow_parametres_retour
common_controle_serveur
```

### Données de test

| Input | Valeur |
|---|---|
| `serveur` | `srv-001` |

### Étapes

1. vérifier que le sous-flow `common_controle_serveur` est bien importé ;
2. ouvrir le flow parent `F06_subflow_parametres_retour` ;
3. cliquer sur **Execute** ;
4. saisir `serveur=srv-001` ;
5. lancer l'exécution ;
6. ouvrir les logs du flow parent ;
7. ouvrir l'exécution du sous-flow si l'interface le permet.

### Résultat attendu

Le flow parent doit se terminer en succès. Le log parent doit afficher un résultat de sous-flow, par exemple :

```text
Résultat subflow = serveur=srv-001 statut=OK
```

### Preuves à collecter

- statut du flow parent ;
- statut du sous-flow ;
- log montrant le résultat renvoyé par le sous-flow.

### Critère OK / KO

Le test est **OK** si le sous-flow est appelé, si le parent attend sa fin et si le résultat est exploité par le parent.

---

## F07 — Subflow en erreur et reprise contrôlée

### Objectif

Vérifier le comportement d'un flow parent lorsqu'un sous-flow échoue, puis vérifier la reprise avec un paramètre corrigé.

### Flows à utiliser

```text
F07_subflow_erreur_reprise
common_operation_fragile
```

### Scénario 1 — échec attendu

| Input | Valeur |
|---|---|
| `provoquer_erreur` | `true` |

### Étapes — échec attendu

1. vérifier que le sous-flow `common_operation_fragile` est importé ;
2. ouvrir le flow `F07_subflow_erreur_reprise` ;
3. cliquer sur **Execute** ;
4. conserver `provoquer_erreur=true` ;
5. lancer l'exécution ;
6. attendre l'échec ;
7. consulter les logs.

### Résultat attendu — échec attendu

L'exécution doit finir en erreur. La branche `errors` doit écrire :

```text
Le subflow a échoué ; rejouer avec provoquer_erreur=false.
```

### Scénario 2 — reprise avec correction

| Input | Valeur |
|---|---|
| `provoquer_erreur` | `false` |

### Étapes — reprise

1. relancer le même flow avec `provoquer_erreur=false` ;
2. vérifier que l'exécution se termine en succès ;
3. consulter le statut du sous-flow.

### Résultat attendu — reprise

Le flow parent et le sous-flow doivent se terminer en succès.

### Preuves à collecter

- preuve de l'échec volontaire ;
- preuve de la reprise réussie ;
- logs de la branche d'erreur ;
- identifiants des deux exécutions.

### Critère OK / KO

Le test est **OK** si l'échec est clairement visible et si la correction du paramètre permet une exécution réussie.

---

## F08 — Retry avec backoff constant

### Objectif

Vérifier qu'une tâche en erreur temporaire est automatiquement réessayée puis réussit.

### Flow à utiliser

```text
F08_retry_backoff
```

### Données de test

Aucun input n'est nécessaire.

### Étapes

1. ouvrir le flow `F08_retry_backoff` ;
2. cliquer sur **Execute** ;
3. lancer l'exécution ;
4. consulter les tentatives de la tâche `api_temporairement_indisponible` ;
5. consulter les logs.

### Résultat attendu

La tâche doit échouer au début puis réussir après retry. Les logs doivent contenir :

```text
échec temporaire
succès après retry
```

La configuration attendue est :

```text
maxAttempts: 4
interval: PT2S
```

### Preuves à collecter

- nombre de tentatives constatées ;
- logs montrant l'échec puis le succès ;
- statut final `WARNING`, qui indique ici un succès après retry.

### Critère OK / KO

Le test est **OK** si le retry est visible, si la tâche finit en succès sans
relance manuelle et si l'exécution termine en `WARNING`. Ce statut est attendu
car le flow utilise `warningOnRetry: true` pour rendre le retry visible.

---

## F09 — Timeout de tâche longue

### Objectif

Vérifier qu'une tâche trop longue est interrompue par timeout et que la branche d'erreur globale est exécutée.

### Flow à utiliser

```text
F09_timeout_tache_longue
```

### Données de test

| Input | Valeur |
|---|---|
| `duree_secondes` | `10` |

### Étapes

1. ouvrir le flow `F09_timeout_tache_longue` ;
2. cliquer sur **Execute** ;
3. conserver `duree_secondes=10` ;
4. lancer l'exécution ;
5. attendre le timeout ;
6. consulter les logs.

### Résultat attendu

La tâche `tache_trop_longue` doit dépasser son timeout de 5 secondes. La branche `errors` doit écrire :

```text
Erreur attendue : timeout.
```

Le statut final peut être en erreur, ce qui est attendu pour ce scénario.

### Preuves à collecter

- statut final ;
- durée approximative avant échec ;
- log de la branche d'erreur ;
- capture de la tâche en timeout.

### Critère OK / KO

Le test est **OK** si la tâche est interrompue automatiquement et si le message d'erreur attendu est visible.

---

## F10 — Gestion d'erreur locale non bloquante

### Objectif

Vérifier qu'une erreur locale peut être acceptée sans faire échouer l'ensemble du flow.

### Flow à utiliser

```text
F10_gestion_erreur_locale
```

### Données de test

Aucun input n'est nécessaire.

### Étapes

1. ouvrir le flow `F10_gestion_erreur_locale` ;
2. cliquer sur **Execute** ;
3. lancer l'exécution ;
4. consulter la tâche `branche_non_bloquante` ;
5. vérifier que le flow continue jusqu'à la tâche `poursuivre`.

### Résultat attendu

La tâche `controle_optionnel` échoue volontairement. Le flow doit continuer et exécuter le log :

```text
Le flow continue malgré l'erreur locale contrôlée.
```

Selon l'affichage de Kestra, la tâche interne peut apparaître en erreur contrôlée, mais le flow global doit démontrer la poursuite du traitement.

### Preuves à collecter

- capture de l'erreur locale ;
- capture de la tâche `poursuivre` exécutée ;
- statut final ou état global de l'exécution ;
- log de poursuite.

### Critère OK / KO

Le test est **OK** si l'erreur locale ne bloque pas la suite du flow.

---

## F11 — Gestion d'erreur globale

### Objectif

Vérifier qu'une erreur critique déclenche la section globale `errors` du flow.

### Flow à utiliser

```text
F11_gestion_erreur_globale
```

### Données de test

Aucun input n'est nécessaire.

### Étapes

1. ouvrir le flow `F11_gestion_erreur_globale` ;
2. cliquer sur **Execute** ;
3. lancer l'exécution ;
4. attendre l'échec de la tâche `action_critique` ;
5. consulter les logs de la tâche `creer_alerte`.

### Résultat attendu

La tâche `action_critique` échoue volontairement avec :

```text
Erreur critique simulée
```

La branche d'erreur globale doit écrire :

```text
Alerte globale : flow=F11_gestion_erreur_globale, execution=<execution_id>
```

Le statut final en erreur est attendu.

### Preuves à collecter

- statut final en erreur ;
- message d'erreur critique ;
- message d'alerte globale ;
- identifiant d'exécution.

### Critère OK / KO

Le test est **OK** si l'échec critique déclenche bien la branche `errors`.

---

## F12 — Reprise manuelle après correction d'un paramètre

### Objectif

Vérifier qu'un flow peut échouer à cause d'un paramètre, puis réussir après correction et relance.

### Flow à utiliser

```text
F12_reprise_manuelle
```

### Scénario 1 — échec attendu

| Input | Valeur |
|---|---|
| `code_validation` | `KO` |

### Étapes — échec

1. ouvrir le flow `F12_reprise_manuelle` ;
2. cliquer sur **Execute** ;
3. conserver `code_validation=KO` ;
4. lancer l'exécution ;
5. constater l'échec.

### Résultat attendu — échec

L'exécution doit échouer avec le message :

```text
Mettre code_validation=OK puis rejouer.
```

### Scénario 2 — relance corrigée

| Input | Valeur |
|---|---|
| `code_validation` | `OK` |

### Étapes — relance

1. relancer le flow ;
2. saisir `code_validation=OK` ;
3. lancer l'exécution ;
4. consulter les logs.

### Résultat attendu — relance

Le flow doit se terminer en succès avec :

```text
Paramètre corrigé, reprise possible.
```

### Preuves à collecter

- identifiant de l'exécution KO ;
- identifiant de l'exécution OK ;
- messages de log des deux exécutions.

### Critère OK / KO

Le test est **OK** si l'erreur fonctionnelle est reproductible et si la correction du paramètre permet la réussite.

---

## F13 — Pause et approbation humaine

### Objectif

Vérifier qu'une exécution peut être mise en pause puis reprise manuellement.

### Flow à utiliser

```text
F13_pause_approbation_humaine
```

### Données de test

Aucun input n'est nécessaire.

### Étapes

1. ouvrir le flow `F13_pause_approbation_humaine` ;
2. cliquer sur **Execute** ;
3. lancer l'exécution ;
4. vérifier que la tâche `preparation` s'exécute ;
5. vérifier que l'exécution s'arrête sur la tâche `attente_approbation` ;
6. relever l'état de pause ;
7. reprendre l'exécution depuis l'interface Kestra ;
8. vérifier que la tâche `execution_apres_approbation` s'exécute.

### Résultat attendu

Avant reprise, le log doit contenir :

```text
Préparation terminée : attendre approbation exploitant.
```

Après reprise, le log doit contenir :

```text
Exécution reprise après approbation.
```

### Preuves à collecter

- capture de l'exécution en pause ;
- capture de l'action de reprise ou de l'état repris ;
- log avant pause ;
- log après reprise.

### Critère OK / KO

Le test est **OK** si l'exécution reste suspendue jusqu'à l'action humaine puis se termine après reprise.

---

## F14 — Exécution programmée

### Objectif

Vérifier que le scheduler Kestra déclenche automatiquement un flow selon une planification.

### Flow à utiliser

```text
F14_execution_programmee
```

### Données de test

Aucun input n'est nécessaire.

Le trigger planifié est :

```text
*/15 * * * *
```

### Étapes

1. vérifier que le flow `F14_execution_programmee` est importé ;
2. vérifier que son trigger `toutes_les_15_minutes` est actif ;
3. attendre le prochain créneau de 15 minutes ;
4. consulter la liste des exécutions du flow ;
5. ouvrir l'exécution déclenchée automatiquement ;
6. consulter les logs.

### Résultat attendu

Une exécution doit être créée automatiquement par le scheduler. Le log doit contenir :

```text
Déclenchement planifié execution=<execution_id> date=<trigger.date>
```

### Preuves à collecter

- capture du trigger actif ;
- capture de l'exécution déclenchée automatiquement ;
- log contenant `trigger.date`.

### Critère OK / KO

Le test est **OK** si une exécution est créée sans action manuelle au créneau attendu.

### Point de vigilance

Le test dépend de l'activation effective du scheduler dans l'environnement POC.

---

## F15 — Exécution API / événementielle avec appel mock

### Objectif

Vérifier qu'un flow peut être exécuté par action externe et appeler une API mock avec un identifiant de corrélation.

### Flow à utiliser

```text
F15_execution_api_evenementielle
```

### Pré-requis spécifique

L'API mock doit être accessible depuis le worker Kestra.

Tester depuis un environnement qui voit le mock :

```bash
curl http://<mock_base_url>/health
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `mock_base_url` | `http://mock-api:8080` ou URL adaptée |
| `correlation_id` | `DEMO-CORR-001` |

### Étapes — exécution depuis l'interface

1. ouvrir le flow `F15_execution_api_evenementielle` ;
2. cliquer sur **Execute** ;
3. renseigner `mock_base_url` si nécessaire ;
4. renseigner `correlation_id=DEMO-CORR-001` ;
5. lancer l'exécution ;
6. consulter les logs et la réponse de la tâche `notifier_mock`.

### Étapes — exécution par API Kestra si disponible

Si l'équipe POC veut tester le déclenchement externe, exécuter le flow via l'API Kestra avec les mêmes inputs. L'URL exacte dépend de l'installation Kestra et du mode d'authentification. Le testeur doit demander à l'administrateur Kestra l'URL d'API et le token de test.

### Résultat attendu

La tâche `notifier_mock` doit appeler :

```text
POST <mock_base_url>/echo
```

Le log doit contenir une réponse mock, par exemple :

```text
Réponse mock=...
```

La réponse doit reprendre la source `kestra`, l'exécution et le use case `F15`.

### Preuves à collecter

- statut final en succès ;
- input `correlation_id` ;
- réponse HTTP du mock ;
- log `Réponse mock=...`.

### Critère OK / KO

Le test est **OK** si le flow appelle l'API mock et si la réponse est visible dans les logs.

---

## F16 — Idempotence

### Objectif

Vérifier qu'une même demande produit une clé d'idempotence stable, permettant d'éviter un double effet de bord.

### Flow à utiliser

```text
F16_idempotence
```

### Données de test

| Input | Valeur |
|---|---|
| `demande_id` | `DEMO-001` |

### Étapes

1. ouvrir le flow `F16_idempotence` ;
2. exécuter une première fois avec `demande_id=DEMO-001` ;
3. relever l'output `idempotency_key` ;
4. exécuter une seconde fois avec la même valeur ;
5. relever le nouvel output `idempotency_key` ;
6. comparer les deux valeurs.

### Résultat attendu

Les deux exécutions doivent produire la même clé :

```text
F16_idempotence:DEMO-001
```

### Preuves à collecter

- identifiant de la première exécution ;
- identifiant de la seconde exécution ;
- output `idempotency_key` des deux exécutions ;
- comparaison des deux valeurs.

### Critère OK / KO

Le test est **OK** si la clé d'idempotence est identique pour la même demande.

### Point de vigilance

Ce test démontre le principe d'idempotence. En production, la clé doit ensuite être utilisée pour vérifier l'état réel dans un référentiel ou une API cible.

---

## F17 — Compensation après erreur

### Objectif

Vérifier qu'une action de compensation est déclenchée lorsqu'un flow échoue après une réussite partielle.

### Flows à utiliser

```text
F17_compensation
common_compensation
```

### Scénario 1 — compensation attendue

| Input | Valeur |
|---|---|
| `provoquer_erreur_finale` | `true` |

### Étapes — compensation attendue

1. vérifier que le sous-flow `common_compensation` est importé ;
2. ouvrir le flow `F17_compensation` ;
3. cliquer sur **Execute** ;
4. conserver `provoquer_erreur_finale=true` ;
5. lancer l'exécution ;
6. constater l'échec de la tâche finale ;
7. vérifier que le sous-flow `common_compensation` est appelé.

### Résultat attendu — compensation

Le flow réserve d'abord une ressource avec un identifiant de type :

```text
RES-<execution_id>
```

Puis la tâche finale échoue. La branche `errors` doit appeler le sous-flow `common_compensation` avec l'identifiant de ressource.

### Scénario 2 — succès sans compensation

| Input | Valeur |
|---|---|
| `provoquer_erreur_finale` | `false` |

### Étapes — succès

1. relancer le flow avec `provoquer_erreur_finale=false` ;
2. vérifier que le flow se termine en succès ;
3. vérifier que le sous-flow de compensation n'est pas appelé.

### Preuves à collecter

- exécution avec compensation ;
- identifiant de ressource réservé ;
- appel du sous-flow `common_compensation` ;
- exécution sans compensation.

### Critère OK / KO

Le test est **OK** si la compensation est déclenchée uniquement en cas d'échec après réservation.

---

## F18 — Corrélation métier

### Objectif

Vérifier qu'un identifiant métier est propagé dans les labels, les logs, les outputs et l'appel API mock.

### Flow à utiliser

```text
F18_correlation_metier
```

### Pré-requis spécifique

L'API mock doit être accessible depuis le worker Kestra.

### Données de test

| Input | Valeur |
|---|---|
| `correlation_id` | `SUB-48972` |
| `mock_base_url` | `http://mock-api:8080` ou URL adaptée |

### Étapes

1. ouvrir le flow `F18_correlation_metier` ;
2. cliquer sur **Execute** ;
3. renseigner `correlation_id=SUB-48972` ;
4. renseigner `mock_base_url` si nécessaire ;
5. lancer l'exécution ;
6. vérifier les labels de l'exécution ;
7. consulter les logs ;
8. consulter les outputs.

### Résultat attendu

L'exécution doit porter les labels :

```text
correlation_id=SUB-48972
usecase=F18
```

Le flow doit appeler :

```text
POST <mock_base_url>/tickets
```

Le log doit contenir :

```text
correlation_id=SUB-48972
```

L'output `correlation_id` doit valoir :

```text
SUB-48972
```

### Preuves à collecter

- capture des labels de l'exécution ;
- réponse de l'API mock de création de ticket ;
- log contenant `correlation_id=SUB-48972` ;
- output `correlation_id`.

### Critère OK / KO

Le test est **OK** si le même identifiant métier est retrouvé dans les labels, les logs, les outputs et l'appel mock.

---

## F19 — Référence à un secret

### Objectif

Vérifier qu'un flow peut référencer un secret sans stocker sa valeur en clair dans Git.

### Flow à utiliser

```text
F19_secrets
```

### Pré-requis spécifique

Le test peut être exécuté sans créer le secret `POC_API_TOKEN`. Dans ce cas, le flow utilise la valeur de démonstration :

```text
SECRET_NON_CONFIGURE
```

Ne pas utiliser de vrai secret de production pour ce test.

### Données de test

| Input | Valeur |
|---|---|
| `endpoint` | `https://example.invalid/api` |

### Étapes

1. ouvrir le fichier du flow dans le dépôt Git ;
2. vérifier que la valeur du secret n'est pas présente en clair ;
3. vérifier que le flow utilise une référence de type `secret('POC_API_TOKEN')` ;
4. ouvrir le flow `F19_secrets` dans Kestra ;
5. exécuter le flow sans créer de vrai secret de production ;
6. consulter les logs ;
7. vérifier qu'aucune valeur sensible réelle n'est collectée dans les preuves.

### Résultat attendu

Le dépôt Git ne doit contenir aucune valeur de secret. Le flow doit contenir uniquement une référence :

```text
secret('POC_API_TOKEN')
```

Le log de consigne doit indiquer :

```text
Vérifier que le secret POC_API_TOKEN n'est jamais stocké en clair dans le flow.
```

### Preuves à collecter

- capture du flow montrant la référence `secret('POC_API_TOKEN')` ;
- capture du log de consigne ;
- mention explicite que le test n'a pas utilisé de secret réel.

### Critère OK / KO

Le test est **OK** si aucun secret réel n'est présent dans Git ni dans les preuves de test.

### Point de vigilance sécurité

Le flow de démonstration construit un en-tête d'autorisation pour montrer la référence au secret. Dans un flow de production, ne jamais afficher ou retourner la valeur d'un secret dans un output, un log ou une tâche de debug.

---

## F20 — Gros outputs et logs

### Objectif

Vérifier que Kestra sait produire un fichier de sortie volumineux, le stocker et en mesurer la taille.

### Flow à utiliser

```text
F20_gros_outputs_logs
```

### Données de test

| Input | Valeur recommandée |
|---|---|
| `lignes` | `1000` |

### Étapes

1. ouvrir le flow `F20_gros_outputs_logs` ;
2. cliquer sur **Execute** ;
3. conserver `lignes=1000` ;
4. lancer l'exécution ;
5. ouvrir les outputs de la tâche `generer_fichier` ;
6. vérifier la présence du fichier `output.log` ;
7. ouvrir ou télécharger le fichier si l'interface le permet ;
8. consulter le log de la tâche `compte_rendu`.

### Résultat attendu

Le flow doit générer un fichier `output.log` contenant le nombre de lignes demandé. La tâche `mesurer_fichier` doit retourner une taille supérieure à zéro. Le log final doit contenir :

```text
Fichier généré=<uri>, taille=<taille>
```

### Preuves à collecter

- statut final en succès ;
- URI ou lien du fichier `output.log` ;
- taille retournée ;
- extrait ou capture montrant quelques lignes du fichier.

### Critère OK / KO

Le test est **OK** si le fichier est produit, stocké, mesuré et consultable.

### Point de vigilance

Ne pas lancer ce test avec un nombre de lignes très élevé sans accord de l'administrateur, car il sollicite le stockage interne et les logs.

---

## Synthèse de fin de campagne orchestration

À la fin des tests F01 à F20, compléter le tableau suivant dans le compte-rendu de POC.

| ID | Statut | Execution ID | Preuve collectée | Commentaire |
|---|---|---|---|---|
| F01 |  |  |  |  |
| F02 |  |  |  |  |
| F03 |  |  |  |  |
| F04 |  |  |  |  |
| F05 |  |  |  |  |
| F06 |  |  |  |  |
| F07 |  |  |  |  |
| F08 |  |  |  |  |
| F09 |  |  |  |  |
| F10 |  |  |  |  |
| F11 |  |  |  |  |
| F12 |  |  |  |  |
| F13 |  |  |  |  |
| F14 |  |  |  |  |
| F15 |  |  |  |  |
| F16 |  |  |  |  |
| F17 |  |  |  |  |
| F18 |  |  |  |  |
| F19 |  |  |  |  |
| F20 |  |  |  |  |

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
