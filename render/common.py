import os, httpx
CONTROLLER = os.environ["CONTROLLER_URL"]          # http://<IP Tailscale GCP>:5000
client = httpx.Client(proxy="http://localhost:1055", timeout=8)

def cloud_actif():
    return client.get(f"{CONTROLLER}/active").json()
