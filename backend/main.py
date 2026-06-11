# -*- coding: utf-8 -*-
"""
main.py — DashGen API
POST /api/analyze : reçoit un CSV/Excel, retourne profil + graphiques recommandés + insights.
Sert aussi le frontend React buildé (dossier static/) — un seul service à déployer.

Lancement local : uvicorn main:app --reload --port 8000
"""
import io
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from profiler import profiler
from recommender import insights, kpi_metier, recommander

MAX_TAILLE_MO = 10
MAX_LIGNES = 100_000

app = FastAPI(title="DashGen API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # démo publique ; restreindre en production client
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


def lire_fichier(nom: str, contenu: bytes) -> pd.DataFrame:
    """Lit CSV (détection de séparateur) ou Excel."""
    if nom.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(contenu))
    # CSV : détection automatique du séparateur (, ; tab |)
    texte = contenu.decode("utf-8", errors="replace")
    return pd.read_csv(io.StringIO(texte), sep=None, engine="python")


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(400, "Format non supporté. Formats acceptés : CSV, XLSX, XLS.")

    contenu = await file.read()
    if len(contenu) > MAX_TAILLE_MO * 1024 * 1024:
        raise HTTPException(413, f"Fichier trop volumineux (max {MAX_TAILLE_MO} Mo).")

    try:
        df = lire_fichier(file.filename, contenu)
    except Exception:
        raise HTTPException(422, "Impossible de lire le fichier. Vérifiez son format.")

    if df.empty or len(df.columns) == 0:
        raise HTTPException(422, "Le fichier ne contient aucune donnée exploitable.")
    if len(df) > MAX_LIGNES:
        df = df.head(MAX_LIGNES)

    profil = profiler(df)
    graphiques = recommander(profil)
    constats = insights(profil)
    kpis = kpi_metier(profil)
    profil.pop("_df_converti")     # interne, jamais dans la réponse

    apercu = df.head(5).fillna("").astype(str).to_dict(orient="records")

    return {
        "fichier": file.filename,
        "profil": profil,
        "apercu": apercu,
        "graphiques": graphiques,
        "kpis": kpis,
        "insights": constats,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- Frontend React buildé (static/) ----
STATIC = Path(__file__).parent / "static"
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        cible = STATIC / path
        if path and cible.is_file():
            return FileResponse(cible)
        return FileResponse(STATIC / "index.html")
