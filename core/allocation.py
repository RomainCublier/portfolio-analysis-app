"""Long-only allocation diagnostics. Limits are user policy, not finance laws."""
from dataclasses import dataclass
from datetime import date
import math
import numpy as np
import pandas as pd


def weights_valid(weights):
    if not weights or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in weights.values()):
        raise ValueError("Poids finis compris entre 0 et 100 % requis.")
    if not math.isclose(sum(weights.values()), 1, abs_tol=1e-10, rel_tol=0):
        raise ValueError("L’allocation doit totaliser 100 %.")


@dataclass(frozen=True)
class HoldingsSnapshot:
    as_of: date
    source_url: str
    issuer_weights: dict[str, float]  # Disjoint issuer buckets; partial coverage allowed.


def allocation_diagnostics(weights, kinds, snapshots, as_of, limits=None, max_age_days=35):
    """Known look-through exposure is a lower bound when holdings are incomplete.

    snapshots are validated upstream, issuer IDs must be consolidated across funds.
    Long-only economic allocations only: leveraged/short/derivative funds require
    a separate exposure model and must not be mapped using this simple kernel.
    """
    weights_valid(weights)
    if set(weights) != set(kinds) or not set(snapshots).issubset(weights):
        raise ValueError("Supports, types et compositions incompatibles.")
    if any(k not in {"ETF", "Fonds", "Action", "Liquidités"} for k in kinds.values()):
        raise ValueError("Type de support non reconnu.")
    if not isinstance(max_age_days, int) or max_age_days < 0:
        raise ValueError("Ancienneté maximale invalide.")
    limits = limits or {}
    if set(limits) - {"position", "stock_picking", "issuer"}:
        raise ValueError("Limite inconnue.")
    for value in limits.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Limite invalide.")
    known, covered, stale = {}, 0., []
    for instrument, w in weights.items():
        if not w:
            continue
        snap = snapshots.get(instrument)
        if snap is None:
            continue
        if not snap.source_url.startswith("https://"):
            raise ValueError("Source de composition requise.")
        age = (as_of - snap.as_of).days
        if age < 0 or age > max_age_days:
            stale.append(instrument)
            continue
        exposures = snap.issuer_weights
        if any(not isinstance(k, str) or not k.strip() for k in exposures):
            raise ValueError("Identifiant émetteur invalide.")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in exposures.values()) or sum(exposures.values()) > 1 + 1e-10:
            raise ValueError("Composition long-only invalide ou avec levier.")
        for issuer, fraction in exposures.items():
            known[issuer] = known.get(issuer, 0) + w * fraction
        covered += w * sum(exposures.values())
    unknown = max(0., 1 - covered)
    direct_stocks = sum(w for key, w in weights.items() if kinds[key] == "Action")
    checks = []
    for metric, actual in (("position", max(weights.values())), ("stock_picking", direct_stocks), ("issuer", max(known.values(), default=0))):
        if metric not in limits:
            continue
        cap = limits[metric]
        status = "Dépassée" if actual > cap + 1e-10 else "Indéterminée" if metric == "issuer" and unknown > 1e-10 else "Respectée sur ce critère"
        checks.append({"criterion": metric, "observed": actual, "limit": cap, "status": status})
    return {"by_kind": {kind: sum(w for key, w in weights.items() if kinds[key] == kind) for kind in sorted(set(kinds.values()))},
            "direct_stock_weight": direct_stocks, "known_issuers": known, "unknown_weight": unknown,
            "stale_snapshots": stale, "checks": checks}


def covariance_risk(weights, covariance):
    """Variance w'Σw and Euler volatility contributions w_i(Σw)_i / σ.

    Covariance units/time scale are those supplied by the caller; no inferred
    annualization, shrinkage or expected returns. Contributions may be negative.
    """
    weights_valid(weights)
    if (not isinstance(covariance, pd.DataFrame) or not covariance.index.is_unique
            or not covariance.columns.is_unique or set(covariance.index) != set(weights)
            or set(covariance.columns) != set(weights)):
        raise ValueError("Matrice de covariance non alignée.")
    keys = list(weights)
    matrix = covariance.loc[keys, keys].to_numpy(dtype=float)
    if not np.isfinite(matrix).all() or not np.allclose(matrix, matrix.T, rtol=0, atol=1e-12):
        raise ValueError("Covariance non finie ou non symétrique.")
    if np.linalg.eigvalsh(matrix).min() < -1e-12:
        raise ValueError("Covariance non semi-définie positive.")
    w = np.array([weights[k] for k in keys])
    variance = max(0., float(w @ matrix @ w))
    volatility = math.sqrt(variance)
    contributions = None if volatility == 0 else dict(zip(keys, (w * (matrix @ w) / volatility).tolist()))
    return {"variance": variance, "volatility": volatility, "volatility_contributions": contributions}
