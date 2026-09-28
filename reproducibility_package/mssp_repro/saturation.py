"""
The saturation radius of Section 5.

The companion work measures blueprint saturation as the stabilization of a
p95/p98 manifold radius computed in a low-dimensional projection. Section 5
makes that precise: the radius is the p-quantile of the radial variable

    D = d(phi(x), c)

where phi is a representation map and c a reference point, and saturation is
the statement that its empirical estimator converges to the population
quantile R_p. This module supplies the estimator.

TWO FITTING MODES, AND WHY THE DISTINCTION MATTERS
--------------------------------------------------
The plug-in remark [rem:plugin_centroid] observes that estimating the
reference point, and the projection in which distances are measured, from the
SAME sample used to compute the radius destroys the exchangeability on which
the certification rests. Both modes are implemented here so the size of that
effect can be measured rather than assumed:

    mode="split"    projection and reference fitted on a disjoint nominal
                    block; exchangeability holds; the certification of
                    [cor:saturation_certification] applies.
    mode="plugin"   projection and reference fitted on the same sample whose
                    radius is being computed; matches common practice and the
                    companion work; expected to bias the radius DOWNWARD,
                    because a sample lies closer to its own centroid and its
                    own principal subspace than a fresh observation does.

The predicted sign of the plug-in bias is a falsifiable claim and is asserted
in tests/test_saturation.py.
"""

import numpy as np
from sklearn.decomposition import PCA

from .calibration import certified_order_statistic, interpolated_quantile


class RadialProjector:
    """
    Maps observation windows to radial distances in a low-dimensional
    projection of representation space.

    Parameters
    ----------
    n_components : int
        Dimension of the projection. The companion work uses 2; the default
        here matches it so the diagnostic is comparable.
    """

    def __init__(self, n_components=2, random_state=0, svd_solver="randomized"):
        self.n_components = int(n_components)
        self.random_state = int(random_state)
        # "randomized" with a fixed random_state is deterministic and is far
        # cheaper than a full SVD when the window length greatly exceeds the
        # number of retained components, which is the regime here (1200
        # features, 2 components). The plug-in study refits the projection
        # thousands of times, so the choice is what keeps the package fast;
        # tests/test_saturation.py pins determinism.
        self.svd_solver = svd_solver
        self._pca = None
        self._centre = None
        self._n_features = None

    def fit(self, X_reference):
        """Fit the projection and the reference point on nominal windows."""
        X = np.asarray(X_reference, dtype=np.float64)
        if X.ndim != 2:
            raise ValueError("expected a 2-D array of windows")
        self._n_features = X.shape[1]
        self._pca = PCA(
            n_components=min(self.n_components, *X.shape),
            svd_solver=self.svd_solver,
            random_state=self.random_state,
        ).fit(X)
        self._centre = self._pca.transform(X).mean(axis=0)
        return self

    def distances(self, X):
        """Euclidean distance to the reference point, in the projection."""
        if self._pca is None:
            raise RuntimeError("projector not fitted")
        X = np.asarray(X, dtype=np.float64)
        if X.ndim != 2 or X.shape[1] != self._n_features:
            raise ValueError("feature dimension mismatch")
        Z = self._pca.transform(X)
        return np.linalg.norm(Z - self._centre, axis=1)


def radial_distances(X, *, mode="split", reference=None, n_components=2):
    """
    Radial distances for a block of windows.

    mode="split"  : `reference` must be a disjoint block of nominal windows.
    mode="plugin" : the projection and reference are fitted on `X` itself.
    """
    if mode == "split":
        if reference is None:
            raise ValueError("mode='split' requires a reference block")
        proj = RadialProjector(n_components=n_components).fit(reference)
    elif mode == "plugin":
        proj = RadialProjector(n_components=n_components).fit(X)
    else:
        raise ValueError("mode must be 'split' or 'plugin'")
    return proj.distances(X)


def empirical_radius(distances, *, p=0.98, certified=True):
    """
    The empirical p-radius.

    certified=True  uses the order statistic of
                    [cor:saturation_certification], returning NaN below the
                    commissioning floor, so an uncertifiable radius is never
                    silently produced.
    certified=False uses the interpolated empirical quantile, matching common
                    practice; anti-conservative by
                    [rem:interpolation_bias].
    """
    d = np.asarray(distances, dtype=np.float64)
    if certified:
        return certified_order_statistic(d, alpha=1.0 - p)
    return interpolated_quantile(d, percentile=100.0 * p)


def population_radius(distances_large, *, p=0.98):
    """
    Reference value of R_p, estimated from a large nominal sample.

    Used as the target that the saturation curve is claimed to approach. It is
    itself an estimate, so it is quoted with its own sampling error where it
    matters; the interpolated quantile is used deliberately, since at large n
    the interpolation gap is negligible and the estimator is smoother.
    """
    return interpolated_quantile(distances_large, percentile=100.0 * p)
