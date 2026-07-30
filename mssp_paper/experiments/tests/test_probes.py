"""
The distance-proxy probe, and the adequacy criterion it defines.

These tests need no deep-learning framework: the criterion is checked on the
linear operator, which is the negative control, and on synthetic operators
constructed to pass or fail by design. The Conv1D operator is exercised
separately in `test_conv_autoencoder.py`, which is skipped when TensorFlow is
absent.
"""

import numpy as np
import pytest

from mssp_repro import (PCAResidualOperator, certified_order_statistic,
                        distance_proxy_probe, passes_distance_proxy)
from mssp_repro.bearing_simulator import CWRU_PARAMS, BearingSignalSimulator

ALPHA = 0.02


def _windows(n, seed, regime="healthy"):
    sim = BearingSignalSimulator(CWRU_PARAMS)
    np.random.seed(seed)
    return np.stack([sim.sample(regime=regime) for _ in range(n)])


class _PCAWithCodec(PCAResidualOperator):
    """PCA operator exposing the encode/decode pair the probe needs."""

    def encode(self, X):
        return self._pca.transform(np.asarray(X, dtype=np.float64))

    def decode(self, Z):
        return self._pca.inverse_transform(np.asarray(Z, dtype=np.float64))


@pytest.fixture(scope="module")
def linear_setup():
    X_fit = _windows(700, 0)
    X_ref = _windows(400, 11)
    op = _PCAWithCodec(16).fit(X_fit)
    tau = certified_order_statistic(op.residual(_windows(300, 3)), ALPHA)
    return op, X_fit, X_ref, tau


# ---------------------------------------------------------------------
# The criterion has teeth: the linear operator fails it, decisively
# ---------------------------------------------------------------------

def test_linear_operator_fails_the_probe(linear_setup):
    op, X_fit, X_ref, tau = linear_setup
    res = distance_proxy_probe(op, X_fit[:400], tau, reference=X_ref)
    assert not passes_distance_proxy(res)
    # accepted points lie orders of magnitude beyond the nominal spacing
    assert res["max_accepted_distance"] > 50.0 * res["nominal_scale"]


def test_linear_operator_accepts_everything_the_probe_offers(linear_setup):
    """Every probe point is accepted: the level set is a slab, not a tube."""
    op, X_fit, X_ref, tau = linear_setup
    res = distance_proxy_probe(op, X_fit[:400], tau, reference=X_ref)
    assert res["accept_ratio"] == 1.0
    assert all(row["residual"] < 1e-20 for row in res["rows"])


def test_linear_operator_still_detects_the_simulated_faults(linear_setup):
    """
    The point of keeping it as a control: good detection does not imply an
    adequate residual. Faults lie off the retained subspace, probe points do
    not, and only the probe distinguishes the two situations.
    """
    op, _, _, tau = linear_setup
    for regime in ("outer_race", "inner_race"):
        r = op.residual(_windows(200, 6, regime))
        assert float(np.mean(r > tau)) > 0.9, regime


# ---------------------------------------------------------------------
# Sanity of the criterion itself
# ---------------------------------------------------------------------

def test_nominal_scale_is_not_degenerate(linear_setup):
    """
    Regression test for a real defect: computing the nominal spacing against
    the cloud itself makes every point its own neighbour, the scale collapses
    to zero and the criterion silently passes nothing.
    """
    op, X_fit, X_ref, tau = linear_setup
    with_ref = distance_proxy_probe(op, X_fit[:200], tau, reference=X_ref)
    self_ref = distance_proxy_probe(op, X_fit[:200], tau)
    assert with_ref["nominal_scale"] > 0.0
    assert self_ref["nominal_scale"] > 0.0
    assert self_ref["nominal_scale"] == pytest.approx(
        with_ref["nominal_scale"], rel=0.5)


def test_an_exact_distance_residual_passes():
    """
    A residual that IS the distance to the nominal sample passes by
    construction. This fixes the upper end of the criterion's range.
    """
    X = _windows(300, 0)
    ref = _windows(300, 11)

    class ExactDistance:
        def encode(self, A):
            return np.asarray(A, dtype=np.float64)[:, :4]

        def decode(self, Z):
            Z = np.asarray(Z, dtype=np.float64)
            out = np.tile(X[0], (Z.shape[0], 1)).copy()
            out[:, :4] = Z
            return out

        def residual(self, A):
            A = np.asarray(A, dtype=np.float64)
            d2 = ((A[:, None, :] - X[None, :, :]) ** 2).sum(-1)
            return np.sqrt(d2.min(1))

    tau = float(np.percentile(ExactDistance().residual(ref), 98))
    res = distance_proxy_probe(ExactDistance(), X[:120], tau, reference=ref,
                               shifts=(0, 3, 10, 30))
    assert passes_distance_proxy(res, tolerance=5.0)


def test_probe_reports_monotone_growth_for_a_distance_like_residual():
    """A residual that tracks distance must grow as the probe moves out."""
    X = _windows(200, 0)
    ref = _windows(200, 11)

    class Radial:
        def __init__(self):
            self.c = X.mean(0)

        def encode(self, A):
            return np.asarray(A, dtype=np.float64) - self.c

        def decode(self, Z):
            return np.asarray(Z, dtype=np.float64) + self.c

        def residual(self, A):
            return ((np.asarray(A, dtype=np.float64) - self.c) ** 2).sum(1)

    op = Radial()
    tau = float(np.percentile(op.residual(ref), 98))
    res = distance_proxy_probe(op, X[:120], tau, reference=ref)
    residuals = [row["residual"] for row in res["rows"]]
    assert all(b >= a for a, b in zip(residuals, residuals[1:])), residuals
    assert res["residual_growth"] > 1.0


def test_tolerance_parameter_is_respected():
    fake = {"max_accepted_distance": 10.0, "nominal_scale": 4.0}
    assert passes_distance_proxy(fake, tolerance=3.0)
    assert not passes_distance_proxy(fake, tolerance=2.0)
