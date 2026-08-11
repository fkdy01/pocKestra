# Mode opératoire — Création d'une VM OCI gratuite pour le POC Kestra

## 1. Objectif

Ce document décrit la création d'une machine virtuelle Oracle Cloud Infrastructure (OCI) destinée à héberger un POC **Kestra Open Source**, en privilégiant :

- l'utilisation des ressources **OCI Always Free** ;
- une VM ARM64 suffisamment dimensionnée pour Kestra ;
- l'absence d'exposition directe de Kestra sur Internet en HTTP ;
- un accès utilisateur à terme uniquement en **HTTPS/443** avec un FQDN autorisé par le proxy d'entreprise ;
- une administration de la VM depuis la console OCI / Cloud Shell, afin de ne pas dépendre d'un accès SSH sortant depuis le poste d'entreprise.

> **Important** : les quotas, libellés de console et conditions commerciales OCI peuvent évoluer. Avant création, vérifier que les ressources choisies portent bien la mention **Always Free-eligible / Toujours gratuit admissible** dans la région d'origine du compte.

---

## 2. Architecture cible du POC

```text
                              POSTE ENTREPRISE
                                    |
                                    | HTTPS 443
                                    v
                           Proxy / filtrage Web
                                    |
                                    | FQDN autorisé
                                    v
                         kestra-poc.example.net
                                    |
                                    v
                      +---------------------------+
                      | OCI Load Balancer         |
                      | HTTPS 443                 |
                      | Certificat TLS public     |
                      +-------------+-------------+
                                    |
                                    | HTTP 8080
                                    | réseau OCI
                                    v
              +-------------------------------------------+
              | VM OCI Ampere A1                         |
              | Ubuntu ARM64                             |
              |                                           |
              | Docker                                   |
              | Kestra OSS :8080                         |
              | PostgreSQL :5432                         |
              +-------------------------------------------+
                                    ^
                                    |
                             administration
                                    |
                         OCI Console / Cloud Shell
```

Dans un premier temps, ce mode opératoire crée uniquement la **VM et son réseau**. Le Load Balancer HTTPS, le DNS et l'installation de Kestra pourront être réalisés dans une étape complémentaire.

---

## 3. Dimensionnement retenu

Kestra indique qu'un serveur standalone nécessite au minimum :

- **2 vCPU** ;
- **4 GiB de RAM**.

OCI met actuellement à disposition dans son offre Always Free une allocation Ampere A1 équivalente à :

- **2 OCPU** ;
- **12 Go de mémoire** ;
- architecture **ARM64**.

Les images Docker officielles Kestra sont publiées pour `linux/arm64` et sont donc compatibles avec Ampere A1.

### Configuration proposée

| Élément | Valeur |
|---|---|
| Cloud | Oracle Cloud Infrastructure |
| Shape | `VM.Standard.A1.Flex` |
| Architecture | ARM64 / Ampere |
| OCPU | 2 |
| Mémoire | 12 Go |
| OS | Ubuntu LTS ARM64 |
| Boot volume | 50 Go |
| Usage | POC uniquement |

> Ne pas sélectionner `VM.Standard.E2.1.Micro` pour Kestra : cette forme est trop limitée en mémoire pour respecter le minimum recommandé par Kestra.

---

## 4. Prérequis

Avant de commencer, disposer de :

1. un compte OCI ;
2. l'accès à la région d'origine (*Home Region*) du compte ;
3. les droits permettant de créer :
   - un compartiment ;
   - un VCN ;
   - un subnet ;
   - une VM Compute ;
   - des règles réseau ;
4. idéalement, un nom de domaine permettant ensuite de publier un FQDN de type :

```text
kestra-poc.example.net
```

5. un navigateur depuis lequel l'URL de la console OCI est autorisée par le filtrage Web d'entreprise.

---

# 5. Vérifier les quotas Always Free

Avant de créer la VM :

1. se connecter à la console OCI ;
2. vérifier que l'on se trouve dans la **Home Region** ;
3. ouvrir :

```text
Governance & Administration
  -> Limits, Quotas and Usage
```

4. vérifier les ressources Compute disponibles ;
5. vérifier que l'allocation Ampere A1 n'est pas déjà consommée par d'autres VM.

L'offre Always Free documentée par Oracle correspond actuellement à environ **2 OCPU et 12 Go de RAM** pour les VM `VM.Standard.A1.Flex`.

