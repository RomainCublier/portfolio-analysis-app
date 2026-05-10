"""
Page : Mon Portefeuille — diagnostic intelligent de diversification.

Sources méthodologiques :
  • Score HHI          : Hirschman (1945), Herfindahl (1950)
  • Corrélation Pearson : Pearson (1895), appliquée à la finance par Markowitz (1952)
  • Sharpe ratio        : Sharpe (1966), Rf = 4 % (Fed Funds approx. 2024-2025)
  • Sortino ratio        : Sortino & Price (1994)
  • Calmar ratio         : Jones (1991)
  • VaR historique       : simulation historique non-paramétrique (Basel II/III)
  • Beta / Alpha         : CAPM — Sharpe (1964), Lintner (1965), régression OLS vs SPY
  • RSI(14)              : Wilder (1978)
  • P/E sectoriel        : médianes consensus marché 2024
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
from scipy import stats as scipy_stats

from config.settings import CSS, PLOTLY, C, CHART_COLORS, plotly_layout
from config.ticker_meta import TICKER_META
from core.indicators import (
    compute_rsi,
    interpret_rsi,
    interpret_pe,
    stock_verdict,
    portfolio_diversification,
    SECTOR_PE_MEDIANS,
)

st.markdown(CSS, unsafe_allow_html=True)

RF_ANNUAL = 0.04   # Taux sans risque annuel (Fed Funds approximatif)

# ─── helpers ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def load_portfolio_data(tickers_tuple: tuple) -> dict:
    """
    Télécharge 13 mois de prix + fondamentaux pour chaque ticker.
    Utilise TICKER_META comme source primaire pour nom/secteur/pays,
    yfinance .info comme complément pour P/E, P/B, ROE, bêta.
    """
    tickers = list(tickers_tuple)
    end     = datetime.today()
    start   = end - timedelta(days=400)

    # ── Prix historiques ──────────────────────────────────────────────────────
    raw = yf.download(tickers, start=start, end=end,
                      auto_adjust=True, progress=False, group_by="ticker")
    if raw.empty:
        return {}

    # Normaliser le DataFrame selon le nombre de tickers
    if isinstance(raw.columns, pd.MultiIndex):
        # Multi-tickers : raw["Close"] donne un DataFrame avec tickers en colonnes
        prices = raw["Close"].copy()
    else:
        # Un seul ticker
        prices = raw[["Close"]].copy()
        prices.columns = [tickers[0]]

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])

    # Forward-fill pour combler les jours fériés / absences de cotation
    prices = prices.ffill().bfill()
    # Conserver uniquement les lignes où au moins 1 ticker a des données
    prices = prices.dropna(how="all")

    # ── Fondamentaux ──────────────────────────────────────────────────────────
    meta = {}
    for t in tickers:
        static = TICKER_META.get(t.upper(), {})
        try:
            info = yf.Ticker(t).info
            pe_raw = info.get("trailingPE") or info.get("forwardPE")
            roe_raw = info.get("returnOnEquity")
            # yfinance retourne ROE en décimal (ex: 0.18 = 18%) → convertir
            if roe_raw is not None and abs(float(roe_raw)) <= 2.0:
                roe_raw = float(roe_raw) * 100
            meta[t] = {
                "name":    info.get("longName") or info.get("shortName") or static.get("name", t),
                "sector":  info.get("sector")   or static.get("sector",  "Unknown"),
                "country": info.get("country")  or static.get("country", "Unknown"),
                "pe":      float(pe_raw)  if pe_raw  and np.isfinite(float(pe_raw))  else None,
                "pb":      float(info.get("priceToBook")) if info.get("priceToBook") else None,
                "roe":     float(roe_raw) if roe_raw else None,
                "beta":    float(info.get("beta"))        if info.get("beta")        else None,
            }
        except Exception:
            meta[t] = {
                "name":    static.get("name",    t),
                "sector":  static.get("sector",  "Unknown"),
                "country": static.get("country", "Unknown"),
                "pe": None, "pb": None, "roe": None, "beta": None,
            }

    return {"prices": prices, "meta": meta}


@st.cache_data(ttl=1800, show_spinner=False)
def load_benchmark(benchmark: str = "SPY") -> pd.Series:
    """Charge le benchmark (SPY par défaut) pour calculs Alpha/Beta."""
    end   = datetime.today()
    start = end - timedelta(days=400)
    raw   = yf.download(benchmark, start=start, end=end,
                        auto_adjust=True, progress=False)
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.squeeze()
    return close.ffill().dropna()


def _safe_float(v):
    try:
        f = float(v)
        return f if np.isfinite(f) else 0.0
    except Exception:
        return 0.0


def color_score(s: float) -> str:
    if s >= 75: return "#34D399"
    if s >= 55: return C["gold"]
    if s >= 35: return "#F97316"
    return "#EF4444"


def score_label(s: float) -> str:
    if s >= 75: return "Bien diversifié"
    if s >= 55: return "Diversification correcte"
    if s >= 35: return "Diversification insuffisante"
    return "Portefeuille concentré"


def kpi_card(label: str, value: str, color: str, caption: str = "") -> str:
    cap_html = (
        f"<div style='color:#4A5568;font-size:0.62rem;margin-top:3px;"
        f"font-style:italic;line-height:1.3;'>{caption}</div>"
        if caption else ""
    )
    return (
        f"<div style='background:#0C1322;border:1px solid #1C2D45;border-top:2px solid {color};"
        f"border-radius:2px;padding:12px 10px;text-align:center;'>"
        f"<div style='color:#5A6E82;font-size:0.65rem;text-transform:uppercase;"
        f"letter-spacing:0.10em;'>{label}</div>"
        f"<div style='color:{color};font-size:1.35rem;font-weight:700;margin-top:4px;"
        f"font-family:\"IBM Plex Mono\",monospace;'>{value}</div>"
        f"{cap_html}"
        f"</div>"
    )


# ─── Page ────────────────────────────────────────────────────────────────────

st.markdown("## 📊 Mon Portefeuille")
st.markdown(
    "<p style='color:#8892A0;margin-top:-8px;'>Entrez vos positions (ticker Yahoo Finance + montant investi) "
    "pour un diagnostic complet : diversification, risque, performance historique et alertes par titre.</p>",
    unsafe_allow_html=True,
)

# ── Input ─────────────────────────────────────────────────────────────────────

st.markdown("### Positions")

DEFAULT_POSITIONS = pd.DataFrame({
    "Ticker":        ["AAPL",  "MSFT",  "NVDA",  "JPM",  "XOM",  "JNJ",  "AMZN",  "TLT",  "GLD",  "VEA"],
    "Montant (€/$)": [ 5000,    4000,    3500,    2500,   2000,   2000,    3000,   2500,   2000,   1500],
})

positions_df = st.data_editor(
    DEFAULT_POSITIONS,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Ticker":        st.column_config.TextColumn("Ticker (Yahoo Finance)", width="small"),
        "Montant (€/$)": st.column_config.NumberColumn("Montant investi (€/$)", min_value=0, format="%.0f"),
    },
    key="portfolio_editor",
)

col_run, col_hint = st.columns([1, 3])
with col_run:
    run = st.button("Analyser →", use_container_width=True, type="primary")
with col_hint:
    st.markdown(
        "<p style='color:#4A5568;font-size:0.8rem;padding-top:8px;'>"
        "Tickers Yahoo Finance — ex : AAPL, BNP.PA, TTE.PA, SIE.DE, 7203.T</p>",
        unsafe_allow_html=True,
    )

if not run:
    st.info("💡 Renseignez vos positions et cliquez sur **Analyser**.")
    st.stop()

# ── Validation ────────────────────────────────────────────────────────────────

positions_df = positions_df.dropna(subset=["Ticker"])
positions_df["Ticker"]         = positions_df["Ticker"].str.strip().str.upper()
positions_df["Montant (€/$)"]  = positions_df["Montant (€/$)"].apply(_safe_float)
positions_df = positions_df[positions_df["Ticker"].str.len() > 0]
positions_df = positions_df[positions_df["Montant (€/$)"] > 0]

if len(positions_df) < 2:
    st.warning("Au moins 2 positions sont nécessaires pour calculer la diversification.")
    st.stop()

tickers = positions_df["Ticker"].tolist()
amounts = positions_df["Montant (€/$)"].tolist()
total   = sum(amounts)
weights = {t: a / total for t, a in zip(tickers, amounts)}

# ── Chargement données ────────────────────────────────────────────────────────

with st.spinner("Chargement des cours historiques et fondamentaux…"):
    data = load_portfolio_data(tuple(tickers))

if not data or "prices" not in data or data["prices"].empty:
    st.error("Impossible de charger les prix. Vérifiez les tickers (format Yahoo Finance).")
    st.stop()

prices = data["prices"]
meta   = data["meta"]

# Garder uniquement les tickers pour lesquels on a des prix
valid_tickers = [t for t in tickers if t in prices.columns]
missing       = [t for t in tickers if t not in prices.columns]
if missing:
    st.warning(f"Données introuvables pour : {', '.join(missing)}")
if len(valid_tickers) < 2:
    st.error("Données insuffisantes pour au moins 2 titres.")
    st.stop()

prices = prices[valid_tickers].copy()

# Vecteur de poids aligné sur valid_tickers
w_arr  = np.array([weights[t] for t in valid_tickers])
w_arr  = w_arr / w_arr.sum()

# Rendements journaliers — dropna(how='any') sur les séries propres
# On garde les lignes où TOUS les tickers ont des données (calendar alignment)
rets_raw = prices.pct_change()
rets     = rets_raw.dropna(how="any")  # jours avec données complètes
if len(rets) < 30:
    # Fallback : si trop peu de jours complets, remplir avec 0 les trous résiduels
    rets = rets_raw.fillna(0).dropna(how="all")

# Matrice de corrélation (min_periods=30 pour les paires)
corr       = prices.pct_change().corr(min_periods=30)
sector_map = {t: meta[t]["sector"] for t in valid_tickers}

# RSI par position
rsi_map = {t: compute_rsi(prices[t].dropna()) for t in valid_tickers}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Score de Diversification
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Score de Diversification")

with st.expander("ℹ️ Méthodologie du score", expanded=False, icon="▸"):
    st.markdown("""
