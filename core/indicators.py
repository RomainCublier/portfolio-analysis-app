"""
Indicateurs financiers et système de scoring pour l'aide à la décision.

Conventions de retour
---------------------
Chaque fonction d'interprétation retourne un dict avec AU MINIMUM :
  label   : libellé court
  verdict : alias de label (pour compatibilité pages)
  color   : couleur hex
  text    : explication longue

Les fonctions spécifiques ajoutent des clés supplémentaires documentées inline.
"""

import numpy as np
import pandas as pd


# ── RSI ───────────────────────────────────────────────────────────────────────

def compute_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff().dropna()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-10)
    rsi   = 100 - 100 / (1 + rs)
    vals  = rsi.dropna()
    return float(vals.iloc[-1]) if len(vals) > 0 else 50.0


def interpret_rsi(rsi: float | None) -> dict:
    if rsi is None:
        return {"label": "N/D", "verdict": "N/D", "color": "#7B8EA8",
                "short": "—", "text": "Données RSI indisponibles."}

    if rsi >= 80:
        d = {"label": "Très suracheté",    "color": "#EF4444", "short": "🔴 SURACHETÉ",
             "text": f"RSI à {rsi:.0f} — Zone de danger. Les acheteurs sont épuisés, une correction est probable à court terme."}
    elif rsi >= 70:
        d = {"label": "Suracheté",          "color": "#F59E0B", "short": "🟠 ATTENTION",
             "text": f"RSI à {rsi:.0f} — Signal de surchauffe. Le titre a fortement progressé ; la prudence s'impose."}
    elif rsi >= 55:
        d = {"label": "Momentum haussier",  "color": "#C9A94A", "short": "🟡 HAUSSIER",
             "text": f"RSI à {rsi:.0f} — Dynamique positive sans excès. La tendance est favorable."}
    elif rsi >= 45:
        d = {"label": "Neutre",             "color": "#7B8EA8", "short": "⚪ NEUTRE",
             "text": f"RSI à {rsi:.0f} — Pas de signal directionnel fort. Attendre une confirmation."}
    elif rsi >= 30:
        d = {"label": "Pression baissière", "color": "#06B6D4", "short": "🔵 SURVENDU",
             "text": f"RSI à {rsi:.0f} — Pression vendeuse. Zone à surveiller pour un rebond potentiel."}
    else:
        d = {"label": "Très survendu",      "color": "#22C55E", "short": "🟢 OPPORTUNITÉ",
             "text": f"RSI à {rsi:.0f} — Survente extrême. Historiquement propice à un retournement haussier."}

    d["verdict"] = d["label"]
    return d


# ── Moyennes mobiles ──────────────────────────────────────────────────────────

def ma_signal(price: float | None, ma50: float | None, ma200: float | None) -> dict:
    """
    Retourne un dict avec les clés :
      signal  : texte court du signal (alias label)
      detail  : explication longue (alias text)
      label, text, color
    """
    if price is None or ma50 is None or ma200 is None:
        d = {"label": "N/D", "color": "#7B8EA8",
             "text": "Données de moyennes mobiles insuffisantes (historique < 200 jours)."}
    elif np.isnan(price) or np.isnan(ma50) or np.isnan(ma200):
        d = {"label": "N/D", "color": "#7B8EA8",
             "text": "Données de moyennes mobiles insuffisantes (historique < 200 jours)."}
    else:
        above50  = price > ma50
        above200 = price > ma200
        cross    = ma50 > ma200  # Golden cross si True

        if above50 and above200 and cross:
            d = {"label": "Golden Cross",    "color": "#22C55E",
                 "text": "Au-dessus de la MA50 et MA200 (MA50>MA200). Configuration haussière — tendance de fond positive."}
        elif above200 and not above50:
            d = {"label": "Consolidation",   "color": "#F59E0B",
                 "text": "En dessous de la MA50 mais au-dessus de la MA200. Phase de consolidation, surveiller la reprise."}
        elif not above200:
            d = {"label": "Bear — sous MA200", "color": "#EF4444",
                 "text": "En dessous de la MA200. Tendance de fond baissière — risque de continuation à la baisse."}
        else:
            d = {"label": "Neutre",          "color": "#C9A94A",
                 "text": "Configuration mixte. Pas de signal technique clair dans un sens ou dans l'autre."}

    d["verdict"] = d["label"]
    d["signal"]  = d["label"]
    d["detail"]  = d["text"]
    return d


