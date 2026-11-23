"""Simulateur de bureaux de vote (stdlib uniquement).
  python simulator.py https://elections-ingestion.onrender.com            # 48 bureaux normaux
  python simulator.py URL --fraudes                                       # + cas frauduleux/invalides
  python simulator.py URL --boucle                                        # renvoie en continu (demo bascule)
"""
import csv, json, random, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

URL = sys.argv[1].rstrip("/") + "/submit"
CLOTURE = datetime.fromisoformat("2026-11-24T20:00:00+00:00")   # = CLOTURE_UTC du .env
CANDIDATS = ["Liste A", "Liste B", "Liste C"]
bureaux = list(csv.DictReader(open("data/bureaux.csv")))

def envoyer(b, votes, ts=None, token=None):
    body = {"bureau_id": b["bureau_id"], "token": token or b["token"], "votes": votes,
            "timestamp": (ts or datetime.now(timezone.utc)).isoformat()}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(b["bureau_id"], r.status, r.read().decode())
    except urllib.error.HTTPError as e:
        print(b["bureau_id"], e.code, e.read().decode()[:150])

def votes_normaux(b):
    n = int(int(b["inscrits"]) * random.uniform(0.45, 0.75))
    p = [random.random() for _ in CANDIDATS]
    v = {c: int(n * x / sum(p)) for c, x in zip(CANDIDATS, p)}
    return v

def tour():
    for b in bureaux:
        envoyer(b, votes_normaux(b)); time.sleep(0.3)

tour()
if "--fraudes" in sys.argv:
    b = bureaux
    print("\n--- Cas frauduleux / invalides ---")
    envoyer(b[0], {"Liste A": int(b[0]["inscrits"]) + 200, "Liste B": 10, "Liste C": 5})   # surplus
    envoyer(b[9], votes_normaux(b[9]), ts=CLOTURE + timedelta(hours=1))                   # apres cloture
    envoyer(b[17], {"Liste A": 0, "Liste B": 300, "Liste C": 0})                          # unanimite
    envoyer(b[25], {"Liste A": 12.5, "Liste B": 10, "Liste C": 5})                        # decimal -> 422
    envoyer(b[26], {"Liste A": -3, "Liste B": 10, "Liste C": 5})                          # negatif -> 422
    envoyer(b[27], votes_normaux(b[27]), token="faux")                                    # token -> 401
if "--boucle" in sys.argv:
    while True:
        b = random.choice(bureaux); envoyer(b, votes_normaux(b)); time.sleep(1)
