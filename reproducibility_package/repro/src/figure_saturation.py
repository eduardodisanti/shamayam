"""The saturation curve, on the quantity that matters: what an observer can
recognise after n encounters.

Three candidates were tried before this one and each failed for a reason worth
recording, because each was the quantity an earlier version of this work
plotted.

  - The median distance between pairs within a class is already at its final
    value from TWO encounters. That is a result -- the typical spread of a
    class is knowable almost immediately -- but a flat line is not an argument.

  - The covering number |S_n| keeps creeping at every sample size we can reach.
    It has to: a covering number is a functional of the SUPPORT, so by
    prop:bulk(ii) it inherits exactly the non-convergence of the boundary. It
    grows sub-linearly, which is the compression the paper reports, but it does
    not plateau, and drawing it on log axes hides that.

  - The mean radius to a centroid does rise, elbow and flatten, and is a
    functional of the measure, so it converges. It was the right shape. It
    needs a centroid, which the rest of this work does without.

What is left is recognition itself. Accuracy is an average -- a functional of
the measure -- so prop:bulk(i) applies: it settles, and it settles fast. The
elbow is real, it is where the paper's claim lives, and it is what a reader
means by learning.

The elbow is declared, not fitted: the smallest n reaching ELBOW_FRAC of the
accuracy at the largest n measured. Same rule as table_learning.

Palette: #2a78d6 / #eb6834 / #1baf7a, light surface #fcfcfb, all checks PASS.
"""
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SURF = "#1a1a19", "#6b6b68", "#e2e2df", "#fcfcfb"
COLOR = {"1-NN": BLUE, "linear SVM": ORANGE, "logistic": AQUA}
ELBOW_FRAC = 0.95


def style(ax):
    ax.set_facecolor(SURF)
    ax.grid(True, color=GRID, lw=.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)


def serie(curva):
    ns = sorted(int(k) for k in curva)
    return np.array(ns), np.array([curva[str(n)][0] for n in ns])


def elbow(ns, acc):
    top = acc[-1]
    for n, a in zip(ns, acc):
        if a >= ELBOW_FRAC * top:
            return int(n), float(a)
    return int(ns[-1]), float(acc[-1])


def build(run, out):
    lc = json.load(open(f"{run}/learning.json"))["datasets"]
    # prefer the higher-resolution dataset when the run has it
    nombre = ("MNIST 28x28" if "MNIST 28x28" in lc else sorted(lc)[0])
    conds = lc[nombre]["conditions"]
    cq = ("quotient (deskew)" if "quotient (deskew)" in conds
          else sorted(conds)[0])
    craw = "raw" if "raw" in conds else cq

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6))
    for ax in axes:
        style(ax)
        ax.set_xscale("log")

    # ---- A: three instruments, one quotient, the elbow marked --------------
    ax = axes[0]
    codos, finales = [], []
    for nm, curva in conds[cq]["curves"].items():
        if not curva:
            continue
        ns, acc = serie(curva)
        c = COLOR.get(nm, MUTED)
        ax.plot(ns, acc, lw=2, color=c, zorder=3)
        e, a = elbow(ns, acc)
        codos.append(e)
        ax.plot([e], [a], "o", ms=9, color=c, zorder=4,
                markeredgecolor=SURF, markeredgewidth=1.8)
        finales.append((float(acc[-1]), nm, c))
    # The three curves end within a point or two of each other, so labelling
    # each at its own final value writes them on top of one another. Space them
    # by hand, in axes coordinates, keeping their order.
    lo, hi = ax.get_ylim()
    finales.sort()
    pos, GAP = [], .085
    for v, nm, c in finales:
        f = (v - lo) / (hi - lo)
        if pos and f - pos[-1] < GAP:
            f = pos[-1] + GAP
        pos.append(f)
    for (v, nm, c), f in zip(finales, pos):
        ax.annotate(nm, (1.0, f), xycoords="axes fraction",
                    textcoords="offset points", xytext=(7, 0), color=c,
                    fontsize=9, fontweight="bold", va="center",
                    annotation_clip=False)
    if codos:
        lo, hi = min(codos), max(codos)
        ax.axvspan(lo, hi, color=MUTED, alpha=.10, zorder=1)
        # what the rest of the curve buys
        ns, acc = serie(conds[cq]["curves"].get("1-NN")
                        or list(conds[cq]["curves"].values())[0])
        j = int(np.argmin(np.abs(ns - hi)))
        ganancia = acc[-1] - acc[j]
        factor = ns[-1] / max(ns[j], 1)
        ax.text(.97, .06,
                f"from the elbow to the end:\n"
                f"{factor:.0f}$\\times$ more encounters buy "
                f"{ganancia * 100:.1f} points",
                transform=ax.transAxes, ha="right", va="bottom", color=INK,
                fontsize=9.5)
    ax.set_xlabel("encounters per concept  $n$", color=INK, fontsize=10)
    ax.set_ylabel("recognised correctly", color=INK, fontsize=10)
    ax.set_title(f"A · {nombre}, {cq}", color=INK, fontsize=11, loc="left")
    ax.set_xlim(right=max(ns) * 1.6)

    # ---- B: what declaring the invariance moves ---------------------------
    ax = axes[1]
    inst = "1-NN" if "1-NN" in conds[cq]["curves"] else \
        sorted(conds[cq]["curves"])[0]
    finales = []
    for cond, color, dash in ((craw, MUTED, (4, 3)), (cq, BLUE, None)):
        curva = conds[cond]["curves"].get(inst)
        if not curva:
            continue
        ns, acc = serie(curva)
        ax.plot(ns, acc, lw=2.2, color=color, zorder=3,
                dashes=dash if dash else (None, None))
        e, a = elbow(ns, acc)
        ax.plot([e], [a], "o", ms=9, color=color, zorder=4,
                markeredgecolor=SURF, markeredgewidth=1.8)
        finales.append((float(acc[-1]), f"{cond}  ·  $n$={e}", color))
    lo, hi = ax.get_ylim()
    finales.sort()
    pos, GAP = [], .085
    for v, lbl, c in finales:
        f = (v - lo) / (hi - lo)
        if pos and f - pos[-1] < GAP:
            f = pos[-1] + GAP
        pos.append(f)
    for (v, lbl, c), f in zip(finales, pos):
        ax.annotate(lbl, (1.0, f), xycoords="axes fraction",
                    textcoords="offset points", xytext=(7, 0), color=c,
                    fontsize=9, fontweight="bold", va="center",
                    annotation_clip=False)
    ax.set_xlabel("encounters per concept  $n$", color=INK, fontsize=10)
    ax.set_ylabel("recognised correctly", color=INK, fontsize=10)
    ax.set_title(f"B · {inst}, with and without the declared invariance",
                 color=INK, fontsize=11, loc="left")
    ax.set_xlim(right=max(ns) * 1.6)

    fig.text(.5, .015,
             f"dots: the fewest encounters reaching "
             f"{int(ELBOW_FRAC * 100)}% of that curve's own best",
             ha="center", color=MUTED, fontsize=9)
    fig.tight_layout(rect=[0, .045, 1, 1])
    fig.savefig(out, dpi=160, facecolor=SURF,
                metadata={"Software": None, "Creation Time": None})
    info = {"dataset": nombre, "quotient": cq, "elbow_fraction": ELBOW_FRAC,
            "elbows": {nm: elbow(*serie(c))[0]
                       for nm, c in conds[cq]["curves"].items() if c}}
    print(f"    fig_saturation: {nombre}, codos {info['elbows']}", flush=True)
    return info


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1], sys.argv[2]), indent=1, sort_keys=True))