# ── 52 semaines ───────────────────────────────────────────────────────────────

def position_52w(current: float | None, low: float | None, high: float | None) -> dict:
    if current is None or low is None or high is None:
        return {"pct": 50, "label": "N/D", "verdict": "N/D",
                "color": "#7B8EA8", "interpretation": "Données insuffisantes", "text": ""}
    if high <= low or high <= 0:
        return {"pct": 50, "label": "—", "verdict": "—",
                "color": "#7B8EA8", "interpretation": "—", "text": ""}

    pct           = (current - low) / (high - low) * 100
    dist_from_high = (high - current) / high * 100

    if pct >= 90:
        d = {"label": f"Proche du sommet ({pct:.0f}%)", "color": "#EF4444",
             "text": f"À {dist_from_high:.1f}% de son plus haut 52 semaines — potentiel limité à court terme."}
    elif pct >= 65:
        d = {"label": f"Zone haute ({pct:.0f}%)",       "color": "#F59E0B",
             "text": f"Dans le tiers supérieur de son range annuel. Momentum positif mais vigilance."}
    elif pct >= 35:
        d = {"label": f"Zone médiane ({pct:.0f}%)",     "color": "#C9A94A",
             "text": f"Au milieu de son range 52 semaines. Pas de signal extrême."}
    elif pct >= 15:
        d = {"label": f"Zone basse ({pct:.0f}%)",       "color": "#06B6D4",
             "text": f"Dans le tiers inférieur du range annuel. Rebond possible si les fondamentaux sont intacts."}
    else:
        d = {"label": f"Proche du creux ({pct:.0f}%)", "color": "#22C55E",
             "text": f"À {pct:.0f}% de son plus bas 52 semaines — zone d'accumulation potentielle."}

    d["pct"]            = pct
    d["verdict"]        = d["label"]
    d["interpretation"] = d["label"]
    return d


# ── Valorisation ──────────────────────────────────────────────────────────────

# Médianes P/E par secteur GICS (source : consensus marché 2024)
SECTOR_PE_MEDIANS: dict[str, float] = {
    "Technology":             28,
    "Healthcare":             23,
    "Financial Services":     13,
    "Financials":             13,
    "Energy":                 10,
    "Utilities":              17,
    "Consumer Defensive":     22,
    "Consumer Staples":       22,
    "Consumer Cyclical":      27,
    "Consumer Discretionary": 27,
    "Industrials":            21,
    "Basic Materials":        18,
    "Real Estate":            38,
    "Communication Services": 20,
    "Unknown":                22,
}


