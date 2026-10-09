"""Show the data, not the statistic.

Every realisation an observer met, in grey; the handful it kept, in colour.
The point is meant to land before any number does: six hundred manoeuvres, and
three of them stand for all of it.
"""
import glob, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/home/claude/v8/src")
from run_experiment import l2_normalise, z_normalise, greedy_net

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SURF, GHOST = "#1a1a19", "#6b6b68", "#e2e2df", "#fcfcfb", "#c9c9c6"
L = 160


def style(ax):
    ax.set_facecolor(SURF); ax.grid(True, color=GRID, lw=.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)


def grid_to(A):
    A = np.asarray(A, float)
    if A.shape[1] == L: return A
    xo, xn = np.linspace(0, 1, A.shape[1]), np.linspace(0, 1, L)
    return np.stack([np.interp(xn, xo, r) for r in A])


def build(base, out):
    def pm(pat):
        o = []
        for f in sorted(glob.glob(f"{base}/pm/{pat}/J1_normal_to_reverse_*.parquet")):
            p = pd.read_parquet(f)["Power"].to_numpy(float)
            o.append(np.interp(np.linspace(0, 1, L), np.linspace(0, 1, len(p)), p))
        return np.stack(o)

    DOM = [("Railway point machine", pm("kaggle_nominal"), "l2", "manoeuvres"),
           ("ECG, normal beats (MIT-BIH)",
            np.load(f"{base}/ecg/field_ecg_dataset_aligned_normalized.npy"),
            "l2", "beats"),
           ("Battery discharge (NASA)",
            np.load(f"{base}/batteries/field_discharges_dataset.npy"),
            "znorm", "discharges")]
    Q = {"l2": l2_normalise, "znorm": z_normalise}

    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.2))
    for ax, (nm, A, q, unidad) in zip(axes, DOM):
        style(ax)
        rng = np.random.default_rng(0)
        A = grid_to(A); n = min(600, len(A))
        raw = A[rng.choice(len(A), n, replace=False)]
        X = Q[q](raw)
        D = 1 - X @ X.T
        eps = float(np.median(D[np.triu_indices(n, 1)]))
        idx = greedy_net(X, eps)[0]
        t = np.linspace(0, 1, L)
        for r in X:
            ax.plot(t, r, color=GHOST, lw=.6, alpha=.35, zorder=2)
        for k in idx:
            ax.plot(t, X[k], color=BLUE, lw=1.6, alpha=.9, zorder=4)
        ax.set_title(f"{nm}", color=INK, fontsize=11, loc="left")
        ax.text(.98, .96, f"{n} {unidad} seen", transform=ax.transAxes,
                color=MUTED, fontsize=9.5, va="top", ha="right")
        ax.text(.98, .88, f"{len(idx)} kept", transform=ax.transAxes,
                color=BLUE, fontsize=12, fontweight="bold", va="top", ha="right")
        ax.set_xlabel("normalised time", color=INK, fontsize=9.5)
        ax.set_yticks([])
    axes[0].set_ylabel("signal, in the declared quotient", color=INK, fontsize=9.5)
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=GHOST, lw=1.6,
                               label="every realisation the observer met"),
                        Line2D([], [], color=BLUE, lw=2,
                               label="the exemplars it kept")],
               loc="lower center", ncol=2, frameon=False, fontsize=9.5,
               labelcolor=MUTED, bbox_to_anchor=(.5, -.03))
    fig.tight_layout(rect=[0, .07, 1, 1])
    fig.savefig(out, dpi=160, facecolor=SURF,
                metadata={"Software": None, "Creation Time": None})
    print(f"    fig_exemplars escrita")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
