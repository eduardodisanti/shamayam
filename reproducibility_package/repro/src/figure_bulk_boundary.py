"""The bulk converges; the boundary does not. Eight panels, measured.

This replaces five per-domain saturation figures inherited from the v7
notebooks, which carried two defects between them.

  - Their first point was the internal Hausdorff discrepancy d_H(X_n, X_{n/2})
    at the smallest n, where the two sets are effectively the same set. It came
    out at 1e-14 and set the vertical scale, so the visible "collapse" was in
    part a comparison of a sample with itself.

  - They mixed metrics inside one panel: a radius in euclidean distance to a
    centroid alongside a Hausdorff quantity in cosine. Only one of the two is
    the metric the rest of the paper declares.

Here everything is cosine, and the two curves are the two halves of the
paper's fourth contribution, measured on the same draws:

    within-class MEDIAN   a functional of the measure -> it settles
    within-class MAXIMUM  a functional of the support -> it does not

Both are divided by the median at the largest n, and the vertical axis is
logarithmic, so the eight panels share one axis and the comparison is between
the SHAPES, not between the units. Without the log the battery panel, whose
maximum reaches thirty-nine times its own median, flattens the other seven. A
converging quantity and a diverging one on the same scale is the whole claim.

Sources: run_*/physical_contrast.json (l2 arm) and run_*/separability.json,
both produced by run_contrast.

Palette: #2a78d6 / #eb6834 on surface #fcfcfb, validated --pairs all.
"""
from __future__ import annotations
import json, sys
import numpy as np
import os
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as F
from figstyle import BLUE, ORANGE, INK, MUTED, GRID, SURF

SHORT = {"PM real (nominal)": "Point machine, measured",
         "PM simulated": "Point machine, simulated",
         "ECG real (MIT-BIH)": "ECG, measured",
         "ECG simulated": "ECG, simulated",
         "Battery real (NASA)": "Battery discharge",
         "UCI digits 8x8": "Handwritten digits, UCI",
         "MNIST 28x28": "Handwritten digits, MNIST",
         "Spoken digits (FSDD)": "Spoken digits"}
ORDER = ["PM real (nominal)", "PM simulated", "ECG real (MIT-BIH)",
         "ECG simulated", "Battery real (NASA)", "UCI digits 8x8",
         "MNIST 28x28", "Spoken digits (FSDD)"]


def series(rec_by_n):
    ns = sorted(int(n) for n in rec_by_n)
    med = np.array([rec_by_n[str(n)]["within_med"][0] for n in ns])
    mx = np.array([rec_by_n[str(n)]["within_max"][0] for n in ns])
    return np.array(ns, float), med, mx


def build(run, out):
    phys = json.load(open(f"{run}/physical_contrast.json"))["l2"]
    sep = json.load(open(f"{run}/separability.json"))["datasets"]

    data = {}
    for k, v in phys.items():
        data[k] = series(v)
    for k, v in sep.items():
        if k not in SHORT:
            continue                       # el brazo con relleno no va acá
        ns = sorted(int(n) for n in v["per_class"]["0"])
        med = np.array([np.mean([v["per_class"][str(c)][str(n)]["within_med"][0]
                                 for c in range(10)]) for n in ns])
        mx = np.array([np.mean([v["per_class"][str(c)][str(n)]["within_max"][0]
                                for c in range(10)]) for n in ns])
        data[k] = (np.array(ns, float), med, mx)

    missing = [k for k in ORDER if k not in data]
    if missing:
        raise SystemExit(f"faltan {missing}")

    # Three by three: eight panels and the legend in the ninth cell. Two by
    # four across 6.5in would give 1.5in panels, too narrow for the row
    # identifiers to sit on one line.
    F.apply()
    fig, axes = plt.subplots(3, 3, figsize=F.size(1.0, 5.9),
                             sharex=True, sharey=True)
    flat = axes.ravel()
    for ax, key in zip(flat, ORDER):
        n, med, mx = data[key]
        u = med[-1]
        F.style(ax)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.axhline(1.0, color=MUTED, lw=.8, ls=(0, (4, 3)), zorder=2)
        ax.plot(n, mx / u, color=ORANGE, lw=1.5, marker="o", ms=3.0,
                mec=SURF, mew=.7, zorder=4)
        ax.plot(n, med / u, color=BLUE, lw=1.7, marker="o", ms=3.0,
                mec=SURF, mew=.7, zorder=5)
        F.ident(ax, SHORT[key])

    flat[0].set_ylim(0.75, 50)
    from matplotlib.ticker import FixedLocator, NullFormatter, FixedFormatter
    for ax in flat[:len(ORDER)]:
        ax.yaxis.set_major_locator(FixedLocator([1, 2, 5, 10, 20, 40]))
        ax.yaxis.set_major_formatter(
            FixedFormatter(["1", "2", "5", "10", "20", "40"]))
        ax.yaxis.set_minor_formatter(NullFormatter())

    # the ninth cell carries the legend, so identity is never colour alone
    lax = flat[8]
    lax.set_axis_off()
    lax.legend(handles=[
        plt.Line2D([], [], color=BLUE, lw=1.7, marker="o", ms=3.0,
                   label="within-class median"),
        plt.Line2D([], [], color=ORANGE, lw=1.5, marker="o", ms=3.0,
                   label="within-class maximum"),
        plt.Line2D([], [], color=MUTED, lw=.8, ls=(0, (4, 3)),
                   label="median at largest $n$"),
    ], loc="center left", labelcolor=INK, borderaxespad=0.0)

    for ax in (flat[5], flat[6], flat[7]):
        ax.set_xlabel("realisations per class, $n$")
        ax.tick_params(labelbottom=True)
    for ax in (flat[0], flat[3], flat[6]):
        ax.set_ylabel("$\\div$ median at largest $n$")

    fig.subplots_adjust(left=.088, right=.985, top=.955, bottom=.085,
                        hspace=.42, wspace=.20)
    F.save(fig, out)
    for k in ORDER:
        n, med, mx = data[k]; u = med[-1]
        print(f"    {SHORT[k]:26s} mediana {med[0]/u:.2f}->{med[-1]/u:.2f}"
              f"   maximo {mx[0]/u:.2f}->{mx[-1]/u:.2f}"
              f"   (n {int(n[0])}..{int(n[-1])})")


if __name__ == "__main__":
    a = sys.argv[1:]
    build(a[0] if a else "run_o", a[1] if len(a) > 1 else "fig_bulk_boundary.png")
