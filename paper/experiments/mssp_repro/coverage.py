"""
Closed-form quantities from the coverage proposition and its two corollaries.

Results are referred to by LaTeX label rather than by number, because numbering
shifts as the paper is drafted. The labels below resolve in mssp_draft.tex.

These are the paper's statements expressed as executable predicates, so the
test suite can check the mathematics directly rather than only checking that
the simulation code runs.

Distribution-free coverage [prop:coverage]
    tau = r_(k_alpha),  k_alpha = ceil((1-alpha)(n+1))
    =>  P(r_{n+1} <= tau) = k_alpha / (n+1)  in  [1-alpha, 1-alpha+1/(n+1)]

Minimum commissioning length [cor:min_commissioning]
    feasible  <=>  k_alpha <= n  <=>  n >= 1/alpha - 1

Degenerate range [cor:degenerate_range]
    k_alpha == n  <=>  1/alpha - 1 <= n < 2/alpha - 1
    i.e. the certified radius is the SAMPLE MAXIMUM throughout that band.
"""

import numpy as np


def k_alpha(n, alpha):
    """Index of the order statistic prescribed by the coverage proposition [prop:coverage] (1-indexed)."""
    return int(np.ceil((1.0 - alpha) * (n + 1)))


def is_feasible(n, alpha):
    """True iff a distribution-free (1-alpha) radius exists for n samples."""
    return k_alpha(n, alpha) <= n


def minimum_commissioning_length(alpha):
    """
    Smallest n admitting a distribution-free (1-alpha) radius (the commissioning-floor corollary [cor:min_commissioning]).

    Equals ceil(1/alpha) - 1. At alpha = 0.02 this is 49.
    """
    return int(np.ceil(1.0 / alpha)) - 1


def exact_coverage(n, alpha):
    """
    Exact attained coverage k_alpha/(n+1) under exchangeability, or NaN when
    infeasible. This is an equality, not a bound.
    """
    if not is_feasible(n, alpha):
        return np.nan
    return k_alpha(n, alpha) / (n + 1.0)


def coverage_band(n, alpha):
    """The admissible interval [1-alpha, 1-alpha+1/(n+1)] of the coverage proposition [prop:coverage]."""
    return (1.0 - alpha, 1.0 - alpha + 1.0 / (n + 1.0))


def is_degenerate_maximum(n, alpha):
    """
    True iff the certified radius coincides with the sample maximum, i.e.
    k_alpha == n (the degenerate-range corollary [cor:degenerate_range]). In this regime the radius is the order
    statistic of largest variance.
    """
    return k_alpha(n, alpha) == n


def degenerate_range(alpha):
    """
    Closed integer interval [n_lo, n_hi] on which the certified radius is the
    sample maximum, per the degenerate-range corollary [cor:degenerate_range]:

        1/alpha - 1 <= n < 2/alpha - 1

    Returns (n_lo, n_hi). The first commissioning length yielding an INTERIOR
    order statistic is n_hi + 1. At alpha = 0.02: (49, 98), interior from 99.
    """
    n_lo = minimum_commissioning_length(alpha)
    n_hi = int(np.ceil(2.0 / alpha)) - 2
    return n_lo, n_hi
