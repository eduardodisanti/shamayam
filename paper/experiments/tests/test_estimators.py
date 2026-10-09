"""
The interpolation remark [rem:interpolation_bias]: the interpolated empirical quantile is anti-conservative relative to
the certified order statistic, and the verbatim port of the published
estimator is faithful.
"""

from collections import deque

import numpy as np
import pytest

from mssp_repro import (AdaptiveOperationalRadius, certified_order_statistic,
                        interpolated_quantile, is_feasible)


# ---------------------------------------------------------------------
# Independent reimplementation of the published class, used only to pin
# that the port in mssp_repro.calibration did not drift.
# ---------------------------------------------------------------------

class _PublishedAdaptiveOperationalRadius:
    """Transcribed from bearing_autoencoder_cwru_per_asset.ipynb."""

    def __init__(self, percentile=98.0, window_size=100, min_samples=20):
        self.percentile = float(percentile)
        self.window_size = int(window_size)
        self.min_samples = int(min_samples)
        self.buf = deque(maxlen=self.window_size)

    def update(self, mse_value):
        self.buf.append(float(mse_value))
        if len(self.buf) < self.min_samples:
            return np.nan
        arr = np.asarray(self.buf, dtype=np.float64)
        return float(np.percentile(arr, self.percentile))

    def warmup_trace(self, mse_sequence):
        return np.asarray([self.update(v) for v in mse_sequence],
                          dtype=np.float64)


def test_port_reproduces_the_published_estimator_exactly():
    rng = np.random.default_rng(0)
    stream = rng.lognormal(0.0, 0.4, 200)

    ported = AdaptiveOperationalRadius(
        interpolated_quantile, window_size=200, min_samples=20
    ).warmup_trace(stream)
    published = _PublishedAdaptiveOperationalRadius(
        percentile=98.0, window_size=200, min_samples=20
    ).warmup_trace(stream)

    assert np.allclose(ported, published, equal_nan=True, rtol=0, atol=0)


@pytest.mark.parametrize("alpha", [0.01, 0.02, 0.05, 0.10])
def test_interpolated_never_exceeds_the_certified_order_statistic(alpha):
    """
    The premise of the interpolation remark [rem:interpolation_bias], as a property test over many random samples:
    for an upper quantile, linear interpolation lands at or below the order
    statistic prescribed by the coverage proposition [prop:coverage]. Hence it cannot satisfy the bound.
    """
    rng = np.random.default_rng(1)
    pct = 100.0 * (1.0 - alpha)
    for _ in range(400):
        n = int(rng.integers(2, 300))
        if not is_feasible(n, alpha):
            continue
        sample = rng.lognormal(0.0, 0.6, n)
        assert interpolated_quantile(sample, pct) <= \
            certified_order_statistic(sample, alpha) + 1e-12


def test_interpolation_gap_is_strict_in_the_degenerate_range():
    """
    Inside the degenerate range the certified radius is the sample maximum, so
    interpolation is strictly smaller whenever the top two values differ.
    """
    rng = np.random.default_rng(2)
    alpha = 0.02
    strictly_smaller = 0
    trials = 300
    for _ in range(trials):
        sample = rng.lognormal(0.0, 0.4, 60)          # inside [49, 98]
        if interpolated_quantile(sample, 98.0) < \
                certified_order_statistic(sample, alpha) - 1e-12:
            strictly_smaller += 1
    assert strictly_smaller == trials


def test_certified_estimator_is_an_order_statistic_of_the_sample():
    """The radius must be an observed value, not an interpolated artefact."""
    rng = np.random.default_rng(4)
    for _ in range(200):
        n = int(rng.integers(49, 300))
        sample = rng.lognormal(0.0, 0.5, n)
        tau = certified_order_statistic(sample, 0.02)
        assert np.any(np.isclose(sample, tau, rtol=0, atol=0))


def test_warmup_returns_nan_before_min_samples():
    rng = np.random.default_rng(6)
    est = AdaptiveOperationalRadius(interpolated_quantile, window_size=100,
                                    min_samples=20)
    trace = est.warmup_trace(rng.random(60))
    assert np.all(np.isnan(trace[:19]))
    assert np.all(np.isfinite(trace[19:]))


def test_certified_trace_is_nan_until_the_coverage_floor():
    """
    With the certified estimator the trace stays NaN until n reaches the
    commissioning floor [cor:min_commissioning], even though warm-up ends earlier. This is the
    intended coupling between the estimator and the guarantee.
    """
    rng = np.random.default_rng(8)
    est = AdaptiveOperationalRadius(certified_order_statistic,
                                    window_size=200, min_samples=20)
    trace = est.warmup_trace(rng.lognormal(0.0, 0.4, 120))
    assert np.all(np.isnan(trace[:48]))       # n <= 48  -> infeasible
    assert np.all(np.isfinite(trace[48:]))    # n >= 49  -> certifiable
