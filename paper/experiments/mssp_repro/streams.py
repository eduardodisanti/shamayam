"""
Synthetic residual-stream generators.

The coverage proposition [prop:coverage] is distribution-free, so the appropriate test is not one
autoencoder's residuals but a family of distributions chosen to be as
heterogeneous as possible: light and heavy tails, bounded and unbounded
support, low and high skewness, unimodal and bimodal. Any dependence of
attained coverage on the member of the family would falsify the proposition.
"""

import numpy as np


def make_distributions(rng):
    """Return {name: n -> residual sample} using the supplied Generator."""
    return {
        "lognormal(0,0.4)": lambda n: rng.lognormal(0.0, 0.4, n),
        "gamma(k=3)":       lambda n: rng.gamma(3.0, 1.0, n),
        "exponential(1)":   lambda n: rng.exponential(1.0, n),
        "pareto(a=3)":      lambda n: rng.pareto(3.0, n) + 1.0,
        "halfnormal":       lambda n: np.abs(rng.normal(1.0, 0.15, n)),
        "bimodal mixture":  lambda n: np.where(
                                rng.random(n) < 0.7,
                                rng.normal(1.0, 0.10, n),
                                rng.normal(1.6, 0.25, n)),
    }


def inject_drift(stream, *, slope):
    """
    Add a deterministic linear trend, breaking exchangeability while leaving
    the marginal spread broadly comparable.

    Used to measure the POWER of the permutation test in
    `exchangeability.py`: a drifting commissioning window is exactly the
    failure mode that voids the exchangeability assumption [ass:exchangeability], and a useful test must
    detect it. `slope` is expressed in units of the stream's own standard
    deviation, accumulated over the full length.
    """
    stream = np.asarray(stream, dtype=np.float64)
    n = stream.size
    trend = np.linspace(0.0, slope * np.std(stream), n)
    return stream + trend
