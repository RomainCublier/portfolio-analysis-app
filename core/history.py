"""Strict total-return series contract and reference buy-and-hold calculation.

No network calls, interpolation, implicit FX conversion or fee double counting.
This kernel is not a transaction ledger or a trading/execution simulator.
"""
from dataclasses import dataclass
import hashlib
import math
import re
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SeriesMetadata:
    instrument_id: str
    currency: str
    source_url: str
    retrieved_at: str
    inception_date: str
    return_basis: str  # net_total_return: distributions reinvested, fund fees embedded
    origin: str  # fund, proxy, synthetic
    license_status: str  # approved or unknown; scopes reviewed outside this module
    license_reference: str
    raw_sha256: str


def _dates(index):
    if (not isinstance(index, pd.DatetimeIndex) or index.tz is not None or index.hasnans
            or not index.is_unique or not index.is_monotonic_increasing
            or not index.equals(index.normalize()) or len(index) < 2):
        raise ValueError("Dates quotidiennes ordonnées, uniques et sans fuseau requises.")


def validate_panel(levels, metadata, expected_dates, reporting_currency="EUR", commercial=False):
    """expected_dates must be a separately reviewed valuation calendar.

    Exact equality intentionally rejects gaps instead of dropping/replacing them.
    Dates alone do not detect stale prices repeated by an upstream provider.
    """
    _dates(expected_dates)
    _dates(levels.index)
    if not levels.index.equals(expected_dates):
        raise ValueError("Historique incomplet ou calendrier incompatible.")
    if levels.empty or not levels.columns.is_unique or set(levels.columns) != set(metadata):
        raise ValueError("Chaque série doit avoir ses métadonnées, sans doublon.")
    if any(not pd.api.types.is_numeric_dtype(t) or pd.api.types.is_bool_dtype(t) for t in levels.dtypes):
        raise ValueError("Valeurs numériques requises.")
    if not np.isfinite(levels.to_numpy(dtype=float)).all() or (levels <= 0).any().any():
        raise ValueError("Valeurs manquantes, infinies, nulles ou négatives interdites.")
    for key in levels:
        m = metadata[key]
        if m.instrument_id != key or m.currency != reporting_currency:
            raise ValueError("Identité ou devise incompatible ; conversion explicite requise.")
        if m.return_basis != "net_total_return":
            raise ValueError("Série de rendement total net documentée requise.")
        if m.origin not in {"fund", "proxy", "synthetic"}:
            raise ValueError("Origine non reconnue.")
        if not m.source_url.startswith("https://") or not re.fullmatch(r"[a-f0-9]{64}", m.raw_sha256):
            raise ValueError("Provenance incomplète.")
        retrieved = pd.Timestamp(m.retrieved_at)
        inception = pd.Timestamp(m.inception_date)
        if pd.isna(retrieved) or pd.isna(inception):
            raise ValueError("Date de provenance invalide.")
        if inception.tz is not None or inception != inception.normalize():
            raise ValueError("Date de création invalide.")
        if levels.index[0] < inception:
            raise ValueError("Historique antérieur à la création de la série.")
        if levels.index[-1].date() > retrieved.date():
            raise ValueError("Observation postérieure à sa récupération.")
        if m.license_status not in {"approved", "unknown"}:
            raise ValueError("Statut de licence non reconnu.")
        if commercial and (m.license_status != "approved" or not m.license_reference.strip() or m.origin != "fund"):
            raise ValueError("Historique réel et droits commerciaux documentés requis.")
    return {"start": str(levels.index[0].date()), "end": str(levels.index[-1].date()),
            "observations": len(levels), "currency": reporting_currency,
            "origins": {k: metadata[k].origin for k in levels},
            "normalized_sha256": hashlib.sha256(levels.to_csv().encode()).hexdigest()}


def buy_and_hold(levels, weights, metadata, expected_dates, commercial=False):
    """Initial allocation held without rebalancing, no cash flows or trading costs.

    Input total-return levels already include fund expenses: no additional TER.
    Output begins at 1 before the first return, preserving first-period losses.
    """
    report = validate_panel(levels, metadata, expected_dates, commercial=commercial)
    if set(weights) != set(levels.columns):
        raise ValueError("Poids et séries doivent correspondre exactement.")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in weights.values()):
        raise ValueError("Poids positifs ou nuls requis.")
    if not math.isclose(sum(weights.values()), 1, abs_tol=1e-10, rel_tol=0):
        raise ValueError("Les poids doivent totaliser 100 %.")
    w = pd.Series(weights).reindex(levels.columns)
    curve = levels.div(levels.iloc[0]).mul(w).sum(axis=1, skipna=False)
    return curve.rename("Valeur base 1"), report


def path_metrics(curve):
    """Calendar-time CAGR; no annual volatility inferred from irregular dates."""
    _dates(curve.index)
    if not np.isfinite(curve.to_numpy(dtype=float)).all() or (curve <= 0).any():
        raise ValueError("Courbe invalide.")
    years = (curve.index[-1] - curve.index[0]).days / 365.25
    total = float(curve.iloc[-1] / curve.iloc[0] - 1)
    return {"total_return": total, "cagr": (1 + total) ** (1 / years) - 1,
            "max_drawdown": float((curve / curve.cummax() - 1).min())}


def periodic_sharpe(returns, risk_free_returns):
    """Sharpe (1994): mean differential return / sample standard deviation.

    Same periodicity and aligned observations required; no silent zero risk-free
    rate and no automatic square-root annualization assumption.
    """
    if not returns.index.equals(risk_free_returns.index) or len(returns) < 2 or not returns.index.is_unique:
        raise ValueError("Rendements et taux sans risque doivent être alignés.")
    if not np.isfinite(returns.to_numpy(dtype=float)).all() or not np.isfinite(risk_free_returns.to_numpy(dtype=float)).all():
        raise ValueError("Rendements manquants ou non finis.")
    if (returns < -1).any() or (risk_free_returns < -1).any():
        raise ValueError("Rendements simples inférieurs à -100 %.")
    differential = returns - risk_free_returns
    std = float(differential.std(ddof=1))
    return None if std == 0 else float(differential.mean() / std)
