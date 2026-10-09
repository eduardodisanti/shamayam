"""Are the four nominal point-machine sets one manifold, two, or four?

This is a question about the asset, not a claim of the paper, so it lives in
its own script and emits nothing the manuscript consumes. What it decides is
the SCOPE of the data: whether the paper's point-machine domain is 2226
manoeuvres of one machine in one direction, or 8788 of two machines in both.

    python pm_sets.py --data-root ~/git/Percepltion_topology/datasets

Two measurements, and they answer different questions.

  POOLING. If two sets are the same manifold, covering m from each costs
  about what covering 2m from either one costs. If they are different
  manifolds, it costs more. The ratio |S(A+B)| / |S(A, 2m)| is therefore ~1
  for one manifold and grows for two, and it needs no threshold to read.

  The tolerance is A's OWN median, not the union's. Using the union's median
  would cancel the effect being measured: a union of two different manifolds
  has larger typical distances, so it gets a larger tolerance, so it needs
  fewer exemplars -- and the heterogeneity hides itself. Fixing the ruler to
  one set is what makes the comparison mean anything.

  SEPARABILITY. The probability that two manoeuvres of the same set are closer
  to each other than to a manoeuvre of the other set. At 0.5 the instrument
  cannot tell them apart; near 1.0 they are two things.

Both are measured at matched n over independent draws, with the same seed
discipline as the rest of the package.
"""
from __future__ import annotations

import json
import argparse
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

L = 160
SEED = 0
M = 600          # manoeuvres drawn from each set per repetition
REPS = 10
EPS_POOL = 600   # the only quadratic object here; capped as everywhere else

SETS = ("J1_normal_to_reverse", "J1_reverse_to_normal",
        "J2_normal_to_reverse", "J2_reverse_to_normal")


def seed_for(*parts):
    import hashlib
    key = "|".join(str(p) for p in parts).encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16)


def load_set(root, name):
    import pandas as pd
    out = []
    for f in sorted(glob.glob(f"{root}/pm/kaggle_nominal/{name}_*.parquet")):
        p = pd.read_parquet(f)["Power"].to_numpy(float)
        out.append(np.interp(np.linspace(0, 1, L), np.linspace(0, 1, len(p)), p))
    return np.stack(out) if out else None


def eps_of(X, tag):
    from scipy.spatial.distance import cdist
    k = min(EPS_POOL, len(X))
    g = np.random.default_rng(seed_for(SEED, tag, "eps"))
    P = X[g.choice(len(X), k, replace=False)]
    w = cdist(P, P, "cosine")
    return float(np.median(w[np.triu_indices(k, 1)]))


