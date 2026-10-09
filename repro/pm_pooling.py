#!/usr/bin/env python3
"""
Do the four nominal point-machine populations go in together?

  J1 normal->reverse   2226
  J1 reverse->normal   2246
  J2 normal->reverse   2151
  J2 reverse->normal   2165
                      -----
                       8788   <- the figure in section 7.1

reproduce.py currently reads only the first of the four: load_physical() globs
"J1_normal_to_reverse_*.parquet". So every point-machine number in the package
is measured on a quarter of what the paper says it measured.

This is a DIAGNOSTIC, deliberately not a stage. It changes nothing. It answers
one question --- what happens to the numbers if the four go in together --- so
that the decision is made on a measurement rather than on an argument.

Why the question is not trivial. Epsilon is the median distance WITHIN the set.
Pool four populations that sit in different places and that median becomes the
median of a mixture, which is larger than any one population's own. A larger
epsilon buys a smaller net. So |S| for the pooled set is not comparable with
|S| for one population, and the difference is not a finding about the geometry:
it is the ruler changing length. Section 4 below separates the two effects by
measuring every set against every ruler.

What is NOT at risk: the surrogate contrast. Surrogates are always evaluated at
the real process's epsilon, whatever it is, so that comparison stays clean.

  python pm_pooling.py --data-root /path/to/datasets
  python pm_pooling.py --data-root ... --quick     (skip section 5)

Writes pm_pooling.json next to the output and prints everything it writes.
"""
import argparse, glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

# --- exactly the constants reproduce.py uses --------------------------------
L, SEED, ORDERS, SUBSAMPLES, NMAX_PHYS = 160, 0, 5, 10, 600
CONV_STEPS = [5, 8, 12, 20, 32, 50, 80, 120, 200, 320, 500, 800, 1300, 2000]
CONV_REPS, CONV_HELD, CONV_HELD_MIN = 20, 200, 50
CONV_AT = [5, 20, 50, 200]

SETS = ["J1_normal_to_reverse", "J1_reverse_to_normal",
        "J2_normal_to_reverse", "J2_reverse_to_normal"]
PRETTY = {"J1_normal_to_reverse": "J1 normal->reverse",
          "J1_reverse_to_normal": "J1 reverse->normal",
          "J2_normal_to_reverse": "J2 normal->reverse",
          "J2_reverse_to_normal": "J2 reverse->normal"}


def seed_for(*parts):
    import hashlib
    key = "|".join(str(p) for p in parts).encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16)


def load_pop(root, name):
    """The same read reproduce.py does, one population at a time."""
    import pandas as pd
    out = []
    for f in sorted(glob.glob(f"{root}/pm/kaggle_nominal/{name}_*.parquet")):
        p = pd.read_parquet(f)["Power"].to_numpy(float)
        out.append(np.interp(np.linspace(0, 1, L), np.linspace(0, 1, len(p)), p))
    if not out:
        raise SystemExit(f"no parquet found for {name} under {root}/pm/kaggle_nominal")
    return np.stack(out)


def ruler(X, tag, n_max=NMAX_PHYS):
    """epsilon and |S(epsilon)|, by the protocol of stage_physical."""
    from run_experiment import l2_normalise, net_sizes_over_eps
    n = min(n_max, len(X))
    eps_d, s_d = [], []
    for rep in range(SUBSAMPLES):
        rng = np.random.default_rng(seed_for(SEED, tag, "subsample", rep))
        A = l2_normalise(X[rng.choice(len(X), n, replace=False)])
        D = 1 - A @ A.T
        e = float(np.median(D[np.triu_indices(n, 1)]))
        eps_d.append(e)
        s_d.append(float(net_sizes_over_eps(A, [e], ORDERS, SEED).mean()))
    return {"n": n, "n_available": int(len(X)),
            "eps": float(np.mean(eps_d)), "eps_sd": float(np.std(eps_d)),
            "S": float(np.mean(s_d)), "S_sd": float(np.std(s_d))}


def net_at(X, eps, tag, n_max=NMAX_PHYS):
    """|S| of this set measured with somebody else's ruler."""
    from run_experiment import l2_normalise, net_sizes_over_eps
    n = min(n_max, len(X))
    vals = []
    for rep in range(SUBSAMPLES):
        rng = np.random.default_rng(seed_for(SEED, tag, "subsample", rep))
        A = l2_normalise(X[rng.choice(len(X), n, replace=False)])
        vals.append(float(net_sizes_over_eps(A, [eps], ORDERS, SEED).mean()))
    return float(np.mean(vals)), float(np.std(vals))


def convergence(X, tag):
    """Radius on realisations the centre never saw. _conv_one, radius only."""
    from run_experiment import l2_normalise
    A = l2_normalise(X)
    c_all = A.mean(0, keepdims=True)
    c_all = c_all / np.linalg.norm(c_all)
    r_true = float((1 - A @ c_all.T).mean())
    steps = [n for n in CONV_STEPS if n + CONV_HELD_MIN <= len(A)]
    rows = []
    for n in steps:
        acc = []
        for rep in range(CONV_REPS):
            g = np.random.default_rng(seed_for(SEED, tag, "conv", n, rep))
            p = g.permutation(len(A))
            S, H = A[p[:n]], A[p[n:n + CONV_HELD]]
            ch = S.mean(0, keepdims=True)
            nrm = np.linalg.norm(ch)
            ch = ch / (nrm if nrm else 1.0)
            acc.append(float((1 - H @ ch.T).mean()))
        rows.append([float(np.mean(acc)), float(np.std(acc))])
    return {"steps": steps, "r_true": r_true, "r_mean": rows,
            "n_available": int(len(A))}


