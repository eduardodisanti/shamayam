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
