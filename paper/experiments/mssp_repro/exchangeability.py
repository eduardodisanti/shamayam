"""
Permutation test for the exchangeability assumption [ass:exchangeability] (exchangeability of nominal commissioning
residuals).

WHY THIS IS THE RIGHT TEST
--------------------------
The coverage proposition [prop:coverage] rests on exactly one assumption: that the commissioning
residuals and the next nominal residual are exchangeable. The exchangeability-probe remark [rem:exchangeability_test] of the
paper observes that this is empirically testable, because under
exchangeability the ARRIVAL ORDER of the commissioning residuals is
distributionally irrelevant. The repeated-commissioning ablation reported in
the published work permutes arrival order and is therefore not merely a
robustness check but a probe of this assumption.

This module turns that observation into a test with a p-value. The statistic
is Spearman rank correlation between residual value and arrival index, which
is zero in expectation under exchangeability and grows under monotone drift.
Its null distribution is obtained by permutation, so the test is exact and
distribution-free, matching the standard of the coverage proposition [prop:coverage] itself.

Interpretation: a small p-value indicates order dependence, i.e. drift or
non-stationarity within the commissioning window, which voids the coverage
guarantee. It does NOT indicate a faulty asset.
"""

import numpy as np


def _value_ranks(stream):
    """Ranks 0..n-1 of the observed values, ties broken by arrival position."""
    n = stream.size
    ranks = np.empty(n, dtype=np.float64)
    ranks[np.argsort(stream, kind="mergesort")] = np.arange(n, dtype=np.float64)
    return ranks


def _abs_corr_rows(rank_matrix, index_vector):
    """
    |Pearson correlation| between each row of `rank_matrix` and
    `index_vector`, vectorised over rows.

    Spearman on the original values equals Pearson on their ranks, and
    permuting the stream permutes the rank vector, so the entire permutation
    null distribution is obtained from one matrix of permuted ranks. This
    avoids re-sorting inside the permutation loop.
    """
    rm = rank_matrix - rank_matrix.mean(axis=1, keepdims=True)
    iv = index_vector - index_vector.mean()
    num = rm @ iv
    denom = np.sqrt((rm * rm).sum(axis=1) * (iv * iv).sum())
    out = np.zeros_like(num)
    nz = denom > 0
    out[nz] = num[nz] / denom[nz]
    return np.abs(out)


def permutation_exchangeability_test(stream, *, n_permutations=2000,
                                     random_state=0):
    """
    Test H0: the commissioning residuals are exchangeable in arrival order.

    Returns
    -------
    dict with keys
        statistic    : |Spearman rho| on the observed arrival order
        p_value      : permutation p-value, (1 + #{perm >= obs}) / (1 + B)
        null_mean    : mean of the permutation null distribution
        n            : stream length

    The p-value uses the standard add-one correction, so it is never zero and
    is valid for any B.
    """
    stream = np.asarray(stream, dtype=np.float64)
    if stream.size < 3:
        raise ValueError("stream too short for a permutation test")

    n = stream.size
    idx = np.arange(n, dtype=np.float64)
    ranks = _value_ranks(stream)

    observed = float(_abs_corr_rows(ranks[None, :], idx)[0])

    rng = np.random.default_rng(random_state)
    permuted = np.argsort(rng.random((n_permutations, n)), axis=1)
    null = _abs_corr_rows(ranks[permuted], idx)

    p_value = (1.0 + np.count_nonzero(null >= observed)) / (1.0 + n_permutations)

    return {
        "statistic": observed,
        "p_value": float(p_value),
        "null_mean": float(null.mean()),
        "n": int(n),
    }
