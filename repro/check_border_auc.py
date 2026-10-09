#!/usr/bin/env python3
"""
check_border_auc.py -- ¿me sali de los perros? ¿y cuantos perros hacen falta
para saberlo?

    python check_border_auc.py --data-root <datasets> --cache-from <run> \
        --out out_border [--only ...] [--skip-mnist]

La pregunta (Eduardo, 2026-09-23)
---------------------------------
La distancia al ejemplar visto mas cercano mide la resolucion DENTRO de la
clase: si esto es un husky o un malamute. No es la pregunta. La pregunta es si
una realizacion nueva SE SALE de la clase, y a partir de cuantos ejemplares esa
decision deja de cambiar. Eso necesita algo que no sea de la clase contra lo que
medir.

Lo que es "no perro", por dominio
---------------------------------
  dominios fisicos  surrogados IAAFT (src/surrogates.py): el mismo espectro y la
                    misma distribucion de amplitudes que la senal real -- la
                    MISMA densidad marginal -- pero no son realizaciones del
                    proceso. Si el borde los deja fuera con pocos ejemplares, el
                    borde no es un efecto de la densidad. Se genera un pool fijo
                    por concepto (semilla declarada) a partir de realizaciones
                    reales, se re-proyecta al cociente del dominio, y en cada
                    sorteo se usan solo surrogados cuya fuente NO esta entre los
                    ejemplares vistos.
  digitos           las otras nueve clases.
  (ECG con etiquetas de cardiologo: ya medido en stage_ecg_anomaly; no se repite.)

Lo que se mide
--------------
Mismos sorteos que la convergencia del paper (semillas y permutacion de
reproduce._conv_one: los mismos n vistos y los mismos held-out). Para cada
held-out real y para 200 "no perro", la distancia coseno al ejemplar visto mas
cercano. AUC = P(d_nn(no perro) > d_nn(perro nuevo)), sin umbral ni punto de
operacion: mide si el borde separa, no construye un detector. Cada dominio se
lee SOLO; no se combinan ni se comparan dominios.

CRITERIO -- fijado con Eduardo ANTES de correr, 2026-09-23
----------------------------------------------------------
  n_settle = primer n desde el cual |AUC(n) - AUC(n final)| <= 0.01 y no sale.
  PASA en un dominio si n_settle <= 25.
(Eduardo: "1% esta ok, pero podria cambiar, es muy dificil"; 25 para que las
mareas, con su pool corto, entren en la medicion.)
"""
from __future__ import annotations

import argparse, json, os, sys
import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import control_sup as C          # noqa: E402
R = C.R
from surrogates import SURROGATES  # noqa: E402

NMAX = 5000
N_OUT = 200
SUR_POOL = 1000
TOL, NSET = 0.01, 25
CRITERION = {"fixed_on": "2026-09-23", "agreed_with": "Eduardo",
             "n_settle": "first n from which |AUC(n) - AUC(n_final)| <= 0.01 and stays",
             "pass": "n_settle <= 25, each domain on its own",
             "out_of_class": {"physical": "IAAFT surrogates, same quotient",
                              "digits": "the other nine classes"}}


