"""Centralised investment assumptions and asset metadata."""

from datetime import date

APP_NAME = "GPT Portfolio Assistant"
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE = date.today().isoformat()

RISK_LEVELS = ["Very Low", "Low", "Moderate", "High", "Very High"]
INVESTMENT_HORIZONS = [
    "Short (<3 years)",
    "Medium (3–5 years)",
    "Long (5–10 years)",
    "Very Long (>10 years)",
]

ETF_DATABASE = {
    "SPY": "US Equities",
    "QQQ": "US Tech Growth",
    "VTI": "US Total Market",
    "AGG": "US Bonds",
    "GLDM": "Gold",
    "BTC-USD": "Crypto",
}

ASSET_CLASS_TICKERS = {
    "US Equities": ["SPY", "VTI"],
    "US Tech Growth": ["QQQ"],
    "US Bonds": ["AGG"],
    "Gold": ["GLDM"],
    "Crypto": ["BTC-USD"],
}

BASE_ALLOCATIONS = {
    "Very Low": {"SPY": 10, "QQQ": 0, "VTI": 10, "AGG": 65, "GLDM": 15},
    "Low": {"SPY": 20, "QQQ": 5, "VTI": 20, "AGG": 45, "GLDM": 10},
    "Moderate": {"SPY": 35, "QQQ": 15, "VTI": 20, "AGG": 20, "GLDM": 5, "BTC-USD": 5},
    "High": {"SPY": 35, "QQQ": 25, "VTI": 15, "AGG": 10, "GLDM": 5, "BTC-USD": 10},
    "Very High": {"SPY": 30, "QQQ": 35, "VTI": 10, "AGG": 5, "GLDM": 5, "BTC-USD": 15},
}

EXPECTED_RETURNS = {
    "SPY": 0.08,
    "QQQ": 0.10,
    "VTI": 0.075,
    "AGG": 0.03,
    "GLDM": 0.04,
    "BTC-USD": 0.20,
}

EXPECTED_VOLATILITIES = {
    "SPY": 0.16,
    "QQQ": 0.22,
    "VTI": 0.15,
    "AGG": 0.06,
    "GLDM": 0.12,
    "BTC-USD": 0.65,
}

CORRELATIONS = {
    ("SPY", "QQQ"): 0.85,
    ("SPY", "VTI"): 0.90,
    ("SPY", "AGG"): 0.35,
    ("SPY", "GLDM"): 0.10,
    ("SPY", "BTC-USD"): 0.05,
    ("QQQ", "AGG"): 0.20,
    ("QQQ", "GLDM"): 0.05,
    ("QQQ", "BTC-USD"): 0.10,
    ("VTI", "AGG"): 0.30,
    ("VTI", "GLDM"): 0.08,
    ("VTI", "BTC-USD"): 0.05,
    ("AGG", "GLDM"): -0.10,
    ("AGG", "BTC-USD"): 0.00,
    ("GLDM", "BTC-USD"): 0.15,
}