**Score composite (0–100)** pondéré sur 3 axes indépendants :

| Axe | Poids | Formule |
|---|---|---|
| Concentration (HHI) | 35% | `(1 − Σwᵢ²) / (1 − 1/N) × 100` |
| Corrélation Pearson | 35% | `(1 − ρ̄) × 100` où ρ̄ = corrélation journalière moyenne |
| Concentration sectorielle | 30% | HHI appliqué aux expositions par secteur GICS |

*Sources : Hirschman (1945), Markowitz (1952), Pearson (1895).*
""")

diag = portfolio_diversification(
    weights     = {t: float(w) for t, w in zip(valid_tickers, w_arr)},
    corr_matrix = corr,
    sector_map  = sector_map,
)

score = diag["score"]
clr   = color_score(score)

col_score, col_breakdown = st.columns([1, 2])

with col_score:
    fig_gauge = go.Figure(go.Indicator(
        mode   = "gauge+number",
        value  = score,
        title  = {"text": "Score Global", "font": {"color": "#E2E8F0", "size": 12}},
        number = {"suffix": "/100", "font": {"color": clr, "size": 36}},
        gauge  = {
            "axis": {"range": [0, 100], "tickvals": [0, 35, 55, 75, 100],
                     "ticktext": ["0", "Concentré", "Correct", "Diversifié", "100"],
                     "tickfont": {"color": "#5A6E82", "size": 8}},
            "bar": {"color": clr, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [
                {"range": [0,  35], "color": "#2D1010"},
                {"range": [35, 55], "color": "#2D2010"},
                {"range": [55, 75], "color": "#1E2010"},
                {"range": [75,100], "color": "#0E2018"},
            ],
        },
    ))
    fig_gauge.update_layout(**plotly_layout(height=240, margin=dict(l=10, r=10, t=40, b=0)))
    st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        f"<div style='text-align:center;color:{clr};font-weight:700;font-size:0.95rem;"
        f"margin-top:-8px;'>{score_label(score)}</div>",
        unsafe_allow_html=True,
    )

with col_breakdown:
    sub = diag.get("sub_scores", {})
    captions = {
        "Concentration (HHI)":      "HHI normalisé — 100 = équipondéré",
        "Corrélation inter-actifs":  "Pearson, rendements journaliers",
        "Concentration sectorielle": "HHI sur expositions sectorielles GICS",
    }
    for name_s, key in [
        ("Concentration (HHI)",      "hhi_score"),
        ("Corrélation inter-actifs",  "corr_score"),
        ("Concentration sectorielle", "sector_score"),
    ]:
        s = sub.get(key, 50)
        c = color_score(s)
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>"
            f"<div style='min-width:200px;'>"
            f"<div style='color:#A8B4C4;font-size:0.8rem;'>{name_s}</div>"
            f"<div style='color:#4A5568;font-size:0.68rem;'>{captions[name_s]}</div>"
            f"</div>"
            f"<div style='flex:1;background:#1C2D45;border-radius:2px;height:6px;'>"
            f"<div style='background:{c};width:{s:.0f}%;height:100%;border-radius:2px;'></div></div>"
            f"<span style='color:{c};font-size:0.85rem;font-weight:700;min-width:28px;'>{s:.0f}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='background:#0C1322;border:1px solid #1C2D45;border-left:3px solid {clr};"
        f"border-radius:2px;padding:10px 14px;margin-top:8px;'>"
        f"<p style='color:#A8B4C4;font-size:0.85rem;margin:0;line-height:1.5;'>{diag['narrative']}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

# Alertes et suggestions
for alert in diag.get("alerts", []):
    st.markdown(
        f"<div style='background:rgba(249,115,22,0.06);border:1px solid rgba(249,115,22,0.25);"
        f"border-radius:2px;padding:8px 14px;margin-top:6px;color:#FBD38D;font-size:0.83rem;'>"
        f"⚠ {alert}</div>",
        unsafe_allow_html=True,
    )
for sug in diag.get("suggestions", []):
    st.markdown(
        f"<div style='background:rgba(37,99,235,0.06);border:1px solid rgba(37,99,235,0.20);"
        f"border-radius:2px;padding:8px 14px;margin-top:6px;color:#93C5FD;font-size:0.83rem;'>"
        f"→ {sug}</div>",
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Composition
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Composition")

col_pie1, col_pie2, col_pie3 = st.columns(3)

with col_pie1:
    fig_w = go.Figure(go.Pie(
        labels   = valid_tickers,
        values   = [weights[t] * 100 for t in valid_tickers],
        hole     = 0.55,
        marker   = dict(colors=CHART_COLORS[:len(valid_tickers)],
                        line=dict(color="#060A14", width=2)),
        textinfo = "label+percent",
        textfont = dict(size=10, color="#E2E8F0"),
        hovertemplate = "<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    ))
    fig_w.update_layout(**plotly_layout(
        title=dict(text="Poids par titre", font=dict(size=11)),
        height=280, margin=dict(l=0, r=0, t=35, b=0), showlegend=False,
    ))
    st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})

with col_pie2:
    sector_weights: dict[str, float] = {}
    for t, w in zip(valid_tickers, w_arr):
        s = meta[t]["sector"] if meta[t]["sector"] not in ("Unknown", None, "") else "Non classifié"
        sector_weights[s] = sector_weights.get(s, 0.0) + float(w)

    fig_s = go.Figure(go.Pie(
        labels   = list(sector_weights.keys()),
        values   = [v * 100 for v in sector_weights.values()],
        hole     = 0.55,
        marker   = dict(colors=CHART_COLORS[:len(sector_weights)],
                        line=dict(color="#060A14", width=2)),
        textinfo = "label+percent",
        textfont = dict(size=10, color="#E2E8F0"),
        hovertemplate = "<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    ))
    fig_s.update_layout(**plotly_layout(
        title=dict(text="Exposition sectorielle (GICS)", font=dict(size=11)),
        height=280, margin=dict(l=0, r=0, t=35, b=0), showlegend=False,
    ))
    st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})

with col_pie3:
    country_weights: dict[str, float] = {}
    for t, w in zip(valid_tickers, w_arr):
        c = meta[t]["country"] if meta[t]["country"] not in ("Unknown", None, "") else "Autre"
        country_weights[c] = country_weights.get(c, 0.0) + float(w)

    fig_c = go.Figure(go.Pie(
        labels   = list(country_weights.keys()),
        values   = [v * 100 for v in country_weights.values()],
        hole     = 0.55,
        marker   = dict(colors=CHART_COLORS[:len(country_weights)],
                        line=dict(color="#060A14", width=2)),
        textinfo = "label+percent",
        textfont = dict(size=10, color="#E2E8F0"),
        hovertemplate = "<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    ))
    fig_c.update_layout(**plotly_layout(
        title=dict(text="Exposition géographique", font=dict(size=11)),
        height=280, margin=dict(l=0, r=0, t=35, b=0), showlegend=False,
    ))
    st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Performance & Risque
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Performance & Risque")

# Variables initialisées à None — remplies dans le bloc ci-dessous
port_rets = None
port_vol  = None
port_ret  = None
max_dd    = None
sharpe    = None

if len(rets) < 5:
    st.warning(
        f"Seulement {len(rets)} jours de données communes disponibles. "
        "Vérifiez que vos tickers sont bien cotés (format Yahoo Finance)."
    )
else:
    # ── Rendements pondérés ────────────────────────────────────────────────────
    # Alignement explicite par nom de colonne → pas de risque d'ordre
    port_rets = rets[valid_tickers].dot(w_arr)          # Σ wᵢ × rᵢ,t
    ew_rets   = rets[valid_tickers].mean(axis=1)        # équipondéré (benchmark interne)

    cum_port  = (1 + port_rets).cumprod()
    cum_ew    = (1 + ew_rets).cumprod()

    # ── Graphique performance cumulative ──────────────────────────────────────
    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=cum_port.index, y=(cum_port.values - 1) * 100,
        name="Votre portefeuille",
        line=dict(color=C["gold"], width=2.5),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.06)",
        hovertemplate="%{x|%d %b %Y}<br>%{y:+.2f}%<extra>Portefeuille</extra>",
    ))
    fig_perf.add_trace(go.Scatter(
        x=cum_ew.index, y=(cum_ew.values - 1) * 100,
        name="Equal-weight (ref.)",
        line=dict(color="#5A6E82", width=1.5, dash="dot"),
        hovertemplate="%{x|%d %b %Y}<br>%{y:+.2f}%<extra>Equal-weight</extra>",
    ))
    fig_perf.update_layout(**plotly_layout(
        height=300,
        title=dict(text="Performance cumulative (base 0 %)", font=dict(size=12)),
        yaxis=dict(ticksuffix="%"),
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.08, x=0),
    ))
    st.plotly_chart(fig_perf, use_container_width=True, config={"displayModeBar": False})

    # ── KPIs de base ──────────────────────────────────────────────────────────
    port_vol  = float(port_rets.std() * np.sqrt(252) * 100)       # σ annualisée
    port_ret  = float(port_rets.mean() * 252 * 100)               # μ annualisée
    sharpe    = (port_ret / 100 - RF_ANNUAL) / (port_vol / 100) if port_vol > 0 else 0.0
    max_dd    = float(((cum_port / cum_port.cummax()) - 1).min() * 100)

    # Corrélation moyenne (triangle supérieur de la matrice)
    mask_upper = np.triu(np.ones(corr.shape, dtype=bool), k=1)
    corr_vals  = corr.where(mask_upper).stack()
    avg_corr   = float(corr_vals.mean()) if len(corr_vals) > 0 else 0.0

    cols_k = st.columns(5)
    kpi_data = [
        ("Rend. annualisé", f"{port_ret:+.1f}%",
         C["gold"] if port_ret > 0 else "#EF4444", "μ × 252 j"),
        ("Volatilité ann.", f"{port_vol:.1f}%",
         "#8892A0", "σ × √252"),
        ("Sharpe (Rf=4%)",  f"{sharpe:.2f}",
         C["gold"] if sharpe > 1 else "#8892A0", "(μ−Rf) / σ"),
        ("Max Drawdown",    f"{max_dd:.1f}%",
         "#EF4444", "Perte pic→creux"),
        ("Corr. moy.",      f"{avg_corr:.2f}",
         "#34D399" if avg_corr < 0.5 else "#F97316", "Pearson moy."),
    ]
    for col, (lbl, val, color, cap) in zip(cols_k, kpi_data):
        with col:
            st.markdown(kpi_card(lbl, val, color, cap), unsafe_allow_html=True)

# ── Matrice de corrélation ─────────────────────────────────────────────────────

st.markdown("---")
col_corr, col_alerts = st.columns([3, 2])

with col_corr:
    st.markdown("#### Matrice de Corrélation (Pearson)")
    st.markdown(
        "<p style='color:#5A6E82;font-size:0.75rem;margin-top:-6px;'>"
        "Rendements journaliers sur 13 mois — 1 = parfaitement corrélés, 0 = indépendants, −1 = inversés.</p>",
        unsafe_allow_html=True,
    )
    corr_r = corr.round(2)

    # Palette divergente : bleu foncé (−1) → neutre → or (+1)
    fig_corr = go.Figure(go.Heatmap(
        z            = corr_r.values.tolist(),
        x            = corr_r.columns.tolist(),
        y            = corr_r.index.tolist(),
        colorscale   = [
            [0.0,  "#1A3A5C"],   # −1 : bleu foncé
            [0.5,  "#0C1322"],   # 0  : neutre/sombre
            [1.0,  "#C9A94A"],   # +1 : or
        ],
        zmid=0, zmin=-1, zmax=1,
        text         = corr_r.values.tolist(),
        texttemplate = "%{text:.2f}",
        textfont     = {"size": 11, "color": "#E2E8F0"},
        showscale    = True,
        colorbar     = dict(
            tickfont=dict(color="#5A6E82", size=9),
            outlinewidth=0, thickness=10, len=0.8,
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1", "-0.5", "0", "+0.5", "+1"],
        ),
    ))
    fig_corr.update_layout(**plotly_layout(
        height=max(280, 50 * len(valid_tickers)),
        margin=dict(l=0, r=40, t=10, b=0),
        xaxis=dict(tickfont=dict(size=11), side="bottom"),
        yaxis=dict(tickfont=dict(size=11), autorange="reversed"),
    ))
    st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})

with col_alerts:
    st.markdown("#### Alertes par Titre")
    st.markdown(
        "<p style='color:#5A6E82;font-size:0.75rem;margin-top:-6px;'>"
        "RSI(14) Wilder · P/E vs médiane sectorielle GICS</p>",
        unsafe_allow_html=True,
    )

    for t in valid_tickers:
        rsi = rsi_map.get(t)
        pe  = meta[t]["pe"]
        v   = stock_verdict(rsi, pe, None, meta[t]["sector"], meta[t]["roe"])

        rsi_interp    = interpret_rsi(rsi) if rsi else {"label": "N/D", "color": "#5A6E82"}
        has_rsi_alert = rsi is not None and (rsi > 70 or rsi < 30)
        pe_interp     = interpret_pe(pe, meta[t]["sector"])
        has_pe_alert  = pe_interp.get("overvalued", False)

        alert_color = "#EF4444" if (has_rsi_alert or has_pe_alert) else "#34D399"
        icon        = "●"

        lines = []
        if has_rsi_alert:
            lines.append(f"RSI {rsi:.0f} — {rsi_interp['label']}")
        if has_pe_alert:
            pe_med = SECTOR_PE_MEDIANS.get(meta[t]["sector"], 22)
            lines.append(f"P/E {pe:.0f}x vs médiane {pe_med}x")
        txt = " · ".join(lines) if lines else "Aucune alerte"

        w_pct = weights.get(t, 0) * 100
        st.markdown(
            f"<div style='background:#0C1322;border:1px solid #1C2D45;border-left:3px solid {alert_color};"
            f"border-radius:2px;padding:8px 12px;margin-bottom:6px;'>"
            f"<div style='display:flex;justify-content:space-between;'>"
            f"<span style='color:#E2E8F0;font-size:0.85rem;font-weight:600;'>"
            f"<span style='color:{alert_color};margin-right:6px;'>{icon}</span>{t}</span>"
            f"<span style='color:#5A6E82;font-size:0.75rem;'>{w_pct:.1f}%</span>"
            f"</div>"
            f"<div style='color:#5A6E82;font-size:0.75rem;margin-top:3px;'>{txt}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Métriques de risque avancées (vs SPY)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Métriques de Risque Avancées")
st.markdown(
    "<p style='color:#5A6E82;font-size:0.78rem;margin-top:-6px;'>"
    "Benchmark : SPY (SPDR S&P 500). Taux sans risque Rf = 4 % (Fed Funds 2024-2025).</p>",
    unsafe_allow_html=True,
)

with st.expander("ℹ️ Définitions des indicateurs", expanded=False, icon="▸"):
    st.markdown(f"""
