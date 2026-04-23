"""
Portfolio optimization algorithms.

Implements:
  1. Mean-Variance Optimization (Markowitz)        — max_sharpe / min_variance
  2. Equal Risk Contribution (Risk Parity)         — erc
  3. Hierarchical Risk Parity (Lopez de Prado 2016)— hrp
  4. Black-Litterman (He & Litterman 1999)         — black_litterman
  5. Utilities: port_stats, risk_contributions, monte_carlo, efficient_frontier
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, LinearConstraint
from scipy.cluster import hierarchy as sch
from scipy.spatial.distance import squareform


# ─────────────────────────────────────────────────────────────────────────────
# 0. Core statistics
# ─────────────────────────────────────────────────────────────────────────────

def port_stats(w: np.ndarray, mu: np.ndarray, Sigma: np.ndarray,
               rf: float = 0.0) -> tuple:
    """
    (annualised return, annualised vol, Sharpe ratio)
    mu and Sigma are daily; annualisation uses sqrt(252) / *252.
    """
    w   = np.asarray(w, dtype=float)
    ret = float(w @ mu) * 252
    vol = float(np.sqrt(np.maximum(w @ Sigma @ w * 252, 0.0)))
    sh  = (ret - rf) / vol if vol > 1e-10 else 0.0
    return ret, vol, sh


def risk_contributions(w: np.ndarray, Sigma: np.ndarray) -> np.ndarray:
    """
    Percentage marginal risk contributions (sum = 1).
    RC_i = w_i * (Sigma @ w)_i / sigma_p
    """
    sigma_p = np.sqrt(np.maximum(w @ Sigma @ w, 0.0))
    if sigma_p < 1e-10:
        return np.ones(len(w)) / len(w)
    mrc = Sigma @ w / sigma_p          # marginal risk contributions
    rc  = w * mrc                      # absolute risk contributions
    return rc / rc.sum()               # normalise


# ─────────────────────────────────────────────────────────────────────────────
# 1. Mean-Variance Optimization
# ─────────────────────────────────────────────────────────────────────────────

def _solve(objective, n: int, long_only: bool = True,
           max_weight: float = 1.0, extra_constraints: list = None) -> np.ndarray:
    bounds = [(0.0, max_weight)] * n if long_only else [(-0.30, max_weight)] * n
    cons   = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    if extra_constraints:
        cons += extra_constraints

    best = None
    rng  = np.random.default_rng(42)
    for _ in range(8):                 # multiple starts for robustness
        x0 = rng.dirichlet(np.ones(n))
        res = minimize(objective, x0, method="SLSQP", bounds=bounds,
                       constraints=cons,
                       options={"ftol": 1e-13, "maxiter": 2000})
        if best is None or res.fun < best.fun:
            best = res
    return best.x


def max_sharpe(mu: np.ndarray, Sigma: np.ndarray, rf: float, n: int,
               long_only: bool = True, max_weight: float = 1.0) -> np.ndarray:
    """Maximum Sharpe Ratio portfolio (tangency portfolio)."""
    def neg_sh(w):
        r, v, s = port_stats(w, mu, Sigma, rf)
        return -s if v > 1e-10 else 0.0
    return _solve(neg_sh, n, long_only, max_weight)


def min_variance(Sigma: np.ndarray, n: int,
                 long_only: bool = True, max_weight: float = 1.0) -> np.ndarray:
    """Global Minimum Variance portfolio."""
    def port_var(w):
        return float(w @ Sigma @ w)
    return _solve(port_var, n, long_only, max_weight)


def max_return_for_vol(mu: np.ndarray, Sigma: np.ndarray,
                       target_vol: float, n: int) -> np.ndarray:
    """Maximise return subject to a volatility ceiling."""
    def neg_ret(w):
        return -float(w @ mu) * 252
    extra = [{"type": "ineq",
              "fun": lambda w: target_vol ** 2 - w @ Sigma @ w * 252}]
    return _solve(neg_ret, n, extra_constraints=extra)


def min_variance_for_return(mu: np.ndarray, Sigma: np.ndarray,
                             target_ret: float, n: int) -> np.ndarray:
    """Minimise variance subject to a minimum return floor (for frontier)."""
    def port_var(w):
        return float(w @ Sigma @ w)
    extra = [{"type": "ineq",
              "fun": lambda w: float(w @ mu) * 252 - target_ret}]
    return _solve(port_var, n, extra_constraints=extra)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Efficient Frontier & Monte Carlo
# ─────────────────────────────────────────────────────────────────────────────

def monte_carlo(mu: np.ndarray, Sigma: np.ndarray, rf: float,
                n: int, n_sim: int = 6000) -> dict:
    """Random portfolios for frontier scatter plot."""
    rng = np.random.default_rng(0)
    rets = np.empty(n_sim)
    vols = np.empty(n_sim)
    shs  = np.empty(n_sim)
    W    = np.empty((n_sim, n))
    for i in range(n_sim):
        w = rng.dirichlet(np.ones(n))
        r, v, s = port_stats(w, mu, Sigma, rf)
        rets[i], vols[i], shs[i] = r, v, s
        W[i] = w
    return {"rets": rets, "vols": vols, "sharpes": shs, "weights": W}


def efficient_frontier(mu: np.ndarray, Sigma: np.ndarray,
                       n: int, n_pts: int = 50) -> tuple:
    """
    Computed efficient frontier (min variance for increasing target returns).
    Returns (vols, rets) arrays.
    """
    mu_min = float(min_variance(Sigma, n) @ mu) * 252
    mu_max = float(mu.max()) * 252 * 0.95
    targets = np.linspace(mu_min, mu_max, n_pts)

    eff_vols = []
    eff_rets = []
    for t in targets:
        try:
            w = min_variance_for_return(mu, Sigma, t, n)
            _, v, _ = port_stats(w, mu, Sigma)
            eff_vols.append(v)
            eff_rets.append(t)
        except Exception:
            continue
    return np.array(eff_vols), np.array(eff_rets)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Equal Risk Contribution (Risk Parity)
# ─────────────────────────────────────────────────────────────────────────────

def erc(Sigma: np.ndarray, n: int) -> np.ndarray:
    """
    Equal Risk Contribution (Maillard, Roncalli, Teiletche 2010).
    Minimises sum of squared differences between each asset's RC and 1/N.
    """
    def objective(w):
        sigma_p = np.sqrt(np.maximum(w @ Sigma @ w, 0.0))
        if sigma_p < 1e-10:
            return 1e10
        mrc = Sigma @ w / sigma_p
        rc  = w * mrc
        budget = sigma_p / n
        return float(np.sum((rc - budget) ** 2))

    best = None
    rng  = np.random.default_rng(0)
    for _ in range(5):
        x0  = rng.dirichlet(np.ones(n))
        res = minimize(objective, x0, method="SLSQP",
                       bounds=[(1e-4, 1.0)] * n,
                       constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                       options={"ftol": 1e-14, "maxiter": 3000})
        if best is None or res.fun < best.fun:
            best = res
    w = np.maximum(best.x, 0)
    return w / w.sum()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Hierarchical Risk Parity (Lopez de Prado, 2016)
# ─────────────────────────────────────────────────────────────────────────────

def _corr_to_dist(corr: np.ndarray) -> np.ndarray:
    """Correlation → distance matrix used for clustering."""
    return np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, 1.0))


def _cluster_variance(Sigma: np.ndarray, idx: list) -> float:
    """Variance of optimal (min-var) sub-portfolio for a cluster."""
    sub = Sigma[np.ix_(idx, idx)]
    w   = min_variance(sub, len(idx))
    return float(w @ sub @ w)


def _recursive_bisect(Sigma: np.ndarray, ordered: list) -> np.ndarray:
    """
    Recursive bisection: allocate weights by splitting the ordered list
    into two halves and weighting inversely by cluster variance.
    """
    w     = pd.Series(1.0, index=ordered)
    items = [ordered]

    while items:
        next_items = []
        for block in items:
            if len(block) <= 1:
                continue
            mid     = len(block) // 2
            left    = block[:mid]
            right   = block[mid:]
            var_l   = _cluster_variance(Sigma, left)
            var_r   = _cluster_variance(Sigma, right)
            alpha   = 1.0 - var_l / (var_l + var_r)   # share to left
            w[left]  *= alpha
            w[right] *= (1.0 - alpha)
            next_items += [left, right]
        items = [b for b in next_items if len(b) > 1]

    return w.values


def hrp(Sigma: np.ndarray, n: int, returns: pd.DataFrame = None) -> tuple:
    """
    Hierarchical Risk Parity.
    If `returns` DataFrame is supplied its correlation is used;
    otherwise the correlation implied by Sigma.

    Returns (weights, linkage_matrix, ordered_labels).
    """
    # Correlation
    if returns is not None:
        corr = returns.corr().values
        labels = list(returns.columns)
    else:
        std  = np.sqrt(np.diag(Sigma))
        corr = Sigma / np.outer(std, std)
        corr = np.clip(corr, -1, 1)
        labels = list(range(n))

    dist      = _corr_to_dist(corr)
    condensed = squareform(dist, checks=False)
    link      = sch.linkage(condensed, method="single")
    order     = sch.leaves_list(link).tolist()   # ordered leaf indices

    w = _recursive_bisect(Sigma, order)
    # Re-map indices back to original order
    weights = np.zeros(n)
    for pos, idx in enumerate(order):
        weights[idx] = w[pos]
    weights = np.maximum(weights, 0)
    weights /= weights.sum()

    ordered_labels = [labels[i] for i in order]
    return weights, link, ordered_labels


# ─────────────────────────────────────────────────────────────────────────────
# 5. Black-Litterman (He & Litterman, 1999)
# ─────────────────────────────────────────────────────────────────────────────

def black_litterman(
    Sigma:      np.ndarray,
    w_mkt:      np.ndarray,   # market cap (or reference) weights
    views_mu:   np.ndarray,   # K absolute views on annualised returns
    views_idx:  list,         # which asset each view refers to (len K)
    rf:         float = 0.04,
    tau:        float = 0.05,
    delta:      float = 2.5,
    view_conf:  float = 0.5,  # uniform view confidence (0–1)
) -> tuple:
    """
    Black-Litterman posterior returns and covariance.

    Only supports absolute views (P = one-hot).
    Returns (BL_mu_ann, BL_Sigma, Pi_ann).
    """
    n = len(w_mkt)
    K = len(views_mu)

    # Equilibrium (implied) excess returns (annualised)
    Pi = delta * (Sigma * 252) @ w_mkt     # already annualised

    if K == 0:
        return Pi + rf, Sigma * 252, Pi

    # Views matrix P (K × N), absolute views → identity rows
    P = np.zeros((K, n))
    for k, idx in enumerate(views_idx):
        P[k, idx] = 1.0

    Q = np.array(views_mu, dtype=float)   # annualised excess returns

    # Uncertainty diagonal: omega proportional to tau * P Σ P'
    tauS   = tau * Sigma * 252
    omega  = np.diag(np.diag(P @ tauS @ P.T) / view_conf)

    # Posterior
    M_inv   = np.linalg.inv(tauS)
    PtOinv  = P.T @ np.linalg.inv(omega)
    M_post  = np.linalg.inv(M_inv + PtOinv @ P)
    BL_mu   = M_post @ (M_inv @ Pi + PtOinv @ Q)   # annualised excess
    BL_Sigma = Sigma * 252 + M_post                 # posterior total cov

    return BL_mu + rf, BL_Sigma, Pi + rf


# ─────────────────────────────────────────────────────────────────────────────
# 6. Maximum Diversification Portfolio
# ─────────────────────────────────────────────────────────────────────────────

def max_diversification(Sigma: np.ndarray, n: int) -> np.ndarray:
    """
    Maximise diversification ratio = (w · σ_i) / σ_p.
    Chovelard et al. (2008).
    """
    sigmas = np.sqrt(np.diag(Sigma))

    def neg_dr(w):
        sigma_p = np.sqrt(np.maximum(w @ Sigma @ w, 0.0))
        return -(float(w @ sigmas) / sigma_p) if sigma_p > 1e-10 else 0.0

    return _solve(neg_dr, n)
