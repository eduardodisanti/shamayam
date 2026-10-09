"""The four multi-site appendix figures, on the shared template.

These existed only inside cross_domain_manifold.ipynb; two of them were a bare
`df.hist(column="n_sat")`, which is why they reached the manuscript with the
raw column name as their title and no axis labels at all. The pipeline is
ported here unchanged in substance so the figures have a generator:

    ~/data/nsrdb_solar/<station>/*.csv  -> nsrdb_manifold_saturation_grid.png
                                           nsrdb_manifold_saturation_distribution.png
    ~/data/noaa_tides/<station>/*.csv   -> tides_manifold_saturation_grid.png
                                           tidal_manifold_saturation_distribution.png

This is the OLDER multi-site pipeline, and the manuscript says so where the
figures appear: calendar days, min--max scaling, R^24. It is kept as a breadth
check across sites, not as evidence about compactness. Nothing here feeds a
number in the body.

Two deliberate changes to the notebook code, both about reproducibility:

  * saturation_curve() shuffled with the global RNG and the per-station sweep
    never seeded it, so n_sat was not reproducible run to run. It is seeded
    per station here.
  * the metrics are computed once and cached to a JSON, so the plotting can be
    re-run without re-reading a gigabyte of CSV.

    python src/figure_multisite.py compute <data_root> <cache.json>
    python src/figure_multisite.py plot    <cache.json> <outdir>
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as F
from figstyle import CAT, INK, MUTED, SURF

DATE_COL, TIME_COL, GHI_COL = "YYYY-MM-DD", "HH:MM (LST)", "Glo Mod (W/m^2)"

# The four series of the notebook's plot_saturation, in a fixed order.
SERIES = [("hausdorff", "Hausdorff($n$ vs $n/2$)", CAT[0]),
          ("r_max",     "radius, maximum",         CAT[1]),
          ("r_mean",    "radius, mean",            CAT[2]),
          ("volume",    "bounding-box volume",     CAT[3])]


# ------------------------------------------------------------------- metrics
def hausdorff(A, B):
    D = cdist(A, B, metric="cosine")
    return max(D.min(axis=1).max(), D.min(axis=0).max())


def radius_from_centroid(X):
    D = cdist(X, X.mean(axis=0, keepdims=True))
    return float(D.max()), float(D.mean())


def bounding_box_volume(X):
    return float(np.sum(X.max(axis=0) - X.min(axis=0)))


def saturation_curve(X, seed=0):
    X = np.array(X, float)
    np.random.default_rng(seed).shuffle(X)
    steps = np.unique(np.logspace(1, np.log10(len(X)), num=12, dtype=int))
    H, rmax, rmean, V = [], [], [], []
    for n in steps:
        s = X[:n]
        # At the smallest step max(10, n//2) == n, so this compares a sample
        # with itself: the value comes out at ~1e-14 and, on a log axis, sets
        # the vertical scale for the whole panel. figure_bulk_boundary.py
        # records this as one of the two defects that took these curves out of
        # the body. It is not reproduced here; the point is left undefined.
        n2 = max(10, n // 2)
        H.append(float(hausdorff(s[:n2], s)) if n2 < n else float("nan"))
        a, b = radius_from_centroid(s)
        rmax.append(a); rmean.append(b)
        V.append(bounding_box_volume(s))
    return steps.tolist(), H, rmax, rmean, V


def estimate_n_sat(steps, r_mean, rel_tol=0.05, consecutive=2):
    steps = np.asarray(steps, float); r = np.asarray(r_mean, float)
    if len(steps) < consecutive + 1:
        return float("nan")
    ch = np.abs(np.diff(r)) / np.maximum(np.abs(r[:-1]), 1e-12)
    for i in range(len(ch) - consecutive + 1):
        if np.all(ch[i:i + consecutive] < rel_tol):
            return float(steps[i])
    return float(steps[-1])


# ------------------------------------------------------------------- loaders
def load_solar(station_dir):
    import pandas as pd
    files = sorted(station_dir.glob("*.csv"))
    if not files:
        return None
    df = pd.concat([pd.read_csv(f).rename(columns=str.strip) for f in files],
                   ignore_index=True)
    df[DATE_COL] = df[DATE_COL].astype(str).str.strip()
    df[TIME_COL] = df[TIME_COL].astype(str).str.strip()
    m = df[TIME_COL] == "24:00"
    a, b = df[m].copy(), df[~m].copy()
    if not a.empty:
        a[DATE_COL] = (pd.to_datetime(a[DATE_COL]) + pd.Timedelta(days=1)
                       ).dt.strftime("%Y-%m-%d")
        a[TIME_COL] = "00:00"
    df = pd.concat([b, a], ignore_index=True)
    df["datetime"] = pd.to_datetime(df[DATE_COL] + " " + df[TIME_COL],
                                    format="%Y-%m-%d %H:%M")
    s = df.set_index("datetime").sort_index()
    s = s[s[GHI_COL] > 0].dropna()
    s = pd.to_numeric(s[GHI_COL]).astype(float).dropna().sort_index()
    return _daily(s, normalise="max")


def load_tides(station_dir):
    import pandas as pd
    files = sorted(station_dir.glob("*.csv"))
    if not files:
        return None
    df = pd.concat([pd.read_csv(f).rename(columns=str.strip) for f in files],
                   ignore_index=True)
    df["datetime"] = pd.to_datetime(df["Date Time"])
    df = df.set_index("datetime").sort_index()
    df["Water Level"] = pd.to_numeric(df["Water Level"], errors="coerce")
    return _daily(df.dropna(subset=["Water Level"])["Water Level"],
                  normalise="minmax")


def _daily(series, normalise):
    """One row per calendar day on a fixed 24-hour grid. The notebook's rule."""
    import pandas as pd
    rows = []
    for day, s in series.groupby(series.index.floor("D")):
        d0 = pd.Timestamp(day).normalize()
        idx = pd.date_range(d0, d0 + pd.Timedelta(hours=23), freq="1h")
        v = s.reindex(idx, method="nearest").to_numpy(float)
        if normalise == "max":
            if np.all(np.isnan(v)):
                continue
            mx = np.nanmax(v)
            if not np.isfinite(mx) or mx <= 0:
                continue
            rows.append(v / mx)
        else:
            if np.any(np.isnan(v)) or len(v) < 24:
                continue
            lo, hi = float(np.min(v)), float(np.max(v))
            if hi - lo == 0:
                continue
            rows.append((v - lo) / (hi - lo))
    return np.vstack(rows) if rows else None


