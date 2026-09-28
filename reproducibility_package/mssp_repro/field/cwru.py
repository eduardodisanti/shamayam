"""
Case Western Reserve University bearing archive: loading and windowing.

Ported from `bearing_autoencoder_cwru_per_asset.ipynb`.

WHAT THE ARCHIVE IS
-------------------
The NumPy redistribution of the CWRU dataset, organised by shaft speed: four
folders, "1730 RPM" through "1797 RPM", each holding `.npz` files with three
accelerometer channels -- `DE` (drive end), `FE` (fan end) and `BA` (base).
Only `DE` is used, as in the notebook.

Filenames encode the condition: `1797_Normal.npz` for healthy, and for faults
`{rpm}_{type}_{size}_{sensor}.npz`, where type is `B` (ball), `IR` (inner
race) or `OR@{clock}` (outer race, with the defect's clock position), size is
the defect diameter in thousandths of an inch, and sensor identifies the
acquisition. The published experiments use only the `DE12` acquisitions, and
concatenate every defect size available for a given fault type.

That concatenation is worth naming, because it is a modelling decision rather
than a detail: a "ball fault" regime here is the union of 7, 14, 21 and
28-thousandth defects, so the regime is a family of severities rather than one
condition. Section 8 of the paper treats each speed as a separate operating
regime, and the fault families within a speed as the classes to be detected.
"""

from pathlib import Path

import numpy as np

from .paths import resolve_ci

__all__ = ["CWRU_SPEEDS", "CWRU_REGIMES", "CWRU_SAMPLE_RATE_HZ",
           "load_signal", "load_asset_windows"]

CWRU_SPEEDS = ("1730", "1750", "1772", "1797")

# Glob patterns per regime, transcribed from the notebook. `healthy` is a
# single file; the fault regimes concatenate every matching defect size.
CWRU_REGIMES = {
    "healthy": None,
    "ball": "{rpm}_B_*_DE12.npz",
    "inner_race": "{rpm}_IR_*_DE12.npz",
    "outer_race": "{rpm}_OR*@*_DE12.npz",
}

CWRU_SAMPLE_RATE_HZ = 12_000     # the DE12 acquisitions


def load_signal(data_root, speed, regime, *, channel="DE"):
    """
    One regime of one speed, as a 1-D float array.

    `data_root` is the `Data` directory of the archive. Fault regimes
    concatenate every matching defect size in sorted filename order, which is
    the order the notebook used and therefore the order the published windows
    were cut in; it is preserved because window boundaries depend on it.
    """
    if regime not in CWRU_REGIMES:
        raise ValueError(f"regime must be one of {tuple(CWRU_REGIMES)}, "
                         f"received {regime!r}")
    folder = resolve_ci(data_root, f"{speed} RPM")

    if regime == "healthy":
        path = resolve_ci(folder, f"{speed}_Normal.npz")
        with np.load(path) as d:
            return np.asarray(d[channel]).reshape(-1)

    pattern = CWRU_REGIMES[regime].format(rpm=speed)
    files = sorted(folder.glob(pattern))
    if not files:
        available = sorted(p.name for p in folder.glob("*.npz"))
        raise FileNotFoundError(
            f"no CWRU files match {pattern!r} in {folder}. "
            f"Present: {', '.join(available[:10])}"
            + (" ..." if len(available) > 10 else ""))

    parts = []
    for path in files:
        with np.load(path) as d:
            if channel not in d:
                raise KeyError(f"{path.name} has channels {tuple(d)}, "
                               f"but {channel!r} was requested")
            parts.append(np.asarray(d[channel]).reshape(-1))
    return np.concatenate(parts)


def load_asset_windows(data_root, speed, *, win=1200, step=1200,
                       channel="DE"):
    """
    All four regimes of one speed, windowed, as `{regime: (n_windows, win)}`.

    This is the oracle view of the notebook: no train/calibration/test split
    is introduced here, because the split is a property of the experiment
    rather than of the data. Section 9 uses one split for the asset-specific
    reference and another for the online-calibration arm, from these same
    windows.
    """
    from .ims import make_windows          # one windowing rule for both archives

    out = {}
    for regime in CWRU_REGIMES:
        signal = load_signal(data_root, speed, regime, channel=channel)
        out[regime] = make_windows(signal, win=win, step=step).astype(np.float32)
    return out
