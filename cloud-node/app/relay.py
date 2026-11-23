"""Pont Kafka -> Cloudflare Worker (le Worker ne peut ni rejoindre Tailscale
ni parler le protocole Kafka). Ne lit que le topic LOCAL 'anomalies'."""
import os, httpx
from common import consume

URL, SECRET = os.environ["WORKER_URL"], os.environ["WORKER_SECRET"]

def handle(a):
    r = httpx.post(URL, json=a, headers={"x-secret": SECRET}, timeout=10)
    print("telegram", a["bureau_id"], a["type"], r.status_code, flush=True)

consume("relay", "anomalies", handle, only_when_leader=False)
