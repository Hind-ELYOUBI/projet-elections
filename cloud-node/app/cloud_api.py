"""API interne du cloud (joignable seulement via Tailscale) :
POST /votes -> Kafka local ; GET /results et /anomalies pour la Dashboard API ;
/metrics pour Prometheus (dont kafka_up et pg_local_leader)."""
import json, os, threading, time
import psycopg
from confluent_kafka import Producer
from fastapi import FastAPI, Header, HTTPException
from prometheus_client import Gauge, make_asgi_app
from common import CLOUD, DSN_RW, KAFKA, local_is_leader

KEY = os.environ["INTERNAL_KEY"]
producer = Producer({"bootstrap.servers": KAFKA, "message.timeout.ms": 5000})
KAFKA_UP = Gauge("kafka_up", "Kafka local joignable")
PG_LEADER = Gauge("pg_local_leader", "Postgres local est primaire")

def sonde():
    while True:
        try:
            producer.list_topics(timeout=3); KAFKA_UP.set(1)
        except Exception:
            KAFKA_UP.set(0)
        PG_LEADER.set(1 if local_is_leader() else 0)
        time.sleep(5)
threading.Thread(target=sonde, daemon=True).start()

app = FastAPI(title=f"cloud-api {CLOUD}")
app.mount("/metrics", make_asgi_app())

@app.get("/health")
def health():
    return {"cloud": CLOUD}

@app.post("/votes", status_code=202)
def votes(m: dict, x_internal_key: str = Header(None)):
    if x_internal_key != KEY:
        raise HTTPException(401)
    producer.produce("votes", key=m["bureau_id"], value=json.dumps(m).encode())
    if producer.flush(5) > 0:
        raise HTTPException(503, "Kafka indisponible")
    return {"cloud": CLOUD}

@app.get("/results")
def results():
    with psycopg.connect(DSN_RW) as c:
        rows = c.execute("SELECT region, candidat, total FROM resultats_region").fetchall()
        remontes = c.execute("SELECT count(DISTINCT bureau_id) FROM votes").fetchone()[0]
        total_b, inscrits = c.execute("SELECT count(*), sum(inscrits) FROM bureaux").fetchone()
    regions, national = {}, {}
    for region, cand, total in rows:
        regions.setdefault(region, {})[cand] = total
        national[cand] = national.get(cand, 0) + total
    return {"cloud": CLOUD, "national": national, "regions": regions,
            "bureaux_remontes": remontes, "bureaux_total": total_b,
            "votants": sum(national.values()), "inscrits": inscrits}

@app.get("/anomalies")
def anomalies():
    with psycopg.connect(DSN_RW) as c:
        rows = c.execute("""SELECT bureau_id, type, details, created_at FROM anomalies
                            ORDER BY created_at DESC LIMIT 50""").fetchall()
    return [{"bureau_id": b, "type": t, "details": d, "created_at": ts.isoformat()}
            for b, t, d, ts in rows]
