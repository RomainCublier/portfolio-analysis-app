"""
Analyse des Risques & Performance

Sections :
  1. Vue d'ensemble performance (rendement cumulé vs benchmark)
  2. Ratios de performance (Sharpe, Sortino, Treynor, Calmar, Omega, M², IR)
  3. VaR / CVaR — 4 méthodes (historique, normale, Cornish-Fisher, Monte Carlo)
  4. Analyse des drawdowns
  5. Attribution factorielle (CAPM + Fama-French 3F + MOM)
  6. Scénarios de stress (GFC, COVID, 2022 taux…)
  7. Décomposition du risque (contributions, corrélations)
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from scipy import stats as sp_stats
from datetime import datetime, timedelta

from config.settings import CSS, C, CHART_COLORS, PLOTLY
import utils.charts as ch
from core.factor_model import get_factors, factor_regression, rolling_beta, rolling_alpha
from core.optimization import risk_contributions

st.markdown(CSS, unsafe_allow_html=True)

# ── Loaders ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _load(tickers: tuple, start: str, end: str) -> pd.DataFrame:
    raw = yf.download(list(tickers), start=start, end=end,
                      auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
        if isinstance(prices, pd.Series):
            prices = prices.to_frame(name=tickers[0])
    else:
        prices = raw[["Close"]].copy()
        prices.columns = [tickers[0]]
    return prices.dropna(how="all")


@st.cache_data(ttl=3600, show_spinner=False)
def _load_factors(start: str, end: str, rf: float) -> pd.DataFrame:
    return get_factors(start, end, rf_annual=rf)


@st.cache_data(ttl=3600, show_spinner=False)
def _get_rf() -> float:
    try:
        raw = yf.download("^IRX", period="5d", auto_adjust=False, progress=False)
        v = (raw["Close"]["^IRX"] if isinstance(raw.columns, pd.MultiIndex)
             else raw["Close"]).dropna().iloc[-1]
        return float(v) / 100
    except Exception:
        return 0.04


# ── Quantitative helpers ──────────────────────────────────────────────────────
def _perf_metrics(rets: pd.Series, rf: float) -> dict:
    """Comprehensive set of performance metrics."""
    ann_ret = rets.mean() * 252
    ann_vol = rets.std()  * np.sqrt(252)
    rf_d    = rf / 252

    # Downside deviation (Sortino)
    dn      = rets[rets < rf_d] - rf_d
    dn_std  = dn.std() * np.sqrt(252) if len(dn) > 1 else ann_vol

    # Cumulative & drawdown
    cum     = (1 + rets).cumprod()
    roll_mx = cum.cummax()
    dd      = (cum - roll_mx) / roll_mx
    max_dd  = float(dd.min())

    # CAPM via simple regression (vs market, done separately)
    sharpe  = (ann_ret - rf) / ann_vol   if ann_vol > 1e-8 else 0.0
    sortino = (ann_ret - rf) / dn_std    if dn_std  > 1e-8 else 0.0
    calmar  = ann_ret / abs(max_dd)      if abs(max_dd) > 1e-8 else 0.0

    # Omega ratio: P(gains > 0) / P(losses < 0) weighted
    gains  = rets[rets > rf_d] - rf_d
    losses = rf_d - rets[rets <= rf_d]
    omega  = gains.sum() / losses.sum() if losses.sum() > 1e-8 else np.inf

    # Skewness & excess kurtosis
    skew = float(rets.skew())
    kurt = float(rets.kurtosis())

    # Ulcer Index (RMS of drawdowns)
    ulcer = float(np.sqrt(np.mean(dd ** 2)))

    return {
        "Rendement ann.":    ann_ret,
        "Volatilité ann.":   ann_vol,
        "Sharpe":            sharpe,
        "Sortino":           sortino,
        "Calmar":            calmar,
        "Omega":             omega,
        "Max Drawdown":      max_dd,
        "Ulcer Index":       ulcer,
        "Skewness":          skew,
        "Kurtosis excès":    kurt,
        "Nb. observations":  len(rets),
    }


def _var_suite(rets: pd.Series, alpha_list=(0.05, 0.01)) -> pd.DataFrame:
    """
    Historical, Parametric (Normal), Cornish-Fisher, Monte Carlo VaR & CVaR.
    """
    rows = []
    mu_d  = rets.mean()
    sig_d = rets.std()
    s     = rets.skew()
    k     = rets.kurtosis()

    for alpha in alpha_list:
        conf = f"{int((1-alpha)*100)}%"

        # 1. Historical
        h_var  = float(np.percentile(rets, alpha * 100))
        h_cvar = float(rets[rets <= h_var].mean())

        # 2. Parametric (Normal)
        z_n     = sp_stats.norm.ppf(alpha)
        p_var   = float(mu_d + z_n * sig_d)
        p_cvar  = float(mu_d - sig_d * sp_stats.norm.pdf(z_n) / alpha)

        # 3. Cornish-Fisher (adjusted z for skewness & kurtosis)
        z_cf   = (z_n
                  + (z_n**2 - 1) * s / 6
                  + (z_n**3 - 3*z_n) * k / 24
                  - (2*z_n**3 - 5*z_n) * s**2 / 36)
        cf_var  = float(mu_d + z_cf * sig_d)
        cf_cvar = float(rets[rets <= cf_var].mean()) if (rets <= cf_var).any() else h_cvar

        # 4. Monte Carlo
        rng    = np.random.default_rng(0)
        sim    = rng.normal(mu_d, sig_d, 50_000)
        mc_var  = float(np.percentile(sim, alpha * 100))
        mc_cvar = float(sim[sim <= mc_var].mean())

        rows.append({
            "Conf.":              conf,
            "VaR Hist.":          h_var,
            "CVaR Hist.":         h_cvar,
            "VaR Param. (N)":     p_var,
            "CVaR Param. (N)":    p_cvar,
            "VaR Cornish-Fisher": cf_var,
            "CVaR C-F":           cf_cvar,
            "VaR Monte Carlo":    mc_var,
            "CVaR Monte Carlo":   mc_cvar,
        })
    return pd.DataFrame(rows)


STRESS_SCENARIOS = [
    ("GFC 2008",           "2008-09-01", "2009-03-09"),
    ("Crise EU 2011",      "2011-07-22", "2011-10-03"),
    ("Taper Tantrum 2013", "2013-05-22", "2013-06-24"),
    ("Vente Covid 2020",   "2020-02-20", "2020-03-23"),
    ("Rate Spike 2022",    "2022-01-01", "2022-10-15"),
    ("SVB Crisis 2023",    "2023-03-06", "2023-03-24"),
]


def _stress_returns(prices: pd.DataFrame, tickers: list,
                    weights: np.ndarray) -> list:
    """Apply stress scenario windows to the portfolio."""
    results = []
    for name, start, end in STRESS_SCENARIOS:
        window = prices[tickers].loc[start:end].dropna()
        if len(window) < 2:
            results.append({"Scénario": name, "Durée (jours)": 0,
                            "Rendement portefeuille (%)": np.nan,
                            "Rendement max journalier (%)": np.nan,
                            "Volatilité annualisée (%)": np.nan})
            continue
        daily_rets = window.pct_change().dropna()
        port_rets  = (daily_rets * weights).sum(axis=1)
        total_ret  = float((1 + port_rets).prod() - 1)
        max_1d     = float(port_rets.min())
        vol        = float(port_rets.std() * np.sqrt(252))
        results.append({
            "Scénario":                    name,
            "Durée (jours)":               len(window),
            "Rendement portefeuille (%)":  round(total_ret * 100, 2),
            "Pire jour (%)":               round(max_1d * 100, 2),
            "Volatilité ann. (%)":         round(vol * 100, 2),
        })
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════════════════════════════════
st.title("Analyse des Risques & Performance")
st.caption(
    "VaR / CVaR · Ratios de performance · Modèles factoriels · "
    "Scénarios de stress · Décomposition du risque"
)

# ── Input form ────────────────────────────────────────────────────────────────
with st.form("risk_form"):
    c1, c2 = st.columns([3, 1])
    with c1:
        raw_t = st.text_input(
            "Tickers du portefeuille (séparés par des virgules)",
            value="SPY, AGG, GLD, TLT",
            help="Pour un portefeuille multi-actifs, entrez chaque ticker."
        )
    with c2:
        bench_t = st.text_input("Benchmark", value="^GSPC")

    c3, c4, c5 = st.columns(3)
    with c3:
        raw_w = st.text_input(
            "Poids (%, séparés par des virgules — laisser vide = équipondéré)",
            value="",
            help="Ex : 40, 30, 20, 10  (doit sommer à 100)"
        )
    with c4:
        period_y = st.selectbox("Période d'analyse",
                                [1, 3, 5, 10], index=2,
                                format_func=lambda x: f"{x} an{'s' if x > 1 else ''}")
    with c5:
        roll_w = st.selectbox("Fenêtre glissante",
                              [21, 63, 126], index=1,
                              format_func=lambda x: f"{x}j (~{x//21}M)")

    run = st.form_submit_button("Analyser ▶", type="primary", use_container_width=True)

if not run:
    st.info("Configurez votre portefeuille et cliquez sur **Analyser**.")
    st.stop()

# ── Prepare data ──────────────────────────────────────────────────────────────
tickers = [t.strip().upper() for t in raw_t.split(",") if t.strip()]
bench   = bench_t.strip().upper()
all_t   = list(dict.fromkeys(tickers + [bench]))

end_s   = datetime.today().strftime("%Y-%m-%d")
start_s = (datetime.today() - timedelta(days=period_y * 365)).strftime("%Y-%m-%d")
# For stress scenarios we need a longer history
start_long = "2007-01-01"

with st.spinner("Téléchargement des données…"):
    prices_long = _load(tuple(all_t), start_long, end_s)
    rf          = _get_rf()

prices = prices_long.loc[start_s:] if start_s in prices_long.index or prices_long.index[0].strftime("%Y-%m-%d") >= start_s else prices_long

valid = [t for t in tickers if t in prices.columns and prices[t].notna().sum() > 60]
if len(valid) == 0:
    st.error("Aucun actif valide. Vérifiez vos tickers.")
    st.stop()

# Weights
if raw_w.strip():
    try:
        w_raw = [float(x) for x in raw_w.split(",") if x.strip()]
        if len(w_raw) != len(valid):
            st.warning(f"Nombre de poids ({len(w_raw)}) ≠ actifs valides ({len(valid)}). Équipondération appliquée.")
            weights = np.ones(len(valid)) / len(valid)
        else:
            weights = np.array(w_raw)
            weights /= weights.sum()
    except ValueError:
        st.warning("Poids invalides. Équipondération appliquée.")
        weights = np.ones(len(valid)) / len(valid)
else:
    weights = np.ones(len(valid)) / len(valid)

# Portfolio returns
prices_v = prices[valid].dropna()
rets_df  = prices_v.pct_change().dropna()
port_ret = (rets_df * weights).sum(axis=1).rename("Portfolio")

# Benchmark returns
bench_ret = pd.Series(dtype=float)
if bench in prices.columns:
    bench_ret = prices[bench].dropna().pct_change().dropna().rename(bench)

n_obs = len(port_ret)
rf_d  = rf / 252

st.caption(
    f"Taux sans risque : **{rf*100:.2f}%**  ·  "
    f"Portefeuille : {', '.join([f'{t} {w*100:.0f}%' for t, w in zip(valid, weights)])}  ·  "
    f"{n_obs:,} observations ({rets_df.index[0].strftime('%d/%m/%Y')} → {rets_df.index[-1].strftime('%d/%m/%Y')})"
)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. PERFORMANCE OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Performance & Rendement")

cum_port  = (1 + port_ret).cumprod()
cum_bench = (1 + bench_ret).cumprod() if len(bench_ret) > 0 else pd.Series()

# Align
series_perf = {"Portefeuille": cum_port}
if len(cum_bench) > 0:
    aligned_b = cum_bench.reindex(cum_port.index, method="ffill")
    series_perf[bench] = aligned_b

fig_cum = ch.line(series_perf, title="Valeur liquidative normalisée (base 1)",
                  y_label="VL", height=360)
st.plotly_chart(fig_cum, use_container_width=True)

# KPI row
m = _perf_metrics(port_ret, rf)
cols = st.columns(6)
cols[0].metric("Rendement ann.",  f"{m['Rendement ann.']*100:.2f}%")
cols[1].metric("Volatilité ann.", f"{m['Volatilité ann.']*100:.2f}%")
cols[2].metric("Sharpe Ratio",    f"{m['Sharpe']:.3f}")
cols[3].metric("Sortino Ratio",   f"{m['Sortino']:.3f}")
cols[4].metric("Max Drawdown",    f"{m['Max Drawdown']*100:.2f}%")
cols[5].metric("Calmar Ratio",    f"{m['Calmar']:.3f}")

# Full ratio table
st.markdown("## Ratios de Performance Complets")

# Benchmark metrics for comparison
ratios_rows = []
for label, rets_s in [("Portefeuille", port_ret)] + (
        [(bench, bench_ret)] if len(bench_ret) > 0 else []):
    mm = _perf_metrics(rets_s, rf)
    # Treynor (needs beta vs benchmark)
    treynor = np.nan
    if label != bench and len(bench_ret) > 0:
        aligned = pd.concat([rets_s, bench_ret], axis=1).dropna()
        if len(aligned) > 10 and aligned.iloc[:,1].var() > 1e-12:
            beta_v = np.cov(aligned.iloc[:,0], aligned.iloc[:,1])[0,1] / aligned.iloc[:,1].var()
            treynor = (mm["Rendement ann."] - rf) / beta_v if abs(beta_v) > 1e-6 else np.nan
    # M² (Modigliani-Modigliani)
    if label != bench and len(bench_ret) > 0:
        bench_m = _perf_metrics(bench_ret, rf)
        m2 = (mm["Sharpe"] - bench_m["Sharpe"]) * bench_m["Volatilité ann."] + rf
    else:
        m2 = np.nan

    ratios_rows.append({
        "Indicateur":            label,
        "Rend. ann. (%)":        round(mm["Rendement ann."] * 100, 2),
        "Vol. ann. (%)":         round(mm["Volatilité ann."] * 100, 2),
        "Sharpe":                round(mm["Sharpe"], 3),
        "Sortino":               round(mm["Sortino"], 3),
        "Treynor":               round(treynor, 4) if not np.isnan(treynor) else "—",
        "Calmar":                round(mm["Calmar"], 3),
        "Omega":                 round(mm["Omega"], 3) if mm["Omega"] != np.inf else ">10",
        "M² (%)":                round(m2 * 100, 2) if not np.isnan(m2) else "—",
        "Max DD (%)":            round(mm["Max Drawdown"] * 100, 2),
        "Ulcer Index":           round(mm["Ulcer Index"] * 100, 4),
        "Skewness":              round(mm["Skewness"], 3),
        "Kurtosis excès":        round(mm["Kurtosis excès"], 3),
    })

st.dataframe(pd.DataFrame(ratios_rows).set_index("Indicateur"),
             use_container_width=True)

st.caption(
    "**Sortino** : pénalise uniquement la volatilité baissière.  "
    "**Treynor** : rendement par unité de risque systématique (β).  "
    "**Omega** : rapport gains/pertes pondérés.  "
    "**M²** : rendement hypothétique du portefeuille si sa volatilité équivalait à celle du marché.  "
    "**Ulcer Index** : profondeur et durée des drawdowns combinées."
)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. VaR / CVaR
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Value at Risk & Expected Shortfall")

df_var = _var_suite(port_ret)

# Format as percentages
pct_cols = [c for c in df_var.columns if c != "Conf."]
styled_var = df_var.style.format({c: lambda v: f"{v*100:.3f}%" for c in pct_cols})
st.dataframe(styled_var, use_container_width=True, hide_index=True)

st.caption(
    "**VaR historique** : quantile empirique des P&L journaliers.  "
    "**VaR Normal** : assume une distribution gaussienne des rendements.  "
    "**Cornish-Fisher** : corrige pour l'asymétrie et l'excès de kurtosis (leptokurticité).  "
    "**Monte Carlo** : simulation de 50 000 scénarios (distribution normale paramétrée)."
)

# Distribution chart with VaR lines
vlines_95 = [
    (float(df_var.loc[0, "VaR Hist."]), C["orange"], "VaR 95% Hist."),
    (float(df_var.loc[0, "VaR Cornish-Fisher"]), C["purple"], "VaR 95% CF"),
]
fig_hist = ch.histogram(port_ret, title="Distribution des rendements journaliers",
                        vlines=vlines_95, height=320)
st.plotly_chart(fig_hist, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. DRAWDOWNS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Analyse des Drawdowns")

dd_series = (cum_port - cum_port.cummax()) / cum_port.cummax()

fig_dd = ch.area(dd_series * 100,
                 title=f"Underwater Chart — Max DD : {m['Max Drawdown']*100:.2f}%",
                 y_label="Drawdown (%)", height=280)
st.plotly_chart(fig_dd, use_container_width=True)

# Top 5 drawdown periods
st.markdown("#### Principaux épisodes de drawdown")
dd_episodes = []
in_dd, start_dd, prev = False, None, 0.0
for dt, v in dd_series.items():
    if v < -0.01 and not in_dd:
        in_dd, start_dd, trough = True, dt, v
    elif in_dd:
        if v < trough:
            trough = v
        if v >= -0.001:
            in_dd = False
            dd_episodes.append({"Début": start_dd, "Trough": trough, "Fin": dt,
                                 "Durée (j)": (dt - start_dd).days})
            trough = 0.0

dd_episodes.sort(key=lambda x: x["Trough"])
top5 = dd_episodes[:5]
if top5:
    df_dd = pd.DataFrame(top5)
    df_dd["Max Drawdown (%)"] = (df_dd["Trough"] * 100).round(2)
    df_dd = df_dd.drop(columns=["Trough"])
    df_dd["Début"] = df_dd["Début"].dt.strftime("%d/%m/%Y")
    df_dd["Fin"]   = df_dd["Fin"].dt.strftime("%d/%m/%Y")
    st.dataframe(df_dd, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. FACTOR ATTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Attribution Factorielle (CAPM + Fama-French 3F + MOM)")

with st.spinner("Calcul du modèle factoriel…"):
    factors = _load_factors(start_s, end_s, rf)

if not factors.empty:
    res = factor_regression(port_ret, factors, rf_daily=rf_d)
else:
    res = {}

if res:
    st.markdown("#### Modèle CAPM (1 facteur)")
    # CAPM only (MKT factor)
    if len(bench_ret) > 0:
        aligned = pd.concat([port_ret - rf_d, bench_ret - rf_d], axis=1).dropna()
        if len(aligned) > 20:
            slope, intercept, r_val, p_val, se = sp_stats.linregress(
                aligned.iloc[:, 1], aligned.iloc[:, 0])
            beta_capm  = float(slope)
            alpha_capm = float(intercept) * 252
            r2_capm    = float(r_val ** 2)
            bench_ann  = float(bench_ret.mean()) * 252
            capm_exp   = rf + beta_capm * (bench_ann - rf)
            te_ann     = float((port_ret - bench_ret.reindex(port_ret.index, method="ffill")).std() * np.sqrt(252))
            ir         = (m["Rendement ann."] - bench_ann) / te_ann if te_ann > 0 else 0.0

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Beta (β)", f"{beta_capm:.3f}",
                      help="Sensibilité au marché. β>1 amplifie les mouvements du benchmark.")
            c2.metric("Alpha (α ann.)", f"{alpha_capm*100:.2f}%",
                      help="Jensen's Alpha : surperformance ajustée du risque systématique.")
            c3.metric("R²", f"{r2_capm:.3f}",
                      help="Part de la variance expliquée par le marché.")
            c4.metric("Tracking Error", f"{te_ann*100:.2f}%")
            c5.metric("Information Ratio", f"{ir:.3f}")

            delta = m["Rendement ann."] * 100 - capm_exp * 100
            st.info(
                f"Rendement CAPM attendu : **{capm_exp*100:.2f}%**  ·  "
                f"Rendement réel : **{m['Rendement ann.']*100:.2f}%**  ·  "
                f"Écart (alpha) : **{delta:+.2f}%**"
            )

    st.markdown("#### Modèle Multi-facteurs (Fama-French + MOM)")
    factor_names = list(res["betas"].keys())

    c1, c2, c3 = st.columns(3)
    c1.metric("Alpha ann. (α)",
              f"{res['alpha_ann']*100:.2f}%",
              help="t-stat = " + f"{res['t_alpha']:.2f}")
    c2.metric("R²", f"{res['r_squared']:.3f}")
    c3.metric("R² ajusté", f"{res['adj_r2']:.3f}")

    # Beta table
    beta_rows = []
    for fname in factor_names:
        beta_rows.append({
            "Facteur": fname,
            "Beta": round(res["betas"][fname], 4),
            "t-stat": round(res["t_stats"].get(fname, np.nan), 2),
            "Significatif (|t|>2)": "✓" if abs(res["t_stats"].get(fname, 0)) > 2 else "",
        })
    st.dataframe(pd.DataFrame(beta_rows), use_container_width=True, hide_index=True)
    st.caption(
        "**MKT** : facteur de marché (excès de rendement SPY).  "
        "**SMB** : Small-minus-Big (prime de taille).  "
        "**HML** : High-minus-Low (prime de valeur).  "
        "**MOM** : Momentum (MTUM ETF)."
    )

    # Volatility decomposition
    idio_pct = (res["idio_vol"] / m["Volatilité ann."] * 100) if m["Volatilité ann."] > 0 else 0
    syst_pct = 100 - idio_pct
    fig_decomp = ch.donut(
        ["Risque systématique", "Risque idiosyncratique"],
        [max(0, syst_pct), max(0, idio_pct)],
        title=f"Décomposition de la volatilité  (σ = {m['Volatilité ann.']*100:.2f}%)",
        height=300,
    )
    st.plotly_chart(fig_decomp, use_container_width=True)

    # Rolling metrics
    st.markdown("#### Métriques glissantes")
    if len(bench_ret) > 0:
        roll_b = rolling_beta(port_ret, bench_ret.reindex(port_ret.index, method="ffill"),
                              rf_daily=rf_d, window=roll_w)
        roll_a = rolling_alpha(port_ret, bench_ret.reindex(port_ret.index, method="ffill"),
                               rf_daily=rf_d, window=roll_w)
        roll_vol = port_ret.rolling(roll_w).std() * np.sqrt(252)

        col_rb, col_rv = st.columns(2)
        with col_rb:
            fig_rb = go.Figure()
            fig_rb.add_trace(go.Scatter(
                x=roll_b.index, y=roll_b.values,
                line=dict(color=C["blue"], width=1.5), name=f"Beta ({roll_w}j)",
            ))
            if not np.isnan(float(slope)):
                fig_rb.add_hline(y=beta_capm, line_dash="dot", line_color=C["red"],
                                 annotation_text=f"Moy. {beta_capm:.2f}")
            fig_rb.add_hline(y=1.0, line_dash="dash", line_color=C["muted"])
            fig_rb.update_layout(**PLOTLY,
                                 title_text=f"Beta glissant ({roll_w}j)",
                                 height=300, showlegend=False)
            st.plotly_chart(fig_rb, use_container_width=True)

        with col_rv:
            fig_rv = go.Figure()
            fig_rv.add_trace(go.Scatter(
                x=roll_vol.index, y=roll_vol.values * 100,
                line=dict(color=C["orange"], width=1.5), name=f"Vol. ({roll_w}j)",
            ))
            fig_rv.add_hline(y=m["Volatilité ann."] * 100, line_dash="dot",
                             line_color=C["red"],
                             annotation_text=f"Moy. {m['Volatilité ann.']*100:.1f}%")
            fig_rv.update_layout(**PLOTLY,
                                 title_text=f"Volatilité ann. glissante ({roll_w}j)",
                                 yaxis_title="%", height=300, showlegend=False)
            st.plotly_chart(fig_rv, use_container_width=True)

else:
    st.warning("Données factorielles insuffisantes pour la période sélectionnée.")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. STRESS SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Scénarios de Stress Historiques")
st.caption(
    "Rendement réel du portefeuille reconstitué sur chaque fenêtre de crise, "
    "en appliquant les pondérations actuelles à l'historique des prix."
)

stress_results = _stress_returns(prices_long, valid, weights)
df_stress = pd.DataFrame(stress_results)

# Style
def _s_style(v):
    if isinstance(v, float) and not pd.isna(v):
        bg = "rgba(34,197,94,0.10)" if v >= 0 else "rgba(239,68,68,0.10)"
        col = C["green"] if v >= 0 else C["red"]
        return f"background-color:{bg};color:{col};font-weight:600"
    return ""

styled_stress = (df_stress.set_index("Scénario")
                 .style
                 .applymap(_s_style, subset=["Rendement portefeuille (%)", "Pire jour (%)"])
                 .format({"Rendement portefeuille (%)": lambda v: f"{v:+.2f}%" if not pd.isna(v) else "—",
                           "Pire jour (%)":             lambda v: f"{v:+.2f}%" if not pd.isna(v) else "—",
                           "Volatilité ann. (%)":       lambda v: f"{v:.2f}%"  if not pd.isna(v) else "—"}))
st.dataframe(styled_stress, use_container_width=True)

valid_stress = [r for r in stress_results if not pd.isna(r["Rendement portefeuille (%)"])]
if valid_stress:
    fig_stress = ch.waterfall(
        [r["Scénario"] for r in valid_stress],
        [r["Rendement portefeuille (%)"] for r in valid_stress],
        title="Impact des crises historiques sur le portefeuille",
        height=340,
    )
    st.plotly_chart(fig_stress, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. RISK DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Décomposition du Risque")

col_a, col_b = st.columns(2)

with col_a:
    # Risk contributions
    if len(valid) > 1:
        Sigma_est = rets_df.cov().values
        rc = risk_contributions(weights, Sigma_est) * 100
        rc_df = pd.DataFrame({
            "Actif":                valid,
            "Poids (%)":            (weights * 100).round(2),
            "Contribution risque (%)": rc.round(2),
            "Ratio (RC/Poids)":     (rc / (weights * 100 + 1e-10)).round(3),
        }).sort_values("Contribution risque (%)", ascending=False)
        st.markdown("#### Contributions au risque")
        st.dataframe(rc_df, use_container_width=True, hide_index=True)

        fig_rc = go.Figure()
        fig_rc.add_trace(go.Bar(
            x=valid, y=weights * 100,
            name="Poids (%)", marker_color=C["blue"], opacity=0.7,
        ))
        fig_rc.add_trace(go.Bar(
            x=valid, y=rc,
            name="Contribution risque (%)", marker_color=C["gold"],
        ))
        fig_rc.update_layout(**PLOTLY, barmode="group",
                             title_text="Poids vs Contribution au risque",
                             yaxis_title="%", height=300)
        st.plotly_chart(fig_rc, use_container_width=True)

with col_b:
    # Correlation matrix
    if len(valid) > 1:
        st.markdown("#### Corrélations")
        fig_corr = ch.heatmap(rets_df.corr(),
                              title="Matrice de corrélation (rendements journaliers)",
                              height=max(280, 35 * len(valid) + 60))
        st.plotly_chart(fig_corr, use_container_width=True)
