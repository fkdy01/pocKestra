# Basculer le webserver Kestra en HTTPS

Ce mode opératoire active TLS directement dans le webserver Kestra, sans reverse
proxy. Il couvre le POC Docker Compose sous Ubuntu et un déploiement Podman
Compose rootless sous Red Hat Enterprise Linux 8.

## Périmètre et résultat attendu

À l'issue de la bascule :

- Kestra écoute en HTTPS sur le port `8443` ;
- le port HTTP `8080` de Kestra n'est plus publié ;
- la clé privée et le keystore restent hors de Git ;
- les clients valident le certificat avec l'autorité du POC ;
- les données PostgreSQL et Kestra existantes sont conservées.

Le certificat généré par le dépôt est réservé au POC. Pour un environnement
pérenne, faire émettre le certificat par l'autorité de certification de
l'organisation et définir une procédure de renouvellement.

## Principe de configuration

Le fichier `docker-compose.yml` active les propriétés Micronaut utilisées par
Kestra :

```yaml
micronaut:
  security:
    x509:
      enabled: false
  ssl:
    enabled: true
  server:
    ssl:
      enabled: true
      port: 8443
      keyStore:
        path: file:/app/ssl/keystore.p12
        password: ${KESTRA_SSL_KEYSTORE_PASSWORD}
        type: PKCS12
```

`x509.enabled: false` signifie que le certificat client n'est pas exigé. Cela ne
désactive pas le certificat HTTPS du serveur.

## Préparer la bascule commune

1. Se placer à la racine du dépôt et vérifier les fichiers modifiés :

   ```bash
   cd /chemin/vers/pocKestra
   git status --short
   git rev-parse HEAD
   ```

   Conserver l'identifiant de commit dans le ticket de changement pour retrouver
   la dernière configuration HTTP approuvée.

2. Sauvegarder la configuration locale avant la bascule. Ne pas ajouter cette
   sauvegarde à Git :

   ```bash
   cp .env .env.before-https
   chmod 600 .env.before-https
   ```

3. Vérifier que les données sont dans des volumes nommés :

   ```bash
   docker compose config --volumes
   ```

   Sous Podman, utiliser à la place :

   ```bash
   podman-compose -f docker-compose.yml -f compose.podman.yml config >/dev/null
   ```

4. Générer deux mots de passe locaux distincts :

   ```bash
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

5. Reporter les valeurs dans `.env`, respectivement dans
   `KESTRA_DB_PASSWORD` et `KESTRA_SSL_KEYSTORE_PASSWORD`. Ne pas les afficher
   dans un ticket, un rapport ou une capture.

## Choisir le nom couvert par le certificat

Pour un accès limité au poste local, conserver :

```dotenv
KESTRA_BIND_ADDRESS=127.0.0.1
KESTRA_PUBLIC_URL=https://localhost:8443/
KESTRA_URL=https://localhost:8443
KESTRA_TLS_DNS_NAME=localhost
KESTRA_TLS_IP_ADDRESS=127.0.0.1
KESTRA_VERIFY_TLS=true
KESTRA_CA_BUNDLE=.kestra-tls/ca.crt
```

Pour accéder au serveur RHEL depuis un autre poste, utiliser son nom DNS réel.
Les valeurs ci-dessous sont volontairement fictives :

```dotenv
KESTRA_BIND_ADDRESS=0.0.0.0
KESTRA_PUBLIC_URL=https://kestra.example.invalid:8443/
KESTRA_URL=https://kestra.example.invalid:8443
KESTRA_TLS_DNS_NAME=kestra.example.invalid
KESTRA_TLS_IP_ADDRESS=192.0.2.10
KESTRA_VERIFY_TLS=true
KESTRA_CA_BUNDLE=.kestra-tls/ca.crt
```

Le nom utilisé dans le navigateur doit être présent dans le SAN du certificat.
Une modification de nom DNS ou d'adresse IP impose de régénérer le certificat.

Charger les variables puis générer l'autorité locale, le certificat serveur et
le keystore PKCS#12 :

```bash
set -a
source .env
set +a
./scripts/generate_local_tls.sh
```

Contrôler les SAN et le keystore sans afficher son mot de passe :

```bash
openssl x509 -in .kestra-tls/server.crt -noout -subject -issuer -dates \
  -ext subjectAltName