> La capacité A1 peut être temporairement indisponible dans un Availability Domain. Dans ce cas, essayer un autre Availability Domain de la Home Region avant d'envisager une ressource payante.

---

# 6. Créer un compartiment dédié

Il est recommandé d'isoler le POC Kestra dans un compartiment.

Dans la console :

```text
Identity & Security
  -> Compartments
  -> Create Compartment
```

Renseigner :

| Champ | Valeur proposée |
|---|---|
| Name | `poc-kestra` |
| Description | `POC Kestra Open Source` |
| Parent Compartment | Root Compartment |

Cliquer sur **Create Compartment**.

## Point de contrôle

Le compartiment suivant doit apparaître :

```text
poc-kestra
```

---

# 7. Créer le réseau OCI

Pour un POC, une topologie simple est suffisante.

## 7.1 VCN

Créer :

```text
VCN : vcn-poc-kestra
CIDR : 10.20.0.0/16
```

Depuis :

```text
Networking
  -> Virtual Cloud Networks
  -> Create VCN
```

Paramètres :

| Champ | Valeur |
|---|---|
| Name | `vcn-poc-kestra` |
| CIDR | `10.20.0.0/16` |
| DNS Resolution | activé |

---

## 7.2 Internet Gateway

Créer un Internet Gateway :

```text
igw-poc-kestra
```

Depuis le VCN :

```text
Internet Gateways
  -> Create Internet Gateway
```

L'activer.

---

## 7.3 Route Table

Dans la route table associée au subnet de la VM, ajouter :

```text
Destination CIDR : 0.0.0.0/0
Target           : Internet Gateway
Target name      : igw-poc-kestra
```

Cette route permet notamment à la VM de télécharger les paquets Ubuntu et les images Docker.

---

## 7.4 Subnet

Créer :

```text
subnet-poc-kestra
CIDR : 10.20.10.0/24
```

Paramètres recommandés :

| Champ | Valeur |
|---|---|
| Name | `subnet-poc-kestra` |
| CIDR | `10.20.10.0/24` |
| Type | Regional |
| DNS | activé |

Pour conserver un POC gratuit et simple, la VM peut disposer d'une **adresse IPv4 publique éphémère** pour ses accès Internet sortants.

Cela ne signifie pas que les ports applicatifs doivent être ouverts depuis Internet.

---

# 8. Créer un Network Security Group

Créer un NSG :

```text
nsg-kestra-vm
```

Depuis :

```text
Networking
  -> Virtual Cloud Networks
  -> vcn-poc-kestra
  -> Network Security Groups
```

## 8.1 Principe de sécurité

Au moment de la création initiale, **ne pas ouvrir Kestra 8080 à Internet**.

Ne pas créer de règle :

```text
0.0.0.0/0 -> TCP/8080
```

Ne pas créer non plus, par défaut, de règle :

```text
0.0.0.0/0 -> TCP/22
```

L'administration devra être réalisée via OCI Cloud Shell connecté au réseau privé OCI ou via OCI Bastion.

## 8.2 Règles entrantes initiales

Le NSG peut être créé sans règle publique entrante.

Lorsque le Load Balancer HTTPS sera ajouté, une règle pourra autoriser :

```text
Source : NSG du Load Balancer
Protocol : TCP
Destination port : 8080
```

Ainsi :

```text
Internet X VM:8080
Load Balancer -> VM:8080
```

---

# 9. Créer la VM Compute

Dans la console OCI :

```text
Compute
  -> Instances
  -> Create instance
```

## 9.1 Informations générales

Renseigner :

| Champ | Valeur |
|---|---|
| Name | `vm-kestra-oss-01` |
| Compartment | `poc-kestra` |

---

## 9.2 Image système

Cliquer sur **Change image**.

Choisir de préférence :

```text
Canonical Ubuntu
Ubuntu 24.04 LTS
Architecture : AArch64 / ARM64
```

Si cette version n'est pas proposée, utiliser la version Ubuntu LTS ARM64 la plus récente disponible et supportée dans la région.

> Vérifier impérativement que l'image est compatible avec une shape Ampere A1.

---

## 9.3 Shape

Cliquer sur :

```text
Change shape
```

Puis sélectionner :

```text
Virtual machine
Ampere
VM.Standard.A1.Flex
```

Configurer :

