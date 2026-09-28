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


# ---------------------------------------------------------------------
# How coverage is MEASURED, not only what it is
#
# The two tests below exist because of a real defect, not a hypothetical one.
# `experiment_saturation` originally evaluated coverage against one fixed
# block of nominal windows, computed once outside the repetition loop. That
# measures coverage against the empirical distribution function of a single
# sample rather than against the distribution, and the resulting offset --
# order sqrt(p(1-p)/M) -- does not average away over repetitions, because the
# same block is reused every time. At M=4000 and p=0.98 it is about 0.002,
# which is the same order as the excess coverage being reported: large enough
# to put the certified radius visibly below its own target in the published
# figure, and so to appear to refute the guarantee it was drawn to confirm.
#
# Every test in this file passed while that was true, because they all tested
# the estimator and none tested the measurement.
# ---------------------------------------------------------------------

def _coverage(rng, D, n, m, reps, fixed_eval):
    """Mean coverage over `reps` draws, with the evaluation block either held
    fixed across repetitions or redrawn disjointly on each one."""
    ev = D[rng.choice(len(D), size=m, replace=False)] if fixed_eval else None
    out = []
    for _ in range(reps):
        idx = rng.choice(len(D), size=n + m, replace=False)
        r = empirical_radius(D[idx[:n]], p=P, certified=True)
        block = ev if fixed_eval else D[idx[n:]]
        out.append(np.mean(block <= r))
    return float(np.mean(out)), float(np.std(out, ddof=1) / np.sqrt(reps))


@pytest.mark.parametrize("n", [99, 300])
def test_resampled_evaluation_recovers_the_exact_coverage(n):
    """
    [prop:coverage] holds as an EQUALITY, and the measurement must be able to
    see that. Drawing the calibration and evaluation points jointly without
    replacement from one pool makes any n+1 of them exchangeable, which is the
    proposition's only hypothesis, so the estimate is unbiased for
    k_alpha/(n+1) -- exactly, not asymptotically.
    """
    from mssp_repro import k_alpha
    rng = np.random.default_rng(4)
    D = rng.lognormal(size=8000)
    got, se = _coverage(rng, D, n, m=300, reps=1500, fixed_eval=False)
    exact = k_alpha(n, ALPHA) / (n + 1)
    assert abs(got - exact) < 4.0 * se, (
        f"n={n}: coverage {got:.5f} differs from the exact {exact:.5f} "
        f"by {abs(got-exact)/se:.1f} standard errors")


def test_a_fixed_evaluation_block_biases_the_measurement():
    """
    The failure mode itself, pinned so it cannot return unnoticed. Holding the
    evaluation block fixed leaves an offset that persists no matter how many
    repetitions are averaged; resampling removes it. The test asserts the
    RELATIVE ordering, which is the robust claim -- the sign of the fixed-block
    offset depends on the particular block drawn, its magnitude does not.
    """
    from mssp_repro import k_alpha
    n, m, reps = 300, 300, 1500
    exact = k_alpha(n, ALPHA) / (n + 1)

    fixed_err, fresh_err = [], []
    for seed in range(6):
        rng = np.random.default_rng(100 + seed)
        D = rng.lognormal(size=8000)
        fixed_err.append(abs(_coverage(rng, D, n, m, reps, True)[0] - exact))
        rng = np.random.default_rng(100 + seed)
        D = rng.lognormal(size=8000)
        fresh_err.append(abs(_coverage(rng, D, n, m, reps, False)[0] - exact))

    assert np.mean(fresh_err) < np.mean(fixed_err), (
        f"resampling the evaluation block did not reduce the departure from "
        f"the exact coverage: fixed {np.mean(fixed_err):.5f}, "
        f"fresh {np.mean(fresh_err):.5f}")
