"""One template for every figure in the paper.

Why this file exists
--------------------
Before it, each figure script set its own figsize, dpi and font sizes, and
every one of them drew wider than the page. The manuscript's text block is
469.755pt = 6.503in. `figure_one.py` drew at 13.6in, so LaTeX scaled it by
0.478 and a nominal 9pt label reached the reader at 4.3pt. That is the whole
of the "no se ven los digitos y las letras" defect: the numbers in the scripts
were fine, the scale factor was not.

The rule here is that a figure is authored at the width it is *included* at,
so the scale factor is exactly 1 and a point is a point. `size(frac, h)` is
the only way to make a figure; it refuses to guess.

Conventions this file enforces
------------------------------
  * Titles are sober: they name what the panel plots, in the paper's own
    vocabulary, and never argue. `title()` sets one; `sub()` adds a second
    line for a fact the panel carries, such as the range a normalisation
    removed. `ident()` is for the short name over one panel of a small
    multiple. What a title must never do is state the conclusion, address
    the reader, or point at the data with an arrow: the caption makes the
    argument and the axes carry the evidence.
  * Sans-serif throughout, including mathtext, so $n$ and $\\varepsilon$ in an
    axis label match the surrounding tick labels.
  * Colour is assigned from CAT in fixed order and never cycled. Four slots:
    no figure in this paper carries more than four coloured series. The fourth
    is vermillion rather than Okabe-Ito's reddish purple, which does not clear
    CVD separation against the green in slot three.
  * Identity is never colour alone. Every coloured series is also named, by
    legend or direct label.

Palette
-------
Okabe-Ito, validated with the dataviz validator at surface #fcfcfb,
`--pairs all`: lightness band PASS, chroma floor PASS, CVD separation PASS
(worst 11.0 deutan), normal-vision floor PASS (worst 15.6). The one WARN is
contrast of #E69F00 against the surface, which is discharged the way the
validator asks: every orange mark in this paper is directly labelled or
legended, never colour-alone.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ------------------------------------------------------------------ geometry
TEXTWIDTH_PT = 469.755          # \the\textwidth of the manuscript
PT_PER_IN    = 72.27            # TeX points
TEXTWIDTH_IN = TEXTWIDTH_PT / PT_PER_IN      # 6.5003
TEXTHEIGHT_IN = 541.400 / PT_PER_IN          # 7.4913, one full page of body

# ------------------------------------------------------------------- palette
CAT   = ("#0072B2", "#E69F00", "#009E73", "#D55E00")   # fixed order, never cycled
BLUE, ORANGE, GREEN, VERMILLION = CAT

INK   = "#1a1a19"      # primary text
MUTED = "#6b6b68"      # secondary text, ticks
GRID  = "#e2e2df"      # gridlines, spines
GHOST = "#c9c9c6"      # unemphasised data (the many, behind the one)
SURF  = "#fcfcfb"      # figure surface; the validated background

# ---------------------------------------------------------------- type sizes
# Authored 1:1, so these are the sizes the reader sees on the page. The body
# text is 11pt; figures sit one step below it.
BASE   = 9.0
TICK   = 8.0
LEGEND = 8.5
IDENT  = 8.5           # short identifier on a small multiple
PANEL  = 10.0          # the (a) (b) (c) markers

DPI = 400              # print; MIR asks for >= 300


def apply() -> None:
    """Set the rcParams. Call once, before any figure is made."""
    plt.rcParams.update({
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "figure.facecolor": SURF,
        "savefig.facecolor": SURF,
        "savefig.bbox": None,          # honour the authored size exactly
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "mathtext.fontset": "dejavusans",
        "font.size": BASE,
        "axes.titlesize": BASE,
        "axes.labelsize": BASE,
        "axes.labelcolor": INK,
        "axes.edgecolor": GRID,
        "axes.facecolor": SURF,
        "axes.linewidth": 0.8,
        "axes.grid": False,
        "axes.prop_cycle": plt.cycler(color=list(CAT)),
        "xtick.labelsize": TICK,
        "ytick.labelsize": TICK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.fontsize": LEGEND,
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        "legend.handletextpad": 0.5,
        "legend.borderaxespad": 0.4,
        "lines.linewidth": 1.4,
        "lines.markersize": 5.0,
        "text.color": INK,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def size(frac: float, height_in: float) -> tuple[float, float]:
    """Figure size in inches for a figure included at `frac`*\\textwidth.

    `frac` must match the \\includegraphics width in the .tex exactly, or the
    scale factor stops being 1 and the point sizes above stop being true.
    """
    if not 0.2 <= frac <= 1.0:
        raise ValueError(f"frac={frac} outside [0.2, 1.0]")
    if height_in > TEXTHEIGHT_IN:
        raise ValueError(
            f"height {height_in:.2f}in exceeds one page ({TEXTHEIGHT_IN:.2f}in)")
    return (TEXTWIDTH_IN * frac, height_in)


def style(ax, grid: bool = True, spines: str = "lb") -> None:
    """The standard axes treatment: recessive grid, two spines, muted ticks."""
    ax.set_facecolor(SURF)
    if grid:
        ax.grid(True, which="major", color=GRID, lw=0.7, zorder=0)
        ax.set_axisbelow(True)
    for s, keep in (("left", "l" in spines), ("bottom", "b" in spines),
                    ("top", "t" in spines), ("right", "r" in spines)):
        ax.spines[s].set_visible(keep)
        if keep:
            ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=TICK, length=3, width=0.8)


def bare(ax) -> None:
    """An axes that carries an image and nothing else."""
    ax.set_facecolor(SURF)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])


def panel(ax, letter: str, dx: float = -0.02, dy: float = 1.04) -> None:
    """The (a) (b) (c) marker, in axes coordinates, above the axes."""
    ax.text(dx, dy, f"({letter})", transform=ax.transAxes, color=INK,
            fontsize=PANEL, fontweight="bold", ha="left", va="bottom")


def title(ax, text: str, pad: float = 5.0) -> None:
    """A sober panel title: what this panel plots, left-aligned.

    Names the quantity; does not say what it shows. "Radius estimate against
    sample size" is a title. "The elbow, per curve" is not.
    """
    ax.set_title(text, color=INK, fontsize=BASE, loc="left", pad=pad)


def sub(ax, text: str, dy: float = 1.02) -> None:
    """A second line under a title, for a fact the panel itself carries."""
    ax.text(0.0, dy, text, transform=ax.transAxes, color=MUTED,
            fontsize=TICK, ha="left", va="bottom")


def ident(ax, text: str, dy: float = 1.02) -> None:
    """A short identifier over one panel of a small multiple.

    This is a label, not a title: it names which of several things the panel
    shows, in as few words as the reader needs, and never describes it.
    """
    ax.text(0.0, dy, text, transform=ax.transAxes, color=INK, fontsize=IDENT,
            ha="left", va="bottom")


def save(fig, path: str) -> None:
    fig.savefig(path, dpi=DPI, facecolor=SURF)
    print(f"wrote {path}  ({fig.get_size_inches()[0]:.3f} x "
          f"{fig.get_size_inches()[1]:.3f} in @ {DPI} dpi)")
