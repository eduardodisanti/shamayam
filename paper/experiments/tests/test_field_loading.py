"""
Layer B, stage 1: locating and reading the field archives.

Tests that need the archives carry `@pytest.mark.field` and skip cleanly when
they are absent, so a reader without the data sees skips rather than failures.
The path-resolution tests need no data and always run.

    python3 -m pytest tests/test_field_loading.py -q
    python3 -m pytest tests -q -m "not field and not slow"     # no archives
"""

from datetime import datetime

import numpy as np
import pytest

from mssp_repro.field import (CWRU_SPEEDS, IMS_CHANNELS, load_asset_windows,
                              load_bearing, load_experiment, load_signal,
                              make_windows, parse_ims_timestamp, resolve_ci)
from mssp_repro.field.paths import find_archive


# ---------------------------------------------------------------------
# Path resolution: the defect that would have broken every reader
#
# The notebooks open `../NASA_Bearing/IMS`; the directory is `NASA_bearing`.
# macOS does not care, Linux does, so the bug was invisible to every run the
# author made and fatal on the first machine belonging to anyone else.
# ---------------------------------------------------------------------

def test_resolution_ignores_case(tmp_path):
    (tmp_path / "NASA_bearing" / "IMS" / "2nd_test").mkdir(parents=True)
    for spelling in (("NASA_bearing", "IMS", "2nd_test"),
                     ("nasa_bearing", "ims", "2nd_test"),
                     ("NASA_BEARING", "IMS", "2ND_TEST"),
                     ("NASA_Bearing", "Ims", "2nd_Test")):
        got = resolve_ci(tmp_path, *spelling)
        assert got.name.lower() == "2nd_test"
        assert got.is_dir()


def test_resolution_error_names_what_is_present(tmp_path):
    """A bare 'no such file' is not actionable; the error should say what is
    there instead."""
    (tmp_path / "IMS").mkdir()
    with pytest.raises(FileNotFoundError, match="IMS"):
        resolve_ci(tmp_path, "nope")


def test_resolution_refuses_to_descend_into_a_file(tmp_path):
    (tmp_path / "notadir").write_text("x")
    with pytest.raises(NotADirectoryError):
        resolve_ci(tmp_path, "notadir", "deeper")


def test_find_archive_prefers_an_explicit_path(tmp_path):
    (tmp_path / "NASA_bearing").mkdir()
    assert find_archive("NASA_bearing", explicit=tmp_path / "NASA_bearing")
    assert find_archive("NASA_bearing", explicit=tmp_path / "absent") is None


def test_find_archive_looks_one_level_into_siblings(tmp_path):
    """
    The archives live beside the paper repository, not inside it, so the
    common ancestor is reached before either and an ancestors-only search
    would never find them.
    """
    (tmp_path / "sibling_repo" / "NASA_bearing").mkdir(parents=True)
    (tmp_path / "paper_repo" / "deep" / "pkg").mkdir(parents=True)
    found = find_archive("NASA_bearing",
                         search_from=tmp_path / "paper_repo" / "deep" / "pkg")
    assert found is not None and found.name == "NASA_bearing"


# ---------------------------------------------------------------------
# Windowing
# ---------------------------------------------------------------------

def test_make_windows_is_contiguous_and_exact():
    x = np.arange(20480, dtype=float)
    w = make_windows(x, win=1200, step=1200)
    assert w.shape == (17, 1200), "IMS recordings must give 17 windows"
    assert np.array_equal(w[0], x[:1200])
    assert np.array_equal(w[-1], x[16 * 1200:17 * 1200])


def test_make_windows_rejects_a_signal_too_short_to_window():
    with pytest.raises(ValueError, match="no complete window"):
        make_windows(np.zeros(100), win=1200, step=1200)


def test_seventeen_windows_is_the_number_the_aggregation_argument_uses():
    """
    Cross-check against `dynamics.recording_score`: the decision to aggregate
    by the mean rests on there being 17 windows per recording, which puts a
    95th percentile below the feasibility floor. If the windowing ever
    changes, that argument must be revisited, so the two are pinned together.
    """
    from mssp_repro import k_alpha, is_feasible
    n = make_windows(np.zeros(20480), win=1200, step=1200).shape[0]
    assert n == 17
    assert not is_feasible(n, 0.05)
    assert k_alpha(n, 0.05) > n


