"""
Plotly chart factory — all figures use the same professional template.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config.settings import PLOTLY, CHART_COLORS, C


# ── Base template applier ─────────────────────────────────────────────────────
def _apply(fig: go.Figure, height: int = 380,
           legend: bool = True, margin_l: int = 48) -> go.Figure:
    layout = dict(PLOTLY)
    layout["height"]      = height
    layout["showlegend"]  = legend
    layout["margin"]      = {**PLOTLY["margin"], "l": margin_l}
    fig.update_layout(**layout)
    return fig


# ── Line chart ────────────────────────────────────────────────────────────────
def line(series: dict, title: str = "", y_label: str = "",
         height: int = 360, pct: bool = False,
         fill_first: bool = False) -> go.Figure:
    """Multi-series line chart. series = {name: pd.Series}."""
    fig = go.Figure()
    for i, (name, s) in enumerate(series.items()):
        y = s.values * 100 if pct else s.values
        kw = dict(
            x=s.index, y=y, name=name, mode="lines",
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.8),
        )
        if fill_first and i == 0:
            kw["fill"] = "tozeroy"
            kw["fillcolor"] = f"rgba({_hex2rgb(CHART_COLORS[0])},0.10)"
        fig.add_trace(go.Scatter(**kw))
    fig.update_yaxes(title_text=y_label)
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height)


# ── Area / underwater ─────────────────────────────────────────────────────────
def area(s: pd.Series, title: str = "", y_label: str = "",
         color: str = None, fill_color: str = None, height: int = 280) -> go.Figure:
    col  = color      or C["red"]
    fill = fill_color or "rgba(239,68,68,0.15)"
    fig  = go.Figure()
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values,
        fill="tozeroy", fillcolor=fill,
        line=dict(color=col, width=1.2),
        name="",
    ))
    fig.update_yaxes(title_text=y_label)
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height, legend=False)


# ── Bar chart ─────────────────────────────────────────────────────────────────
def bar(labels: list, values: list, title: str = "",
        color_by_sign: bool = True, height: int = 320,
        horizontal: bool = False) -> go.Figure:
    if color_by_sign:
        colors = [C["green"] if v >= 0 else C["red"] for v in values]
    else:
        colors = CHART_COLORS[:len(labels)]

    if horizontal:
        trace = go.Bar(y=labels, x=values, orientation="h", marker_color=colors)
    else:
        trace = go.Bar(x=labels, y=values, marker_color=colors)

    fig = go.Figure(trace)
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height, legend=False)


# ── Grouped bar ───────────────────────────────────────────────────────────────
def grouped_bar(df: pd.DataFrame, title: str = "",
                height: int = 380) -> go.Figure:
    """df: rows=categories, columns=series."""
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        colors = [C["green"] if v >= 0 else C["red"] for v in df[col]]
        fig.add_trace(go.Bar(
            name=col, x=df.index.tolist(), y=df[col].values,
            marker_color=CHART_COLORS[i % len(CHART_COLORS)],
        ))
    fig.update_layout(barmode="group", title_text=title)
    return _apply(fig, height=height)


# ── Heatmap ───────────────────────────────────────────────────────────────────
def heatmap(matrix: pd.DataFrame, title: str = "",
            zmin: float = -1, zmax: float = 1,
            colorscale: str = "RdYlGn", height: int = 420,
            fmt: str = ".2f") -> go.Figure:
    fig = px.imshow(
        matrix,
        text_auto=fmt,
        color_continuous_scale=colorscale,
        zmin=zmin, zmax=zmax,
    )
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height)


# ── Pie / Donut ───────────────────────────────────────────────────────────────
def donut(labels: list, values: list, title: str = "",
          height: int = 360) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(colors=CHART_COLORS[:len(labels)],
                    line=dict(color=C["bg"], width=2)),
        textinfo="label+percent",
        textfont_size=11,
        insidetextorientation="radial",
    ))
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height)


# ── Scatter (efficient frontier) ──────────────────────────────────────────────
def scatter(x, y, color=None, title: str = "",
            x_label: str = "", y_label: str = "",
            colorbar_title: str = "", height: int = 480) -> go.Figure:
    fig = go.Figure()
    if color is not None:
        fig.add_trace(go.Scatter(
            x=x * 100, y=y * 100,
            mode="markers",
            marker=dict(
                color=color,
                colorscale="Viridis",
                size=3,
                opacity=0.55,
                colorbar=dict(title=colorbar_title, thickness=12,
                              len=0.6, x=1.01,
                              tickfont=dict(size=10)),
            ),
            hovertemplate=f"Vol: %{{x:.2f}}%<br>Rend: %{{y:.2f}}%<extra></extra>",
            showlegend=False,
        ))
    else:
        fig.add_trace(go.Scatter(
            x=x * 100, y=y * 100, mode="markers",
            marker=dict(color=C["blue"], size=3, opacity=0.5),
            showlegend=False,
        ))
    fig.update_xaxes(title_text=x_label)
    fig.update_yaxes(title_text=y_label)
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height)


# ── Histogram with KDE ────────────────────────────────────────────────────────
def histogram(s: pd.Series, title: str = "", nbins: int = 80,
              vlines: list = None, height: int = 320) -> go.Figure:
    """vlines: list of (x, color, label)."""
    from scipy import stats as sp_stats
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=s * 100, nbinsx=nbins,
        marker_color=C["blue"], opacity=0.7, name="Rendements",
    ))
    # Normal fit overlay
    xs = np.linspace(s.min() * 100, s.max() * 100, 300)
    mu, sigma = (s * 100).mean(), (s * 100).std()
    pdf = sp_stats.norm.pdf(xs, mu, sigma)
    scale = len(s) * (s.max() - s.min()) * 100 / nbins
    fig.add_trace(go.Scatter(
        x=xs, y=pdf * scale, mode="lines",
        line=dict(color="rgba(255,255,255,0.6)", width=1.5, dash="dot"),
        name="Loi normale",
    ))
    if vlines:
        for xv, col, lbl in vlines:
            fig.add_vline(x=xv * 100, line_color=col, line_dash="dash",
                          annotation_text=lbl, annotation_position="top right",
                          annotation_font_size=10)
    fig.update_xaxes(title_text="Rendement journalier (%)")
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height)


# ── Yield curve ───────────────────────────────────────────────────────────────
def yield_curve(snapshots: dict, mat_vals: list, mat_labels: list,
                title: str = "Courbe des Taux", height: int = 400) -> go.Figure:
    """snapshots = {label: array_of_yields}."""
    fig = go.Figure()
    styles = [
        dict(color=C["gold"], width=2.5, dash="solid"),
        dict(color=C["muted"], width=1.5, dash="dash"),
        dict(color=C["blue"], width=1.5, dash="dot"),
    ]
    for i, (lbl, vals) in enumerate(snapshots.items()):
        s = styles[i % len(styles)]
        fig.add_trace(go.Scatter(
            x=mat_vals, y=vals,
            mode="lines+markers",
            line=s,
            marker=dict(size=7),
            name=lbl,
            hovertemplate="%{y:.2f}%<extra>" + lbl + "</extra>",
        ))
        # Annotate the last snapshot
        if i == 0:
            for xv, yv in zip(mat_vals, vals):
                fig.add_annotation(
                    x=xv, y=yv, text=f"{yv:.2f}%",
                    showarrow=False, yshift=12,
                    font=dict(size=10, color=C["gold"]),
                )
    fig.update_xaxes(title_text="Maturité",
                     tickvals=mat_vals, ticktext=mat_labels)
    fig.update_yaxes(title_text="Taux (%)")
    fig.update_layout(title_text=title)
    return _apply(fig, height=height)


# ── Waterfall ─────────────────────────────────────────────────────────────────
def waterfall(labels: list, values: list, title: str = "",
              height: int = 320) -> go.Figure:
    colors = [C["green"] if v >= 0 else C["red"] for v in values]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"{v:+.2f}%" for v in values],
        textposition="outside",
        textfont=dict(size=10),
    ))
    fig.add_hline(y=0, line_color=C["border"], line_width=1)
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height, legend=False)


# ── Dendogram (for HRP) ───────────────────────────────────────────────────────
def dendrogram(linkage_matrix, labels: list, title: str = "",
               height: int = 320) -> go.Figure:
    import scipy.cluster.hierarchy as sch
    dn = sch.dendrogram(linkage_matrix, labels=labels, no_plot=True)
    fig = go.Figure()
    for xs, ys in zip(dn["icoord"], dn["dcoord"]):
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            line=dict(color=C["gold"], width=1.2),
            showlegend=False,
        ))
    tick_pos = [xs[1] for xs in dn["icoord"] if xs[1] in dn["leaves_color_list"]]
    fig.update_xaxes(
        tickvals=[5 + 10 * i for i in range(len(dn["ivl"]))],
        ticktext=dn["ivl"],
        tickfont=dict(size=10),
    )
    fig.update_yaxes(title_text="Distance")
    if title:
        fig.update_layout(title_text=title)
    return _apply(fig, height=height, legend=False)


# ── Risk contribution stacked bar ─────────────────────────────────────────────
def risk_contrib_bar(labels: list, rc_before: list, rc_after: list,
                     method: str = "ERC", height: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Pondération naïve (1/N)",
        x=labels, y=rc_before,
        marker_color=C["muted"], opacity=0.6,
    ))
    fig.add_trace(go.Bar(
        name=f"Portefeuille {method}",
        x=labels, y=rc_after,
        marker_color=C["gold"],
    ))
    fig.update_layout(
        barmode="group",
        yaxis_title="Contribution au risque (%)",
        title_text=f"Contribution au risque — {method} vs Équipondéré",
    )
    return _apply(fig, height=height)


# ── Helper ────────────────────────────────────────────────────────────────────
def _hex2rgb(h: str) -> str:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
