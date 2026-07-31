#!/usr/bin/env python3
"""
Regenerate every figure in the paper from `results/data.json`.

WHY THIS READS A FILE RATHER THAN RECOMPUTING
---------------------------------------------
Figures are build artefacts, not drawings. They are produced from the same
record that produces the LaTeX tables, so a figure and the number quoted
beside it cannot disagree: both come from one run of `run_all.py`. Recomputing
here instead would reintroduce exactly the divergence this arrangement is
meant to prevent, and would require retraining the A2 operator to redraw a
curve.

Consequently this script is fast and needs no TensorFlow. If `data.json` was
produced by `--layer a1` the A2 figures are skipped with a notice rather than
drawn from stale data.

    python3 make_figures.py                 # -> figures/*.pdf

Output is vector PDF at a fixed physical width, so the paper never rescales a
figure and font sizes stay consistent with the body text.
"""

import json
import sys
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    # This script is the only thing in the package that needs a plotting
    # library, and it is the last step of the pipeline. A bare
    # ModuleNotFoundError here reads as though the reproduction failed, when
    # in fact every number has already been computed and written to
    # results/data.json; only the redrawing is blocked. Say so.
    raise SystemExit(
        f"make_figures.py needs matplotlib ({exc.name} not installed).\n"
        "\n"
        "    pip install 'matplotlib>=3.5'      # or: pip install -r "
        "requirements.txt\n"
        "\n"
        "Nothing else in the package requires it: run_all.py, make_tables.py,\n"
        "make_macros.py and the test suite all run without it. If you have\n"
        "already run run_all.py, results/data.json is complete and the "
        "figures\n"
        "can be redrawn at any time -- no experiment needs repeating."
    ) from exc

HERE = Path(__file__).parent
DATA_PATH = HERE / "results" / "data.json"
FIGDIR = HERE.parent / "figures"

# Single-column width of the target class, in inches, so no rescaling occurs.
WIDTH = 6.6
# Colourblind-safe; the paper may be printed in greyscale, so line style
# carries the distinction as well as colour.
C_CERT, C_INTERP, C_REF = "#0072B2", "#D55E00", "#444444"
C_OK, C_BAD = "#009E73", "#CC79A7"

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "figure.constrained_layout.use": True, "savefig.bbox": "tight",
    "pdf.fonttype": 42,
})


NAMES = {"adequacy": "distance_proxy_probe", "drift": "degradation_trajectory",
         "saturation": "saturation", "variance": "estimator_variance",
         "dimension": "intrinsic_dimension"}


def _placeholder(key):
    """
    A missing figure must not break the build. An explicit placeholder keeps
    the document compilable and makes the gap visible in the PDF.
    """
    fig, ax = plt.subplots(figsize=(WIDTH, 2.0))
    ax.axis("off")
    ax.text(0.5, 0.5, f"NOT GENERATED\n{key}: requires layer A2\n"
            "run_all.py then make_figures.py",
            ha="center", va="center", fontsize=11, color=C_BAD,
            bbox=dict(boxstyle="round", fc="white", ec=C_BAD, lw=1.2))
    _save(fig, NAMES[key])


def _save(fig, name):
    FIGDIR.mkdir(exist_ok=True)
    path = FIGDIR / f"{name}.pdf"
    fig.savefig(path)
    plt.close(fig)
    print(f"  wrote {path.relative_to(HERE.parent)}")


# ---------------------------------------------------------------------
# Figure 1 -- saturation, and the tension it hides
# ---------------------------------------------------------------------