| Indicateur | Formule | Source |
|---|---|---|
| **Beta** | Cov(rₚ, rₘ) / Var(rₘ) — régression OLS | CAPM (Sharpe 1964, Lintner 1965) |
| **Alpha annualisé** | (rₚ̄ − β × rₘ̄) × 252 | Régression CAPM |
| **VaR 95 % (1j)** | Percentile 5 % des rendements journaliers | Simulation historique — Basel II/III |
| **CVaR 95 % (1j)** | Moyenne des rendements < VaR | Expected Shortfall — Acerbi & Tasche (2002) |
| **Sortino** | (μ − Rf) / σ_down, σ_down = σ(r < 0) × √252 | Sortino & Price (1994) |
| **Calmar** | μ_annualisé / \\|Max Drawdown\\| | Jones (1991) |
| **Tracking Error** | σ(rₚ − rₘ) × √252 | Active management |
| **Info. Ratio** | (μₚ − μₘ) × 252 / Tracking Error | Grinold & Kahn (1995) |

*Rf = {RF_ANNUAL*100:.0f} %. Tous les rendements annualisés supposent 252 jours de cotation.*
""")

if port_rets is None:
    st.info("Calcul indisponible — données de performance insuffisantes (voir section précédente).")
else:
    # Chargement SPY
    spy_close = load_benchmark("SPY")
    spy_rets  = spy_close.pct_change().dropna()

    common_idx = port_rets.index.intersection(spy_rets.index)

    if len(common_idx) < 30:
        st.warning(
            f"Seulement {len(common_idx)} jours en commun avec SPY "
            "(données insuffisantes pour le calcul Alpha/Beta)."
        )
    else:
        p_al = port_rets.loc[common_idx].values
        b_al = spy_rets.loc[common_idx].values

        # Beta & Alpha (OLS — scipy)
        slope, intercept, r_value, _, _ = scipy_stats.linregress(b_al, p_al)
        beta    = float(slope)
        alpha_a = float(intercept) * 252 * 100   # annualisé en %
        r2      = float(r_value ** 2)

        # VaR & CVaR historique
        var_level = np.percentile(port_rets.values, 5)
        var_95    = float(var_level * 100)
        cvar_95   = float(port_rets[port_rets <= var_level].mean() * 100)

        # Sortino
        down_rets = port_rets[port_rets < 0]
        down_vol  = float(down_rets.std() * np.sqrt(252) * 100) if len(down_rets) > 5 else port_vol
        sortino   = (port_ret / 100 - RF_ANNUAL) / (down_vol / 100) if down_vol > 0 else 0.0

        # Calmar
        calmar = (port_ret / 100) / abs(max_dd / 100) if max_dd and max_dd != 0 else 0.0

        # Tracking Error & Information Ratio
        active   = port_rets.loc[common_idx] - spy_rets.loc[common_idx]
        te       = float(active.std() * np.sqrt(252) * 100)
        spy_ret  = float(b_al.mean() * 252 * 100)
        ir       = (port_ret - spy_ret) / te if te > 0 else 0.0

        # ── Affichage KPIs avancés ─────────────────────────────────────────────
        adv = [
            ("Beta (vs SPY)",   f"{beta:.2f}",
             "#34D399" if beta < 0.9 else "#5A6E82" if beta < 1.1 else "#EF4444",
             "β < 1 = moins volatile que le marché"),
            ("Alpha annualisé", f"{alpha_a:+.1f}%",
             C["gold"] if alpha_a > 0 else "#EF4444",
             f"R² = {r2:.2f}"),
            ("VaR 95 % (1j)",   f"{var_95:.2f}%",
             "#EF4444", "Perte max probable 1j/20"),
            ("CVaR 95 % (1j)",  f"{cvar_95:.2f}%",
             "#EF4444", "Perte moy. au-delà du VaR"),
            ("Sortino",         f"{sortino:.2f}",
             C["gold"] if sortino > 1.5 else "#5A6E82",
             "(μ−Rf) / σ_downside"),
            ("Calmar",          f"{calmar:.2f}",
             C["gold"] if calmar > 0.5 else "#5A6E82",
             "μ / |Max Drawdown|"),
            ("Tracking Error",  f"{te:.1f}%",
             "#5A6E82", "σ(rₚ − rSPY) × √252"),
            ("Info. Ratio",     f"{ir:.2f}",
             C["gold"] if ir > 0.5 else "#5A6E82",
             "(μₚ − μSPY) / TE"),
        ]

        cols_adv = st.columns(4)
        for i, (lbl, val, color, cap) in enumerate(adv):
            with cols_adv[i % 4]:
                st.markdown(kpi_card(lbl, val, color, cap), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Rolling Sharpe 3M ─────────────────────────────────────────────────
        roll_sharpe = port_rets.rolling(63).apply(
            lambda x: (x.mean() * 252 - RF_ANNUAL) / (x.std() * np.sqrt(252))
            if x.std() > 0 else 0.0,
            raw=True,
        ).dropna()

        if len(roll_sharpe) > 10:
            fig_rs = go.Figure()
            fig_rs.add_hrect(y0=-10, y1=0,
                             fillcolor="rgba(239,68,68,0.04)", line_width=0)
            fig_rs.add_hrect(y0=0, y1=1,
                             fillcolor="rgba(245,158,11,0.03)", line_width=0)
            fig_rs.add_hrect(y0=1, y1=10,
                             fillcolor="rgba(52,211,153,0.03)", line_width=0)
            fig_rs.add_hline(y=1.0, line_dash="dot", line_color="#34D399",
                             line_width=1,
                             annotation_text="Sharpe = 1",
                             annotation_font_color="#34D399",
                             annotation_font_size=10)
            fig_rs.add_hline(y=0.0, line_dash="dot", line_color="#EF4444",
                             line_width=1)
            fig_rs.add_trace(go.Scatter(
                x=roll_sharpe.index, y=roll_sharpe.values,
                name="Sharpe glissant 3M",
                line=dict(color=C["gold"], width=2),
                fill="tozeroy",
                fillcolor="rgba(59,130,246,0.06)",
                hovertemplate="%{x|%d %b %Y}<br>Sharpe = %{y:.2f}<extra></extra>",
            ))
            fig_rs.update_layout(**plotly_layout(
                height=220,
                title=dict(text="Sharpe Ratio glissant 3M (fenêtre 63 j, Rf=4%)", font=dict(size=11)),
                yaxis=dict(zeroline=True, title="Sharpe"),
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False,
            ))
            st.plotly_chart(fig_rs, use_container_width=True, config={"displayModeBar": False})

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Tableau de positions
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Tableau des Positions")

rows = []
for t in valid_tickers:
    price_s = prices[t].dropna()
    rsi     = rsi_map.get(t)
    v       = stock_verdict(rsi, meta[t]["pe"], None, meta[t]["sector"], meta[t]["roe"])

    mom_3m = None
    if len(price_s) >= 63:
        mom_3m = (float(price_s.iloc[-1]) / float(price_s.iloc[-63]) - 1) * 100

    pe_med = SECTOR_PE_MEDIANS.get(meta[t]["sector"], None)
    pe_str = "—"
    if meta[t]["pe"]:
        pe_str = f"{meta[t]['pe']:.1f}x"
        if pe_med:
            pe_str += f" (méd. {pe_med}x)"

    rows.append({
        "Ticker":    t,
        "Nom":       meta[t]["name"][:24],
        "Secteur":   meta[t]["sector"] if meta[t]["sector"] not in ("Unknown", None, "") else "—",
        "Pays":      meta[t]["country"] if meta[t]["country"] not in ("Unknown", None, "") else "—",
        "Poids":     f"{weights[t]*100:.1f}%",
        "RSI(14)":   f"{rsi:.1f}" if rsi else "—",
        "Mom. 3M":   f"{mom_3m:+.1f}%" if mom_3m is not None else "—",
        "P/E":       pe_str,
        "Bêta":      f"{meta[t]['beta']:.2f}" if meta[t]["beta"] else "—",
        "Verdict":   f"{v['icon']} {v['label']}",
    })

st.dataframe(pd.DataFrame(rows).set_index("Ticker"), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Recommandations
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### Recommandations de Rééquilibrage")
st.markdown(
    "<p style='color:#5A6E82;font-size:0.78rem;margin-top:-6px;'>"
    "Basées sur : concentration (>35%), RSI Wilder(14), P/E vs médiane sectorielle GICS.</p>",
    unsafe_allow_html=True,
)

suggestions_final = []

for t in valid_tickers:
    w_pct = weights[t] * 100
    rsi   = rsi_map.get(t)
    pe_i  = interpret_pe(meta[t]["pe"], meta[t]["sector"])
    pe_med = SECTOR_PE_MEDIANS.get(meta[t]["sector"], 22)

    if w_pct > 30:
        suggestions_final.append({
            "icon": "⚖", "color": "#F59E0B",
            "text": f"**{t}** ({w_pct:.1f}% du portefeuille) : concentration supérieure à 30%. "
                    f"Règle de gestion : limiter chaque ligne à 20–25% pour réduire le risque idiosyncratique."
        })
    if rsi and rsi > 75:
        suggestions_final.append({
            "icon": "🌡", "color": "#EF4444",
            "text": f"**{t}** : RSI à {rsi:.0f} — zone de surchauffe technique (seuil : 70). "
                    f"Un stop-loss trailing ou un allègement partiel protège les gains latents."
        })
    if rsi and rsi < 28:
        suggestions_final.append({
            "icon": "📉", "color": "#06B6D4",
            "text": f"**{t}** : RSI à {rsi:.0f} — zone de survente (seuil : 30). "
                    f"Potentiellement intéressant pour un renforcement si la thèse fondamentale est intacte."
        })
    if pe_i.get("overvalued") and meta[t]["pe"]:
        suggestions_final.append({
            "icon": "💰", "color": "#F59E0B",
            "text": f"**{t}** : P/E {meta[t]['pe']:.0f}x vs médiane sectorielle {pe_med}x — "
                    f"{pe_i['verdict']}. "
                    f"La valorisation suppose une croissance bénéficiaire au-dessus de la médiane du secteur."
        })

n_sectors_uniq = len(set(
    meta[t]["sector"] for t in valid_tickers
    if meta[t]["sector"] not in ("Unknown", None, "")
))
if n_sectors_uniq < 3:
    suggestions_final.append({
        "icon": "🏗", "color": "#8B5CF6",
        "text": f"Seulement {n_sectors_uniq} secteur(s) distinct(s). "
                "Ajouter des positions dans des secteurs décorrélés (ex : santé, consommation de base, "
                "obligations) réduit la sensibilité aux chocs sectoriels."
    })

if not suggestions_final:
    suggestions_final.append({
        "icon": "✓", "color": "#34D399",
        "text": "Aucune alerte critique. Le profil global est équilibré. "
                "Continuez à surveiller les RSI et les niveaux de valorisation lors des prochains reporting."
    })

for item in suggestions_final[:6]:
    st.markdown(
        f"<div style='background:#0C1322;border:1px solid #1C2D45;border-left:3px solid {item['color']};"
        f"border-radius:2px;padding:10px 16px;margin-bottom:6px;color:#A8B4C4;font-size:0.84rem;'>"
        f"<span style='color:{item['color']};margin-right:8px;font-size:1rem;'>{item['icon']}</span>"
        f"{item['text']}</div>",
        unsafe_allow_html=True,
    )

# ── Footer méthodologique ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='color:#2D3748;font-size:0.72rem;text-align:center;'>"
    "Données : Yahoo Finance (yfinance, cache 30 min) · Calculs : numpy / scipy · "
    "Méthodologie complète → page Méthodologie · "
    "⚠ Outil d'aide à la décision — ne constitue pas un conseil en investissement (MIF II).</p>",
    unsafe_allow_html=True,
)
