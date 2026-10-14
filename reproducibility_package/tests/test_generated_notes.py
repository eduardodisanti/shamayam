"""
Every table in mssp_paper/notas is generated, and these tests hold it to that.

A table that was edited by hand, or that went stale after a code change,
fails here: each one is regenerated from its committed inputs and compared
byte for byte with the committed Markdown. The inputs are small committed
artefacts (residual caches, results.json), so no archive, no network and no
TensorFlow are needed.
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
NOTES = HERE.parent / "mssp_paper" / "notas"
sys.path.insert(0, str(HERE))

import cwru_projection_report                                    # noqa: E402
import ims_certified_recalibration as ims                        # noqa: E402
from mssp_repro.calibration import (tolerance_order_statistic,   # noqa: E402
                                    tolerance_rank)


# ------------------------------------------------------------- IMS

@pytest.fixture(scope="module")
def ims_results():
    return ims.run()


def test_ims_table_is_regenerated_exactly(ims_results):
    committed = (NOTES / "tablas_ims_certificado.md").read_text()
    assert ims.to_markdown(ims_results) == committed


# Published Table 10: radius and lead time per bearing.
PUBLISHED = {"1": (0.014150, 73.83), "2": (0.018596, 31.33),
             "3": (0.021798, 14.33), "4": (0.009729, 52.50)}


@pytest.mark.parametrize("bearing", sorted(PUBLISHED))
def test_published_arm_reproduces_table_10(ims_results, bearing):
    tau, lead = PUBLISHED[bearing]
    p = ims_results["bearings"][bearing]["published"]
    assert round(p["tau"], 6) == pytest.approx(tau, abs=5e-7)
    assert round(p["lead_hours"], 2) == pytest.approx(lead, abs=5e-3)


def test_failed_bearing_departure_does_not_depend_on_the_radius(ims_results):
    b = ims_results["bearings"][str(ims.FAILED_BEARING)]
    departures = {b["published"]["departure"]} | {
        b[label]["departure"] for label, _, _ in ims.ARMS}
    assert departures == {539}


# ------------------------------------------------------------- CWRU

def test_cwru_tables_are_regenerated_exactly():
    buf = io.StringIO()
    with redirect_stdout(buf):
        cwru_projection_report.main(HERE / "results" / "cwru_projection")
    committed = (NOTES / "tablas_cwru_proyeccion.md").read_text()
    assert buf.getvalue() == committed


# ------------------------------------------------------------- tolerance

def test_tolerance_rank_needs_149_at_098_095():
    assert tolerance_rank(148) is None
    assert tolerance_rank(149) == 149
    assert np.isnan(tolerance_order_statistic(np.arange(148.0)))


def test_tolerance_rank_is_minimal():
    from scipy.stats import binom
    for n in (149, 200, 500):
        k = tolerance_rank(n)
        assert binom.cdf(k - 1, n, 0.98) >= 0.95
        assert k == 1 or binom.cdf(k - 2, n, 0.98) < 0.95


def test_tolerance_radius_covers_with_stated_confidence():
    """Monte Carlo: the frozen radius covers >= 98% of the distribution in at
    least 95% of commissioning samples (exact coverage is uniform-free, so a
    uniform population suffices)."""
    rng = np.random.default_rng(0)
    n, reps = 200, 4000
    taus = np.array([tolerance_order_statistic(rng.random(n))
                     for _ in range(reps)])
    # for U(0,1) the coverage of a radius tau is tau itself
    assert np.mean(taus >= 0.98) >= 0.95 - 3 * np.sqrt(0.95 * 0.05 / reps)


# ------------------------------------------------------------- IMS learning curve

def test_ims_learning_curve_table_is_regenerated_exactly():
    import ims_learning_curve_report as lc
    res = HERE / "results" / "ims_quotient" / "learning_curve.json"
    if not res.exists():
        pytest.skip("learning-curve results not committed yet")
    import json
    committed = (NOTES / "tablas_ims_cociente.md").read_text()
    md = lc.to_markdown(json.loads(res.read_text()))
    seeds = res.parent / "seeds.json"
    if seeds.exists():
        md = md.rstrip("\n") + "\n" + lc.seeds_markdown(
            json.loads(res.read_text()), json.loads(seeds.read_text()))
    assert md == committed


# ------------------------------------------------------------- Ottawa

def test_ottawa_table_is_regenerated_exactly():
    import ottawa_report
    res = HERE / "results" / "ottawa" / "results.json"
    if not res.exists():
        pytest.skip("Ottawa results not committed yet")
    committed = (NOTES / "tablas_ottawa.md").read_text()
    assert ottawa_report.full_markdown() == committed


def test_ottawa_training_free_arms_reproduce_across_runs():
    """The seed-0 run was repeated. Arms without training (RMS, kurtosis)
    must agree exactly; trained arms are not bit-reproducible on CPU and are
    reported over seeds instead."""
    import json
    a = HERE / "results" / "ottawa" / "results.json"
    b = HERE / "results" / "ottawa" / "results_seed0.json"
    if not (a.exists() and b.exists()):
        pytest.skip("Ottawa runs not committed yet")
    A, B = json.loads(a.read_text()), json.loads(b.read_text())
    for sc in B["scenarios"]:
        for arm in ("rms_t", "kurt_q"):
            assert A["scenarios"][sc][arm] == B["scenarios"][sc][arm], (sc, arm)


# ------------------------------------------------------------- IMS classical, contamination

@pytest.mark.parametrize("res,note,fn", [
    ("ims_classical/results.json", "tablas_ims_clasicos.md", "classical_markdown"),
    ("contamination/results.json", "tablas_contaminacion.md", "contamination_markdown"),
    ("multispace/results.json", "tablas_multiespacio.md", "multispace_markdown")])
def test_extra_tables_are_regenerated_exactly(res, note, fn):
    import json
    import extra_reports
    path = HERE / "results" / res
    if not path.exists():
        pytest.skip(f"{res} not committed yet")
    md = getattr(extra_reports, fn)(json.loads(path.read_text()))
    assert md == (NOTES / note).read_text()


def test_contamination_tolerance_is_exactly_n_minus_k():
    """Up to n - k contaminated recordings the radius does not move and the
    fault is found with the clean lead time; one more and it moves."""
    import json
    path = HERE / "results" / "contamination" / "results.json"
    if not path.exists():
        pytest.skip("contamination results not committed yet")
    for rows in json.loads(path.read_text())["scores"].values():
        for r in rows:
            if r["m"] <= r["tolerates"]:
                assert r["lost"] == 0 and abs(r["inflation_median"] - 1) < 0.05
            if r["m"] == r["tolerates"] + 1:
                assert r["inflation_median"] > 1.5


# ------------------------------------------------------------- bench (CWRU -> IMS, Ottawa)

def _bench():
    import bench_report
    res = HERE / "results" / "bench"
    if not (res / "analysis.json").exists():
        pytest.skip("bench results not committed yet")
    return bench_report, res


def test_bench_table_is_regenerated_exactly():
    import json
    br, res = _bench()
    T, E, _, _ = br.load(res)
    A = json.loads((res / "analysis.json").read_text())
    assert br.to_markdown(T, E, A) == (NOTES / "tablas_banco.md").read_text()


@pytest.mark.slow
def test_bench_analysis_recomputes_exactly():
    """The record bootstrap behind the H1 verdict is deterministic and
    reproduces the committed analysis from the committed window scores."""
    import json
    br, res = _bench()
    _, _, W, ott = br.load(res)
    fresh = json.loads(json.dumps(br.analyse(W, ott)))
    assert fresh == json.loads((res / "analysis.json").read_text())
