import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from scipy.optimize import minimize
from datetime import datetime, timedelta


@st.cache_data(show_spinner=False, ttl=3600)
def _load_prices(tickers_tuple: tuple, start: str, end: str) -> pd.DataFrame:
    tickers = list(tickers_tuple)
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


def _portfolio_stats(w: np.ndarray, mean_ret: np.ndarray, cov: np.ndarray, rf: float):
    ret = float(w @ mean_ret) * 252
    vol = float(np.sqrt(w @ cov @ w * 252))
    sharpe = (ret - rf) / vol if vol > 0 else 0.0
    return ret, vol, sharpe


def _max_sharpe(mean_ret: np.ndarray, cov: np.ndarray, rf: float, n: int) -> np.ndarray:
    def neg_sharpe(w):
        return -_portfolio_stats(w, mean_ret, cov, rf)[2]

    res = minimize(
        neg_sharpe,
        np.ones(n) / n,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"ftol": 1e-12, "maxiter": 2000},
    )
    return res.x


def _min_variance(cov: np.ndarray, n: int) -> np.ndarray:
    def port_var(w):
        return float(w @ cov @ w)

    res = minimize(
        port_var,
        np.ones(n) / n,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"ftol": 1e-12, "maxiter": 2000},
    )
    return res.x


def _monte_carlo(mean_ret: np.ndarray, cov: np.ndarray, rf: float, n: int, n_sim: int):
    rets = np.empty(n_sim)
    vols = np.empty(n_sim)
    sharpes = np.empty(n_sim)
    weights = np.empty((n_sim, n))
    for i in range(n_sim):
        w = np.random.dirichlet(np.ones(n))
        r, v, s = _portfolio_stats(w, mean_ret, cov, rf)
        rets[i], vols[i], sharpes[i] = r, v, s
        weights[i] = w
    return rets, vols, sharpes, weights


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


# ─────────────────────────────────────────────────────────────────────────────
st.title("📊 Optimiseur de Portefeuille — Markowitz")
st.caption("Frontière efficiente · Capital Market Line · Portefeuilles optimaux")

with st.form("markowitz_form"):
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        raw_input = st.text_input(
            "Tickers (séparés par des virgules)",
            value="SPY, QQQ, AGG, GLD, VNQ, EFA",
            help="Ex : AAPL, MSFT, AMZN  ou  SPY, QQQ, AGG, GLD",
        )
    with c2:
        period_years = st.selectbox(
            "Historique", [1, 3, 5, 10], index=2,
            format_func=lambda x: f"{x} an{'s' if x > 1 else ''}"
        )
    with c3:
        n_sim = st.selectbox("Simulations MC", [1000, 3000, 5000, 10000], index=2)

    submitted = st.form_submit_button("Optimiser ▶", type="primary", use_container_width=True)

if not submitted:
    st.info("Entrez vos tickers puis cliquez sur **Optimiser** pour lancer l'analyse.")
    st.stop()

# ── Data ──────────────────────────────────────────────────────────────────────
tickers = [t.strip().upper() for t in raw_input.split(",") if t.strip()]
if len(tickers) < 2:
    st.error("Entrez au moins 2 tickers.")
    st.stop()

end_str = datetime.today().strftime("%Y-%m-%d")
start_str = (datetime.today() - timedelta(days=period_years * 365)).strftime("%Y-%m-%d")

with st.spinner("Téléchargement des données historiques…"):
    prices = _load_prices(tuple(tickers), start_str, end_str)

valid = [t for t in tickers if t in prices.columns and prices[t].notna().sum() > 50]
if len(valid) < 2:
    st.error("Données insuffisantes. Vérifiez vos tickers.")
    st.stop()

removed = set(tickers) - set(valid)
if removed:
    st.warning(f"Tickers ignorés (données insuffisantes) : {', '.join(removed)}")

prices = prices[valid].dropna()
daily_ret = prices.pct_change().dropna()
mean_ret = daily_ret.mean().values
cov = daily_ret.cov().values
n = len(valid)

# ── Risk-free rate ─────────────────────────────────────────────────────────────
with st.spinner("Récupération du taux sans risque (T-Bill 3M)…"):
    rf = _get_rf()
st.caption(f"Taux sans risque (T-Bill 3M) : **{rf * 100:.2f}%**")

