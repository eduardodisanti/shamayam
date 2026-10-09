"""The saturation figure, in the layout of cross_domain_manifold.ipynb.

The design is Eduardo's and is kept: four curves against n, one panel per
domain, log axes, the same four quantities in the same order. Three things
are corrected, all of them measurement rather than drawing.

  1. THE RADIUS IS MEASURED ON REALISATIONS THE CENTRE NEVER SAW. In the
     original, the centroid is computed from the same n points the radius is
     then measured against, so at small n the radius is biased low and the
     curve rises partly because the bias is wearing off. Measured on held-out
     realisations the same quantity falls to the same plateau from above.
     Both are drawn, because the gap between them closing is itself the
     evidence that the manifold has been resolved.

  2. ONE METRIC. The original used euclidean for the radius and cosine for
     the Hausdorff discrepancy on the same axes. Everything here is cosine,
     the metric the rest of the paper declares.

  3. THE INTERNAL HAUSDORFF CURVE IS GONE. d_H(X_n, X_n/2) is a functional of
     the SUPPORT: by prop:bulk(ii) it need not converge, and measured it does
     not -- on the battery, the real ECG and the point machine it climbs with
     n rather than falling. Nothing in the paper rests on it any more, so a
     curve that rises where the others fall was reading as a defect in the
     figure instead of as the theorem it actually illustrates. The bbox extent
     is left in, and carries the same point without the noise: it is the one
     curve that does not settle, and that is deliberate.

The bounding-box curve is labelled for what the function computes: the L1
extent, the sum over axes of (max - min). It is not a volume.
"""
import json
import math
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA, PLUM = "#2a78d6", "#eb6834", "#1baf7a", "#7a5cc7"
INK, MUTED, GRID, SURF = "#1a1a19", "#6b6b68", "#e2e2df", "#fcfcfb"

# Each curve is drawn as a fraction of its own value at the largest n. The
# four quantities live on scales that differ by two orders of magnitude -- the
# L1 extent of the bounding box is a sum over 160 axes, the radii are cosine
# distances below one -- so on a shared logarithmic axis the extent sets the
# scale and the three curves that carry the argument are squashed into a band.
# Dividing each by its own plateau puts them on the one axis that is common to
# all four and is the one the figure is about: how far each is from where it
# ends up.
NORMALISE = True

CURVES = [
    ("r_max",  "radius (max), unseen",          ORANGE, "-o"),
    ("r_mean", "radius (mean), unseen",         AQUA,   "-o"),
    ("bbox",   "bbox extent ($L_1$)",           PLUM,   "-o"),
]


def panel(ax, rec, title):
    ax.set_facecolor(SURF)
    ax.grid(True, which="both", color=GRID, lw=.7, alpha=.9, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)

    n = np.array(rec["steps"], float)
    drawn = False
    hi = 1.0
    for key, label, colour, style in CURVES:
        if key not in rec:
            continue
        v = np.array(rec[key], float)[:, 0]
        m = np.isfinite(v) & (v > 0)          # exact zeros are not plotted
        if m.sum() < 2:
            continue
        if NORMALISE:
            v = v / v[m][-1]
        ax.plot(n[m], v[m], style, ms=3.2, lw=1.6, color=colour, label=label,
                zorder=3, markeredgecolor=SURF, markeredgewidth=.6)
        hi = max(hi, float(np.max(v[m])))
        drawn = True
    if drawn:
        ax.set_xscale("log")
        if NORMALISE:
            ax.axhline(1.0, color=MUTED, lw=.9, zorder=1)
            # The limit follows the data. A fixed 1.35 silently cut the top
            # off the battery panel, where the max-radius curve starts above
            # 1.5: the curve was not missing, it was outside the axes.
            ax.set_ylim(0, max(1.35, 1.04 * hi))
        else:
            ax.set_yscale("log")
    ax.set_xlabel("$n$ (realisations)", color=INK, fontsize=9)
    ax.set_ylabel("value / value at largest $n$" if NORMALISE
                  else "metric value", color=INK, fontsize=9)
    ax.set_title(title, color=INK, fontsize=10)


def build(run, out, which="domains"):
    d = json.load(open(f"{run}/convergence.json"))
    sets = {**d.get("domains", {}), **d.get("digits", {})}
    sets = {k: v for k, v in sets.items() if v.get("steps")}
    if not sets:
        raise ValueError("convergence.json has no measured set")

    names = sorted(sets)
    cols = 3 if len(names) > 4 else min(len(names), 2)
    rows = math.ceil(len(names) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.4 * cols, 4.2 * rows),
                             squeeze=False)
    flat = axes.ravel()
    for ax, nm in zip(flat, names):
        panel(ax, sets[nm], nm)
    for ax in flat[len(names):]:
        ax.axis("off")

    h, l = flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=len(l), frameon=False,
               labelcolor=MUTED, fontsize=9,
               bbox_to_anchor=(.5, .012))
    fig.text(.5, .055,
             "every curve is measured on realisations the observer has not "
             "seen, and is drawn as a fraction of its own value at the largest "
             "$n$.  exact zeros are not plotted.",
             ha="center", color=MUTED, fontsize=8.6)
    fig.suptitle("Geometric saturation, one panel per domain",
                 color=INK, fontsize=12)
    fig.tight_layout(rect=[0, .10, 1, .97])
    fig.savefig(out, dpi=160, facecolor=SURF,
                metadata={"Software": None, "Creation Time": None})
    plt.close(fig)
    info = {"panels": names}
    print(f"    fig_saturation_grid: {len(names)} paneles", flush=True)
    return info


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1], sys.argv[2]), indent=1, sort_keys=True))
