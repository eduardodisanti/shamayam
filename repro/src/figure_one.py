"""Figure 1 -- seven phenomena, ten curves, one elbow.

The figure the introduction needs, and it is made of data, not of a diagram.

  Top row. One concept from each of the seven phenomena the paper measures.
      Sixty realisations in grey and one in blue, or -- where the realisation
      is an image rather than a trace -- three of them. Nothing here is
      normalised, aligned or selected beyond what the corresponding stage of
      reproduce.py already does: this is what the observer is shown.

  Bottom left (b). The nine convergence curves on one axis. Each is the
      radius an observer estimates for its concept from n encounters,
      measured on realisations it has NOT seen, divided by that concept's own
      limiting radius. Dividing by the limit is what puts nine quantities
      with nine different units on one axis; it does not move any curve's
      shape. The nine lie on top of each other.

  Bottom right (c). Where each curve enters its limit and stays there, at two
      tolerances. Identity is carried by position, not by colour, which is
      why nine series need no nine hues.

The claim the figure carries is CONVERGENCE, not a constant. A curve that
settles at n=10 and one that settles at n=12 say the same thing; what would
falsify the paper is a curve that does not settle at all. That is also the
form in which the result is used downstream, as an applicability diagnostic:
non-convergence says the process is outside the assumption, not that the
method is slow.

Palette: #2a78d6 / #eb6834 on surface #fcfcfb. Validated with the dataviz
validator, --pairs all: five PASS.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as F
from figstyle import BLUE, ORANGE, INK, MUTED, GRID, GHOST, SURF

L = 160
N_SHOW = 60


def medoid(A):
    """The realisation closest to the middle of the set. Highlighting the
    first row instead would put an accident of file order in the figure."""
    c = A.mean(0, keepdims=True)
    return int(np.argmin(((A - c) ** 2).sum(1)))


# ---------------------------------------------------------------------- data
def grid_to(A, n=L):
    A = np.asarray(A, float)
    if A.shape[1] == n:
        return A
    xo, xn = np.linspace(0, 1, A.shape[1]), np.linspace(0, 1, n)
    return np.stack([np.interp(xn, xo, r) for r in A])


def load_pm(root, k=N_SHOW):
    import pandas as pd
    fs = sorted(glob.glob(f"{root}/pm/kaggle_nominal/J1_normal_to_reverse_*.parquet"))
    if not fs:
        raise SystemExit(f"sin parquet PM bajo {root}/pm/kaggle_nominal")
    g = np.random.default_rng(0)
    out = []
    for f in [fs[i] for i in g.choice(len(fs), min(k, len(fs)), replace=False)]:
        p = pd.read_parquet(f)["Power"].to_numpy(float)
        out.append(np.interp(np.linspace(0, 1, L), np.linspace(0, 1, len(p)), p))
    return np.stack(out)


def kt_ok(A):
    """Drop the NSRDB fill days.

    The solar observable is the clearness index, global over extraterrestrial
    irradiance. It cannot be negative, and 3862 of the 7203 days in the
    clear-sky subset are: they are fill values, and after l2-normalisation
    they collapse to thirty identical vectors -- one per daylight length.
    They are not days and they are not shown.
    """
    A = np.asarray(A, float)
    return A[~(A < 0).any(1)]


def pick(A, k=N_SHOW, seed=0):
    A = np.asarray(A, float)
    g = np.random.default_rng(seed)
    return A[g.choice(len(A), min(k, len(A)), replace=False)]


# --------------------------------------------------------------- convergence
def curve(rec):
    """(n, radius / limiting radius). The division is the only transform."""
    n = np.array(rec["steps"], float)
    r = np.array(rec["r_mean"], float)[:, 0] / float(rec["r_true"])
    return n, r


def enters(n, q, frac):
    """First n from which the curve is within `frac` of the limit and never
    leaves again. Same rule as reproduce.crossings; recomputed here so the
    figure does not depend on which aggregates happened to store it."""
    inside = np.abs(q - 1.0) <= frac
    for i in range(len(n)):
        if inside[i:].all():
            return float(n[i])
    return None


# --------------------------------------------------------------------- build
def build(root, run, out):
    conv = json.load(open(f"{run}/convergence.json"))
    S = {**conv.get("domains", {}), **conv.get("digits", {})}
    xtra = np.load(f"{run}/cache/conv_extra.npz")
    # Through the loader, so the panel shows the representation that was
    # measured: the cache holds the zero-padded observable and
    # src/audio_mnist.py applies the declared duration quotient on top.
    from audio_mnist import load_spoken
    _sx, _sy, _ = load_spoken(None, f"{run}/cache/spoken.npz")
    spk = {"X": np.asarray(_sx, float), "y": np.asarray(_sy).astype(int)}
    from sklearn.datasets import load_digits
    Xd, yd = load_digits(return_X_y=True)

    # -- top row: one concept per phenomenon, in the order of the dot plot ---
    traces = [
        ("Point machine", "power, one manoeuvre",
         grid_to(load_pm(root))),
        ("ECG, normal beat", "MIT-BIH, aligned",
         grid_to(pick(np.load(f"{root}/ecg/field_ecg_dataset_aligned_normalized.npy"), seed=1))),
        ("Battery", "NASA, voltage",
         grid_to(pick(np.load(f"{root}/batteries/field_discharges_dataset.npy"), seed=2))),
        ("Tide", "NOAA, Boston, one day",
         pick(xtra["NOAA tides||Boston"], seed=3)),
        ("Solar irradiance", "NSRDB, clear-sky day",
         pick(kt_ok(xtra["NSRDB solar (GHI)||clear"]), seed=4)),
    ]
    sp3 = spk["X"][spk["y"] == 3][:3].reshape(-1, 64, 101)
    # no crop: the duration quotient already removed the padding
    dg3 = Xd[yd == 3][:9].reshape(-1, 8, 8)

    # Each row is (label, first curve, second curve or None, (tag, tag)).
    # The tags are per row and not global: for the point machine and the ECG
    # the second curve IS the simulator, but the two handwritten sets are both
    # measured -- writing "simulated" there, as an earlier version did, states
    # something false about MNIST.
    rows = [("Point machine", "PM real (nominal)", "PM simulated",
             ("measured", "simulated")),
            ("ECG", "ECG real (MIT-BIH)", "ECG simulated",
             ("measured", "simulated")),
            ("Battery", "Battery real (NASA)", None, ("", "")),
            ("Tides", "NOAA tides", None, ("", "")),
            ("Solar", "NSRDB solar (GHI)", None, ("", "")),
            ("Spoken digits", "Spoken digits (FSDD)", None, ("", "")),
            ("Handwritten digits", "UCI digits 8x8", "MNIST 28x28",
             ("UCI", "MNIST"))]
    keys = [k for _, a, b, _ in rows for k in (a, b) if k]
    missing = [k for k in keys if k not in S]
    if missing:
        raise SystemExit(f"convergence.json no tiene {missing}")

    # Authored at the width it is included at (width=\textwidth), so the point
    # sizes in figstyle are the point sizes the reader sees.
    F.apply()
    fig = plt.figure(figsize=F.size(1.0, 7.15))
    gs = GridSpec(4, 12, figure=fig, height_ratios=[0.78, 0.78, 2.10, 2.10],
                  hspace=.52, wspace=.95,
                  left=.110, right=.975, top=.955, bottom=.055)

    # -- (a) one concept per phenomenon -------------------------------------
    # Four panels on the first row, three on the second. Seven across 6.5in
    # would be 0.93in each, which is where the old figure became unreadable.
    cells = [gs[0, 0:3], gs[0, 3:6], gs[0, 6:9], gs[0, 9:12],
             gs[1, 0:4], gs[1, 4:8], gs[1, 8:12]]

    for j, (nm, sub_, A) in enumerate(traces):
        ax = fig.add_subplot(cells[j])
        F.style(ax, grid=False)
        ax.set_yticks([]); ax.set_xticks([])
        x = np.linspace(0, 1, A.shape[1])
        for r in A:
            ax.plot(x, r, color=GHOST, lw=.5, alpha=.55, zorder=1)
        ax.plot(x, A[medoid(A)], color=BLUE, lw=1.5, zorder=3)
        F.title(ax, nm, pad=12)
        F.sub(ax, sub_)

    ax = fig.add_subplot(cells[5])
    F.bare(ax); F.title(ax, "Spoken digit /3/", pad=12)
    F.sub(ax, "FSDD, log-mel, 3 speakers")
    v0, v1 = np.percentile(sp3, 3), np.percentile(sp3, 99.6)
    ax.imshow(np.concatenate([np.pad(s, ((3, 3), (0, 0)),
                                     constant_values=v0) for s in sp3][::-1], 0),
              aspect="auto", origin="lower", cmap="Blues", vmin=v0, vmax=v1,
              interpolation="nearest")

    ax = fig.add_subplot(cells[6])
    F.bare(ax); F.title(ax, "Handwritten digit 3", pad=12)
    F.sub(ax, "UCI, $8\\times8$, 9 writings")
    ax.set_anchor("N")   # square pixels, box pinned to the top of its cell
    ax.imshow(np.block([[dg3[3 * a + b] for b in range(3)] for a in range(3)]),
              cmap="Blues", interpolation="nearest")

    # -- (b) the convergence curves -----------------------------------------
    axb = fig.add_subplot(gs[2, :])
    F.style(axb); axb.set_xscale("log")
    axb.axhspan(0.90, 1.10, color=BLUE, alpha=.09, zorder=1, lw=0)
    axb.axhline(1.0, color=MUTED, lw=.9, ls=(0, (4, 3)), zorder=2)

    for k in keys:
        n, q = curve(S[k])
        axb.plot(n, q, color=INK, lw=1.0, alpha=.45, solid_capstyle="round",
                 zorder=4)

    e10 = [enters(*curve(S[k]), .10) for k in keys]
    e05 = [enters(*curve(S[k]), .05) for k in keys]
    lo, hi = min(e10), max(e10)
    axb.axvspan(lo, hi, color=ORANGE, alpha=.16, zorder=3, lw=0)

    axb.set_xlim(1, 1000); axb.set_ylim(.93, 2.35)
    F.title(axb, "Radius estimate against sample size")
    axb.set_xlabel("realisations encountered, $n$")
    axb.set_ylabel("estimated radius $\\div$ its own limit")
    axb.legend(handles=[
        Line2D([], [], color=INK, lw=1.0, alpha=.45,
               label="one curve per class (%d curves)" % len(keys)),
        Patch(facecolor=BLUE, alpha=.09, label="within 10% of the limit"),
        Patch(facecolor=ORANGE, alpha=.16,
              label="every curve enters here (n = %.0f to %.0f)" % (lo, hi)),
    ], loc="upper right", labelcolor=INK)


    # -- (c) where each one enters and stays --------------------------------
    axc = fig.add_subplot(gs[3, :])
    _bb = axc.get_position()
    axc.set_position([0.285, _bb.y0, 0.975 - 0.285, _bb.height])
    F.style(axc); axc.set_xscale("log")
    labels, ys = [], []
    y = 0
    for pretty, a, b, tg in reversed(rows):
        for k, tag in ((b, tg[1]), (a, tg[0])):
            if not k:
                continue
            i = keys.index(k)
            axc.plot([e10[i], e05[i]], [y, y], color=GRID, lw=1.4, zorder=2)
            axc.plot([e10[i]], [y], "o", ms=6, color=BLUE, mec=SURF, mew=1.4,
                     zorder=4)
            if e05[i]:
                axc.plot([e05[i]], [y], "o", ms=6, color=ORANGE, mec=SURF,
                         mew=1.4, zorder=4)
            labels.append(pretty if b is None else f"{pretty}, {tag}")
            ys.append(y)
            y += 1
    axc.set_yticks(ys); axc.set_yticklabels(labels, fontsize=F.TICK, color=INK)
    axc.set_ylim(-.7, y - .3)
    axc.set_xlim(6, 400)
    F.title(axc, "Entry into the band, per curve")
    axc.set_xlabel("$n$ at which the estimate enters the band, and stays")
    axc.legend(handles=[
        Line2D([], [], ls="none", marker="o", ms=6, color=BLUE, mec=SURF,
               mew=1.4, label="within 10%"),
        Line2D([], [], ls="none", marker="o", ms=6, color=ORANGE, mec=SURF,
               mew=1.4, label="within 5%"),
    ], loc="lower right", ncol=2, labelcolor=INK)

    # -- panel letters, in figure coordinates ------------------------------
    for letter, a in (("a", fig.axes[0]), ("b", axb), ("c", axc)):
        bb = a.get_position()
        # clear of the rotated y-axis label, whose top reaches the axes top
        fig.text(0.012, bb.y1 + (0.030 if letter == "a" else 0.021), f"({letter})",
                 color=INK, fontsize=F.PANEL, fontweight="bold",
                 ha="left", va="bottom")

    F.save(fig, out)
    for k, a, b in zip(keys, e10, e05):
        print(f"    {k:24s} 10% n={a}   5% n={b}")


if __name__ == "__main__":
    a = sys.argv[1:]
    root = a[0] if len(a) > 0 else "data"
    run = a[1] if len(a) > 1 else "run_m"
    out = a[2] if len(a) > 2 else "fig1_seven_phenomena.png"
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    build(root, run, out)
