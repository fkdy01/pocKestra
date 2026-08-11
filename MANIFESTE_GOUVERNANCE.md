# Lot gouvernance POC Kestra

Ce paquet correspond à l'onglet **Gouvernance** du POC Kestra.

Contenu poussé dans la branche `agent/gouvernance-use-cases` :

- `kestra/flows/gouvernance/` : flows G01 à G10 ;
- `docs/use-cases/gouvernance.md` : catalogue des scénarios ;
- `docs/test-guides/gouvernance.md` : mode opératoire testeur ;
- `mock-api/governance_support.py` : endpoints mock RBAC, CI/CD, audit, promotion et worker groups ;
- `mock-api/app.py` : enregistrement des routes gouvernance ;
- `README.md` : ajout de l'arborescence gouvernance.

La syntaxe YAML des flows a été contrôlée localement avant publication.
