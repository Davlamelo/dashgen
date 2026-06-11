# -*- coding: utf-8 -*-
"""
profiler.py — DashGen v4
Détection par nom de colonne d'abord (sémantique), puis règles génériques (structure).
"""
import re
import numpy as np
import pandas as pd

MAX_CAT_UNIQUE = 20

# ────────────────────────────────────────────────────────────────────────────
# DICTIONNAIRES SÉMANTIQUES — basés sur le nom de la colonne
# Ordre = priorité. Le premier match gagne.
# ────────────────────────────────────────────────────────────────────────────

# Identifiants : codes, références, clés
MOTS_IDENTIFIANT = [
    "id", "code", "ref", "num", "no", "numero", "number", "uuid",
    "cle", "key", "identifiant", "matricule", "siret", "siren", "ean",
]

# Texte libre : noms propres, descriptions, commentaires
MOTS_TEXTE = [
    "nom", "prenom", "name", "firstname", "lastname",
    "description", "commentaire", "comment", "note", "remarque",
    "adresse", "address", "email", "mail", "telephone", "phone", "tel",
    "titre", "title", "url", "lien",
]

# Catégorielles : champs à valeurs limitées (même si répétées)
MOTS_CATEGORIELLE = [
    "ville", "city", "pays", "country", "region", "departement", "district",
    "categorie", "category", "type", "genre", "sexe", "gender",
    "statut", "status", "etat", "state",
    "specialite", "specialty", "metier", "fonction", "poste", "role",
    "diagnostic", "marque", "brand", "modele", "model",
    "secteur", "domaine", "famille", "groupe", "classe",
]

# Numériques : mesures, montants, quantités
MOTS_NUMERIQUE = [
    "montant", "prix", "cout", "cost", "price", "amount", "total", "ca",
    "quantite", "quantity", "qte", "qty", "nombre", "count", "stock",
    "age", "taille", "poids", "weight", "duree", "duration",
    "salaire", "revenu", "income", "marge", "benefice", "remise",
    "score", "note", "rating", "pourcentage", "pct", "taux",
]

# Dates
MOTS_DATE = ["date", "jour", "heure", "time", "datetime", "timestamp", "created", "updated"]


def _match_mot(nom: str, liste: list[str]) -> bool:
    """Cherche un mot de la liste dans le nom de colonne (frontières \\b)."""
    nom_norm = nom.lower().strip()
    for mot in liste:
        # frontière : début/fin de chaîne OU séparateur (_, -, espace)
        pattern = rf"(^|[_\-\s]){re.escape(mot)}([_\-\s]|$)"
        if re.search(pattern, nom_norm):
            return True
    return False


def _detecter_par_nom(nom: str) -> str | None:
    """Retourne un type forcé par le nom de colonne, ou None si pas de match.
    Ordre de priorité : identifiant > texte > catégorielle > date > numérique."""
    if not nom:
        return None
    if _match_mot(nom, MOTS_IDENTIFIANT):
        return "identifiant"
    if _match_mot(nom, MOTS_TEXTE):
        return "texte"
    if _match_mot(nom, MOTS_CATEGORIELLE):
        return "categorielle"
    if _match_mot(nom, MOTS_DATE):
        return "date"
    if _match_mot(nom, MOTS_NUMERIQUE):
        return "numerique"
    return None


def _est_sequentiel(s: pd.Series) -> bool:
    if not pd.api.types.is_integer_dtype(s):
        return False
    ratio = s.nunique() / len(s)
    return ratio > 0.85 and s.min() <= 10 and s.max() <= len(s) * 1.5


