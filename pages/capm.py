import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from scipy import stats
from datetime import datetime, timedelta


@st.cache_data(show_spinner=False, ttl=3600)
def _load(ticker: str, benchmark: str, start: str, end: str) -> pd.DataFrame:
    tickers = list({ticker, benchmark})
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])
    else:
        close = raw[["Close"]].copy()
        close.columns = [tickers[0]]
    return close.dropna(how="all")


def _get_rf() -> float:
    try:
        raw = yf.download("^IRX", period="5d", auto_adjust=False, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            val = raw["Close"]["^IRX"].dropna().iloc[-1]
        else:
            val = raw["Close"].dropna().iloc[-1]
        return float(val) / 100
    except Exception:
        return 0.04


def _var(returns: pd.Series, alpha: float = 0.05):
    hist = float(np.percentile(returns, alpha * 100))
    mu, sigma = returns.mean(), returns.std()
    param = float(stats.norm.ppf(alpha, mu, sigma))
    cvar = float(returns[returns <= hist].mean())
    return hist, param, cvar


# ─────────────────────────────────────────────────────────────────────────────
st.title("📈 Analyse CAPM & Métriques de Risque")
st.caption("Beta · Alpha · Sharpe · Sortino · Treynor · Calmar · VaR · CVaR · Drawdown")

with st.form("capm_form"):
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        ticker = st.text_input("Actif à analyser", value="AAPL").upper().strip()
    with c2:
        benchmark = st.text_input("Benchmark", value="^GSPC").upper().strip()
    with c3:
        period_years = st.selectbox(
            "Période", [1, 3, 5, 10], index=2,
            format_func=lambda x: f"{x} an{'s' if x > 1 else ''}"
        )
    submitted = st.form_submit_button("Analyser ▶", type="primary", use_container_width=True)

if not submitted:
    st.info("Entrez un ticker et cliquez sur **Analyser**.")
    st.stop()

end_str = datetime.today().strftime("%Y-%m-%d")
start_str = (datetime.today() - timedelta(days=period_years * 365)).strftime("%Y-%m-%d")

with st.spinner("Téléchargement des données…"):
    prices = _load(ticker, benchmark, start_str, end_str)

if prices.empty or ticker not in prices.columns or benchmark not in prices.columns:
    st.error("Impossible de télécharger les données. Vérifiez les tickers.")
    st.stop()

with st.spinner("Calcul du taux sans risque…"):
    rf = _get_rf()
st.caption(f"Taux sans risque (T-Bill 3M) : **{rf * 100:.2f}%**")

# ── Returns ───────────────────────────────────────────────────────────────────
a_ret = prices[ticker].pct_change().dropna()
m_ret = prices[benchmark].pct_change().dropna()
aligned = pd.concat([a_ret, m_ret], axis=1).dropna()
aligned.columns = ["asset", "market"]

excess_a = aligned["asset"] - rf / 252
excess_m = aligned["market"] - rf / 252

# ── CAPM regression ───────────────────────────────────────────────────────────
beta, alpha_d, r_val, p_val, _ = stats.linregress(excess_m, excess_a)
r2 = r_val ** 2
alpha_ann = alpha_d * 252

ann_ret_a = aligned["asset"].mean() * 252
ann_ret_m = aligned["market"].mean() * 252
capm_exp = rf + beta * (ann_ret_m - rf)
te = (aligned["asset"] - aligned["market"]).std() * np.sqrt(252)
ir = (ann_ret_a - ann_ret_m) / te if te > 0 else 0.0

# ── Performance ratios ────────────────────────────────────────────────────────
ann_vol = aligned["asset"].std() * np.sqrt(252)
downside = aligned["asset"][aligned["asset"] < rf / 252]
dn_std = downside.std() * np.sqrt(252) if len(downside) > 1 else ann_vol

sharpe = (ann_ret_a - rf) / ann_vol if ann_vol > 0 else 0.0
sortino = (ann_ret_a - rf) / dn_std if dn_std > 0 else 0.0
treynor = (ann_ret_a - rf) / beta if beta != 0 else 0.0

cum = (1 + aligned["asset"]).cumprod()
roll_max = cum.cummax()
dd_series = (cum - roll_max) / roll_max
max_dd = float(dd_series.min())
calmar = ann_ret_a / abs(max_dd) if max_dd != 0 else 0.0

# ── VaR / CVaR ────────────────────────────────────────────────────────────────
hvar95, pvar95, cvar95 = _var(aligned["asset"], 0.05)
hvar99, pvar99, cvar99 = _var(aligned["asset"], 0.01)

# ═════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ═════════════════════════════════════════════════════════════════════════════

# ── CAPM block ────────────────────────────────────────────────────────────────
st.subheader("Modèle CAPM")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Beta (β)", f"{beta:.3f}",
          help="β > 1 : amplifie le marché  |  β < 1 : plus défensif")
c2.metric("Alpha (α) ann.", f"{alpha_ann * 100:.2f}%",
          help="Jensen's Alpha — surperformance ajustée du risque systématique")
c3.metric("R²", f"{r2:.3f}",
          help="Part de la variance de l'actif expliquée par le marché")
c4.metric("Tracking Error", f"{te * 100:.2f}%",
          help="Écart-type annualisé des rendements différentiels vs benchmark")
c5.metric("Information Ratio", f"{ir:.3f}",
          help="Alpha actif / Tracking Error")

delta_str = f"Réel : {ann_ret_a * 100:.2f}%  ({(ann_ret_a - capm_exp) * 100:+.2f}%)"
st.info(
    f"**Rendement CAPM attendu :** {capm_exp * 100:.2f}%  ·  {delta_str}"
)

