"""Moteur d'anomalies : regles simples, chaque anomalie est enregistree
une seule fois (UNIQUE bureau_id,type) puis publiee dans le topic 'anomalies'."""
import json, os
from datetime import datetime
import psycopg
from confluent_kafka import Producer
from prometheus_client import Counter, start_http_server
from common import DSN_RW, KAFKA, VOTES_PATTERN, consume, parse_ts

CLOTURE = parse_ts(os.environ["CLOTURE_UTC"])
DETECTEES = Counter("anomalies_detectees_total", "Anomalies detectees")
producer = Producer({"bootstrap.servers": KAFKA})
_inscrits = {}

def inscrits(bureau_id):
    if not _inscrits:
        with psycopg.connect(DSN_RW) as c:
            _inscrits.update(c.execute("SELECT bureau_id, inscrits FROM bureaux").fetchall())
    return _inscrits[bureau_id]

def regles(m):
    ins = inscrits(m["bureau_id"])
    total = sum(m["votes"].values())
    ts = parse_ts(m["timestamp"])
    out = []
    if total > ins:
        out.append(("SURPLUS_VOTES", f"{total} votes pour {ins} inscrits"))
    elif total > 0.95 * ins:
        out.append(("PARTICIPATION_SUSPECTE", f"participation de {100*total/ins:.1f} %"))
    if ts > CLOTURE:
        out.append(("VOTE_APRES_CLOTURE", f"soumis a {ts:%H:%M} UTC, cloture a {CLOTURE:%H:%M} UTC"))
    if total >= 50 and max(m["votes"].values()) == total:
        out.append(("UNANIMITE", f"100 % des {total} voix pour un seul candidat"))
    return out

def handle(m):
    found = regles(m)
    if not found:
        return
    with psycopg.connect(DSN_RW) as c:
        for typ, details in found:
            row = c.execute("""INSERT INTO anomalies (bureau_id, type, details) VALUES (%s,%s,%s)
                               ON CONFLICT (bureau_id, type) DO NOTHING RETURNING created_at""",
                            (m["bureau_id"], typ, details)).fetchone()
            if row:  # nouvelle anomalie seulement -> pas de doublon Telegram
                DETECTEES.inc()
                producer.produce("anomalies", json.dumps({
                    "bureau_id": m["bureau_id"], "type": typ, "details": details,
                    "created_at": row[0].isoformat()}).encode())
                print("ANOMALIE", m["bureau_id"], typ, flush=True)
    producer.flush(5)

start_http_server(9202)
consume("anomaly_engine", VOTES_PATTERN, handle)