def figure_saturation(d):
    """
    The central figure of Section 5. Three things must be visible at once:
    the certified radius does not flatten inside the degenerate band, it falls
    discontinuously when an interior order statistic first becomes available,
    and the estimator that does produce a smooth saturating curve is the one
    that undercovers.
    """
    s = d["saturation"]
    rows = [r for r in s["rows"] if r["certified_mean"] is not None]
    n = np.array([r["n"] for r in rows], float)
    m = np.array([r["certified_mean"] for r in rows])
    sd = np.array([r["certified_sd"] for r in rows])
    cov = np.array([r["coverage"] for r in rows])
    interp = np.array([r["interpolated_mean"] for r in rows])
    icov = np.array([r["interpolated_coverage"] for r in rows])
    lo, hi = s["degenerate_range"]
    p = s["p"]

    fig, (ax, bx) = plt.subplots(2, 1, figsize=(WIDTH, 5.2), sharex=True)

    ax.axvspan(lo, hi, color="0.90", zorder=0)
    ax.axhline(s["R_pop"], color=C_REF, ls=":", lw=1.2,
               label=r"population radius $R_p$")
    ax.fill_between(n, m - sd, m + sd, color=C_CERT, alpha=0.18, lw=0)
    ax.plot(n, m, "o-", color=C_CERT, ms=3.5, lw=1.4,
            label=r"certified $r_{(k_\alpha)}$  ($\pm 1$ sd)")
    ax.plot(n, interp, "s--", color=C_INTERP, ms=3.5, lw=1.4,
            label="interpolated quantile")
    ax.axvline(hi + 1, color="0.55", lw=0.9)
    ax.set_ylabel("radius")
    ax.legend(loc="lower right", framealpha=0.95)

    # Headroom first, then place the annotation in it: the variability band is
    # widest inside the degenerate range and was previously clipped, and the
    # label sat on top of the certified curve.
    span = float(np.max(m + sd) - np.min(np.minimum(m - sd, interp)))
    ax.set_ylim(float(np.min(np.minimum(m - sd, interp))) - 0.05 * span,
                float(np.max(m + sd)) + 0.26 * span)
    ax.annotate("degenerate range:\nthe estimator is the sample maximum",
                xy=(lo, ax.get_ylim()[1]), xytext=(2, -3),
                textcoords="offset points", ha="left", va="top",
                fontsize=7.5, color="0.30")

    bx.axvspan(lo, hi, color="0.90", zorder=0)
    bx.axhline(p, color="0.70", ls="-", lw=0.8, label=f"target $p={p}$")
    # The reference for the certified curve is NOT the flat target: the
    # proposition predicts k_alpha/(n+1) exactly, which exceeds p and is not
    # monotone in n. Drawing the flat line alone invites reading the excess as
    # slack; drawing the exact prediction makes the agreement the visible fact.
    th = np.array([r.get("coverage_theory") or np.nan for r in rows])
    bx.plot(n, th, color=C_REF, ls=":", lw=1.4, zorder=2,
            label=r"exact $k_\alpha/(n{+}1)$")
    cse = np.array([r.get("coverage_se") or 0.0 for r in rows])
    bx.errorbar(n, cov, yerr=cse, fmt="o-", color=C_CERT, ms=3.5, lw=1.4,
                capsize=2, elinewidth=0.9, label="certified", zorder=3)
    bx.plot(n, icov, "s--", color=C_INTERP, ms=3.5, lw=1.4,
            label="interpolated")
    bx.axvline(hi + 1, color="0.55", lw=0.9)
    bx.set_xlabel("commissioning length $n$")
    bx.set_ylabel("attained coverage")
    bx.set_xscale("log")
    bx.legend(loc="lower right", framealpha=0.95)

    _save(fig, "saturation")


# ---------------------------------------------------------------------
# Figure 2 -- estimator dispersion across the degenerate boundary
# ---------------------------------------------------------------------

def figure_variance(d):
    rows = d["variance"]
    n = np.array([r["n"] for r in rows], float)
    sd = np.array([r["sd"] for r in rows])
    is_max = np.array([r["is_max"] for r in rows])

    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    # Shade the degenerate range and rule the boundary. Without them the gap
    # between the two curves reads as missing data rather than as the
    # discontinuity it is: the estimator changes identity at that n.
    lo, hi = d["saturation"]["degenerate_range"] if "saturation" in d else (None, None)
    if lo is not None:
        ax.axvspan(lo, hi, color="0.90", zorder=0)
        ax.axvline(hi + 1, color="0.55", lw=0.9, zorder=1)
    ax.plot(n[is_max], sd[is_max], "o-", color=C_BAD, ms=4, lw=1.4,
            label="sample maximum")
    ax.plot(n[~is_max], sd[~is_max], "o-", color=C_OK, ms=4, lw=1.4,
            label="interior order statistic")
    ax.set_xscale("log")
    ax.set_xlabel("commissioning length $n$")
    ax.set_ylabel(r"$\mathrm{sd}(\tau)$")
    ax.legend(framealpha=0.95)
    ax.set_title("clearing the floor is necessary, not sufficient",
                 fontsize=8.5, color="0.30")
    _save(fig, "estimator_variance")


