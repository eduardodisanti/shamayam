"""
The stopping rule, and the confound flagged in Section 9 of the paper.

The published commissioning lengths cluster at 49, and the the commissioning-floor corollary [cor:min_commissioning]
coverage floor at alpha=0.02 is also 49. These tests establish that the two
numbers arise from unrelated mechanisms, so the observed clustering carries no
evidence about the coverage floor.
"""

import numpy as np
import pytest

from mssp_repro import (AdaptiveOperationalRadius, MAX_CALIBRATION_SIZE,
                        MIN_WARMUP_SAMPLES, certified_order_statistic,
                        find_convergence_index, interpolated_quantile,
                        make_distributions, minimum_commissioning_length,
                        stopping_rule_floor)


def test_stopping_floor_closed_form():
    """
    Earliest emittable calibration size is
        max(N_min - 1, min_samples - 1 + lookback) + consecutive.
    The second term binds when N_min is small, because C_k(t) is undefined
    until both tau(t) and tau(t - lookback) are finite.
    """
    assert stopping_rule_floor(40, 10, 20, 10) == 49      # published config
    assert stopping_rule_floor(25, 10, 20, 10) == 39      # warm-up binds
    for min_cal in (10, 25, 40, 60):
        for consec in (3, 5, 10, 20):
            expected = max(min_cal - 1, 20 - 1 + 10) + consec
            assert stopping_rule_floor(min_cal, consec, 20, 10) == expected


def test_which_constraint_binds():
    """The crossover is at N_min = min_samples + lookback."""
    assert stopping_rule_floor(30, 10, 20, 10) == 39      # tie
    assert stopping_rule_floor(31, 10, 20, 10) == 40      # N_min binds
    assert stopping_rule_floor(29, 10, 20, 10) == 39      # warm-up binds


def test_stopping_floor_is_independent_of_alpha():
    """
    The crux of the confound: the stopping floor is combinatorial and does not
    involve alpha at all, whereas the coverage floor is 1/alpha - 1.
    """
    floor = stopping_rule_floor(40, 10, 20, 10)
    coverage_floors = {a: minimum_commissioning_length(a)
                       for a in (0.005, 0.01, 0.02, 0.05, 0.10)}
    assert floor == 49
    assert coverage_floors[0.02] == 49                 # they coincide here
    assert len({v for v in coverage_floors.values()}) == len(coverage_floors)
    for a, cf in coverage_floors.items():
        if a != 0.02:
            assert cf != floor, (a, cf)                # and nowhere else


@pytest.mark.parametrize("min_cal,consec", [(40, 10), (40, 5), (25, 10),
                                            (60, 10), (40, 20)])
def test_observed_minimum_equals_the_predicted_floor(min_cal, consec):
    """
    Empirically, across heterogeneous residual streams, the smallest
    calibration size the rule ever emits equals the predicted floor exactly,
    and it moves when the stopping parameters move.
    """
    rng = np.random.default_rng(0)
    dists = make_distributions(rng)
    observed_min = np.inf
    for gen in dists.values():
        for _ in range(120):
            stream = gen(MAX_CALIBRATION_SIZE)
            trace = AdaptiveOperationalRadius(
                interpolated_quantile,
                window_size=MAX_CALIBRATION_SIZE,
                min_samples=MIN_WARMUP_SAMPLES,
            ).warmup_trace(stream)
            idx = find_convergence_index(trace, lookback=10, tolerance=0.01,
                                         consecutive=consec,
                                         min_index=min_cal - 1)
            if idx is not None:
                observed_min = min(observed_min, idx + 1)
    assert observed_min == stopping_rule_floor(min_cal, consec,
                                               MIN_WARMUP_SAMPLES, 10)


def test_clustering_tracks_the_stopping_floor_not_the_coverage_floor():
    """
    The control proposed in Section 9. Halving `consecutive` moves the
    stopping floor from 49 to 44 while leaving alpha untouched. If the
    clustering were a signature of the coverage floor it would not move.
    """
    rng = np.random.default_rng(1)
    dists = make_distributions(rng)

    def min_size(consec):
        m = np.inf
        for gen in dists.values():
            for _ in range(120):
                trace = AdaptiveOperationalRadius(
                    interpolated_quantile,
                    window_size=MAX_CALIBRATION_SIZE,
                    min_samples=MIN_WARMUP_SAMPLES,
                ).warmup_trace(gen(MAX_CALIBRATION_SIZE))
                idx = find_convergence_index(trace, lookback=10,
                                             tolerance=0.01,
                                             consecutive=consec,
                                             min_index=39)
                if idx is not None:
                    m = min(m, idx + 1)
        return m

    assert min_size(10) == 49
    assert min_size(5) == 44        # moved with the stopping rule, not alpha


def test_certified_estimator_cannot_emit_below_the_coverage_floor():
    """
    Regardless of stopping parameters, the certified estimator yields NaN
    below n = 49, so no asset can be released with an uncertifiable radius
    even if the stopping rule would have permitted it.
    """
    rng = np.random.default_rng(2)
    trace = AdaptiveOperationalRadius(
        certified_order_statistic, window_size=MAX_CALIBRATION_SIZE,
        min_samples=MIN_WARMUP_SAMPLES,
    ).warmup_trace(rng.lognormal(0.0, 0.4, MAX_CALIBRATION_SIZE))

    # a permissive rule that would otherwise converge very early
    idx = find_convergence_index(trace, lookback=5, tolerance=1.0,
                                 consecutive=2, min_index=10)
    assert idx is None or (idx + 1) >= minimum_commissioning_length(0.02)


def test_non_convergence_is_reported_rather_than_guessed():
    """A stream that never stabilises must yield None, not a fallback value."""
    n = MAX_CALIBRATION_SIZE
    # monotonically exploding stream: the upper quantile never settles
    stream = np.exp(np.linspace(0.0, 12.0, n))
    trace = AdaptiveOperationalRadius(
        interpolated_quantile, window_size=n, min_samples=MIN_WARMUP_SAMPLES
    ).warmup_trace(stream)
    assert find_convergence_index(trace, lookback=10, tolerance=0.01,
                                  consecutive=10, min_index=39) is None
