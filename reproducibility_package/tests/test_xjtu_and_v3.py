"""
XJTU-SY (09_protocolo_xjtu.md), bench v3 (10_protocolo_banco_v3.md) and the
5-seed CWRU ablation: the pieces that can be checked without the archives,
and the generated tables, byte for byte, once their results are committed.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[1]
NOTES = HERE.parent / "mssp_paper" / "notas"
sys.path.insert(0, str(HERE))

from mssp_repro.field import xjtu                                # noqa: E402


# ------------------------------------------------------------- XJTU loader

def test_xjtu_constants_match_the_authors_table():
    assert sum(xjtu.LIFE_RECORDS.values()) == 9216
    assert len(xjtu.BEARINGS) == 15 and set(xjtu.FAULT_ELEMENT) == set(xjtu.BEARINGS)


def test_ordered_files_refuses_gaps_and_foreign_names(tmp_path):
    for i in (1, 2, 3):
        (tmp_path / f"{i}.csv").write_text("h,v\n")
    assert [p.name for p in xjtu.ordered_files(tmp_path)] == ["1.csv", "2.csv", "3.csv"]
    (tmp_path / "5.csv").write_text("h,v\n")
    with pytest.raises(ValueError):
        xjtu.ordered_files(tmp_path)
    (tmp_path / "5.csv").unlink()
    (tmp_path / "notes.txt").write_text("x")
    with pytest.raises(ValueError):
        xjtu.ordered_files(tmp_path)


def test_commissionable_bearings_are_as_registered():
    import xjtu_report as xr
    assert set(xr.commissionable(49)) == set(xjtu.BEARINGS) - {"1_5", "2_4"}
    assert xr.commissionable(99) == xr.commissionable(49)
    assert all(xr.band(b)[1] - xr.band(b)[0] >= 50 for b in xr.BAND_BEARINGS)


def test_union_radius_needs_99():
    import xjtu_report as xr
    s = np.random.default_rng(0).random(200)
    life = dict(xjtu.LIFE_RECORDS)
    xjtu.LIFE_RECORDS["1_1"] = 200
    try:
        with pytest.raises(ValueError):
            xr.evaluate_bearing({"H": s, "V": s}, "1_1", 49)
        xr.evaluate_bearing({"H": s, "V": s}, "1_1", 99)
    finally:
        xjtu.LIFE_RECORDS.update(life)


# ------------------------------------------------------------- v3 representation

def test_ses_is_gain_invariant_and_resolves_orders():
    import bench_transfer_v3 as v3
    rng = np.random.default_rng(1)
    t = np.arange(v3.WIN) / 400.0                       # revolutions
    x = rng.standard_normal(v3.WIN) * 0.1
    x[(np.floor(t * 7.0) != np.floor((t - 1 / 400.0) * 7.0))] += 5.0   # 7 impacts/rev
    a, b = v3.ses(x[None]), v3.ses(3.7 * x[None])
    assert a.shape == (1, 1200)
    np.testing.assert_allclose(a, b, atol=1e-4)
    k = 7 * v3.SEG_REVS - 1                             # bin of order 7
    assert a[0, k] > 3.0 and a[0, k] > a[0, k - 15] + 3.0


# ------------------------------------------------------------- generated tables

def test_xjtu_table_is_regenerated_exactly():
    import xjtu_report as xr
    if not (xr.RES / "report.json").exists():
        pytest.skip("XJTU results not committed yet")
    D = xr.load()
    A = json.loads(json.dumps(xr.analyse(D)))
    # Same numbers; scipy's Spearman p-values may differ in the last bits
    # across scipy versions, so floats are compared to 1e-9 relative.
    _assert_close(A, json.loads((xr.RES / "report.json").read_text()))
    assert xr.to_markdown(A, D) == (NOTES / "tablas_xjtu.md").read_text()


def _assert_close(a, b, path=""):
    if isinstance(a, dict):
        assert set(a) == set(b), path
        for k in a:
            _assert_close(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_close(x, y, f"{path}[{i}]")
    elif isinstance(a, float) and isinstance(b, float):
        assert a == pytest.approx(b, rel=1e-9, abs=1e-300), path
    else:
        assert a == b, path


def test_bench_v3_table_is_regenerated_exactly():
    import bench_report_v3 as br
    if not (br.RES / "evaluation.json").exists():
        pytest.skip("bench v3 results not committed yet")
    T, E, W = br.load()
    A = json.loads((br.RES / "analysis_v3.json").read_text())
    assert br.to_markdown(T, E, A) == (NOTES / "tablas_banco_v3.md").read_text()


def test_cwru_ablation_5seeds_table_is_regenerated_exactly():
    import cwru_ablation_5seeds_report as cr
    if not cr.RES.exists():
        pytest.skip("5-seed ablation not committed yet")
    assert cr.to_markdown(json.loads(cr.RES.read_text())) == cr.OUT.read_text()


def test_xjtu_discussion_tables_are_regenerated_exactly():
    import xjtu_discussion as xd
    if not (xd.RES / "report.json").exists():
        pytest.skip("XJTU results not committed yet")
    assert xd.to_markdown(*xd.load()) == xd.OUT.read_text()