def interpret_pe(pe: float | None, sector: str = "Unknown") -> dict:
    """
    Clés retournées : label, verdict, color, text, overvalued (bool), sector_median
    """
    if pe is None or not np.isfinite(pe) or pe <= 0:
        return {"label": "N/D", "verdict": "N/D", "color": "#7B8EA8",
                "text": "P/E non disponible (résultat négatif ou données manquantes).",
                "overvalued": False, "sector_median": SECTOR_PE_MEDIANS.get(sector, 22)}

    median    = SECTOR_PE_MEDIANS.get(sector, SECTOR_PE_MEDIANS["Unknown"])
    ratio     = pe / median
    overvalued = ratio >= 1.5

    if ratio >= 2.5:
        d = {"label": "Très survalorisé", "color": "#EF4444",
             "text": f"P/E de {pe:.1f}x = {ratio:.1f}× la médiane sectorielle ({median}x). Prime extrême — le marché intègre une croissance parfaite."}
    elif ratio >= 1.5:
        d = {"label": "Survalorisé",      "color": "#F59E0B",
             "text": f"P/E de {pe:.1f}x vs {median}x ({sector}). Prime de {(ratio-1)*100:.0f}% — justifiée seulement par une croissance supérieure."}
    elif ratio >= 0.85:
        d = {"label": "Juste valorisé",   "color": "#C9A94A",
             "text": f"P/E de {pe:.1f}x, en ligne avec la médiane sectorielle de {median}x. Valorisation équilibrée."}
    elif ratio >= 0.5:
        d = {"label": "Sous-valorisé",    "color": "#06B6D4",
             "text": f"P/E de {pe:.1f}x vs {median}x. Décote de {(1-ratio)*100:.0f}% — opportunité si les fondamentaux sont intacts."}
    else:
        d = {"label": "Très sous-valorisé", "color": "#22C55E",
             "text": f"P/E de {pe:.1f}x — décote marquée vs secteur. Vérifier l'absence de value trap."}

    d["verdict"]       = d["label"]
    d["overvalued"]    = overvalued
    d["sector_median"] = median
    return d


def interpret_pb(pb: float | None) -> dict:
    """Clés : label, verdict, color, text"""
    if pb is None or not np.isfinite(pb) or pb <= 0:
        return {"label": "N/D", "verdict": "N/D", "color": "#7B8EA8", "text": ""}

    if pb > 10:
        d = {"label": f"P/B {pb:.1f}x — très élevé", "color": "#EF4444",
             "text": f"Valeur de marché = {pb:.0f}× la valeur comptable. Reflète des actifs intangibles significatifs."}
    elif pb > 4:
        d = {"label": f"P/B {pb:.1f}x — élevé",      "color": "#F59E0B",
             "text": "Prime importante sur la valeur comptable — attentes de croissance élevées."}
    elif pb > 1:
        d = {"label": f"P/B {pb:.1f}x — normal",     "color": "#C9A94A",
             "text": "Valorisation raisonnable par rapport aux actifs nets."}
    else:
        d = {"label": f"P/B {pb:.1f}x — sous pair",  "color": "#22C55E",
             "text": "Se négocie en dessous de sa valeur comptable. Signal de détresse ou opportunité profonde."}

    d["verdict"] = d["label"]
    return d


# ── Qualité fondamentale ──────────────────────────────────────────────────────

def interpret_margins(gross_pct: float | None, operating_pct: float | None) -> dict:
    """
    Attend des marges EN POURCENTAGE (0–100), ex: gross=45.2, operating=18.1
    Clés : label, verdict, color, text
    """
    if gross_pct is None or operating_pct is None:
        return {"label": "N/D", "verdict": "N/D", "color": "#7B8EA8", "text": ""}

    # Tolérance : si quelqu'un passe des décimales (0-1), on convertit
    if abs(gross_pct) <= 1.5 and abs(operating_pct) <= 1.5:
        gross_pct     = gross_pct * 100
        operating_pct = operating_pct * 100

    if operating_pct > 25:
        d = {"label": "Marges excellentes", "color": "#22C55E",
             "text": f"Marge brute {gross_pct:.1f}% · Marge opé. {operating_pct:.1f}% — pricing power fort, position concurrentielle solide."}
    elif operating_pct > 10:
        d = {"label": "Marges correctes",   "color": "#C9A94A",
             "text": f"Marge brute {gross_pct:.1f}% · Marge opé. {operating_pct:.1f}% — rentabilité satisfaisante."}
    elif operating_pct > 0:
        d = {"label": "Marges faibles",     "color": "#F59E0B",
             "text": f"Marge opérationnelle de seulement {operating_pct:.1f}% — sensible aux chocs de coûts."}
    else:
        d = {"label": "Pertes opérationnelles", "color": "#EF4444",
             "text": f"Marge opérationnelle négative ({operating_pct:.1f}%). Modèle économique sous pression."}

    d["verdict"] = d["label"]
    return d


