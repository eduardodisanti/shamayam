"""
NASA IMS run-to-failure archive: loading and windowing.

Ported from `bearing_autoencoder_NASA_per_asset.ipynb`. Two departures from
the notebook are deliberate and are marked below; everything else is intended
to be behaviourally identical, and `tests/test_field_ims.py` checks the pieces
that can be checked without the archive.

WHAT THE ARCHIVE IS
-------------------
IMS Experiment 2 is 984 chronological recordings taken every ten minutes over
164 hours, from four bearings on one shaft running to failure. Each file is
whitespace-delimited ASCII of shape (20480, 4): 1.02 seconds at 20 kHz, one
column per bearing. The filename is the timestamp, `YYYY.MM.DD.HH.MM.SS`.

DEPARTURE 1: one pass, not four.
The notebook calls its loader once per bearing, so it reads all 984 files four
times and keeps one column each time. Reading is not free -- roughly seven
seconds a pass -- and more importantly the four bearings are then loaded under
four separate traversals whose file ordering is established independently.
`load_experiment` reads each file once and returns all four channels, so the
chronology is established exactly once and shared. `load_bearing` is kept as
the single-channel view for callers that want it.

DEPARTURE 2: paths are resolved case-insensitively (see `paths.py`).
"""

from datetime import datetime
from pathlib import Path

import numpy as np

from .paths import resolve_ci

__all__ = ["IMS_CHANNELS", "IMS_SAMPLE_RATE_HZ", "IMS_RECORDING_INTERVAL_HOURS",
           "parse_ims_timestamp", "load_experiment", "load_bearing",
           "make_windows"]

# Column of the recording matrix carrying each bearing. Experiment 1 has two
# accelerometers per bearing; experiments 2 and 3 have one.
IMS_CHANNELS = {
    1: {1: (0, 1), 2: (2, 3), 3: (4, 5), 4: (6, 7)},
    2: {1: (0,), 2: (1,), 3: (2,), 4: (3,)},
    3: {1: (0,), 2: (1,), 3: (2,), 4: (3,)},
}

IMS_EXPERIMENT_FOLDERS = {1: "1st_test", 2: "2nd_test", 3: "3rd_test"}

IMS_SAMPLE_RATE_HZ = 20_000
IMS_RECORDING_INTERVAL_HOURS = 10.0 / 60.0     # one recording every 10 minutes


def parse_ims_timestamp(path):
    """
    Timestamp of an IMS recording, taken from its filename.

    The fallback to file mtime is inherited from the notebook. It is a trap
    worth naming: mtime is set by whoever unpacked the archive, so if it ever
    fires the chronology is the extraction order rather than the acquisition
    order, and every lead time computed downstream is meaningless. Callers
    should use `load_experiment`, which refuses to guess (see below).
    """
    try:
        return datetime.strptime(Path(path).name, "%Y.%m.%d.%H.%M.%S")
    except ValueError:
        return datetime.fromtimestamp(Path(path).stat().st_mtime)


def _ordered_files(folder):
    files = [p for p in Path(folder).iterdir()
             if p.is_file() and not p.name.startswith(".")]
    if not files:
        raise FileNotFoundError(f"no IMS recording files in {folder}")

    # Refuse the mtime fallback rather than silently ordering by extraction
    # time. Chronology is the whole content of a run-to-failure experiment.
    unparseable = []
    for p in files:
        try:
            datetime.strptime(p.name, "%Y.%m.%d.%H.%M.%S")
        except ValueError:
            unparseable.append(p.name)
    if unparseable:
        raise ValueError(
            f"{len(unparseable)} file(s) in {folder} do not carry a parseable "
            f"IMS timestamp, e.g. {unparseable[:3]}. Ordering would fall back "
            "to modification time, which reflects when the archive was "
            "unpacked rather than when the data was acquired, and every lead "
            "time derived from it would be meaningless.")

    return sorted(files, key=lambda p: datetime.strptime(
        p.name, "%Y.%m.%d.%H.%M.%S"))


def load_experiment(data_root, experiment_id=2, *, cache_dir=None,
                    max_recordings=None):
    """
    Load one IMS experiment in chronological order, all channels at once.

    Returns `(signals, timestamps, files)` with `signals` of shape
    `(n_recordings, n_samples, n_channels)` in float32.

    `cache_dir` writes a `.npy` beside the parsed result and reuses it when the
    file count and the first and last filenames agree. Parsing the ASCII takes
    about seven seconds; the cache matters less for one pass than for the
    repeated runs a reader doing Layer B will make.
    """
    folder = resolve_ci(data_root, IMS_EXPERIMENT_FOLDERS[experiment_id])
    files = _ordered_files(folder)
    if max_recordings is not None:
        files = files[:int(max_recordings)]

    tag = f"ims_exp{experiment_id}_{len(files)}_{files[0].name}_{files[-1].name}"
    cache = Path(cache_dir) / f"{tag}.npy" if cache_dir else None
    if cache is not None and cache.exists():
        signals = np.load(cache)
    else:
        rows = []
        expected = None
        for p in files:
            rec = np.loadtxt(p)
            if rec.ndim == 1:
                rec = rec[:, None]
            if expected is None:
                expected = rec.shape
            elif rec.shape != expected:
                raise ValueError(
                    f"inconsistent recording shape in {p.name}: expected "
                    f"{expected}, found {rec.shape}")
            rows.append(rec.astype(np.float32))
        signals = np.stack(rows)
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache, signals)

    timestamps = np.asarray([parse_ims_timestamp(p) for p in files])
    return signals, timestamps, files


def load_bearing(data_root, experiment_id=2, bearing_id=1, *, sensor_index=0,
                 **kw):
    """
    One bearing's channel, as `(signals, timestamps, files)` with `signals` of
    shape `(n_recordings, n_samples)`. Thin view over `load_experiment`.
    """
    channels = IMS_CHANNELS[experiment_id]
    if bearing_id not in channels:
        raise ValueError(f"bearing_id must be one of {tuple(channels)}, "
                         f"received {bearing_id}")
    chans = channels[bearing_id]
    if not 0 <= sensor_index < len(chans):
        raise ValueError(
            f"experiment {experiment_id}, bearing {bearing_id} has "
            f"{len(chans)} channel(s); received sensor_index={sensor_index}")

    signals, timestamps, files = load_experiment(data_root, experiment_id, **kw)
    column = chans[sensor_index]
    if column >= signals.shape[2]:
        raise ValueError(
            f"recordings carry {signals.shape[2]} channels, but channel "
            f"{column} was requested for bearing {bearing_id}")
    return signals[:, :, column], timestamps, files


def make_windows(x, win=1200, step=1200):
    """
    Contiguous windows of a 1-D signal, transcribed from the notebook.

    At the IMS length this yields 17 windows of 1200 samples per recording,
    the count that decides the aggregation argument in `dynamics.py`: a 95th
    percentile of 17 values is the sample maximum, and is not feasible
    distribution-free at all.
    """
    x = np.asarray(x)
    n = (len(x) - win) // step + 1
    if n <= 0:
        raise ValueError(
            f"signal of length {len(x)} contains no complete window of "
            f"{win} samples")
    return np.stack([x[i * step:i * step + win] for i in range(n)], axis=0)