```text
OCPU   : 2
Memory : 12 GB
```

## Point de contrôle

La console doit indiquer que la forme est **Always Free-eligible** ou incluse dans le quota Always Free.

Si ce n'est pas le cas, **ne pas lancer la création** avant d'avoir compris la cause.

---

# 10. Configurer le réseau de la VM

Dans la section Networking :

```text
VCN        : vcn-poc-kestra
Subnet     : subnet-poc-kestra
Private IP : automatique
```

Associer le NSG :

```text
nsg-kestra-vm
```

## Adresse IPv4 publique

Pour ce POC, deux options existent.

### Option A — POC gratuit simple

Activer :

```text
Automatically assign a public IPv4 address
```

La VM obtient une IPv4 publique éphémère.

Cette adresse sert principalement à permettre un accès Internet simple à la VM. Les règles NSG continuent de bloquer les ports non explicitement autorisés.

### Option B — Architecture privée stricte

Désactiver l'adresse publique et utiliser :

- un NAT Gateway pour les flux sortants ;
- OCI Bastion / Cloud Shell Private Networking pour l'administration.

Cette option est plus proche d'une architecture d'entreprise mais peut introduire des ressources supplémentaires susceptibles d'être facturées.

**Pour le POC gratuit, utiliser l'option A.**

---

# 11. Clé SSH

OCI demande une clé SSH lors de la création de l'instance Linux.

Même si le poste d'entreprise n'utilisera pas SSH directement, conserver une clé d'administration.

Deux possibilités :

### Générer une clé depuis OCI

Sélectionner :

```text
Generate a key pair for me
```

Télécharger immédiatement :

```text
Private Key
Public Key
```

Stocker la clé privée dans un emplacement sécurisé.

### Utiliser une clé existante

Sélectionner :

```text
Upload public key files
```

et fournir uniquement la clé publique.

> Ne jamais déposer la clé privée dans le dépôt Git `pocKestra`.

---

# 12. Boot Volume

Conserver :

```text
50 GB
```

Cela est suffisant pour le POC initial Kestra + PostgreSQL.

OCI inclut actuellement jusqu'à 200 Go cumulés de volumes de boot/bloc dans les ressources Always Free de la Home Region.

Ne pas augmenter inutilement la taille du disque.

---

# 13. Créer l'instance

Avant de cliquer sur **Create**, vérifier :

```text
Name        : vm-kestra-oss-01
Shape       : VM.Standard.A1.Flex
OCPU        : 2
RAM         : 12 GB
OS          : Ubuntu ARM64
Disk        : 50 GB
VCN         : vcn-poc-kestra
Subnet      : subnet-poc-kestra
NSG         : nsg-kestra-vm
Kestra 8080 : NON exposé sur Internet
```

Cliquer ensuite sur :

```text
Create
```

Attendre que l'état passe à :

```text
RUNNING
```

---

# 14. Relever les informations de la VM

Dans la page de l'instance, relever :

```text
Display name
Private IPv4
Public IPv4 éventuelle
Availability Domain
Fault Domain
Shape
OCPU
Memory
```

Exemple :

```text
Name       : vm-kestra-oss-01
Private IP : 10.20.10.25
Public IP  : 203.0.113.10
```

> L'adresse publique ci-dessus est un exemple fictif.

---

# 15. Administration depuis un poste d'entreprise limité au HTTPS

Le poste d'entreprise ne doit pas avoir besoin d'ouvrir une connexion SSH directe vers OCI.

Le chemin recommandé est :

```text
Poste entreprise
      |
      | HTTPS/443
      v
Console OCI
      |
      v
OCI Cloud Shell
      |
      | réseau OCI
      v
VM Kestra
```

Le navigateur du poste ne communique donc qu'en HTTPS avec OCI.

---

## 15.1 Ouvrir Cloud Shell

Depuis la console OCI, cliquer sur l'icône :

```text
Cloud Shell
```

Un terminal Linux s'ouvre dans le navigateur.

OCI Cloud Shell propose plusieurs modes réseau, notamment :

- OCI Service Network ;
- Public Network ;
- Private Network Access.

Pour administrer la VM sans publier SSH sur Internet, privilégier **Private Network Access** vers `vcn-poc-kestra` / `subnet-poc-kestra`.

---

## 15.2 Tester la connectivité privée

Depuis Cloud Shell :

