"""
The embedding reading [rem:delay_embedding], [rem:nuisance_on_attractor] and
the drift picture [subsec:disc_dynamics].

The dimension prediction is falsifiable in a specific way: the estimator must
TRACK the number of active nuisance parameters. Absolute accuracy is not the
criterion, because the maximum-likelihood estimator is biased downward and
increasingly so with dimension; a wrong reading would fail to track.
"""

import numpy as np
import pytest

from mssp_repro import (PCAResidualOperator, certified_order_statistic,
                        degradation_trajectory, first_persistent_departure,
                        levina_bickel, nominal_family, predicted_dimension)
from mssp_repro.bearing_simulator import CWRU_PARAMS, BearingSignalSimulator

ALPHA = 0.02


# ---------------------------------------------------------------------
# Intrinsic dimension
# ---------------------------------------------------------------------

def test_single_parameter_family_is_one_dimensional():
    """The anchor: with one active parameter the estimate must be near 1."""
    X = nominal_family(1500, seed=0, vary_amplitude=True, vary_phase=False,
                       vary_speed=False, vary_offset=False)
    est = levina_bickel(X, k_values=(10, 20))
    assert 0.85 < est[10] < 1.20, est
    assert 0.85 < est[20] < 1.20, est


@pytest.mark.parametrize("kw,pred", [
    (dict(vary_amplitude=True,  vary_phase=False, vary_speed=False,
          vary_offset=False), 1),
    (dict(vary_amplitude=True,  vary_phase=True,  vary_speed=False,
          vary_offset=False), 2),
    (dict(vary_amplitude=True,  vary_phase=True,  vary_speed=True,
          vary_offset=False), 3),
    (dict(vary_amplitude=True,  vary_phase=True,  vary_speed=True,
          vary_offset=True),  4),
])
def test_estimate_is_close_to_the_predicted_dimension(kw, pred):
    """
    Within the known downward bias, which grows with dimension. The band is
    deliberately generous on the low side and tight on the high side: the
    estimator is not expected to overshoot.
    """
    assert predicted_dimension(**kw) == pred
    X = nominal_family(2500, seed=1, **kw)
    est = levina_bickel(X, k_values=(20,))[20]
    assert pred - 0.9 < est < pred + 0.3, (pred, est)


def test_estimate_tracks_the_parameter_count_monotonically():
    """Adding a parameter must raise the estimate; this is the real test."""
    seq = []
    for kw in (
        dict(vary_amplitude=True,  vary_phase=False, vary_speed=False, vary_offset=False),
        dict(vary_amplitude=True,  vary_phase=True,  vary_speed=False, vary_offset=False),
        dict(vary_amplitude=True,  vary_phase=True,  vary_speed=True,  vary_offset=False),
        dict(vary_amplitude=True,  vary_phase=True,  vary_speed=True,  vary_offset=True),
    ):
        seq.append(levina_bickel(nominal_family(2500, seed=2, **kw),
                                 k_values=(20,))[20])
    assert all(b > a for a, b in zip(seq, seq[1:])), seq
    increments = [b - a for a, b in zip(seq, seq[1:])]
    assert all(0.5 < d < 1.3 for d in increments), increments


def test_intrinsic_dimension_is_far_below_the_ambient_dimension():
    X = nominal_family(1500, seed=3)
    assert X.shape[1] == 1200
    assert levina_bickel(X, k_values=(20,))[20] < 10.0


def test_noise_raises_the_small_scale_estimate():
    """
    Additive noise adds thickness, not dimension: at small neighbourhood sizes
    the noisy cloud looks higher-dimensional, and the gap closes as the
    neighbourhood grows.
    """
    sim = BearingSignalSimulator(CWRU_PARAMS)
    np.random.seed(4)
    X_noisy = np.stack([sim.sample(regime="healthy") for _ in range(2000)])
    X_clean = nominal_family(2000, seed=4)
    ks = (5, 80)
    en = levina_bickel(X_noisy, k_values=ks)
    ec = levina_bickel(X_clean, k_values=ks)
    assert en[5] > ec[5] + 3.0, (en, ec)
    assert (en[80] - ec[80]) < (en[5] - ec[5]), (en, ec)


# ---------------------------------------------------------------------
# Attractor drift
# ---------------------------------------------------------------------

def test_trajectory_is_nominal_before_onset_and_ramps_after():
    X, sev = degradation_trajectory(400, seed=5, healthy_fraction=0.5)
    assert X.shape == (400, 1200)
    n_h = int(round(0.5 * 400))
    assert np.all(sev[:n_h] == 0.0)
    assert sev[n_h:].max() > 0.0
    assert np.all(np.diff(sev[n_h:]) >= -1e-12)     # monotone ramp


def test_frozen_radius_detects_drift_without_labels():
    """
    The radius is commissioned on the early-life segment and never adapted;
    a persistent departure must follow, and must follow onset rather than
    precede it.
    """
    sim = BearingSignalSimulator(CWRU_PARAMS)
    np.random.seed(6)
    op = PCAResidualOperator(16).fit(
        np.stack([sim.sample(regime="healthy") for _ in range(500)]))
    X, sev = degradation_trajectory(700, regime="inner_race", seed=7,
                                    healthy_fraction=0.5)
    r = op.residual(X)
    tau = certified_order_statistic(r[:120], ALPHA)
    assert np.isfinite(tau)
    det = first_persistent_departure(r > tau, q=8, p=10, start=120)
    onset = int(np.argmax(sev > 0))
    assert det is not None
    assert det > onset


def test_no_departure_is_declared_on_a_purely_nominal_record():
    """A record with no degradation must not trigger the persistence rule."""
    sim = BearingSignalSimulator(CWRU_PARAMS)
    np.random.seed(8)
    op = PCAResidualOperator(16).fit(
        np.stack([sim.sample(regime="healthy") for _ in range(500)]))
    X, sev = degradation_trajectory(600, seed=9, healthy_fraction=1.0)
    assert sev.max() == 0.0
    r = op.residual(X)
    tau = certified_order_statistic(r[:120], ALPHA)
    assert first_persistent_departure(r > tau, q=8, p=10, start=120) is None


def test_persistence_rule_semantics():
    flags = np.zeros(40, dtype=bool)
    assert first_persistent_departure(flags, q=3, p=5) is None
    flags[10:13] = True
    assert first_persistent_departure(flags, q=3, p=5) == 12
    assert first_persistent_departure(flags, q=4, p=5) is None
    assert first_persistent_departure(flags, q=3, p=5, start=20) is None
