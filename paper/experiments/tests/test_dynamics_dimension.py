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


# ---------------------------------------------------------------------
# The persistence rule as a decision, not a default
#
# The published notebook used three-of-five; the accompanying text described
# eight-of-ten; the two give different lead times and the discrepancy went
# unresolved through a full draft. These tests pin the argument that settles
# it, so the choice cannot quietly revert to the permissive rule.
# ---------------------------------------------------------------------

def test_permissive_persistence_is_unusable_at_the_attained_false_alarm_rate():
    """
    At the healthy false-alarm rate actually attained on the IMS bearings --
    near 5%, not the nominal 2%, because the field results used the
    interpolated estimator -- a three-of-five rule declares a spurious
    departure in a large fraction of records. It cannot be used to time an
    event it manufactures on its own that often.
    """
    from mssp_repro import false_declaration_probability
    attained = 0.0498
    _, loose = false_declaration_probability(q=3, p=5, alpha=attained,
                                             n_recordings=2000)
    _, strict = false_declaration_probability(q=8, p=10, alpha=attained,
                                              n_recordings=2000)
    assert loose > 0.30, f"3/5 spurious-declaration risk was {loose:.3f}"
    assert strict < 1e-5, f"8/10 spurious-declaration risk was {strict:.3e}"
    assert strict < loose / 1e5


def test_the_gap_survives_at_the_nominal_rate_too():
    """The conclusion must not depend on using the attained rather than the
    target rate: at 2% the separation is even wider."""
    from mssp_repro import false_declaration_probability
    loose = false_declaration_probability(q=3, p=5, alpha=0.02)
    strict = false_declaration_probability(q=8, p=10, alpha=0.02)
    assert strict < loose / 1e6


def test_stricter_rule_never_declares_earlier():
    """
    Monotonicity, which is the reason the choice matters for lead times: a
    stricter rule can only postpone the declaration, so it can only SHORTEN
    the reported lead time. Adopting it works against the headline result.
    """
    from mssp_repro import first_persistent_departure
    rng = np.random.default_rng(7)
    for _ in range(200):
        flags = rng.random(400) < rng.uniform(0.05, 0.5)
        loose = first_persistent_departure(flags, q=3, p=5)
        strict = first_persistent_departure(flags, q=8, p=10)
        if strict is not None:
            assert loose is not None, "8/10 fired where 3/5 did not"
            assert loose <= strict


def test_aggregation_is_explicit_and_rejects_silent_defaults():
    from mssp_repro import recording_score
    import pytest as _pytest
    w = [1.0, 1.0, 1.0, 9.0]
    assert recording_score(w) == pytest.approx(3.0)
    assert recording_score(w, mode="percentile") > 7.0
    with _pytest.raises(ValueError):
        recording_score(w, mode="p95")
    with _pytest.raises(ValueError):
        recording_score([])


def test_a_high_quantile_over_few_windows_is_the_sample_maximum():
    """
    The reduction from window residuals to a recording score is itself a
    quantile estimate, and the corollaries of Section 7 apply to it. At the 17
    windows of an IMS recording a 95th percentile is not a percentile: it is
    the sample maximum, and it is not even feasible distribution-free.

    This is the argument that settled the aggregation question, so it is
    pinned rather than left in prose.
    """
    from mssp_repro import (k_alpha, is_feasible, minimum_commissioning_length,
                            is_degenerate_maximum, recording_score)
    n_windows, alpha = 17, 0.05

    assert not is_feasible(n_windows, alpha), (
        "17 windows should be below the feasibility floor at alpha=0.05")
    assert minimum_commissioning_length(alpha) == 19
    assert k_alpha(n_windows, alpha) > n_windows

    # Overlapping to 33 windows clears the floor but not the degenerate range.
    assert is_feasible(33, alpha)
    assert is_degenerate_maximum(33, alpha), (
        "at 33 windows the estimator is still the sample maximum")

    # And the empirical statement: p95 of 17 draws IS the largest or the
    # second largest, never an interior order statistic.
    rng = np.random.default_rng(3)
    for _ in range(300):
        x = rng.lognormal(size=n_windows)
        p95 = recording_score(x, mode="percentile")
        assert p95 >= np.sort(x)[-2]


def test_averaging_wins_when_the_signature_is_ubiquitous():
    """
    The sensitivity claim, in the regime that actually holds for a bearing
    defect: the signature is present in every window, so the mean improves the
    normalized contrast by averaging noise, while a high quantile discards 16
    of 17 observations.
    """
    from mssp_repro import recording_score
    rng = np.random.default_rng(11)
    n, reps = 17, 4000
    nominal = rng.lognormal(sigma=0.5, size=(reps, n))
    degraded = nominal * 3.0            # ubiquitous: every window affected

    def contrast(mode):
        s_nom = np.array([recording_score(r, mode=mode) for r in nominal])
        s_deg = np.array([recording_score(r, mode=mode) for r in degraded])
        return (s_deg.mean() - s_nom.mean()) / s_nom.std()

    assert contrast("mean") > 1.4 * contrast("percentile")
