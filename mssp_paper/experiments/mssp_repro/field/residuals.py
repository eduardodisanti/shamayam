"""
Layer B, stage 3: per-recording residuals, and the cache that makes them
reusable.

WHAT THIS PRODUCES
------------------
One scalar per recording per bearing: the frozen shared operator's
reconstruction error, aggregated over the 17 windows of that recording by the
mean (see `dynamics.recording_score` for why the mean and not a quantile).
For IMS Experiment 2 that is a (4, 984) array -- about 31 kB, against the
523 MB archive and the several minutes of training that produce it.

WHY IT IS CACHED, AND WHY THAT IS NOT A SHORTCUT
------------------------------------------------
Everything the paper actually claims lives downstream of this array: radii,
commissioning lengths, false-alarm rates, departure indices, lead times. All
of it is pure numpy and runs in seconds. The expensive parts -- reading the
archive, training the operator, scoring 66,912 windows -- are data production.

So the array is committed to the repository, and a reader without the 523 MB
archive can still regenerate every field table and figure in the paper. That
would be a shortcut if it were merely a convenience. It is not, because of
`compare_to_cache`: a reader who DOES have the archive runs the full chain and
the pipeline checks its own output against the committed cache, reporting the
agreement and failing when it is not there. The cache is an assertion the
pipeline can be held to, in the same spirit as the test that pins the
autoencoder at 847,601 parameters.

WHAT AGREEMENT MEANS HERE
-------------------------
Not equality. The residuals descend from a trained network, and TensorFlow is
not reproducible across builds, backends or versions -- the reference run was
Metal on macOS ARM. Comparing float arrays for equality would fail for reasons
that have nothing to do with correctness.

What must agree is what the paper reports. `compare_to_cache` therefore checks
the rank correlation of each series, the relative shift of its median level,
and -- the one that matters -- whether the derived departure index moves. A
port that reproduces the science will hold all three; one that broke the
scaling or the window order will fail the first two, and one that subtly
changed the operator will fail the third even when the first two look fine.
"""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .ims import IMS_CHANNELS, IMS_RECORDING_INTERVAL_HOURS, load_experiment

__all__ = ["IMS_EXPERIMENT", "FIELD_WARMUP_RECORDINGS", "compute_ims_residuals",
           "save_cache", "load_cache", "compare_to_cache"]

IMS_EXPERIMENT = 2

# Recordings reserved as the early-life commissioning prefix. The adaptive
# rule stops somewhere inside this window; the remainder is the monitoring
# trajectory. Transcribed from the notebook, where it equals MAX_CALIBRATION_SIZE.
FIELD_WARMUP_RECORDINGS = 200

# Tolerances for `compare_to_cache`. Chosen from what the quantities are, not
# from what a particular run happened to produce: Spearman rho below 0.99 means
# the series no longer rank the recordings the same way, a median level shift
# beyond 25% would move a calibrated radius materially, and a departure index
# that moves by more than the persistence window is a different conclusion.
MIN_RANK_CORRELATION = 0.99
MAX_LEVEL_SHIFT = 0.25
MAX_DEPARTURE_SHIFT = 10


def compute_ims_residuals(operator, ims_root, *, experiment=IMS_EXPERIMENT,
                          max_recordings=None, cache_dir=None, progress=None):
    """
    Score every recording of every bearing through a fitted operator.

    Returns `{"scores": (n_bearings, n_recordings), "bearings": [...],
    "timestamps": [...]}`. The archive is read ONCE and all channels kept, so
    the chronology is established a single time and shared across bearings.
    """
    if operator.ae_ is None:
        raise RuntimeError("operator is not fitted; call fit() first")

    signals, timestamps, files = load_experiment(
        ims_root, experiment, cache_dir=cache_dir,
        max_recordings=max_recordings)

    bearings = sorted(IMS_CHANNELS[experiment])
    scores = np.empty((len(bearings), signals.shape[0]), dtype=float)
    for row, bearing in enumerate(bearings):
        (column,) = IMS_CHANNELS[experiment][bearing]
        if progress:
            progress(f"    bearing {bearing} (channel {column}): "
                     f"{signals.shape[0]} recordings")
        scores[row] = operator.recording_residuals(signals[:, :, column])

    return {
        "scores": scores,
        "bearings": bearings,
        "timestamps": [str(t) for t in timestamps],
        "n_recordings": int(signals.shape[0]),
        "first_file": files[0].name,
        "last_file": files[-1].name,
    }


# ---------------------------------------------------------------------
# The cache
# ---------------------------------------------------------------------

