"""
Intrinsic dimension of the nominal observation cloud.

WHY THIS IS A TEST AND NOT A DESCRIPTION
----------------------------------------
Read through the delay-embedding remark [rem:delay_embedding], an observation
window is a delay-coordinate vector, and the nuisance remark
[rem:nuisance_on_attractor] says each nuisance parameter that acts
non-trivially on the reconstructed orbit contributes one direction to the
nominal set while additive noise contributes thickness rather than dimension.

That makes the intrinsic dimension of the nominal cloud PREDICTABLE from the
generator, and therefore falsifiable. For the vendored simulator with a fixed
asset signature the deterministic nuisance parameters are amplitude, phase,
speed and offset, so the noise-free nominal family should have intrinsic
dimension 4 against an ambient dimension of 1200. If the measured value were
far from 4, the reading would be wrong.

SCALE DEPENDENCE IS THE POINT, NOT A NUISANCE
---------------------------------------------
On noisy data any neighbourhood-based estimator is scale dependent: below the
noise level the cloud looks full-dimensional, above it the manifold structure
appears. The estimator is therefore reported as a function of the neighbourhood
size k rather than as a single number, and the noise-free family is measured
separately as the clean test of the prediction.

The estimator is the maximum-likelihood construction of Levina and Bickel,
with the Mackay-Ghahramani correction of averaging inverses rather than
estimates, which removes the bias of the original averaging.
"""

import numpy as np


def _knn_distances(X, k_max):
    """Distances to the k_max nearest neighbours, excluding the point itself."""
    X = np.asarray(X, dtype=np.float64)
    n = X.shape[0]
    if k_max >= n:
        raise ValueError("k_max must be smaller than the number of points")
    # squared euclidean via the gram trick, then partial sort
    sq = (X * X).sum(axis=1)
    d2 = sq[:, None] + sq[None, :] - 2.0 * (X @ X.T)
    np.fill_diagonal(d2, np.inf)
    np.maximum(d2, 0.0, out=d2)
    idx = np.argpartition(d2, k_max, axis=1)[:, :k_max]
    d = np.sqrt(np.take_along_axis(d2, idx, axis=1))
    d.sort(axis=1)
    return d


def levina_bickel(X, k_values=(5, 10, 20, 40, 80), *, corrected=True):
    """
    Maximum-likelihood intrinsic dimension at several neighbourhood sizes.

    Parameters
    ----------
    X : (n_samples, n_features)
    k_values : neighbourhood sizes to report
    corrected : average the inverse estimates (Mackay-Ghahramani) rather than
        the estimates themselves. The uncorrected average is biased upward.

    Returns
    -------
    dict mapping k to the estimated intrinsic dimension.
    """
    X = np.asarray(X, dtype=np.float64)
    k_max = int(max(k_values))
    d = _knn_distances(X, k_max)

    out = {}
    for k in k_values:
        k = int(k)
        if k < 3:
            raise ValueError("k must be at least 3")
        Tk = d[:, k - 1][:, None]                 # distance to the k-th
        Tj = d[:, : k - 1]                        # the first k-1
        with np.errstate(divide="ignore", invalid="ignore"):
            logs = np.log(Tk / Tj)
        good = np.isfinite(logs).all(axis=1)
        logs = logs[good]
        if logs.size == 0:
            out[k] = np.nan
            continue
        inv_m = logs.mean(axis=1)                 # 1 / m_hat per point
        if corrected:
            out[k] = float(1.0 / inv_m.mean())    # average inverses
        else:
            out[k] = float((1.0 / inv_m).mean())
    return out


def predicted_dimension(*, vary_amplitude=True, vary_phase=True,
                        vary_speed=True, vary_offset=True,
                        signature_dims=0):
    """
    Dimension predicted by the embedding reading: one direction per nuisance
    parameter that acts non-trivially, plus any varied asset-signature
    directions. Additive noise is excluded because it contributes thickness,
    not dimension.
    """
    return (int(vary_amplitude) + int(vary_phase) + int(vary_speed)
            + int(vary_offset) + int(signature_dims))