def auc(pos_out, neg_in):
    """P(out > in), con empates a medias (Mann-Whitney)."""
    x = np.concatenate([neg_in, pos_out])
    r = rankdata(x)
    n1, n0 = len(pos_out), len(neg_in)
    return float((r[n0:].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def surrogate_pool(X, quot, tag):
    g = np.random.default_rng(R.seed_for(R.SEED, tag, "border-sur"))
    src = g.choice(len(X), min(SUR_POOL, len(X)), replace=False)
    Z = SURROGATES["iaaft"](X[src].copy(), g)
    return C.Q[quot](Z), src


def curve(X, tag, out_fn):
    N = len(X)
    steps = [n for n in R.CONV_STEPS
             if n + R.CONV_HELD_MIN <= N and n <= min(R.CONV_NMAX, NMAX)]
    res = {"steps": steps, "auc": [], "auc_sd": []}
    for n in steps:
        a = []
        for rep in range(R.reps_for(n)):
            g = np.random.default_rng(R.seed_for(R.SEED, tag, "conv", n, rep))
            p = g.permutation(N)
            S, H = X[p[:n]], X[p[n:n + R.CONV_HELD]]
            O = out_fn(set(p[:n].tolist()), np.random.default_rng(
                R.seed_for(R.SEED, tag, "border-out", n, rep)))
            d_in = cdist(H, S, "cosine").min(1)
            d_out = cdist(O, S, "cosine").min(1)
            a.append(auc(d_out, d_in))
        res["auc"].append(float(np.mean(a)))
        res["auc_sd"].append(float(np.std(a)))
    return res


def n_settle(steps, y):
    f = y[-1]
    for i in range(len(steps)):
        if all(abs(v - f) <= TOL for v in y[i:]):
            return steps[i]
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--cache-from", default=None)
    p.add_argument("--out", default="out_border")
    p.add_argument("--only", nargs="+", default=None)
    p.add_argument("--skip-mnist", action="store_true")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "CRITERIO.json"), "w") as f:
        json.dump(CRITERION, f, indent=1)

    concepts = list(C.concepts(a.data_root, a.cache_from, a.only, a.skip_mnist))
    by_dom = {}
    for c in concepts:
        by_dom.setdefault(c[0], []).append(c)

    per = {}
    for dom, items in by_dom.items():
        digits = not items[0][6]
        for (d_, sub, X, tag, quot, n_pool, series) in items:
            X = np.asarray(X, float)
            if digits:
                others = np.vstack([np.asarray(o[2], float) for o in items if o[1] != sub])

                def out_fn(seen, g, others=others):
                    return others[g.choice(len(others), N_OUT, replace=False)]
            else:
                Z, src = surrogate_pool(X, quot, tag)

                def out_fn(seen, g, Z=Z, src=src):
                    ok = np.flatnonzero([s not in seen for s in src])
                    return Z[g.choice(ok, min(N_OUT, len(ok)), replace=False)]
            r = curve(X, tag, out_fn)
            per.setdefault(dom, {})[sub or "_"] = r
            print(f"    {tag:28s} AUC n=1 {r['auc'][0]:.3f}  n={r['steps'][-1]} "
                  f"{r['auc'][-1]:.3f}", flush=True)

    res = {"criterion": CRITERION, "domains": {}}
    for dom, subs in per.items():
        keys = list(subs)
        ns = min((subs[k]["steps"] for k in keys), key=len)
        y = np.mean([subs[k]["auc"][:len(ns)] for k in keys], 0).tolist()
        ns_ = n_settle(ns, y)
        at = {n: y[ns.index(n)] for n in (1, 5, 25) if n in ns}
        res["domains"][dom] = {"steps": ns, "auc": y, "n_concepts": len(keys),
                               "n_settle": ns_, "auc_at": at, "auc_final": y[-1],
                               "n_final": ns[-1],
                               "pass": bool(ns_ is not None and ns_ <= NSET),
                               "per_concept": subs}
    R.jdump(res, os.path.join(a.out, "border_auc.json"))
    print(f"\n  {'dominio':22s} {'AUC n=1':>8s} {'n=5':>7s} {'n=25':>7s} {'final':>7s} "
          f"{'(n)':>6s} {'n_settle':>9s}  pasa")
    for dom, d in res["domains"].items():
        g = lambda n: f"{d['auc_at'][n]:.3f}" if n in d["auc_at"] else "--"
        print(f"  {dom:22s} {g(1):>8s} {g(5):>7s} {g(25):>7s} {d['auc_final']:7.3f} "
              f"{d['n_final']:6d} {str(d['n_settle']):>9s}  {d['pass']}")


if __name__ == "__main__":
    main()
