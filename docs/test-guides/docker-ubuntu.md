# Lancer Kestra OSS avec Docker Engine sous Ubuntu

Ce mode opératoire démarre un environnement local de POC composé de Kestra OSS,
PostgreSQL et de l'API mock du dépôt. Il cible Ubuntu 22.04 LTS, 24.04 LTS ou une
version Ubuntu prise en charge par Docker Engine.

## Périmètre et limites

- L'environnement est local et non destiné à la production.
- L'interface Kestra utilise HTTPS directement dans le webserver Kestra et écoute
  uniquement sur `127.0.0.1:8443`.
- L'authentification Kestra n'est pas activée.
- Le mot de passe PostgreSQL est un secret local propre au POC.
- Le socket Docker de l'hôte n'est pas monté dans Kestra.
- Les flows utilisant le runner `Process` restent exécutables. Un flow utilisant
  un runner Docker demanderait une configuration supplémentaire.
- La version Kestra est épinglée dans `.env.example` et `docker-compose.yml`.
- Une validation YAML ne prouve pas une exécution réelle dans Kestra.

## Prérequis matériels

Prévoir au minimum :

- 2 processeurs ;
- 4 Gio de mémoire disponible ;
- 10 Gio d'espace disque disponible pour les images et volumes du POC.

## Installer Docker Engine et Compose

Si Docker Engine et le plugin Compose sont déjà installés, passer directement à
la section suivante.

Ajouter le dépôt officiel Docker :

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo apt install -y python3 python3-venv python3-pip
```

Vérifier le service et les commandes :

```bash
sudo systemctl status docker --no-pager
sudo docker run --rm hello-world
sudo docker compose version
```

Pour utiliser Docker sans `sudo`, ajouter le compte local au groupe `docker` :

```bash
sudo usermod -aG docker "$USER"
```

Fermer puis rouvrir la session Ubuntu avant de continuer. L'appartenance au groupe
`docker` donne des privilèges équivalents à ceux de `root` sur la machine. Sur un
poste partagé, conserver plutôt l'utilisation explicite de `sudo`.

## Préparer les variables locales

Depuis la racine du dépôt :

```bash
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Copier la valeur générée dans `KESTRA_DB_PASSWORD` du fichier `.env`. Conserver les
autres valeurs proposées pour un premier démarrage :

```dotenv
KESTRA_DB_PASSWORD=<VALEUR_LOCALE_GENEREE>
KESTRA_SSL_KEYSTORE_PASSWORD=<AUTRE_VALEUR_LOCALE_GENEREE>
KESTRA_IMAGE=kestra/kestra:v1.3.20
KESTRA_BIND_ADDRESS=127.0.0.1
KESTRA_PUBLIC_URL=https://localhost:8443/
KESTRA_URL=https://localhost:8443
KESTRA_TENANT=main
KESTRA_RUN_TESTS=false
KESTRA_API_TOKEN=
KESTRA_TLS_DNS_NAME=localhost
KESTRA_TLS_IP_ADDRESS=127.0.0.1
KESTRA_VERIFY_TLS=true
KESTRA_CA_BUNDLE=.kestra-tls/ca.crt
```

Le fichier `.env` est ignoré par Git. Le vérifier avant de poursuivre :

```bash
git check-ignore .env
```

La commande doit afficher `.env`. Ne jamais utiliser dans ce POC un mot de passe,
un token ou une URL provenant d'un environnement réel.

## Générer le certificat HTTPS local

Le webserver Kestra attend un keystore PKCS#12. Charger les variables locales puis
générer un certificat autosigné valable pour `localhost` et `127.0.0.1` :

```bash
set -a
source .env
set +a
./scripts/generate_local_tls.sh
```

Le script crée une autorité locale, un certificat serveur et
`.kestra-tls/keystore.p12`. Ce dossier est ignoré par Git. Ne jamais commiter ni
transmettre `.kestra-tls/ca.key`, `.kestra-tls/server.key` ou le keystore.

Le certificat local chiffre les échanges, mais le navigateur ne lui fait pas
confiance par défaut. Pour supprimer l'avertissement, installer uniquement
`.kestra-tls/ca.crt` dans le magasin de certificats local. Ne jamais importer une
clé privée ailleurs.

## Vérifier et démarrer l'environnement

Valider la configuration sans afficher les valeurs interpolées :

```bash
docker compose config --quiet
```

Télécharger les images, construire le mock et démarrer les services :

```bash
docker compose pull
docker compose build mock-api
docker compose up -d
docker compose ps
```

Le premier démarrage peut prendre plusieurs minutes. Suivre Kestra avec :

```bash
docker compose logs --follow kestra
```

Quitter le suivi avec `Ctrl+C` ne stoppe pas les conteneurs.

## Contrôler le démarrage

Vérifier l'API mock depuis Ubuntu :

```bash
curl --fail --silent --show-error http://localhost:18080/health
```

Vérifier Kestra en validant explicitement le certificat généré :

```bash
curl --fail --silent --show-error \
  --cacert .kestra-tls/ca.crt \
  https://localhost:8443/api/v1/configs
```

Ouvrir ensuite `https://localhost:8443` dans un navigateur. Depuis un flow Kestra,
le mock est accessible sur le réseau Compose avec :

```text
http://mock-api:8080
```

Depuis le conteneur Kestra, `localhost` désigne le conteneur Kestra lui-même. Il ne
faut donc pas remplacer l'URL interne du mock par `http://localhost:18080`.

## Valider et importer les flows

Installer les dépendances Python dans un environnement virtuel local :

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

Charger les variables de `.env` dans le shell courant. Docker Compose lit ce
fichier automatiquement, mais les scripts Python utilisent les variables déjà
présentes dans leur environnement :

```bash
set -a
source .env
set +a
```

Valider uniquement la syntaxe YAML :

```bash
python3 scripts/validate_yaml.py
```

Importer ensuite les flows dans l'instance Kestra démarrée :

```bash
python3 scripts/import_flows.py --all
```

Lancer les smoke tests live :

```bash
python3 scripts/run_kestra_tests.py --kestra-live
```

Vérifier le résultat pytest et les exécutions dans l'interface avant de conclure à
une validation de bout en bout.

## Arrêter ou réinitialiser

Arrêter les services en conservant les conteneurs et les données :

```bash
docker compose stop
```

Supprimer les conteneurs et le réseau en conservant les volumes :

```bash
docker compose down
```

La commande suivante supprime aussi la base PostgreSQL et les données Kestra. Elle
est irréversible et ne doit être utilisée que pour réinitialiser volontairement le
POC :

```bash
docker compose down --volumes
```

## Diagnostic rapide

```bash
docker compose ps
docker compose logs --tail 100 postgres
docker compose logs --tail 100 mock-api
docker compose logs --tail 100 kestra
curl --fail --silent --show-error http://localhost:18080/health
curl --fail --silent --show-error \
  --cacert .kestra-tls/ca.crt \
  https://localhost:8443/api/v1/configs
```

Si le port `8443` ou `18080` est déjà utilisé, arrêter le service en conflit avant
de relancer Compose. Conserver `http://mock-api:8080` pour les appels effectués par
les flows.

## Références

- [Installation officielle de Docker Engine sous Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Étapes Docker après installation sous Linux](https://docs.docker.com/engine/install/linux-postinstall/)
- [Déploiement officiel de Kestra avec Docker Compose](https://kestra.io/docs/installation/docker-compose)
- [Configuration SSL/TLS officielle de Kestra](https://kestra.io/docs/administrator-guide/ssl-configuration)
