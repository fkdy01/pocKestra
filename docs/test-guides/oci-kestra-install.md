# Mode opératoire — Installation de Kestra OSS sur OCI avec PostgreSQL et HTTPS

## 1. Objectif

Ce document poursuit [`oci-vm.md`](./oci-vm.md). Il décrit l'installation de **Kestra Open Source** et PostgreSQL sur la VM OCI ARM64, puis sa publication en HTTPS afin que l'IHM soit utilisable depuis un poste d'entreprise limité à des sites HTTPS autorisés.

Architecture cible :

```text
Poste entreprise
      |
      | HTTPS/443
      v
Proxy Web entreprise
      |
      v
kestra-poc.example.net
      |
      v
OCI Load Balancer :443
      |
      | HTTP/8080 réseau OCI
      v
VM OCI vm-kestra-oss-01
      |
      +-- Kestra OSS :8080
      +-- PostgreSQL :5432
```

Aucun accès public direct à `8080` ou `5432` n'est nécessaire.

---

## 2. Prérequis

Le guide suppose que la VM suivante existe :

```text
VM          : vm-kestra-oss-01
Shape       : VM.Standard.A1.Flex
CPU         : 2 OCPU
RAM         : 12 Go
OS          : Ubuntu LTS ARM64
Architecture: aarch64
```

Vérifier :

```bash
uname -m
nproc
free -h
df -h /
```

Résultat attendu :

```text
aarch64
2 CPU
~12 Go RAM
```

Prévoir également :

- un FQDN, par exemple `kestra-poc.example.net` ;
- un certificat TLS reconnu par le poste d'entreprise ;
- la possibilité de demander l'autorisation de ce FQDN dans le proxy Web entreprise.

---

## 3. Se connecter à la VM

Depuis OCI Cloud Shell ou OCI Bastion :

```bash
ssh ubuntu@<PRIVATE_IP_VM>
```

Exemple :

```bash
ssh ubuntu@10.20.10.25
```

L'accès SSH direct depuis le poste d'entreprise n'est pas requis.

---

## 4. Mettre à jour Ubuntu

```bash
sudo apt update
sudo apt upgrade -y
sudo reboot
```

Se reconnecter après le redémarrage.

---

## 5. Installer Docker

Installer Docker depuis le dépôt Ubuntu :

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Fermer puis rouvrir la session SSH.

Vérifier :

```bash
docker version
docker compose version
```

Tester l'architecture d'une image :

```bash
docker run --rm alpine uname -m
```

Résultat attendu :

```text
aarch64
```

---

## 6. Créer les répertoires du POC

```bash
sudo mkdir -p /opt/kestra
sudo chown -R $USER:$USER /opt/kestra
cd /opt/kestra
```

Créer un fichier `.env` :

```bash
touch .env
chmod 600 .env
```

Générer deux mots de passe :

```bash
openssl rand -base64 32
openssl rand -base64 32
```

Créer `/opt/kestra/.env` :

```dotenv
POSTGRES_PASSWORD=<MOT_DE_PASSE_POSTGRES>
KESTRA_ADMIN_PASSWORD=<MOT_DE_PASSE_KESTRA>
KESTRA_ADMIN_USERNAME=admin@example.net
```

Ne jamais commiter ce fichier ni les secrets dans Git.

---

## 7. Créer Docker Compose

Créer `/opt/kestra/docker-compose.yml` :

```yaml
services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: kestra
      POSTGRES_USER: kestra
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - kestra
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kestra -d kestra"]
      interval: 10s
      timeout: 5s
      retries: 10

  kestra:
    image: kestra/kestra:latest
    restart: unless-stopped
    command: server standalone
    user: "root"
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8080:8080"
    environment:
      KESTRA_CONFIGURATION: |
        datasources:
          postgres:
            url: jdbc:postgresql://postgres:5432/kestra
            driverClassName: org.postgresql.Driver
            username: kestra
            password: ${POSTGRES_PASSWORD}
        kestra:
          repository:
            type: postgres
          queue:
            type: postgres
          storage:
            type: local
            local:
              basePath: /app/storage
          server:
            basic-auth:
              enabled: true
              username: ${KESTRA_ADMIN_USERNAME}
              password: ${KESTRA_ADMIN_PASSWORD}
    volumes:
      - kestra-storage:/app/storage
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp:/tmp
    networks:
      - kestra

networks:
  kestra:

volumes:
  postgres-data:
  kestra-storage:
```

