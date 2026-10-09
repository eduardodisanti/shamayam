"""
Noise-free nominal families and slow degradation trajectories.

Two generators, serving the two dynamical readings that
Section 10 of the paper insists on keeping apart.

`nominal_family` produces the deterministic nuisance family with no additive
noise, by calling the simulator's harmonic construction directly. This is the
object whose intrinsic dimension the embedding reading predicts, and it is the
clean setting in which that prediction can be tested; the full simulator adds
noise, which thickens the set without changing its dimension.

`degradation_trajectory` produces a chronological sequence of windows under a
slowly ramping fault severity. This is the second reading: not motion along a
fixed reconstructed orbit but slow drift of the orbit itself as the parameters
defining it change. It is a self-contained analogue of a run-to-failure record
and lets the frozen-radius protocol be exercised end to end without requiring
the IMS archive.
"""

import math

import numpy as np

from .bearing_simulator import BearingSignalSimulator, CWRU_PARAMS

# Kinematic fault frequencies of the vendored simulator, in Hz before the
# speed factor is applied.
FAULT_FREQ = {"outer_race": 108.0, "inner_race": 162.0, "ball_fault": 72.0}


def _base(sim, *, amp, phase, speed, signature):
    return sim._healthy_base(amp, phase, speed, signature)


def nominal_family(n, *, seed=0, params=CWRU_PARAMS, signature=None,
                   vary_amplitude=True, vary_phase=True, vary_speed=True,
                   vary_offset=True):
    """
    Deterministic nominal windows, no additive noise and no dropout.

    Each enabled flag contributes one continuously varying parameter, so the
    image is generically a manifold of that dimension embedded in R^{n_w}.
    Disabling a flag removes exactly one direction, which is what makes the
    prediction testable rather than merely plausible.
    """
    rng = np.random.default_rng(seed)
    sim = BearingSignalSimulator(params)
    if signature is None:
        signature = np.ones(5)

    rows = []
    for _ in range(int(n)):
        amp = rng.uniform(0.85, 1.15) if vary_amplitude else 1.0
        phase = rng.uniform(-0.3, 0.3) if vary_phase else 0.0
        speed = rng.uniform(0.95, 1.05) if vary_speed else 1.0
        offset = rng.uniform(-0.05, 0.05) if vary_offset else 0.0
        rows.append(_base(sim, amp=amp, phase=phase, speed=speed,
                          signature=signature) + offset)
    return np.stack(rows)


def degradation_trajectory(n_recordings, *, regime="outer_race", seed=0,
                           params=CWRU_PARAMS, signature=None,
                           healthy_fraction=0.35, max_severity=0.6,
                           noise=True):
    """
    A chronological sequence of windows under slowly ramping fault severity.

    The first `healthy_fraction` of the record has zero severity and stands
    for the early-life nominal segment from which a radius is commissioned.
    Severity then ramps smoothly to `max_severity`, so the reconstructed orbit
    deforms continuously rather than switching between discrete regimes.

    Returns
    -------
    X : (n_recordings, n_w) windows in chronological order
    severity : (n_recordings,) the ramp actually applied, for reference only;
        it is never used by the detector.
    """
    rng = np.random.default_rng(seed)
    sim = BearingSignalSimulator(params)
    if signature is None:
        signature = np.ones(5)
    if regime not in FAULT_FREQ:
        raise ValueError(f"unknown regime {regime!r}")

    n = int(n_recordings)
    n_healthy = int(round(healthy_fraction * n))
    ramp = np.zeros(n, dtype=np.float64)
    if n > n_healthy:
        ramp[n_healthy:] = np.linspace(0.0, max_severity, n - n_healthy)

    rows = []
    for t in range(n):
        # Nuisance drawn exactly as the simulator's own `sample` draws it, so
        # that the early-life segment is on-distribution with respect to a
        # representation fitted on `sample` output. Reusing the vendored
        # `_nuisance` rather than reimplementing it keeps the noise model
        # identical by construction.
        amp = rng.uniform(0.85, 1.15)
        phase = rng.uniform(-0.3, 0.3)
        speed = rng.uniform(0.95, 1.05)
        offset = rng.uniform(-0.05, 0.05)
        extra_noise = rng.uniform(0.0, 0.03)
        dropout = rng.uniform(0.0, 0.03)

        # the simulator's impulse and nuisance construction use the legacy
        # global RNG; seed it from our generator to stay reproducible
        np.random.seed(int(rng.integers(0, 2**31 - 1)))

        x = _base(sim, amp=amp, phase=phase, speed=speed, signature=signature)
        if ramp[t] > 0.0:
            x = x + sim._impulse_train(FAULT_FREQ[regime] * speed,
                                       strength=float(ramp[t]), jitter=0.05)
        if noise:
            x = sim._nuisance(x, offset, extra_noise, dropout)
        else:
            x = x + offset
        rows.append(x)

    return np.stack(rows), ramp