# ── Performance ratios ────────────────────────────────────────────────────────
st.subheader("Ratios de Performance")
r1, r2c, r3, r4, r5 = st.columns(5)
r1.metric("Sharpe Ratio", f"{sharpe:.3f}",
          help="(Rend ann. – Rf) / Volatilité ann.")
r2c.metric("Sortino Ratio", f"{sortino:.3f}",
           help="(Rend ann. – Rf) / Volatilité baissière ann.")
r3.metric("Treynor Ratio", f"{treynor:.4f}",
          help="(Rend ann. – Rf) / Beta")
r4.metric("Calmar Ratio", f"{calmar:.3f}",
          help="Rendement ann. / |Max Drawdown|")
r5.metric("Max Drawdown", f"{max_dd * 100:.2f}%")

# ── VaR / CVaR ────────────────────────────────────────────────────────────────
st.subheader("Value at Risk — journalière")
v1, v2, v3, v4, v5, v6 = st.columns(6)
v1.metric("VaR 95% hist.", f"{hvar95 * 100:.2f}%")
v2.metric("VaR 95% param.", f"{pvar95 * 100:.2f}%")
v3.metric("CVaR 95%", f"{cvar95 * 100:.2f}%",
          help="Expected Shortfall : perte moyenne conditionnelle au-delà du VaR")
v4.metric("VaR 99% hist.", f"{hvar99 * 100:.2f}%")
v5.metric("VaR 99% param.", f"{pvar99 * 100:.2f}%")
v6.metric("CVaR 99%", f"{cvar99 * 100:.2f}%")

# ── Row 1 : performance + distribution ───────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    norm_a = (1 + aligned["asset"]).cumprod()
    norm_m = (1 + aligned["market"]).cumprod()
    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=norm_a.index, y=norm_a.values,
        name=ticker, line=dict(color="cyan", width=2)
    ))
    fig_perf.add_trace(go.Scatter(
        x=norm_m.index, y=norm_m.values,
        name=benchmark, line=dict(color="orange", width=1.5, dash="dash")
    ))
    fig_perf.update_layout(
        title=f"Performance comparative (base 1) — {ticker} vs {benchmark}",
        template="plotly_dark", height=330,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_perf, use_container_width=True)

with col_r:
    ret_pct = aligned["asset"] * 100
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=ret_pct, nbinsx=80,
        marker_color="steelblue", opacity=0.8, name="Rendements"
    ))
    # Normal fit overlay
    x_fit = np.linspace(ret_pct.min(), ret_pct.max(), 200)
    pdf = stats.norm.pdf(x_fit, ret_pct.mean(), ret_pct.std())
    scale = len(ret_pct) * (ret_pct.max() - ret_pct.min()) / 80
    fig_dist.add_trace(go.Scatter(
        x=x_fit, y=pdf * scale,
        mode="lines", line=dict(color="white", width=1.5), name="Loi normale"
    ))
    fig_dist.add_vline(x=hvar95 * 100, line_color="orange", line_dash="dash",
                       annotation_text="VaR 95%", annotation_position="top right")
    fig_dist.add_vline(x=hvar99 * 100, line_color="red", line_dash="dash",
                       annotation_text="VaR 99%", annotation_position="top right")
    fig_dist.update_layout(
        title=f"Distribution des rendements journaliers — {ticker}",
        xaxis_title="Rendement (%)",
        template="plotly_dark", height=330,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_dist, use_container_width=True)

# ── Underwater (drawdown) chart ───────────────────────────────────────────────
fig_dd = go.Figure()
fig_dd.add_trace(go.Scatter(
    x=dd_series.index, y=dd_series.values * 100,
    fill="tozeroy",
    fillcolor="rgba(220, 50, 47, 0.22)",
    line=dict(color="tomato", width=1),
    name="Drawdown",
))
fig_dd.update_layout(
    title=f"Underwater Chart — {ticker}  (Max DD : {max_dd * 100:.2f}%)",
    yaxis_title="Drawdown (%)",
    template="plotly_dark",
    height=280,
)
st.plotly_chart(fig_dd, use_container_width=True)

# ── Rolling metrics ───────────────────────────────────────────────────────────
window = max(20, min(60, len(aligned) // 8))

roll_beta_s = (
    aligned["asset"].rolling(window).cov(aligned["market"])
    / aligned["market"].rolling(window).var()
)
roll_vol_s = aligned["asset"].rolling(window).std() * np.sqrt(252) * 100

col_l, col_r = st.columns(2)

with col_l:
    fig_rb = go.Figure()
    fig_rb.add_trace(go.Scatter(
        x=roll_beta_s.index, y=roll_beta_s.values,
        line=dict(color="cyan", width=1.5), name=f"Beta glissant ({window}j)"
    ))
    fig_rb.add_hline(y=1.0, line_dash="dash", line_color="gray",
                     annotation_text="β = 1")
    fig_rb.add_hline(y=beta, line_dash="dot", line_color="crimson",
                     annotation_text=f"Moy. {beta:.2f}")
    fig_rb.update_layout(
        title=f"Beta glissant — fenêtre {window}j",
        template="plotly_dark", height=300,
    )
    st.plotly_chart(fig_rb, use_container_width=True)

with col_r:
    fig_rv = go.Figure()
    fig_rv.add_trace(go.Scatter(
        x=roll_vol_s.index, y=roll_vol_s.values,
        line=dict(color="orange", width=1.5), name=f"Vol. ann. ({window}j)"
    ))
    fig_rv.add_hline(y=ann_vol * 100, line_dash="dot", line_color="crimson",
                     annotation_text=f"Moy. {ann_vol * 100:.1f}%")
    fig_rv.update_layout(
        title=f"Volatilité annualisée glissante — fenêtre {window}j",
        yaxis_title="%",
        template="plotly_dark", height=300,
    )
    st.plotly_chart(fig_rv, use_container_width=True)