# ---------------------------------------------------------------------
# Timestamps and chronology
# ---------------------------------------------------------------------

def test_timestamp_is_parsed_from_the_filename(tmp_path):
    p = tmp_path / "2004.02.12.10.32.39"
    p.write_text("")
    assert parse_ims_timestamp(p) == datetime(2004, 2, 12, 10, 32, 39)


def test_unparseable_filenames_are_refused_rather_than_ordered_by_mtime(tmp_path):
    """
    The notebook falls back to modification time. That is the extraction
    order, not the acquisition order, and every lead time computed from it
    would be meaningless. Failing loudly is the only safe behaviour.
    """
    folder = tmp_path / "2nd_test"
    folder.mkdir()
    (folder / "2004.02.12.10.32.39").write_text("0 0 0 0")
    (folder / "recording_017.txt").write_text("0 0 0 0")
    with pytest.raises(ValueError, match="meaningless"):
        load_experiment(tmp_path, 2)


# ---------------------------------------------------------------------
# The archives themselves
# ---------------------------------------------------------------------

@pytest.mark.field
def test_ims_experiment_two_has_the_documented_shape(ims_root):
    signals, timestamps, files = load_experiment(ims_root, 2, max_recordings=6)
    assert signals.shape[1:] == (20480, 4), (
        "IMS Experiment 2 is 20480 samples by 4 channels, one per bearing")
    assert signals.dtype == np.float32
    assert len(timestamps) == len(files) == signals.shape[0]


@pytest.mark.field
def test_ims_recordings_are_in_acquisition_order(ims_root):
    _, timestamps, _ = load_experiment(ims_root, 2, max_recordings=12)
    assert list(timestamps) == sorted(timestamps)
    gaps = {(b - a).total_seconds() for a, b in zip(timestamps, timestamps[1:])}
    assert gaps == {600.0}, f"expected a 10-minute cadence, saw {gaps}"


@pytest.mark.field
def test_load_bearing_is_a_view_of_load_experiment(ims_root):
    """The one-pass loader must agree exactly with the per-bearing view; this
    is what licenses reading the archive once instead of four times."""
    signals, _, _ = load_experiment(ims_root, 2, max_recordings=4)
    for bearing, (column,) in IMS_CHANNELS[2].items():
        one, _, _ = load_bearing(ims_root, 2, bearing, max_recordings=4)
        assert np.array_equal(one, signals[:, :, column])


@pytest.mark.field
def test_ims_cache_round_trips(ims_root, tmp_path):
    a, _, _ = load_experiment(ims_root, 2, max_recordings=4, cache_dir=tmp_path)
    assert list(tmp_path.glob("*.npy")), "no cache written"
    b, _, _ = load_experiment(ims_root, 2, max_recordings=4, cache_dir=tmp_path)
    assert np.array_equal(a, b)


@pytest.mark.field
def test_cwru_gives_four_regimes_per_speed(cwru_root):
    windows = load_asset_windows(cwru_root / "Data", "1730")
    assert set(windows) == {"healthy", "ball", "inner_race", "outer_race"}
    for regime, w in windows.items():
        assert w.ndim >= 2 and w.shape[1] == 1200, regime
        assert w.shape[0] > 100, f"{regime} has only {w.shape[0]} windows"


@pytest.mark.field
def test_cwru_healthy_record_at_1797_is_half_the_others(cwru_root):
    """
    Not a defect, but a fact worth pinning: the healthy record at 1797 RPM is
    about half the length of the other three, so that speed commissions its
    radius from half the nominal data. Any per-speed comparison has to carry
    this, and a silent change to the archive would otherwise go unnoticed.
    """
    counts = {s: load_asset_windows(cwru_root / "Data", s)["healthy"].shape[0]
              for s in CWRU_SPEEDS}
    assert counts["1797"] < 0.6 * max(counts[s] for s in ("1730", "1750", "1772"))


@pytest.mark.field
def test_cwru_fault_regimes_concatenate_defect_sizes(cwru_root):
    """A fault regime is the union of every available defect size, so it is
    longer than any single acquisition. Stated as a test because it is a
    modelling decision inherited from the notebook, not an obvious default."""
    root = cwru_root / "Data"
    healthy = load_signal(root, "1730", "healthy")
    outer = load_signal(root, "1730", "outer_race")
    assert outer.size > healthy.size
