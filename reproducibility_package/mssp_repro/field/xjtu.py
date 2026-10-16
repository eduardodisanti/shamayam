"""
XJTU-SY run-to-failure archive: loading, ordering and caching.

WHAT THE ARCHIVE IS
-------------------
Fifteen LDK UER204 bearings run to failure on the XJTU-SY bench, five under
each of three operating conditions (authors' introduction, Tables 1-2):

    35Hz12kN    2100 rpm, 12 kN     Bearing1_1 ... Bearing1_5
    37.5Hz11kN  2250 rpm, 11 kN     Bearing2_1 ... Bearing2_5
    40Hz10kN    2400 rpm, 10 kN     Bearing3_1 ... Bearing3_5

One CSV per minute, named 1.csv, 2.csv, ... in acquisition order, each with a
header row and 32768 rows (1.28 s at 25.6 kHz); column 1 is the horizontal
and column 2 the vertical accelerometer (g). Each test was stopped when the
maximum amplitude of either channel exceeded ten times its normal-stage
maximum, so there are no inactive recordings after the failure (unlike IMS).

Chronology is the file number, never the modification time: `ordered_files`
refuses a folder whose names are not exactly 1..L.
"""

from pathlib import Path

import numpy as np

__all__ = ["XJTU_FS", "XJTU_SAMPLES", "XJTU_INTERVAL_MIN", "CONDITIONS",
           "BEARINGS", "FAULT_ELEMENT", "LIFE_RECORDS", "CHANNELS",
           "bearing_folder", "ordered_files", "load_bearing"]

XJTU_FS = 25_600
XJTU_SAMPLES = 32_768
XJTU_INTERVAL_MIN = 1.0
CONDITIONS = {"35Hz12kN": 35.0, "37.5Hz11kN": 37.5, "40Hz10kN": 40.0}
CHANNELS = ("H", "V")

BEARINGS = {f"{c}_{i}": cond
            for c, cond in ((1, "35Hz12kN"), (2, "37.5Hz11kN"), (3, "40Hz10kN"))
            for i in range(1, 6)}

# Authors' Table 2.
LIFE_RECORDS = {"1_1": 123, "1_2": 161, "1_3": 158, "1_4": 122, "1_5": 52,
                "2_1": 491, "2_2": 161, "2_3": 533, "2_4": 42, "2_5": 339,
                "3_1": 2538, "3_2": 2496, "3_3": 371, "3_4": 1515, "3_5": 114}
FAULT_ELEMENT = {"1_1": "outer race", "1_2": "outer race", "1_3": "outer race",
                 "1_4": "cage", "1_5": "inner race and outer race",
                 "2_1": "inner race", "2_2": "outer race", "2_3": "cage",
                 "2_4": "outer race", "2_5": "outer race",
                 "3_1": "outer race",
                 "3_2": "inner race, ball, cage and outer race",
                 "3_3": "inner race", "3_4": "inner race", "3_5": "outer race"}


def shaft_hz(bearing):
    return CONDITIONS[BEARINGS[bearing]]


def bearing_folder(root, bearing):
    return Path(root) / BEARINGS[bearing] / f"Bearing{bearing}"


def ordered_files(folder):
    files = [p for p in Path(folder).iterdir()
             if p.is_file() and not p.name.startswith(".")]
    try:
        idx = sorted(int(p.stem) for p in files if p.suffix == ".csv")
    except ValueError as e:
        raise ValueError(f"{folder}: a CSV name is not a record number") from e
    if len(idx) != len(files) or idx != list(range(1, len(idx) + 1)):
        raise ValueError(f"{folder}: records are not exactly 1..{len(idx)}.csv")
    return [Path(folder) / f"{i}.csv" for i in idx]


def _read_csv(path):
    try:
        import pandas as pd
        a = pd.read_csv(path, dtype=np.float32).to_numpy()
    except ImportError:
        a = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.float32)
    if a.shape != (XJTU_SAMPLES, 2):
        raise ValueError(f"{path}: shape {a.shape}, expected ({XJTU_SAMPLES}, 2)")
    return a


def load_bearing(root, bearing, *, cache_dir=None):
    """
    All recordings of one bearing in chronological order, as float32 of shape
    (L, 32768, 2) (channel 0 horizontal, 1 vertical). With `cache_dir`, the
    parsed array is kept as `<cache_dir>/xjtu_<bearing>_<L>.npy` and reused.
    """
    files = ordered_files(bearing_folder(root, bearing))
    if len(files) != LIFE_RECORDS[bearing]:
        raise ValueError(f"Bearing{bearing}: {len(files)} records, the authors "
                         f"list {LIFE_RECORDS[bearing]}")
    cache = (Path(cache_dir) / f"xjtu_{bearing}_{len(files)}.npy"
             if cache_dir else None)
    if cache is not None and cache.exists():
        return np.load(cache, mmap_mode="r")
    X = np.stack([_read_csv(p) for p in files])
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp.npy")
        np.save(tmp, X)
        tmp.rename(cache)
    return X