def interpret_debt(debt_eq: float | None) -> dict:
    """
    debt_eq en % (ex: 85.0 = 85%).
    Clés : label, verdict, color, text
    """
    if debt_eq is None or not np.isfinite(debt_eq):
        return {"label": "N/D", "verdict": "N/D", "color": "#7B8EA8", "text": ""}

    if debt_eq < 30:
        d = {"label": "Bilan solide",        "color": "#22C55E",
             "text": f"Dette/Equity de {debt_eq:.0f}% — levier très faible, grande résilience en période de stress."}
    elif debt_eq < 80:
        d = {"label": "Levier modéré",       "color": "#C9A94A",
             "text": f"Dette/Equity de {debt_eq:.0f}% — niveau raisonnable dans la plupart des secteurs."}
    elif debt_eq < 150:
        d = {"label": "Levier significatif", "color": "#F59E0B",
             "text": f"Dette/Equity de {debt_eq:.0f}% — surveiller la couverture des intérêts en cas de remontée des taux."}
    else:
        d = {"label": "Endettement élevé",   "color": "#EF4444",
             "text": f"Dette/Equity de {debt_eq:.0f}% — risque financier important, sensible aux conditions de refinancement."}

    d["verdict"] = d["label"]
    return d


# ── Verdict global par action ─────────────────────────────────────────────────

def stock_verdict(
    rsi:         float | None,
    pe:          float | None,
    momentum_3m: float | None,   # en POURCENTAGE, ex: 15.0 = +15 %
    sector:      str   = "Unknown",
    roe:         float | None = None,  # en POURCENTAGE, ex: 18.0 = 18 % ROE
) -> dict:
    """
    Combine tous les signaux en un verdict synthétique actionnable.

    Retourne : icon, label, verdict, color, signals (list[str]), recommendation
    """
    red, green = 0, 0
    signals    = []

    # ── RSI ──
    if rsi is not None and np.isfinite(rsi):
        if rsi >= 75:
            red += 2; signals.append(f"RSI {rsi:.0f} — zone de surchauffe")
        elif rsi >= 65:
            red += 1; signals.append(f"RSI {rsi:.0f} — légère surchauffe")
        elif rsi <= 28:
            green += 2; signals.append(f"RSI {rsi:.0f} — zone de survente (opportunité)")
        elif rsi <= 38:
            green += 1; signals.append(f"RSI {rsi:.0f} — pression vendeuse récente")

    # ── P/E vs médiane sectorielle ──
    if pe is not None and np.isfinite(pe) and pe > 0:
        median = SECTOR_PE_MEDIANS.get(sector, 22)
        ratio  = pe / median
        if ratio > 2.0:
            red += 2; signals.append(f"P/E {pe:.0f}x = {ratio:.1f}× le secteur — très survalorisé")
        elif ratio > 1.5:
            red += 1; signals.append(f"P/E {pe:.0f}x — prime notable vs secteur ({median}x)")
        elif ratio < 0.65:
            green += 2; signals.append(f"P/E {pe:.0f}x — décote attractive vs secteur ({median}x)")
        elif ratio < 0.8:
            green += 1; signals.append(f"P/E {pe:.0f}x — légère décote sectorielle")

    # ── Momentum 3M (valeur en %) ──
    if momentum_3m is not None and np.isfinite(momentum_3m):
        if momentum_3m > 25:
            red += 1; signals.append(f"+{momentum_3m:.0f}% en 3 mois — attention à la prise de profit")
        elif momentum_3m < -20:
            signals.append(f"{momentum_3m:.0f}% en 3 mois — tendance baissière à surveiller")
        elif momentum_3m > 10:
            green += 1; signals.append(f"+{momentum_3m:.0f}% en 3 mois — momentum positif")

    # ── ROE (valeur en %) ──
    if roe is not None and np.isfinite(roe):
        if roe > 20:
            green += 1; signals.append(f"ROE {roe:.0f}% — création de valeur solide")
        elif roe < 0:
            red += 1; signals.append(f"ROE négatif ({roe:.0f}%) — rentabilité compromise")

    # ── Décision ──
    score = green - red
    if score >= 3:
        out = {"label": "Potentiel haussier",       "icon": "🟢", "color": "#22C55E",
               "recommendation": "Les indicateurs techniques et fondamentaux convergent positivement. Le titre mérite une attention particulière."}
    elif score >= 1:
        out = {"label": "Zone d'intérêt",           "icon": "🔵", "color": "#06B6D4",
               "recommendation": "Profil globalement favorable. Surveiller la confirmation technique avant de renforcer."}
    elif score == 0:
        out = {"label": "Neutre — Juste valeur",    "icon": "🟡", "color": "#C9A94A",
               "recommendation": "Pas de signal fort dans un sens ou dans l'autre. Attendre un catalyseur ou une consolidation."}
    elif score >= -2:
        out = {"label": "Légèrement risqué",        "icon": "🟠", "color": "#F59E0B",
               "recommendation": "Quelques signaux d'alerte. Réduire l'exposition ou poser un stop-loss trailing."}
    else:
        out = {"label": "En surchauffe — Prudence", "icon": "🔴", "color": "#EF4444",
               "recommendation": "Signaux négatifs multiples. Éviter de renforcer. Envisager un allègement partiel."}

    out["verdict"] = out["label"]
    out["signals"] = signals if signals else ["Aucun signal particulier détecté."]
    return out


