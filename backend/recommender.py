# -*- coding: utf-8 -*-
"""
recommender.py — DashGen v2
Sélection des visualisations + KPI métier + humanisation des labels.
"""
import re
import numpy as np
import pandas as pd

MAX_GRAPHIQUES = 6
MAX_POINTS_SERIE = 200
MAX_POINTS_SCATTER = 500


# ── Humanisation des noms de colonnes ──────────────────────────────────────
def _humaniser(nom: str) -> str:
    """'montant_ttc' → 'Montant TTC' | 'date_commande' → 'Date commande'"""
    s = re.sub(r"[_\-]", " ", nom)
    mots = s.split()
    acronymes = {"ttc", "ht", "ca", "tva", "id", "ref", "num", "pct", "qty", "qte", "pu"}
    return " ".join(m.upper() if m.lower() in acronymes else m.capitalize() for m in mots)


# ── Formatage des valeurs pour les labels ──────────────────────────────────
def _fmt_val(v, compact=True):
    if not isinstance(v, (int, float)) or pd.isna(v):
        return str(v)
    if compact:
        if abs(v) >= 1_000_000:
            return f"{v/1_000_000:.1f} M"
        if abs(v) >= 10_000:
            return f"{v/1_000:.0f} K"
    return f"{v:,.2f}".replace(",", " ").rstrip("0").rstrip(".")


def _fmt_bords(a, b):
    """Formate un intervalle histogramme lisiblement."""
    def f(x):
        if abs(x) >= 1_000_000: return f"{x/1_000_000:.1f}M"
        if abs(x) >= 1_000:     return f"{x/1_000:.1f}K"
        return f"{x:.4g}"
    return f"{f(a)}–{f(b)}"


def _cols_par_type(profil: dict) -> dict:
    groupes = {"date": [], "numerique": [], "categorielle": [], "booleen": []}
    for col, info in profil["colonnes"].items():
        t = info["type"]
        if t in groupes:
            groupes[t].append(col)
    return groupes


def _meilleure_numerique(df: pd.DataFrame, numeriques: list) -> str | None:
    scores = {}
    for c in numeriques:
        s = df[c].dropna()
        if len(s) > 1 and s.mean() != 0:
            scores[c] = abs(s.std() / s.mean())
    return max(scores, key=scores.get) if scores else (numeriques[0] if numeriques else None)


# ── Graphiques ─────────────────────────────────────────────────────────────
def _serie_temporelle(df, col_date, col_num):
    d = df[[col_date, col_num]].dropna()
    if len(d) == 0:
        return None
    etendue = (d[col_date].max() - d[col_date].min()).days
    freq = "D" if etendue <= 92 else ("W" if etendue <= 400 else "ME")
    g = d.set_index(col_date)[col_num].resample(freq).sum().reset_index()
    g = g.tail(MAX_POINTS_SERIE)
    h_num = _humaniser(col_num)
    return {
        "type": "ligne",
        "titre": f"{h_num} dans le temps",
        "raison": f"Colonne date détectée + mesure principale « {h_num} » : "
                  "Idéal pour repérer des tendances, pics ou baisses dans le temps.",
        "x": col_date, "y": col_num,
        "data": [{"x": r[col_date].strftime("%Y-%m-%d"), "y": round(float(r[col_num]), 2)}
                 for _, r in g.iterrows()],
    }


def _barres_categorie(df, col_cat, col_num):
    d = df[[col_cat, col_num]].dropna()
    if len(d) == 0:
        return None
    g = d.groupby(col_cat)[col_num].sum().sort_values(ascending=False).head(12)
    h_cat, h_num = _humaniser(col_cat), _humaniser(col_num)
    return {
        "type": "barres",
        "titre": f"{h_num} par {h_cat}",
        "raison": f"« {h_cat} » a peu de valeurs distinctes : comparer "
                  f"« {h_num} » selon « {h_cat} » pour identifier les plus gros contributeurs.",
        "x": col_cat, "y": col_num,
        "data": [{"x": str(k), "y": round(float(v), 2)} for k, v in g.items()],
    }


