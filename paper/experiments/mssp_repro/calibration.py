"""
Operational-radius estimators and the convergence-based stopping rule.

PROVENANCE
----------
`AdaptiveOperationalRadius`, `operational_radius_convergence_trace` and
`find_convergence_index` are ported verbatim (modulo the injected
`estimator` argument) from

    inverse_problem @ TRB2027
      journal_paper/bearing_autoencoder_cwru_per_asset.ipynb
      journal_paper/bearing_autoencoder_NASA_per_asset.ipynb

so that the `interpolated_quantile` configuration reproduces the published
pipeline exactly. `tests/test_estimators.py` pins this equivalence against
an independent reimplementation.

The two estimators correspond to the two calibration conventions compared in
Section 7 of the paper:

  interpolated_quantile      -- numpy's linear-interpolation empirical
                                quantile, i.e. what the published code uses.
                                Anti-conservative: the interpolation remark [rem:interpolation_bias].
  certified_order_statistic  -- the order statistic prescribed by
                                The coverage proposition [prop:coverage], which carries the
                                distribution-free coverage guarantee.
"""

from collections import deque

import numpy as np

# ---------------------------------------------------------------------
# Configuration, matching the published notebooks exactly.
# ---------------------------------------------------------------------

TARGET_PERCENTILE = 98.0
ALPHA = 1.0 - TARGET_PERCENTILE / 100.0

MIN_WARMUP_SAMPLES = 20
MIN_CALIBRATION_SIZE = 40
MAX_CALIBRATION_SIZE = 200

CONVERGENCE_LOOKBACK = 10
CONVERGENCE_TOLERANCE = 0.01
CONVERGENCE_CONSECUTIVE = 10


# ---------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------

def interpolated_quantile(a, percentile=TARGET_PERCENTILE):
    """
    Empirical quantile with linear interpolation between order statistics.

    This is the estimator used in the published notebooks. For an upper
    quantile it returns a value at or below the corresponding order
    statistic and therefore does NOT satisfy the coverage bound of
    The coverage proposition [prop:coverage] (the interpolation remark [rem:interpolation_bias]).
    """
    return float(np.percentile(np.asarray(a, dtype=np.float64), percentile))


def certified_order_statistic(a, alpha=ALPHA):
    """
    The radius prescribed by the coverage proposition [prop:coverage]:

        tau = r_(k_alpha),   k_alpha = ceil((1 - alpha) * (n + 1))

    Returns NaN when n < 1/alpha - 1, i.e. when the target coverage is not
    attainable from n observations by ANY distribution-free procedure
    (the commissioning-floor corollary [cor:min_commissioning]). Returning NaN rather than silently falling back is
    deliberate: an uncertifiable radius must not be deployed.
    """
    a = np.sort(np.asarray(a, dtype=np.float64))
    n = a.size
    k = int(np.ceil((1.0 - alpha) * (n + 1)))
    if k > n:
        return np.nan
    return float(a[k - 1])              # a[] is 0-indexed, k is 1-indexed


# ---------------------------------------------------------------------
# Online estimator and stopping rule (ported verbatim)
# ---------------------------------------------------------------------

class AdaptiveOperationalRadius:
    """
    Online empirical-quantile estimator.

    The globally shared quantity is the target nominal coverage, not a
    z-score and not an absolute threshold. The local operational radius is
    estimated from the accepted nominal residuals of a single asset.

    Parameters
    ----------
    estimator : callable
        Maps a 1-D array of residuals to a scalar radius. Pass
        `interpolated_quantile` to reproduce the published pipeline or
        `certified_order_statistic` for the guarantee of the coverage proposition [prop:coverage].
    """

    def __init__(self, estimator=interpolated_quantile, window_size=100,
                 min_samples=20):
        if window_size < 2:
            raise ValueError("window_size must be at least 2.")
        if min_samples < 2:
            raise ValueError("min_samples must be at least 2.")
        if min_samples > window_size:
            raise ValueError("min_samples cannot be larger than window_size.")

        self.estimator = estimator
        self.window_size = int(window_size)
        self.min_samples = int(min_samples)
        self.buf = deque(maxlen=self.window_size)

    def update(self, value):
        """Add one nominal residual; return the current radius, NaN before warm-up."""
        self.buf.append(float(value))
        if len(self.buf) < self.min_samples:
            return np.nan
        return self.estimator(np.asarray(self.buf, dtype=np.float64))

    def warmup_trace(self, sequence):
        """Process a whole commissioning stream and return tau(t)."""
        return np.asarray([self.update(v) for v in sequence], dtype=np.float64)


def operational_radius_convergence_trace(tau_history, *, lookback=10,
                                         eps=1e-12):
    """Relative variation C_k(t) of Eq. (convergence) in the paper."""
    tau_history = np.asarray(tau_history, dtype=np.float64)
    conv = np.full(tau_history.shape, np.nan, dtype=np.float64)
    for t in range(lookback, len(tau_history)):
        cur, prev = tau_history[t], tau_history[t - lookback]
        if np.isfinite(cur) and np.isfinite(prev):
            conv[t] = abs(cur - prev) / max(abs(prev), eps)
    return conv


def find_convergence_index(tau_history, *, lookback=CONVERGENCE_LOOKBACK,
                           tolerance=CONVERGENCE_TOLERANCE,
                           consecutive=CONVERGENCE_CONSECUTIVE,
                           min_index=0):
    """
    First index at which C_k has stayed below `tolerance` for `consecutive`
    consecutive updates, not before `min_index`. None means the asset did
    not converge and must not be released into monitoring.
    """
    conv = operational_radius_convergence_trace(tau_history, lookback=lookback)
    stable = 0
    for t, value in enumerate(conv):
        if t < min_index:
            stable = 0
            continue
        if np.isfinite(value) and value < tolerance:
            stable += 1
            if stable >= consecutive:
                return t
        else:
            stable = 0
    return None


def stopping_rule_floor(min_calibration_size=MIN_CALIBRATION_SIZE,
                        consecutive=CONVERGENCE_CONSECUTIVE,
                        min_samples=MIN_WARMUP_SAMPLES,
                        lookback=CONVERGENCE_LOOKBACK):
    """
    Smallest calibration size the stopping rule can possibly emit.

    Two constraints bind, and the binding one depends on the configuration:

    1. The convergence scan is not allowed to start before index
       `min_calibration_size - 1`.
    2. The relative-variation trace C_k(t) is undefined until both tau(t) and
       tau(t - lookback) are finite. Since tau is NaN before `min_samples`
       observations, the first finite C_k is at index
       `min_samples - 1 + lookback`.

    The scan therefore effectively begins at the later of the two, and needs
    `consecutive` successive values below tolerance, giving

        floor = max(min_calibration_size - 1,
                    min_samples - 1 + lookback) + consecutive

    At the published configuration (min_calibration_size=40, consecutive=10,
    min_samples=20, lookback=10) constraint 1 binds, max(39, 29) = 39, and the
    floor is 49. Reducing min_calibration_size below 30 makes constraint 2
    bind instead: at min_calibration_size=25 the floor is 39, not 34.

    This floor is purely combinatorial and INDEPENDENT OF alpha. That it
    equals 49 at the published configuration, numerically coinciding with the
    The commissioning-floor corollary [cor:min_commissioning] coverage floor at alpha=0.02, is a coincidence of two
    unrelated mechanisms; see the confound note in Section 9 of the paper and
    `tests/test_stopping.py`.
    """
    scan_start = max(int(min_calibration_size) - 1,
                     int(min_samples) - 1 + int(lookback))
    return scan_start + int(consecutive)
