#!/bin/sh
# Genere prometheus.yml et mm2.properties a partir des IP du fichier .env
set -a; . ./.env; set +a
for f in prometheus.yml mm2.properties; do
  envsubst '$AZURE_IP $ORACLE_IP $GCP_IP' < "$f.tpl" > "$f"
done
echo "OK : prometheus.yml et mm2.properties generes"