# ---------------------------------------------------------------------
# Figure 3 -- the distance-proxy probe
# ---------------------------------------------------------------------

def figure_adequacy(d):
    """
    Log axes, because the two operators differ by thirty orders of magnitude
    in residual and by two in accepted distance. A linear plot would show one
    curve and a flat line at zero.
    """
    ops = d["adequacy"]["operators"]
    fig, ax = plt.subplots(figsize=(WIDTH, 3.1))

    taus = []
    for op, colour, marker in zip(ops, (C_BAD, C_OK), ("s", "o")):
        rows = op["rows"]
        dist = np.array([r["distance"] for r in rows])
        res = np.array([max(r["residual"], 1e-32) for r in rows])
        acc = np.array([r["accepted"] for r in rows])
        label = f"{op['operator'].split('(')[0].strip()}  " \
                f"({'pass' if op['passes'] else 'fail'}, " \
                f"{op['ratio']:.0f}$\\times$ spacing)"
        ax.plot(dist, res, marker + "-", color=colour, ms=5, lw=1.4,
                label=label)
        ax.plot(dist[acc], res[acc], marker, color=colour, ms=10, mfc="none",
                mew=1.4)
        ax.axhline(op["tau"], color=colour, ls=":", lw=1.0)
        taus.append(op["tau"])

    scale = ops[0]["nominal_scale"]
    ax.set_xscale("log")
    ax.set_yscale("log")

    # The nominal-spacing rule sat on the left spine with its label behind the
    # legend. Widen the left limit to give the rule room, annotate in axes
    # coordinates AFTER the scales are set (reading get_ylim() before that
    # returns provisional limits), and move the legend to the lower right,
    # which the two curves leave empty by construction: the failing operator
    # occupies the bottom left and the passing one the top right.
    x0 = min(min(r["distance"] for r in op["rows"]) for op in ops)
    ax.set_xlim(min(x0, scale) / 3.0, None)
    ax.axvline(scale, color=C_REF, ls="--", lw=1.0)
    ax.annotate("median nominal\nnearest-neighbour spacing",
                xy=(scale, 0.985), xycoords=("data", "axes fraction"),
                xytext=(3, 0), textcoords="offset points",
                va="top", ha="left", fontsize=7, color="0.30")
    ax.set_xlabel("true distance to the nearest nominal window")
    ax.set_ylabel("residual")
    # The two calibrated radii very nearly coincide -- that is the result, not
    # a coincidence to hide: identical calibration data and identical target
    # coverage give the two operators almost the same threshold, and they
    # nevertheless accept points twenty-five orders of magnitude apart in
    # residual. One shared label says so; two separate ones would overprint.
    ax.annotate(f"calibrated radii $\\tau$, both operators\n"
                f"({min(taus):.1e} and {max(taus):.1e})",
                xy=(0.985, min(taus)), xycoords=("axes fraction", "data"),
                xytext=(0, -6), textcoords="offset points",
                va="top", ha="right", fontsize=7, color="0.30")
    # Legend in the mid-left band: the failing operator runs along the bottom
    # and the passing one along the top right, so the corners are occupied.
    ax.legend(loc="center left", framealpha=0.95)
    ax.set_title("hollow markers are accepted by the calibrated radius; the "
                 "probe moves within the operator's own level set",
                 fontsize=7.5, color="0.30")
    _save(fig, "distance_proxy_probe")


# ---------------------------------------------------------------------
# Figure 4 -- degradation trajectory under a frozen radius
# ---------------------------------------------------------------------

