"""The radius converges.

This is the paper's claim in one picture, and it is the quantity the original
experiment measured: the radius of what an observer knows about a concept,
against how many realisations it has encountered. It rises -- or falls, seen
from outside -- and then stops changing.

Two corrections to the original measurement, both about measurement and
neither about drawing:

  1. The radius is measured on realisations the observer has NOT seen. A
     centroid computed from the same n points it is then scored against is
     biased at small n, so part of the original curve's shape was the bias
     wearing off rather than the concept being learned.

  2. Cosine throughout, the metric the rest of the paper declares.

No convergence threshold is drawn. The claim is that the curve stops changing,
and that is what the figure shows; a numeric criterion would have to be chosen
and the three this project has used disagree with each other.

Palette: #2a78d6 / #eb6834, light surface #fcfcfb.
"""
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID, SURF, GREY = "#1a1a19", "#6b6b68", "#e2e2df", "#fcfcfb", "#c9c9c6"
HERO_ORDER = ["PM real (nominal)", "ECG real (MIT-BIH)", "UCI digits 8x8"]


def style(ax):
    ax.set_facecolor(SURF)
    ax.grid(True, which="both", color=GRID, lw=.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("realisations encountered  $n$", color=INK, fontsize=10)


def radius(rec):
    a = np.array(rec["r_mean"], float)
    return np.array(rec["steps"], float), a[:, 0], a[:, 1]


def build(run, out):
    d = json.load(open(f"{run}/convergence.json"))
    sets = {k: v for k, v in {**d.get("domains", {}),
                              **d.get("digits", {})}.items() if v.get("steps")}
    if not sets:
        raise ValueError("convergence.json has no measured set")
    hero = next((h for h in HERO_ORDER if h in sets), sorted(sets)[0])
    others = [k for k in sorted(sets) if k != hero]

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.7))

    # ---- A: every domain, as a fraction of where its radius ends up --------
    ax = axes[0]; style(ax)
    ax.axhline(1.0, color=MUTED, lw=.9, zorder=1)
    for k in others:
        n, m, _ = radius(sets[k])
        ax.plot(n, m / m[-1], lw=1.5, color=GREY, zorder=3)
    n, m, _ = radius(sets[hero])
    ax.plot(n, m / m[-1], lw=2.4, color=BLUE, zorder=4, marker="o", ms=4,
            markeredgecolor=SURF, markeredgewidth=1)
    ax.annotate(hero, (n[-1], (m / m[-1])[-1]), textcoords="offset points",
                xytext=(-6, 14), ha="right", color=BLUE, fontsize=9,
                fontweight="bold")
    ax.set_ylabel("radius, as a fraction of\nwhere it settles",
                  color=INK, fontsize=10)
    ax.set_title("A · every domain settles", color=INK, fontsize=11, loc="left")
    ax.set_xlim(right=max(n) * 1.5)

    # ---- B: the same curve, in the units it is measured in -----------------
    ax = axes[1]; style(ax)
    n, m, s = radius(sets[hero])
    ax.fill_between(n, m - s, m + s, color=BLUE, alpha=.15, lw=0, zorder=2)
    ax.plot(n, m, lw=2.4, color=BLUE, zorder=4, marker="o", ms=4,
            markeredgecolor=SURF, markeredgewidth=1)
    fin = sets[hero].get("r_true")
    if fin:
        ax.axhline(fin, color=ORANGE, lw=1.2, ls=(0, (4, 3)), zorder=3)
        ax.annotate("radius over every available realisation",
                    (n[-1], fin), textcoords="offset points", xytext=(-4, -14),
                    ha="right", color=ORANGE, fontsize=8.5)
    lo = min(fin or m.min(), m.min())
    ax.set_ylim(lo - .12 * (m.max() - lo), m.max() + .10 * (m.max() - lo))
    ax.set_ylabel("radius of the concept", color=INK, fontsize=10)
    ax.set_title(f"B · {hero}, measured", color=INK, fontsize=11, loc="left")

    fig.text(.5, .038,
             "measured on realisations the observer has not seen; band is "
             "1 s.d. over independent draws. No convergence threshold is "
             "applied.", ha="center", color=MUTED, fontsize=8.8)
    fig.text(.5, .010, "grey: " + ", ".join(others),
             ha="center", color=MUTED, fontsize=8.2)
    fig.tight_layout(rect=[0, .075, 1, 1])
    fig.savefig(out, dpi=160, facecolor=SURF,
                metadata={"Software": None, "Creation Time": None})
    plt.close(fig)
    info = {"hero": hero, "domains": sorted(sets)}
    print(f"    fig_convergence: radio, {len(sets)} conjuntos", flush=True)
    return info


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1], sys.argv[2]), indent=1, sort_keys=True))