# ── Optimisation ──────────────────────────────────────────────────────────────
with st.spinner("Optimisation et simulation Monte Carlo…"):
    mc_rets, mc_vols, mc_sharpes, mc_weights = _monte_carlo(mean_ret, cov, rf, n, n_sim)
    w_sharpe = _max_sharpe(mean_ret, cov, rf, n)
    w_minvar = _min_variance(cov, n)

r_s, v_s, s_s = _portfolio_stats(w_sharpe, mean_ret, cov, rf)
r_m, v_m, s_m = _portfolio_stats(w_minvar, mean_ret, cov, rf)

# ── Capital Market Line ───────────────────────────────────────────────────────
cml_vols = np.linspace(0, mc_vols.max() * 1.15, 120)
cml_rets = rf + s_s * cml_vols

# ── Chart : Efficient Frontier ────────────────────────────────────────────────
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=mc_vols * 100, y=mc_rets * 100,
    mode="markers",
    marker=dict(
        color=mc_sharpes, colorscale="Viridis", size=3, opacity=0.5,
        colorbar=dict(title="Sharpe", thickness=12, len=0.65, x=1.02),
    ),
    name="Portefeuilles simulés",
    hovertemplate="Vol : %{x:.2f}%<br>Rend : %{y:.2f}%<extra></extra>",
))

fig.add_trace(go.Scatter(
    x=cml_vols * 100, y=cml_rets * 100,
    mode="lines",
    line=dict(color="rgba(255,255,255,0.45)", dash="dot", width=1.5),
    name="Capital Market Line",
    hoverinfo="skip",
))

fig.add_trace(go.Scatter(
    x=[v_s * 100], y=[r_s * 100],
    mode="markers+text",
    marker=dict(color="crimson", size=16, symbol="star",
                line=dict(color="white", width=1)),
    text=[f"Max Sharpe ({s_s:.2f})"],
    textposition="top right",
    textfont=dict(color="crimson"),
    name=f"Max Sharpe — {s_s:.2f}",
))

fig.add_trace(go.Scatter(
    x=[v_m * 100], y=[r_m * 100],
    mode="markers+text",
    marker=dict(color="deepskyblue", size=14, symbol="diamond",
                line=dict(color="white", width=1)),
    text=["Min Variance"],
    textposition="top right",
    textfont=dict(color="deepskyblue"),
    name="Min Variance",
))

fig.update_layout(
    title="Frontière Efficiente",
    xaxis_title="Volatilité annualisée (%)",
    yaxis_title="Rendement annualisé (%)",
    template="plotly_dark",
    height=520,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)
st.plotly_chart(fig, use_container_width=True)

# ── Optimal portfolios side-by-side ──────────────────────────────────────────
col1, col2 = st.columns(2)

for col, label, icon, w, r, v, s in [
    (col1, "Max Sharpe (Tangent)", "⭐", w_sharpe, r_s, v_s, s_s),
    (col2, "Min Variance", "💎", w_minvar, r_m, v_m, s_m),
]:
    with col:
        st.subheader(f"{icon} {label}")
        df = (
            pd.DataFrame({"Ticker": valid, "Poids (%)": (w * 100).round(2)})
            .sort_values("Poids (%)", ascending=False)
            .reset_index(drop=True)
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rendement ann.", f"{r * 100:.2f}%")
        m2.metric("Volatilité ann.", f"{v * 100:.2f}%")
        m3.metric("Sharpe Ratio", f"{s:.3f}")

# ── Correlation heatmap ───────────────────────────────────────────────────────
st.subheader("Matrice de Corrélation")
corr = daily_ret.corr()
fig_corr = px.imshow(
    corr,
    text_auto=".2f",
    color_continuous_scale="RdYlGn",
    zmin=-1, zmax=1,
    template="plotly_dark",
    title="Corrélations (rendements journaliers)",
)
fig_corr.update_layout(height=420)
st.plotly_chart(fig_corr, use_container_width=True)

# ── Individual asset stats ────────────────────────────────────────────────────
st.subheader("Statistiques individuelles")
rows = []
for i, t in enumerate(valid):
    r = float(mean_ret[i]) * 252
    v = float(daily_ret[t].std()) * np.sqrt(252)
    sh = (r - rf) / v if v > 0 else 0.0
    rows.append({
        "Ticker": t,
        "Rend. ann. (%)": round(r * 100, 2),
        "Vol. ann. (%)": round(v * 100, 2),
        "Sharpe": round(sh, 3),
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
