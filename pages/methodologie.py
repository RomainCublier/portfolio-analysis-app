"""
Page : Méthodologie — documentation des modèles et indicateurs.
Niveau : investisseur averti / CFA candidat.
"""

import streamlit as st
from config.settings import CSS, C

st.markdown(CSS, unsafe_allow_html=True)

st.markdown("## 📐 Méthodologie")
st.markdown(
    "<p style='color:#8892A0;margin-top:-8px;'>Documentation complète des indicateurs, modèles "
    "et règles de décision utilisés dans QuantDesk.</p>",
    unsafe_allow_html=True,
)

# ─── helper ──────────────────────────────────────────────────────────────────

def section(title: str, tag: str = ""):
    tag_html = (
        f"<span style='background:rgba(37,99,235,0.12);color:#3B82F6;font-size:8px;"
        f"font-weight:700;letter-spacing:0.14em;text-transform:uppercase;padding:2px 8px;"
        f"border-radius:2px;margin-right:10px;'>{tag}</span>"
        if tag else ""
    )
    st.markdown(
        f"<h3 style='border-bottom:1px solid #1C2D45;padding-bottom:8px;margin-top:28px;'>"
        f"{tag_html}{title}</h3>",
        unsafe_allow_html=True,
    )


def formula_box(latex_or_text: str, caption: str = ""):
    st.markdown(
        f"<div style='background:#0C1322;border:1px solid #1C2D45;border-left:3px solid #2563EB;"
        f"border-radius:2px;padding:12px 16px;margin:10px 0;font-family:\"IBM Plex Mono\",monospace;"
        f"color:#E8EDF5;font-size:12px;'>{latex_or_text}</div>"
        + (f"<p style='color:#5A6E82;font-size:11px;margin-top:-4px;'>{caption}</p>" if caption else ""),
        unsafe_allow_html=True,
    )


def verdict_pill(label: str, color: str, desc: str):
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:12px;margin:6px 0;'>"
        f"<span style='background:{color}22;color:{color};padding:2px 10px;border-radius:20px;"
        f"font-size:11px;font-weight:600;min-width:160px;display:inline-block;text-align:center;'>{label}</span>"
        f"<span style='color:#A8B4C4;font-size:12px;'>{desc}</span></div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

