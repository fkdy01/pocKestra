# AGENTS.md — POC Kestra Enterprise

## Objectif du dépôt

Ce dépôt contient le matériel de POC Kestra Enterprise pour évaluer le remplacement de workflows HPOO.

Le dépôt est organisé par familles de cas d'usage correspondant aux onglets de la grille d'évaluation :

- orchestration ;
- infrastructure ;
- exploitation ;
- gouvernance ;
- futurs onglets de POC.

Les artefacts attendus sont :

- flows Kestra YAML ;
- API mock FastAPI ;
- catalogues de cas d'usage ;
- modes opératoires pour testeurs non spécialistes Kestra ;
- scripts de validation.

## Rôle de Codex

Codex peut aider à faire évoluer ce dépôt depuis VS Code en proposant des modifications de code, de YAML et de documentation.

Codex doit :

- respecter la structure existante du dépôt ;
- privilégier des changements petits, relisibles et traçables ;
- conserver une logique de POC exécutable sans dépendance à des SI réels ;
- utiliser des mocks lorsque la cible réelle n'est pas disponible ;
- documenter les limites et prérequis de chaque cas ;
- ne jamais introduire de secret, mot de passe, token ou endpoint interne réel.

## Structure du dépôt

```text
kestra/flows/orchestration/     # flows F01 à F20
kestra/flows/infrastructure/    # flows I01 à I15
kestra/flows/exploitation/      # flows R01 à R10
kestra/flows/gouvernance/       # flows G01 à G10
docs/use-cases/                 # catalogues par famille de cas d'usage
docs/test-guides/               # modes opératoires testeur
mock-api/                       # API FastAPI de simulation
scripts/validate_yaml.py        # validation syntaxique YAML
```

## Conventions de nommage

### Flows Kestra

Les flows doivent être nommés selon le format :

```text
<ID>_<nom_court>.yml
```

Exemples :

```text
F01_sequence_simple.yml
I01_api_rest_interne.yml
R01_consulter_execution_echec.yml
G01_flow_source_git.yml
```

### Identifiants Kestra

Chaque fichier YAML doit contenir :

- un `id` identique au nom du fichier sans extension ;
- un `namespace` cohérent avec la famille ;
- des `labels` permettant de retrouver le domaine et le cas d'usage.

Namespaces existants :

```text
poc.kestra.orchestration
poc.kestra.infrastructure
poc.kestra.exploitation
poc.kestra.gouvernance
```

Labels recommandés :

```yaml
labels:
  poc.domain: <orchestration|infrastructure|exploitation|gouvernance>
  poc.usecase: <ID>
```

## Règles de conception des flows

Un flow de POC doit être compréhensible par un testeur non spécialiste Kestra.

Chaque flow doit :

- avoir une description explicite ;
- exposer des inputs simples et documentables ;
- produire des logs lisibles ;
- produire des outputs utiles lorsque cela aide à la preuve ;
- éviter les dépendances fortes à un environnement réel ;
- proposer un mode mock si la cible réelle n'est pas disponible ;
- indiquer clairement lorsqu'un échec est volontaire et attendu.

Les cas d'erreur volontaires doivent être nommés et documentés, afin d'éviter qu'un testeur les interprète comme une anomalie de plateforme.

## API mock

Le dossier `mock-api/` contient une API FastAPI utilisée pour simuler les SI externes.

Elle peut simuler notamment :

- API interne ;
- CMDB ;
- ITSM ;
- AAP / Ansible Automation Platform ;
- VMware / vCenter ;
- AD / LDAP ;
- SCCM ;
- SIEM ;
- alerting ;
- purge / rétention ;
- audit ;
- contrôles de gouvernance.

Règles pour modifier le mock :

- ne pas supprimer un endpoint déjà utilisé par un flow existant ;
- ajouter des endpoints explicites et stables ;
- conserver des réponses JSON simples ;
- éviter les états complexes sauf si le scénario le nécessite ;
- documenter les nouveaux endpoints dans le catalogue ou le guide testeur ;
- ne jamais intégrer d'URL ou de secret réel.

## Documentation attendue par onglet

Pour chaque nouvelle famille de cas d'usage, créer ou mettre à jour :

```text
docs/use-cases/<onglet>.md
docs/test-guides/<onglet>.md
```

Le catalogue `docs/use-cases/<onglet>.md` doit contenir :

- l'objectif de la famille ;
- les prérequis ;
- la liste des flows ;
- un tableau ID / flow / objectif / preuve attendue ;
- les points de vigilance.