def main():
    from run_experiment import l2_normalise, greedy_net
    from scipy.spatial.distance import cdist

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-root",
                    default=os.path.expanduser("~/git/Percepltion_topology/datasets"))
    a = ap.parse_args()

    data = {}
    for s in SETS:
        X = load_set(a.data_root, s)
        if X is None:
            print(f"  {s}: sin archivos, se omite")
            continue
        data[s] = l2_normalise(X)
        print(f"  {s:24s} {len(X):5d} maniobras   eps propio "
              f"{eps_of(data[s], s):.4f}")
    if len(data) < 2:
        print("\nno hay conjuntos suficientes para comparar")
        return

    def one_way(ref, other):
        """Ratio and separability with `ref` supplying the ruler."""
        A, B = data[ref], data[other]
        m = min(M, len(A) // 2, len(B) // 2)
        juntos, solos, seps = [], [], []
        for rep in range(REPS):
            g = np.random.default_rng(seed_for(SEED, ref, other, rep))
            a1 = A[g.choice(len(A), 2 * m, replace=False)]
            b1 = B[g.choice(len(B), m, replace=False)]
            mix = np.vstack([a1[:m], b1])
            g.shuffle(mix)                          # arrival order, not blocks
            e = eps_of(a1, f"{ref}|ref|{rep}")
            juntos.append(len(greedy_net(mix, e)[0]))
            solos.append(len(greedy_net(a1, e)[0]))
            s1, s2 = a1[:200], b1[:200]
            dw = cdist(s1, s1, "cosine")[np.triu_indices(len(s1), 1)]
            db = cdist(s1, s2, "cosine").ravel()
            seps.append(float((dw[:, None] < db[None, ::37]).mean()))
        return (float(np.mean(juntos)), float(np.mean(solos)),
                float(np.mean(juntos) / max(np.mean(solos), 1e-9)),
                float(np.mean(seps)))

    names = list(data)
    out = {"sets": {n: {"n": int(len(data[n])), "eps": eps_of(data[n], n)}
                    for n in names},
           "m_per_set": M, "reps": REPS, "pairs": {}}
    print(f"\n{'pareja':<50} {'coc. A->B':>10} {'coc. B->A':>10} "
          f"{'sep. A->B':>10} {'sep. B->A':>10}")
    print("-" * 94)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            # BOTH directions. The ruler is the reference set's own tolerance,
            # and the four sets have tolerances that differ by a factor of
            # three, so a single direction confounds "these sets differ" with
            # "the reference set happens to be the tight one".
            ab, ba = one_way(a, b), one_way(b, a)
            out["pairs"][f"{a}|{b}"] = {"a_to_b": ab, "b_to_a": ba}
            print(f"{a} + {b:<26} {ab[2]:10.2f} {ba[2]:10.2f} "
                  f"{ab[3]:10.3f} {ba[3]:10.3f}")

    with open("pm_sets.json", "w") as f:
        import json
        json.dump(out, f, indent=1, sort_keys=True)
    print("\n  detalle en pm_sets.json")

    print("\nlectura: cociente ~1 y separabilidad ~0.5  ->  una sola variedad")
    print("         cociente ~2 y separabilidad ~1.0  ->  dos variedades")


def selftest():
    """Run the same two measurements on controls whose answer is known.

    A diagnostic that has never been shown to distinguish the two cases it is
    meant to distinguish is not a diagnostic. Two compact manifolds of the same
    kind must give a ratio near one and separability near a half; two manifolds
    in different subspaces must give a clearly larger ratio and separability
    near one.
    """
    from run_experiment import l2_normalise, greedy_net
    from scipy.spatial.distance import cdist
    g0 = np.random.default_rng(0)
    B1 = l2_normalise(g0.normal(size=(3, L)))
    B2 = l2_normalise(g0.normal(size=(3, L)))
    a1_ = l2_normalise(g0.normal(size=(1, L)))
    a2_ = l2_normalise(g0.normal(size=(1, L)))

    def mk(n, B, anc, amp=.25, nz=.01):
        w = g0.normal(size=(n, 3)) * amp
        return l2_normalise(np.repeat(anc, n, 0) + w @ B + nz * g0.normal(size=(n, L)))

    A = mk(1400, B1, a1_)
    print("  autotest (controles con respuesta conocida)")
    got = {}
    for etiq, key, Bs in (("misma variedad    ", "same", mk(1400, B1, a1_)),
                          ("variedad distinta ", "different", mk(1400, B2, a2_))):
        ju, so, se = [], [], []
        for rep in range(5):
            g = np.random.default_rng(rep)
            a = A[g.choice(len(A), 1200, replace=False)]
            b = Bs[g.choice(len(Bs), 600, replace=False)]
            mix = np.vstack([a[:600], b]); g.shuffle(mix)
            e = eps_of(a, f"selftest|{rep}")
            ju.append(len(greedy_net(mix, e)[0])); so.append(len(greedy_net(a, e)[0]))
            s1, s2 = a[:200], b[:200]
            dw = cdist(s1, s1, "cosine")[np.triu_indices(200, 1)]
            db = cdist(s1, s2, "cosine").ravel()
            se.append(float((dw[:, None] < db[None, ::37]).mean()))
        got[key] = {"rho": float(np.mean(ju) / np.mean(so)),
                    "separability": float(np.mean(se))}
        print(f"    {etiq} cociente {np.mean(ju)/np.mean(so):5.2f}   "
              f"separabilidad {np.mean(se):.3f}")
    return got


if __name__ == "__main__":
    if "--controls-out" in sys.argv:
        # The two controls the pair table normalises against. They were printed
        # and thrown away, which is why that table could not be generated.
        dest = sys.argv[sys.argv.index("--controls-out") + 1]
        json.dump(selftest(), open(dest, "w"), indent=1, sort_keys=True)
        print(f"  controles escritos en {dest}")
    elif "--selftest" in sys.argv:
        selftest()
    else:
        main()