def figure_drift(d):
    regimes = d["drift"]["regimes"]
    fig, axes = plt.subplots(len(regimes), 1, figsize=(WIDTH, 1.5 * len(regimes) + 1.2),
                             sharex=True)
    axes = np.atleast_1d(axes)

    for ax, reg in zip(axes, regimes):
        r = np.array(reg["residual"])
        t = np.arange(r.size)
        ax.plot(t, r, lw=0.7, color="0.35")
        ax.axhline(reg["tau"], color=C_CERT, ls="-", lw=1.2,
                   label=r"frozen $\tau$")
        ax.axvline(reg["onset"], color=C_REF, ls="--", lw=1.0, label="onset")
        if reg["detected"] is not None:
            ax.axvline(reg["detected"], color=C_BAD, ls="-", lw=1.2,
                       label="persistent departure")
            ax.axvspan(reg["onset"], reg["detected"], color=C_BAD, alpha=0.10,
                       lw=0)
        ax.set_yscale("log")
        ax.set_ylabel(reg["regime"].replace("_", " "), fontsize=8)

    axes[0].legend(loc="upper left", ncol=3, framealpha=0.95, fontsize=7.5)
    axes[-1].set_xlabel("record index")
    # The per-panel labels name the regime, so the quantity itself would
    # otherwise go unnamed on a log axis.
    fig.supylabel("residual", fontsize=9)
    fig.suptitle("the radius is commissioned early and never adapted; "
                 "the shaded gap is the detection delay",
                 fontsize=8, color="0.30")
    _save(fig, "degradation_trajectory")


# ---------------------------------------------------------------------
# Figure 5 -- intrinsic dimension
# ---------------------------------------------------------------------

def figure_dimension(d):
    dim = d["dimension"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(WIDTH, 2.7))

    tr = dim["tracking"]
    pred = np.array([r["predicted"] for r in tr], float)
    est = np.array([r["k20"] for r in tr])
    lim = [0, max(pred.max(), est.max()) + 0.6]
    ax.plot(lim, lim, ls=":", color=C_REF, lw=1.2, label="exact")
    ax.plot(pred, est, "o", color=C_CERT, ms=6)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("active nuisance parameters")
    ax.set_ylabel(r"estimated dimension ($k=20$)")
    ax.legend(framealpha=0.95)

    sc = dim["scale"]
    k = np.array([r["k"] for r in sc], float)
    bx.plot(k, [r["with_noise"] for r in sc], "o-", color=C_INTERP, ms=4,
            lw=1.4, label="with noise")
    bx.plot(k, [r["noise_free"] for r in sc], "o-", color=C_CERT, ms=4,
            lw=1.4, label="noise-free")
    bx.set_xscale("log")
    bx.set_xlabel("neighbourhood size $k$")
    bx.set_ylabel("estimated dimension")
    bx.legend(framealpha=0.95)
    bx.set_title(f"ambient dimension {dim['ambient']}", fontsize=8,
                 color="0.30")
    _save(fig, "intrinsic_dimension")


# ---------------------------------------------------------------------

FIGURES = [
    ("saturation", figure_saturation, "saturation"),
    ("variance", figure_variance, "variance"),
    ("dimension", figure_dimension, "dimension"),
    ("adequacy", figure_adequacy, "adequacy"),
    ("drift", figure_drift, "drift"),
]


def main():
    if not DATA_PATH.exists():
        raise SystemExit(f"{DATA_PATH} not found; run `python3 run_all.py` first")
    d = json.loads(DATA_PATH.read_text())
    meta = d.get("_meta", {})
    print(f"figures from a run of {meta.get('generated_utc', 'unknown date')}"
          f", seed {meta.get('seed', '?')}, layers {meta.get('layer', '?')}"
          + ("  [QUICK RUN]" if meta.get("quick") else ""))

    drawn, skipped = 0, []
    for key, fn, needs in FIGURES:
        if needs not in d:
            _placeholder(key)
            skipped.append(key)
            continue
        fn(d)
        drawn += 1

    if skipped:
        print(f"  skipped (absent from data.json): {', '.join(skipped)}")
        print("  run `python3 run_all.py` with layer A2 to produce them")
    print(f"{drawn} figure(s) written to {FIGDIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
