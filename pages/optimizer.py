"""
Construction de Portefeuille

Méthodes d'optimisation :
  MVO   — Markowitz (Mean-Variance Optimization)
  ERC   — Equal Risk Contribution (Risk Parity)
  HRP   — Hierarchical Risk Parity  (Lopez de Prado)
  BL    — Black-Litterman

Affiche également la frontière efficiente et un tableau comparatif.
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from scipy.cluster import hierarchy as sch
from datetime import datetime, timedelta

from config.settings import CSS, C, CHART_COLORS, PLOTLY
import utils.charts as ch
from core.optimization import (
    port_stats, risk_contributions, monte_carlo, efficient_frontier,
    max_sharpe, min_variance, erc, hrp, black_litterman, max_diversification,
)

st.markdown(CSS, unsafe_allow_html=True)

# ── Data loader ───────────────────────────────────────────────────────────────
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
def _get_rf() -> float:
    try:
        raw = yf.download("^IRX", period="5d", auto_adjust=False, progress=False)
        v = (raw["Close"]["^IRX"] if isinstance(raw.columns, pd.MultiIndex)
             else raw["Close"]).dropna().iloc[-1]
        return float(v) / 100
    except Exception:
        return 0.04


# ── Helpers ───────────────────────────────────────────────────────────────────
def _metrics_row(w, mu, Sigma, rf, tickers, label):
    r, v, s = port_stats(w, mu, Sigma, rf)
    rc = risk_contributions(w, Sigma)
    max_dd = _approx_maxdd(w, mu, Sigma)
    return {
        "Méthode":       label,
        "Rend. ann.":    r,
        "Vol. ann.":     v,
        "Sharpe":        s,
        "Max RC (%)":    float(rc.max()) * 100,
        "Conc. (HHI)":  float((w ** 2).sum()),
    }


def _approx_maxdd(w, mu, Sigma, horizon=252):
    """Approximation analytique du Max Drawdown (Magdon-Ismail 2004)."""
    r, v, _ = port_stats(w, mu, Sigma)
    if v < 1e-6:
        return 0.0
    mu_d  = r / 252
    sig_d = v / np.sqrt(252)
    return float(-0.5 * v ** 2 / (r if r > 0 else 1e-4))   # rough lower bound


def _weight_df(tickers, weights, label="Poids (%)"):
    return (pd.DataFrame({"Ticker": tickers, label: (weights * 100).round(2)})
            .sort_values(label, ascending=False)
            .reset_index(drop=True))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════
st.title("Construction de Portefeuille")
st.caption("Optimisation multi-méthodes · Frontière efficiente · Analyse de risque")

# ── Input form ────────────────────────────────────────────────────────────────
with st.form("opt_form"):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
        raw_tickers = st.text_input(
            "Tickers (séparés par des virgules)",
            value="SPY, QQQ, AGG, GLD, VNQ, EFA, HYG, TLT",
            help="Exemples : SPY, QQQ, AGG, GLD  |  AAPL, MSFT, AMZN, META",
        )
    with c2:
        period_y = st.selectbox("Historique d'estimation",
                                [1, 3, 5, 10], index=2,
                                format_func=lambda x: f"{x} an{'s' if x > 1 else ''}")
    with c3:
        n_sim = st.selectbox("Simulations MC",
                             [2000, 5000, 10000], index=1)
    with c4:
        max_w = st.slider("Poids max / actif (%)", 10, 100, 40, step=5) / 100

    run = st.form_submit_button("Lancer l'optimisation ▶", type="primary",
                                use_container_width=True)

if not run:
    st.info("Renseignez vos tickers et paramètres, puis cliquez sur **Lancer l'optimisation**.")
    st.stop()

# ── Data preparation ──────────────────────────────────────────────────────────
tickers = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]
if len(tickers) < 2:
    st.error("Entrez au moins 2 tickers.")
    st.stop()

end_s   = datetime.today().strftime("%Y-%m-%d")
start_s = (datetime.today() - timedelta(days=period_y * 365)).strftime("%Y-%m-%d")

with st.spinner("Téléchargement des données…"):
    prices = _load(tuple(tickers), start_s, end_s)
    rf     = _get_rf()

valid = [t for t in tickers
         if t in prices.columns and prices[t].notna().sum() > 60]
if len(valid) < 2:
    st.error("Données insuffisantes. Vérifiez les tickers.")
    st.stop()

removed = set(tickers) - set(valid)
if removed:
    st.warning(f"Tickers ignorés (données insuffisantes) : {', '.join(removed)}")

prices = prices[valid].dropna()
n      = len(valid)
rets   = prices.pct_change().dropna()
mu     = rets.mean().values
Sigma  = rets.cov().values

st.caption(
    f"Taux sans risque (T-Bill 3M) : **{rf*100:.2f}%**  ·  "
    f"{n} actifs  ·  {len(rets):,} observations journalières "
    f"({rets.index[0].strftime('%d/%m/%Y')} → {rets.index[-1].strftime('%d/%m/%Y')})"
)

# ── Run all optimisations ─────────────────────────────────────────────────────
with st.spinner("Optimisation en cours (MVO · ERC · HRP · BL)…"):
    # MVO
    w_ms   = max_sharpe(mu, Sigma, rf, n, max_weight=max_w)
    w_mv   = min_variance(Sigma, n, max_weight=max_w)
    w_1n   = np.ones(n) / n                           # 1/N benchmark

    # ERC
    w_erc  = erc(Sigma, n)

    # HRP
    w_hrp, linkage, hrp_order = hrp(Sigma, n, returns=rets)

    # Black-Litterman (prior only, no views by default)
    w_mkt  = w_1n.copy()
    BL_mu_ann, BL_Sigma, Pi_ann = black_litterman(
        Sigma, w_mkt, views_mu=[], views_idx=[], rf=rf)
    # Use BL posterior for max-Sharpe in annualised space
    BL_mu_daily = (BL_mu_ann - rf) / 252
    w_bl_ms = max_sharpe(BL_mu_daily + rf / 252, BL_Sigma / 252, rf, n, max_weight=max_w)

    # Monte Carlo & frontier
    mc       = monte_carlo(mu, Sigma, rf, n, n_sim)
    ef_vols, ef_rets = efficient_frontier(mu, Sigma, n, n_pts=60)

    # CML
    r_ms, v_ms, s_ms = port_stats(w_ms, mu, Sigma, rf)
    cml_v = np.linspace(0, mc["vols"].max() * 1.1, 120)
    cml_r = rf + s_ms * cml_v

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_mvo, tab_erc, tab_hrp, tab_bl, tab_cmp = st.tabs([
    "MVO — Markowitz",
    "ERC — Risk Parity",
    "HRP — Lopez de Prado",
    "Black-Litterman",
    "Comparaison",
])

# ── TAB 1 : MVO ───────────────────────────────────────────────────────────────
with tab_mvo:
    st.markdown("## Frontière Efficiente & CML")
    st.caption(
        "La frontière efficiente représente l'ensemble des portefeuilles optimaux "
        "(rendement maximal pour un niveau de risque donné). La CML relie le taux sans "
        "risque au portefeuille tangent (max Sharpe)."
    )

    fig_ef = go.Figure()

    # MC cloud
    fig_ef.add_trace(go.Scatter(
        x=mc["vols"] * 100, y=mc["rets"] * 100,
        mode="markers",
        marker=dict(color=mc["sharpes"], colorscale="Viridis",
                    size=3, opacity=0.5,
                    colorbar=dict(title="Sharpe", thickness=11, len=0.55, x=1.01,
                                  tickfont=dict(size=9))),
        name="Portefeuilles simulés",
        hovertemplate="Vol: %{x:.2f}%<br>Rend: %{y:.2f}%<extra></extra>",
        showlegend=False,
    ))

    # Efficient frontier curve
    if len(ef_vols) > 2:
        fig_ef.add_trace(go.Scatter(
            x=ef_vols * 100, y=ef_rets * 100,
            mode="lines",
            line=dict(color=C["gold"], width=2),
            name="Frontière efficiente",
        ))

    # CML
    fig_ef.add_trace(go.Scatter(
        x=cml_v * 100, y=cml_r * 100,
        mode="lines",
        line=dict(color="rgba(255,255,255,0.35)", width=1.2, dash="dot"),
        name="Capital Market Line",
    ))

    # Special portfolios
    def _mark(w, col, sym, lbl):
        r, v, s = port_stats(w, mu, Sigma, rf)
        fig_ef.add_trace(go.Scatter(
            x=[v * 100], y=[r * 100],
            mode="markers+text",
            marker=dict(color=col, size=14, symbol=sym,
                        line=dict(color="white", width=1)),
            text=[lbl], textposition="top right",
            textfont=dict(color=col, size=10),
            name=lbl,
        ))

    _mark(w_ms,  C["red"],    "star",    f"Max Sharpe ({s_ms:.2f})")
    r_mv, v_mv, _ = port_stats(w_mv, mu, Sigma, rf)
    _mark(w_mv,  C["blue"],   "diamond", "Min Variance")
    _mark(w_1n,  C["muted"],  "circle",  "Equal Weight")

    # RF point
    fig_ef.add_trace(go.Scatter(
        x=[0], y=[rf * 100],
        mode="markers+text",
        marker=dict(color=C["green"], size=8, symbol="x"),
        text=["Rf"], textposition="top right",
        textfont=dict(color=C["green"], size=9),
        name=f"Taux sans risque ({rf*100:.2f}%)",
    ))

    fig_ef.update_layout(
        **PLOTLY,
        title_text="Frontière Efficiente de Markowitz",
        xaxis_title="Volatilité annualisée (%)",
        yaxis_title="Rendement annualisé (%)",
        height=500,
        legend=dict(orientation="h", y=1.04, x=0),
    )
    st.plotly_chart(fig_ef, use_container_width=True)

    # ── Optimal portfolio weights ──────────────────────────────────────────────
    col_ms, col_mv = st.columns(2)

    with col_ms:
        st.markdown("#### Portefeuille Max Sharpe (Tangent)")
        st.dataframe(_weight_df(valid, w_ms), use_container_width=True, hide_index=True)
        r, v, s = port_stats(w_ms, mu, Sigma, rf)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rendement ann.", f"{r*100:.2f}%")
        m2.metric("Volatilité ann.", f"{v*100:.2f}%")
        m3.metric("Sharpe Ratio", f"{s:.3f}")

        fig_w = ch.bar(valid, list(w_ms * 100), color_by_sign=False, height=220)
        fig_w.update_layout(yaxis_title="Poids (%)")
        st.plotly_chart(fig_w, use_container_width=True)

    with col_mv:
        st.markdown("#### Portefeuille Min Variance")
        st.dataframe(_weight_df(valid, w_mv), use_container_width=True, hide_index=True)
        r, v, s = port_stats(w_mv, mu, Sigma, rf)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rendement ann.", f"{r*100:.2f}%")
        m2.metric("Volatilité ann.", f"{v*100:.2f}%")
        m3.metric("Sharpe Ratio", f"{s:.3f}")

        fig_w2 = ch.bar(valid, list(w_mv * 100), color_by_sign=False, height=220)
        fig_w2.update_layout(yaxis_title="Poids (%)")
        st.plotly_chart(fig_w2, use_container_width=True)

    # ── Correlation matrix ─────────────────────────────────────────────────────
    st.markdown("## Matrice de Corrélation")
    fig_corr = ch.heatmap(rets.corr(),
                          title="Corrélations (rendements journaliers)",
                          height=max(320, 40 * n + 60))
    st.plotly_chart(fig_corr, use_container_width=True)

    # ── Individual asset stats ─────────────────────────────────────────────────
    st.markdown("## Statistiques individuelles")
    stats_rows = []
    for i, t in enumerate(valid):
        r_a = float(mu[i]) * 252
        v_a = float(rets[t].std()) * np.sqrt(252)
        sh  = (r_a - rf) / v_a if v_a > 0 else 0
        stats_rows.append({
            "Ticker":         t,
            "Rend. ann. (%)": round(r_a * 100, 2),
            "Vol. ann. (%)":  round(v_a * 100, 2),
            "Sharpe":         round(sh, 3),
            "Skew.":          round(float(rets[t].skew()), 3),
            "Kurtosis":       round(float(rets[t].kurtosis()), 3),
        })
    st.dataframe(pd.DataFrame(stats_rows), use_container_width=True, hide_index=True)


# ── TAB 2 : ERC ───────────────────────────────────────────────────────────────
with tab_erc:
    st.markdown("## Equal Risk Contribution (Risk Parity)")
    st.caption(
        "Chaque actif contribue de manière égale à la volatilité totale du portefeuille. "
        "Contrairement à la MVO, l'ERC ne dépend pas d'estimations des rendements attendus "
        "(plus stables, moins sensibles au bruit)."
    )

    rc_erc = risk_contributions(w_erc, Sigma) * 100
    rc_1n  = risk_contributions(w_1n, Sigma) * 100

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Poids ERC")
        st.dataframe(_weight_df(valid, w_erc), use_container_width=True, hide_index=True)
        r, v, s = port_stats(w_erc, mu, Sigma, rf)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rendement ann.", f"{r*100:.2f}%")
        m2.metric("Volatilité ann.", f"{v*100:.2f}%")
        m3.metric("Sharpe Ratio", f"{s:.3f}")

    with col_b:
        fig_rc = ch.risk_contrib_bar(
            valid, list(rc_1n), list(rc_erc), method="ERC", height=320)
        st.plotly_chart(fig_rc, use_container_width=True)

    # ERC vs EW comparison chart
    st.markdown("#### Décomposition du risque — ERC vs Équipondéré")
    rc_data = pd.DataFrame({
        "Actif":   valid,
        "Équipondéré (%)": list(rc_1n),
        "ERC (%)":         list(rc_erc),
    })
    st.dataframe(rc_data.set_index("Actif"), use_container_width=True)

    fig_p = ch.donut(valid, list(w_erc * 100), title="Allocation ERC", height=360)
    st.plotly_chart(fig_p, use_container_width=True)


# ── TAB 3 : HRP ───────────────────────────────────────────────────────────────
with tab_hrp:
    st.markdown("## Hierarchical Risk Parity (Lopez de Prado, 2016)")
    st.caption(
        "HRP regroupe les actifs par similarité (clustering hiérarchique) puis alloue le "
        "budget de risque récursivement. Robust aux matrices de covariance singulières et "
        "supérieur à la MVO hors-échantillon selon l'étude originale."
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("#### Dendrogramme de clustering")
        fig_dn = go.Figure()
        dn = sch.dendrogram(linkage, labels=[valid[i] for i in range(n)], no_plot=True)
        for xs, ys in zip(dn["icoord"], dn["dcoord"]):
            fig_dn.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines",
                line=dict(color=C["gold"], width=1.2),
                showlegend=False,
            ))
        fig_dn.update_xaxes(
            tickvals=[5 + 10 * i for i in range(len(dn["ivl"]))],
            ticktext=dn["ivl"],
            tickfont=dict(size=10),
        )
        fig_dn.update_yaxes(title_text="Distance")
        fig_dn.update_layout(**PLOTLY, title_text="Clustering hiérarchique (single linkage)",
                             height=320, showlegend=False)
        st.plotly_chart(fig_dn, use_container_width=True)

    with col_b:
        st.markdown("#### Allocation HRP")
        st.dataframe(_weight_df(valid, w_hrp), use_container_width=True, hide_index=True)
        r, v, s = port_stats(w_hrp, mu, Sigma, rf)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rendement ann.", f"{r*100:.2f}%")
        m2.metric("Volatilité ann.", f"{v*100:.2f}%")
        m3.metric("Sharpe Ratio", f"{s:.3f}")

    # Risk contribution
    rc_hrp = risk_contributions(w_hrp, Sigma) * 100
    fig_rc2 = ch.risk_contrib_bar(valid, list(rc_1n), list(rc_hrp), method="HRP", height=300)
    st.plotly_chart(fig_rc2, use_container_width=True)


# ── TAB 4 : BLACK-LITTERMAN ───────────────────────────────────────────────────
with tab_bl:
    st.markdown("## Black-Litterman")
    st.caption(
        "Le modèle BL part des rendements d'équilibre (implicites aux capitalisations de "
        "marché) et les ajuste selon les vues de l'investisseur. Le résultat est un vecteur "
        "de rendements attendus plus stable que les estimations historiques pures."
    )

    # Show prior (equilibrium returns)
    st.markdown("#### Rendements d'équilibre (prior)")
    prior_df = pd.DataFrame({
        "Ticker":           valid,
        "Rendement CAPM implicite (% ann.)": (Pi_ann * 100).round(2),
    })
    st.dataframe(prior_df, use_container_width=True, hide_index=True)
    st.caption(
        "Ces rendements sont implicites : ils correspondent aux rendements qui, dans un "
        "équilibre de marché, résulteraient d'une optimisation MVO sur les poids de référence. "
        "Paramètre de risque δ = 2.5."
    )

    # Views input
    st.markdown("#### Vos vues (optionnel)")
    st.caption(
        "Exprimez vos anticipations de rendement annualisé pour les actifs de votre choix. "
        "La confiance (%) module le poids accordé à chaque vue dans le posterior."
    )

    default_views = pd.DataFrame({
        "Ticker":                   valid[:min(3, n)],
        "Rendement attendu (% ann.)": [0.0] * min(3, n),
        "Confiance (%)":            [50.0] * min(3, n),
        "Activer":                  [False] * min(3, n),
    })
    views_editor = st.data_editor(
        default_views, use_container_width=True, hide_index=True,
        column_config={
            "Ticker": st.column_config.SelectboxColumn(
                "Ticker", options=valid, required=True),
            "Rendement attendu (% ann.)": st.column_config.NumberColumn(
                min_value=-50.0, max_value=100.0, step=0.5),
            "Confiance (%)": st.column_config.NumberColumn(
                min_value=10.0, max_value=100.0, step=5.0),
            "Activer": st.column_config.CheckboxColumn(),
        },
        num_rows="dynamic",
    )

    # Rebuild BL with user views
    active_views = views_editor[views_editor["Activer"] == True]
    views_mu_list  = []
    views_idx_list = []
    view_conf_list = []

    for _, row in active_views.iterrows():
        if row["Ticker"] in valid:
            views_mu_list.append(float(row["Rendement attendu (% ann.)"]) / 100)
            views_idx_list.append(valid.index(row["Ticker"]))
            view_conf_list.append(float(row["Confiance (%)"]) / 100)

    avg_conf = float(np.mean(view_conf_list)) if view_conf_list else 0.5

    BL_mu_u, BL_Sigma_u, Pi_u = black_litterman(
        Sigma, w_mkt, views_mu_list, views_idx_list, rf=rf, view_conf=avg_conf)

    # Optimal weights under BL
    BL_mu_daily_u = (BL_mu_u - rf) / 252
    w_bl_u = max_sharpe(BL_mu_daily_u + rf / 252, BL_Sigma_u / 252, rf, n, max_weight=max_w)

    # Compare prior vs posterior returns
    cmp_df = pd.DataFrame({
        "Ticker":             valid,
        "Prior (% ann.)":     (Pi_ann * 100).round(2),
        "Posterior BL (% ann.)": (BL_mu_u * 100).round(2),
        "Δ":                  ((BL_mu_u - Pi_ann) * 100).round(2),
    })

    def _delta_style(v):
        if pd.isna(v) or v == 0:
            return ""
        return f"color:{C['green']}" if v > 0 else f"color:{C['red']}"

    st.markdown("#### Prior vs Posterior")
    st.dataframe(
        cmp_df.style.applymap(_delta_style, subset=["Δ"])
                    .format({"Δ": lambda v: f"{v:+.2f}%"}),
        use_container_width=True, hide_index=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Poids BL (Max Sharpe posterior)")
        st.dataframe(_weight_df(valid, w_bl_u), use_container_width=True, hide_index=True)
        r, v, s = port_stats(w_bl_u, mu, Sigma, rf)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rendement ann.", f"{r*100:.2f}%")
        m2.metric("Volatilité ann.", f"{v*100:.2f}%")
        m3.metric("Sharpe Ratio", f"{s:.3f}")

    with col_b:
        fig_bl = ch.donut(valid, list(w_bl_u * 100), title="Allocation BL", height=340)
        st.plotly_chart(fig_bl, use_container_width=True)


# ── TAB 5 : COMPARISON ────────────────────────────────────────────────────────
with tab_cmp:
    st.markdown("## Comparaison des 5 méthodes")

    METHODS = [
        ("Max Sharpe (MVO)",  w_ms),
        ("Min Variance",      w_mv),
        ("Equal Weight",      w_1n),
        ("ERC",               w_erc),
        ("HRP",               w_hrp),
        ("Black-Litterman",   w_bl_u),
    ]

    # Summary table
    rows = []
    for lbl, w in METHODS:
        r, v, s = port_stats(w, mu, Sigma, rf)
        rc      = risk_contributions(w, Sigma)
        rows.append({
            "Méthode":             lbl,
            "Rend. ann. (%)":      round(r * 100, 2),
            "Vol. ann. (%)":       round(v * 100, 2),
            "Sharpe":              round(s, 3),
            "Max RC (%)":          round(float(rc.max()) * 100, 1),
            "HHI (concentration)": round(float((w ** 2).sum()), 4),
        })

    df_cmp = pd.DataFrame(rows)
    st.dataframe(df_cmp.set_index("Méthode"), use_container_width=True)
    st.caption(
        "HHI (Herfindahl-Hirschman Index) : proche de 1/N = concentration minimale, "
        "proche de 1 = concentration maximale."
    )

    # Weights comparison bar chart
    st.markdown("#### Poids par méthode")
    fig_cmp = go.Figure()
    for i, (lbl, w) in enumerate(METHODS):
        fig_cmp.add_trace(go.Bar(
            name=lbl, x=valid, y=(w * 100).round(2),
            marker_color=CHART_COLORS[i % len(CHART_COLORS)],
        ))
    fig_cmp.update_layout(**PLOTLY, barmode="group",
                          yaxis_title="Poids (%)",
                          title_text="Comparaison des allocations",
                          height=400,
                          legend=dict(orientation="h", y=1.04))
    st.plotly_chart(fig_cmp, use_container_width=True)

    # Efficient frontier with all methods marked
    st.markdown("#### Positionnement sur la frontière efficiente")
    fig_pos = go.Figure()
    fig_pos.add_trace(go.Scatter(
        x=mc["vols"] * 100, y=mc["rets"] * 100, mode="markers",
        marker=dict(color=mc["sharpes"], colorscale="Viridis", size=2.5,
                    opacity=0.4, showscale=False),
        showlegend=False,
        hovertemplate="Vol: %{x:.2f}%<br>Rend: %{y:.2f}%<extra></extra>",
    ))
    for i, (lbl, w) in enumerate(METHODS):
        r, v, _ = port_stats(w, mu, Sigma, rf)
        fig_pos.add_trace(go.Scatter(
            x=[v * 100], y=[r * 100],
            mode="markers+text",
            marker=dict(color=CHART_COLORS[i], size=13,
                        line=dict(color="white", width=1)),
            text=[lbl], textposition="top right",
            textfont=dict(size=9, color=CHART_COLORS[i]),
            name=lbl,
        ))
    fig_pos.update_layout(
        **PLOTLY,
        title_text="Positionnement espace risque/rendement",
        xaxis_title="Volatilité ann. (%)",
        yaxis_title="Rendement ann. (%)",
        height=480,
        legend=dict(orientation="h", y=1.04),
    )
    st.plotly_chart(fig_pos, use_container_width=True)
