"""API d'ingestion : authentifie le bureau, valide le format, demande au
Failover Controller quel cloud est actif, puis lui transmet les votes."""
import hashlib, hmac, json, os, time
from datetime import datetime, timezone
from typing import Annotated
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from common import client, cloud_actif

BUREAUX = json.load(open("bureaux_hashes.json"))
CANDIDATS = set(os.environ.get("CANDIDATS", "Liste A,Liste B,Liste C").split(","))
KEY = os.environ["INTERNAL_KEY"]

app = FastAPI(title="API d'ingestion")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Soumission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bureau_id: str
    token: str
    # strict=True : refuse 12.5, "12", true ; ge=0 : refuse les negatifs
    votes: dict[str, Annotated[int, Field(strict=True, ge=0)]]
    timestamp: datetime

@app.get("/")
def root():
    return {"service": "ingestion", "ok": True}

@app.post("/submit")
def submit(s: Soumission):
    attendu = BUREAUX.get(s.bureau_id)
    if not attendu or not hmac.compare_digest(attendu, hashlib.sha256(s.token.encode()).hexdigest()):
        raise HTTPException(401, "Bureau inconnu ou token invalide")
    if set(s.votes) != CANDIDATS:
        raise HTTPException(422, f"Candidats attendus : {sorted(CANDIDATS)}")
    ts = s.timestamp if s.timestamp.tzinfo else s.timestamp.replace(tzinfo=timezone.utc)
    payload = {"bureau_id": s.bureau_id, "votes": s.votes, "timestamp": ts.isoformat()}
    for essai in range(3):
        try:
            actif = cloud_actif()
            r = client.post(f"{actif['url']}/votes", json=payload, headers={"x-internal-key": KEY})
            if r.status_code == 202:
                return {"ok": True, "cloud": actif["cloud"]}
        except Exception as e:
            print("echec envoi", essai, e, flush=True)
        time.sleep(2)
    raise HTTPException(503, "Aucun cloud disponible, reessayez")