### Remarque POC

Le montage :

```text
/var/run/docker.sock:/var/run/docker.sock
```

permet à Kestra de lancer des tâches Docker. Il donne cependant des privilèges importants au conteneur Kestra. Cette configuration convient à un **POC isolé**, pas à une architecture de production sans analyse de sécurité complémentaire.

---

## 8. Démarrer PostgreSQL et Kestra

```bash
cd /opt/kestra
docker compose pull
docker compose up -d
```

Vérifier :

```bash
docker compose ps
```

Les deux services doivent être `Up` et PostgreSQL `healthy`.

Consulter les logs :

```bash
docker compose logs -f kestra
```

Quitter avec `Ctrl-C`.

---

## 9. Vérifier Kestra localement

Depuis la VM :

```bash
curl -I http://127.0.0.1:8080
```

Puis :

```bash
curl -u "$(grep KESTRA_ADMIN_USERNAME .env | cut -d= -f2):$(grep KESTRA_ADMIN_PASSWORD .env | cut -d= -f2)" \
  http://127.0.0.1:8080/api/v1/configs
```

Un retour HTTP de Kestra confirme que le serveur est joignable.

Vérifier également :

```bash
ss -lntp | grep 8080
```

---

## 10. Sécuriser le réseau OCI

Le NSG de la VM doit respecter le principe suivant :

```text
Internet             X   VM:8080
Internet             X   VM:5432
OCI Load Balancer    --> VM:8080
```

Créer un NSG pour le Load Balancer :

```text
nsg-kestra-lb
```

### NSG Load Balancer

Ingress :

```text
Source : 0.0.0.0/0
TCP    : 443
```

### NSG VM Kestra

Ingress :

```text
Source : nsg-kestra-lb
TCP    : 8080
```

Ne pas créer :

```text
0.0.0.0/0 -> 8080
0.0.0.0/0 -> 5432
```

PostgreSQL n'est pas publié par Docker et reste accessible uniquement dans le réseau Docker `kestra`.

---

## 11. Créer le Load Balancer OCI

Dans OCI :

```text
Networking
 -> Load Balancers
 -> Create Load Balancer
```

Créer par exemple :

```text
Name : lb-kestra-poc
Type : Public
```

Choisir la bande passante minimale proposée pour le POC et vérifier son éligibilité/coût dans le compte OCI avant validation.

Associer :

```text
VCN : vcn-poc-kestra
NSG : nsg-kestra-lb
```

Le Load Balancer reçoit une adresse IP publique.

---

## 12. Créer le Backend Set

Créer :

```text
Backend Set : bs-kestra
Protocol    : HTTP
Port        : 8080
```

Ajouter comme backend l'adresse privée de la VM :

```text
10.20.10.25:8080
```

Adapter l'adresse à la VM réelle.

Configurer un health check HTTP sur :

```text
Protocol : HTTP
Port     : 8080
Path     : /
```

Le backend doit apparaître :

```text
OK / Healthy
```

Si le health check échoue, vérifier :

```bash
curl -I http://127.0.0.1:8080
```

puis les NSG OCI.

---

## 13. Installer le certificat TLS

Deux possibilités :

### Option A — OCI Certificates

Créer ou importer le certificat dans :

```text
Identity & Security
 -> Certificates
```

Le certificat doit correspondre au FQDN :

```text
kestra-poc.example.net
```

### Option B — Certificat existant

Importer dans OCI :

- certificat serveur ;
- clé privée ;
- chaîne intermédiaire si nécessaire.

La clé privée ne doit jamais être déposée dans Git.

Pour un poste d'entreprise, privilégier une CA publique ou une CA d'entreprise déjà approuvée par le poste.

