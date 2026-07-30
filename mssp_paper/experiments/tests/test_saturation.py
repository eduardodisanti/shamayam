"""
The saturation radius of Section 5.

Checks the three claims that have empirical content: consistency of the
estimator [prop:radius_consistency], certification of the radius
[cor:saturation_certification], and the predicted SIGN of the plug-in bias
[rem:plugin_centroid]. Finiteness [cor:finite_radius] is an analytic
consequence of compactness and is checked only as a sanity condition.
"""

import numpy as np
import pytest

from mssp_repro import (RadialProjector, degenerate_range, empirical_radius,
                        minimum_commissioning_length, population_radius,
                        radial_distances)
from mssp_repro.bearing_simulator import CWRU_PARAMS, BearingSignalSimulator

P = 0.98
ALPHA = 1.0 - P


def _windows(sim, regime, n, seed):
    np.random.seed(seed)
    return np.stack([sim.sample(regime=regime) for _ in range(n)])


@pytest.fixture(scope="module")
def geometry():
    sim = BearingSignalSimulator(CWRU_PARAMS)
    proj = RadialProjector(n_components=2).fit(_windows(sim, "healthy", 600, 11))
    D_pool = proj.distances(_windows(sim, "healthy", 3000, 12))
    D_eval = proj.distances(_windows(sim, "healthy", 3000, 13))
    return sim, proj, D_pool, D_eval


def test_radius_is_finite_and_positive(geometry):
    """[cor:finite_radius]: compactness makes every quantile finite."""
    _, _, D_pool, _ = geometry
    r = empirical_radius(D_pool, p=P, certified=True)
    assert np.isfinite(r) and r > 0
    assert np.isfinite(D_pool).all()


def test_estimator_converges_towards_the_population_radius(geometry):
    """
    [prop:radius_consistency] in its testable form: the bias of the estimator
    shrinks as n grows. Evaluated outside the degenerate range, where the
    estimator is an interior order statistic; inside that range the certified
    radius is the sample maximum and behaves differently by construction
    (see the dedicated test below).
    """
    _, _, D_pool, D_eval = geometry
    rng = np.random.default_rng(0)
    R_pop = population_radius(D_eval, p=P)

    def mean_abs_bias(n, reps=120):
        vals = [empirical_radius(D_pool[rng.choice(len(D_pool), n, replace=False)],
                                 p=P, certified=True) for _ in range(reps)]
        return abs(np.mean(vals) - R_pop) / R_pop

    b_small, b_large = mean_abs_bias(150), mean_abs_bias(1500)
    assert b_large < b_small, (b_small, b_large)
    assert b_large < 0.02


def test_dispersion_shrinks_with_sample_size(geometry):
    """The other half of consistency: the spread must contract."""
    _, _, D_pool, _ = geometry
    rng = np.random.default_rng(1)

    def sd(n, reps=150):
        return float(np.std([
            empirical_radius(D_pool[rng.choice(len(D_pool), n, replace=False)],
                             p=P, certified=True) for _ in range(reps)]))

    assert sd(1500) < sd(300) < sd(120)


def test_certified_radius_attains_target_coverage(geometry):
    """
    [cor:saturation_certification]: coverage on held-out nominal windows must
    reach p. Averaged over calibration draws, which is the marginal statement
    the corollary makes.
    """
    _, _, D_pool, D_eval = geometry
    rng = np.random.default_rng(2)
    for n in (99, 300, 800):
        cov = np.mean([
            np.mean(D_eval <= empirical_radius(
                D_pool[rng.choice(len(D_pool), n, replace=False)],
                p=P, certified=True))
            for _ in range(150)])
        assert cov >= P - 0.005, (n, cov)


def test_interpolated_radius_undercovers(geometry):
    """
    [rem:interpolation_bias] transferred to radii: the interpolated quantile
    covers strictly less than the certified order statistic.
    """
    _, _, D_pool, D_eval = geometry
    rng = np.random.default_rng(3)
    cov_c, cov_i = [], []
    for _ in range(200):
        d = D_pool[rng.choice(len(D_pool), 300, replace=False)]
        cov_c.append(np.mean(D_eval <= empirical_radius(d, p=P, certified=True)))
        cov_i.append(np.mean(D_eval <= empirical_radius(d, p=P, certified=False)))
    assert np.mean(cov_i) < np.mean(cov_c)


def test_certified_radius_is_the_sample_maximum_inside_the_degenerate_range(geometry):
    """[cor:degenerate_range] holds for radii exactly as it does for residuals."""
    _, _, D_pool, _ = geometry
    rng = np.random.default_rng(4)
    lo, hi = degenerate_range(ALPHA)
    for n in (lo, (lo + hi) // 2, hi):
        d = D_pool[rng.choice(len(D_pool), n, replace=False)]
        assert empirical_radius(d, p=P, certified=True) == pytest.approx(d.max())


def test_radius_rises_with_n_inside_the_degenerate_range(geometry):
    """
    A saturation curve computed with the certified estimator CANNOT flatten
    inside the degenerate range: the estimator is the sample maximum, which
    increases stochastically with n. Apparent flattening there would be an
    artefact of a different estimator, not evidence about the regime.
    """
    _, _, D_pool, _ = geometry
    rng = np.random.default_rng(5)
    lo, hi = degenerate_range(ALPHA)

    def mean_radius(n, reps=200):
        return float(np.mean([
            empirical_radius(D_pool[rng.choice(len(D_pool), n, replace=False)],
                             p=P, certified=True) for _ in range(reps)]))

    assert mean_radius(lo) < mean_radius(hi)


def test_plugin_reference_shrinks_the_radius(geometry):
    """
    [rem:plugin_centroid], predicted sign: fitting the projection and the
    reference on the same sample places that sample closer to its own centre
    and its own principal subspace, so the radius is biased downward.
    """
    sim, proj, _, _ = geometry
    rng = np.random.default_rng(6)
    X = _windows(sim, "healthy", 2400, 14)
    split, plug = [], []
    for _ in range(40):
        Xn = X[rng.choice(len(X), 300, replace=False)]
        split.append(empirical_radius(proj.distances(Xn), p=P, certified=True))
        plug.append(empirical_radius(
            radial_distances(Xn, mode="plugin", n_components=2),
            p=P, certified=True))
    assert np.mean(plug) < np.mean(split)


def test_below_the_floor_no_radius_is_certified(geometry):
    _, _, D_pool, _ = geometry
    n = minimum_commissioning_length(ALPHA) - 1
    assert np.isnan(empirical_radius(D_pool[:n], p=P, certified=True))


def test_projector_is_deterministic_and_validates_input(geometry):
    sim, proj, _, _ = geometry
    X = _windows(sim, "healthy", 40, 15)
    assert np.array_equal(proj.distances(X), proj.distances(X))
    with pytest.raises(ValueError):
        proj.distances(np.zeros((3, 7)))
    with pytest.raises(ValueError):
        radial_distances(X, mode="nonsense")
    with pytest.raises(ValueError):
        radial_distances(X, mode="split", reference=None)