def _provenance(operator, extra=None):
    try:
        import tensorflow as tf
        tf_version = tf.__version__
        gpus = tf.config.list_physical_devices("GPU")
        device = ", ".join(
            tf.config.experimental.get_device_details(g).get("device_name",
                                                             g.name)
            for g in gpus) if gpus else "CPU"
    except Exception:                                  # pragma: no cover
        tf_version, device = "absent", "unknown"

    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "tensorflow": tf_version,
        "device": device,
        "operator_seed": operator.seed,
        "operator_epochs": operator.epochs,
        "tau_mc": operator.tau_mc_,
        "training": operator.history_,
    }
    if extra:
        meta.update(extra)
    return meta


def save_cache(path, residuals, operator, *, extra=None):
    """Write the residual series plus enough provenance to judge them."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scores = np.asarray(residuals["scores"], dtype=float)
    meta = _provenance(operator, extra)
    meta.update({k: residuals[k] for k in
                 ("bearings", "n_recordings", "first_file", "last_file")})
    meta["sha256"] = hashlib.sha256(scores.tobytes()).hexdigest()
    np.savez_compressed(path, scores=scores,
                        timestamps=np.asarray(residuals["timestamps"]),
                        meta=json.dumps(meta, indent=1))
    return path


def load_cache(path):
    with np.load(path, allow_pickle=False) as d:
        return {"scores": d["scores"],
                "timestamps": [str(t) for t in d["timestamps"]],
                "meta": json.loads(str(d["meta"]))}


def _spearman(a, b):
    """Rank correlation without scipy, which Layer A1 does not depend on."""
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / denom) if denom > 0 else float("nan")


def _departure(scores, tau, q=8, p=10):
    from ..dynamics import first_persistent_departure
    return first_persistent_departure(np.asarray(scores) > tau, q=q, p=p)


def compare_to_cache(fresh, cached, *, tau_per_bearing=None):
    """
    Compare a freshly computed residual set against the committed cache.

    Returns `(ok, rows)` where `rows` is one dict per bearing carrying the
    three diagnostics. See the module docstring for why equality is the wrong
    comparison and these three are the right ones.
    """
    fresh_s = np.asarray(fresh["scores"], dtype=float)
    cached_s = np.asarray(cached["scores"], dtype=float)
    if fresh_s.shape != cached_s.shape:
        return False, [{"bearing": None,
                        "error": f"shape {fresh_s.shape} against cached "
                                 f"{cached_s.shape}"}]

    rows, ok = [], True
    for i, bearing in enumerate(fresh.get("bearings",
                                          range(1, fresh_s.shape[0] + 1))):
        a, b = fresh_s[i], cached_s[i]
        rho = _spearman(a, b)
        level = abs(np.median(a) - np.median(b)) / max(np.median(b), 1e-30)

        shift = None
        if tau_per_bearing is not None:
            tau = tau_per_bearing[i]
            da, db = _departure(a, tau), _departure(b, tau)
            shift = (abs(da - db) if (da is not None and db is not None)
                     else None if (da is None and db is None) else np.inf)

        row_ok = (rho >= MIN_RANK_CORRELATION
                  and level <= MAX_LEVEL_SHIFT
                  and (shift is None or shift <= MAX_DEPARTURE_SHIFT))
        ok &= row_ok
        rows.append({"bearing": bearing, "spearman": rho,
                     "level_shift": float(level), "departure_shift": shift,
                     "ok": row_ok})
    return ok, rows


# ---------------------------------------------------------------------
# Commissioning, in one place
#
# The adaptive rule was previously spelled out in every caller that needed
# it. Three copies of a five-line procedure is how two callers end up
# disagreeing about `min_index` and nobody notices, so it lives here and the
# stability experiment, the figure generator and the table generator all go
# through it.
# ---------------------------------------------------------------------

def commission_bearing(series, *, estimator=None, warmup=None):
    """
    Commission one bearing from its early-life residual series.

    Returns None when the convergence criterion is never met -- which is a
    reportable outcome, not an error: an asset whose radius never settles is
    one the procedure declines to certify.
    """
    from ..calibration import (AdaptiveOperationalRadius, find_convergence_index,
                               interpolated_quantile)
    from .. import (CONVERGENCE_CONSECUTIVE, CONVERGENCE_LOOKBACK,
                    CONVERGENCE_TOLERANCE, MAX_CALIBRATION_SIZE,
                    MIN_CALIBRATION_SIZE, MIN_WARMUP_SAMPLES)

    estimator = estimator or interpolated_quantile
    warmup = MAX_CALIBRATION_SIZE if warmup is None else int(warmup)
    early = np.asarray(series, dtype=float)[:warmup]

    trace = AdaptiveOperationalRadius(
        estimator, window_size=warmup,
        min_samples=MIN_WARMUP_SAMPLES).warmup_trace(early)
    idx = find_convergence_index(
        trace, lookback=CONVERGENCE_LOOKBACK, tolerance=CONVERGENCE_TOLERANCE,
        consecutive=CONVERGENCE_CONSECUTIVE,
        min_index=MIN_CALIBRATION_SIZE - 1)
    if idx is None:
        return None
    return {"n": int(idx + 1), "tau": float(trace[idx]),
            "oracle": float(estimator(early)),
            "early_median": float(np.median(early)),
            "trace": trace}


def describe_trajectory(series, *, q=8, p=10, interval_hours=None,
                        warmup=None):
    """
    Everything the run-to-failure figure and table need for one bearing.

    Commissioning, the frozen radius, the first persistent departure and the
    lead time to the documented end of the record.
    """
    interval = (IMS_RECORDING_INTERVAL_HOURS if interval_hours is None
                else float(interval_hours))
    s = np.asarray(series, dtype=float)
    c = commission_bearing(s, warmup=warmup)
    if c is None:
        return {"converged": False}

    # Trim trailing recordings taken with the rig stopped before measuring
    # anything: they are not nominal operation and not degradation either.
    inactive = flag_inactive_recordings(s, warmup=warmup or FIELD_WARMUP_RECORDINGS)
    n_trailing = 0
    while n_trailing < s.size and inactive[s.size - 1 - n_trailing]:
        n_trailing += 1
    s_active = s[:s.size - n_trailing] if n_trailing else s

    from ..dynamics import first_persistent_departure
    d = first_persistent_departure(s_active > c["tau"], q=q, p=p, start=c["n"])
    out = {"converged": True, "n": c["n"], "tau": c["tau"],
           "n_trailing_inactive": int(n_trailing),
           "oracle": c["oracle"], "early_median": c["early_median"],
           "tau_normalised": c["tau"] / c["early_median"],
           "n_recordings": int(s.size),
           "n_active": int(s.size - n_trailing),
           "departure": None, "lead_hours": None,
           "exceedance_post": None,
           "far_commissioned": float(np.mean(s[c["n"]:warmup or 200]
                                             > c["tau"])) if c["n"] < (warmup or 200) else float("nan")}
    if d is not None:
        out.update({"departure": int(d),
                    "lead_hours": float((s_active.size - d) * interval),
                    "exceedance_post": float(np.mean(s_active[d:] > c["tau"]))})
    return out


# A recording is treated as taken with the machine stopped when its residual
# falls below this fraction of the SMALLEST residual seen during commissioning.
# Relative to the minimum rather than the median, because the four bearings sit
# at different nominal levels and a fraction of the median that catches three
# of them misses the fourth: bearing 4's stopped recording is 0.53 of its
# median but 0.56 of its minimum, while bearings 1-3 sit at 0.27-0.40 of theirs.
# The minimum is the natural reference -- the question is whether a recording is
# quieter than anything the rig produced while running.
INACTIVE_FRACTION_OF_MIN = 0.75

# Raw-signal criterion, used when the archive is at hand. A stopped rig gives a
# standard deviation near 0.001 against 0.13-0.48 while running, so the
# threshold is nowhere near delicate.
INACTIVE_SIGNAL_STD = 0.01


def flag_inactive_recordings(series, *, warmup=FIELD_WARMUP_RECORDINGS,
                             signal_std=None):
    """
    Recordings taken with the machine stopped.

    IMS Experiment 2 does not end when the bearing fails; it ends when someone
    shut the rig down. The last two of the 984 files carry a signal with
    standard deviation near 0.001 on all four channels, against 0.13-0.48 on
    the recording before them. The rig is not running.

    This matters in three small ways, none fatal and all worth getting right.
    Those recordings do not exceed the radius, so they dilute the
    post-departure exceedance. They count towards the record length, so they
    add twenty minutes to every lead time. And on a log axis they produce a
    cliff at the right edge of the trajectory figure that a reader will
    reasonably take for a measurement artefact -- which it is, though not the
    kind they will guess.

    Pass `signal_std` when the raw archive is available; that is the direct
    criterion. Without it the test falls back to the residual, which works
    from the committed cache alone. A stopped rig produces an almost constant
    window, which the operator reconstructs easily, so its residual sits far
    BELOW the nominal level rather than above it. A stopped machine looks
    nothing like a faulty one, and nothing like a healthy one either.
    """
    if signal_std is not None:
        return np.asarray(signal_std, dtype=float) < INACTIVE_SIGNAL_STD
    s = np.asarray(series, dtype=float)
    floor = float(np.min(s[:warmup]))
    return s < INACTIVE_FRACTION_OF_MIN * floor