def detecter_type(serie: pd.Series, nom_col: str = "") -> str:
    s = serie.dropna()
    if len(s) == 0:
        return "vide"

    # ── ÉTAPE 1 : détection sémantique par nom de colonne ───────────────
    type_par_nom = _detecter_par_nom(nom_col)
    if type_par_nom:
        # On valide rapidement la cohérence avec le contenu
        if type_par_nom == "date":
            # Vérifier que ça parse vraiment comme date
            ech = s.astype(str).head(100)
            try:
                parsed = pd.to_datetime(ech, errors="coerce", dayfirst=True, format="mixed")
                if parsed.notna().mean() > 0.85:
                    return "date"
            except (ValueError, TypeError):
                pass
            # sinon : fall through aux règles génériques
        elif type_par_nom == "numerique":
            # Vérifier que c'est bien numérique (sinon fall through)
            if pd.api.types.is_numeric_dtype(s):
                return "numerique"
            ech = s.astype(str).head(100)
            nettoye = (ech.str.replace(r"[\s%€$MAD]", "", regex=True)
                       .str.replace(",", ".", regex=False))
            if pd.to_numeric(nettoye, errors="coerce").notna().mean() > 0.85:
                return "numerique"
        else:
            return type_par_nom

    # ── ÉTAPE 2 : règles génériques basées sur la STRUCTURE ─────────────

    # Colonne constante → numérique si nombre, sinon texte
    if s.nunique() == 1:
        return "numerique" if pd.api.types.is_numeric_dtype(s) else "texte"

    # Booléen strict
    if s.dtype == bool or set(s.unique()).issubset({True, False}):
        return "booleen"
    if (pd.api.types.is_integer_dtype(s) and s.nunique() == 2
            and set(s.unique()).issubset({0, 1})):
        return "booleen"

    # Numérique natif
    if pd.api.types.is_numeric_dtype(s):
        if _est_sequentiel(s):
            return "identifiant"
        if (pd.api.types.is_integer_dtype(s)
                and s.nunique() <= 6 and s.max() <= 20 and s.min() >= 0):
            return "categorielle"
        return "numerique"

    # Date (parsing)
    echantillon = s.astype(str).head(200)
    try:
        parsed = pd.to_datetime(echantillon, errors="coerce",
                                dayfirst=True, format="mixed")
        if parsed.notna().mean() > 0.85:
            return "date"
    except (ValueError, TypeError):
        pass

    # Numérique stocké en texte
    nettoye = (echantillon.str.replace(r"[\s%€$MAD]", "", regex=True)
               .str.replace(",", ".", regex=False))
    if pd.to_numeric(nettoye, errors="coerce").notna().mean() > 0.85:
        return "numerique"

    # Catégorielle si peu de valeurs distinctes
    if s.nunique() <= MAX_CAT_UNIQUE:
        return "categorielle"

    # Identifiant si quasi-unique ET valeurs courtes
    ratio = s.nunique() / len(s)
    longueur_moy = s.astype(str).str.len().mean()
    if ratio > 0.85 and longueur_moy <= 15:
        return "identifiant"

    return "texte"


def convertir(serie: pd.Series, type_detecte: str) -> pd.Series:
    if type_detecte == "date":
        return pd.to_datetime(serie, errors="coerce", dayfirst=True, format="mixed")
    if type_detecte == "numerique" and not pd.api.types.is_numeric_dtype(serie):
        nettoye = (serie.astype(str)
                   .str.replace(r"[\s%€$MAD]", "", regex=True)
                   .str.replace(",", ".", regex=False))
        return pd.to_numeric(nettoye, errors="coerce")
    return serie


def profiler_colonne(serie: pd.Series, type_detecte: str) -> dict:
    n = len(serie)
    manquants = int(serie.isna().sum())
    base = {
        "type": type_detecte,
        "valeurs_manquantes": manquants,
        "pct_manquants": round(manquants / n * 100, 1) if n else 0,
        "valeurs_uniques": int(serie.nunique()),
    }
    s = serie.dropna()
    if len(s) == 0:
        return base

    if type_detecte == "numerique":
        base.update({
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "moyenne": round(float(s.mean()), 2),
            "mediane": round(float(s.median()), 2),
            "ecart_type": round(float(s.std()), 2) if len(s) > 1 else 0,
        })
    elif type_detecte == "date":
        base.update({
            "min": s.min().strftime("%Y-%m-%d"),
            "max": s.max().strftime("%Y-%m-%d"),
            "etendue_jours": int((s.max() - s.min()).days),
        })
    elif type_detecte in ("categorielle", "booleen"):
        top = s.value_counts().head(5)
        base["top_valeurs"] = [
            {"valeur": str(k), "n": int(v)} for k, v in top.items()
        ]
    return base


def profiler(df: pd.DataFrame) -> dict:
    types = {col: detecter_type(df[col], col) for col in df.columns}
    df_conv = df.copy()
    for col, t in types.items():
        df_conv[col] = convertir(df_conv[col], t)

    colonnes = {col: profiler_colonne(df_conv[col], types[col]) for col in df.columns}
    doublons = int(df.duplicated().sum())
    lignes_incompletes = int(df.isna().any(axis=1).sum())

    return {
        "n_lignes": len(df),
        "n_colonnes": len(df.columns),
        "doublons": doublons,
        "lignes_incompletes": lignes_incompletes,
        "colonnes": colonnes,
        "_df_converti": df_conv,
    }
