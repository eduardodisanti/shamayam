"""
A linear-subspace representation operator, retained as a NEGATIVE CONTROL.

WHAT THIS OPERATOR IS FOR
-------------------------
Reconstruction error against a principal subspace is a legitimate residual for
the purposes of the calibration theory: the residual-proxy assumption
[ass:residual_proxy] asks only that the score be usable, and the coverage
result of Section 7 holds for any scalar whatever. Using this operator
therefore demonstrates that the calibration is genuinely operator-independent,
which is worth demonstrating.

It is NOT adequate for demonstrating the membership geometry, and the package
keeps it precisely in order to show why. Reconstruction error against a
16-dimensional subspace is exactly distance to that subspace, so a point moved
along a retained direction has residual zero however far from the nominal
manifold it lies. The accepted region is a slab around a 16-dimensional
subspace rather than a tube around a four-dimensional manifold, and the
distance-proxy probe in `probes.py` measures the consequence directly: this
operator accepts points some four hundred times the nominal nearest-neighbour
spacing, with residuals of order 1e-30.

The operator used for the geometry demonstrations is the Conv1D autoencoder of
the technical note, in `conv_autoencoder.py`, which passes the probe at 1.5
times the nominal spacing. Its convolutional structure is not incidental:
translation equivariance matches the phase-shift nuisance that the quotient
construction removes [rem:nuisance_on_attractor].

Keeping both makes the adequacy criterion informative rather than decorative.
A residual is not adequate merely because it yields good detection rates on
the faults one happens to have: this operator detects the simulator faults at
79-100% and still fails the probe, because those faults lie off the retained
subspace while the probe points do not.
"""

import numpy as np
from sklearn.decomposition import PCA


class PCAResidualOperator:
    """
    Linear-subspace representation operator with reconstruction-error residual.

    Trained on nominal observations only, mirroring the constraint imposed on
    the autoencoder in the paper: no non-nominal sample is used at any stage
    of representation learning.
    """

    def __init__(self, n_components=16, random_state=0):
        self.n_components = int(n_components)
        self.random_state = int(random_state)
        self._pca = None
        self._n_features = None

    def fit(self, X_nominal):
        """X_nominal : (n_samples, n_features), nominal windows only."""
        X = np.asarray(X_nominal, dtype=np.float64)
        if X.ndim != 2:
            raise ValueError("expected a 2-D array of windows")
        self._n_features = X.shape[1]
        self._pca = PCA(
            n_components=min(self.n_components, *X.shape),
            svd_solver="full",              # deterministic
            random_state=self.random_state,
        ).fit(X)
        return self

    def residual(self, X):
        """Mean squared reconstruction error per window."""
        if self._pca is None:
            raise RuntimeError("operator not fitted")
        X = np.asarray(X, dtype=np.float64)
        if X.ndim != 2 or X.shape[1] != self._n_features:
            raise ValueError("feature dimension mismatch")
        recon = self._pca.inverse_transform(self._pca.transform(X))
        return np.mean((X - recon) ** 2, axis=1)
