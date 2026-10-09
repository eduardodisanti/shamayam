"""
The minimum commissioning length [cor:min_commissioning] and the degenerate
range [cor:degenerate_range], verified over grids of alpha and n rather than at
the single configuration used in the paper.
"""

import numpy as np
import pytest

from mssp_repro import (certified_order_statistic, degenerate_range,
                        is_degenerate_maximum, is_feasible, k_alpha,
                        minimum_commissioning_length)

ALPHAS = [0.005, 0.01, 0.02, 0.025, 0.05, 0.10, 0.20, 0.25]


@pytest.mark.parametrize("alpha", ALPHAS)
def test_feasibility_matches_the_closed_form(alpha):
    """k_alpha <= n  <=>  n >= 1/alpha - 1, exactly, with no off-by-one."""
    n_min = minimum_commissioning_length(alpha)
    for n in range(2, 4 * n_min + 40):
        assert is_feasible(n, alpha) == (n >= n_min), (alpha, n, n_min)


@pytest.mark.parametrize("alpha", ALPHAS)
def test_minimum_length_is_tight(alpha):
    """n_min feasible, n_min - 1 infeasible: the bound is attained."""
    n_min = minimum_commissioning_length(alpha)
    assert is_feasible(n_min, alpha)
    assert not is_feasible(n_min - 1, alpha)


def test_minimum_length_at_the_papers_configuration():
    """The value quoted throughout the paper."""
    assert minimum_commissioning_length(0.02) == 49
    assert k_alpha(49, 0.02) == 49


@pytest.mark.parametrize("alpha", ALPHAS)
def test_degenerate_range_matches_the_closed_form(alpha):
    """
    The degenerate-range corollary [cor:degenerate_range]: k_alpha == n  <=>  1/alpha - 1 <= n < 2/alpha - 1.
    Checked against the inequality directly, over a grid wider than the range.
    """
    lo, hi = degenerate_range(alpha)
    for n in range(2, 4 * hi + 40):
        expected = (1.0 / alpha - 1.0 <= n) and (n < 2.0 / alpha - 1.0)
        assert is_degenerate_maximum(n, alpha) == expected, (alpha, n)
        assert (lo <= n <= hi) == expected, (alpha, n, lo, hi)


def test_degenerate_range_at_the_papers_configuration():
    """At alpha=0.02 the radius is the sample maximum for n in [49, 98]."""
    assert degenerate_range(0.02) == (49, 98)
    assert is_degenerate_maximum(98, 0.02)
    assert not is_degenerate_maximum(99, 0.02)
    assert k_alpha(99, 0.02) == 98          # first interior order statistic


@pytest.mark.parametrize("alpha", ALPHAS)
def test_in_the_degenerate_range_the_radius_is_the_sample_maximum(alpha):
    """Behavioural counterpart: the estimator really does return max(r)."""
    rng = np.random.default_rng(7)
    lo, hi = degenerate_range(alpha)
    for n in {lo, (lo + hi) // 2, hi}:
        sample = rng.lognormal(0.0, 0.5, n)
        assert certified_order_statistic(sample, alpha=alpha) == \
            pytest.approx(sample.max(), abs=1e-12)


@pytest.mark.parametrize("alpha", ALPHAS)
def test_just_above_the_degenerate_range_the_radius_is_interior(alpha):
    """And immediately above it, it is strictly below the maximum."""
    rng = np.random.default_rng(11)
    _, hi = degenerate_range(alpha)
    n = hi + 1
    sample = rng.lognormal(0.0, 0.5, n)
    tau = certified_order_statistic(sample, alpha=alpha)
    assert tau < sample.max()
    assert k_alpha(n, alpha) == n - 1


def test_variance_drops_on_leaving_the_degenerate_range():
    """
    The practical claim of the degenerate-range corollary [cor:degenerate_range] as stated in the paper: sd(tau) is
    roughly flat inside the degenerate band and falls substantially once an
    interior order statistic is used. Verified at alpha=0.02.
    """
    alpha = 0.02
    rng = np.random.default_rng(3)
    reps = 4000

    def sd_at(n):
        return float(np.std([
            certified_order_statistic(rng.lognormal(0.0, 0.4, n), alpha=alpha)
            for _ in range(reps)
        ]))

    sd_49, sd_98, sd_200 = sd_at(49), sd_at(98), sd_at(200)
    # flat within the band (within 25%), and materially lower outside it
    assert 0.75 < sd_49 / sd_98 < 1.25, (sd_49, sd_98)
    assert sd_200 < 0.6 * sd_98, (sd_200, sd_98)


@pytest.mark.parametrize("alpha", ALPHAS)
def test_estimator_returns_nan_below_the_floor(alpha):
    """An uncertifiable radius must not be silently produced."""
    rng = np.random.default_rng(5)
    n = minimum_commissioning_length(alpha) - 1
    if n >= 2:
        assert np.isnan(certified_order_statistic(rng.random(n), alpha=alpha))
