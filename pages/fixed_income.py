"""
Analyse Obligataire & Taux d'Intérêt

Sections :
  1. Courbe des taux US (spot + forward implicites + 3 snapshots)
  2. Calculateur de sensibilité obligataire (Duration, Convexité, DV01, BPV)
  3. Scénarios de taux (parallel shift, steepening, flattening, butterfly)
  4. Marchés obligataires — comparaison d'ETF (AGG, TLT, HYG, LQD, EMB, TIPS)
"""

import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.settings import CSS, C, CHART_COLORS, PLOTLY
import utils.charts as ch

st.markdown(CSS, unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TREASURIES = {
    "3M": "^IRX", "1Y": None,          # 1Y not available on Yahoo
    "2Y": None,   "5Y": "^FVX",
    "10Y": "^TNX", "30Y": "^TYX",
}
# Only tickers that exist on Yahoo Finance
YF_TREASURIES = {"3M": "^IRX", "5Y": "^FVX", "10Y": "^TNX", "30Y": "^TYX"}
MAT_VALS      = {"3M": 0.25, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0}

BOND_ETFS = {
    "AGG":  "US Agg Bond (IG)",
    "TLT":  "US 20Y+ Treasuries",
    "IEF":  "US 7-10Y Treasuries",
    "SHY":  "US 1-3Y Treasuries",
    "HYG":  "US High Yield",
    "LQD":  "US Investment Grade Corp.",
    "EMB":  "EM Bonds (USD)",
    "TIP":  "US TIPS (Inflation-linked)",
    "VCLT": "US Long-Term Corp.",
}

# Approximate durations and yields for bond ETFs (updated manually)
ETF_META = {
    "AGG":  {"Duration": 6.3,  "YTM (%)": 5.2, "Qualité": "AA"},
    "TLT":  {"Duration": 17.2, "YTM (%)": 4.7, "Qualité": "AAA"},
    "IEF":  {"Duration": 7.5,  "YTM (%)": 4.5, "Qualité": "AAA"},
    "SHY":  {"Duration": 1.9,  "YTM (%)": 4.8, "Qualité": "AAA"},
    "HYG":  {"Duration": 3.6,  "YTM (%)": 7.4, "Qualité": "B+"},
    "LQD":  {"Duration": 8.9,  "YTM (%)": 5.5, "Qualité": "A"},
    "EMB":  {"Duration": 7.1,  "YTM (%)": 6.8, "Qualité": "BBB"},
    "TIP":  {"Duration": 7.1,  "YTM (%)": 2.2, "Qualité": "AAA"},
    "VCLT": {"Duration": 14.4, "YTM (%)": 6.0, "Qualité": "A-"},
}


# ── Loaders ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def _load_yields(start: str, end: str) -> pd.DataFrame:
    tickers = list(YF_TREASURIES.values())
    raw = yf.download(tickers, start=start, end=end, auto_adjust=False, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        df = raw["Close"].copy()
    else:
        df = raw.copy()
    df = df.rename(columns={v: k for k, v in YF_TREASURIES.items()})
    return df[[c for c in YF_TREASURIES if c in df.columns]].dropna(how="all")


@st.cache_data(ttl=3600, show_spinner=False)
def _load_etfs(start: str, end: str) -> pd.DataFrame:
    tickers = list(BOND_ETFS.keys())
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw
    return prices[[t for t in tickers if t in prices.columns]].dropna(how="all")


# ── Bond math ─────────────────────────────────────────────────────────────────
def bond_price(ytm: float, coupon: float, face: float,
               maturity: float, freq: int = 2) -> float:
    """Clean price of a fixed-rate bond."""
    n    = int(maturity * freq)
    c    = coupon / freq * face
    r    = ytm / freq
    if r < 1e-10:
        return face + c * n
    t    = np.arange(1, n + 1)
    pv   = c / (1 + r) ** t
    pv[-1] += face / (1 + r) ** n
    return float(pv.sum())


def macaulay_duration(ytm: float, coupon: float, face: float,
                      maturity: float, freq: int = 2) -> float:
    """Macaulay Duration (in years)."""
    n   = int(maturity * freq)
    c   = coupon / freq * face
    r   = ytm / freq
    if r < 1e-10:
        t = np.arange(1, n + 1) / freq
        w = np.ones(n) * c
        w[-1] += face
        return float(np.sum(t * w) / np.sum(w))
    t   = np.arange(1, n + 1)
    cf  = np.full(n, c)
    cf[-1] += face
    pv  = cf / (1 + r) ** t
    mac = float(np.sum(t / freq * pv) / pv.sum())
    return mac


def modified_duration(ytm: float, coupon: float, face: float,
                      maturity: float, freq: int = 2) -> float:
    mac = macaulay_duration(ytm, coupon, face, maturity, freq)
    return mac / (1 + ytm / freq)


def convexity(ytm: float, coupon: float, face: float,
              maturity: float, freq: int = 2) -> float:
    """Convexity (in years²)."""
    n  = int(maturity * freq)
    c  = coupon / freq * face
    r  = ytm / freq
    if r < 1e-10:
        return 0.0
    t  = np.arange(1, n + 1)
    cf = np.full(n, c, dtype=float)
    cf[-1] += face
    pv = cf / (1 + r) ** t
    P  = pv.sum()
    cx = float(np.sum(pv * t * (t + 1)) / (P * (1 + r) ** 2 * freq ** 2))
    return cx


def price_change(md: float, cx: float, P: float, dy: float) -> float:
    """ΔP ≈ -MD·P·Δy + ½·Cx·P·(Δy)²"""
    return -md * P * dy + 0.5 * cx * P * dy ** 2


def implied_forward(r_short: float, t_short: float,
                    r_long: float,  t_long: float) -> float:
    """
    Implied forward rate between t_short and t_long
    using continuous compounding approximation.
    f(t1, t2) = (r_long * t_long - r_short * t_short) / (t_long - t_short)
    """
    if t_long <= t_short:
        return np.nan
    return (r_long * t_long - r_short * t_short) / (t_long - t_short)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════════════════════════════════
st.title("Analyse Obligataire & Taux d'Intérêt")
st.caption(
    "Courbe des taux · Taux forward implicites · "
    "Duration / Convexité / DV01 · Scénarios de taux · ETF obligataires"
)

today = datetime.today()
end_s = today.strftime("%Y-%m-%d")
s_5y  = (today - timedelta(days=5 * 365)).strftime("%Y-%m-%d")
s_1y  = (today - timedelta(days=365)).strftime("%Y-%m-%d")

with st.spinner("Chargement des données obligataires…"):
    yields_df = _load_yields(s_5y, end_s)
    etf_prices = _load_etfs(s_1y, end_s)

avail_m = [m for m in YF_TREASURIES if m in yields_df.columns]

# ═══════════════════════════════════════════════════════════════════════════════
# 1. YIELD CURVE
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Courbe des Taux US — Treasuries")

if avail_m and not yields_df.empty:
    clean = yields_df[avail_m].dropna()
    latest = clean.iloc[-1]
    date_l = clean.index[-1]

    def _snap(days):
        target = date_l - timedelta(days=days)
        idx    = clean.index.searchsorted(target)
        return clean.iloc[min(idx, len(clean) - 1)]

    snap_6m  = _snap(180)
    snap_1y  = _snap(365)
    snap_2y  = _snap(730)

    mat_vals  = [MAT_VALS[m] for m in avail_m]
    mats_cont = np.linspace(0.25, 30, 200)     # for interpolation

    # Linear interpolation for display
    from numpy import interp

    def _interp(snap):
        return interp(mats_cont, mat_vals, snap[avail_m].values)

    snapshots_display = {
        f"Actuel ({date_l.strftime('%d/%m/%Y')})": latest[avail_m].values,
        f"6 mois":                                  snap_6m[avail_m].values,
        f"1 an":                                    snap_1y[avail_m].values,
        f"2 ans":                                   snap_2y[avail_m].values,
    }

    fig_yc = ch.yield_curve(snapshots_display, mat_vals, avail_m,
                            title="Courbe des Taux US (Treasuries)",
                            height=420)
    st.plotly_chart(fig_yc, use_container_width=True)

    # Rate display
    rate_cols = st.columns(len(avail_m))
    for i, m in enumerate(avail_m):
        delta_1y = float(latest[m]) - float(snap_1y[m])
        rate_cols[i].metric(
            f"T-{m}",
            f"{float(latest[m]):.2f}%",
            delta=f"{delta_1y:+.2f}% (1A)",
            delta_color="inverse",
        )

    # Slope & inversion
    if "10Y" in avail_m and "3M" in avail_m:
        slope = float(latest["10Y"]) - float(latest["3M"])
        if slope < 0:
            st.error(
                f"Pente 10Y – 3M : **{slope:.2f}%** — "
                "Courbe inversée. Historiquement précurseur de récession (délai ~12-18 mois)."
            )
        elif slope < 0.5:
            st.warning(f"Pente 10Y – 3M : **{slope:.2f}%** — Courbe plate (régime de ralentissement).")
        else:
            st.success(f"Pente 10Y – 3M : **{slope:.2f}%** — Courbe normale (régime de croissance).")

    # Historical yield evolution
    st.markdown("#### Évolution historique des taux (5 ans)")
    colors_yc = [C["gold"], C["blue"], C["green"], C["red"]]
    fig_hist_y = go.Figure()
    for i, m in enumerate(avail_m):
        s = yields_df[m].dropna()
        fig_hist_y.add_trace(go.Scatter(
            x=s.index, y=s.values, name=f"T-{m}",
            line=dict(color=colors_yc[i % 4], width=1.5),
        ))
    fig_hist_y.update_layout(
        **PLOTLY,
        yaxis_title="Taux (%)",
        title_text="Évolution des taux de référence (5 ans)",
        height=320,
        legend=dict(orientation="h", y=1.04),
    )
    st.plotly_chart(fig_hist_y, use_container_width=True)

    # ── Implied forward rates ──────────────────────────────────────────────────
    st.markdown("#### Taux Forward Implicites")
    st.caption(
        "Les taux forward sont les taux implicites dans la structure actuelle de la courbe. "
        "f(t₁,t₂) = (r(t₂)·t₂ − r(t₁)·t₁) / (t₂−t₁).  "
        "Un forward élevé anticipe une hausse des taux futurs."
    )

    fwd_rows = []
    pairs = [(avail_m[i], avail_m[i+1]) for i in range(len(avail_m) - 1)]
    for m1, m2 in pairs:
        t1, t2 = MAT_VALS[m1], MAT_VALS[m2]
        r1, r2 = float(latest[m1]) / 100, float(latest[m2]) / 100
        fwd = implied_forward(r1, t1, r2, t2) * 100
        fwd_rows.append({
            "Contrat forward":    f"f({m1},{m2})",
            "Départ":             m1,
            "Maturité":           m2,
            "Taux forward (%)":   round(fwd, 3),
            "Taux spot {m2} (%)": round(float(latest[m2]), 3),
            "Spread fwd-spot (bp)": round((fwd - float(latest[m2])) * 100, 1),
        })

    if fwd_rows:
        st.dataframe(pd.DataFrame(fwd_rows), use_container_width=True, hide_index=True)

else:
    st.warning("Données de taux indisponibles.")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. BOND SENSITIVITY CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Calculateur de Sensibilité Obligataire")
st.caption(
    "Calcul exact de la Duration de Macaulay, Duration Modifiée, Convexité, "
    "DV01 (Dollar Value of 1 bp) et impact de scénarios de taux."
)

with st.form("bond_form"):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        face    = st.number_input("Nominal (€)", value=1000.0, min_value=1.0, step=100.0)
    with c2:
        coupon  = st.number_input("Coupon annuel (%)", value=3.0,  min_value=0.0,
                                  max_value=30.0, step=0.25) / 100
    with c3:
        ytm     = st.number_input("YTM actuel (%)",    value=4.5,  min_value=0.01,
                                  max_value=30.0, step=0.1) / 100
    with c4:
        mat     = st.number_input("Maturité (années)", value=10.0, min_value=0.5,
                                  max_value=50.0, step=0.5)
    with c5:
        freq    = st.selectbox("Fréquence coupons", [1, 2, 4], index=1,
                               format_func=lambda x: {1:"Annuelle", 2:"Semestrielle",
                                                       4:"Trimestrielle"}[x])
    calc = st.form_submit_button("Calculer ▶", type="primary", use_container_width=True)

if calc:
    P    = bond_price(ytm, coupon, face, mat, freq)
    mac  = macaulay_duration(ytm, coupon, face, mat, freq)
    md   = modified_duration(ytm, coupon, face, mat, freq)
    cx   = convexity(ytm, coupon, face, mat, freq)
    dv01 = abs(price_change(md, cx, P, 0.0001))   # 1 bp move
    bpv  = dv01                                    # BPV = DV01 per unit

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Prix (€)",         f"{P:,.2f}")
    c2.metric("Cours (% nominal)", f"{P/face*100:.2f}%")
    c3.metric("Duration Macaulay", f"{mac:.3f} ans")
    c4.metric("Duration Modifiée", f"{md:.3f}")
    c5.metric("Convexité",         f"{cx:.3f}")
    c6.metric("DV01 (€ / bp)",     f"{dv01:.4f}")

    st.caption(
        f"**Duration Modifiée {md:.3f}** : une hausse de taux de +1% entraîne une perte "
        f"approximative de **{md*100:.1f}%** sur le prix.  "
        f"**DV01 {dv01:.4f}€** : variation du prix pour 1 point de base (0,01%)."
    )

    # Price / Yield relationship
    ytm_range = np.linspace(max(0.001, ytm - 0.05), ytm + 0.05, 200)
    prices    = [bond_price(y, coupon, face, mat, freq) for y in ytm_range]
    prices_md = [P + price_change(md, 0, P, y - ytm) for y in ytm_range]   # linear approx
    prices_cx = [P + price_change(md, cx, P, y - ytm) for y in ytm_range]  # w/ convexity

    fig_py = go.Figure()
    fig_py.add_trace(go.Scatter(
        x=ytm_range * 100, y=prices,
        name="Prix exact", line=dict(color=C["gold"], width=2),
    ))
    fig_py.add_trace(go.Scatter(
        x=ytm_range * 100, y=prices_md,
        name="Approx. linéaire (MD)", line=dict(color=C["blue"], width=1.2, dash="dash"),
    ))
    fig_py.add_trace(go.Scatter(
        x=ytm_range * 100, y=prices_cx,
        name="Approx. + Convexité", line=dict(color=C["green"], width=1.2, dash="dot"),
    ))
    fig_py.add_vline(x=ytm * 100, line_dash="dash", line_color=C["muted"],
                     annotation_text=f"YTM actuel {ytm*100:.2f}%")
    fig_py.update_layout(
        **PLOTLY,
        title_text="Relation Prix / Rendement",
        xaxis_title="YTM (%)",
        yaxis_title="Prix (€)",
        height=360,
        legend=dict(orientation="h", y=1.04),
    )
    st.plotly_chart(fig_py, use_container_width=True)

    # Rate scenarios
    st.markdown("#### Scénarios de variation de taux")
    scenarios = [-200, -150, -100, -75, -50, -25, +25, +50, +75, +100, +150, +200]
    scen_rows = []
    for bps in scenarios:
        dy      = bps / 10_000
        new_ytm = max(0.0001, ytm + dy)
        new_P   = bond_price(new_ytm, coupon, face, mat, freq)
        dp      = new_P - P
        dp_pct  = dp / P * 100
        dp_md   = price_change(md, 0,  P, dy)
        dp_cx   = price_change(md, cx, P, dy)
        scen_rows.append({
            "Δ Taux (bp)":       bps,
            "Nouveau YTM (%)":   round(new_ytm * 100, 3),
            "Prix (€)":          round(new_P, 4),
            "ΔPrix (€)":         round(dp, 4),
            "ΔPrix (%)":         round(dp_pct, 3),
            "Approx. MD (€)":    round(dp_md, 4),
            "Approx. MD+CX (€)": round(dp_cx, 4),
            "Erreur CX (€)":     round(dp - dp_cx, 5),
        })

    scen_df = pd.DataFrame(scen_rows)

    def _scen_style(v):
        if isinstance(v, float) and not pd.isna(v):
            if v > 0:
                return f"color:{C['green']};font-weight:600"
            elif v < 0:
                return f"color:{C['red']};font-weight:600"
        return ""

    st.dataframe(
        scen_df.style.applymap(_scen_style, subset=["ΔPrix (€)", "ΔPrix (%)"]),
        use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. YIELD CURVE SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Scénarios de Déformation de la Courbe")
st.caption(
    "Impact de déformations types de la courbe des taux sur un portefeuille obligataire."
)

if avail_m and not yields_df.empty:
    st.markdown("#### Choisissez un scénario de déformation")
    scen_type = st.radio(
        "",
        ["Déplacement parallèle (+/- bp)",
         "Pentification (long terme monte, court terme stable)",
         "Aplatissement (court terme monte, long terme stable)",
         "Butterfly (ventre monte, extrémités stables)"],
        horizontal=True,
        label_visibility="collapsed",
    )

    col_sc, col_bp = st.columns([2, 1])
    with col_bp:
        shock_bp = st.slider("Choc (bp)", -300, 300, 100, step=25)

    shock = shock_bp / 10_000

    # Build shocked curve
    if scen_type.startswith("Déplacement"):
        shocks = {m: shock for m in avail_m}
    elif scen_type.startswith("Pentification"):
        shocks = {
            "3M": 0, "5Y": shock * 0.3, "10Y": shock * 0.7, "30Y": shock
        }
    elif scen_type.startswith("Aplatissement"):
        shocks = {
            "3M": shock, "5Y": shock * 0.7, "10Y": shock * 0.3, "30Y": 0
        }
    else:  # Butterfly
        shocks = {
            "3M": 0, "5Y": shock, "10Y": shock, "30Y": 0
        }

    latest_base    = {m: float(latest[m]) / 100 for m in avail_m}
    latest_shocked = {m: max(0.0001, latest_base[m] + shocks.get(m, 0)) for m in avail_m}

    with col_sc:
        fig_scen = go.Figure()
        fig_scen.add_trace(go.Scatter(
            x=mat_vals,
            y=[latest_base[m] * 100 for m in avail_m],
            mode="lines+markers",
            name="Courbe actuelle",
            line=dict(color=C["gold"], width=2),
            marker=dict(size=8),
        ))
        fig_scen.add_trace(go.Scatter(
            x=mat_vals,
            y=[latest_shocked[m] * 100 for m in avail_m],
            mode="lines+markers",
            name=f"Après choc ({shock_bp:+d} bp)",
            line=dict(color=C["red"] if shock > 0 else C["green"], width=2, dash="dash"),
            marker=dict(size=8),
        ))
        fig_scen.update_layout(
            **PLOTLY,
            xaxis=dict(title="Maturité", tickvals=mat_vals, ticktext=avail_m),
            yaxis_title="Taux (%)",
            title_text=f"Courbe choquée — {scen_type.split('(')[0].strip()}",
            height=360,
            legend=dict(orientation="h", y=1.04),
        )
        st.plotly_chart(fig_scen, use_container_width=True)

    # Impact on bond ETFs (using metadata)
    st.markdown("#### Impact estimé sur les ETF obligataires")
    impact_rows = []
    for etf, label in BOND_ETFS.items():
        if etf not in ETF_META:
            continue
        meta   = ETF_META[etf]
        dur    = meta["Duration"]
        # Use 10Y shock as representative for most fixed income
        rep_shock = shocks.get("10Y", shock)
        price_impact = -dur * rep_shock * 100   # % impact = -MD * Δy * 100
        impact_rows.append({
            "ETF":                etf,
            "Description":        label,
            "Duration (ans)":     dur,
            "YTM estimé (%)":     meta["YTM (%)"],
            "Qualité":            meta["Qualité"],
            f"Impact prix ({shock_bp:+d}bp, %)": round(price_impact, 2),
        })

    impact_df = pd.DataFrame(impact_rows)

    def _impact_style(v):
        if isinstance(v, float):
            return f"color:{C['green']};font-weight:600" if v >= 0 else f"color:{C['red']};font-weight:600"
        return ""

    last_col = impact_df.columns[-1]
    st.dataframe(
        impact_df.style.applymap(_impact_style, subset=[last_col]),
        use_container_width=True, hide_index=True)
    st.caption(
        "Impact estimé via l'approximation : ΔP ≈ −Duration × Δy. "
        "La convexité améliore la précision pour les grands chocs. "
        "Les YTM et durations sont indicatifs (source : metadata ETF approximatifs)."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# 4. BOND ETF COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## Marchés Obligataires — Comparaison d'ETF")

if not etf_prices.empty:
    avail_etf = [t for t in BOND_ETFS if t in etf_prices.columns]

    # Performance table
    perf_rows = []
    for etf in avail_etf:
        s = etf_prices[etf].dropna()
        if len(s) < 5:
            continue
        rets = s.pct_change().dropna()

        def _ret(days):
            if len(s) < 2:
                return np.nan
            return float(s.iloc[-1] / s.iloc[max(-days-1, -len(s))] - 1)

        ann_ret = rets.mean() * 252
        ann_vol = rets.std() * np.sqrt(252)
        sharpe  = (ann_ret - 0.04) / ann_vol if ann_vol > 0 else 0

        meta = ETF_META.get(etf, {})
        perf_rows.append({
            "ETF":              etf,
            "Description":      BOND_ETFS[etf],
            "Duration (ans)":   meta.get("Duration", "—"),
            "YTM est. (%)":     meta.get("YTM (%)", "—"),
            "Qualité":          meta.get("Qualité", "—"),
            "1M (%)":           round(_ret(21) * 100, 2),
            "3M (%)":           round(_ret(63) * 100, 2),
            "6M (%)":           round(_ret(126)* 100, 2),
            "1A (%)":           round(_ret(252)* 100, 2),
            "Vol. ann. (%)":    round(ann_vol * 100, 2),
            "Sharpe":           round(sharpe, 3),
        })

    df_etf = pd.DataFrame(perf_rows)
    pct_cols = ["1M (%)", "3M (%)", "6M (%)", "1A (%)"]

    def _etf_style(v):
        if isinstance(v, float) and not pd.isna(v):
            bg  = "rgba(34,197,94,0.10)" if v >= 0 else "rgba(239,68,68,0.10)"
            col = C["green"] if v >= 0 else C["red"]
            return f"background-color:{bg};color:{col};font-weight:600"
        return ""

    st.dataframe(
        df_etf.style
              .applymap(_etf_style, subset=pct_cols)
              .format({c: lambda v: f"{v:+.2f}%" if isinstance(v, float) and not pd.isna(v) else str(v)
                       for c in pct_cols}),
        use_container_width=True, hide_index=True, height=360)

    # Normalised performance chart
    st.markdown("#### Performance normalisée (base 100, 1 an)")
    norm = etf_prices[avail_etf] / etf_prices[avail_etf].iloc[0] * 100
    series_etf = {etf: norm[etf].dropna() for etf in avail_etf}
    fig_etf = ch.line(series_etf, title="ETF Obligataires — Performance normalisée",
                      y_label="Indice", height=380)
    st.plotly_chart(fig_etf, use_container_width=True)

    # Spread analysis: HYG vs AGG total return spread
    if "HYG" in avail_etf and "AGG" in avail_etf:
        st.markdown("#### Spread HY vs Investment Grade (proxy de risque crédit)")
        rets_hy  = etf_prices["HYG"].pct_change().dropna()
        rets_agg = etf_prices["AGG"].pct_change().dropna()
        spread   = (rets_hy - rets_agg).rolling(21).mean() * 252 * 100
        spread   = spread.dropna()

        fig_sp = ch.area(spread,
                         title="Spread de rendement HYG – AGG (21j glissant, ann.)",
                         y_label="%",
                         color=C["purple"],
                         fill_color="rgba(139,92,246,0.12)",
                         height=260)
        st.plotly_chart(fig_sp, use_container_width=True)
        st.caption(
            "Un spread positif indique que le High Yield surperforme le marché obligataire "
            "IG : signe d'appétit pour le risque. Un spread négatif reflète un flight-to-quality."
        )

else:
    st.warning("Données ETF obligataires indisponibles.")
