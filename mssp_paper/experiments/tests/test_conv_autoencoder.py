"""
The Conv1D operator of the technical note: architecture fidelity, determinism,
and the adequacy criterion it is kept in order to satisfy.

Skipped when TensorFlow is unavailable, so that layer A1 remains runnable
without a deep-learning framework.
"""

import numpy as np
import pytest

tf = pytest.importorskip("tensorflow", reason="layer A2 requires TensorFlow")

from mssp_repro import (certified_order_statistic, distance_proxy_probe,
                        passes_distance_proxy)
from mssp_repro.bearing_simulator import CWRU_PARAMS, BearingSignalSimulator
from mssp_repro.conv_autoencoder import (EXPECTED_PARAMS, ConvAEResidualOperator,
                                         build_autoencoder, configure)

ALPHA = 0.02
SIG_LEN = 1200


def _windows(n, seed, regime="healthy"):
    sim = BearingSignalSimulator(CWRU_PARAMS)
    np.random.seed(seed)
    return np.stack([sim.sample(regime=regime) for _ in range(n)])


# ---------------------------------------------------------------------
# Architecture fidelity
# ---------------------------------------------------------------------

def test_parameter_count_matches_the_technical_note():
    """
    847,601 trainable parameters, as reported. This pins the transcription:
    any drift in kernel sizes, strides or the latent width would move it.
    """
    configure(42)
    ae, _ = build_autoencoder(SIG_LEN, 16)
    assert ae.count_params() == EXPECTED_PARAMS


def test_latent_width_and_output_shape():
    configure(42)
    ae, enc = build_autoencoder(SIG_LEN, 16)
    assert enc.output_shape[-1] == 16
    assert ae.output_shape[1] == SIG_LEN


# ---------------------------------------------------------------------
# Determinism, with op determinism enabled
# ---------------------------------------------------------------------

def test_initial_weights_are_reproducible_under_the_seed():
    configure(42)
    a, _ = build_autoencoder(SIG_LEN, 16)
    w_a = [w.copy() for w in a.get_weights()]
    configure(42)
    b, _ = build_autoencoder(SIG_LEN, 16)
    w_b = b.get_weights()
    assert all(np.array_equal(x, y) for x, y in zip(w_a, w_b))


def test_a_different_seed_gives_different_weights():
    configure(42)
    a, _ = build_autoencoder(SIG_LEN, 16)
    w_a = [w.copy() for w in a.get_weights()]
    configure(7)
    b, _ = build_autoencoder(SIG_LEN, 16)
    assert not all(np.array_equal(x, y) for x, y in zip(w_a, b.get_weights()))


@pytest.mark.slow
def test_training_is_reproducible_under_the_seed():
    """
    Two independent short trainings from the same seed must agree exactly.
    This is what `enable_op_determinism` buys, and it holds within a single
    TensorFlow build rather than across builds.
    """
    X = _windows(200, 0)
    r1 = ConvAEResidualOperator(seed=42, epochs=2).fit(X).residual(X[:32])
    r2 = ConvAEResidualOperator(seed=42, epochs=2).fit(X).residual(X[:32])
    assert np.array_equal(r1, r2)


# ---------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------

# A converging schedule rather than a fixed small epoch count. These tests are
# marked slow and are meant to be run deliberately; a truncated run would test
# an undertrained operator, which is not the object of interest.
_SCHEDULE = dict(seed=42, epochs=150, patience=12, lr_patience=6)


@pytest.fixture(scope="module")
def trained():
    op = ConvAEResidualOperator(**_SCHEDULE).fit(_windows(900, 0))
    tau = certified_order_statistic(op.residual(_windows(300, 3)), ALPHA)
    return op, tau


@pytest.mark.slow
def test_training_stops_before_exhausting_the_budget(trained):
    """
    The budget is an upper bound, not a target. Reaching it means training was
    truncated rather than converged, and every downstream number would then be
    reporting an undertrained operator.
    """
    op, _ = trained
    assert op.history_["stop_reason"] != "budget_exhausted", op.describe_training()
    assert op.history_["epochs_run"] < op.history_["epochs_budget"]


@pytest.mark.slow
def test_operator_passes_the_distance_proxy_probe(trained):
    """
    The reason this operator replaced the linear one for the geometry
    demonstrations: it accepts only near the nominal scale, whereas the linear
    control accepts at hundreds of times that spacing.
    """
    op, tau = trained
    res = distance_proxy_probe(op, _windows(900, 0)[:400], tau,
                               reference=_windows(400, 11))
    assert passes_distance_proxy(res), res
    assert res["residual_growth"] > 100.0


@pytest.mark.slow
def test_residual_orders_nominal_below_faults(trained):
    """
    An invariant, not a tuned rate. Absolute detection rates depend on the
    training budget and belong in the reported tables; what must hold for any
    adequately trained operator is that fault residuals sit above nominal ones
    and that the calibrated radius keeps nominal false alarms near the target.
    """
    op, tau = trained
    r_nominal = op.residual(_windows(300, 5))
    assert float(np.mean(r_nominal > tau)) < 3.0 * ALPHA
    for regime in ("outer_race", "inner_race", "ball_fault"):
        r_fault = op.residual(_windows(200, 6, regime))
        assert np.median(r_fault) > np.median(r_nominal), regime


def test_operator_validates_input():
    op = ConvAEResidualOperator(seed=42, epochs=1)
    with pytest.raises(RuntimeError):
        op.residual(np.zeros((4, SIG_LEN)))
    op.fit(_windows(40, 0))
    with pytest.raises(ValueError):
        op.residual(np.zeros((4, 17)))
