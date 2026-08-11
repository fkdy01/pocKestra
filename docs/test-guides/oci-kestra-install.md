# Mode opératoire — Installation de Kestra OSS sur OCI avec PostgreSQL et accès HTTPS

## 1. Objectif

Ce document poursuit le mode opératoire [`oci-vm.md`](./oci-vm.md).

Il décrit l'installation d'un environnement de test **Kestra Open Source** sur la VM OCI créée précédemment, puis sa publication en HTTPS afin qu'il puisse être utilisé depuis un poste d'entreprise dont les accès Web sont limités aux sites HTTPS explicitement autorisés.

L'objectif est d'obtenir le chemin d'accès suivant :

```text
Poste entreprise
      |
      | HTTPS 443
      v
Proxy / filtrage Web entreprise
      |
      | FQDN autorisé
      v
https://kestra-poc.example.net
     