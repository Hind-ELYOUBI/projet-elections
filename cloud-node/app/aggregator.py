"""Agregateur : votes Kafka -> PostgreSQL (UPSERT idempotent : un vote traite
deux fois pendant une bascule ne fausse jamais les totaux)."""
import psycopg
from prometheus_client import Counter, start_http_server
from common import DSN_RW, VOTES_PATTERN, consume

TRAITES = Counter("votes_agreges_total", "Soumissions agregees")

def handle(m):
    with psycopg.connect(DSN_RW) as c:
        for candidat, nb in m["votes"].items():
            c.execute("""INSERT INTO votes (bureau_id, candidat, nb, submitted_at)
                         VALUES (%s, %s, %s, %s)
                         ON CONFLICT (bureau_id, candidat)
                         DO UPDATE SET nb = EXCLUDED.nb, submitted_at = EXCLUDED.submitted_at""",
                      (m["bureau_id"], candidat, nb, m["timestamp"]))
    TRAITES.inc()
    print("agrege", m["bureau_id"], flush=True)

start_http_server(9201)
consume("aggregator", VOTES_PATTERN, handle)
