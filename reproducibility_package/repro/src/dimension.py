"""
Intrinsic dimension from covering numbers — a DECLARED protocol.

Why this file exists
--------------------
The first version of this measurement reported 1.36 for handwritten digits.
Re-running it with a different epsilon grid gave 1.98. Nothing was wrong with
either run: the fitted slope of log|S| against log(1/eps) depends on the range
of eps you fit over, and neither range had been declared. A number a reviewer
can move by choosing the grid is not a measurement. This module fixes every
choice, in the open, and calibrates the estimator against manifolds whose
dimension is known.

The protocol
------------
1.  METRIC.  The dimension is fitted against the ANGULAR metric
        theta = arccos(1 - d_cos),
    not against the cosine distance itself.

    This is not cosmetic. Near zero, cosine distance is QUADRATIC in angle
    (1 - cos t ~ t^2 / 2), so a cosine ball of radius eps is an angular ball of
    radius ~sqrt(2 eps). Fitting against eps therefore reports HALF the true
    dimension. The net is untouched -- a cosine ball of radius eps IS an angular
    ball of radius theta(eps), the same points, the same S -- only the abscissa
    of the fit changes.

2.  GRID.  12 points, log-uniform in eps, between the 1st and the 90th
    percentile of the within-set distance distribution. Data-derived, never
    guessed.

3.  ADMISSIBLE WINDOW.  Fit only where  4 <= |S(eps)| <= n/4.
    Below 4 the net has collapsed to a handful of points and the slope is
    dominated by rounding; above n/4 the net is running out of DATA, not of
    geometry, and the slope is biased down. Fewer than 4 admissible points
    means the sample cannot support the estimate: report NA, not a number.

4.  AVERAGING.  |S(eps)| is the mean over `orders` arrival orders of the greedy
    net, so the estimate does not depend on the order the samples arrived in.

5.  FIT.  Ordinary least squares of log|S| on log(1/theta), reported with its
    standard error and the number of admissible points. n is always stated.

Calibration
-----------
`calibrate()` runs the identical protocol on uniform samples from spheres
S^d embedded in R^64, at a matched sample size. The estimator recovers d = 1
essentially exactly and is increasingly conservative above it: the covering
number of a d-dimensional set grows like theta^-d, so at fixed n the admissible
window shrinks as d grows and the fit is pulled down. Report the number as a
LOWER BOUND on the dimension, with the calibration alongside it.
"""
from __future__ import annotations

import numpy as np

from run_experiment import l2_normalise, net_sizes_over_eps

N_GRID_POINTS = 12
PCTL_LO, PCTL_HI = 1.0, 90.0
MIN_SIZE = 4
CAP_FRAC = 0.25
MIN_POINTS = 4


def angle(eps):
    """Cosine distance -> angular (geodesic) distance on the unit sphere."""
    return np.arccos(np.clip(1.0 - np.asarray(eps, float), -1.0, 1.0))


def within_distances(Xn, rng, max_pairs_from=400):
    m = min(len(Xn), max_pairs_from)
    A = Xn[rng.choice(len(Xn), m, replace=False)] if len(Xn) > m else Xn
    D = 1.0 - A @ A.T
    return D[np.triu_indices(len(A), 1)]


def eps_grid(Xn, seed=0):
    rng = np.random.default_rng(seed)
    w = within_distances(Xn, rng)
    lo, hi = np.percentile(w, [PCTL_LO, PCTL_HI])
    lo = max(float(lo), 1e-6)
    hi = max(float(hi), lo * 10)
    return np.geomspace(lo, hi, N_GRID_POINTS)


def dimension(Xn, orders=5, seed=0, grid=None):
    """Intrinsic dimension of an l2-normalised set, under the declared protocol.

    Returns a dict: dim, stderr, n_points_used, n, eps, sizes, window.
    dim is NaN when the sample cannot support the fit.
    """
    Xn = np.asarray(Xn, float)
    n = len(Xn)
    eps = eps_grid(Xn, seed) if grid is None else np.asarray(grid, float)
    sizes = net_sizes_over_eps(Xn, eps, orders, seed).mean(1)

    m = (sizes >= MIN_SIZE) & (sizes <= CAP_FRAC * n)
    out = {"n": int(n), "eps": eps.tolist(), "sizes": sizes.tolist(),
           "window": [MIN_SIZE, CAP_FRAC * n], "n_points_used": int(m.sum())}
    if m.sum() < MIN_POINTS:
        out.update(dim=float("nan"), stderr=float("nan"))
        return out

    x = np.log(1.0 / angle(eps[m]))
    y = np.log(sizes[m])
    k = m.sum()
    b, a = np.polyfit(x, y, 1)
    resid = y - (b * x + a)
    sxx = ((x - x.mean()) ** 2).sum()
    se = float(np.sqrt((resid ** 2).sum() / max(k - 2, 1) / sxx)) if sxx > 0 else float("nan")
    out.update(dim=float(b), stderr=se)
    return out


def calibrate(n, dims=(1, 2, 3, 4), ambient=64, orders=5, seed=0):
    """Same protocol on uniform samples from S^d, d known. n matched to the data."""
    res = {}
    for d in dims:
        rng = np.random.default_rng(seed)
        k = d + 1                                   # S^d lives in a (d+1)-dim span
        X = l2_normalise(rng.standard_normal((n, k)) @ rng.standard_normal((k, ambient)))
        r = dimension(X, orders=orders, seed=seed)
        res[d] = {"estimate": r["dim"], "stderr": r["stderr"],
                  "n_points_used": r["n_points_used"]}
    return res