def _repartition(df, col_cat):
    s = df[col_cat].dropna()
    if len(s) == 0:
        return None
    g = s.value_counts().head(8)
    autres = len(s) - g.sum()
    # data : x = label string, y = entier → pas de float dans les labels
    data = [{"x": str(k), "y": int(v)} for k, v in g.items()]
    if autres > 0:
        data.append({"x": "Autres", "y": int(autres)})
    h_cat = _humaniser(col_cat)
    return {
        "type": "donut",
        "titre": f"Répartition — {h_cat}",
        "raison": f"« {h_cat} » est catégorielle : sa distribution montre "
                  "Utile pour voir si certaines catégories dominent.",
        "x": col_cat, "y": "effectif",
        "data": data,
    }


def _histogramme(df, col_num):
    s = df[col_num].dropna()
    if len(s) < 5:
        return None
    n_bins = min(15, max(8, int(np.sqrt(len(s)))))
    comptes, bords = np.histogram(s, bins=n_bins)
    h_num = _humaniser(col_num)
    return {
        "type": "histogramme",
        "titre": f"Distribution — {h_num}",
        "raison": f"« {h_num} » est numérique : l'histogramme expose sa forme "
                  "Révèle si les valeurs sont concentrées ou très dispersées.",
        "x": col_num, "y": "effectif",
        "data": [{"x": _fmt_bords(bords[i], bords[i+1]), "y": int(comptes[i])}
                 for i in range(len(comptes))],
    }


def _scatter_correlation(df, numeriques):
    if len(numeriques) < 2:
        return None
    corr = df[numeriques].corr().abs()
    mask = ~np.eye(len(corr), dtype=bool)
    corr = corr.where(mask, 0)
    paire = corr.stack().idxmax()
    valeur = corr.stack().max()
    # Filtre : corrélation triviale (>0.98) ou trop faible (<0.35)
    if pd.isna(valeur) or valeur < 0.35 or valeur > 0.98:
        return None
    c1, c2 = paire
    d = df[[c1, c2]].dropna()
    if len(d) > MAX_POINTS_SCATTER:
        d = d.sample(MAX_POINTS_SCATTER, random_state=42)
    h1, h2 = _humaniser(c1), _humaniser(c2)
    return {
        "type": "scatter",
        "titre": f"{h1} vs {h2}",
        "raison": f"Corrélation de {valeur:.2f} détectée entre ces deux mesures : "
                  "Plus les points forment une ligne, plus les deux mesures évoluent ensemble.",
        "x": c1, "y": c2,
        "data": [{"x": round(float(r[c1]), 3), "y": round(float(r[c2]), 3)}
                 for _, r in d.iterrows()],
    }