---

## 14. Créer le listener HTTPS

Dans le Load Balancer :

```text
Listeners
 -> Create Listener
```

Configurer :

```text
Name        : https-kestra
Protocol    : HTTPS
Port        : 443
Backend Set : bs-kestra
Certificate : certificat kestra-poc.example.net
```

Le chemin devient :

```text
HTTPS :443 -> OCI Load Balancer -> HTTP :8080 -> Kestra
```

La terminaison TLS se fait au niveau du Load Balancer OCI.

---

## 15. Configurer le DNS

Créer un enregistrement DNS :

```text
kestra-poc.example.net -> <IP_PUBLIQUE_LOAD_BALANCER>
```

Selon le DNS utilisé, il s'agira d'un enregistrement `A` ou d'un mécanisme équivalent proposé par le fournisseur DNS.

Vérifier :

```bash
nslookup kestra-poc.example.net
```

ou :

```bash
dig kestra-poc.example.net
```

---

## 16. Tester HTTPS hors poste entreprise

Avant de demander l'autorisation du site dans le SI d'entreprise :

```bash
curl -I https://kestra-poc.example.net
```

Vérifier le certificat :

```bash
openssl s_client -connect kestra-poc.example.net:443 \
  -servername kestra-poc.example.net </dev/null
```

Contrôler :

- nom du certificat ;
- chaîne de certification ;
- date de validité ;
- absence d'erreur TLS.

---

## 17. Faire autoriser le site par l'entreprise

Demander l'enregistrement du site :

```text
https://kestra-poc.example.net
```

comme site conforme/autorisé.

Informations généralement utiles à fournir :

```text
Protocole       : HTTPS
Port            : 443
Usage           : POC orchestration Kestra
Hébergement     : Oracle Cloud Infrastructure
Authentification: Basic Authentication Kestra OSS
Données         : données de test uniquement
```

Aucun accès aux URL suivantes n'est nécessaire depuis le poste :

```text
http://<IP_VM>:8080
ssh://<IP_VM>:22
postgresql://<IP_VM>:5432
```

---

## 18. Tester depuis le poste d'entreprise

Ouvrir :

```text
https://kestra-poc.example.net
```

S'authentifier avec :

```text
KESTRA_ADMIN_USERNAME
KESTRA_ADMIN_PASSWORD
```

Le navigateur doit afficher l'IHM Kestra sans avertissement TLS.

---

## 19. Créer un premier flow de validation

Dans Kestra, créer :

```yaml
id: validation_oci
namespace: poc.oci

tasks:
  - id: hello
    type: io.kestra.plugin.core.log.Log
    message: "Kestra OSS fonctionne sur OCI"
```

Enregistrer puis cliquer sur **Execute**.

Résultat attendu :

```text
Status : SUCCESS
```

Le log doit contenir :

```text
Kestra OSS fonctionne sur OCI
```

---

## 20. Tester l'exécution Docker

Créer :

```yaml
id: validation_docker
namespace: poc.oci

tasks:
  - id: test
    type: io.kestra.plugin.scripts.shell.Commands
    containerImage: alpine:latest
    commands:
      - echo "Architecture du worker"
      - uname -m
```

Résultat attendu :

```text
Architecture du worker
aarch64
```

Ce test valide également l'accès au moteur Docker depuis Kestra.

---

## 21. Vérifier PostgreSQL

Depuis la VM :

```bash
cd /opt/kestra
docker compose exec postgres psql -U kestra -d kestra -c '\dt'
```

Des tables Kestra doivent être présentes.

Vérifier la persistance :

```bash
docker compose restart
```

Puis retourner dans l'IHM. Le flow précédemment créé doit toujours exister.

---

## 22. Sauvegarde minimale du POC

Les données persistantes se trouvent dans les volumes Docker :

```text
postgres-data
kestra-storage
```

Sauvegarde PostgreSQL :

```bash
mkdir -p ~/backup
cd /opt/kestra
docker compose exec -T postgres \
  pg_dump -U kestra -d kestra > ~/backup/kestra.sql
```

