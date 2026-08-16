# Tester Kestra Red Hat/Podman via une VIP HTTPS

Les tests sont lancés depuis un poste client. Aucun accès shell au serveur Red Hat
n'est requis. La VIP termine HTTPS et relaie les requêtes vers Kestra.

## Prérequis à demander à l'administrateur

- URL de la VIP et chaîne de certificats valide ;
- tenant cible ;
- compte ou token autorisé à importer des flows, les exécuter et lire leur statut ;
- routage de `/api/` sans réécriture incompatible, avec des timeouts supérieurs à 180 s ;
- URL du mock joignable **depuis les workers Kestra**.

Sans mock joignable, la campagne exhaustive ne peut pas valider les flows qui
simulent les SI externes. Le testeur ne doit pas tenter de modifier Podman sans accès administrateur.

## Configurer le poste client

```bash
git clone <URL_DU_DEPOT>
cd pocKestra
cp config/examples/redhat-vip-client.env.example .env.redhat-vip.local
chmod 600 .env.redhat-vip.local
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Dans `.env.redhat-vip.local`, renseigner localement :

- `KESTRA_URL` avec le nom couvert par le certificat de la VIP ;
- l'authentification fournie ;
- `KESTRA_MOCK_BASE_URL` fourni par l'administrateur ;
- `KESTRA_CA_BUNDLE` seulement pour une autorité privée non installée sur le poste.

Conserver `KESTRA_VERIFY_TLS=true`. Ne jamais commiter le fichier ni utiliser une
adresse IP qui n'est pas présente dans le SAN du certificat.

## Tester puis lancer la campagne

```bash
set -a
source .env.redhat-vip.local
set +a

# Smoke test sans dépendance au mock.
.venv/bin/python -m pytest tests/kestra/test_smoke_orchestration.py \
  --kestra-live -k f01 -v

# Campagne exhaustive et rapport de preuve.
.venv/bin/python scripts/run_kestra_tests.py --kestra-live \
  --report test-reports/redhat-vip-https.md
```

Le critère est `Résultat global : OK` avec 66 scénarios automatiques prouvés.
Un HTTP `401/403` indique un problème de droits ; un `502/504`, un problème de
VIP ou de timeout ; une erreur de certificat doit être corrigée, jamais contournée.

Relire le rapport avant diffusion. L'URL de la VIP, celle du mock et les secrets
issus de l'environnement sont masqués automatiquement.
