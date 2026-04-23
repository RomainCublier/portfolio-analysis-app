"""
QuantDesk — Configuration visuelle.
Palette inspirée de l'esthétique Aladdin / Bloomberg : terminal institutionnel,
bleu nuit profond, typographie dense, zéro décoratif superflu.
"""

APP_NAME    = "QuantDesk"
APP_VERSION = "3.0"

# ── Palette institutionnelle ──────────────────────────────────────────────────
C = {
    # Fonds
    "bg":          "#060A14",   # quasi-noir bleu
    "surface":     "#0C1322",   # dark navy
    "surface2":    "#101A2E",   # slightly lighter
    "surface3":    "#152138",   # hover state

    # Bordures
    "border":      "#1C2D45",
    "border2":     "#243652",

    # Texte
    "text":        "#E8EDF5",   # blanc doux
    "text2":       "#A8B4C4",   # gris-bleu clair
    "muted":       "#5A6E82",   # gris-bleu sombre

    # Accents institutionnels
    "blue":        "#2563EB",   # accent principal
    "blue_light":  "#3B82F6",   # hover / variante
    "blue_dim":    "#1E40AF",   # variante sombre
    "teal":        "#0D9488",

    # Signaux
    "green":       "#10B981",
    "red":         "#EF4444",
    "orange":      "#F59E0B",
    "yellow":      "#EAB308",
    "purple":      "#8B5CF6",

    # Alias rétro-compat (anciennes pages utilisaient "gold")
    "gold":        "#3B82F6",
}

CHART_COLORS = [
    "#3B82F6",  # blue
    "#10B981",  # green
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#8B5CF6",  # purple
    "#06B6D4",  # cyan
    "#EC4899",  # pink
    "#A3E635",  # lime
    "#FB923C",  # orange
    "#14B8A6",  # teal
]

# ── Template Plotly ───────────────────────────────────────────────────────────
_PLOTLY_BASE = {
    "plot_bgcolor":  C["surface"],
    "paper_bgcolor": C["bg"],
    "font": {
        "family": "'Inter','IBM Plex Sans','Segoe UI',sans-serif",
        "color":  C["text2"],
        "size":   11,
    },
    "colorway":   CHART_COLORS,
    "hoverlabel": {
        "bgcolor":     C["surface2"],
        "bordercolor": C["border2"],
        "font":        {"size": 11, "color": C["text"]},
    },
    "modebar": {
        "bgcolor":     "rgba(0,0,0,0)",
        "color":       C["muted"],
        "activecolor": C["blue_light"],
    },
}

_PLOTLY_AXES = {
    "xaxis": {
        "gridcolor":     C["surface2"],
        "linecolor":     C["border"],
        "zerolinecolor": C["border2"],
        "tickfont":      {"size": 10, "color": C["muted"]},
        "tickcolor":     C["border"],
    },
    "yaxis": {
        "gridcolor":     C["surface2"],
        "linecolor":     C["border"],
        "zerolinecolor": C["border2"],
        "tickfont":      {"size": 10, "color": C["muted"]},
        "tickcolor":     C["border"],
    },
    "legend": {
        "bgcolor":     "rgba(0,0,0,0)",
        "bordercolor": C["border"],
        "borderwidth": 1,
        "font":        {"size": 10, "color": C["text2"]},
    },
    "title": {
        "font": {
            "size":   12,
            "color":  C["text2"],
            "family": "'Inter','IBM Plex Sans',sans-serif",
        },
        "pad": {"t": 0, "b": 4},
    },
}

# Alias rétro-compatible
PLOTLY = dict(_PLOTLY_BASE)


def plotly_layout(**overrides) -> dict:
    """
    Retourne un dict prêt pour fig.update_layout(**plotly_layout(...)).
    Fusionne template de base + défauts axes/légende + surcharges caller.
    Les surcharges de type dict sont fusionnées (merge profond niveau 1).
    """
    result = dict(_PLOTLY_BASE)
    for key, default in _PLOTLY_AXES.items():
        if key in overrides and isinstance(overrides[key], dict):
            merged = dict(default)
            merged.update(overrides.pop(key))
            result[key] = merged
        else:
            result[key] = default
    result.update(overrides)
    return result