# ------------------------------------------------------------------- compute
def compute(data_root, cache):
    data_root = Path(os.path.expanduser(data_root))
    out = {}
    for name, sub, loader, step, min_days in (
            ("solar", "nsrdb_solar", load_solar, 5, 50),
            ("tides", "noaa_tides", load_tides, 1, 20)):
        root = data_root / sub
        recs = []
        for i, d in enumerate(sorted(p for p in root.iterdir() if p.is_dir())):
            try:
                X = loader(d)
            except Exception as e:
                print(f"  {d.name}: {type(e).__name__}: {e}", flush=True)
                continue
            if X is None or len(X) < min_days:
                continue
            steps, H, rmax, rmean, V = saturation_curve(X[::step], seed=i)
            recs.append({"station": d.name, "n_days": int(len(X)),
                         "steps": steps, "hausdorff": H, "r_max": rmax,
                         "r_mean": rmean, "volume": V,
                         "n_sat": estimate_n_sat(steps, rmean)})
            print(f"  {name} {d.name}: n_days={len(X)} "
                  f"n_sat={recs[-1]['n_sat']:.0f}", flush=True)
        out[name] = recs
        print(f"{name}: {len(recs)} stations", flush=True)
    json.dump(out, open(cache, "w"))
    print(f"wrote {cache}")


# ---------------------------------------------------------------------- plot
def _grid(recs, out, frac=0.80, seed=123):
    """Nine stations, four metrics each, log-log. Station id labels the panel."""
    pick = list(np.random.default_rng(seed).choice(len(recs), min(9, len(recs)),
                                                   replace=False))
    fig, axes = plt.subplots(3, 3, figsize=F.size(frac, 5.3))
    flat = axes.ravel()
    for ax, i in zip(flat, pick):
        r = recs[i]
        F.style(ax)
        ax.set_xscale("log"); ax.set_yscale("log")
        for key, _lab, col in SERIES:
            y = np.array(r[key], float)
            m = np.isfinite(y) & (y > 0)
            ax.plot(np.array(r["steps"], float)[m], y[m],
                    marker="o", ms=2.4, lw=1.1, color=col)
        F.ident(ax, r["station"])
    for ax in flat[len(pick):]:
        ax.set_axis_off()
    for ax in flat[6:9]:
        ax.set_xlabel("$n$ (days)")
    for ax in (flat[0], flat[3], flat[6]):
        ax.set_ylabel("metric value")
    fig.legend(handles=[plt.Line2D([], [], color=c, marker="o", ms=2.4, lw=1.1,
                                   label=l) for _k, l, c in SERIES],
               loc="lower center", ncol=2, labelcolor=INK,
               bbox_to_anchor=(0.5, -0.008))
    fig.subplots_adjust(left=.125, right=.985, top=.955, bottom=.165,
                        hspace=.52, wspace=.36)
    F.save(fig, out)


def _hist(recs, out, unit, title_, frac=0.50):
    """Included inside a 0.50\\textwidth minipage, so it is authored at half
    the text width. N and the median are in the table beside it, which is why
    there is no legend here."""
    v = np.array([r["n_sat"] for r in recs], float)
    fig, ax = plt.subplots(figsize=F.size(frac, 2.45))
    F.style(ax)
    ax.hist(v, bins=10, color=CAT[0], edgecolor=SURF, lw=.8, zorder=3)
    med = float(np.median(v))
    ax.axvline(med, color=CAT[1], lw=1.4, ls=(0, (4, 3)), zorder=4)
    F.title(ax, title_)
    ax.set_xlabel(f"$n_{{\\mathrm{{sat}}}}$ ({unit})")
    ax.set_ylabel("stations")
    fig.subplots_adjust(left=.175, right=.975, top=.875, bottom=.215)
    F.save(fig, out)
    print(f"    N={len(v)} mean={v.mean():.2f} std={v.std(ddof=1):.2f} "
          f"median={med:.2f} q25={np.percentile(v,25):.2f} "
          f"q75={np.percentile(v,75):.2f} min={v.min():.2f} max={v.max():.2f}")


def plot(cache, outdir):
    F.apply()
    D = json.load(open(cache))
    _grid(D["solar"], os.path.join(outdir, "nsrdb_manifold_saturation_grid.png"))
    _hist(D["solar"], os.path.join(
        outdir, "nsrdb_manifold_saturation_distribution.png"), "days",
        "Saturation scale, NSRDB stations")
    _grid(D["tides"], os.path.join(outdir, "tides_manifold_saturation_grid.png"))
    _hist(D["tides"], os.path.join(
        outdir, "tidal_manifold_saturation_distribution.png"), "days",
        "Saturation scale, NOAA stations")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "compute":
        compute(a[1], a[2])
    else:
        plot(a[1], a[2])