```bash
ping 10.20.10.25
```

Le ping peut être bloqué par les règles réseau. Ce n'est pas nécessairement une anomalie.

Tester ensuite TCP/22 si le NSG autorise SSH depuis le réseau Cloud Shell :

```bash
nc -vz 10.20.10.25 22
```

---

## 15.3 Connexion SSH depuis Cloud Shell

Lorsque la clé privée est disponible dans Cloud Shell :

```bash
chmod 600 ~/.ssh/id_rsa
ssh -i ~/.ssh/id_rsa ubuntu@10.20.10.25
```

Selon l'image OCI, l'utilisateur par défaut peut varier. Pour Ubuntu, il est généralement :

```text
ubuntu
```

Une fois connecté :

```bash
hostname
uname -a
free -h
lsblk
```

Vérifier que l'architecture est ARM64 :

```bash
uname -m
```

Résultat attendu :

```text
aarch64
```

---

# 16. Alternative : OCI Bastion

OCI Bastion permet un accès SSH temporaire et contrôlé à une ressource sans endpoint public. Oracle indique que le service Bastion est gratuit pour les comptes gratuits et payants.

Cette option est recommandée si l'on veut supprimer complètement l'adresse publique de la VM dans une évolution ultérieure.

Architecture :

```text
Poste entreprise
      |
      | HTTPS
      v
Console OCI
      |
      v
Cloud Shell
      |
      v
OCI Bastion
      |
      | SSH privé
      v
VM Kestra
```

---

# 17. Préparer l'accès HTTPS à Kestra

L'objectif final n'est pas :

```text
http://IP_VM:8080
```

Le schéma cible est :

```text
https://kestra-poc.example.net
```

sur le port :

```text
443/TCP
```

avec :

- un certificat TLS émis par une autorité reconnue par le poste d'entreprise ;
- un FQDN enregistré comme conforme/autorisé dans le proxy Web de l'entreprise ;
- un Load Balancer OCI ou un reverse proxy HTTPS ;
- Kestra restant sur `8080` dans le réseau OCI.

Le port `8080` ne doit pas être ouvert à `0.0.0.0/0`.

---

# 18. Contrôles de sécurité

À l'issue de la création de la VM, vérifier les points suivants.

## Réseau

- [ ] aucun accès Internet vers TCP/8080 ;
- [ ] aucun accès Internet générique vers TCP/5432 ;
- [ ] PostgreSQL ne sera accessible que localement ou depuis les composants Kestra autorisés ;
- [ ] SSH n'est pas ouvert à `0.0.0.0/0` ;
- [ ] les règles sont portées de préférence par des NSG.

## Système

- [ ] Ubuntu LTS ARM64 ;
- [ ] mises à jour système appliquées ;
- [ ] clé privée SSH non stockée dans Git ;
- [ ] utilisateur `root` non utilisé pour les connexions SSH ;
- [ ] heure système synchronisée.

## Cloud

- [ ] resources dans le compartiment `poc-kestra` ;
- [ ] shape `VM.Standard.A1.Flex` ;
- [ ] 2 OCPU maximum pour ce POC ;
- [ ] 12 Go de RAM maximum pour ce POC ;
- [ ] ressources marquées Always Free lorsque cela s'applique.

---

# 19. Vérifier l'absence de coût inattendu

Après création :

```text
Billing & Cost Management
  -> Cost Analysis
```

Vérifier qu'aucune ressource inattendue n'est facturée.

Contrôler notamment :

- Compute ;
- Block Volume ;
- Load Balancer lorsqu'il sera créé ;
- adresses IP/réseau ;
- stockage ;
- trafic sortant.

Créer si possible une alerte de budget très faible afin d'être averti rapidement en cas de consommation non prévue.

---

# 20. Validation avant installation de Kestra

Depuis la VM :

```bash
uname -m
nproc
free -h
df -h /
curl -I https://registry-1.docker.io
```

Résultats attendus :

```text
Architecture : aarch64
CPU          : 2
RAM          : environ 12 Go
Disk         : environ 50 Go
Internet     : accessible en sortie
```

La VM est alors prête pour l'étape suivante :

```text
Ubuntu ARM64
   -> Docker
   -> PostgreSQL
   -> Kestra OSS
   -> Load Balancer HTTPS
   -> DNS
   -> certificat TLS
```

---

# 21. Dépannage

