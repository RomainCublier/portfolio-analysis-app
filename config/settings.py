"""
Central configuration: palette, CSS, and Plotly template.
"""

APP_NAME    = "QuantDesk"
APP_VERSION = "2.0"

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":       "#0B0E17",
    "surface":  "#111827",
    "surface2": "#1A2233",
    "border":   "#1F2D42",
    "text":     "#E5EAF3",
    "muted":    "#7B8EA8",
    "gold":     "#C9A94A",
    "blue":     "#4A8FD4",
    "green":    "#22C55E",
    "red":      "#EF4444",
    "orange":   "#F59E0B",
    "purple":   "#8B5CF6",
    "cyan":     "#06B6D4",
}

CHART_COLORS = [
    "#4A8FD4", "#C9A94A", "#22C55E", "#EF4444",
    "#8B5CF6", "#F59E0B", "#06B6D4", "#EC4899",
    "#A3E635", "#FB923C",
]

# ── Plotly Template ───────────────────────────────────────────────────────────
# Base Plotly layout — ne contient PAS les clés souvent surchargées
# (title, xaxis, yaxis, legend, margin) pour éviter les TypeError Python.
# Utiliser plotly_layout(**overrides) à la place de update_layout(**PLOTLY, ...).
_PLOTLY_BASE = {
    "plot_bgcolor":  C["surface"],
    "paper_bgcolor": C["bg"],
    "font":          {"family": "'Inter','Segoe UI',-apple-system,sans-serif",
                      "color": C["text"], "size": 12},
    "colorway":      CHART_COLORS,
    "hoverlabel":    {"bgcolor": C["surface2"], "bordercolor": C["border"],
                      "font": {"size": 12, "color": C["text"]}},
    "modebar":       {"bgcolor": "rgba(0,0,0,0)", "color": C["muted"],
                      "activecolor": C["gold"]},
}

# Defaults pour axes et légende — appliqués via plotly_layout()
_PLOTLY_AXES = {
    "xaxis":  {"gridcolor": C["surface2"], "linecolor": C["border"],
               "zerolinecolor": C["border"],
               "tickfont": {"size": 11, "color": C["muted"]}},
    "yaxis":  {"gridcolor": C["surface2"], "linecolor": C["border"],
               "zerolinecolor": C["border"],
               "tickfont": {"size": 11, "color": C["muted"]}},
    "legend": {"bgcolor": "rgba(0,0,0,0)", "bordercolor": C["border"],
               "borderwidth": 1, "font": {"size": 11}},
    "title":  {"font": {"size": 14, "color": C["gold"],
                        "family": "'Inter','Segoe UI',sans-serif"},
               "pad": {"t": 2, "b": 2}},
}

# Alias rétro-compatible : PLOTLY = base seule (pour les anciens fichiers)
PLOTLY = dict(_PLOTLY_BASE)


def plotly_layout(**overrides) -> dict:
    """
    Retourne un dict prêt à passer à fig.update_layout().

    Fusionne le template de base + défauts axes/légende + surcharges caller.
    Usage :
        fig.update_layout(**plotly_layout(
            height=300,
            margin=dict(l=0, r=0, t=40, b=0),
            title=dict(text="Mon titre"),
            yaxis=dict(ticksuffix="%"),
        ))
    """
    result = dict(_PLOTLY_BASE)
    # Merge axis/legend defaults, puis les surcharges caller
    for key, default_val in _PLOTLY_AXES.items():
        if key in overrides and isinstance(overrides[key], dict):
            # Fusionner le défaut avec la surcharge (la surcharge prime)
            merged = dict(default_val)
            merged.update(overrides.pop(key))
            result[key] = merged
        else:
            result[key] = default_val
    result.update(overrides)
    return result

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset & base ────────────────────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main { background-color: #0B0E17 !important; }

* { font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif !important; }

/* ── Fix icônes Streamlit (Material Symbols) ────────────────────────────── */
/* La règle * ci-dessus écrase la police Material Symbols utilisée pour les
   icônes d'expanders, boutons, etc. On la restaure explicitement. */
.material-symbols-rounded,
.material-symbols-outlined,
.material-icons,
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] * {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24 !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #0D1320 !important;
    border-right: 1px solid #1F2D42 !important;
}
[data-testid="stSidebarContent"] { padding: 0 !important; }

/* App name in sidebar */
[data-testid="stSidebarNav"]::before {
    content: "QUANTDESK";
    display: block;
    padding: 20px 16px 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2em;
    color: #C9A94A;
}

[data-testid="stSidebarNavLink"] {
    padding: 8px 16px !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    color: #7B8EA8 !important;
    margin: 1px 8px !important;
    text-decoration: none !important;
}
[data-testid="stSidebarNavLink"]:hover { color: #E5EAF3 !important; background: #1A2233 !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(201,169,74,0.12) !important;
    color: #C9A94A !important;
    font-weight: 600 !important;
    border-left: 2px solid #C9A94A !important;
}