openssl verify -CAfile .kestra-tls/ca.crt .kestra-tls/server.crt
git check-ignore .env .env.before-https .kestra-tls/keystore.p12
```

Les trois chemins doivent être ignorés par Git. Les fichiers `ca.key`,
`server.key` et `keystore.p12` sont confidentiels.

## Parcours A — Ubuntu avec Docker Compose

### Prérequis

- Docker Engine et le plugin Docker Compose sont installés ;
- l'utilisateur peut exécuter `docker compose` ;
- les ports `8443` et `18080` sont disponibles ;
- le certificat a été généré avec la procédure commune.

### Appliquer la bascule

1. Vérifier la configuration sans imprimer les valeurs interpolées :

   ```bash
   docker compose config --quiet
   ```

2. Recréer Kestra. Les volumes nommés ne sont pas supprimés :

   ```bash
   docker compose up -d --force-recreate kestra
   docker compose ps
   ```

3. Vérifier que Kestra annonce un serveur HTTPS sur `8443` :

   ```bash
   docker compose logs --tail 100 kestra
   ```

4. Tester la chaîne de confiance et l'API :

   ```bash
   curl --fail --silent --show-error \
     --cacert .kestra-tls/ca.crt \
     https://localhost:8443/api/v1/configs
   ```

5. Ouvrir `https://localhost:8443` dans le navigateur. Pour supprimer
   l'avertissement, importer uniquement `.kestra-tls/ca.crt` dans le magasin de
   confiance du navigateur ou du poste. Ne jamais importer une clé privée.

6. Exécuter un smoke test réel avec les variables chargées :

   ```bash
   python3 scripts/run_kestra_tests.py --kestra-live
   ```

Une réponse HTTPS valide ne suffit pas à prouver l'exécution des flows : conserver
également le rapport de tests et les identifiants d'exécution.

## Parcours B — RHEL 8 avec Podman rootless

### Prérequis administrateur, une seule fois

L'administrateur RHEL installe les outils de conteneur approuvés par
l'organisation :

```bash
sudo dnf module install -y container-tools
```

Le fournisseur Compose doit aussi être présent. Le présent guide utilise la
commande `podman-compose`, conformément au guide Kestra. Selon les dépôts activés,
son installation peut être assurée par un paquet approuvé ou un environnement
Python maintenu par l'organisation.

Vérifier que le compte de service rootless possède des plages distinctes dans les
deux fichiers :

```bash
grep "^${USER}:" /etc/subuid /etc/subgid
```

Si une ligne manque, demander à l'administrateur d'allouer des plages subuid et
subgid non conflictuelles. Ne pas choisir arbitrairement une plage déjà utilisée.

Pour permettre un redémarrage automatique hors session, l'administrateur peut
activer le maintien du gestionnaire systemd utilisateur :

```bash
sudo loginctl enable-linger kestra-poc
```

Remplacer `kestra-poc` par le compte rootless réellement retenu.

### Vérifier le contexte rootless

Toutes les commandes suivantes, sauf celles explicitement préfixées par `sudo`,
sont exécutées avec le compte rootless :

```bash
podman --version
podman-compose version
podman info --format '{{.Host.Security.Rootless}}'
```

La dernière commande doit retourner `true`. Le `user: "root"` du service Kestra
désigne seulement root dans l'espace de noms du conteneur ; il ne donne pas les
privilèges root sur l'hôte RHEL.

### Préparer SELinux et le réseau

Conserver SELinux en mode enforcing. La surcharge `compose.podman.yml` ajoute le
suffixe `:Z` au montage du certificat afin de lui attribuer un label privé au
conteneur Kestra. Ne pas utiliser `--privileged` et ne pas désactiver SELinux.

Le port `8443`, supérieur à `1024`, peut être publié sans modifier la plage des
ports privilégiés rootless. Pour un accès distant, faire ouvrir le port par
l'administrateur :

```bash
sudo firewall-cmd --permanent --add-port=8443/tcp
sudo firewall-cmd --reload
```

Pour un POC limité à `127.0.0.1`, ne pas ouvrir le pare-feu.

### Démarrer avec Podman Compose

1. Valider la fusion de la configuration commune et de la surcharge SELinux :

   ```bash
   podman-compose -f docker-compose.yml -f compose.podman.yml config >/dev/null
   ```

   La redirection évite d'afficher les secrets interpolés dans le terminal ou
   dans un journal de session.

2. Construire le mock, créer le réseau et démarrer les services :

   ```bash
   podman-compose -f docker-compose.yml -f compose.podman.yml build mock-api
   podman-compose -f docker-compose.yml -f compose.podman.yml up -d
   podman-compose -f docker-compose.yml -f compose.podman.yml ps
   ```

3. Si la version de Podman Compose ne gère pas les conditions de santé, attendre
   que PostgreSQL et le mock soient sains, puis recréer Kestra :

   ```bash
   podman healthcheck run poc-kestra-postgres-1
   podman healthcheck run poc-kestra-mock-api-1
   podman-compose -f docker-compose.yml -f compose.podman.yml up -d kestra
   ```

   Les noms exacts peuvent varier avec la version. Les relever avec
   `podman ps -a --format '{{.Names}}'`.

4. Contrôler les journaux et le port publié :

   ```bash
   podman-compose -f docker-compose.yml -f compose.podman.yml logs --tail 100 kestra
   podman ps --format 'table {{.Names}}\t{{.Ports}}'
   ```

5. Tester depuis l'hôte RHEL avec l'URL définie dans `KESTRA_URL` :

   ```bash
   curl --fail --silent --show-error \
     --cacert .kestra-tls/ca.crt \
     "${KESTRA_URL}/api/v1/configs"
   ```