# ── CSS — Terminal institutionnel ─────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ── Reset & base ─────────────────────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {
    background-color: #060A14 !important;
}
* { font-family: 'Inter', 'IBM Plex Sans', 'Segoe UI', sans-serif !important; }

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #060A10 !important;
    border-right: 1px solid #1C2D45 !important;
}

[data-testid="stSidebarNav"]::before {
    content: "QUANTDESK";
    display: block;
    padding: 20px 16px 14px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.28em;
    color: #3B82F6;
    border-bottom: 1px solid #1C2D45;
    margin-bottom: 6px;
}

[data-testid="stSidebarNavLink"] {
    display: flex !important;
    align-items: center !important;
    padding: 8px 16px !important;
    border-radius: 0 !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    color: #5A6E82 !important;
    margin: 0 !important;
    border-left: 2px solid transparent !important;
    letter-spacing: 0.02em !important;
    text-decoration: none !important;
}
[data-testid="stSidebarNavLink"]:hover {
    color: #A8B4C4 !important;
    background: rgba(37,99,235,0.05) !important;
    border-left-color: #1C2D45 !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    color: #E8EDF5 !important;
    background: rgba(37,99,235,0.10) !important;
    border-left: 2px solid #2563EB !important;
    font-weight: 600 !important;
}

/* ── Typographie ──────────────────────────────────────────────────────────── */
h1 {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #E8EDF5 !important;
    letter-spacing: 0.01em !important;
    padding-bottom: 10px !important;
    margin-bottom: 16px !important;
    border-bottom: 1px solid #1C2D45 !important;
}
h2 {
    font-size: 8px !important;
    font-weight: 700 !important;
    color: #2563EB !important;
    text-transform: uppercase !important;
    letter-spacing: 0.20em !important;
    margin: 22px 0 10px 0 !important;
    padding-bottom: 5px !important;
    border-bottom: 1px solid #1C2D45 !important;
}
h3 {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #A8B4C4 !important;
    letter-spacing: 0.04em !important;
    margin-bottom: 8px !important;
}
p, li { color: #A8B4C4 !important; font-size: 12px !important; line-height: 1.6 !important; }
label span { color: #5A6E82 !important; font-size: 10px !important; font-weight: 600 !important;
             text-transform: uppercase !important; letter-spacing: 0.10em !important; }

/* ── Metric cards ─────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #0C1322 !important;
    border: 1px solid #1C2D45 !important;
    border-radius: 2px !important;
    padding: 12px 14px !important;
    transition: border-color 0.1s;
}
[data-testid="metric-container"]:hover { border-color: #243652 !important; }
[data-testid="stMetricLabel"] {
    font-size: 9px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: #5A6E82 !important;
}
[data-testid="stMetricValue"] {
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #E8EDF5 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"]          { font-size: 11px !important; }
[data-testid="stMetricDeltaIcon-Up"]   { color: #10B981 !important; }
[data-testid="stMetricDeltaIcon-Down"] { color: #EF4444 !important; }

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid #1C2D45 !important;
    gap: 0 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-size: 9px !important;
    font-weight: 700 !important;
    color: #5A6E82 !important;
    padding: 7px 18px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.10em !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: #A8B4C4 !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #3B82F6 !important;
    border-bottom-color: #2563EB !important;
}

/* ── Boutons ──────────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: #1D4ED8 !important;
    color: #E8EDF5 !important;
    border: none !important;
    border-radius: 2px !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
    padding: 8px 22px !important;
}
.stButton > button[kind="primary"]:hover { background: #2563EB !important; }
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #5A6E82 !important;
    border: 1px solid #1C2D45 !important;
    border-radius: 2px !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
.stButton > button[kind="secondary"]:hover {
    color: #A8B4C4 !important;
    border-color: #243652 !important;
    background: #0C1322 !important;
}

/* ── Inputs & selects ─────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: #0C1322 !important;
    border: 1px solid #1C2D45 !important;
    border-radius: 2px !important;
    color: #E8EDF5 !important;
    font-size: 12px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 2px rgba(37,99,235,0.12) !important;
}
[data-baseweb="select"] { background: #0C1322 !important; }
[data-baseweb="select"] * { color: #E8EDF5 !important; font-size: 12px !important; }
[data-baseweb="popover"] { background: #0C1322 !important; border: 1px solid #1C2D45 !important; }

/* ── Dataframes ───────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #1C2D45 !important;
    border-radius: 2px !important;
}
[data-testid="stDataFrame"] th {
    background: #0C1322 !important;
    color: #5A6E82 !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.10em !important;
    border-bottom: 1px solid #1C2D45 !important;
    padding: 7px 10px !important;
}
[data-testid="stDataFrame"] td {
    font-size: 11px !important;
    color: #A8B4C4 !important;
    border-bottom: 1px solid #0C1322 !important;
    padding: 5px 10px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stDataFrame"] tr:nth-child(even) td { background: rgba(12,19,34,0.5) !important; }
[data-testid="stDataFrame"] tr:hover td { background: #101A2E !important; }

/* ── data_editor ──────────────────────────────────────────────────────────── */
[data-testid="stDataEditor"] {
    border: 1px solid #1C2D45 !important;
    border-radius: 2px !important;
}

/* ── Alertes ──────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 2px !important;
    font-size: 12px !important;
    border-left: 3px solid !important;
}

/* ── Expanders ────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #1C2D45 !important;
    border-radius: 2px !important;
    background: #0C1322 !important;
    margin-bottom: 4px !important;
}
[data-testid="stExpander"] summary {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #A8B4C4 !important;
    padding: 9px 14px !important;
}
[data-testid="stExpander"] summary:hover { color: #E8EDF5 !important; }

/* ── Forms ────────────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: #0C1322 !important;
    border: 1px solid #1C2D45 !important;
    border-radius: 2px !important;
    padding: 16px !important;
}

/* ── Slider ───────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [role="slider"] {
    background: #2563EB !important;
    border-color: #2563EB !important;
}

/* ── HR ───────────────────────────────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid #1C2D45 !important; margin: 16px 0 !important; }

/* ── Spinner ──────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div { border-top-color: #2563EB !important; }

/* ── Scrollbar ────────────────────────────────────────────────────────────── */
::-webkit-scrollbar            { width: 4px; height: 4px; }
::-webkit-scrollbar-track      { background: #060A14; }
::-webkit-scrollbar-thumb      { background: #1C2D45; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #243652; }

/* ── Utilitaires ──────────────────────────────────────────────────────────── */
.ql-pos   { color: #10B981 !important; font-weight: 600; }
.ql-neg   { color: #EF4444 !important; font-weight: 600; }
.ql-neu   { color: #F59E0B !important; font-weight: 600; }
.ql-muted { color: #5A6E82 !important; }
.mono     { font-family: 'IBM Plex Mono', monospace !important; }

/* Tag institutionnel */
.ql-tag {
    display: inline-block;
    font-size: 8px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #3B82F6;
    border: 1px solid rgba(37,99,235,0.30);
    border-radius: 1px;
    padding: 1px 6px;
    margin-bottom: 6px;
}

/* Carte de données */
.ql-card {
    background: #0C1322;
    border: 1px solid #1C2D45;
    border-radius: 2px;
    padding: 14px 16px;
    margin-bottom: 6px;
}
.ql-card:hover { border-color: #243652; }

/* Barre de progress fine */
.ql-bar-track {
    background: #1C2D45;
    border-radius: 1px;
    height: 4px;
    margin: 4px 0;
}
.ql-bar-fill {
    height: 100%;
    border-radius: 1px;
}
</style>
"""
