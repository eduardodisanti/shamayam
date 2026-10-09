#!/usr/bin/env python3
"""
Blueprints v8 — parameterised experiment driver.

This is the base for every experiment in the paper. Nothing is hard-coded:
dataset, quotient, metric, epsilon grid, budgets and outputs are all flags.
Every run writes a JSON with the raw numbers AND .tex fragments for \\input{},
so no number is ever typed into the paper by hand.

--------------------------------------------------------------------------
DECLARED CHOICES (Phase 0) — change them with flags, never silently
--------------------------------------------------------------------------
Quotient   l2-normalisation: signals compared modulo global amplitude.
           Cosine distance is the metric ON THE QUOTIENT (the unit sphere).
           This is a declared change of space, NOT justified by norm equivalence.
Metric     d(x, y) = 1 - <x, y>  for l2-normalised x, y.   Range [0, 2].
           eps = 0.05 <-> 18 deg, 0.10 <-> 26 deg, 0.20 <-> 37 deg.
Net        greedy: store x iff min_{y in S} d(x, y) > eps  (Gonzalez 1985,
           2-approximation). Order-dependent -> every quantity is repeated
           over --orders arrival orders and the spread is reported.
Reference  none. No centre, no centroid. S[0] is just the first arrival.

The epsilon-net and farthest-point traversal are the SAME construction read
two ways: fix eps and you get a size k; fix k and you get an eps. The probe
fixes eps (--run probe/gate); the budget experiment fixes k (--run budget),
so that a geometric support of size k is exactly comparable to k random
prototypes.

--------------------------------------------------------------------------
EXPERIMENTS
--------------------------------------------------------------------------
probe   |S(eps)| per class over the eps grid; growth |S_n| vs n; log-log slope
        of |S(eps)| vs 1/eps  (= intrinsic dimension estimate).
gate    the same, for pseudo-classes whose membership is arbitrary (labels
        shuffled across all classes). Reports |S_arb| / |S_real|.
        Both saturate — everything bounded is totally bounded. The signal is
        SIZE. Ratio -> n_classes if the class manifolds are separated at that
        eps; ratio -> 1 means the geometry does not see the concept.
budget  THE DECISIVE ONE. 1-NN accuracy on held-out data using k prototypes
        per class, selected two ways: by farthest-point traversal (geometric)
        vs uniformly at random. Plus an SVM baseline at the same budget.
        If the geometric support matches or beats random at equal k, the
        geometry is doing work.

--------------------------------------------------------------------------
EXAMPLES
--------------------------------------------------------------------------
  python run_experiment.py --dataset mnist --run all --out results/mnist
  python run_experiment.py --dataset mnist --run budget --budgets 5 10 20 40 80 160 320 650
  python run_experiment.py --dataset digits --run gate --orders 10
  python run_experiment.py --dataset npy --data-path ecg.npy --run probe \\
         --eps 0.001 0.002 0.005 0.01 0.02 0.05
  python run_experiment.py --dataset mnist --run gate --canonicalise deskew
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

# --------------------------------------------------------------------------- #
# quotient / metric
# --------------------------------------------------------------------------- #


def l2_normalise(X: np.ndarray) -> np.ndarray:
    """Quotient by amplitude only. Correct when zero is MEANINGFUL."""
    X = np.asarray(X, dtype=np.float64)
    if X.ndim > 2:
        X = X.reshape(len(X), -1)
    n = np.linalg.norm(X, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return X / n


def z_normalise(X: np.ndarray) -> np.ndarray:
    """
    Quotient by amplitude AND offset. Correct when the baseline is arbitrary.

    Cosine distance between two signals that share a large DC component is
    dominated by that component: a discharge curve is ~3.3 V of constant plus
    ~0.2 V of signal, so after l2-normalisation every curve is nearly the same
    unit vector and the metric measures nothing. Removing the per-signal mean
    first is the quotient by {scale, offset} -- the same construction used in
    the streaming work (z-normalised windows).

    Which of the two is right is a DOMAIN DECLARATION, not a default:
      zero is meaningful  -> l2      (pixels: zero = background;
                                      irradiance: zero = night;
                                      RMS power at rest: near zero)
      zero is arbitrary   -> znorm   (voltage, temperature, sea level)
    """
    X = np.asarray(X, dtype=np.float64)
    if X.ndim > 2:
        X = X.reshape(len(X), -1)
    X = X - X.mean(axis=1, keepdims=True)
    sd = X.std(axis=1, keepdims=True)
    sd[sd == 0] = 1.0
    return l2_normalise(X / sd)


def deskew(X: np.ndarray, side: int) -> np.ndarray:
    """
    Canonicalise by the affine shear+translation of the writer group:
    centre each image on its centre of mass and remove its second-moment skew.

    This is NOT cleaning. It is quotienting by (part of) the benign group.
    Prediction: real classes shrink more than arbitrary ones, so the gate
    ratio should RISE. If it only denoised, both would shrink in proportion
    and the ratio would stay put.
    """
    from scipy.ndimage import affine_transform

    out = np.empty_like(X, dtype=np.float64)
    for i, flat in enumerate(X):
        img = flat.reshape(side, side).astype(np.float64)
        tot = img.sum()
        if tot <= 0:
            out[i] = flat
            continue
        gy, gx = np.mgrid[:side, :side]
        mu_x = (gx * img).sum() / tot
        mu_y = (gy * img).sum() / tot
        mu11 = ((gx - mu_x) * (gy - mu_y) * img).sum() / tot
        mu02 = (((gy - mu_y) ** 2) * img).sum() / tot
        alpha = mu11 / mu02 if mu02 > 1e-8 else 0.0
        M = np.array([[1.0, 0.0], [alpha, 1.0]])            # shear in y->x
        offset = np.array([mu_y - side / 2.0,
                           mu_x - side / 2.0 - alpha * (side / 2.0)])
        out[i] = affine_transform(img, M, offset=offset, order=1,
                                  mode="constant", cval=0.0).ravel()
    return out


def blur_only(X: np.ndarray, side: int) -> np.ndarray:
    """
    CONTROL for deskew. Applies the SAME bilinear interpolation machinery with
    NO pose correction: a half-pixel shift, identical for every image.

    Blur alone shrinks distances, and it shrinks them preferentially at high
    spatial frequency -- which is where WITHIN-class differences (fine stroke
    detail) live, while BETWEEN-class differences (gross layout) are lower
    frequency. So blur alone could raise separability without any quotient.
    If separability under `blur` stays at the raw value, the deskew effect is
    the quotient. If it rises to the deskew value, it was interpolation.
    """
    from scipy.ndimage import affine_transform

    out = np.empty_like(X, dtype=np.float64)
    M = np.eye(2)
    for i, flat in enumerate(X):
        img = flat.reshape(side, side).astype(np.float64)
        out[i] = affine_transform(img, M, offset=(0.5, 0.5), order=1,
                                  mode="constant", cval=0.0).ravel()
    return out


def randshear(X: np.ndarray, side: int, seed: int = 0) -> np.ndarray:
    """
    MATCHED control. Applies a shear of the same magnitude the deskew would
    have applied to that image, but with a RANDOM sign, and no centring.
    Same amount of resampling per image, no alignment. Anti-canonicalising.
    """
    from scipy.ndimage import affine_transform

    rng = np.random.default_rng(seed)
    out = np.empty_like(X, dtype=np.float64)
    for i, flat in enumerate(X):
        img = flat.reshape(side, side).astype(np.float64)
        tot = img.sum()
        if tot <= 0:
            out[i] = flat
            continue
        gy, gx = np.mgrid[:side, :side]
        mu_x = (gx * img).sum() / tot
        mu_y = (gy * img).sum() / tot
        mu11 = ((gx - mu_x) * (gy - mu_y) * img).sum() / tot
        mu02 = (((gy - mu_y) ** 2) * img).sum() / tot
        alpha = abs(mu11 / mu02) if mu02 > 1e-8 else 0.0
        alpha *= rng.choice([-1.0, 1.0])
        M = np.array([[1.0, 0.0], [alpha, 1.0]])
        out[i] = affine_transform(img, M, offset=(0.0, -alpha * side / 2.0),
                                  order=1, mode="constant", cval=0.0).ravel()
    return out

# --------------------------------------------------------------------------- #
# the net
# --------------------------------------------------------------------------- #


def greedy_net(Xn: np.ndarray, eps: float, record_growth: bool = False):
    """Greedy eps-net. Store x iff its distance to every prototype exceeds eps."""
    keep: list[int] = []
    P = np.empty((0, Xn.shape[1]), dtype=Xn.dtype)
    growth = np.empty(len(Xn), dtype=np.int32) if record_growth else None
    for i in range(len(Xn)):
        x = Xn[i]
        if len(keep) == 0:
            keep.append(i)
            P = x[None, :].copy()
        elif 1.0 - float(np.max(P @ x)) > eps:
            keep.append(i)
            P = np.vstack([P, x[None, :]])
        if record_growth:
            growth[i] = len(keep)
    return np.asarray(keep, dtype=np.int64), growth


def farthest_point(Xn: np.ndarray, k: int, seed: int = 0) -> np.ndarray:
    """
    Farthest-point traversal: the eps-net with the budget fixed instead of eps.
    Returns k indices; the first j of them are a 2-approx j-centre for every j.
    """
    n = len(Xn)
    k = min(k, n)
    rng = np.random.default_rng(seed)
    first = int(rng.integers(n))
    chosen = [first]
    d = 1.0 - Xn @ Xn[first]
    for _ in range(k - 1):
        j = int(np.argmax(d))
        chosen.append(j)
        d = np.minimum(d, 1.0 - Xn @ Xn[j])
    return np.asarray(chosen, dtype=np.int64)


def slope_log_log(eps_grid, sizes, n_samples: int | None = None,
                  cap_frac: float = 0.5) -> float:
    """
    Slope of log|S(eps)| vs log(1/eps): box-counting dimension estimate.

    IMPORTANT: fitted only where the net is far from the sample size. When
    |S| approaches n every sample is its own prototype, the curve flattens
    because the DATA ran out, not because the geometry did, and the fitted
    slope is biased DOWN. Points with |S| >= cap_frac * n are dropped.
    """
    e = np.asarray(eps_grid, float)
    s = np.asarray(sizes, float)
    m = (s > 1) & (e > 0)
    if n_samples:
        m &= s < cap_frac * n_samples
    if m.sum() < 3:
        return float("nan")
    return float(np.polyfit(np.log(1.0 / e[m]), np.log(s[m]), 1)[0])


def net_sizes_over_eps(Xn, eps_grid, orders: int, seed: int):
    """|S(eps)| for each eps, repeated over `orders` arrival orders."""
    rng = np.random.default_rng(seed)
    out = np.zeros((len(eps_grid), orders), dtype=np.int64)
    for o in range(orders):
        Xp = Xn[rng.permutation(len(Xn))]
        for j, eps in enumerate(eps_grid):
            out[j, o] = len(greedy_net(Xp, float(eps))[0])
    return out


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #


def load_dataset(name: str, path: str | None, labels_path: str | None):
    """Returns (X_train, y_train, X_test, y_test, side or None)."""
    if name == "mnist":
        from sklearn.datasets import fetch_openml
        from sklearn.model_selection import train_test_split
        X, y = fetch_openml("mnist_784", version=1, return_X_y=True, as_frame=False)
        X = X.astype(np.float64) / 255.0
        y = y.astype(np.int64)
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=10000,
                                              random_state=42, stratify=y)
        return Xtr, ytr, Xte, yte, 28

    if name == "digits":
        from sklearn.datasets import load_digits
        from sklearn.model_selection import train_test_split
        d = load_digits()
        X = d.data.astype(np.float64) / 16.0
        Xtr, Xte, ytr, yte = train_test_split(X, d.target, test_size=0.3,
                                              random_state=42, stratify=d.target)
        return Xtr, ytr, Xte, yte, 8

    if name == "npy":
        if path is None:
            raise SystemExit("--dataset npy requires --data-path")
        X = np.load(path).astype(np.float64)
        if X.ndim > 2:
            X = X.reshape(len(X), -1)
        if labels_path:
            y = np.load(labels_path).astype(np.int64)
        else:                       # unlabelled: one single class
            y = np.zeros(len(X), dtype=np.int64)
        return X, y, np.empty((0, X.shape[1])), np.empty(0, dtype=np.int64), None

    raise SystemExit(f"unknown dataset {name!r}")


# --------------------------------------------------------------------------- #
# experiments
# --------------------------------------------------------------------------- #


def run_probe(Xn, y, classes, eps_grid, n_per_class, orders, seed, mid_eps):
    rng = np.random.default_rng(seed)
    sizes, growth, slopes = {}, {}, {}
    for c in classes:
        idx = np.where(y == c)[0]
        if n_per_class and len(idx) > n_per_class:
            idx = rng.choice(idx, size=n_per_class, replace=False)
        Xc = Xn[idx]
        s = net_sizes_over_eps(Xc, eps_grid, orders, seed + int(c))
        sizes[int(c)] = s
        growth[int(c)] = greedy_net(Xc, mid_eps, record_growth=True)[1]
        slopes[int(c)] = slope_log_log(eps_grid, s.mean(axis=1), len(idx))
        print(f"  class {c}: |S| = {[int(v) for v in s.mean(axis=1).round()]}"
              f"  slope={slopes[int(c)]:.2f}  (n={len(idx)})", flush=True)
    return sizes, growth, slopes


def run_gate(Xn, y, classes, eps_grid, n_per_class, orders, seed):
    """Pseudo-classes of the same size whose membership is arbitrary."""
    rng = np.random.default_rng(seed + 9999)
    sizes = {}
    for c in classes:
        n = n_per_class or int(np.sum(y == c))
        idx = rng.choice(len(Xn), size=min(n, len(Xn)), replace=False)
        s = net_sizes_over_eps(Xn[idx], eps_grid, orders, seed + 1000 + int(c))
        sizes[int(c)] = s
        print(f"  shuffled {c}: |S| = {[int(v) for v in s.mean(axis=1).round()]}",
              flush=True)
    return sizes


def run_budget(Xtr_n, ytr, Xte_n, yte, classes, budgets, seeds, do_svm):
    """1-NN with k prototypes per class: geometric (FPT) vs random. Plus SVM."""
    res = {"budgets": list(budgets), "net": {}, "random": {}, "svm": {}}
    for k in budgets:
        acc_net, acc_rnd, acc_svm = [], [], []
        for sd in seeds:
            rng = np.random.default_rng(sd)
            protos_net, protos_rnd, lab = [], [], []
            for c in classes:
                idx = np.where(ytr == c)[0]
                Xc = Xtr_n[idx]
                protos_net.append(Xc[farthest_point(Xc, k, seed=sd)])
                protos_rnd.append(Xc[rng.choice(len(Xc),
                                                size=min(k, len(Xc)),
                                                replace=False)])
                lab.append(np.full(min(k, len(Xc)), c))
            lab = np.concatenate(lab)

            for P, bucket in ((np.vstack(protos_net), acc_net),
                              (np.vstack(protos_rnd), acc_rnd)):
                pred = lab[np.argmax(Xte_n @ P.T, axis=1)]   # 1-NN, cosine
                bucket.append(float((pred == yte).mean()))

            if do_svm:
                from sklearn.svm import SVC
                Xs = np.vstack(protos_rnd)
                clf = SVC(kernel="rbf", C=10.0, gamma="scale").fit(Xs, lab)
                acc_svm.append(float((clf.predict(Xte_n) == yte).mean()))

        res["net"][str(k)] = acc_net
        res["random"][str(k)] = acc_rnd
        if do_svm:
            res["svm"][str(k)] = acc_svm
        msg = (f"  k={k:5d}  net={np.mean(acc_net):.4f}  "
               f"random={np.mean(acc_rnd):.4f}")
        if do_svm:
            msg += f"  svm={np.mean(acc_svm):.4f}"
        print(msg, flush=True)
    return res


def run_distances(Xn, y, classes, n_sample, seed):
    """
    Where does eps LIVE for this dataset? Never guess the grid again.

    Reports the distribution of within-class and between-class cosine
    distances, and suggests an eps grid from the within-class percentiles.
    An eps far below the within-class median cannot compress: almost every
    sample becomes its own prototype. An eps above the between-class median
    cannot discriminate: everything collapses together.
    """
    rng = np.random.default_rng(seed)
    within, between = [], []
    for c in classes:
        idx = np.where(y == c)[0]
        idx = rng.choice(idx, size=min(n_sample, len(idx)), replace=False)
        A = Xn[idx]
        D = 1.0 - A @ A.T
        within.append(D[np.triu_indices(len(A), k=1)])

        other = np.where(y != c)[0]
        other = rng.choice(other, size=min(n_sample, len(other)), replace=False)
        between.append((1.0 - A @ Xn[other].T).ravel())

    w = np.concatenate(within)
    b = np.concatenate(between)
    qs = [1, 5, 10, 25, 50, 75, 90]
    wq = np.percentile(w, qs)
    bq = np.percentile(b, qs)

    print("  percentile      ", "  ".join(f"{q:6d}" for q in qs))
    print("  within-class  d ", "  ".join(f"{v:6.3f}" for v in wq))
    print("  between-class d ", "  ".join(f"{v:6.3f}" for v in bq))
    print(f"\n  within  mean={w.mean():.3f}  median={np.median(w):.3f}")
    print(f"  between mean={b.mean():.3f}  median={np.median(b):.3f}")
    print(f"  separation (between-median - within-median) = "
          f"{np.median(b) - np.median(w):.3f}")

    suggested = np.round(np.percentile(w, [1, 5, 10, 25, 40, 50, 60, 75]), 3)
    print("\n  SUGGESTED --eps " + " ".join(f"{v:g}" for v in suggested))
    print("  (within-class percentiles: the eps range where compression can "
          "happen at all)")
    return {"quantiles": qs, "within": wq.tolist(), "between": bq.tolist(),
            "within_median": float(np.median(w)),
            "between_median": float(np.median(b)),
            "suggested_eps": suggested.tolist()}


def run_contrast(Xn, y, classes, n_grid, reps, seed):
    """
    2a — THE CONTRAST.  Eduardo's actual criterion, measured.

    Not "does |S| stop growing" but:
      (a) does the distance BETWEEN DOGS stop growing, and
      (b) is the CAT much further away,
      (c) and how many samples before that contrast stops improving?

    Monte Carlo over RANDOM SUBSETS of increasing size (as in v6), repeated,
    with spread reported -- not prefixes.

    For each class c and each subset size n:
      A = n random members of c        -> within-class distances
      B = n random non-members         -> between-class distances
      within_med / within_p95 / within_max
      between_med / between_p05 / between_min
      contrast   = between_med - within_med
      separab.   = P(d_within < d_between)   in [0,1], 1 = perfect

    The point to watch: the MEDIAN should stabilise fast while the MAX keeps
    creeping. Bulk converges, tail does not. That is the whole story in one
    figure, told honestly.
    """
    out = {}
    for c in classes:
        # One generator PER CLASS, seeded by the class label. A single shared
        # generator makes each class's draws depend on how many samples the
        # classes before it had, so adding rows to one class silently changes
        # the numbers for every other class.
        rng = np.random.default_rng([seed, int(c)])
        idx_in = np.where(y == c)[0]
        idx_out = np.where(y != c)[0]
        per_n = {}
        for n in n_grid:
            if n > len(idx_in):
                continue
            acc = {k: [] for k in ("within_med", "within_p95", "within_max",
                                   "between_med", "between_p05", "between_min",
                                   "contrast", "separability")}
            for r in range(reps):
                A = Xn[rng.choice(idx_in, size=n, replace=False)]
                B = Xn[rng.choice(idx_out, size=n, replace=False)]

                Dw = 1.0 - A @ A.T
                w = Dw[np.triu_indices(n, k=1)]
                if w.size == 0:                       # n == 1
                    continue
                b = (1.0 - A @ B.T).ravel()

                ws = np.sort(w)
                # P(d_within < d_between): for each b, how many w fall below
                sep = float(np.searchsorted(ws, b, side="left").sum()
                            / (ws.size * b.size))

                acc["within_med"].append(float(np.median(w)))
                acc["within_p95"].append(float(np.percentile(w, 95)))
                acc["within_max"].append(float(w.max()))
                acc["between_med"].append(float(np.median(b)))
                acc["between_p05"].append(float(np.percentile(b, 5)))
                acc["between_min"].append(float(b.min()))
                acc["contrast"].append(float(np.median(b) - np.median(w)))
                acc["separability"].append(sep)

            if acc["within_med"]:
                per_n[int(n)] = {k: [float(np.mean(v)), float(np.std(v))]
                                 for k, v in acc.items()}
        out[int(c)] = per_n

        ns = sorted(per_n)
        print(f"  class {c}:")
        print("    n           " + "  ".join(f"{n:7d}" for n in ns))
        for key, lbl in (("within_med", "within med "),
                         ("within_max", "within MAX "),
                         ("between_med", "between med"),
                         ("separability", "separabil. ")):
            print(f"    {lbl} " + "  ".join(f"{per_n[n][key][0]:7.3f}" for n in ns))
        print(flush=True)
    return out



# --------------------------------------------------------------------------- #
# .tex emission — no number is ever typed by hand
# --------------------------------------------------------------------------- #


def write_tex_gate(path, eps_grid, real, shuf, ratio, label, caption):
    cols = "l" + "c" * len(eps_grid)
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule",
             r"$\varepsilon$ & " + " & ".join(f"{e:g}" for e in eps_grid) + r" \\",
             r"\midrule",
             r"$|S|$ real & " + " & ".join(f"{v:.1f}" for v in real) + r" \\",
             r"$|S|$ arbitrary & " + " & ".join(f"{v:.1f}" for v in shuf) + r" \\",
             r"ratio & " + " & ".join(rf"\textbf{{{v:.2f}}}" for v in ratio) + r" \\",
             r"\bottomrule", r"\end{tabular}"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write_tex_budget(path, res, do_svm):
    ks = res["budgets"]
    cols = "l" + "c" * len(ks)
    rows = [(r"$\varepsilon$-net (FPT)", "net"), ("random", "random")]
    if do_svm:
        rows.append(("SVM", "svm"))
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule",
             r"prototypes per class & " + " & ".join(str(k) for k in ks) + r" \\",
             r"\midrule"]
    for name, key in rows:
        vals = [np.mean(res[key][str(k)]) for k in ks]
        lines.append(name + " & " + " & ".join(f"{v:.4f}" for v in vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #


def main():
    p = argparse.ArgumentParser(
        description="Blueprints v8 experiment driver",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--dataset", default="mnist", choices=["mnist", "digits", "npy"])
    p.add_argument("--data-path", default=None, help="for --dataset npy")
    p.add_argument("--labels-path", default=None, help="optional labels for npy")
    p.add_argument("--run", default="all",
                   choices=["distances", "contrast", "probe", "gate", "budget", "all"])
    p.add_argument("--eps", type=float, nargs="+",
                   default=[0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40],
                   help="epsilon grid (swept, not chosen)")
    p.add_argument("--mid-eps", type=float, default=0.10,
                   help="epsilon at which |S_n| growth is recorded")
    p.add_argument("--n-per-class", type=int, default=1000,
                   help="0 = use every sample")
    p.add_argument("--orders", type=int, default=5,
                   help="arrival orders; greedy nets are order dependent")
    p.add_argument("--budgets", type=int, nargs="+",
                   default=[5, 10, 20, 40, 80, 160, 320, 650])
    p.add_argument("--budget-seeds", type=int, default=5)
    p.add_argument("--no-svm", action="store_true")
    p.add_argument("--canonicalise", default="none", choices=["none", "deskew", "blur", "randshear"],
                   help="deskew = quotient by (part of) the writer group; "
                        "blur/randshear = controls isolating the interpolation")
    p.add_argument("--dist-sample", type=int, default=400,
                   help="samples per class for --run distances")
    p.add_argument("--n-grid", type=int, nargs="+",
                   default=[5, 10, 20, 40, 80, 160, 320, 640],
                   help="subset sizes for --run contrast")
    p.add_argument("--reps", type=int, default=20,
                   help="random subsets drawn per size")
    p.add_argument("--quotient", default="l2", choices=["l2", "znorm"],
                   help="l2 = amplitude only (zero is meaningful); "
                        "znorm = amplitude and offset (zero is arbitrary)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default="results")
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    Xtr, ytr, Xte, yte, side = load_dataset(args.dataset, args.data_path,
                                            args.labels_path)
    if args.canonicalise != "none":
        if side is None:
            raise SystemExit(f"--canonicalise {args.canonicalise} needs square images")
        fn = {"deskew": lambda A: deskew(A, side),
              "blur": lambda A: blur_only(A, side),
              "randshear": lambda A: randshear(A, side, args.seed)}[args.canonicalise]
        print(f"applying {args.canonicalise} ({side}x{side}) ...", flush=True)
        Xtr = fn(Xtr)
        if len(Xte):
            Xte = fn(Xte)

    qfn = {'l2': l2_normalise, 'znorm': z_normalise}[args.quotient]
    Xtr_n = qfn(Xtr)
    Xte_n = qfn(Xte) if len(Xte) else Xte
    classes = np.unique(ytr)
    eps_grid = np.asarray(args.eps, dtype=float)
    npc = args.n_per_class or None

    print(f"\ndataset={args.dataset}  quotient={args.quotient}  "
          f"canonicalise={args.canonicalise}  "
          f"train={Xtr_n.shape}  test={Xte_n.shape}  classes={len(classes)}\n")

    out = {"config": vars(args), "eps_grid": eps_grid.tolist(),
           "classes": [int(c) for c in classes]}

    if args.run in ("distances", "all"):
        print("DISTANCES — where does eps live?")
        out["distances"] = run_distances(Xtr_n, ytr, classes,
                                         args.dist_sample, args.seed)
        print()

    if args.run in ("contrast", "all"):
        print("CONTRAST — random subsets, does the contrast stop improving?")
        out["contrast"] = run_contrast(Xtr_n, ytr, classes,
                                       args.n_grid, args.reps, args.seed)

    if args.run in ("probe", "gate", "all"):
        print("PROBE — real classes")
        sizes, growth, slopes = run_probe(Xtr_n, ytr, classes, eps_grid,
                                          npc, args.orders, args.seed,
                                          args.mid_eps)
        real_mean = np.stack([sizes[int(c)].mean(axis=1) for c in classes]).mean(0)
        spread = np.stack([
            (sizes[int(c)].max(axis=1) - sizes[int(c)].min(axis=1))
            / np.maximum(sizes[int(c)].mean(axis=1), 1e-9) for c in classes
        ]).mean(0)
        out["probe"] = {
            "per_class_mean": {str(c): sizes[int(c)].mean(axis=1).tolist()
                               for c in classes},
            "real_mean": real_mean.tolist(),
            "order_spread": spread.tolist(),
            "slopes": {str(c): slopes[int(c)] for c in classes},
            "growth_mid_eps": {str(c): growth[int(c)].tolist() for c in classes},
            "mid_eps": args.mid_eps,
        }

    if args.run in ("gate", "all"):
        print("\nGATE — arbitrary classes")
        shuf = run_gate(Xtr_n, ytr, classes, eps_grid, npc, args.orders, args.seed)
        shuf_mean = np.stack([shuf[int(c)].mean(axis=1) for c in classes]).mean(0)
        ratio = shuf_mean / np.maximum(real_mean, 1e-9)
        out["gate"] = {"shuffled_mean": shuf_mean.tolist(),
                       "ratio": ratio.tolist(),
                       "n_classes": int(len(classes))}
        write_tex_gate(os.path.join(args.out, "table_gate.tex"),
                       eps_grid, real_mean, shuf_mean, ratio,
                       "tab:gate", "Covering number, real vs arbitrary class.")
        print("\n  eps        ", "  ".join(f"{e:6.2f}" for e in eps_grid))
        print("  |S| real   ", "  ".join(f"{v:6.1f}" for v in real_mean))
        print("  |S| arbitr ", "  ".join(f"{v:6.1f}" for v in shuf_mean))
        print("  ratio      ", "  ".join(f"{v:6.2f}" for v in ratio))
        print(f"  (n_classes = {len(classes)})")

    if args.run in ("budget", "all"):
        if not len(Xte_n):
            print("\nBUDGET — skipped (no test split for this dataset)")
        else:
            print("\nBUDGET — 1-NN, geometric support vs random, same k")
            res = run_budget(Xtr_n, ytr, Xte_n, yte, classes, args.budgets,
                             range(args.budget_seeds), not args.no_svm)
            out["budget"] = res
            write_tex_budget(os.path.join(args.out, "table_budget.tex"),
                             res, not args.no_svm)

    tag = f"{args.dataset}_{args.canonicalise}"
    with open(os.path.join(args.out, f"{tag}.json"), "w") as f:
        json.dump(out, f)

    print(f"\nwritten to {args.out}/  ({time.time() - t0:.0f}s)")
    print("  " + tag + ".json, table_gate.tex, table_budget.tex")


if __name__ == "__main__":
    main()
