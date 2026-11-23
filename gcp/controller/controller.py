"""Failover Controller : ne sonde rien lui-meme, il ecoute le flux d'alertes
de Prometheus (via Alertmanager) et dit a l'API d'ingestion quel cloud est actif."""
import os
from datetime import datetime
from flask import Flask, jsonify, request

URLS = {"azure": f"http://{os.environ['AZURE_IP']}:8000",
        "oracle": f"http://{os.environ['ORACLE_IP']}:8000"}
firing = set()          # alertes de bascule actuellement actives
historique = []
app = Flask(__name__)

def actif():
    return "oracle" if firing else "azure"

@app.post("/alerts")
def alerts():
    avant = actif()
    for a in request.get_json().get("alerts", []):
        lab = a["labels"]
        if lab.get("failover") != "true":
            continue
        (firing.add if a["status"] == "firing" else firing.discard)(lab["alertname"])
    if actif() != avant:
        historique.append({"heure": datetime.utcnow().isoformat(), "de": avant,
                           "vers": actif(), "alertes": sorted(firing)})
        print(f"*** BASCULE {avant} -> {actif()}  alertes={sorted(firing)}", flush=True)
    return "ok"

@app.get("/active")
def active():
    c = actif()
    return jsonify(cloud=c, url=URLS[c], alertes=sorted(firing), historique=historique[-10:])

@app.get("/metrics")
def metrics():
    return f"failover_oracle_actif {1 if actif() == 'oracle' else 0}\n", 200, {"Content-Type": "text/plain"}

app.run(host="0.0.0.0", port=5000)