# ── Diversification portefeuille ──────────────────────────────────────────────

def portfolio_diversification(
    weights:    dict[str, float],      # {ticker: poids}  — somme = 1
    corr_matrix: pd.DataFrame,         # index/columns = tickers
    sector_map:  dict[str, str],       # {ticker: secteur}
) -> dict:
    """
    Évalue la diversification sur 3 axes et génère un diagnostic narratif.

    Retourne : score (0-100), narrative, alerts, suggestions, sub_scores, sector_exp
    """
    tickers = list(weights.keys())
    n       = len(tickers)
    w_arr   = np.array([weights[t] for t in tickers])
    w_arr   = w_arr / w_arr.sum()   # re-normalise par sécurité

    # 1. Concentration par ligne (HHI normalisé) — 1 = parfait, 0 = mono
    hhi      = float(np.dot(w_arr, w_arr))
    hhi_norm = (1 - hhi) / (1 - 1 / n) if n > 1 else 0.0
    hhi_score = hhi_norm * 100

    # 2. Corrélation moyenne inter-actifs
    tickers_in_corr = [t for t in tickers if t in corr_matrix.columns]
    if len(tickers_in_corr) >= 2:
        sub_corr  = corr_matrix.loc[tickers_in_corr, tickers_in_corr]
        corr_vals = sub_corr.values.astype(float)
        mask      = ~np.eye(len(corr_vals), dtype=bool)
        off_diag  = corr_vals[mask]
        valid     = off_diag[~np.isnan(off_diag)]          # ignorer les paires sans min_periods
        avg_corr  = float(valid.mean()) if len(valid) > 0 else 0.5
    else:
        avg_corr = 0.5

    corr_score = max(0.0, (1.0 - max(avg_corr, 0)) * 100)

    # 3. Concentration sectorielle
    sec_exp: dict[str, float] = {}
    for t, w in zip(tickers, w_arr):
        sec = sector_map.get(t, "Unknown")
        sec_exp[sec] = sec_exp.get(sec, 0.0) + float(w)

    ns    = len(sec_exp)
    s_arr = np.array(list(sec_exp.values()))
    if ns > 1:
        s_hhi     = float(np.dot(s_arr, s_arr))
        s_norm    = (1 - s_hhi) / (1 - 1 / ns)
        sector_score = s_norm * 100
    else:
        sector_score = 0.0

    # Score composite pondéré
    score = int(hhi_score * 0.35 + corr_score * 0.35 + sector_score * 0.30)
    score = max(0, min(100, score))

    # ── Alertes narratives ──
    alerts      = []
    suggestions = []

    max_w = float(w_arr.max())
    if max_w > 0.35:
        top_t = tickers[int(w_arr.argmax())]
        alerts.append(
            f"{top_t} représente {max_w*100:.0f}% du portefeuille — "
            f"risque idiosyncratique élevé : un événement spécifique à ce titre "
            f"aurait un impact majeur sur l'ensemble."
        )
        suggestions.append("Plafonner chaque ligne à 20–25% maximum pour limiter le risque titre.")

    if sec_exp:
        top_sec = max(sec_exp, key=sec_exp.get)
        top_pct = sec_exp[top_sec] * 100
        if top_pct > 50:
            alerts.append(
                f"{top_pct:.0f}% du portefeuille est dans le secteur «{top_sec}» — "
                f"un choc sectoriel (réglementation, taux, cycle) affecterait la quasi-totalité des positions."
            )
            suggestions.append(
                f"Diversifier hors du secteur «{top_sec}» : ajouter des positions dans des secteurs "
                f"décorrélés (santé, consommation de base, utilities)."
            )

    if avg_corr > 0.70:
        alerts.append(
            f"Corrélation moyenne de {avg_corr:.2f} — vos titres évoluent quasi-ensemble. "
            f"La diversification entre ces actions est essentiellement cosmétique."
        )
        suggestions.append(
            "Intégrer des actifs réellement décorrélés : obligations (AGG/TLT), or (GLD), "
            "immobilier coté (REITs), ou actions de marchés émergents."
        )
    elif avg_corr > 0.55:
        alerts.append(f"Corrélation modérée ({avg_corr:.2f}) — diversification partielle, "
                      f"exposition commune aux facteurs macro (taux, risque US).")

    if n < 5:
        suggestions.append(
            f"Avec seulement {n} positions, le portefeuille reste concentré. "
            f"Viser 8–15 positions pour réduire le risque non-systématique."
        )

    # Valeurs de sécurité pour la narrative
    top_sec  = max(sec_exp, key=sec_exp.get) if sec_exp else "Unknown"
    top_pct_ = sec_exp[top_sec] * 100 if sec_exp else 0.0

    # ── Narrative synthétique ──
    if score >= 75:
        narrative = (
            f"Votre portefeuille affiche un bon niveau de diversification (score {score}/100). "
            f"Les {n} positions sont réparties sur {ns} secteur(s) avec une corrélation "
            f"moyenne de {avg_corr:.2f}. Continuez à surveiller la dérive des pondérations."
        )
    elif score >= 50:
        narrative = (
            f"Diversification correcte mais perfectible (score {score}/100). "
            f"Corrélation moyenne de {avg_corr:.2f} — vos titres partagent des facteurs de risque communs. "
            f"Les améliorations suggérées ci-dessous renforceraient significativement la résilience."
        )
    elif score >= 30:
        narrative = (
            f"Diversification insuffisante (score {score}/100). "
            f"Votre portefeuille est exposé à des risques de concentration importants — "
            f"concentration sectorielle ({top_sec}: {top_pct_:.0f}%) "
            f"et corrélation élevée ({avg_corr:.2f}). Un choc ciblé pourrait impacter l'ensemble."
        )
    else:
        narrative = (
            f"Portefeuille très concentré (score {score}/100). "
            f"Les {n} positions évoluent de concert (corrélation {avg_corr:.2f}) "
            f"et se regroupent dans {ns} secteur(s). Ce n'est pas un portefeuille diversifié "
            f"— c'est un pari directionnel sur un thème unique."
        )

    return {
        "score":        score,
        "narrative":    narrative,          # texte principal
        "alerts":       alerts,
        "suggestions":  suggestions,
        "sub_scores": {
            "hhi_score":    round(hhi_score, 1),
            "corr_score":   round(corr_score, 1),
            "sector_score": round(sector_score, 1),
        },
        "avg_corr":     avg_corr,
        "sector_exp":   sec_exp,
        "n_sectors":    ns,
    }
