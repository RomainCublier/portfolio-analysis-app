import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta


TREASURIES = {
    "3M":  "^IRX",
    "5Y":  "^FVX",
    "10Y": "^TNX",
    "30Y": "^TYX",
}
MAT_YEARS = {"3M": 0.25, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0}


@st.cache_data(show_spinner=False, ttl=1800)
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


@st.cache_data(show_spinner=False, ttl=1800)
def _load_market(start: str, end: str):
    raw = yf.download(["^GSPC", "^VIX"], start=start, end=end,
                      auto_adjust=True, progress=False)
    if raw.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        spx = raw["Close"]["^GSPC"].dropna()
        vix = raw["Close"]["^VIX"].dropna()
    else:
        spx = pd.Series(dtype=float)
        vix = pd.Series(dtype=float)
    return spx, vix


# ─────────────────────────────────────────────────────────────────────────────
st.title("🌍 Contexte de Marché")
st.caption("Courbe des taux US · VIX · Régimes de marché · Taux sans risque")

today = datetime.today()
end_str   = today.strftime("%Y-%m-%d")
start_5y  = (today - timedelta(days=5 * 365)).strftime("%Y-%m-%d")
start_1y  = (today - timedelta(days=365)).strftime("%Y-%m-%d")

with st.spinner("Chargement des données de marché…"):
    yields_df = _load_yields(start_5y, end_str)
    spx, vix  = _load_market(start_1y, end_str)

available = [m for m in TREASURIES if m in yields_df.columns]

# ═════════════════════════════════════════════════════════════════════════════
# YIELD CURVE
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Courbe des Taux US — Treasuries")

if available:
    clean = yields_df[available].dropna()
    latest = clean.iloc[-1]
    date_latest = clean.index[-1]

    # snapshot 1 year ago
    target_1y = date_latest - timedelta(days=365)
    idx_1y = clean.index.searchsorted(target_1y)
    yields_1y = clean.iloc[min(idx_1y, len(clean) - 1)]

    mat_vals = [MAT_YEARS[m] for m in available]

    fig_curve = go.Figure()

    fig_curve.add_trace(go.Scatter(
        x=mat_vals,
        y=latest[available].values,
        mode="lines+markers+text",
        line=dict(color="cyan", width=3),
        marker=dict(size=11),
        text=[f"{v:.2f}%" for v in latest[available].values],
        textposition="top center",
        textfont=dict(color="cyan", size=11),
        name=f"Actuel — {date_latest.strftime('%d/%m/%Y')}",
        hovertemplate="%{y:.2f}%<extra></extra>",
    ))

    fig_curve.add_trace(go.Scatter(
        x=mat_vals,
        y=yields_1y[available].values,
        mode="lines+markers",
        line=dict(color="orange", width=2, dash="dash"),
        marker=dict(size=8),
        name=f"Il y a 1 an — {target_1y.strftime('%d/%m/%Y')}",
        hovertemplate="%{y:.2f}%<extra></extra>",
    ))

    fig_curve.update_layout(
        xaxis=dict(
            title="Maturité",
            tickvals=mat_vals,
            ticktext=available,
        ),
        yaxis_title="Taux (%)",
        template="plotly_dark",
        height=440,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_curve, use_container_width=True)

    # Current rate metrics
    rate_cols = st.columns(len(available))
    for i, m in enumerate(available):
        delta = f"{latest[m] - yields_1y[m]:+.2f}% vs 1A"
        rate_cols[i].metric(f"T-{m}", f"{latest[m]:.2f}%", delta=delta)

    # Slope / inversion signal
    if "10Y" in available and "3M" in available:
        slope = latest["10Y"] - latest["3M"]
        msg = f"**Pente 10Y – 3M : {slope:.2f}%**"
        if slope < 0:
            st.error(f"{msg} — Courbe inversée ⚠️  (signal historiquement récessif)")
        elif slope < 0.5:
            st.warning(f"{msg} — Courbe plate (signal de ralentissement potentiel)")
        else:
            st.success(f"{msg} — Courbe normale (pentue, régime de croissance)")