## 21.1 La shape A1 n'est pas disponible

Symptôme :

```text
Out of host capacity
```

Actions :

1. essayer un autre Availability Domain ;
2. réessayer ultérieurement ;
3. vérifier les limites du compte ;
4. ne pas choisir automatiquement une shape payante sans contrôler son coût.

---

## 21.2 La VM n'accède pas à Internet

Vérifier :

1. présence de l'Internet Gateway ;
2. route :

```text
0.0.0.0/0 -> Internet Gateway
```

3. adresse IPv4 publique éphémère si cette architecture a été retenue ;
4. règles egress du NSG / Security List ;
5. DNS.

Tests :

```bash
ip addr
ip route
curl -I https://www.oracle.com
```

---

## 21.3 Impossible de joindre SSH depuis Cloud Shell

Ne pas ouvrir immédiatement TCP/22 à tout Internet.

Vérifier d'abord :

- le mode réseau Cloud Shell ;
- le subnet sélectionné ;
- les règles NSG ;
- la route entre Cloud Shell et la VM ;
- l'adresse IP privée utilisée.

Tester :

```bash
nc -vz <PRIVATE_IP_VM> 22
```

---

## 21.4 L'accès Kestra est refusé depuis le poste d'entreprise

Avant toute modification côté Kestra, vérifier :

1. que l'accès est bien en HTTPS ;
2. que le certificat TLS est reconnu ;
3. que le FQDN est enregistré comme conforme par l'entreprise ;
4. que le proxy d'entreprise autorise ce FQDN ;
5. que le Load Balancer OCI répond sur 443 ;
6. que son backend Kestra répond sur 8080.

---

# 22. Critère de réussite

Le mode opératoire est considéré comme terminé lorsque :

- la VM `vm-kestra-oss-01` est `RUNNING` ;
- elle utilise `VM.Standard.A1.Flex` ;
- elle dispose de 2 OCPU et 12 Go de RAM ;
- Ubuntu ARM64 est opérationnel ;
- la VM peut accéder à Internet en sortie ;
- Kestra 8080 n'est pas exposé directement sur Internet ;
- l'administration peut être réalisée via les services OCI accessibles en HTTPS depuis le poste d'entreprise ;
- aucune ressource payante inattendue n'a été créée.

---

# 23. Étapes suivantes

Les étapes suivantes du POC sont :

1. installation de Docker ;
2. déploiement de PostgreSQL ;
3. déploiement de Kestra OSS ;
4. création d'un Load Balancer OCI HTTPS ;
5. création du FQDN ;
6. installation du certificat TLS ;
7. demande d'autorisation du FQDN auprès du filtrage Web entreprise ;
8. exécution des scénarios du dépôt `pocKestra`.

---

# 24. Références

Documentation officielle OCI :

- Always Free Resources : https://docs.oracle.com/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Création d'une instance : https://docs.oracle.com/iaas/Content/Compute/Tasks/launchinginstance.htm
- Adresse IPv4 publique lors de la création d'une instance : https://docs.oracle.com/iaas/Content/Network/Tasks/assign-public-ip-instance-launch.htm
- Cloud Shell Networking : https://docs.oracle.com/iaas/Content/API/Concepts/cloudshellintro_topic-Cloud_Shell_Networking.htm
- OCI Bastion : https://docs.oracle.com/iaas/Content/Bastion/home.htm
- Load Balancer : https://docs.oracle.com/iaas/Content/Balance/home.htm

Documentation officielle Kestra :

- Prérequis : https://kestra.io/docs/administrator-guide/requirements
- Installation Docker : https://kestra.io/docs/installation/docker

---

## Résumé des paramètres du POC

```text
COMPARTMENT : poc-kestra
VCN         : vcn-poc-kestra
VCN CIDR    : 10.20.0.0/16
SUBNET      : subnet-poc-kestra
SUBNET CIDR : 10.20.10.0/24
NSG         : nsg-kestra-vm
VM          : vm-kestra-oss-01
SHAPE       : VM.Standard.A1.Flex
OCPU        : 2
RAM         : 12 GB
OS          : Ubuntu LTS ARM64
DISK        : 50 GB
KESTRA      : TCP/8080 interne uniquement
PUBLIC      : HTTPS/443 uniquement via publication dédiée
ADMIN       : OCI Console / Cloud Shell / Bastion
```
