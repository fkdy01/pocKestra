#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tls_dir="${repo_root}/.kestra-tls"
keystore_password="${KESTRA_SSL_KEYSTORE_PASSWORD:-SECRET_NON_CONFIGURE}"
tls_dns_name="${KESTRA_TLS_DNS_NAME:-localhost}"
tls_ip_address="${KESTRA_TLS_IP_ADDRESS:-127.0.0.1}"

if [[ "${keystore_password}" == "SECRET_NON_CONFIGURE" || ${#keystore_password} -lt 16 ]]; then
  echo "Définir KESTRA_SSL_KEYSTORE_PASSWORD avec au moins 16 caractères." >&2
  exit 1
fi

if [[ ! "${tls_dns_name}" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "KESTRA_TLS_DNS_NAME contient des caractères non autorisés." >&2
  exit 1
fi

if [[ ! "${tls_ip_address}" =~ ^[0-9A-Fa-f:.]+$ ]]; then
  echo "KESTRA_TLS_IP_ADDRESS n'est pas une adresse IP valide pour ce script." >&2
  exit 1
fi

umask 077
mkdir -p "${tls_dir}"

openssl req \
  -x509 \
  -newkey rsa:3072 \
  -sha256 \
  -nodes \
  -days 365 \
  -subj "/CN=POC Kestra local CA/O=POC Kestra local" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -keyout "${tls_dir}/ca.key" \
  -out "${tls_dir}/ca.crt"

openssl req \
  -newkey rsa:3072 \
  -sha256 \
  -nodes \
  -subj "/CN=${tls_dns_name}/O=POC Kestra local" \
  -keyout "${tls_dir}/server.key" \
  -out "${tls_dir}/server.csr"

openssl x509 \
  -req \
  -sha256 \
  -days 365 \
  -in "${tls_dir}/server.csr" \
  -CA "${tls_dir}/ca.crt" \
  -CAkey "${tls_dir}/ca.key" \
  -CAserial "${tls_dir}/ca.srl" \
  -CAcreateserial \
  -extfile <(printf '%s\n' \
    "subjectAltName=DNS:${tls_dns_name},IP:${tls_ip_address}" \
    "basicConstraints=critical,CA:FALSE" \
    "keyUsage=critical,digitalSignature,keyEncipherment" \
    "extendedKeyUsage=serverAuth") \
  -out "${tls_dir}/server.crt"

openssl pkcs12 \
  -export \
  -name kestra-local \
  -inkey "${tls_dir}/server.key" \
  -in "${tls_dir}/server.crt" \
  -certfile "${tls_dir}/ca.crt" \
  -out "${tls_dir}/keystore.p12" \
  -passout "pass:${keystore_password}"

openssl pkcs12 \
  -info \
  -noout \
  -in "${tls_dir}/keystore.p12" \
  -passin "pass:${keystore_password}"

openssl verify \
  -CAfile "${tls_dir}/ca.crt" \
  "${tls_dir}/server.crt"

openssl verify \
  -CAfile "${tls_dir}/ca.crt" \
  -verify_hostname "${tls_dns_name}" \
  "${tls_dir}/server.crt"

openssl verify \
  -CAfile "${tls_dir}/ca.crt" \
  -verify_ip "${tls_ip_address}" \
  "${tls_dir}/server.crt"

echo "Certificat TLS local généré dans ${tls_dir}."
echo "Noms couverts : DNS ${tls_dns_name}, IP ${tls_ip_address}."
echo "Empreinte de l'autorité locale :"
openssl x509 -in "${tls_dir}/ca.crt" -noout -fingerprint -sha256
