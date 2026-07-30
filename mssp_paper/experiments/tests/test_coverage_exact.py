"""
The coverage proposition [prop:coverage], checked exactly rather than statistically.

The coverage claim P(r_{n+1} <= r_(k_alpha)) = k_alpha/(n+1) follows from the
rank of r_{n+1} being uniform on {1,...,n+1} under exchangeability. For small
n that probability can be computed by exhaustive enumeration of all orderings
of n+1 distinct values, with no sampling involved. These tests therefore
verify the proposition itself, not a Monte Carlo approximation of it.
"""

import itertools
from math import erf, factorial, log, sqrt

import numpy as np
import pytest

from mssp_repro import (certified_order_statistic, exact_coverage, k_alpha,
                        coverage_band, is_feasible)


@pytest.mark.parametrize("n", [4, 5, 6, 7])
@pytest.mark.parametrize("alpha", [0.5, 0.4, 0.3, 0.25, 0.2])
def test_coverage_by_exhaustive_enumeration(n, alpha):
    """
    Enumerate every ordering of n+1 distinct exchangeable values and count how
    often the last one falls at or below the k_alpha-th order statistic of the
    first n. The exact frequency must equal k_alpha/(n+1).
    """
    if not is_feasible(n, alpha):
        pytest.skip("infeasible by the commissioning-floor corollary [cor:min_commissioning]")

    k = k_alpha(n, alpha)
    values = list(range(n + 1))          # distinct: no ties, as assumed

    hits = 0
    total = 0
    for perm in itertools.permutations(values):
        cal = np.array(perm[:n], dtype=np.float64)
        future = float(perm[n])
        tau = np.sort(cal)[k - 1]
        hits += int(future <= tau)
        total += 1

    assert total == factorial(n + 1)
    assert hits / total == pytest.approx(k / (n + 1.0), abs=1e-12)
    assert hits / total == pytest.approx(exact_coverage(n, alpha), abs=1e-12)


@pytest.mark.parametrize("alpha", [0.01, 0.02, 0.05, 0.10, 0.20])
def test_exact_coverage_lies_in_the_stated_band(alpha):
    """The equality k_alpha/(n+1) must sit inside [1-a, 1-a+1/(n+1)]."""
    for n in range(2, 400):
        if not is_feasible(n, alpha):
            continue
        cov = exact_coverage(n, alpha)
        lo, hi = coverage_band(n, alpha)
        assert lo - 1e-12 <= cov <= hi + 1e-12, (n, alpha, cov, lo, hi)


@pytest.mark.parametrize("alpha", [0.01, 0.02, 0.05, 0.10])
def test_coverage_never_falls_below_target(alpha):
    """The guarantee is one-sided: coverage must never undershoot 1-alpha."""
    for n in range(2, 400):
        if is_feasible(n, alpha):
            assert exact_coverage(n, alpha) >= 1.0 - alpha - 1e-12


def test_rank_uniformity_under_exchangeability():
    """
    The mechanism behind the coverage proposition [prop:coverage]: under exchangeability the rank of the
    future residual is uniform on {1,...,n+1}. Checked by enumeration.
    """
    n = 6
    counts = np.zeros(n + 2, dtype=int)
    for perm in itertools.permutations(range(n + 1)):
        future = perm[n]
        rank = 1 + sum(1 for v in perm[:n] if v < future)
        counts[rank] += 1
    occupied = counts[1:n + 2]
    assert occupied.sum() == factorial(n + 1)
    assert len(set(occupied.tolist())) == 1, "ranks are not equiprobable"


def test_monte_carlo_agrees_with_the_exact_value():
    """
    Sanity bridge between the exact result and the simulation used to produce
    the paper's tables, on a distribution for which nothing is Gaussian.
    """
    rng = np.random.default_rng(12345)
    n, alpha, reps = 50, 0.02, 40000
    tau_covs = np.empty(reps)
    for i in range(reps):
        cal = rng.lognormal(0.0, 0.4, n)
        tau = certified_order_statistic(cal, alpha=alpha)
        # exact conditional coverage via the lognormal CDF, no eval sampling
        tau_covs[i] = 0.5 * (1.0 + erf(log(tau) / (0.4 * sqrt(2.0))))
    predicted = exact_coverage(n, alpha)
    se = tau_covs.std(ddof=1) / np.sqrt(reps)
    assert abs(tau_covs.mean() - predicted) < 5.0 * se