6. Depuis un poste client distant, copier seulement `ca.crt` par un canal
   approuvé, valider son empreinte par un second canal, puis tester le même nom
   DNS dans le navigateur. Ne jamais transférer le dossier `.kestra-tls` entier.

### Démarrage automatique rootless

RHEL 8 peut utiliser les unités systemd générées par Podman. Comme les noms de
conteneur dépendent du fournisseur Compose, les relever d'abord :

```bash
podman ps -a --format '{{.Names}}'
postgres_container=poc-kestra-postgres-1
mock_container=poc-kestra-mock-api-1
kestra_container=poc-kestra-kestra-1
mkdir -p "${HOME}/.config/systemd/user"
cd "${HOME}/.config/systemd/user"
podman generate systemd --files --name "${postgres_container}"
podman generate systemd --files --name "${mock_container}"
podman generate systemd --files --name "${kestra_container}"
chmod 600 "container-${postgres_container}.service"
chmod 600 "container-${mock_container}.service"
chmod 600 "container-${kestra_container}.service"
systemctl --user daemon-reload
systemctl --user enable --now "container-${postgres_container}.service"
systemctl --user enable --now "container-${mock_container}.service"
systemctl --user enable --now "container-${kestra_container}.service"
```

Adapter les trois variables si `podman ps` affiche d'autres noms.

Cette variante gère les conteneurs existants et n'inscrit pas leur configuration
complète dans les unités. Après une modification Compose, exécuter de nouveau
`podman-compose up -d`, puis régénérer les unités.

Redémarrer l'hôte pendant une fenêtre de test, puis vérifier :

```bash
systemctl --user status "container-${kestra_container}.service" --no-pager
curl --fail --silent --show-error \
  --cacert /chemin/vers/pocKestra/.kestra-tls/ca.crt \
  https://kestra.example.invalid:8443/api/v1/configs
```

Quadlet est recommandé avec les versions récentes de Podman, mais n'est pas
disponible sur toutes les versions livrées avec RHEL 8. La méthode ci-dessus est
donc retenue pour la compatibilité de ce POC.

## Critères de validation et preuves

| Contrôle | Critère OK | Preuve à conserver |
|---|---|---|
| Certificat | SAN conforme, dates valides, `openssl verify` retourne `OK` | Sortie sans clé ni mot de passe |
| Publication | Seul `8443` est publié pour Kestra | Sortie `compose ps` ou `podman port` |
| Démarrage | Le journal annonce HTTPS sur `8443` | Extrait de journal expurgé |
| Confiance TLS | `curl --cacert` réussit sans `-k` | Commande et code retour |
| Interface | L'UI s'ouvre avec le nom présent dans le certificat | Capture sans donnée sensible |
| Flow | Le smoke test atteint le statut attendu | Rapport Markdown et ID d'exécution |
| Rootless RHEL | `Rootless` vaut `true`, SELinux reste actif | Sorties `podman info` et `getenforce` |

Le test est **KO** si l'accès nécessite `curl -k`, si le nom du certificat ne
correspond pas, si une clé privée apparaît dans Git, si Kestra ne démarre qu'avec
`--privileged`, ou si les données existantes ont disparu.

## Retour arrière

1. Arrêter uniquement le service Kestra, sans option `--volumes` :

   ```bash
   docker compose stop kestra
   ```

   ou :

   ```bash
   podman-compose -f docker-compose.yml -f compose.podman.yml stop kestra
   ```

2. Restaurer la configuration Compose HTTP depuis la révision approuvée relevée
   avant la bascule, puis les valeurs locales de `.env.before-https`. Effectuer
   cette restauration sur une branche et contrôler le diff avant redémarrage.

3. Recréer Kestra puis vérifier l'ancienne URL. Ne pas supprimer les volumes
   `postgres-data`, `kestra-data` ou `kestra-workdir`.

4. Si le port RHEL a été ouvert uniquement pour ce test, demander à
   l'administrateur de le refermer :

   ```bash
   sudo firewall-cmd --permanent --remove-port=8443/tcp
   sudo firewall-cmd --reload
   ```

Conserver les certificats jusqu'à la fin de la période de retour arrière, puis
les détruire selon la procédure de gestion des secrets de l'organisation.

## Renouvellement du certificat

Contrôler régulièrement l'échéance :

```bash
openssl x509 -in .kestra-tls/server.crt -noout -enddate
```

Au moins 30 jours avant l'expiration, générer ou recevoir un nouveau certificat,
mettre à jour le keystore, recréer seulement Kestra et répéter tous les contrôles
TLS. La génération locale renouvelle aussi l'autorité du POC : il faut alors
redistribuer le nouveau `ca.crt` aux clients.

## Références

- [Configuration SSL/TLS officielle de Kestra](https://kestra.io/docs/administrator-guide/ssl-configuration)
- [Kestra avec Podman Compose](https://kestra.io/docs/installation/podman-compose)
- [Conteneurs rootless sous RHEL 8](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/building_running_and_managing_containers/)
- [Unités systemd Podman](https://docs.podman.io/en/latest/markdown/podman-generate-systemd.1.html)
