"""
Page : Analyse d'Actions — verdicts intelligents par titre.

Pour chaque ticker saisi :
  • Données de marché (prix, 52W, MA50/200, RSI)
  • Fondamentaux (P/E, P/B, marges, dette)
  • Verdict composite coloré avec signaux explicites
  • Tableau comparatif multi-titres + radar chart
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

from config.settings import CSS, PLOTLY, C, plotly_layout
from config.ticker_meta import TICKER_META
from core.indicators import (
    compute_rsi,
    interpret_rsi,
    ma_signal,
    position_52w,
    interpret_pe,
    interpret_pb,
    interpret_margins,
    interpret_debt,
    stock_verdict,
)

st.markdown(CSS, unsafe_allow_html=True)

# ─── helpers ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def load_stock(ticker: str) -> dict:
    """Download price history + fundamentals for one ticker."""
    end   = datetime.today()
    start = end - timedelta(days=400)

    hist = yf.download(ticker, start=start, end=end,
                       auto_adjust=True, progress=False)
    if hist.empty:
        return {}

    # flatten MultiIndex if needed
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    close = hist["Close"].dropna()
    if len(close) < 30:
        return {}

    # Technicals
    rsi_val  = compute_rsi(close)
    ma50     = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else np.nan
    ma200    = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else np.nan
    price    = float(close.iloc[-1])
    low_52w  = float(close.tail(252).min())
    high_52w = float(close.tail(252).max())

    mom_3m  = float((close.iloc[-1] / close.iloc[-63] - 1) * 100) if len(close) >= 63 else np.nan
    mom_6m  = float((close.iloc[-1] / close.iloc[-126] - 1) * 100) if len(close) >= 126 else np.nan
    mom_1y  = float((close.iloc[-1] / close.iloc[-252] - 1) * 100) if len(close) >= 252 else np.nan

    # Fundamentals via yfinance .info
    static = TICKER_META.get(ticker.upper(), {})
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}

    pe       = info.get("trailingPE")       or info.get("forwardPE")
    pb       = info.get("priceToBook")
    gross_m  = info.get("grossMargins")
    oper_m   = info.get("operatingMargins")
    debt_eq  = info.get("debtToEquity")
    roe      = info.get("returnOnEquity")
    sector   = info.get("sector") or static.get("sector") or "Unknown"
    name     = info.get("longName") or info.get("shortName") or static.get("name") or ticker
    currency = info.get("currency") or "USD"
    mktcap   = info.get("marketCap")

    # Convert margins from 0-1 to percentage if needed
    if gross_m is not None and gross_m <= 1:
        gross_m = gross_m * 100
    if oper_m is not None and oper_m <= 1:
        oper_m = oper_m * 100
    if roe is not None and roe <= 1:
        roe = roe * 100

    return {
        "ticker":   ticker.upper(),
        "name":     name,
        "sector":   sector,
        "currency": currency,
        "mktcap":   mktcap,
        "price":    price,
        "low_52w":  low_52w,
        "high_52w": high_52w,
        "ma50":     ma50,
        "ma200":    ma200,
        "rsi":      rsi_val,
        "mom_3m":   mom_3m,
        "mom_6m":   mom_6m,
        "mom_1y":   mom_1y,
        "pe":       pe,
        "pb":       pb,
        "gross_m":  gross_m,
        "oper_m":   oper_m,
        "debt_eq":  debt_eq,
        "roe":      roe,
        "close":    close,
    }


def fmt_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:+.1f}%"


def fmt_val(v, decimals=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:.{decimals}f}"


def fmt_mktcap(v):
    if not v:
        return "—"
    if v >= 1e12:
        return f"${v/1e12:.1f}T"
    if v >= 1e9:
        return f"${v/1e9:.1f}Md"
    return f"${v/1e6:.0f}M"


# ─── Gauge RSI ───────────────────────────────────────────────────────────────

def rsi_gauge(rsi_val: float, ticker: str) -> go.Figure:
    interp = interpret_rsi(rsi_val)
    fig = go.Figure(go.Indicator(
        mode   = "gauge+number",
        value  = rsi_val,
        title  = {"text": f"RSI(14) — {ticker}", "font": {"color": "#E2E8F0", "size": 14}},
        number = {"font": {"color": interp["color"], "size": 28}},
        gauge  = {
            "axis": {"range": [0, 100], "tickcolor": "#4A5568",
                     "tickvals": [0, 20, 30, 50, 70, 80, 100],
                     "ticktext": ["0", "20", "Survente", "50", "Surchauffe", "80", "100"],
                     "tickfont": {"color": "#8892A0", "size": 9}},
            "bar":  {"color": interp["color"], "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 20],   "color": "#1A3A4A"},
                {"range": [20, 30],  "color": "#1A4A3A"},
                {"range": [30, 50],  "color": "#1E2535"},
                {"range": [50, 70],  "color": "#1E2535"},
                {"range": [70, 80],  "color": "#4A3A1A"},
                {"range": [80, 100], "color": "#4A1A1A"},
            ],
            "threshold": {
                "line": {"color": interp["color"], "width": 3},
                "thickness": 0.75,
                "value": rsi_val,
            },
        },
    ))
    fig.update_layout(**plotly_layout(
        height=220,
        margin=dict(l=20, r=20, t=40, b=0),
    ))
    return fig


# ─── Price chart with MAs ─────────────────────────────────────────────────

def price_chart(data: dict) -> go.Figure:
    close = data["close"]
    dates = close.index

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=close.values,
        name="Prix",
        line=dict(color=C["gold"], width=2),
        fill="tozeroy",
        fillcolor="rgba(201,169,74,0.05)",
    ))

    if not np.isnan(data["ma50"]):
        ma50s = close.rolling(50).mean()
        fig.add_trace(go.Scatter(
            x=dates, y=ma50s.values,
            name="MA50",
            line=dict(color="#38BDF8", width=1.5, dash="dot"),
        ))

    if not np.isnan(data["ma200"]):
        ma200s = close.rolling(200).mean()
        fig.add_trace(go.Scatter(
            x=dates, y=ma200s.values,
            name="MA200",
            line=dict(color="#F472B6", width=1.5, dash="dash"),
        ))

    # 52W range band
    fig.add_hrect(
        y0=data["low_52w"], y1=data["high_52w"],
        fillcolor="rgba(100,100,100,0.05)",
        line_width=0,
        annotation_text="Range 52S",
        annotation_position="top left",
        annotation_font_color="#4A5568",
    )

    fig.update_layout(**plotly_layout(
        height=280,
        margin=dict(l=0, r=0, t=30, b=0),
        title=dict(text=f"{data['ticker']} — 13 derniers mois", font=dict(size=13)),
        showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis=dict(tickprefix=data["currency"] + " " if data["currency"] != "USD" else ""),
    ))
    return fig


# ─── Radar chart multi-titres ─────────────────────────────────────────────

def radar_chart(stocks: list[dict]) -> go.Figure:
    """Compare up to 5 stocks on 6 normalized dimensions."""
    dims = ["RSI\n(neutre=50)", "Momentum\n3M", "P/E\n(inv.)", "Marge\nOpé.", "ROE", "52W\nPosition"]
    colors = [C["gold"], "#38BDF8", "#34D399", "#F472B6", "#A78BFA"]

    fig = go.Figure()
    for i, d in enumerate(stocks[:5]):
        # Normalize each dim to 0–100 (higher = better except RSI extremes & PE)
        rsi_norm  = 100 - abs(d["rsi"] - 50) * 2 if d["rsi"] else 50       # 50 = max, extremes bad
        mom_norm  = min(max((d["mom_3m"] or 0) + 50, 0), 100)               # 0% mom → 50, -50 → 0, +50 → 100
        pe_inv    = max(0, 100 - (d["pe"] or 25) / 0.5) if d["pe"] else 50  # lower PE → higher score
        pe_inv    = min(pe_inv, 100)
        margin_n  = min(max((d["oper_m"] or 0) * 2, 0), 100)                # 50% margin → 100
        roe_n     = min(max((d["roe"] or 0) * 3, 0), 100)                   # 33% ROE → 100
        pos_52w   = position_52w(d["price"], d["low_52w"], d["high_52w"])["pct"] if d["price"] else 50

        vals = [rsi_norm, mom_norm, pe_inv, margin_n, roe_n, pos_52w]
        vals_closed = vals + [vals[0]]
        dims_closed = dims + [dims[0]]

        fig.add_trace(go.Scatterpolar(
            r      = vals_closed,
            theta  = dims_closed,
            fill   = "toself",
            name   = d["ticker"],
            line   = dict(color=colors[i % len(colors)], width=2),
            fillcolor = f"rgba({int(colors[i%len(colors)][1:3],16)},"
                        f"{int(colors[i%len(colors)][3:5],16)},"
                        f"{int(colors[i%len(colors)][5:7],16)},0.1)",
        ))

    fig.update_layout(**plotly_layout(
        polar=dict(
            bgcolor      = "rgba(0,0,0,0)",
            angularaxis  = dict(tickfont=dict(color="#8892A0", size=10), linecolor="#2D3748"),
            radialaxis   = dict(visible=True, range=[0, 100],
                                tickfont=dict(color="#4A5568", size=8),
                                gridcolor="#2D3748", linecolor="#2D3748"),
        ),
        height=400,
        title=dict(text="Comparaison multi-critères (normalisée 0–100)", font=dict(size=13)),
        legend=dict(orientation="h", y=-0.1),
        margin=dict(l=50, r=50, t=50, b=50),
    ))
    return fig


# ─── Page layout ─────────────────────────────────────────────────────────────

st.markdown("## 🔍 Analyse d'Actions")
st.markdown(
    "<p style='color:#8892A0;margin-top:-8px;'>Entrez 1 à 5 tickers pour obtenir un verdict intelligent "
    "sur chaque titre : surchauffe, valorisation, qualité fondamentale.</p>",
    unsafe_allow_html=True,
)

# ── Input ────────────────────────────────────────────────────────────────────
with st.form("stock_form"):
    raw = st.text_input(
        "Tickers (séparés par des virgules)",
        value="AAPL, NVDA, MSFT",
        placeholder="ex: AAPL, TSLA, NVDA, META",
    )
    submitted = st.form_submit_button("Analyser →", use_container_width=True)

if not submitted:
    st.info("💡 Entrez vos tickers ci-dessus et cliquez sur **Analyser**.")
    st.stop()

tickers = [t.strip().upper() for t in raw.split(",") if t.strip()][:5]
if not tickers:
    st.warning("Veuillez entrer au moins un ticker.")
    st.stop()

# ── Load data ────────────────────────────────────────────────────────────────
stocks = []
errors = []
with st.spinner("Chargement des données de marché…"):
    for t in tickers:
        d = load_stock(t)
        if d:
            stocks.append(d)
        else:
            errors.append(t)

if errors:
    st.warning(f"Données introuvables pour : {', '.join(errors)}")

if not stocks:
    st.error("Aucune donnée disponible. Vérifiez vos tickers.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Carte verdict par action
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### Verdict par Titre")

for data in stocks:
    verdict = stock_verdict(
        rsi        = data["rsi"],
        pe         = data["pe"],
        momentum_3m= data["mom_3m"],
        sector     = data["sector"],
        roe        = data["roe"],
    )

    # Header card
    icon  = verdict["icon"]
    color = verdict["color"]
    label = verdict["label"]

    st.markdown(
        f"""<div style="background:rgba(30,37,53,0.6);border-left:4px solid {color};
        border-radius:8px;padding:16px 20px;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <span style="font-size:1.4rem;font-weight:700;color:#E2E8F0;">{icon} {data['name']}</span>
            <span style="color:#8892A0;font-size:0.85rem;margin-left:10px;">{data['ticker']} · {data['sector'] if data['sector'] not in ('Unknown', '', None) else '—'}</span>
          </div>
          <div style="text-align:right;">
            <span style="background:{color}22;color:{color};padding:4px 12px;border-radius:20px;
            font-size:0.85rem;font-weight:600;">{label}</span>
            <span style="color:#8892A0;font-size:0.8rem;margin-left:8px;">{fmt_mktcap(data['mktcap'])}</span>
          </div>
        </div>
        <p style="color:#CBD5E1;margin:10px 0 4px 0;font-size:0.9rem;">{verdict['recommendation']}</p>
        </div>""",
        unsafe_allow_html=True,
    )

    # Signals strip
    signals_html = "".join(
        f"<span style='background:rgba(100,100,100,0.2);color:#CBD5E1;padding:3px 10px;"
        f"border-radius:12px;font-size:0.78rem;margin-right:6px;'>{s}</span>"
        for s in verdict["signals"]
    )
    st.markdown(f"<div style='margin-bottom:16px;'>{signals_html}</div>", unsafe_allow_html=True)

    # ── Three columns: chart | RSI gauge | metrics
    col_chart, col_gauge, col_metrics = st.columns([3, 2, 2])

    with col_chart:
        st.plotly_chart(price_chart(data), use_container_width=True, config={"displayModeBar": False})

    with col_gauge:
        st.plotly_chart(rsi_gauge(data["rsi"], data["ticker"]),
                        use_container_width=True, config={"displayModeBar": False})

        rsi_interp = interpret_rsi(data["rsi"])
        st.markdown(
            f"<div style='text-align:center;color:{rsi_interp['color']};font-size:0.85rem;"
            f"font-weight:600;margin-top:-10px;'>{rsi_interp['label']}</div>"
            f"<div style='text-align:center;color:#8892A0;font-size:0.78rem;margin-top:4px;'>"
            f"{rsi_interp['text']}</div>",
            unsafe_allow_html=True,
        )

        # 52W position
        pos = position_52w(data["price"], data["low_52w"], data["high_52w"])
        pct = pos["pct"]
        st.markdown(
            f"""<div style='margin-top:14px;'>
            <div style='display:flex;justify-content:space-between;color:#8892A0;font-size:0.75rem;'>
              <span>52S bas</span><span>52S haut</span>
            </div>
            <div style='background:#2D3748;border-radius:4px;height:6px;margin:4px 0;'>
              <div style='background:{C['gold']};width:{pct:.0f}%;height:100%;border-radius:4px;'></div>
            </div>
            <div style='color:#CBD5E1;font-size:0.82rem;text-align:center;'>
              {data['price']:.2f} · {pos['interpretation']}
            </div></div>""",
            unsafe_allow_html=True,
        )

    with col_metrics:
        st.markdown("<div style='font-size:0.8rem;color:#8892A0;font-weight:600;margin-bottom:8px;"
                    "letter-spacing:0.05em;'>FONDAMENTAUX</div>", unsafe_allow_html=True)

        def metric_row(label, value, interp_text="", interp_color="#8892A0"):
            return (
                f"<div style='display:flex;justify-content:space-between;align-items:baseline;"
                f"border-bottom:1px solid #2D3748;padding:5px 0;'>"
                f"<span style='color:#8892A0;font-size:0.78rem;'>{label}</span>"
                f"<div style='text-align:right;'>"
                f"<span style='color:#E2E8F0;font-size:0.88rem;font-weight:600;'>{value}</span>"
                f"{'<br><span style=color:'+interp_color+';font-size:0.72rem;>' + interp_text + '</span>' if interp_text else ''}"
                f"</div></div>"
            )

        pe_interp  = interpret_pe(data["pe"], data["sector"])
        pb_interp  = interpret_pb(data["pb"])
        mgn_interp = interpret_margins(data["gross_m"], data["oper_m"])
        dbt_interp = interpret_debt(data["debt_eq"])

        rows = [
            metric_row("P/E (trailing)", fmt_val(data["pe"], 1),
                       pe_interp["verdict"], pe_interp["color"]),
            metric_row("P/B", fmt_val(data["pb"], 1),
                       pb_interp["verdict"], pb_interp["color"]),
            metric_row("Marge brute", fmt_pct(data["gross_m"]),
                       mgn_interp["verdict"], mgn_interp["color"]),
            metric_row("Marge opérationnelle", fmt_pct(data["oper_m"])),
            metric_row("Dette/Capitaux propres", fmt_val(data["debt_eq"], 1),
                       dbt_interp["verdict"], dbt_interp["color"]),
            metric_row("ROE", fmt_pct(data["roe"])),
        ]
        st.markdown("".join(rows), unsafe_allow_html=True)

        st.markdown("<div style='font-size:0.8rem;color:#8892A0;font-weight:600;"
                    "margin:14px 0 8px 0;letter-spacing:0.05em;'>MOMENTUM</div>", unsafe_allow_html=True)

        ma_interp = ma_signal(data["price"], data["ma50"], data["ma200"])
        rows_mom  = [
            metric_row("Momentum 3M", fmt_pct(data["mom_3m"])),
            metric_row("Momentum 6M", fmt_pct(data["mom_6m"])),
            metric_row("Momentum 1A", fmt_pct(data["mom_1y"])),
            metric_row("Signal MA", ma_interp["signal"],
                       ma_interp["detail"], ma_interp["color"]),
        ]
        st.markdown("".join(rows_mom), unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#2D3748;margin:24px 0;'>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Tableau comparatif
# ─────────────────────────────────────────────────────────────────────────────

if len(stocks) > 1:
    st.markdown("### Comparaison des Titres")

    rows = []
    for d in stocks:
        v = stock_verdict(d["rsi"], d["pe"], d["mom_3m"], d["sector"], d["roe"])
        rows.append({
            "Ticker":      d["ticker"],
            "Nom":         d["name"][:25],
            "Secteur":     d["sector"][:20] if d["sector"] else "—",
            "Prix":        f"{d['price']:.2f}",
            "RSI":         f"{d['rsi']:.1f}" if d["rsi"] else "—",
            "Mom. 3M":     fmt_pct(d["mom_3m"]),
            "P/E":         fmt_val(d["pe"], 1),
            "Marge Opé.":  fmt_pct(d["oper_m"]),
            "ROE":         fmt_pct(d["roe"]),
            "Verdict":     f"{v['icon']} {v['label']}",
        })

    df = pd.DataFrame(rows).set_index("Ticker")
    st.dataframe(df, use_container_width=True)

    # Radar
    st.markdown("### Profil Multi-Critères")
    st.plotly_chart(radar_chart(stocks), use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Note méthodologique
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("ℹ️ Méthodologie des verdicts"):
    st.markdown("""
**RSI (Relative Strength Index, période 14)**
RSI > 70 → zone de surchauffe. RSI < 30 → zone de survente. Zone 40–60 = neutre/sain.

**Verdict composite**
Combine 4 critères pondérés :
- RSI (surchauffe technique)
- P/E vs médiane sectorielle (survalorisation fondamentale)
- Momentum 3 mois (dynamique de prix)
- ROE (qualité du rendement sur capitaux)

Chaque critère génère un score positif ou négatif. La somme détermine la couleur :
🟢 Opportunité · 🔵 Neutre favorable · 🟡 Vigilance · 🟠 Risque · 🔴 Surchauffe/Fuite

**Limites**
Les fondamentaux (P/E, P/B, marges) proviennent de yfinance et peuvent présenter
un décalage de quelques jours. Ce verdict est indicatif et ne constitue pas un conseil en investissement.
    """)
