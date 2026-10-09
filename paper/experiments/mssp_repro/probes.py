"""
The distance-proxy probe: an adequacy diagnostic for a residual.

WHAT IT TESTS
-------------
The residual-proxy assumption [ass:residual_proxy] asks that the residual
track distance to the nominal manifold. As stated it is one-sided and
qualitative, and the calibration of Section 7 does not need more than that:
coverage holds for any residual whatever. What coverage cannot supply is
tightness, because a level set that contains the nominal set may contain a
great deal else [rem:level_not_shape].

Tightness needs the OTHER direction, a lower bound of the form

    r(x)  >=  c * d(x, M_N)^p

for some c, p > 0. Without it a point arbitrarily far from nominal can carry
an arbitrarily small residual and be accepted, and no amount of calibration
repairs that: the fault is in the shape of the level set, not in its level.

HOW IT TESTS IT
---------------
Construct points that the operator itself considers reconstructible, by
decoding latent codes pushed progressively far outside the nominal latent
range, then compare their residual against their true distance to the nominal
sample. A residual that tracks distance rises; a residual that measures
distance to a larger ambient structure containing the nominal set stays flat.

The probe is decisive on a linear operator. Reconstruction error against a
principal subspace is exactly distance to that subspace, so a point moved
along a retained direction has residual zero however far from nominal it lies:
the accepted region is a slab around a 16-dimensional subspace rather than a
tube around a four-dimensional manifold. Whether a nonlinear operator escapes
this is not settled by its nonlinearity, since a ReLU network is piecewise
affine and extrapolates affinely; it is settled by running the probe.

Reporting `accept_ratio` and the residual growth makes the outcome a stated
adequacy criterion rather than an assumption, and any candidate residual can
be held to it before deployment.
"""

import numpy as np


def _pairwise_min_distance(A, B, block=256, exclude_self=False):
    """
    Distance from each row of A to the nearest row of B, blocked.

    `exclude_self` drops the trivial zero that appears when A is a subset of B,
    by taking the second smallest distance. Without it the nominal scale
    computed from a cloud against itself is identically zero, which silently
    disables the adequacy criterion.
    """
    A = np.asarray(A, dtype=np.float64)
    B = np.asarray(B, dtype=np.float64)
    out = np.empty(A.shape[0], dtype=np.float64)
    b_sq = (B * B).sum(1)
    for i in range(0, A.shape[0], block):
        chunk = A[i:i + block]
        d2 = (chunk * chunk).sum(1)[:, None] + b_sq[None, :] - 2.0 * chunk @ B.T
        np.maximum(d2, 0.0, out=d2)
        if exclude_self:
            part = np.partition(d2, 1, axis=1)[:, 1]
            out[i:i + block] = np.sqrt(part)
        else:
            out[i:i + block] = np.sqrt(d2.min(1))
    return out


def distance_proxy_probe(operator, X_nominal, tau, *, shifts=(0, 3, 10, 30, 100),
                         n_points=8, latent_dim_index=0, reference=None):
    """
    Push latent codes away from the nominal range and see whether the residual
    follows the distance.

    Parameters
    ----------
    operator : must expose `residual`, `encode` and `decode`.
    X_nominal : windows used as the reference cloud for the true distance.
    tau : the calibrated radius, used only to report acceptance.
    shifts : multiples of the per-dimension latent standard deviation.
    reference : optional distinct cloud for distance computation; defaults to
        `X_nominal`.

    Returns
    -------
    dict with the per-shift table and two summary numbers:
        accept_ratio  : fraction of probe points accepted; a residual that
                        tracks distance accepts only the near ones.
        max_accepted_distance : the largest true distance among accepted
                        points, in the units of the observation space. Compare
                        it against `nominal_scale` in the same dict.
    """
    X_nominal = np.asarray(X_nominal, dtype=np.float64)
    ref = X_nominal if reference is None else np.asarray(reference,
                                                         dtype=np.float64)

    Z = np.asarray(operator.encode(X_nominal), dtype=np.float64)
    mu, sd = Z.mean(0), Z.std(0)

    # Nearest-neighbour spacing within the nominal cloud, which sets the unit
    # in which "far from nominal" is judged. Self-matches are excluded when the
    # reference is the cloud itself, otherwise the scale collapses to zero.
    self_ref = reference is None
    nominal_scale = float(np.median(_pairwise_min_distance(
        X_nominal[: min(200, len(X_nominal))], ref, exclude_self=self_ref)))

    rows = []
    for m in shifts:
        Zq = np.tile(mu, (int(n_points), 1)).astype(np.float64)
        Zq[:, int(latent_dim_index)] += float(m) * sd[int(latent_dim_index)]
        Xq = np.asarray(operator.decode(Zq), dtype=np.float64)
        r = np.asarray(operator.residual(Xq), dtype=np.float64)
        d = _pairwise_min_distance(Xq, ref)
        rows.append({
            "shift_sd": float(m),
            "residual": float(np.median(r)),
            "distance": float(np.median(d)),
            "accepted": bool(np.median(r) <= tau),
        })

    accepted = [row for row in rows if row["accepted"]]
    return {
        "rows": rows,
        "tau": float(tau),
        "nominal_scale": nominal_scale,
        "accept_ratio": len(accepted) / len(rows),
        "max_accepted_distance": (max(a["distance"] for a in accepted)
                                  if accepted else 0.0),
        "residual_growth": (rows[-1]["residual"] / max(rows[0]["residual"],
                                                       1e-300)),
    }


def passes_distance_proxy(result, *, tolerance=3.0):
    """
    A residual passes if it accepts nothing far beyond the nominal scale.

    `tolerance` is expressed in multiples of the nominal nearest-neighbour
    scale, so the criterion is dimensionless and comparable across operators.
    A linear reconstruction residual fails by many orders of magnitude, which
    is what makes the criterion informative rather than decorative.
    """
    return result["max_accepted_distance"] <= tolerance * result["nominal_scale"]
