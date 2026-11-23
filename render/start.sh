#!/bin/sh
# Render ne permet pas de VPN classique -> Tailscale en mode "userspace" :
# on joint le reseau prive via un proxy HTTP local (localhost:1055).
mkdir -p /var/run/tailscale
tailscaled --tun=userspace-networking --state=mem: \
  --socket=/var/run/tailscale/tailscaled.sock \
  --outbound-http-proxy-listen=localhost:1055 &
sleep 3
tailscale --socket=/var/run/tailscale/tailscaled.sock up \
  --authkey="$TS_AUTHKEY" --hostname="$TS_HOSTNAME" --accept-dns=false
exec uvicorn "$APP_MODULE":app --host 0.0.0.0 --port "${PORT:-10000}"