# ── KPI métier ─────────────────────────────────────────────────────────────
def kpi_metier(profil: dict) -> list[dict]:
    """KPI contextuels dérivés automatiquement des données."""
    df = profil["_df_converti"]
    g = _cols_par_type(profil)
    kpis = []

    num_principale = _meilleure_numerique(df, g["numerique"])

    # 1. Total + moyenne de la métrique principale
    if num_principale:
        s = df[num_principale].dropna()
        total = s.sum()
        h = _humaniser(num_principale)
        kpis.append({"label": f"Total {h}", "valeur": _fmt_val(total), "brut": float(total)})
        if g["date"]:
            # moyenne par période (semaine si > 3 mois, sinon jour)
            d = df[[g["date"][0], num_principale]].dropna()
            etendue = (d[g["date"][0]].max() - d[g["date"][0]].min()).days
            n_periodes = max(1, etendue // (7 if etendue > 90 else 1))
            moy = total / n_periodes
            label_prd = "/ semaine" if etendue > 90 else "/ jour"
            kpis.append({"label": f"Moy. {h} {label_prd}", "valeur": _fmt_val(moy), "brut": float(moy)})

    # 2. Période couverte + tendance
    if g["date"] and num_principale:
        d = df[[g["date"][0], num_principale]].dropna().set_index(g["date"][0])
        etendue = (d.index.max() - d.index.min()).days
        kpis.append({
            "label": "Période couverte",
            "valeur": f"{d.index.min().strftime('%d/%m/%Y')} → {d.index.max().strftime('%d/%m/%Y')}",
            "brut": etendue,
        })
        # tendance : dernier tiers vs premier tiers
        n = len(d)
        if n >= 6:
            tiers = n // 3
            debut = d.iloc[:tiers][num_principale].sum()
            fin = d.iloc[-tiers:][num_principale].sum()
            if debut > 0:
                delta = (fin - debut) / debut * 100
                fleche = "▲" if delta > 0 else "▼"
                kpis.append({
                    "label": "Tendance globale",
                    "valeur": f"{fleche} {abs(delta):.1f}%",
                    "brut": delta,
                    "positif": bool(delta > 0),
                })

    # 3. Nombre de catégories distinctes (col catégorielle principale)
    if g["categorielle"]:
        col = g["categorielle"][0]
        n = df[col].nunique()
        kpis.append({"label": _humaniser(col), "valeur": f"{n} valeurs distinctes", "brut": n})

    # 4. Complétude globale
    total_cellules = profil["n_lignes"] * profil["n_colonnes"]
    manquantes = sum(i["valeurs_manquantes"] for i in profil["colonnes"].values())
    completude = (1 - manquantes / total_cellules) * 100 if total_cellules else 100
    kpis.append({"label": "Complétude", "valeur": f"{completude:.1f}%", "brut": float(completude)})

    return kpis[:5]


# ── Orchestration ───────────────────────────────────────────────────────────
def recommander(profil: dict) -> list[dict]:
    df = profil["_df_converti"]
    g = _cols_par_type(profil)
    recos = []
    num_principale = _meilleure_numerique(df, g["numerique"])

    if g["date"] and num_principale:
        r = _serie_temporelle(df, g["date"][0], num_principale)
        if r: recos.append(r)

    if num_principale:
        cats_triees = sorted(g["categorielle"], key=lambda c: profil["colonnes"][c]["valeurs_uniques"])
        for cat in cats_triees[:2]:
            r = _barres_categorie(df, cat, num_principale)
            if r: recos.append(r)

    r = _scatter_correlation(df, g["numerique"])
    if r: recos.append(r)

    if num_principale:
        r = _histogramme(df, num_principale)
        if r: recos.append(r)

    if g["categorielle"] and len(recos) < MAX_GRAPHIQUES:
        r = _repartition(df, g["categorielle"][0])
        if r: recos.append(r)

    if g["booleen"] and len(recos) < MAX_GRAPHIQUES:
        r = _repartition(df, g["booleen"][0])
        if r: recos.append(r)

    return recos[:MAX_GRAPHIQUES]


def insights(profil: dict) -> list[dict]:
    df = profil["_df_converti"]
    out = []

    if profil["doublons"]:
        out.append({"niveau": "alerte",
                    "texte": f"{profil['doublons']} lignes dupliquées "
                             f"({profil['doublons']/profil['n_lignes']*100:.1f}% du fichier)."})

    for col, info in profil["colonnes"].items():
        h = _humaniser(col)
        if info["pct_manquants"] > 20:
            out.append({"niveau": "alerte",
                        "texte": f"« {h} » : {info['pct_manquants']}% de valeurs manquantes."})
        if info["type"] == "categorielle" and info.get("top_valeurs"):
            top = info["top_valeurs"][0]
            part = top["n"] / profil["n_lignes"] * 100
            if part > 80:
                out.append({"niveau": "info",
                            "texte": f"« {h} » très déséquilibrée : "
                                     f"« {top['valeur']} » = {part:.0f}% des lignes."})

    numeriques = [c for c, i in profil["colonnes"].items() if i["type"] == "numerique"]
    for c in numeriques:
        s = df[c].dropna()
        if len(s) > 10:
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                outliers = int(((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).sum())
                if outliers > 0:
                    out.append({"niveau": "info",
                                "texte": f"« {_humaniser(c)} » : {outliers} valeurs extrêmes "
                                         "(au-delà de 3×IQR)."})

    if not out:
        out.append({"niveau": "ok", "texte": "Aucun problème de qualité majeur détecté."})
    return out[:5]