# ── Historical yield evolution ────────────────────────────────────────────────
if available:
    st.subheader("Évolution historique des taux (5 ans)")
    COLORS = ["cyan", "orange", "limegreen", "tomato"]
    fig_hist = go.Figure()
    for i, m in enumerate(available):
        s = yields_df[m].dropna()
        fig_hist.add_trace(go.Scatter(
            x=s.index, y=s.values,
            name=f"T-{m}",
            line=dict(color=COLORS[i % 4], width=1.5),
        ))
    fig_hist.update_layout(
        yaxis_title="Taux (%)",
        template="plotly_dark",
        height=330,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# VIX & MARKET REGIME
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("VIX & Régime de Marché")

col_vix, col_spx = st.columns(2)

# ── VIX ──────────────────────────────────────────────────────────────────────
with col_vix:
    if len(vix) > 0:
        cur_vix = float(vix.iloc[-1])
        ma20    = float(vix.rolling(20).mean().iloc[-1])
        ma52w   = float(vix.rolling(252).mean().iloc[-1]) if len(vix) >= 252 else cur_vix

        if cur_vix > 30:
            regime_vix = "🔴 Stress élevé (>30)"
        elif cur_vix > 20:
            regime_vix = "🟡 Incertitude modérée (20–30)"
        else:
            regime_vix = "🟢 Faible volatilité (<20)"

        st.metric("VIX actuel", f"{cur_vix:.1f}",
                  delta=f"MA20 : {ma20:.1f}  |  MA52S : {ma52w:.1f}",
                  delta_color="inverse")
        st.caption(regime_vix)

        fig_vix = go.Figure()
        fig_vix.add_trace(go.Scatter(
            x=vix.index, y=vix.values,
            fill="tozeroy",
            fillcolor="rgba(255, 80, 80, 0.12)",
            line=dict(color="tomato", width=1.5),
            name="VIX",
        ))
        fig_vix.add_hrect(y0=20, y1=30, fillcolor="yellow",
                          opacity=0.04, line_width=0)
        fig_vix.add_hrect(y0=30, y1=100, fillcolor="red",
                          opacity=0.04, line_width=0)
        fig_vix.add_hline(y=20, line_dash="dash", line_color="gold",
                          annotation_text="20", annotation_position="right")
        fig_vix.add_hline(y=30, line_dash="dash", line_color="tomato",
                          annotation_text="30", annotation_position="right")
        fig_vix.update_layout(
            title="VIX — 1 an",
            template="plotly_dark", height=330,
        )
        st.plotly_chart(fig_vix, use_container_width=True)
    else:
        st.warning("Données VIX indisponibles.")

# ── S&P 500 ───────────────────────────────────────────────────────────────────
with col_spx:
    if len(spx) > 0:
        ma50  = spx.rolling(50).mean()
        ma200 = spx.rolling(200).mean()
        cur_spx   = float(spx.iloc[-1])
        cur_ma50  = float(ma50.iloc[-1])
        cur_ma200 = float(ma200.iloc[-1])

        if cur_spx > cur_ma200 and cur_ma50 > cur_ma200:
            regime_spx = "🟢 Bull Market — MA50 > MA200 (Golden Cross)"
        elif cur_spx < cur_ma200 and cur_ma50 < cur_ma200:
            regime_spx = "🔴 Bear Market — sous MA200 (Death Cross)"
        else:
            regime_spx = "🟡 Zone de transition"

        ytd_pct = (cur_spx / float(spx.iloc[0]) - 1) * 100
        st.metric(
            "S&P 500",
            f"{cur_spx:,.0f}",
            delta=f"1A : {ytd_pct:+.1f}%",
            delta_color="normal",
        )
        st.caption(regime_spx)

        fig_spx = go.Figure()
        fig_spx.add_trace(go.Scatter(
            x=spx.index, y=spx.values,
            name="S&P 500", line=dict(color="cyan", width=2)
        ))
        fig_spx.add_trace(go.Scatter(
            x=ma50.index, y=ma50.values,
            name="MA50", line=dict(color="orange", width=1.5, dash="dash")
        ))
        fig_spx.add_trace(go.Scatter(
            x=ma200.index, y=ma200.values,
            name="MA200", line=dict(color="tomato", width=1.5, dash="dot")
        ))
        fig_spx.update_layout(
            title="S&P 500 & Moyennes Mobiles — 1 an",
            template="plotly_dark", height=330,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_spx, use_container_width=True)
    else:
        st.warning("Données S&P 500 indisponibles.")

# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY PANEL
# ═════════════════════════════════════════════════════════════════════════════
if available and "3M" in available:
    rf_now = latest["3M"] / 100
    erp = (latest.get("10Y", latest["3M"]) - latest["3M"]) / 100

    parts = [
        f"**Taux sans risque (T-Bill 3M) :** {rf_now * 100:.2f}%",
        f"**Prime de terme (10Y – 3M) :** {erp * 100:.2f}%",
    ]
    if len(vix) > 0:
        parts.append(f"**VIX :** {float(vix.iloc[-1]):.1f}")
    if len(spx) > 0:
        parts.append(f"**S&P 500 :** {float(spx.iloc[-1]):,.0f}")

    st.divider()
    st.info("  ·  ".join(parts))
