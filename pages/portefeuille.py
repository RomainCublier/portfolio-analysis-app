"""
Page : Mon Portefeuille — diagnostic intelligent de diversification.

Flux utilisateur :
  1. L'utilisateur entre ses positions (ticker + montant investi)
  2. L'app calcule la composition, les risques et la diversification
  3. Elle génère une narrative intelligente : pourquoi c'est diversifié (ou non)
  4. Alertes par position (RSI, valorisation) + suggestions de rééquilibrage
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from config.settings import CSS, PLOTLY, C, CHART_COLORS, plotly_layout
from config.ticker_meta import TICKER_META
from core.indicators import (
    compute_rsi,
    interpret_rsi,
    interpret_pe,
    stock_verdict,
    portfolio_diversification,
)

st.markdown(CSS, unsafe_allow_html=True)


# ─── helpers ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def load_portfolio_data(tickers_tuple: tuple) -> dict:
    """Load 1 year of prices + fundamentals for all tickers."""
    tickers = list(tickers_tuple)
    end     = datetime.today()
    start   = end - timedelta(days=400)

    raw = yf.download(tickers, start=start, end=end,
                      auto_adjust=True, progress=False)
    if raw.empty:
        return {}

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]].copy()
        prices.columns = tickers

    # Ensure proper column format
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])

    prices = prices.dropna(how="all")

    # Fundamentals per ticker
    meta = {}
    for t in tickers:
        static = TICKER_META.get(t.upper(), {})
        try:
            info = yf.Ticker(t).info
            meta[t] = {
                "name":    info.get("longName") or info.get("shortName") or static.get("name") or t,
                "sector":  info.get("sector")  or static.get("sector")  or "Unknown",
                "country": info.get("country") or static.get("country") or "Unknown",
                "pe":      info.get("trailingPE") or info.get("forwardPE"),
                "pb":      info.get("priceToBook"),
                "roe":     info.get("returnOnEquity"),
                "beta":    info.get("beta"),
            }
            if meta[t]["roe"] is not None and abs(meta[t]["roe"]) <= 1.0:
                meta[t]["roe"] = meta[t]["roe"] * 100
        except Exception:
            meta[t] = {
                "name": static.get("name", t),
                "sector": static.get("sector", "Unknown"),
                "country": static.get("country", "Unknown"),
                "pe": None, "pb": None, "roe": None, "beta": None,
            }

    return {"prices": prices, "meta": meta}


def _safe_float(v):
    try:
        f = float(v)
        return f if not np.isnan(f) else 0.0
    except Exception:
        return 0.0


def color_score(score: float) -> str:
    if score >= 75: return "#34D399"   # green
    if score >= 55: return C["gold"]   # yellow
    if score >= 35: return "#F97316"   # orange
    return "#EF4444"                    # red


def score_label(score: float) -> str:
    if score >= 75: return "Bien diversifié"
    if score >= 55: return "Diversification correcte"
    if score >= 35: return "Diversification insuffisante"
    return "Portefeuille concentré"


# ─── Page ────────────────────────────────────────────────────────────────────

st.markdown("## 📊 Mon Portefeuille")
st.markdown(
    "<p style='color:#8892A0;margin-top:-8px;'>Entrez vos positions pour obtenir un diagnostic "
    "complet de diversification, de risque et des alertes par titre.</p>",
    unsafe_allow_html=True,
)

# ── Step 1 : Input table ──────────────────────────────────────────────────────

st.markdown("### Mes Positions")

DEFAULT_POSITIONS = pd.DataFrame({
    "Ticker":        ["AAPL", "MSFT", "NVDA", "JPM", "XOM", "JNJ", "AMZN", "TLT", "GLD", "VEA"],
    "Montant (€/$)": [5000,   4000,   3500,   2500,  2000,  2000,  3000,   2500,  2000,  1500],
})

positions_df = st.data_editor(
    DEFAULT_POSITIONS,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Ticker":          st.column_config.TextColumn("Ticker", width="small"),
        "Montant (€/$)":   st.column_config.NumberColumn("Montant investi", min_value=0, format="%.0f"),
    },
    key="portfolio_editor",
)

col_run, col_hint = st.columns([1, 3])
with col_run:
    run = st.button("Analyser mon portefeuille →", use_container_width=True, type="primary")
with col_hint:
    st.markdown("<p style='color:#4A5568;font-size:0.82rem;padding-top:8px;'>"
                "Ajoutez / supprimez des lignes directement dans le tableau.</p>",
                unsafe_allow_html=True)

if not run:
    st.info("💡 Renseignez vos positions et cliquez sur **Analyser mon portefeuille**.")
    st.stop()

# ── Validate & load ───────────────────────────────────────────────────────────

positions_df = positions_df.dropna(subset=["Ticker"])
positions_df["Ticker"]         = positions_df["Ticker"].str.strip().str.upper()
positions_df["Montant (€/$)"]  = positions_df["Montant (€/$)"].apply(_safe_float)
positions_df = positions_df[positions_df["Ticker"] != ""]
positions_df = positions_df[positions_df["Montant (€/$)"] > 0]

if len(positions_df) < 2:
    st.warning("Veuillez entrer au moins 2 positions pour une analyse de diversification.")
    st.stop()

tickers  = positions_df["Ticker"].tolist()
amounts  = positions_df["Montant (€/$)"].tolist()
total    = sum(amounts)
weights  = {t: a / total for t, a in zip(tickers, amounts)}

with st.spinner("Chargement des données de marché…"):
    data = load_portfolio_data(tuple(tickers))

if not data or data["prices"].empty:
    st.error("Impossible de charger les données. Vérifiez vos tickers.")
    st.stop()

prices = data["prices"]
meta   = data["meta"]

# Keep only tickers with data
valid_tickers = [t for t in tickers if t in prices.columns]
if len(valid_tickers) < 2:
    st.error("Données insuffisantes. Vérifiez vos tickers.")
    st.stop()

prices = prices[valid_tickers].dropna(how="all")
w_arr  = np.array([weights[t] for t in valid_tickers])
w_arr  = w_arr / w_arr.sum()

# Daily returns — dropna(how="any") supprime les jours où un titre manque.
# Si trop peu de lignes restent (actifs internationaux / ETFs), on garde
# toutes les lignes valides et on remplace les NaN par 0 (pas de mouvement).
rets_raw = prices.pct_change()
rets     = rets_raw.dropna(how="any")
if len(rets) < 60:                          # seuil : 60 jours minimum
    rets = rets_raw.dropna(how="all").fillna(0)
corr     = rets.corr(min_periods=30)
sector_map = {t: meta[t]["sector"] for t in valid_tickers}

# RSI per position
rsi_map = {}
for t in valid_tickers:
    if t in prices.columns:
        rsi_map[t] = compute_rsi(prices[t].dropna())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Score de diversification
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Diagnostic de Diversification")

diag = portfolio_diversification(
    weights     = {t: float(w) for t, w in zip(valid_tickers, w_arr)},
    corr_matrix = corr,
    sector_map  = sector_map,
)

score = diag["score"]
clr   = color_score(score)
lbl   = score_label(score)

# Big score card
col_score, col_breakdown = st.columns([1, 2])

with col_score:
    fig_gauge = go.Figure(go.Indicator(
        mode   = "gauge+number",
        value  = score,
        title  = {"text": "Score Diversification", "font": {"color": "#E2E8F0", "size": 13}},
        number = {"suffix": "/100", "font": {"color": clr, "size": 36}},
        gauge  = {
            "axis": {"range": [0, 100], "tickcolor": "#4A5568",
                     "tickvals": [0, 35, 55, 75, 100],
                     "ticktext": ["0", "Conc.", "Correct", "Bien", "100"],
                     "tickfont": {"color": "#8892A0", "size": 9}},
            "bar": {"color": clr, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  35], "color": "#2D1515"},
                {"range": [35, 55], "color": "#2D2215"},
                {"range": [55, 75], "color": "#2D2D15"},
                {"range": [75,100], "color": "#152D1E"},
            ],
        },
    ))
    fig_gauge.update_layout(**plotly_layout(
        height=250,
        margin=dict(l=20, r=20, t=40, b=0),
    ))
    st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f"<div style='text-align:center;color:{clr};font-weight:700;font-size:1rem;"
        f"margin-top:-10px;'>{lbl}</div>",
        unsafe_allow_html=True,
    )

with col_breakdown:
    # Sub-scores — barres = SCORES (100 = bon, 0 = mauvais)
    # Markowitz : bonne diversification = poids répartis + faible corrélation + multi-secteurs
    sub = diag.get("sub_scores", {})
    sub_items = [
        # Label                          Score                         Explication
        ("Répartition des poids  (HHI)", sub.get("hhi_score",   50), "100 = équipondéré · 0 = mono-position"),
        ("Décorrélation des actifs",     sub.get("corr_score",  50), "100 = actifs indépendants · 0 = corrélation totale"),
        ("Diversification sectorielle",  sub.get("sector_score",50), "100 = tous secteurs distincts · 0 = mono-secteur"),
    ]
    for label, s, tooltip in sub_items:
        c = color_score(s)
        st.markdown(
            f"<div style='margin-bottom:12px;'>"
            f"<div style='display:flex;align-items:center;gap:12px;'>"
            f"<span style='color:#8892A0;font-size:0.80rem;min-width:220px;'>{label}</span>"
            f"<div style='flex:1;background:#2D3748;border-radius:4px;height:8px;'>"
            f"<div style='background:{c};width:{s:.0f}%;height:100%;border-radius:4px;'></div></div>"
            f"<span style='color:{c};font-size:0.82rem;font-weight:600;min-width:32px;text-align:right;'>{s:.0f}</span>"
            f"</div>"
            f"<div style='color:#4A5568;font-size:0.68rem;margin-top:2px;padding-left:2px;font-style:italic;'>{tooltip}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Narrative
    st.markdown(
        f"<div style='background:rgba(30,37,53,0.6);border-left:3px solid {clr};"
        f"border-radius:6px;padding:12px 16px;'>"
        f"<p style='color:#CBD5E1;font-size:0.88rem;margin:0;'>{diag['narrative']}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

# Alerts
if diag.get("alerts"):
    st.markdown("<br>", unsafe_allow_html=True)
    for alert in diag["alerts"]:
        st.markdown(
            f"<div style='background:rgba(249,115,22,0.08);border:1px solid rgba(249,115,22,0.3);"
            f"border-radius:6px;padding:10px 16px;margin-bottom:6px;color:#FBD38D;"
            f"font-size:0.85rem;'>⚠️ {alert}</div>",
            unsafe_allow_html=True,
        )

if diag.get("suggestions"):
    for sug in diag["suggestions"]:
        st.markdown(
            f"<div style='background:rgba(56,189,248,0.06);border:1px solid rgba(56,189,248,0.2);"
            f"border-radius:6px;padding:10px 16px;margin-bottom:6px;color:#7DD3FC;"
            f"font-size:0.85rem;'>💡 {sug}</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Composition du portefeuille
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Composition")

col_pie1, col_pie2, col_pie3 = st.columns(3)

with col_pie1:
    # Weight donut
    fig_w = go.Figure(go.Pie(
        labels     = valid_tickers,
        values     = [weights[t] * 100 for t in valid_tickers],
        hole       = 0.55,
        marker     = dict(colors=CHART_COLORS[:len(valid_tickers)],
                          line=dict(color="#0B0E17", width=2)),
        textinfo   = "label+percent",
        textfont   = dict(size=11, color="#E2E8F0"),
        hovertemplate = "<b>%{label}</b><br>%{percent}<br>%{value:.1f}%<extra></extra>",
    ))
    fig_w.update_layout(**plotly_layout(
        title=dict(text="Poids par titre", font=dict(size=12)),
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
    ))
    st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})

with col_pie2:
    # Sector donut
    sector_weights: dict[str, float] = {}
    for t, w in zip(valid_tickers, w_arr):
        s = meta[t]["sector"] if meta[t]["sector"] not in ("Unknown", None, "") else "Non classifié"
        sector_weights[s] = sector_weights.get(s, 0) + float(w)

    secs = list(sector_weights.keys())
    swts = [sector_weights[s] * 100 for s in secs]

    fig_s = go.Figure(go.Pie(
        labels     = secs,
        values     = swts,
        hole       = 0.55,
        marker     = dict(colors=CHART_COLORS[:len(secs)],
                          line=dict(color="#0B0E17", width=2)),
        textinfo   = "label+percent",
        textfont   = dict(size=11, color="#E2E8F0"),
        hovertemplate = "<b>%{label}</b><br>%{percent}<extra></extra>",
    ))
    fig_s.update_layout(**plotly_layout(
        title=dict(text="Exposition sectorielle", font=dict(size=12)),
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
    ))
    st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})

with col_pie3:
    # Country / geography
    country_weights: dict[str, float] = {}
    for t, w in zip(valid_tickers, w_arr):
        c = meta[t]["country"] if meta[t]["country"] not in ("Unknown", None, "") else "Non disponible"
        country_weights[c] = country_weights.get(c, 0) + float(w)

    cnts = list(country_weights.keys())
    cwts = [country_weights[c] * 100 for c in cnts]

    fig_c = go.Figure(go.Pie(
        labels     = cnts,
        values     = cwts,
        hole       = 0.55,
        marker     = dict(colors=CHART_COLORS[:len(cnts)],
                          line=dict(color="#0B0E17", width=2)),
        textinfo   = "label+percent",
        textfont   = dict(size=11, color="#E2E8F0"),
        hovertemplate = "<b>%{label}</b><br>%{percent}<extra></extra>",
    ))
    fig_c.update_layout(**plotly_layout(
        title=dict(text="Exposition géographique", font=dict(size=12)),
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
    ))
    st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Performance & risque global
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Performance & Risque")

# Normalised cumulative portfolio vs equal-weight benchmark
try:
    port_rets   = rets[valid_tickers].dot(w_arr)   # alignement explicite colonnes→poids
    ew_rets     = rets[valid_tickers].mean(axis=1)
    cum_port    = (1 + port_rets).cumprod()
    cum_ew      = (1 + ew_rets).cumprod()

    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=cum_port.index, y=cum_port.values * 100 - 100,
        name="Votre portefeuille",
        line=dict(color=C["gold"], width=2.5),
        fill="tozeroy", fillcolor="rgba(201,169,74,0.06)",
    ))
    fig_perf.add_trace(go.Scatter(
        x=cum_ew.index, y=cum_ew.values * 100 - 100,
        name="Equal-weight",
        line=dict(color="#8892A0", width=1.5, dash="dot"),
    ))
    fig_perf.update_layout(**plotly_layout(
        height=300,
        title=dict(text="Performance cumulative pondérée (base 0%)", font=dict(size=13)),
        yaxis=dict(ticksuffix="%"),
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", y=1.08, x=0),
    ))
    st.plotly_chart(fig_perf, use_container_width=True, config={"displayModeBar": False})

    # KPI strip
    port_vol    = float(port_rets.std() * np.sqrt(252) * 100)
    port_ret    = float(port_rets.mean() * 252 * 100)
    sharpe      = (port_ret / 100 - 0.04) / (port_vol / 100) if port_vol > 0 else 0
    max_dd      = float(((cum_port / cum_port.cummax()) - 1).min() * 100)
    avg_corr    = float(corr.where(np.triu(np.ones_like(corr, dtype=bool), k=1)).stack().mean())

    k1, k2, k3, k4, k5 = st.columns(5)
    kpis = [
        (k1, "Rend. annualisé", f"{port_ret:+.1f}%", C["gold"] if port_ret > 0 else "#EF4444"),
        (k2, "Volatilité ann.", f"{port_vol:.1f}%",  "#8892A0"),
        (k3, "Sharpe",         f"{sharpe:.2f}",      C["gold"] if sharpe > 1 else "#8892A0"),
        (k4, "Max Drawdown",   f"{max_dd:.1f}%",     "#EF4444"),
        (k5, "Corr. moy.",     f"{avg_corr:.2f}",    "#34D399" if avg_corr < 0.5 else "#F97316"),
    ]
    for col, label, value, color in kpis:
        with col:
            st.markdown(
                f"<div style='background:rgba(30,37,53,0.6);border-radius:8px;padding:14px;text-align:center;'>"
                f"<div style='color:#8892A0;font-size:0.72rem;letter-spacing:0.06em;'>{label}</div>"
                f"<div style='color:{color};font-size:1.4rem;font-weight:700;margin-top:4px;'>{value}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
except Exception:
    st.warning("Calcul de performance indisponible (données insuffisantes).")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3b — Advanced Risk Metrics (institutional grade)
# ─────────────────────────────────────────────────────────────────────────────

try:
    # Benchmark SPY via Ticker.history() — API stable, pas de MultiIndex
    _spy_hist  = yf.Ticker("SPY").history(period="2y", auto_adjust=True)
    spy_close  = _spy_hist["Close"].dropna()
    if spy_close.index.tz is not None:
        spy_close.index = spy_close.index.tz_convert(None)
    spy_rets = spy_close.pct_change().dropna()

    # Align dates
    common_idx  = port_rets.index.intersection(spy_rets.index)
    p_aligned   = port_rets.loc[common_idx]
    b_aligned   = spy_rets.loc[common_idx]

    if len(common_idx) > 30:
        # Beta & Alpha (OLS)
        cov_pb  = float(np.cov(p_aligned, b_aligned)[0, 1])
        var_b   = float(np.var(b_aligned))
        beta    = cov_pb / var_b if var_b > 0 else 1.0
        alpha_d = float(p_aligned.mean() - beta * b_aligned.mean())   # daily
        alpha_a = alpha_d * 252 * 100  # annualised %

        # VaR & CVaR (historical, 95%)
        var_95  = float(np.percentile(port_rets, 5) * 100)
        cvar_95 = float(port_rets[port_rets <= np.percentile(port_rets, 5)].mean() * 100)

        # Sortino
        downside = port_rets[port_rets < 0]
        down_vol = float(downside.std() * np.sqrt(252) * 100) if len(downside) > 0 else float(port_vol)
        sortino  = (port_ret / 100 - 0.04) / (down_vol / 100) if down_vol > 0 else 0.0

        # Calmar
        calmar   = (port_ret / 100) / abs(max_dd / 100) if max_dd != 0 else 0.0

        # Tracking Error
        active_rets = p_aligned - b_aligned
        te = float(active_rets.std() * np.sqrt(252) * 100)
        ir = float(active_rets.mean() * 252 * 100 / te) if te > 0 else 0.0

        st.markdown("---")
        st.markdown("### Métriques de Risque Avancées")

        adv_kpis = [
            ("Beta (vs SPY)",    f"{beta:.2f}",       "#8892A0" if 0.8 < beta < 1.2 else C["gold"] if beta < 0.8 else "#EF4444"),
            ("Alpha annualisé",  f"{alpha_a:+.1f}%",  C["gold"] if alpha_a > 0 else "#EF4444"),
            ("VaR 95% (1j)",     f"{var_95:.2f}%",    "#EF4444"),
            ("CVaR 95% (1j)",    f"{cvar_95:.2f}%",   "#EF4444"),
            ("Sortino",          f"{sortino:.2f}",     C["gold"] if sortino > 1.5 else "#8892A0"),
            ("Calmar",           f"{calmar:.2f}",      C["gold"] if calmar > 0.5 else "#8892A0"),
            ("Tracking Error",   f"{te:.1f}%",         "#8892A0"),
            ("Info. Ratio",      f"{ir:.2f}",          C["gold"] if ir > 0.5 else "#8892A0"),
        ]

        cols_adv = st.columns(4)
        for i, (lbl, val, clr) in enumerate(adv_kpis):
            with cols_adv[i % 4]:
                st.markdown(
                    f"<div style='background:rgba(30,37,53,0.6);border-radius:8px;padding:12px;"
                    f"text-align:center;border-top:2px solid {clr};margin-bottom:8px;'>"
                    f"<div style='color:#8892A0;font-size:0.7rem;letter-spacing:0.06em;text-transform:uppercase;'>{lbl}</div>"
                    f"<div style='color:{clr};font-size:1.2rem;font-weight:700;margin-top:4px;font-family:\"IBM Plex Mono\",monospace;'>{val}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Rolling 3M Sharpe
        roll_sharpe = port_rets.rolling(63).apply(
            lambda x: (x.mean() * 252 - 0.04) / (x.std() * np.sqrt(252))
            if x.std() > 0 else 0, raw=True
        ).dropna()

        fig_rs = go.Figure()
        fig_rs.add_hline(y=1, line_dash="dot", line_color="#4A5568",
                          annotation_text="Sharpe=1", annotation_font_color="#4A5568")
        fig_rs.add_hline(y=0, line_dash="dot", line_color="#EF444455")
        fig_rs.add_trace(go.Scatter(
            x=roll_sharpe.index, y=roll_sharpe.values,
            name="Sharpe glissant 3M",
            line=dict(color=C["gold"], width=2),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.07)",
        ))
        fig_rs.update_layout(**plotly_layout(
            height=220,
            title=dict(text="Sharpe Ratio glissant (fenêtre 63 jours, Rf=4%)", font=dict(size=12)),
            yaxis=dict(zeroline=True),
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", y=1.08),
        ))
        st.plotly_chart(fig_rs, use_container_width=True, config={"displayModeBar": False})

except Exception as e:
    st.info(f"Métriques avancées indisponibles : {e}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Corrélation heatmap
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")

col_corr, col_alerts = st.columns([2, 1])

with col_corr:
    st.markdown("#### Matrice de Corrélation")
    corr_rounded = corr.round(2)
    fig_corr = go.Figure(go.Heatmap(
        z          = corr_rounded.values,
        x          = corr_rounded.columns.tolist(),
        y          = corr_rounded.index.tolist(),
        colorscale = [[0.0, "#1A3A4A"], [0.5, "#1E2535"], [1.0, C["gold"]]],
        zmid       = 0,
        zmin       = -1, zmax=1,
        text       = corr_rounded.values,
        texttemplate = "%{text:.2f}",
        textfont   = {"size": 11, "color": "#E2E8F0"},
        showscale  = True,
        colorbar   = dict(tickfont=dict(color="#8892A0"), outlinewidth=0),
    ))
    fig_corr.update_layout(**plotly_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11)),
    ))
    st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})

with col_alerts:
    st.markdown("#### Alertes par Titre")

    for t in valid_tickers:
        rsi = rsi_map.get(t)
        pe  = meta[t]["pe"]
        roe = meta[t]["roe"]
        v   = stock_verdict(rsi, pe, None, meta[t]["sector"], roe)

        rsi_interp = interpret_rsi(rsi) if rsi else {"label": "N/A", "color": "#8892A0"}

        has_rsi_alert = rsi and (rsi > 70 or rsi < 30)
        pe_interp     = interpret_pe(pe, meta[t]["sector"])
        has_pe_alert  = pe_interp.get("overvalued", False)

        alert_color   = "#EF4444" if has_rsi_alert or has_pe_alert else "#34D399"
        alert_icon    = "🔴" if has_rsi_alert or has_pe_alert else "🟢"

        alerts_list = []
        if has_rsi_alert:
            alerts_list.append(f"RSI {rsi:.0f} — {rsi_interp['label']}")
        if has_pe_alert:
            alerts_list.append(f"P/E {pe:.0f}x — {pe_interp['verdict']}")

        alerts_txt = " · ".join(alerts_list) if alerts_list else "Aucune alerte"

        w_pct = weights.get(t, 0) * 100
        st.markdown(
            f"<div style='background:rgba(30,37,53,0.5);border-left:3px solid {alert_color};"
            f"border-radius:6px;padding:10px 14px;margin-bottom:8px;'>"
            f"<div style='display:flex;justify-content:space-between;'>"
            f"<span style='color:#E2E8F0;font-weight:600;'>{alert_icon} {t}</span>"
            f"<span style='color:#8892A0;font-size:0.78rem;'>{w_pct:.1f}% du port.</span>"
            f"</div>"
            f"<div style='color:#8892A0;font-size:0.78rem;margin-top:4px;'>{alerts_txt}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Tableau de positions détaillé
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Tableau des Positions")

rows = []
for t in valid_tickers:
    price_s = prices[t].dropna()
    current_price = float(price_s.iloc[-1]) if len(price_s) > 0 else None
    rsi = rsi_map.get(t)
    v   = stock_verdict(rsi, meta[t]["pe"], None, meta[t]["sector"], meta[t]["roe"])

    mom_3m = None
    if len(price_s) >= 63:
        mom_3m = (float(price_s.iloc[-1]) / float(price_s.iloc[-63]) - 1) * 100

    rows.append({
        "Ticker":       t,
        "Nom":          meta[t]["name"][:22],
        "Secteur":      meta[t]["sector"][:18] if meta[t]["sector"] not in ("Unknown", None, "") else "—",
        "Poids":        f"{weights[t]*100:.1f}%",
        "RSI":          f"{rsi:.1f}" if rsi else "—",
        "Mom. 3M":      f"{mom_3m:+.1f}%" if mom_3m is not None else "—",
        "P/E":          f"{meta[t]['pe']:.1f}" if meta[t]["pe"] else "—",
        "Bêta":         f"{meta[t]['beta']:.2f}" if meta[t]["beta"] else "—",
        "Verdict":      f"{v['icon']} {v['label']}",
    })

df_pos = pd.DataFrame(rows).set_index("Ticker")
st.dataframe(df_pos, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Suggestions de rééquilibrage
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 💡 Recommandations de Rééquilibrage")

# Identify overweight + alerted positions
suggestions = []
for t in valid_tickers:
    w_pct = weights[t] * 100
    rsi   = rsi_map.get(t)
    pe    = meta[t]["pe"]
    pe_i  = interpret_pe(pe, meta[t]["sector"])

    if w_pct > 35:
        suggestions.append(
            f"**{t}** représente {w_pct:.1f}% du portefeuille — concentration élevée. "
            f"Envisagez de réduire à <25% pour limiter le risque idiosyncratique."
        )
    if rsi and rsi > 75:
        suggestions.append(
            f"**{t}** : RSI à {rsi:.0f} (surchauffe technique). "
            f"Un allègement partiel ou un stop-loss trailing peut protéger les gains."
        )
    if rsi and rsi < 25:
        suggestions.append(
            f"**{t}** : RSI à {rsi:.0f} (survente). Possible opportunité d'accumulation "
            f"si la thèse fondamentale reste intacte."
        )
    if pe_i.get("overvalued"):
        suggestions.append(
            f"**{t}** : {pe_i['verdict']} — exiger une forte croissance bénéficiaire "
            f"pour justifier la valorisation actuelle."
        )

n_sectors = len(set(meta[t]["sector"] for t in valid_tickers))
if n_sectors < 3:
    suggestions.append(
        "Votre portefeuille est exposé à moins de 3 secteurs. Envisagez d'ajouter des titres "
        "dans des secteurs défensifs (santé, consommation de base) ou non-corrélés."
    )

if not suggestions:
    suggestions.append(
        "Aucune alerte critique détectée. Votre portefeuille présente un profil équilibré. "
        "Continuez à surveiller les évolutions de RSI et de valorisation."
    )

for i, sug in enumerate(suggestions[:6]):
    st.markdown(
        f"<div style='background:rgba(30,37,53,0.5);border-radius:8px;padding:14px 18px;"
        f"margin-bottom:8px;color:#CBD5E1;font-size:0.87rem;'>"
        f"<span style='color:{C['gold']};font-weight:700;margin-right:8px;'>{i+1}.</span>"
        f"{sug}</div>",
        unsafe_allow_html=True,
    )