/* ── Typography ──────────────────────────────────────────────────────────── */
h1 {
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #E5EAF3 !important;
    letter-spacing: -0.02em !important;
    padding-bottom: 10px !important;
    margin-bottom: 16px !important;
    border-bottom: 1px solid #1F2D42 !important;
}
h2 {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #C9A94A !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    margin-top: 28px !important;
    margin-bottom: 12px !important;
}
h3 {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #7B8EA8 !important;
    margin-bottom: 6px !important;
}
p, li, label, span { color: #E5EAF3; font-size: 13px; }

/* ── Metric cards ────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #111827 !important;
    border: 1px solid #1F2D42 !important;
    border-radius: 6px !important;
    padding: 14px 16px !important;
    transition: border-color 0.15s ease;
}
[data-testid="metric-container"]:hover { border-color: #C9A94A !important; }
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: #7B8EA8 !important;
}
[data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 600 !important;
    color: #E5EAF3 !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] { font-size: 12px !important; }
[data-testid="stMetricDeltaIcon-Up"]   { color: #22C55E !important; }
[data-testid="stMetricDeltaIcon-Down"] { color: #EF4444 !important; }

/* ── Tabs ────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid #1F2D42 !important;
    gap: 0 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #7B8EA8 !important;
    padding: 8px 16px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: #E5EAF3 !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #C9A94A !important;
    border-bottom-color: #C9A94A !important;
    background: transparent !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: #C9A94A !important;
    color: #0B0E17 !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border-radius: 4px !important;
    padding: 8px 24px !important;
}
.stButton > button[kind="primary"]:hover { background: #D9B95A !important; }
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #7B8EA8 !important;
    border: 1px solid #1F2D42 !important;
    border-radius: 4px !important;
    font-size: 12px !important;
}
.stButton > button[kind="secondary"]:hover {
    color: #E5EAF3 !important;
    border-color: #C9A94A !important;
}

/* ── Inputs & selects ────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: #111827 !important;
    border: 1px solid #1F2D42 !important;
    color: #E5EAF3 !important;
    border-radius: 4px !important;
    font-size: 13px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #C9A94A !important;
    box-shadow: 0 0 0 2px rgba(201,169,74,0.15) !important;
}
[data-baseweb="select"] { background: #111827 !important; }
[data-baseweb="select"] * { color: #E5EAF3 !important; }
[data-baseweb="popover"] { background: #111827 !important; border: 1px solid #1F2D42 !important; }

/* ── Dataframes ──────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #1F2D42 !important;
    border-radius: 6px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: #1A2233 !important;
    color: #7B8EA8 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid #1F2D42 !important;
}
[data-testid="stDataFrame"] td {
    font-size: 12px !important;
    color: #E5EAF3 !important;
    border-bottom: 1px solid #1A2233 !important;
}
[data-testid="stDataFrame"] tr:hover td { background: #1A2233 !important; }

/* ── Info / Warning / Error ──────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 4px !important;
    font-size: 13px !important;
    border-left: 3px solid !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="info"] {
    background: rgba(74,143,212,0.08) !important;
    border-left-color: #4A8FD4 !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="success"] {
    background: rgba(34,197,94,0.08) !important;
    border-left-color: #22C55E !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="warning"] {
    background: rgba(245,158,11,0.08) !important;
    border-left-color: #F59E0B !important;
}
[data-testid="stAlert"][data-baseweb="notification"][kind="error"] {
    background: rgba(239,68,68,0.08) !important;
    border-left-color: #EF4444 !important;
}

/* ── Dividers ────────────────────────────────────────────────────────────── */
hr { border-color: #1F2D42 !important; margin: 20px 0 !important; }

/* ── Expanders ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #1F2D42 !important;
    border-radius: 6px !important;
    background: #111827 !important;
}
[data-testid="stExpander"] summary {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #7B8EA8 !important;
}

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar            { width: 5px; height: 5px; }
::-webkit-scrollbar-track      { background: #0B0E17; }
::-webkit-scrollbar-thumb      { background: #1F2D42; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2D3E55; }

/* ── Spinner ─────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div { border-top-color: #C9A94A !important; }

/* ── Forms ───────────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: #111827;
    border: 1px solid #1F2D42;
    border-radius: 8px;
    padding: 20px !important;
}

/* ── Slider ──────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [role="slider"] { background: #C9A94A !important; }
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stMarkdownContainer"] {
    font-size: 11px !important; color: #7B8EA8 !important;
}

/* ── Custom utility classes ──────────────────────────────────────────────── */
.kpi-positive { color: #22C55E !important; font-weight: 600; }
.kpi-negative { color: #EF4444 !important; font-weight: 600; }
.kpi-neutral  { color: #F59E0B !important; font-weight: 600; }

.section-tag {
    display: inline-block;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #C9A94A;
    border: 1px solid rgba(201,169,74,0.4);
    border-radius: 2px;
    padding: 2px 7px;
    margin-bottom: 10px;
    vertical-align: middle;
}
</style>
"""