def first_persistent_departure(flags, *, q=8, p=10, start=0):
    """
    Index of the first recording at which at least `q` of the trailing `p`
    observations exceed the radius, searched only from `start` onward.

    Returns None if no such index exists. The rule mirrors the persistence
    criterion used on the run-to-failure records, and is stated here once so
    that the convention is unambiguous.
    """
    flags = np.asarray(flags, dtype=bool)
    for t in range(max(start, p - 1), flags.size):
        if flags[t - p + 1: t + 1].sum() >= q:
            return int(t)
    return None


def false_declaration_probability(*, q=8, p=10, alpha=0.02, n_recordings=None):
    """
    Probability that the persistence rule declares a departure while the
    process is still nominal.

    WHY THIS FUNCTION EXISTS
    ------------------------
    The persistence rule is the one free parameter of the run-to-failure
    protocol, and it is the parameter that sets the reported lead times: a
    permissive rule declares departure earlier and therefore flatters the
    result. It should not be chosen by inspection.

    Under the nominal regime an exceedance occurs with probability `alpha`, so
    the probability that a window of `p` consecutive recordings contains at
    least `q` exceedances is the upper tail of a Binomial(p, alpha). The
    calculation assumes independence between recordings, which is optimistic:
    residuals of neighbouring recordings are positively correlated, so the
    true probability is HIGHER than this returns. Treat the value as a lower
    bound on the risk.

    The numbers decide the question for the IMS protocol. At the healthy
    false-alarm rate actually attained there, near 5% rather than the nominal
    2%, a three-of-five rule declares a spurious departure in roughly a third
    of bearings over a run of two thousand recordings, while eight-of-ten does
    so with probability of order 1e-9. A rule cannot be used to time an event
    it produces on its own that often.

    Parameters
    ----------
    q, p : int
        Declare departure when at least `q` of the trailing `p` recordings
        exceed the radius. Must satisfy 1 <= q <= p.
    alpha : float
        Per-recording exceedance probability under the nominal regime. Use the
        ATTAINED false-alarm rate, not the target: the two differ whenever the
        estimator undercovers, and it is the attained rate that governs.
    n_recordings : int, optional
        If given, also return the probability of at least one spurious
        declaration over a record of this length, counting disjoint windows.

    Returns
    -------
    float or tuple(float, float)
        Per-window probability, and if `n_recordings` is given, the
        probability of at least one spurious declaration over the record.
    """
    if not 1 <= q <= p:
        raise ValueError(f"need 1 <= q <= p, got q={q}, p={p}")
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be a probability, got {alpha}")

    per_window = float(sum(math.comb(p, k) * alpha**k * (1.0 - alpha)**(p - k)
                           for k in range(q, p + 1)))
    if n_recordings is None:
        return per_window
    n_windows = int(n_recordings) // int(p)
    return per_window, float(1.0 - (1.0 - per_window)**n_windows)


def recording_score(window_scores, *, mode="mean", percentile=95.0):
    """
    Aggregate the window-level residuals of one recording into a single score.

    The aggregation must be IDENTICAL in calibration and in evaluation. This
    is not a stylistic requirement: the radius is a quantile of the calibration
    scores, so calibrating on one statistic and testing against another
    compares quantities on different scales and voids the coverage guarantee
    entirely. Stating the rule in one function, used by both paths, is what
    makes that impossible to get wrong by accident.

    `mode="mean"` is the convention under which the reported field results were
    produced, and it is the correct one at the window length used. That is not
    obvious, so the argument is recorded here rather than in a commit message.

    A high quantile looks like the more sensitive statistic -- the usual
    justification is that a localized disturbance should not be diluted by the
    nominal windows sharing its recording -- but it fails on two counts at 17
    windows per IMS recording.

    First, a 95th percentile of 17 values IS the sample maximum. At alpha=0.05
    the feasibility floor is 1/alpha - 1 = 19 observations and k_alpha = 18 >
    17, so no such quantile is defined distribution-free at all; overlapping
    the windows to reach 33 does not help, because the degenerate range extends
    to 39 and the estimator stays the sample maximum. Using it would reproduce,
    inside the reduction, exactly the failure mode this package exists to
    document.

    Second, the premise is false for this signal. The IMS bearings run at 2000
    rpm with an outer-race defect frequency near 236 Hz, so a 1200-sample
    window at 20 kHz spans 60 ms and holds roughly fourteen defect impulses.
    The signature is in every window, not in a few, which is the regime where
    averaging divides the nominal dispersion by sqrt(17) and leaves the shift
    in the mean untouched.

    `mode="percentile"` is therefore kept for a genuinely sparse anomaly -- a
    single impact, an ingress of contaminant -- and for window counts well
    clear of the degenerate range. It is not a drop-in alternative.
    """
    w = np.asarray(window_scores, dtype=float)
    if w.size == 0:
        raise ValueError("no window scores to aggregate")
    if mode == "mean":
        return float(np.mean(w))
    if mode == "percentile":
        return float(np.percentile(w, percentile))
    raise ValueError(f"unknown aggregation mode {mode!r}; "
                     "use 'mean' or 'percentile'")
