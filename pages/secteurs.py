"""
Page : Cartographie des Secteurs

Pour chaque secteur GICS :
  • ETF sectoriel : performance live + sparkline
  • Description narrative investisseur
  • Drivers thématiques
  • Entreprises leaders visibles
  • Entreprises "backbone" : indispensables mais sous le radar
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.settings import CSS, PLOTLY, C, CHART_COLORS, plotly_layout
from config.sector_data import SECTORS

st.markdown(CSS, unsafe_allow_html=True)


# ─── data loading ────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def load_etf_data(etfs: tuple) -> pd.DataFrame:
    end   = datetime.today()
    start = end - timedelta(days=400)
    raw   = yf.download(list(etfs), start=start, end=end,
                        auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        return raw["Close"].dropna(how="all")
    return raw[["Close"]].copy().rename(columns={"Close": etfs[0]})


@st.cache_data(ttl=1800, show_spinner=False)
def load_company_prices(tickers: tuple) -> dict[str, float | None]:
    """Load latest price + 3M change for a list of tickers."""
    end   = datetime.today()
    start = end - timedelta(days=100)
    try:
        raw = yf.download(list(tickers), start=start, end=end,
                          auto_adjust=True, progress=False)
        if raw.empty:
            return {}
        if isinstance(raw.columns, pd.MultiIndex):
            prices = raw["Close"]
        else:
            prices = raw

        result = {}
        for t in tickers:
            if t in prices.columns:
                s = prices[t].dropna()
                if len(s) >= 2:
                    cur  = float(s.iloc[-1])
                    old  = float(s.iloc[0])
                    chg  = (cur / old - 1) * 100
                    result[t] = {"price": cur, "chg_3m": chg}
        return result
    except Exception:
        return {}


def fmt_pct(v, sign=True):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{'+' if sign and v > 0 else ''}{v:.1f}%"


def perf_color(v):
    if v is None:
        return "#8892A0"
    return "#34D399" if v >= 0 else "#EF4444"


def sparkline(series: pd.Series, color: str) -> go.Figure:
    normed = (series / series.iloc[0] - 1) * 100
    fig = go.Figure(go.Scatter(
        x=series.index, y=normed.values,
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
    ))
    fig.update_layout(**plotly_layout(
        height=100,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=True, ticksuffix="%", tickfont=dict(size=9, color="#4A5568"),
                   gridcolor="#1E2535", zeroline=True, zerolinecolor="#4A5568"),
        showlegend=False,
    ))
    return fig


# ─── load all ETF data ────────────────────────────────────────────────────────

st.markdown("## 🗺️ Cartographie des Secteurs")
st.markdown(
    "<p style='color:#8892A0;margin-top:-8px;'>Panorama sectoriel : performance, thématiques de fond, "
    "entreprises leaders et entreprises <em>backbone</em> — indispensables mais sous le radar.</p>",
    unsafe_allow_html=True,
)

etf_list = tuple(s["etf"] for s in SECTORS.values())

with st.spinner("Chargement des données sectorielles…"):
    etf_prices = load_etf_data(etf_list)

# ── Overview strip ─────────────────────────────────────────────────────────────

st.markdown("### Performance ETF Sectoriels")

overview_cols = st.columns(len(SECTORS))
for i, (key, sec) in enumerate(SECTORS.items()):
    etf  = sec["etf"]
    with overview_cols[i]:
        if not etf_prices.empty and etf in etf_prices.columns:
            s     = etf_prices[etf].dropna()
            ret1m = (float(s.iloc[-1]) / float(s.iloc[-22]) - 1) * 100 if len(s) >= 22 else None
            ret3m = (float(s.iloc[-1]) / float(s.iloc[-63]) - 1) * 100 if len(s) >= 63 else None
            clr   = perf_color(ret1m)
        else:
            ret1m, ret3m, clr = None, None, "#8892A0"

        st.markdown(
            f"<div style='background:rgba(30,37,53,0.7);border-radius:8px;padding:10px 12px;"
            f"text-align:center;border-top:2px solid {clr};'>"
            f"<div style='font-size:0.7rem;color:#8892A0;'>{etf}</div>"
            f"<div style='font-size:0.8rem;color:#E2E8F0;font-weight:600;'>{sec['label'][:14]}</div>"
            f"<div style='font-size:1.1rem;color:{clr};font-weight:700;'>{fmt_pct(ret1m)}</div>"
            f"<div style='font-size:0.68rem;color:#4A5568;'>1M · 3M: {fmt_pct(ret3m)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

# ─── Sector cards ────────────────────────────────────────────────────────────

# Preload all company tickers
all_company_tickers = []
for sec in SECTORS.values():
    for co in sec["leaders"] + sec["backbone"]:
        all_company_tickers.append(co["ticker"])

with st.spinner("Chargement des cours individuels…"):
    co_data = load_company_prices(tuple(all_company_tickers))

# Sector selector
sector_labels  = {k: v["label"] for k, v in SECTORS.items()}
selected_sector = st.selectbox(
    "Afficher un secteur en détail :",
    list(SECTORS.keys()),
    format_func=lambda k: f"{SECTORS[k]['label']} ({SECTORS[k]['etf']})",
)

st.markdown("<br>", unsafe_allow_html=True)

# ── All sectors as expandable cards ──────────────────────────────────────────

for key, sec in SECTORS.items():
    etf = sec["etf"]
    is_selected = (key == selected_sector)

    with st.expander(
        f"{'📌 ' if is_selected else ''}{sec['label']}  —  ETF: {etf}",
        expanded=is_selected,
    ):

        col_desc, col_spark = st.columns([3, 2])

        with col_desc:
            # Description
            st.markdown(
                f"<p style='color:#CBD5E1;font-size:0.9rem;line-height:1.6;'>{sec['description']}</p>",
                unsafe_allow_html=True,
            )

            # Drivers
            st.markdown(
                "<div style='font-size:0.78rem;color:#8892A0;font-weight:600;"
                "letter-spacing:0.06em;margin:12px 0 6px;'>MOTEURS THÉMATIQUES</div>",
                unsafe_allow_html=True,
            )
            drivers_html = "".join(
                f"<span style='background:rgba(201,169,74,0.12);color:{C['gold']};padding:3px 10px;"
                f"border-radius:12px;font-size:0.78rem;margin:0 4px 4px 0;display:inline-block;'>"
                f"◆ {d}</span>"
                for d in sec["drivers"]
            )
            st.markdown(f"<div>{drivers_html}</div>", unsafe_allow_html=True)

        with col_spark:
            if not etf_prices.empty and etf in etf_prices.columns:
                s = etf_prices[etf].dropna()
                # Performance summary
                ret_1m  = (float(s.iloc[-1]) / float(s.iloc[-22])  - 1) * 100 if len(s) >= 22  else None
                ret_3m  = (float(s.iloc[-1]) / float(s.iloc[-63])  - 1) * 100 if len(s) >= 63  else None
                ret_6m  = (float(s.iloc[-1]) / float(s.iloc[-126]) - 1) * 100 if len(s) >= 126 else None
                ret_ytd = None
                try:
                    ytd_start = s[s.index >= f"{datetime.today().year}-01-01"]
                    if len(ytd_start) > 0:
                        ret_ytd = (float(s.iloc[-1]) / float(ytd_start.iloc[0]) - 1) * 100
                except Exception:
                    pass

                # Mini metrics
                m1, m2, m3, m4 = st.columns(4)
                for mc, label, val in [(m1,"1M",ret_1m),(m2,"3M",ret_3m),(m3,"6M",ret_6m),(m4,"YTD",ret_ytd)]:
                    with mc:
                        clr = perf_color(val)
                        st.markdown(
                            f"<div style='text-align:center;'>"
                            f"<div style='color:#4A5568;font-size:0.68rem;'>{label}</div>"
                            f"<div style='color:{clr};font-size:0.92rem;font-weight:700;'>{fmt_pct(val)}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                # Sparkline
                clr_line = perf_color(ret_3m)
                st.plotly_chart(
                    sparkline(s.tail(180), clr_line),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

        # ── Companies ─────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        col_leaders, col_backbone = st.columns(2)

        def company_card(co: dict, category_color: str):
            t     = co["ticker"]
            d     = co_data.get(t, {})
            price = d.get("price")
            chg   = d.get("chg_3m")
            c     = perf_color(chg)

            price_str = f"${price:.2f}" if price else "—"
            chg_str   = fmt_pct(chg) if chg is not None else "—"

            return (
                f"<div style='background:rgba(20,25,40,0.7);border-left:3px solid {category_color};"
                f"border-radius:6px;padding:12px 14px;margin-bottom:10px;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:baseline;'>"
                f"<span style='font-size:0.88rem;font-weight:700;color:#E2E8F0;'>{t}</span>"
                f"<div style='text-align:right;'>"
                f"<span style='color:#8892A0;font-size:0.78rem;'>{price_str}</span>"
                f"<span style='color:{c};font-size:0.78rem;margin-left:8px;'>{chg_str} 3M</span>"
                f"</div></div>"
                f"<div style='color:#CBD5E1;font-size:0.82rem;margin:4px 0 2px;font-weight:500;'>"
                f"{co['name']}</div>"
                f"<div style='color:#8892A0;font-size:0.75rem;margin-bottom:4px;'>{co['role']}</div>"
                f"<div style='color:#64748B;font-size:0.73rem;line-height:1.4;'>{co['why']}</div>"
                f"</div>"
            )

        with col_leaders:
            st.markdown(
                f"<div style='font-size:0.8rem;color:{C['gold']};font-weight:700;"
                f"letter-spacing:0.06em;margin-bottom:10px;'>◈ LEADERS VISIBLES</div>",
                unsafe_allow_html=True,
            )
            for co in sec["leaders"]:
                st.markdown(company_card(co, C["gold"]), unsafe_allow_html=True)

        with col_backbone:
            st.markdown(
                "<div style='font-size:0.8rem;color:#38BDF8;font-weight:700;"
                "letter-spacing:0.06em;margin-bottom:10px;'>◇ ENTREPRISES BACKBONE</div>",
                unsafe_allow_html=True,
            )
            backbone_intro = (
                "<div style='background:rgba(56,189,248,0.06);border:1px solid rgba(56,189,248,0.2);"
                "border-radius:6px;padding:8px 12px;margin-bottom:10px;color:#7DD3FC;font-size:0.78rem;'>"
                "Ces entreprises sont indispensables au fonctionnement du secteur mais restent "
                "souvent sous le radar des investisseurs particuliers.</div>"
            )
            st.markdown(backbone_intro, unsafe_allow_html=True)
            for co in sec["backbone"]:
                st.markdown(company_card(co, "#38BDF8"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Comparaison relative des ETF (chart)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Performance Relative des ETF Sectoriels (3 derniers mois)")

if not etf_prices.empty:
    try:
        perf_data = etf_prices.tail(63).copy()
        norm      = perf_data / perf_data.iloc[0] * 100 - 100

        fig = go.Figure()
        colors_cycle = CHART_COLORS * 3
        for i, (key, sec) in enumerate(SECTORS.items()):
            etf = sec["etf"]
            if etf in norm.columns:
                fig.add_trace(go.Scatter(
                    x=norm.index,
                    y=norm[etf].values,
                    name=f"{etf} ({sec['label'][:12]})",
                    line=dict(color=colors_cycle[i], width=2),
                    hovertemplate=f"<b>{etf}</b><br>%{{x|%d %b}}<br>%{{y:+.2f}}%<extra></extra>",
                ))

        fig.update_layout(**plotly_layout(
            height=400,
            title=dict(text="Performance normalisée vs il y a 3 mois (base 0%)", font=dict(size=13)),
            yaxis=dict(ticksuffix="%"),
            legend=dict(orientation="v", x=1.01, y=1, font=dict(size=10)),
            margin=dict(l=0, r=150, t=40, b=0),
        ))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except Exception as e:
        st.warning(f"Graphique de performance indisponible : {e}")
