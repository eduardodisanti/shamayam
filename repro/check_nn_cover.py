#!/usr/bin/env python3
"""
check_nn_cover.py -- la prueba directa: ¿cuantos ejemplares hasta que lo nuevo
cae cerca de algo ya visto?

    python check_nn_cover.py --data-root <datasets> --cache-from <run> \
        --dimension <run>/dimension.json --out out_nn \
        [--only ...] [--skip-mnist]

Por que
-------
La curva de convergencia del paper mide la distancia de lo no visto al
CENTROIDE de lo visto. Un centroide es una media, y su residuo relativo es
~1/n para cualquier conjunto concentrado (check_one_over_n.py): esa curva es
del estimador y no dice nada de la forma. La tesis no es sobre la media, es
sobre Lobo: una realizacion nueva, ¿que tan lejos esta del EJEMPLAR visto mas
cercano? Esa distancia al vecino mas cercano cae como n^(-1/d) en la distancia
euclidea (n^(-2/d) en coseno, que es su cuadrado), con d la dimension
intrinseca: depende del fenomeno por construccion.

Lo que se mide
--------------
Mismos conceptos, mismos sorteos (las semillas y la permutacion de
reproduce._conv_one: los mismos n vistos y los mismos held-out), misma
escalera. Para cada held-out h, d_nn(h) = min sobre los vistos de la distancia
coseno. Por n: mediana y p95 de d_nn (el p95 es el borde tal como lo ve el
observador, el mismo umbral que usa el detector de ECG), y la COBERTURA a la
resolucion del paper, P(d_nn <= eps), con eps = reproduce._conv_eps (la mediana
intra-conjunto, el eps de todas las redes del paper).

PREDICCIONES -- fijadas ANTES de correr, 2026-09-23
---------------------------------------------------
  P1  no es universal: el n al que la cobertura a eps alcanza el 90% y no baja
      difiere entre dominios en un factor de al menos 3 (max/min >= 3).
      Contraste: el calendario del centroide es 10-12 en los diez.
  P2  lo ordena la geometria: en los ocho dominios con dimension intrinseca
      medida (Tabla de dimension del paper), Spearman entre |b| y 1/d >= 0.6,
      con b la pendiente de log mediana(d_nn) contra log n en 5 <= n <=
      min(500, N/4).
  Descriptivo, no criterio: b frente a -2/d. d es una cota inferior (el paper
  lo dice), asi que no se espera igualdad.
Si P1 o P2 fallan, se reporta asi.
"""
from __future__ import annotations

import argparse, json, os, sys
import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import control_sup as C          # noqa: E402
R = C.R

NMAX = 5000
PREDICTION = {"fixed_on": "2026-09-23",
              "P1": "n at which coverage at eps reaches 90% and stays: max/min over domains >= 3",
              "P2": "Spearman(|slope of log median d_nn vs log n|, 1/d) >= 0.6 over the 8 domains with d",
              "fit_range": "5 <= n <= min(500, N/4)",
              "eps": "reproduce._conv_eps (within-set median cosine distance)"}


def nn_curves(X, tag):
    eps = R._conv_eps(X, tag)
    N = len(X)
    steps = [n for n in R.CONV_STEPS
             if n + R.CONV_HELD_MIN <= N and n <= min(R.CONV_NMAX, NMAX)]
    out = {"steps": steps, "eps": eps, "N": N, "med": [], "p95": [], "cov": []}
    for n in steps:
        acc = {"med": [], "p95": [], "cov": []}
        for rep in range(R.reps_for(n)):
            g = np.random.default_rng(R.seed_for(R.SEED, tag, "conv", n, rep))
            p = g.permutation(N)
            S, H = X[p[:n]], X[p[n:n + R.CONV_HELD]]
            d = cdist(H, S, "cosine").min(1)
            acc["med"].append(float(np.median(d)))
            acc["p95"].append(float(np.quantile(d, 0.95)))
            acc["cov"].append(float((d <= eps).mean()))
        for k in acc:
            out[k].append(float(np.mean(acc[k])))
    return out


def first_stay(ns, y, thr):
    for i in range(len(ns)):
        if all(v >= thr for v in y[i:]):
            return ns[i]
    return None


