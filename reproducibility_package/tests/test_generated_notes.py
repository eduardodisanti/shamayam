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
