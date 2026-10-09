"""The three synthetic-generator figures, on the shared template.

Each of these existed only as a cell in a notebook, saved by hand. They are
rebuilt here from the arrays the notebooks wrote, so the figures in the paper
have a generator that can be re-run:

    mc_pm_dataset.npy            -> pm_ac_gen_results.png
    mc_ecg_mcsharry_dataset.npy  -> mc_mcsharry_generator.png
    mc_ecg_gaussian_dataset.npy  -> ecg_gaussian_mc_gen.png

What changed besides the size and the font. The old point-machine panel drew
the field signals in lime green over grey, which is neither legible in print
nor separable under any colour-vision deficiency; it is now the paper's own
blue over the same grey, with a legend. None of the three carried axis labels
and one carried the raw variable name as its title. The data drawn is the
same data.

    python src/figure_generators.py <datasets_root> <outdir>
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as F
from figstyle import BLUE, ORANGE, INK, MUTED, GHOST, SURF

N_DRAW = 2000          # how many realisations to draw; the rest are identical ink


def _thin(A, k=N_DRAW, seed=0):
    A = np.asarray(A, float)
    if len(A) <= k:
        return A
    g = np.random.default_rng(seed)
    return A[g.choice(len(A), k, replace=False)]


def _field_pm(root, k=400, L=160):
    """The measured RMS pool, on the same 160-point grid as the simulator."""
    import pandas as pd
    fs = sorted(glob.glob(f"{root}/pm/kaggle_nominal/*.parquet"))
    if not fs:
        return None
    g = np.random.default_rng(0)
    out = []
    for f in [fs[i] for i in g.choice(len(fs), min(k, len(fs)), replace=False)]:
        p = pd.read_parquet(f)["Power"].to_numpy(float)
        out.append(np.interp(np.linspace(0, 1, L), np.linspace(0, 1, len(p)), p))
    return np.stack(out)


def pm(root, out):
    """Simulated against measured, as two populations.

    The notebook version drew eight thousand simulated traces and the field
    pool on top of each other; whichever was drawn second hid the other
    completely, so the comparison the figure exists to make was not visible.
    Each population is now its pointwise median and its 5th-to-95th percentile
    band. Both are divided by their own plateau median, because the two are
    recorded in different units and the figure is about the shape.
    """
    sim = np.load(f"{root}/pm/mc_pm_dataset.npy")
    fld = _field_pm(root, k=800)

    def band(ax, A, colour, label):
        A = np.asarray(A, float)
        A = A / np.median(A[:, 40:120])
        lo, md, hi = np.percentile(A, [5, 50, 95], axis=0)
        x = np.arange(A.shape[1])
        ax.fill_between(x, lo, hi, color=colour, alpha=.22, lw=0, zorder=2)
        ax.plot(x, md, color=colour, lw=1.3, zorder=3)
        return plt.Line2D([], [], color=colour, lw=1.3, label=label)

    fig, ax = plt.subplots(figsize=F.size(0.90, 2.7))
    F.style(ax)
    h = [band(ax, sim, ORANGE, f"simulated ({len(sim)})")]
    if fld is not None:
        h.append(band(ax, fld, BLUE, f"measured ({len(fld)} drawn)"))
    F.title(ax, "Simulated and measured RMS envelopes")
    ax.set_xlabel("sample index (160-point grid)")
    ax.set_ylabel("RMS $\\div$ its own\nplateau median")
    ax.set_xlim(0, sim.shape[1] - 1)
    h.append(plt.Line2D([], [], color=MUTED, lw=6, alpha=.22,
                        label="5th to 95th percentile"))
    ax.legend(handles=h, loc="upper right", labelcolor=INK)
    fig.subplots_adjust(left=.135, right=.985, top=.885, bottom=.19)
    F.save(fig, out)


def _beats(path, out, rpeak, frac, label, title_):
    A = np.load(path)
    fig, ax = plt.subplots(figsize=F.size(frac, 2.5))
    F.style(ax)
    for b in _thin(A):
        ax.plot(b, color=GHOST, lw=.5, alpha=.05, zorder=1)
    ax.plot(np.median(A, 0), color=BLUE, lw=1.4, zorder=3)
    ax.axvline(rpeak, color=ORANGE, lw=1.2, ls=(0, (4, 3)), zorder=4)
    F.title(ax, title_)
    ax.set_xlabel("sample index (128-point beat)")
    ax.set_ylabel("amplitude, normalised")
    ax.set_xlim(0, A.shape[1] - 1)
    ax.legend(handles=[
        plt.Line2D([], [], color=GHOST, lw=1.6, label=f"{label} ({len(A)})"),
        plt.Line2D([], [], color=BLUE, lw=1.4, label="pointwise median"),
        plt.Line2D([], [], color=ORANGE, lw=1.2, ls=(0, (4, 3)),
                   label=f"R-peak alignment index ({rpeak})"),
    ], loc="upper right", labelcolor=INK)
    fig.subplots_adjust(left=.105, right=.985, top=.885, bottom=.20)
    F.save(fig, out)


def main(root, outdir):
    F.apply()
    pm(root, os.path.join(outdir, "pm_ac_gen_results.png"))
    _beats(f"{root}/ecg/mc_ecg_mcsharry_dataset.npy",
           os.path.join(outdir, "mc_mcsharry_generator.png"),
           rpeak=64, frac=0.95, label="McSharry beats",
           title_="Monte Carlo beats, McSharry dynamical model")
    _beats(f"{root}/ecg/mc_ecg_gaussian_dataset.npy",
           os.path.join(outdir, "ecg_gaussian_mc_gen.png"),
           rpeak=65, frac=0.95, label="Gaussian beats",
           title_="Monte Carlo beats, Gaussian morphological emulator")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0] if a else "data", a[1] if len(a) > 1 else "../v8_final/tex")