Le guide `docs/test-guides/<onglet>.md` doit contenir, pour chaque cas :

- l'objectif du test ;
- le flow à utiliser ;
- les prérequis spécifiques ;
- les données d'entrée ;
- les étapes d'exécution dans Kestra ;
- le résultat attendu ;
- les preuves à collecter ;
- le critère OK / KO ;
- les points de vigilance.

## Convention de preuve pour les testeurs

Pour chaque test, le guide doit demander de collecter au minimum :

- identifiant du cas d'usage ;
- identifiant du flow Kestra ;
- identifiant d'exécution Kestra ;
- statut final ;
- inputs utilisés ;
- capture ou extrait des logs ;
- capture ou extrait des outputs ;
- date du test ;
- nom du testeur ;
- commentaire en cas d'écart.

Nom de preuve recommandé :

```text
<usecase>_<flowId>_<executionId>_<AAAAMMJJ>.png
```

## Validation locale

Avant de proposer ou finaliser une modification, lancer au minimum :

```bash
python3 scripts/validate_yaml.py
```

Si le mock API est modifié, lancer si possible :

```bash
docker compose up -d mock-api
```

Puis vérifier que l'API démarre correctement.

Ne pas prétendre qu'un flow a été exécuté dans Kestra si seule la syntaxe YAML a été validée.

## Travail avec Git et VS Code

Lorsque Codex agit comme agent dans VS Code :

- lire ce fichier avant toute modification ;
- inspecter les fichiers existants similaires avant d'ajouter un nouveau lot ;
- éviter de reformater massivement des fichiers non concernés ;
- limiter les changements au périmètre demandé ;
- préparer un résumé clair des fichiers modifiés ;
- indiquer les tests exécutés et ceux non exécutés.

Même si l'utilisateur autorise un commit direct sur `main`, privilégier une branche de travail pour les changements significatifs.

Un commit direct sur `main` n'est acceptable que pour :

- correction documentaire simple ;
- ajout de consignes ;
- ajustement mineur sans impact fonctionnel.

## Branches et Pull Requests

Pour tout lot fonctionnel ou nouvel onglet, utiliser une branche dédiée :

```text
agent/<nom-du-lot>
```

Exemples :

```text
agent/securite-use-cases
agent/resilience-use-cases
agent/capacity-planning
```

La PR doit contenir :

- objet ;
- contenu ;
- couverture fonctionnelle ;
- validations réalisées ;
- limites connues ;
- points de vigilance ;
- mention explicite si les flows n'ont pas été exécutés dans Kestra.

## Sécurité

Ne jamais ajouter dans le dépôt :

- secret réel ;
- token ;
- mot de passe ;
- clé privée ;
- certificat privé ;
- URL interne réelle ;
- IP interne réelle ;
- nom d'environnement sensible ;
- donnée de production ;
- extrait de logs contenant des informations sensibles.

Utiliser systématiquement des valeurs fictives, par exemple :

```text
example.invalid
mock-api
srv-001
SUB-48972
POC_API_TOKEN
SECRET_NON_CONFIGURE
```

Les flows démontrant l'usage des secrets doivent vérifier la référence au secret, pas afficher sa valeur.

## Worker groups et environnements réels

Les worker groups Kestra Enterprise sont souvent dépendants de l'environnement.

Lorsqu'un flow fait référence à un worker group :

- prévoir un mode mock si possible ;
- documenter le worker group attendu ;
- ne pas rendre le test bloquant si le worker group n'existe pas ;
- indiquer clairement ce qui relève du POC mock et ce qui relève du test réel.

Worker groups déjà utilisés ou envisagés :

```text
windows
windows-sccm
linux-podman
linux-outils
```

## Style de rédaction

La documentation doit être écrite en français, avec un style opérationnel.

Préférer :

- phrases courtes ;
- étapes numérotées ;
- tableaux simples ;
- critères OK / KO explicites ;
- avertissements de sécurité visibles.

Éviter :

- jargon Kestra non expliqué ;
- longues sections théoriques ;
- hypothèses implicites ;
- promesses d'exécution non vérifiées.

## Règle de sincérité technique

Toujours distinguer :

- fichier généré ;
- syntaxe YAML validée ;
- mock API démarré ;
- flow réellement exécuté dans Kestra ;
- résultat observé par un testeur.

Ne jamais écrire qu'un test est validé de bout en bout si l'exécution réelle dans Kestra n'a pas été faite.
