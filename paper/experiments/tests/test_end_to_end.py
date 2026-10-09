"""
End-to-end Layer-A pipeline on the vendored bearing simulator:

    simulator -> nominal-only representation operator -> residuals
              -> certified radius -> membership decision

This exercises the full chain of Section 7 without TensorFlow and without any
downloaded dataset, and checks the qualitative predictions the theory makes
about it: nominal residuals concentrate, fault residuals do not, the radius is
asset-specific, and detection follows from a single membership test.
"""

import numpy as np
import pytest

from mssp_repro import (PCAResidualOperator, certified_order_statistic,
                        minimum_commissioning_length)
from mssp_repro.bearing_simulator import CWRU_PARAMS, BearingSignalSimulator

ALPHA = 0.02
N_TRAIN = 600
N_EVAL = 400


def _windows(sim, regime, n, seed, asset_signature=None):
    np.random.seed(seed)                 # simulator uses the legacy global RNG
    return np.stack([
        sim.sample(regime=regime, asset_signature=asset_signature)
        for _ in range(n)
    ])


@pytest.fixture(scope="module")
def fitted():
    sim = BearingSignalSimulator(CWRU_PARAMS)
    X_nominal = _windows(sim, "healthy", N_TRAIN, seed=0)
    op = PCAResidualOperator(n_components=16).fit(X_nominal)
    return sim, op


def test_operator_is_deterministic(fitted):
    """Layer A must be exactly reproducible, not merely statistically stable."""
    sim, op = fitted
    X = _windows(sim, "healthy", 32, seed=123)
    assert np.array_equal(op.residual(X), op.residual(X))


def test_nominal_residuals_are_far_below_fault_residuals(fitted):
    """
    The residual-proxy assumption [ass:residual_proxy] evaluated empirically: the residual behaves as a proxy for
    distance to the nominal structure, with no fault sample used in fitting.
    """
    sim, op = fitted
    r_healthy = op.residual(_windows(sim, "healthy", N_EVAL, seed=1))
    for regime in ("outer_race", "inner_race", "ball_fault"):
        r_fault = op.residual(_windows(sim, regime, N_EVAL, seed=2))
        assert np.median(r_fault) > np.median(r_healthy)


def test_certified_radius_attains_near_nominal_false_alarm_rate(fitted):
    """
    The operative claim of the coverage proposition [prop:coverage] on simulator residuals: calibrate on
    nominal windows, evaluate on disjoint nominal windows, and the false-alarm
    rate should sit near alpha rather than far above it.
    """
    sim, op = fitted
    r_cal = op.residual(_windows(sim, "healthy", 120, seed=3))
    r_eval = op.residual(_windows(sim, "healthy", 1500, seed=4))
    tau = certified_order_statistic(r_cal, ALPHA)
    far = float(np.mean(r_eval > tau))
    assert far < 3.0 * ALPHA, far


def test_detection_follows_from_the_single_membership_test(fitted):
    """
    One radius, no fault labels, no per-fault tuning: every fault family must
    be detected by the same rule r > tau.
    """
    sim, op = fitted
    r_cal = op.residual(_windows(sim, "healthy", 120, seed=5))
    tau = certified_order_statistic(r_cal, ALPHA)
    for regime in ("outer_race", "inner_race", "ball_fault"):
        r_fault = op.residual(_windows(sim, regime, N_EVAL, seed=6))
        assert float(np.mean(r_fault > tau)) > 0.5, regime


def test_radius_is_asset_specific_under_a_shared_operator(fitted):
    """
    The residual-scale remark [rem:scale_not_invariant] and the equivalence-class
    corollary [cor:equivalence_class_diagnosis], in behavioural form: distinct simulated assets,
    differing only by an installation signature, share the operator but
    identify materially different radii.
    """
    sim, op = fitted
    rng = np.random.default_rng(0)
    taus = []
    for a in range(4):
        signature = rng.uniform(0.8, 1.2, 5)
        r = op.residual(_windows(sim, "healthy", 120, seed=100 + a,
                                 asset_signature=signature))
        taus.append(certified_order_statistic(r, ALPHA))
    taus = np.array(taus)
    assert np.all(np.isfinite(taus))
    assert taus.max() / taus.min() > 1.2, taus


def test_pipeline_respects_the_commissioning_floor(fitted):
    """Below the commissioning floor [cor:min_commissioning] no radius is produced."""
    sim, op = fitted
    n = minimum_commissioning_length(ALPHA) - 1
    r = op.residual(_windows(sim, "healthy", n, seed=7))
    assert np.isnan(certified_order_statistic(r, ALPHA))


def test_operator_rejects_dimension_mismatch(fitted):
    sim, op = fitted
    with pytest.raises(ValueError):
        op.residual(np.zeros((4, 17)))
