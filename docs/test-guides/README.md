# Guides de test POC Kestra

Ce dossier contient les modes opératoires destinés aux testeurs qui ne sont pas spécialistes Kestra.

## Règle à appliquer pour chaque onglet

Pour chaque famille de cas d'usage, le guide doit contenir :

1. les prérequis communs ;
2. le mode d'import ou de vérification des flows ;
3. un déroulé pas-à-pas pour chaque cas d'usage ;
4. les jeux de données à saisir ;
5. les résultats attendus ;
6. les preuves à collecter ;
7. les critères OK / KO ;
8. les points de vigilance.

## Convention de preuve

Pour chaque test, le testeur doit relever au minimum :

- l'identifiant du cas d'usage, par exemple `F01` ;
- l'identifiant du flow Kestra ;
- l'identifiant d'exécution Kestra ;
- le statut final de l'exécution ;
- une capture ou un extrait des logs montrant le résultat attendu ;
- une capture ou un extrait des outputs lorsque le cas en produit ;
- la date et le nom du testeur.

Nom de fichier recommandé :

```text
<usecase>_<flowId>_<executionId>_<AAAAMMJJ>.png
```

Exemple :

```text
F01_F01_sequence_simple_3pZxA1_20260811.png
```

## Statuts recommandés

| Statut | Signification |
|---|---|
| OK | Le résultat attendu est obtenu et les preuves sont collectées. |
| OK avec réserve | Le test passe mais une limite ou une anomalie mineure est notée. |
| KO | Le résultat attendu n'est pas obtenu. |
| Non testé | Le test n'a pas pu être exécuté. |
| Non applicable | Le cas ne s'applique pas à l'environnement testé. |
