"""Code partage par l'agregateur, le moteur d'anomalies et le relay."""
import json, os, time
from datetime import datetime, timezone

import psycopg
from confluent_kafka import Consumer

CLOUD = os.environ["CLOUD"]
PW = os.environ["PG_PASSWORD"]
AZ, OR = os.environ["AZURE_IP"], os.environ["ORACLE_IP"]
KAFKA = "localhost:9092"
# Les topics recus via MirrorMaker 2 sont prefixes : azure.votes / oracle.votes
VOTES_PATTERN = r"^(azure\.|oracle\.)?votes$"

DSN_LOCAL = f"host=127.0.0.1 port=5432 dbname=postgres user=postgres password={PW} connect_timeout=3"
# libpq trouve tout seul le leader Patroni (celui qui accepte l'ecriture)
DSN_RW = (f"host={AZ},{OR} port=5432,5432 dbname=postgres user=postgres password={PW} "
          "target_session_attrs=read-write connect_timeout=3")


def local_is_leader() -> bool:
    """Vrai si le PostgreSQL de CE cloud est le primaire Patroni."""
    try:
        with psycopg.connect(DSN_LOCAL) as c:
            return not c.execute("SELECT pg_is_in_recovery()").fetchone()[0]
    except Exception:
        return False


def parse_ts(s: str) -> datetime:
    ts = datetime.fromisoformat(s)
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def consume(group, pattern, handle, only_when_leader=True):
    """Boucle de consommation. Si only_when_leader : ne traite QUE si le
    Postgres local est primaire -> Oracle reste inactif tant qu'Azure va bien."""
    consumer, leader, last_check = None, False, 0.0
    while True:
        if only_when_leader and time.time() - last_check > 5:
            new = local_is_leader()
            if new != leader:
                print(f"[{CLOUD}] {group}: {'ACTIF (leader)' if new else 'en attente'}", flush=True)
            leader, last_check = new, time.time()
        if only_when_leader and not leader:
            if consumer:
                consumer.close(); consumer = None
            time.sleep(2); continue
        if consumer is None:
            consumer = Consumer({"bootstrap.servers": KAFKA, "group.id": group,
                                 "auto.offset.reset": "earliest",
                                 "topic.metadata.refresh.interval.ms": 10000})
            consumer.subscribe([pattern])
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        try:
            handle(json.loads(msg.value()))
        except Exception as e:  # on ne bloque jamais la file
            print(f"erreur {group}: {e}", flush=True)
