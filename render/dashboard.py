"""Dashboard API : lit les resultats et les anomalies sur le cloud actif."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from common import client, cloud_actif

app = FastAPI(title="Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

def lire(chemin):
    try:
        return client.get(cloud_actif()["url"] + chemin).json()
    except Exception as e:
        raise HTTPException(503, str(e))

@app.get("/")
def root():
    return {"service": "dashboard", "ok": True}

@app.get("/api/resultats")
def resultats():
    return lire("/results")

@app.get("/api/anomalies")
def anomalies():
    return lire("/anomalies")

@app.get("/api/etat")
def etat():
    return cloud_actif()