def pct_from_settled(c, k):
    if k not in c["steps"] or not c["r_true"]:
        return None
    v = c["r_mean"][c["steps"].index(k)][0]
    return 100.0 * abs(v - c["r_true"]) / c["r_true"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", default="pm_pooling.json")
    ap.add_argument("--quick", action="store_true",
                    help="skip section 5 (the convergence curves)")
    a = ap.parse_args()

    print("=" * 74)
    print("1 . WHAT IS THERE")
    print("=" * 74)
    P = {}
    for s in SETS:
        P[s] = load_pop(a.data_root, s)
        print(f"  {PRETTY[s]:22s} {len(P[s]):5d}")
    POOL = np.concatenate([P[s] for s in SETS])
    print(f"  {'POOLED':22s} {len(POOL):5d}")
    if len(POOL) != 8788:
        print(f"  !! section 7.1 says 8788, this is {len(POOL)}")

    print()
    print("=" * 74)
    print("2 . EACH POPULATION MEASURED WITH ITS OWN RULER")
    print("=" * 74)
    print(f"  {'set':22s} {'eps':>18s}   {'|S(eps)|':>16s}")
    R = {}
    for s in SETS:
        R[s] = ruler(P[s], "PM real (nominal)")
        print(f"  {PRETTY[s]:22s} {R[s]['eps']:.6f} +- {R[s]['eps_sd']:.6f}"
              f"   {R[s]['S']:6.2f} +- {R[s]['S_sd']:5.2f}")
    e = [R[s]["eps"] for s in SETS]
    print(f"  {'':22s} spread: {max(e) / min(e):.2f}x between loosest and tightest")

    print()
    print("=" * 74)
    print("3 . THE POOLED SET WITH ITS OWN RULER")
    print("=" * 74)
    RP = ruler(POOL, "PM real (nominal)")
    print(f"  {'POOLED':22s} {RP['eps']:.6f} +- {RP['eps_sd']:.6f}"
          f"   {RP['S']:6.2f} +- {RP['S_sd']:5.2f}")
    print(f"  the pooled epsilon is {RP['eps'] / np.mean(e):.2f}x the mean of the four")

    print()
    print("=" * 74)
    print("4 . EVERY SET AGAINST EVERY RULER  (|S|; rows = set, cols = ruler)")
    print("   this is the section that separates 'the geometry changed' from")
    print("   'the ruler changed'. Read down a column, not across a row.")
    print("=" * 74)
    rulers = [(PRETTY[s], R[s]["eps"]) for s in SETS] + [("POOLED", RP["eps"])]
    print(f"  {'':22s}" + "".join(f"{nm.split()[0] + nm.split()[-1][:3]:>12s}"
                                  for nm, _ in rulers))
    X = {}
    for s in SETS + ["POOLED"]:
        A = POOL if s == "POOLED" else P[s]
        row = []
        for nm, eps in rulers:
            m, sd = net_at(A, eps, "PM real (nominal)")
            row.append(m)
        X[s] = row
        label = "POOLED" if s == "POOLED" else PRETTY[s]
        print(f"  {label:22s}" + "".join(f"{v:12.2f}" for v in row))

    res = {"populations": {s: {"n": int(len(P[s])), **R[s]} for s in SETS},
           "pooled": {"n": int(len(POOL)), **RP},
           "cross": {"rulers": [nm for nm, _ in rulers],
                     "eps": [ep for _, ep in rulers], "S": X}}

    if not a.quick:
        print()
        print("=" * 74)
        print("5 . DOES THE CONVERGENCE SURVIVE POOLING?")
        print("   radius measured on realisations the centre never saw;")
        print("   the cells are how far it still is from where it settles.")
        print("=" * 74)
        print(f"  {'set':22s} {'settles at':>11s}" +
              "".join(f"{'n=' + str(k):>9s}" for k in CONV_AT))
        C = {}
        for s in SETS + ["POOLED"]:
            A = POOL if s == "POOLED" else P[s]
            C[s] = convergence(A, "PM real (nominal)")
            label = "POOLED" if s == "POOLED" else PRETTY[s]
            cells = []
            for k in CONV_AT:
                v = pct_from_settled(C[s], k)
                cells.append("--" if v is None else f"{v:.1f}%")
            print(f"  {label:22s} {C[s]['r_true']:11.4f}" +
                  "".join(f"{c:>9s}" for c in cells))
        res["convergence"] = C
        print()
        print("  If the POOLED row has the same shape as the four, the four go in")
        print("  together and nothing about the claim changes. If the pooled radius")
        print("  settles much later, the pooled set is not one manifold and the")
        print("  populations belong in the paper separately.")

    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print()
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