Vérifier :

```bash
ls -lh ~/backup/kestra.sql
```

Pour un POC, cette sauvegarde est suffisante avant une modification importante.

---

## 23. Commandes d'exploitation utiles

État :

```bash
cd /opt/kestra
docker compose ps
```

Logs Kestra :

```bash
docker compose logs --tail=200 kestra
```

Logs PostgreSQL :

```bash
docker compose logs --tail=200 postgres
```

Redémarrage :

```bash
docker compose restart
```

Arrêt :

```bash
docker compose stop
```

Démarrage :

```bash
docker compose start
```

Mise à jour Kestra :

```bash
docker compose pull kestra
docker compose up -d
```

Pour un POC reproductible, remplacer ultérieurement `latest` par une version Kestra explicitement validée.

---

## 24. Points de vigilance

### Sécurité

Ce POC n'est pas une architecture de production.

En particulier :

- le Docker socket donne des privilèges élevés à Kestra ;
- Kestra et PostgreSQL sont sur la même VM ;
- le stockage interne est local ;
- l'authentification OSS est volontairement simple ;
- la haute disponibilité n'est pas testée par cette installation.

### Architecture ARM64

Certains conteneurs appelés par les flows peuvent ne pas proposer d'image ARM64.

Avant d'utiliser une image :

```bash
docker manifest inspect <IMAGE>
```

Vérifier la présence de :

```text
linux/arm64
```

### Proxy entreprise

Kestra utilise des communications Web longues pour certaines mises à jour temps réel de l'IHM. Si les exécutions fonctionnent mais que l'IHM se rafraîchit mal, vérifier les timeouts et le support des connexions persistantes du proxy d'entreprise et du Load Balancer.

---

## 25. Contrôle des coûts OCI

Après la création du Load Balancer et du certificat, ouvrir :

```text
Billing & Cost Management
 -> Cost Analysis
```

Contrôler qu'aucune ressource payante inattendue n'a été créée.

Les conditions Free Tier, quotas et tarifs OCI peuvent évoluer : toujours vérifier dans la console OCI avant de créer une ressource additionnelle.

---

## 26. Critères de réussite

Le déploiement est considéré comme validé lorsque :

- [ ] PostgreSQL est `healthy` ;
- [ ] Kestra est `Up` ;
- [ ] `http://127.0.0.1:8080` répond depuis la VM ;
- [ ] le backend OCI Load Balancer est `Healthy` ;
- [ ] `https://kestra-poc.example.net` présente un certificat valide ;
- [ ] le FQDN est autorisé depuis le poste d'entreprise ;
- [ ] l'IHM Kestra est accessible uniquement via HTTPS côté utilisateur ;
- [ ] aucun port public `8080` ou `5432` n'est ouvert ;
- [ ] le flow `validation_oci` termine en `SUCCESS` ;
- [ ] le flow `validation_docker` s'exécute ;
- [ ] les données survivent à un redémarrage Docker Compose.

---

## 27. Références officielles

Kestra :

- https://kestra.io/docs/installation/docker
- https://kestra.io/docs/administrator-guide/requirements
- https://kestra.io/docs/configuration

Oracle Cloud Infrastructure :

- https://docs.oracle.com/iaas/Content/Balance/home.htm
- https://docs.oracle.com/iaas/Content/Balance/Tasks/managingcertificates.htm
- https://docs.oracle.com/iaas/Content/KeyManagement/Tasks/managingcertificates.htm
- https://docs.oracle.com/iaas/Content/DNS/home.htm

---

## 28. Résumé

```text
Poste entreprise
   |
   | HTTPS/443
   v
Proxy entreprise
   |
   v
kestra-poc.example.net
   |
   v
OCI Load Balancer
   | 443 TLS termination
   |
   | HTTP/8080
   v
VM.Standard.A1.Flex ARM64
   |
   +-- Kestra OSS
   +-- PostgreSQL 16
   +-- Docker

Administration : OCI Console / Cloud Shell / Bastion
```
