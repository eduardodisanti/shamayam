"""Appendix figure -- the ten concepts of each digit set, one curve each.

The body reports one convergence curve per digit set, aggregated over its ten
concepts. That aggregate could hide two different worlds: ten classes that all
settle at the same n, or a mixture where some settle early and others never do
and the mean lands in between. This figure separates them, and the answer is
the first.

  One panel per set. Ten grey curves, one per digit: the radius an observer
      estimates for that digit from n encounters -- measured on realisations
      it has NOT seen -- divided by that digit's own limiting radius. Dividing
      by each class's own limit is what puts ten quantities of different size
      on one axis; it does not change any curve's shape.

  The panel subtitle carries what the division removes: the spread of the ten
      limits. That is the part that is a property of the concepts, and it is
      not small -- a factor of 2.3 in UCI.

Identity is carried by position and by the table, not by colour: ten hues for
ten curves that lie on top of each other would be ten hues spent on nothing.

Palette and style are figure_one.py's, unchanged.

    python src/figure_digits_per_class.py run_o ../v8_final/tex
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as F
from figstyle import BLUE, ORANGE, INK, MUTED, GRID, SURF, GHOST

SETS = [("UCI digits 8x8", "UCI, $8\\times8$"),
        ("MNIST 28x28", "MNIST, $28\\times28$"),
        ("Spoken digits (FSDD)", "Spoken, log-mel")]


def build(run, outdir):
    D = json.load(open(os.path.join(run, "convergence.json")))["digits"]
    missing = [k for k, _ in SETS if k not in D or "per_subset" not in D[k]]
    if missing:
        raise SystemExit(f"convergence.json no tiene per_subset para {missing}")

    F.apply()
    fig, axes = plt.subplots(1, 3, figsize=F.size(1.0, 3.30))
    rows = {}
    for ax, (key, pretty) in zip(axes, SETS):
        ps = D[key]["per_subset"]
        F.style(ax)
        ax.set_xscale("log")
        ax.axhspan(0.90, 1.10, color=BLUE, alpha=.07, zorder=1, lw=0)
        ax.axhline(1.0, color=MUTED, lw=.9, ls=(0, (4, 3)), zorder=2)

        limits, e10 = [], []
        for c in map(str, range(10)):
            s = ps[c]
            n = np.array(s["steps"], float)
            r = np.array([v[0] for v in s["r_mean"]], float) / s["r_true"]
            ax.plot(n, r, color=INK, lw=1.0, alpha=.42,
                    solid_capstyle="round", zorder=4)
            limits.append(s["r_true"])
            e10.append(s["crossings"].get("within_10pct"))
            rows.setdefault(c, {})[key] = (s["r_true"],
                                           s["crossings"].get("within_10pct"),
                                           s["crossings"].get("within_5pct"))
        lo, hi = min(x for x in e10 if x), max(x for x in e10 if x)
        # Where all ten concepts cross at the same n the span has zero width
        # and vanishes. That case is the strongest one in the figure, so it
        # gets a line rather than nothing.
        if hi > lo:
            ax.axvspan(lo, hi, color=ORANGE, alpha=.13, zorder=3, lw=0)
        else:
            ax.axvline(lo, color=ORANGE, alpha=.55, lw=2.2, zorder=3)
        L = np.array(limits)
        ax.set_xlim(1, max(2e2, ax.get_xlim()[1] * 0))
        ax.set_xlim(1, 200)
        ax.set_ylim(.93, 2.35)
        ax.set_xlabel("realisations encountered, $n$")
        F.title(ax, pretty, pad=12)
        # The second line carries what the division removes: the spread of the
        # ten limits. It is a fact about the concepts, so it belongs in the
        # panel; the reading of it belongs in the caption.
        # three significant figures: the exact limits are in the table
        F.sub(ax, f"limits {L.min():.3f}\u2013{L.max():.3f} "
                  f"($\\times${L.max()/L.min():.2f})")
        print(f"    {pretty}: limits {L.min():.4f}..{L.max():.4f} "
              f"(x{L.max()/L.min():.2f}), all ten within 10% by n={hi:.0f}")
    axes[0].set_ylabel("estimated radius $\\div$\nthat digit's own limit")

    fig.legend(handles=[
        Line2D([], [], color=INK, lw=1.0, alpha=.42,
               label="one curve per digit (10 per set)"),
        Patch(facecolor=BLUE, alpha=.07, label="within 10% of the limit"),
        Patch(facecolor=ORANGE, alpha=.13,
              label="range over which the ten enter"),
    ], loc="lower center", ncol=3, labelcolor=INK,
        bbox_to_anchor=(0.5, -0.012))
    fig.subplots_adjust(left=.125, right=.985, top=.855, bottom=.30, wspace=.22)
    png = os.path.join(outdir, "fig_digits_per_class.png")
    F.save(fig, png)

    tex = os.path.join(outdir, "table_digits_per_class.tex")
    with open(tex, "w") as f:
        f.write("\\begin{tabular}{lrrrrrr}\n\\toprule\n")
        f.write("& \\multicolumn{2}{c}{UCI $8\\times8$} & "
                "\\multicolumn{2}{c}{MNIST $28\\times28$} & "
                "\\multicolumn{2}{c}{Spoken (FSDD)} \\\\\n")
        f.write("\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}\n")
        f.write("digit & limit & $n_{10\\%}$ & limit & $n_{10\\%}$ & "
                "limit & $n_{10\\%}$ \\\\\n\\midrule\n")
        for c in map(str, range(10)):
            cells = []
            for key, _ in SETS:
                rt, n10, _n5 = rows[c][key]
                cells += [f"{rt:.4f}", f"{n10}" if n10 else "--"]
            f.write(f"{c} & " + " & ".join(cells) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
        f.write("% limit = the radius over every realisation of that concept.\n"
                "% n_10% = smallest n after which the estimate stays within\n"
                "%   ten per cent of that limit; same criterion as the body.\n")
    print(f"    {tex}")


if __name__ == "__main__":
    a = sys.argv[1:]
    build(a[0] if a else "run_o", a[1] if len(a) > 1 else "../v8_final/tex")
