"""
Tableau de Bord — Vue macro multi-actifs.

Chargement automatique au démarrage. Rafraîchissement toutes les 30 min.
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

from config.settings import CSS, C, CHART_COLORS
import utils.charts as ch

st.markdown(CSS, unsafe_allow_html=True)

# ── Universe ──────────────────────────────────────────────────────────────────
UNIVERSE = {
    # Equities
    "S&P 500":        "^GSPC",
    "NASDAQ 100":     "QQQ",
    "MSCI World":     "URTH",
    "MSCI EM":        "EEM",
    "Euro Stoxx 50":  "FEZ",
    "Nikkei 225":     "EWJ",
    # Fixed income
    "US 10Y (ETF)":   "TLT",
    "US Agg Bond":    "AGG",
    "High Yield US":  "HYG",
    "EM Bonds":       "EMB",
    # Alternatives
    "Or (Gold)":      "GLD",
    "Argent (Silver)":"SLV",
    "REITs US":       "VNQ",
    "Pétrole (Oil)":  "USO",
}

CLASSES = {
    "^GSPC": "Actions", "QQQ": "Actions", "URTH": "Actions",
    "EEM": "Actions", "FEZ": "Actions", "EWJ": "Actions",
    "TLT": "Obligations", "AGG": "Obligations",
    "HYG": "Obligations", "EMB": "Obligations",
    "GLD": "Alternatifs", "SLV": "Alternatifs",
    "VNQ": "Alternatifs", "USO": "Alternatifs",
}

TREASURIES = {"3M": "^IRX", "5Y": "^FVX", "10Y": "^TNX", "30Y": "^TYX"}
MAT_VALS   = {"3M": 0.25, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0}


# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def _load_universe(start: str, end: str) -> pd.DataFrame:
    tickers = list(UNIVERSE.values())
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw
    prices = prices[[t for t in tickers if t in prices.columns]]
    return prices.dropna(how="all")


@st.cache_data(ttl=1800, show_spinner=False)
def _load_yields(start: str, end: str) -> pd.DataFrame:
    tickers = list(TREASURIES.values())
    raw = yf.download(tickers, start=start, end=end, auto_adjust=False, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        df = raw["Close"].copy()
    else:
        df = raw.copy()
    rename = {v: k for k, v in TREASURIES.items()}
    df = df.rename(columns=rename)
    return df[[c for c in TREASURIES if c in df.columns]].dropna(how="all")


@st.cache_data(ttl=1800, show_spinner=False)
def _load_vix(start: str, end: str) -> pd.Series:
    raw = yf.download("^VIX", start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        return raw["Close"]["^VIX"].dropna()
    return raw["Close"].dropna()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _ret(prices: pd.DataFrame, ticker: str, days: int) -> float:
    s = prices[ticker].dropna()
    if len(s) < 2:
        return np.nan
    end_p = s.iloc[-1]
    start_p = s.iloc[max(-days - 1, -len(s))]
    return float(end_p / start_p - 1)


def _ytd_ret(prices: pd.DataFrame, ticker: str) -> float:
    s = prices[ticker].dropna()
    if len(s) < 2:
        return np.nan
    today = s.index[-1]
    jan1  = pd.Timestamp(today.year, 1, 1)
    past  = s[s.index >= jan1]
    if len(past) < 2:
        return np.nan
    return float(past.iloc[-1] / past.iloc[0] - 1)


def _color_cell(v: float) -> str:
    if pd.isna(v):
        return "—"
    color = C["green"] if v >= 0 else C["red"]
    return f'<span style="color:{color};font-weight:600">{v*100:+.2f}%</span>'


def _fmt_yield(v) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v):.2f}%"


# ── Page ──────────────────────────────────────────────────────────────────────
today  = datetime.today()
end_s  = today.strftime("%Y-%m-%d")
s_1y   = (today - timedelta(days=365)).strftime("%Y-%m-%d")
s_5y   = (today - timedelta(days=5 * 365)).strftime("%Y-%m-%d")

st.title("Tableau de Bord — Marchés & Macro")
st.caption(f"Données Yahoo Finance · Dernière mise à jour : {today.strftime('%d %m %Y, %H:%M')}")

with st.spinner("Chargement des données de marché…"):
    prices  = _load_universe(s_5y, end_s)
    yields  = _load_yields(s_5y, end_s)
    vix_s   = _load_vix(s_1y, end_s)

if prices.empty:
    st.error("Impossible de charger les données de marché.")
    st.stop()

REV  = {v: k for k, v in UNIVERSE.items()}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — KPI TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Indicateurs clés")

KPI_TICKERS = ["^GSPC", "QQQ", "EEM", "GLD", "TLT", "^VIX_PROXY"]
kpi_layout  = st.columns(6)

# S&P 500
def _kpi(col, ticker, label):
    if ticker not in prices.columns:
        return
    s     = prices[ticker].dropna()
    last  = float(s.iloc[-1])
    d1    = _ret(prices, ticker, 1)
    d1_s  = f"{d1*100:+.2f}% (1J)" if not pd.isna(d1) else ""
    col.metric(label, f"{last:,.2f}", delta=d1_s,
               delta_color="normal" if not pd.isna(d1) else "off")

with kpi_layout[0]:
    _kpi(kpi_layout[0], "^GSPC", "S&P 500")
with kpi_layout[1]:
    _kpi(kpi_layout[1], "QQQ",   "NASDAQ 100")
with kpi_layout[2]:
    _kpi(kpi_layout[2], "EEM",   "MSCI EM")
with kpi_layout[3]:
    _kpi(kpi_layout[3], "GLD",   "Or (GLD)")
with kpi_layout[4]:
    _kpi(kpi_layout[4], "TLT",   "US 10Y (TLT)")
with kpi_layout[5]:
    if len(vix_s) > 0:
        cur  = float(vix_s.iloc[-1])
        prev = float(vix_s.iloc[-2]) if len(vix_s) > 1 else cur
        delta_v = f"{cur - prev:+.2f} (1J)"
        kpi_layout[5].metric("VIX", f"{cur:.1f}", delta=delta_v,
                              delta_color="inverse")

# ─── Yield quick strip ────────────────────────────────────────────────────────
if not yields.empty:
    avail_m = [m for m in TREASURIES if m in yields.columns]
    if avail_m:
        latest_y = yields[avail_m].dropna().iloc[-1]
        ycols    = st.columns(len(avail_m))
        for i, m in enumerate(avail_m):
            prev_y = yields[m].dropna().iloc[-2] if len(yields[m].dropna()) > 1 else latest_y[m]
            ycols[i].metric(
                f"T-{m}",
                f"{latest_y[m]:.2f}%",
                delta=f"{latest_y[m] - float(prev_y):+.2f}bp (1J)",
                delta_color="inverse",
            )

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — CROSS-ASSET PERFORMANCE TABLE
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Performance multi-actifs")

rows = []
for name, ticker in UNIVERSE.items():
    if ticker not in prices.columns:
        continue
    s = prices[ticker].dropna()
    if len(s) < 2:
        continue
    rows.append({
        "Actif":       name,
        "Classe":      CLASSES.get(ticker, "—"),
        "Dernière":    f"{float(s.iloc[-1]):,.2f}",
        "1J":          _ret(prices, ticker, 1),
        "1S":          _ret(prices, ticker, 5),
        "1M":          _ret(prices, ticker, 21),
        "3M":          _ret(prices, ticker, 63),
        "6M":          _ret(prices, ticker, 126),
        "YTD":         _ytd_ret(prices, ticker),
        "1A":          _ret(prices, ticker, 252),
        "3A ann.":     (float(s.iloc[-1] / s.iloc[max(-756, -len(s))]) ** (1 / 3) - 1)
                       if len(s) >= 50 else np.nan,
    })

df_perf = pd.DataFrame(rows)

# Style with color-coded cells via Streamlit's native styling
numeric_cols = ["1J", "1S", "1M", "3M", "6M", "YTD", "1A", "3A ann."]

def _style_pct(v):
    if pd.isna(v):
        return ""
    bg = "rgba(34,197,94,0.12)" if v >= 0 else "rgba(239,68,68,0.12)"
    col = C["green"] if v >= 0 else C["red"]
    return f"background-color:{bg};color:{col};font-weight:600"

styled = (
    df_perf.style
    .format({c: lambda v: f"{v*100:+.2f}%" if not pd.isna(v) else "—"
             for c in numeric_cols})
    .applymap(_style_pct, subset=numeric_cols)
    .set_properties(**{"font-size": "12px"})
)
st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — YIELD CURVE + VIX / S&P 500
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Taux & volatilité")

col_yc, col_vix = st.columns([1, 1])

# ── Yield Curve ───────────────────────────────────────────────────────────────
with col_yc:
    if not yields.empty:
        avail    = [m for m in TREASURIES if m in yields.columns]
        clean_y  = yields[avail].dropna()
        latest_y = clean_y.iloc[-1]
        date_l   = clean_y.index[-1]

        # Snapshots: current, 1Y ago, 2Y ago
        def _snap(days_ago):
            target = date_l - timedelta(days=days_ago)
            idx    = clean_y.index.searchsorted(target)
            return clean_y.iloc[min(idx, len(clean_y) - 1)]

        snap_1y = _snap(365)
        snap_2y = _snap(730)

        mat_vals   = [MAT_VALS[m] for m in avail]
        snapshots  = {
            f"Actuel ({date_l.strftime('%d/%m/%Y')})":        latest_y[avail].values,
            f"Il y a 1 an ({snap_1y.name.strftime('%d/%m/%Y') if hasattr(snap_1y, 'name') else ''})":
                snap_1y[avail].values,
            f"Il y a 2 ans":     snap_2y[avail].values,
        }
        fig_yc = ch.yield_curve(snapshots, mat_vals, avail,
                                title="Courbe des Taux US — Treasuries", height=360)
        st.plotly_chart(fig_yc, use_container_width=True)

        # Slope signal
        if "10Y" in avail and "3M" in avail:
            slope = float(latest_y["10Y"]) - float(latest_y["3M"])
            if slope < 0:
                st.error(f"Pente 10Y – 3M : **{slope:.2f}%** — Courbe inversée (signal récessif)")
            elif slope < 0.5:
                st.warning(f"Pente 10Y – 3M : **{slope:.2f}%** — Courbe plate")
            else:
                st.success(f"Pente 10Y – 3M : **{slope:.2f}%** — Courbe normale")

# ── VIX + S&P 500 Regime ─────────────────────────────────────────────────────
with col_vix:
    if len(vix_s) > 0:
        cur_vix = float(vix_s.iloc[-1])

        if cur_vix > 30:
            label = "Stress élevé"
            col_v = C["red"]
        elif cur_vix > 20:
            label = "Incertitude"
            col_v = C["orange"]
        else:
            label = "Faible volatilité"
            col_v = C["green"]

        fig_vix = go.Figure()
        fig_vix.add_trace(go.Scatter(
            x=vix_s.index, y=vix_s.values,
            fill="tozeroy",
            fillcolor="rgba(239,68,68,0.10)",
            line=dict(color=C["red"], width=1.3),
            name="VIX",
        ))
        fig_vix.add_hrect(y0=20, y1=30, fillcolor=C["orange"], opacity=0.04, line_width=0)
        fig_vix.add_hrect(y0=30, y1=100, fillcolor=C["red"],   opacity=0.04, line_width=0)
        fig_vix.add_hline(y=20, line_dash="dash", line_color=C["orange"],
                          annotation_text="20", annotation_position="right",
                          annotation_font_size=10)
        fig_vix.add_hline(y=30, line_dash="dash", line_color=C["red"],
                          annotation_text="30", annotation_position="right",
                          annotation_font_size=10)
        from config.settings import PLOTLY
        fig_vix.update_layout(**PLOTLY, title_text=f"VIX — Régime : {label}  ({cur_vix:.1f})",
                              height=360, showlegend=False)
        st.plotly_chart(fig_vix, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — S&P 500 MOMENTUM CHART
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## S&P 500 — Tendance & Moyennes Mobiles")

if "^GSPC" in prices.columns:
    spx   = prices["^GSPC"].dropna().tail(252 + 200)
    ma50  = spx.rolling(50).mean()
    ma200 = spx.rolling(200).mean()

    cur_spx   = float(spx.iloc[-1])
    cur_ma50  = float(ma50.iloc[-1])
    cur_ma200 = float(ma200.iloc[-1])

    if cur_spx > cur_ma200 and cur_ma50 > cur_ma200:
        regime_text = "Bull Market · MA50 > MA200 (Golden Cross)"
        regime_col  = C["green"]
    elif cur_spx < cur_ma200:
        regime_text = "Bear Market · sous MA200"
        regime_col  = C["red"]
    else:
        regime_text = "Transition · entre MA50 et MA200"
        regime_col  = C["orange"]

    fig_spx = go.Figure()
    fig_spx.add_trace(go.Scatter(
        x=spx.index, y=spx.values, name="S&P 500",
        line=dict(color=C["blue"], width=1.8)
    ))
    fig_spx.add_trace(go.Scatter(
        x=ma50.index, y=ma50.values, name="MA50",
        line=dict(color=C["gold"], width=1.2, dash="dash")
    ))
    fig_spx.add_trace(go.Scatter(
        x=ma200.index, y=ma200.values, name="MA200",
        line=dict(color=C["red"], width=1.2, dash="dot")
    ))
    from config.settings import PLOTLY
    fig_spx.update_layout(
        **PLOTLY,
        title_text=f"S&P 500  ·  <span style='color:{regime_col}'>{regime_text}</span>",
        height=340,
        legend=dict(orientation="h", y=1.04, x=0, font=dict(size=11)),
    )
    st.plotly_chart(fig_spx, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — CROSS-ASSET CORRELATIONS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Corrélations entre classes d'actifs (1 an)")

REPR = {
    "^GSPC": "S&P 500", "QQQ": "NASDAQ",
    "EEM": "MSCI EM", "FEZ": "Euro Stoxx",
    "TLT": "US 10Y", "HYG": "High Yield",
    "GLD": "Or", "VNQ": "REITs",
}

avail_repr = [t for t in REPR if t in prices.columns]
if len(avail_repr) >= 3:
    p_sub = prices[avail_repr].dropna().tail(252).pct_change().dropna()
    corr  = p_sub.corr()
    corr.index   = [REPR[t] for t in avail_repr]
    corr.columns = [REPR[t] for t in avail_repr]

    fig_corr = ch.heatmap(corr, title="Matrice de Corrélation (rendements journaliers, 1 an)",
                          zmin=-1, zmax=1, height=420)
    st.plotly_chart(fig_corr, use_container_width=True)

    st.caption(
        "Lecture : une corrélation proche de +1 indique que les actifs évoluent de concert "
        "(diversification faible) ; proche de -1, ils sont des couvertures naturelles l'un de l'autre."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — PERFORMANCE COMPARÉE 1 AN
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Performance comparée — 1 an (base 100)")

SEL = ["^GSPC", "QQQ", "EEM", "GLD", "TLT", "HYG"]
avail_sel = [t for t in SEL if t in prices.columns]
if avail_sel:
    p1y   = prices[avail_sel].tail(252).dropna()
    norm  = p1y / p1y.iloc[0] * 100

    series_dict = {UNIVERSE.get(t, t): norm[t] for t in avail_sel}
    fig_norm = ch.line(series_dict, title="Performance normalisée (base 100)",
                       y_label="Indice", height=360)
    st.plotly_chart(fig_norm, use_container_width=True)
