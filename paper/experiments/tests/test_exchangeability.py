"""
The permutation test of the exchangeability assumption [ass:exchangeability]: size under exchangeability, power under
drift.

A test that rejects too often would make the published robustness ablation
look like evidence of a violated assumption when none exists; a test with no
power would make it uninformative. Both directions are checked here before the
test is applied to real commissioning streams.
"""

import numpy as np
import pytest

from mssp_repro import (inject_drift, make_distributions,
                        permutation_exchangeability_test)


def test_size_under_exchangeability_is_at_most_nominal():
    """
    Under H0 the rejection rate at level 0.05 must not exceed 0.05 by more
    than sampling error. Checked across all six residual distributions.
    """
    rng = np.random.default_rng(0)
    dists = make_distributions(rng)
    trials_per_dist = 120
    rejections = 0
    total = 0
    for gen in dists.values():
        for t in range(trials_per_dist):
            res = permutation_exchangeability_test(
                gen(60), n_permutations=400, random_state=t
            )
            rejections += int(res["p_value"] < 0.05)
            total += 1
    rate = rejections / total
    se = np.sqrt(0.05 * 0.95 / total)
    assert rate <= 0.05 + 3.0 * se, (rate, total)


@pytest.mark.parametrize("slope", [1.5, 3.0])
def test_power_against_monotone_drift(slope):
    """
    A drifting commissioning window is the failure mode that voids
    The exchangeability assumption [ass:exchangeability]. The test must detect it with high probability.
    """
    rng = np.random.default_rng(1)
    dists = make_distributions(rng)
    rejections = 0
    total = 0
    for gen in dists.values():
        for t in range(60):
            stream = inject_drift(gen(60), slope=slope)
            res = permutation_exchangeability_test(
                stream, n_permutations=400, random_state=t
            )
            rejections += int(res["p_value"] < 0.05)
            total += 1
    power = rejections / total
    assert power > 0.80, (slope, power)


def test_power_increases_with_drift_magnitude():
    """Monotonicity: a larger violation must be easier to detect."""
    rng = np.random.default_rng(2)
    base = rng.lognormal(0.0, 0.4, 80)

    def rejection_rate(slope):
        hits = 0
        for t in range(80):
            r = np.random.default_rng(1000 + t)
            stream = inject_drift(r.lognormal(0.0, 0.4, 80), slope=slope)
            res = permutation_exchangeability_test(
                stream, n_permutations=300, random_state=t
            )
            hits += int(res["p_value"] < 0.05)
        return hits / 80

    r0, r1, r2 = rejection_rate(0.0), rejection_rate(1.0), rejection_rate(3.0)
    assert r0 <= r1 <= r2
    assert r0 < 0.15 and r2 > 0.80


def test_p_value_is_bounded_away_from_zero_and_never_exceeds_one():
    """Add-one correction: valid for any number of permutations."""
    rng = np.random.default_rng(3)
    for b in (10, 100, 1000):
        res = permutation_exchangeability_test(
            rng.lognormal(0.0, 0.4, 50), n_permutations=b, random_state=0
        )
        assert 1.0 / (1.0 + b) <= res["p_value"] <= 1.0


def test_is_invariant_to_monotone_rescaling_of_the_residual():
    """
    The statistic is rank-based, so the verdict must not depend on the units
    of the residual. This matters because the residual scale is precisely what
    does not transfer between assets (the residual-scale remark [rem:scale_not_invariant]).
    """
    rng = np.random.default_rng(4)
    stream = rng.lognormal(0.0, 0.4, 70)
    a = permutation_exchangeability_test(stream, n_permutations=500,
                                         random_state=0)
    b = permutation_exchangeability_test(17.0 * stream + 3.0,
                                         n_permutations=500, random_state=0)
    assert a["statistic"] == pytest.approx(b["statistic"], abs=1e-12)
    assert a["p_value"] == pytest.approx(b["p_value"], abs=1e-12)


def test_rejects_a_deterministically_sorted_stream():
    """Degenerate extreme: perfectly ordered arrival must be rejected."""
    res = permutation_exchangeability_test(np.sort(np.random.default_rng(5)
                                                  .lognormal(0.0, 0.4, 60)),
                                           n_permutations=500, random_state=0)
    assert res["statistic"] == pytest.approx(1.0, abs=1e-12)
    assert res["p_value"] < 0.01