def slope(ns, y, N):
    hi = min(500, N // 4)
    idx = [i for i, n in enumerate(ns) if 5 <= n <= hi and y[i] > 0]
    if len(idx) < 3:
        return None
    b, _ = np.polyfit(np.log([ns[i] for i in idx]), np.log([y[i] for i in idx]), 1)
    return float(b)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--cache-from", default=None)
    p.add_argument("--dimension", required=True)
    p.add_argument("--out", default="out_nn")
    p.add_argument("--only", nargs="+", default=None)
    p.add_argument("--skip-mnist", action="store_true")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "PREDICCION.json"), "w") as f:
        json.dump(PREDICTION, f, indent=1)

    per = {}
    for dom, sub, X, tag, quot, n_pool, series in C.concepts(
            a.data_root, a.cache_from, a.only, a.skip_mnist):
        c = nn_curves(np.asarray(X, float), tag)
        per.setdefault(dom, {})[sub or "_"] = c
        print(f"    {tag:28s} N={c['N']:6d}  eps={c['eps']:.4f}  "
              f"cov n=1 {c['cov'][0]:.2f} -> {c['cov'][-1]:.2f} (n={c['steps'][-1]})",
              flush=True)

    dim = json.load(open(a.dimension))
    res = {"prediction": PREDICTION, "domains": {}}
    for dom, subs in per.items():
        keys = list(subs)
        ns = min((subs[k]["steps"] for k in keys), key=len)
        m = len(ns)
        agg = {q: np.mean([subs[k][q][:m] for k in keys], 0).tolist()
               for q in ("med", "p95", "cov")}
        N = min(subs[k]["N"] for k in keys)
        d = {"steps": ns, "n_concepts": len(keys), "N": N,
             "eps": float(np.mean([subs[k]["eps"] for k in keys])), **agg,
             "n_cov90": first_stay(ns, agg["cov"], 0.90),
             "n_cov95": first_stay(ns, agg["cov"], 0.95),
             "slope_med": slope(ns, agg["med"], N),
             "slope_p95": slope(ns, agg["p95"], N)}
        src = dim.get("domains", {}).get(dom) or dim.get("digits", {}).get(dom)
        dhat = None
        if src:
            # dimension.json: 'dim' for physical domains, 'real_mean' for digit sets
            for key in ("dim", "real_mean"):
                if isinstance(src.get(key), (int, float)):
                    dhat = float(src[key]); break
        d["d_hat"] = dhat
        res["domains"][dom] = d

    n90 = [d["n_cov90"] for d in res["domains"].values() if d["n_cov90"]]
    res["P1"] = {"n_cov90": {k: v["n_cov90"] for k, v in res["domains"].items()},
                 "ratio": (max(n90) / min(n90)) if n90 else None}
    res["P1"]["holds"] = bool(res["P1"]["ratio"] is not None and res["P1"]["ratio"] >= 3
                              and len(n90) == len(res["domains"]))
    pairs = [(abs(d["slope_med"]), 1 / d["d_hat"]) for d in res["domains"].values()
             if d["d_hat"] and d["slope_med"] is not None]
    if len(pairs) >= 4:
        rho, pv = spearmanr([x for x, _ in pairs], [y for _, y in pairs])
        res["P2"] = {"n": len(pairs), "spearman": float(rho), "p": float(pv),
                     "holds": bool(rho >= 0.6)}
    R.jdump(res, os.path.join(a.out, "nn_cover.json"))

    print(f"\n  {'dominio':22s} {'d':>5s} {'eps':>7s} {'cov n=1':>8s} {'n90':>6s} {'n95':>6s} "
          f"{'b med':>7s} {'-2/d':>6s} {'b p95':>7s}")
    for dom, d in res["domains"].items():
        dd = d["d_hat"]
        print(f"  {dom:22s} {('%.2f' % dd) if dd else '--':>5s} {d['eps']:7.4f} "
              f"{d['cov'][0]:8.2f} {str(d['n_cov90']):>6s} {str(d['n_cov95']):>6s} "
              f"{d['slope_med']:7.3f} {('%.3f' % (-2/dd)) if dd else '--':>6s} "
              f"{(d['slope_p95'] or 0):7.3f}")
    print(f"\n  P1 {res['P1']}\n  P2 {res.get('P2')}")


if __name__ == "__main__":
    main()
