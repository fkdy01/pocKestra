# Générer un rapport de tests automatisés

## Objectif

Cette procédure génère une preuve Markdown horodatée pour la validation YAML et les tests pytest du POC.

Le rapport indique clairement :

- les commandes exécutées ;
- le résultat et la durée de chaque étape ;
- les tests réussis, échoués ou ignorés ;
- le namespace, le flow, les inputs, l'identifiant d'exécution Kestra, le statut
  attendu, le statut observé et le verdict lorsque le test live a réellement
  créé une exécution ;
- les sorties textuelles utiles au diagnostic.

Le dossier `test-reports/` est local et ignoré par Git.

Le catalogue [flow_test_catalog.yml](../../tests/kestra/flow_test_catalog.yml)
recense tous les flows présents sous `kestra/flows/`. Le test échoue si un flow
du dépôt manque dans ce catalogue ou si une entrée ne correspond plus à un
fichier réel.

## Prérequis

1. Installer les dépendances de développement :

   ```bash
   python3 -m pip install -r requirements-dev.txt
   ```

2. Se placer à la racine du dépôt.

3. Pour un test live, démarrer Kestra et le mock API puis configurer les variables locales nécessaires.

Les mots de passe, tokens et autres secrets doivent rester dans `.env` ou dans l'environnement local. Ils ne doivent jamais être copiés dans le dépôt.

## Rapport sans exécution live

Exécuter :

```bash
python3 scripts/run_kestra_tests.py
```

Cette commande :

1. valide tous les fichiers YAML ;
2. lance les tests unitaires ;
3. marque les smoke tests Kestra comme ignorés ;
4. écrit un rapport sous `test-reports/kestra-tests-<horodatage>.md`.

Un test ignoré ne constitue pas une preuve d'exécution dans Kestra.

## Rapport avec exécutions Kestra

Configurer l'environnement local sans afficher les secrets :

```bash
export KESTRA_RUN_TESTS=true
python3 scripts/run_kestra_tests.py
```

Il est aussi possible d'utiliser l'option explicite :

```bash
python3 scripts/run_kestra_tests.py --kestra-live
```

Chaque smoke test live émet des preuves structurées :

- création de l'exécution Kestra ;
- observation de son état terminal ;
- comparaison avec l'état attendu par le test.

Le lanceur consolide ces éléments dans le tableau « Preuves d'exécution Kestra » du rapport.

Il produit également une matrice exhaustive contenant :

- tous les cas d'usage et sous-flows communs ;
- chaque scénario automatique attendu ;
- l'identifiant d'exécution et le verdict observé ;
- les flows restant manuels et la justification correspondante.

Pour conserver un nom stable lors de la revue, utiliser :

```bash
python3 scripts/run_kestra_tests.py --kestra-live \
  --report test-reports/kestra-exhaustif.md
```

## Choisir le chemin du rapport

Pour produire un fichier déterministe, par exemple dans une collecte CI locale :

```bash
python3 scripts/run_kestra_tests.py --report test-reports/rapport-courant.md
```

Attention : une nouvelle exécution avec le même chemin remplace ce fichier local.

## Sécurité du rapport

Avant écriture, le lanceur masque :

- la valeur de `KESTRA_URL` ;
- les variables dont le nom indique un mot de passe, un token, un secret, une authentification ou une clé privée.

Le rapport consigne les inputs des smoke tests afin de constituer la preuve. Ces
tests doivent donc employer uniquement les valeurs fictives prévues par le POC.
Les en-têtes HTTP d'authentification ne sont pas consignés. Il faut néanmoins
relire le rapport avant de le transmettre, car une application testée peut
produire elle-même des données sensibles dans un message d'erreur.

## Critère OK / KO

- **OK** : validation YAML réussie, code retour pytest égal à `0` et catalogue
  cohérent avec les flows du dépôt.
- **OK exhaustif** : tous les scénarios automatiques du catalogue possèdent une
  assertion `OK`. Les flows marqués `manual` restent visibles et ne sont jamais
  assimilés à des tests exécutés.
- **KO** : validation YAML ou pytest en échec.
- **KO, code `3`** : le mode live était demandé mais aucune exécution Kestra n'a pu être prouvée, par exemple si l'instance était injoignable et que les tests ont été ignorés.
- **KO, code `4`** : le catalogue et les fichiers du dépôt ne correspondent pas.
- **Preuve live disponible** : le rapport contient le flow, les inputs,
  l'identifiant d'exécution, le statut attendu, le statut observé et le verdict.
- **Preuve live absente** : le rapport mentionne que les tests live sont désactivés ou qu'aucune preuve structurée n'a été collectée.

## Limites

Le rapport Markdown fournit une preuve technique textuelle d'import, d'exécution
et de statut. Il ne remplace pas les captures de l'interface, l'analyse complète
des logs et outputs, ni les preuves manuelles demandées par les guides de test du
POC. Une matrice exhaustive ne signifie donc pas que les scénarios marqués
`MANUEL` ont été exécutés.