tab_tech, tab_fund, tab_verdict, tab_portfolio, tab_limits = st.tabs([
    "Analyse Technique",
    "Analyse Fondamentale",
    "Système de Verdict",
    "Diagnostic Portefeuille",
    "Limites & Sources",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Analyse Technique
# ─────────────────────────────────────────────────────────────────────────────

with tab_tech:

    section("RSI — Relative Strength Index", "Momentum")
    st.markdown("""
Le RSI mesure la **vitesse et l'amplitude des mouvements de prix** sur une fenêtre glissante de 14 séances,
en normalisant le rapport gains/pertes sur une échelle de 0 à 100.
""")
    formula_box(
        "RSI = 100 − 100 / (1 + RS)&nbsp;&nbsp;&nbsp;où RS = Moyenne(gains, 14j) / Moyenne(pertes, 14j)",
        "Wilder (1978). Calcul avec rolling mean simple (Streamlit/pandas)."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Zones d'interprétation**")
        for zone, color, interp in [
            ("≥ 80",    "#EF4444", "Très suracheté — épuisement des acheteurs probable"),
            ("70–79",   "#F59E0B", "Suracheté — prudence, risque de retournement"),
            ("55–69",   "#EAB308", "Momentum haussier — tendance favorable sans excès"),
            ("45–54",   "#5A6E82", "Neutre — pas de signal directionnel"),
            ("30–44",   "#06B6D4", "Pression baissière — surveiller un rebond"),
            ("< 30",    "#10B981", "Très survendu — opportunité de retournement potentiel"),
        ]:
            st.markdown(
                f"<div style='display:flex;gap:10px;align-items:center;padding:4px 0;"
                f"border-bottom:1px solid #0C1322;'>"
                f"<span style='color:{color};font-size:11px;min-width:50px;font-weight:600;"
                f"font-family:IBM Plex Mono,monospace;'>{zone}</span>"
                f"<span style='color:#A8B4C4;font-size:11px;'>{interp}</span></div>",
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown("**Usage dans QuantDesk**")
        st.markdown("""
- RSI ≥ 75 → **−2 points** dans le score de verdict
- RSI ≥ 65 → **−1 point**
- RSI ≤ 28 → **+2 points** (zone d'opportunité)
- RSI ≤ 38 → **+1 point**

Le seuil de 70/30 classique est volontairement élargi à 75/25 pour
réduire les faux signaux sur les titres en forte tendance.
""")

    section("Moyennes Mobiles — MA50 & MA200", "Tendance")
    st.markdown("""
Les moyennes mobiles simples lissent le bruit de cours et révèlent la **tendance structurelle**.
La MA50 capture le momentum intermédiaire ; la MA200 définit la tendance de fond.
""")
    formula_box(
        "MA(n, t) = (1/n) · Σ Pᵢ  pour i de t−n+1 à t",
        "Appliquées sur les prix de clôture ajustés (auto_adjust=True via yfinance)."
    )

    st.markdown("**Configurations reconnues :**")
    configs = [
        ("Golden Cross",       "#10B981", "Prix > MA50 > MA200",         "Configuration haussière de fond. Tendance primaire positive."),
        ("Consolidation",      "#F59E0B", "Prix < MA50, Prix > MA200",   "Correction dans une tendance haussière. Zone de surveillance."),
        ("Bear — sous MA200",  "#EF4444", "Prix < MA200",                "Tendance de fond baissière. Risque de continuation."),
        ("Neutre",             "#EAB308", "Mixte",                       "Pas de signal technique clair."),
    ]
    for label, color, cond, desc in configs:
        st.markdown(
            f"<div style='background:#0C1322;border:1px solid #1C2D45;border-radius:2px;"
            f"padding:10px 14px;margin-bottom:6px;display:flex;gap:14px;align-items:baseline;'>"
            f"<span style='color:{color};font-weight:700;min-width:160px;font-size:12px;'>{label}</span>"
            f"<span style='color:#5A6E82;font-size:11px;min-width:200px;font-family:IBM Plex Mono,monospace;'>{cond}</span>"
            f"<span style='color:#A8B4C4;font-size:11px;'>{desc}</span></div>",
            unsafe_allow_html=True,
        )

    section("Range 52 Semaines", "Position de prix")
    st.markdown("""
Positionne le cours actuel dans l'intervalle **bas–haut des 252 dernières séances**.
Un titre proche de son plus haut annuel témoigne d'un fort momentum mais d'un potentiel de hausse réduit à court terme.
""")
    formula_box(
        "Position = (Prix − Bas 52S) / (Haut 52S − Bas 52S) × 100",
        "Exprimé en %. 100% = au plus haut annuel, 0% = au plus bas annuel."
    )

    section("Momentum de Prix", "Rendement relatif")
    st.markdown("""
Le momentum est mesuré comme le **rendement simple** sur 3, 6 et 12 mois glissants.
Il capture la persistance des tendances, documentée empiriquement depuis Jegadeesh & Titman (1993).
""")
    formula_box(
        "Momentum(n mois) = (P_t / P_{t−n} − 1) × 100   [en %]",
        "Calculé sur les prix de clôture ajustés. 63 séances ≈ 3 mois, 126 ≈ 6 mois, 252 ≈ 1 an."
    )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Analyse Fondamentale
# ─────────────────────────────────────────────────────────────────────────────

with tab_fund:

    section("P/E Ratio — Price to Earnings", "Valorisation")
    st.markdown("""
Le P/E mesure combien le marché paie pour **1 € de bénéfice annuel**.
QuantDesk compare le P/E de chaque titre à la **médiane sectorielle GICS** pour une
évaluation contextuelle (un P/E de 30 est normal pour la tech, excessif pour l'énergie).
""")
    formula_box(
        "P/E = Prix de marché / BPA (Bénéfice par action)\n\nRatio sectoriel = P/E titre / Médiane P/E secteur",
        "Source : trailingPE ou forwardPE via yfinance .info. Médianes : consensus marché 2024."
    )

    st.markdown("**Médianes P/E de référence par secteur :**")
    medians = {
        "Technology": 28, "Healthcare": 23, "Financial Services": 13,
        "Energy": 10, "Utilities": 17, "Consumer Defensive": 22,
        "Consumer Cyclical": 27, "Industrials": 21, "Basic Materials": 18,
        "Real Estate": 38, "Communication Services": 20,
    }
    cols = st.columns(4)
    for i, (sec, pe) in enumerate(medians.items()):
        with cols[i % 4]:
            st.markdown(
                f"<div style='background:#0C1322;border:1px solid #1C2D45;border-radius:2px;"
                f"padding:8px 10px;margin-bottom:4px;'>"
                f"<div style='color:#5A6E82;font-size:9px;text-transform:uppercase;letter-spacing:.08em;'>{sec}</div>"
                f"<div style='color:#E8EDF5;font-size:18px;font-weight:600;font-family:IBM Plex Mono,monospace;'>{pe}×</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    section("P/B Ratio — Price to Book", "Valorisation")
    st.markdown("""
Le P/B compare la valeur de marché aux **actifs nets comptables**.
Un P/B < 1 peut signaler une décote (value trap ou opportunité). Un P/B élevé reflète
souvent des actifs intangibles significatifs (marques, brevets, réseau).
""")
    formula_box("P/B = Capitalisation boursière / Valeur comptable nette (Book Value)")

    section("Marges Opérationnelles & Brutes", "Qualité")
    st.markdown("""
Les marges mesurent la **capacité bénéficiaire** et le **pricing power** d'une entreprise.
""")
    col1, col2 = st.columns(2)
    with col1:
        formula_box(
            "Marge brute = (CA − Coût des ventes) / CA × 100",
            "Reflète le pricing power et l'efficacité de production."
        )
    with col2:
        formula_box(
            "Marge opé. = EBIT / CA × 100",
            "Intègre les coûts de structure (S&M, R&D, G&A)."
        )

    st.markdown("**Seuils d'interprétation (marge opérationnelle) :**")
    for threshold, color, desc in [
        ("> 25%",   "#10B981", "Excellentes — pricing power fort, avantage concurrentiel durable (ex: MSFT ~40%, AAPL ~30%)"),
        ("10–25%",  "#EAB308", "Correctes — rentabilité satisfaisante pour la majorité des secteurs"),
        ("0–10%",   "#F59E0B", "Faibles — sensible aux chocs de coûts, peu de marge de sécurité"),
        ("< 0%",    "#EF4444", "Pertes opérationnelles — modèle économique sous pression"),
    ]:
        st.markdown(
            f"<div style='display:flex;gap:12px;border-bottom:1px solid #0C1322;padding:5px 0;'>"
            f"<span style='color:{color};font-weight:700;min-width:60px;font-family:IBM Plex Mono,monospace;font-size:11px;'>{threshold}</span>"
            f"<span style='color:#A8B4C4;font-size:11px;'>{desc}</span></div>",
            unsafe_allow_html=True,
        )

    section("ROE — Return on Equity", "Rentabilité")
    st.markdown("""
Le ROE mesure combien l'entreprise génère de profit pour chaque euro de capitaux propres.
Un ROE élevé et stable indique une **création de valeur actionnariale** durable.
""")
    formula_box(
        "ROE = Résultat net / Capitaux propres moyens × 100",
        "Interprétation par la décomposition DuPont : ROE = Marge nette × Rotation actifs × Levier financier."
    )

    section("Dette / Capitaux propres", "Solidité bilancielle")
    formula_box(
        "Debt/Equity = Dette financière totale / Capitaux propres × 100",
        "Exprimé en %. Fourni par yfinance (debtToEquity). Peut dépasser 100% pour les secteurs capitalistiques."
    )
    for threshold, color, desc in [
        ("< 30%",     "#10B981", "Bilan solide — résilience maximale en période de stress de taux"),
        ("30–80%",    "#EAB308", "Levier modéré — acceptable dans la plupart des secteurs"),
        ("80–150%",   "#F59E0B", "Levier significatif — surveiller la couverture des intérêts"),
        ("> 150%",    "#EF4444", "Endettement élevé — risque de refinancement et sensibilité aux taux"),
    ]:
        st.markdown(
            f"<div style='display:flex;gap:12px;border-bottom:1px solid #0C1322;padding:5px 0;'>"
            f"<span style='color:{color};font-weight:700;min-width:70px;font-family:IBM Plex Mono,monospace;font-size:11px;'>{threshold}</span>"
            f"<span style='color:#A8B4C4;font-size:11px;'>{desc}</span></div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Système de Verdict
# ─────────────────────────────────────────────────────────────────────────────

with tab_verdict:

    section("Scoring composite par titre", "Algorithme de décision")
    st.markdown("""
Chaque titre reçoit un **score entier** calculé en additionnant des signaux binaires positifs et négatifs.
Quatre critères sont évalués indépendamment ; leur somme détermine le verdict final.
""")

    st.markdown("**Règles de scoring :**")
    rules = [
        ("RSI",        "≥ 75",     "−2", "Surchauffe forte"),
        ("RSI",        "65–74",    "−1", "Légère surchauffe"),
        ("RSI",        "≤ 28",     "+2", "Survente forte (opportunité)"),
        ("RSI",        "29–38",    "+1", "Pression vendeuse (rebond possible)"),
        ("P/E",        "> 2× secteur",  "−2", "Très survalorisé"),
        ("P/E",        "1.5–2× secteur","−1", "Prime notable"),
        ("P/E",        "< 0.65× secteur","+2","Décote attractive"),
        ("P/E",        "0.65–0.8× secteur","+1","Légère décote"),
        ("Momentum 3M","> +25%",   "−1", "Attention prise de profit"),
        ("Momentum 3M","+10 à +25%","+1","Momentum positif"),
        ("ROE",        "> 20%",    "+1", "Création de valeur solide"),
        ("ROE",        "< 0%",     "−1", "Rentabilité compromise"),
    ]

    header = (
        "<div style='display:grid;grid-template-columns:110px 160px 50px 1fr;gap:8px;"
        "padding:5px 0;border-bottom:2px solid #1C2D45;'>"
        "<span style='color:#5A6E82;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.10em;'>Critère</span>"
        "<span style='color:#5A6E82;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.10em;'>Condition</span>"
        "<span style='color:#5A6E82;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.10em;'>Points</span>"
        "<span style='color:#5A6E82;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.10em;'>Interprétation</span>"
        "</div>"
    )
    st.markdown(header, unsafe_allow_html=True)
    for crit, cond, pts, interp in rules:
        color = "#10B981" if pts.startswith("+") else "#EF4444"
        st.markdown(
            f"<div style='display:grid;grid-template-columns:110px 160px 50px 1fr;gap:8px;"
            f"padding:5px 0;border-bottom:1px solid #0C1322;'>"
            f"<span style='color:#A8B4C4;font-size:11px;font-weight:600;'>{crit}</span>"
            f"<span style='color:#5A6E82;font-size:11px;font-family:IBM Plex Mono,monospace;'>{cond}</span>"
            f"<span style='color:{color};font-size:11px;font-weight:700;font-family:IBM Plex Mono,monospace;'>{pts}</span>"
            f"<span style='color:#A8B4C4;font-size:11px;'>{interp}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>**Verdict final selon le score total :**", unsafe_allow_html=True)
    verdicts = [
        ("🟢 Potentiel haussier",       "#10B981", "Score ≥ +3", "Convergence positive. Signaux techniques et fondamentaux alignés."),
        ("🔵 Zone d'intérêt",           "#06B6D4", "Score +1 ou +2", "Profil globalement favorable. Attendre confirmation."),
        ("🟡 Neutre — Juste valeur",    "#EAB308", "Score 0",  "Pas de signal fort. Attendre un catalyseur."),
        ("🟠 Légèrement risqué",        "#F59E0B", "Score −1 ou −2", "Signaux d'alerte. Réduire ou poser un stop."),
        ("🔴 En surchauffe — Prudence", "#EF4444", "Score ≤ −3", "Signaux négatifs multiples. Éviter de renforcer."),
    ]
    for label, color, score_range, desc in verdicts:
        st.markdown(
            f"<div style='background:#0C1322;border:1px solid #1C2D45;border-radius:2px;"
            f"border-left:3px solid {color};padding:10px 14px;margin-bottom:6px;"
            f"display:grid;grid-template-columns:200px 120px 1fr;gap:12px;align-items:center;'>"
            f"<span style='color:{color};font-weight:700;font-size:12px;'>{label}</span>"
            f"<span style='color:#5A6E82;font-size:11px;font-family:IBM Plex Mono,monospace;'>{score_range}</span>"
            f"<span style='color:#A8B4C4;font-size:11px;'>{desc}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Diagnostic Portefeuille
# ─────────────────────────────────────────────────────────────────────────────

with tab_portfolio:

    section("Score de diversification (0–100)", "Algorithme composite")
    st.markdown("""
Le score de diversification est une **moyenne pondérée de trois sous-scores** mesurant
des dimensions orthogonales du risque de concentration.
""")
    formula_box(
        "Score = 0.35 × Score_HHI + 0.35 × Score_Corrélation + 0.30 × Score_Sectoriel",
        "Pondérations calibrées pour refléter l'importance relative de chaque axe de risque."
    )

    section("1. Concentration par ligne — Indice HHI", "Herfindahl-Hirschman")
    st.markdown("""
L'indice HHI (Herfindahl-Hirschman) mesure la **concentration des pondérations**.
Il vaut 1/N pour un portefeuille équipondéré (maximum de dispersion) et 1 pour une position unique.
""")
    formula_box(
        "HHI = Σ wᵢ²   (somme des carrés des poids)\n\n"
        "Score_HHI = (1 − HHI) / (1 − 1/N) × 100   [normalisé 0–100, N = nb titres]",
        "100 = parfaitement équipondéré. 0 = tout dans un seul titre. Source : théorie IO (Hirschman, 1945)."
    )

    section("2. Corrélation moyenne inter-actifs", "Diversification effective")
    st.markdown("""
La corrélation de Pearson mesure la **co-évolution linéaire des rendements journaliers**.
Des corrélations élevées signifient que les actifs réagissent aux mêmes facteurs
(macro, sectoriels) — la diversification est alors illusoire.
""")
    formula_box(
        "ρᵢⱼ = Cov(rᵢ, rⱼ) / (σᵢ · σⱼ)   sur 1 an de rendements journaliers\n\n"
        "Corrélation moyenne = moyenne de tous les ρᵢⱼ (i ≠ j)\n\n"
        "Score_Corrélation = max(0, (1 − max(ρ̄, 0)) × 100)",
        "Calculée via pandas .corr() sur les rendements simples quotidiens."
    )
    st.markdown("**Interprétation :**")
    for threshold, color, interp in [
        ("ρ̄ > 0.70",     "#EF4444", "Diversification cosmétique — vos titres évoluent quasi-ensemble"),
        ("ρ̄ 0.55–0.70",  "#F59E0B", "Diversification partielle — exposition commune aux facteurs macro"),
        ("ρ̄ 0.35–0.55",  "#EAB308", "Diversification raisonnable — facteurs spécifiques importants"),
        ("ρ̄ < 0.35",     "#10B981", "Bonne diversification — faible co-mouvement entre actifs"),
    ]:
        st.markdown(
            f"<div style='display:flex;gap:12px;border-bottom:1px solid #0C1322;padding:5px 0;'>"
            f"<span style='color:{color};font-weight:700;min-width:90px;font-family:IBM Plex Mono,monospace;font-size:11px;'>{threshold}</span>"
            f"<span style='color:#A8B4C4;font-size:11px;'>{interp}</span></div>",
            unsafe_allow_html=True,
        )

    section("3. Concentration sectorielle — HHI sectoriel", "Exposition thématique")
    st.markdown("""
Même logique HHI mais appliquée aux **expositions sectorielles agrégées**.
Un portefeuille avec 70% en technologie a un score sectoriel quasi nul même avec 10 titres.
""")
    formula_box(
        "Exposition_secteur s = Σ wᵢ  pour tous les titres i du secteur s\n\n"
        "Score_Sectoriel = (1 − HHI_sectoriel) / (1 − 1/Ns) × 100   [Ns = nb secteurs]"
    )

    section("Métriques de risque-rendement", "Performance")
    col1, col2 = st.columns(2)
    with col1:
        formula_box(
            "Rendement annualisé = r̄_quotidien × 252\n\nVolatilité annualisée = σ_quotidien × √252",
            "Calculé sur l'historique disponible (max 1 an)."
        )
        formula_box(
            "Sharpe ratio = (Rp − Rf) / σp\n\nRf = 4% (taux sans risque approximatif 2024–2025)",
            "Sharpe > 1 = bon. Sharpe > 2 = excellent. Sharpe < 0 = performance négative ajustée du risque."
        )
    with col2:
        formula_box(
            "Max Drawdown = min((Vt / max(V_s, s≤t)) − 1) × 100",
            "Perte maximale pic-à-creux observée sur la période. Mesure du risque de perte en capital."
        )
        formula_box(
            "Corrélation portefeuille = moyenne des ρᵢⱼ hors diagonale\nde la matrice de corrélation",
            "Affiché dans le KPI strip de la page Portefeuille."
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Limites & Sources
# ─────────────────────────────────────────────────────────────────────────────

with tab_limits:

    section("Sources de données")
    st.markdown("""
| Donnée | Source | Fréquence de mise à jour |
|---|---|---|
| Prix historiques (OHLCV) | Yahoo Finance via `yfinance` | Temps réel différé ~15 min |
| Fondamentaux (P/E, P/B, marges…) | Yahoo Finance `.info` | Trimestriel (mise à jour après résultats) |
| Données sectorielles ETF | Yahoo Finance (ETF tickers) | Quotidien |
| Médianes P/E sectorielles | Consensus marché 2024 | Statique dans le code |

> **Cache** : toutes les requêtes réseau sont mises en cache 30 minutes (`@st.cache_data(ttl=1800)`).
""")

    section("Limites connues")

    limits = [
        ("Décalage des fondamentaux",
         "Les données P/E, marges et dette proviennent du dernier rapport trimestriel publié. "
         "Elles peuvent avoir 1 à 4 mois de décalage par rapport à la réalité économique actuelle."),
        ("RSI sur données journalières",
         "Le RSI est calculé sur des clôtures journalières. Sur des actifs très volatils (small caps, cryptos), "
         "les niveaux de survente/surchauffe peuvent persister longtemps. Le RSI seul n'est pas un signal d'achat/vente."),
        ("Corrélation historique ≠ corrélation future",
         "La matrice de corrélation est calculée sur les 12 derniers mois. En période de crise (mars 2020, 2022), "
         "les corrélations convergent toutes vers 1 — le risque de queue est sous-estimé par cette approche."),
        ("P/E sur bénéfices passés",
         "Le trailing P/E utilise les bénéfices des 12 derniers mois. Pour les entreprises en forte croissance "
         "ou en retournement, le forward P/E (basé sur estimations analystes) est plus pertinent."),
        ("Sharpe avec Rf fixe",
         "Le taux sans risque est fixé à 4% (approximation Fed Funds Rate 2024–2025). Il n'est pas mis à jour "
         "dynamiquement. Les comparaisons de Sharpe sur des périodes de taux très différents sont à relativiser."),
        ("Univers limité aux actions cotées US/internationales sur Yahoo Finance",
         "Les titres non couverts par Yahoo Finance (OTC, certains marchés émergents, obligations) "
         "ne peuvent pas être analysés. L'app retourne une erreur si le ticker est invalide."),
    ]

    for title, desc in limits:
        st.markdown(
            f"<div style='background:#0C1322;border:1px solid #1C2D45;border-left:3px solid #F59E0B;"
            f"border-radius:2px;padding:12px 16px;margin-bottom:8px;'>"
            f"<div style='color:#E8EDF5;font-size:12px;font-weight:600;margin-bottom:4px;'>⚠ {title}</div>"
            f"<div style='color:#A8B4C4;font-size:11px;line-height:1.6;'>{desc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    section("Avertissement réglementaire")
    st.markdown(
        "<div style='background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.25);"
        "border-radius:2px;padding:16px 18px;color:#FCA5A5;font-size:12px;line-height:1.7;'>"
        "<strong>QuantDesk est un outil d'aide à la décision à usage éducatif et analytique.</strong><br>"
        "Les verdicts, scores et recommandations générés par cette application ne constituent pas "
        "un conseil en investissement au sens de la directive MIF II. Ils ne tiennent pas compte "
        "de votre situation patrimoniale, de vos objectifs financiers, ni de votre tolérance au risque personnelle.<br><br>"
        "Toute décision d'investissement doit être prise après analyse approfondie et, le cas échéant, "
        "consultation d'un conseiller en gestion de patrimoine agréé (CIF/AMF)."
        "</div>",
        unsafe_allow_html=True,
    )

    section("Références bibliographiques")
    st.markdown("""
- **Wilder, J.W.** (1978). *New Concepts in Technical Trading Systems*. RSI original.
- **Jegadeesh, N. & Titman, S.** (1993). Returns to Buying Winners and Selling Losers. *Journal of Finance*, 48(1).
- **Hirschman, A.O.** (1945). *National Power and the Structure of Foreign Trade*. Indice HHI.
- **Sharpe, W.F.** (1966). Mutual Fund Performance. *Journal of Business*, 39(S1).
- **Fama, E. & French, K.** (1993). Common Risk Factors in the Returns on Stocks and Bonds. *Journal of Financial Economics*, 33(1).
- **Markowitz, H.** (1952). Portfolio Selection. *Journal of Finance*, 7(1).
- **Graham, B. & Dodd, D.** (1934). *Security Analysis*. P/E et P/B comme métriques de valorisation.
""")
