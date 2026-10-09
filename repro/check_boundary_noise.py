#!/usr/bin/env python3
"""
check_boundary_noise.py -- lo que sube, ¿es el borde de la variedad o el ruido?

    python check_boundary_noise.py --data-root <datasets> --cache-from <run> \
        --out out_boundary [--only ...] [--skip-mnist]

La pregunta
-----------
El paper mide el maximo de las distancias por pares dentro de una clase y dice
que "sube a todo n". La teoria dice otra cosa: si la variedad es compacta su
radio es finito y el maximo acumulado converge (Teorema de Monte Carlo,
Apendice A). Lo que se observa, sin embargo, no es un punto de la variedad sino
punto + ruido, y el ruido no se cociente. Si el ruido tiene colas no acotadas,
el maximo de n observaciones crece como ~sigma*sqrt(2 log n) sin tope, aunque
la variedad debajo sea compacta. La alternativa que la teoria tambien admite:
el borde es finito pero se alcanza despacio, porque la medida pone poca masa
cerca de el. Este script separa las dos.

El diseno
---------
Cada realizacion (ya en el cociente) se descompone en una parte de forma y una
residual: la forma es su proyeccion sobre las k primeras componentes
principales del pool de su concepto, re-proyectada a la esfera; el residuo es
lo que queda. k se DECLARA: el menor numero de componentes que explica el 99%
de la varianza del pool. Se reportan tambien 95% y 99.9% como sensibilidad,
porque truncar tambien quita forma rara en direcciones de poca varianza, y un
lector tiene que poder ver cuanto depende la conclusion de k.

Para cada n de la escalera y cada repeticion se toma un subconjunto al azar y
se mide el maximo por pares en tres versiones: crudo (coseno, lo del paper),
forma (coseno sobre la parte de forma) y residuo (euclidea sobre el residuo).
Crecimiento G = maximo(n mayor) / maximo(n = 40).

PREDICCIONES -- fijadas ANTES de correr, 2026-09-23
---------------------------------------------------
  P1  el crecimiento lo lleva el ruido: en cada dominio, con k al 99%,
      (G_forma - 1) <= 0.5 * (G_crudo - 1).
  P2  el residuo se comporta como valores extremos de ruido: su maximo es
      lineal en sqrt(log n) con R^2 >= 0.9.
Si P1 falla en un dominio, lo que sube ahi es forma, y se reporta como "el
borde es finito y se alcanza despacio" (o como no resuelto), no como ruido.
Nada se ajusta para que pase.
"""
from __future__ import annotations

import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import control_sup as C          # noqa: E402
R = C.R

NS = [10, 20, 40, 80, 160, 320, 640, 1280, 2560, 5000]
REPS = 10
FRACS = (0.95, 0.99, 0.999)
PRIMARY = 0.99
PREDICTION = {"fixed_on": "2026-09-23",
              "P1": "(G_shape - 1) <= 0.5 * (G_raw - 1), k at 99% variance",
              "P2": "residual max linear in sqrt(log n), R^2 >= 0.9",
              "G": "max(n_largest) / max(n=40)"}


def pca(X):
    mu = X.mean(0)
    U, s, Vt = np.linalg.svd(X - mu, full_matrices=False)
    var = s ** 2 / (s ** 2).sum()
    return mu, Vt, np.cumsum(var)


def split(X, mu, Vt, k):
    Z = (X - mu) @ Vt[:k].T
    S = mu + Z @ Vt[:k]
    res = X - S
    S = S / np.maximum(np.linalg.norm(S, axis=1, keepdims=True), 1e-12)
    return S, res


def max_cos(A):
    G = A @ A.T
    np.fill_diagonal(G, np.inf)
    return float(1.0 - G.min())


def max_euc(A):
    sq = (A * A).sum(1)
    D2 = sq[:, None] + sq[None, :] - 2 * A @ A.T
    return float(np.sqrt(max(D2.max(), 0.0)))


def curves(X, tag, ks):
    N = len(X)
    ns = [n for n in NS if n <= N]
    out = {"ns": ns, "raw": [], **{f"shape_{f}": [] for f in ks},
           **{f"res_{f}": [] for f in ks}}
    parts = {f: split(X, *ks[f]) for f in ks}
    for n in ns:
        acc = {k: [] for k in out if k != "ns"}
        for rep in range(REPS):
            g = np.random.default_rng(R.seed_for(R.SEED, tag, "boundary", n, rep))
            idx = g.choice(N, n, replace=False)
            acc["raw"].append(max_cos(X[idx]))
            for f, (S, res) in parts.items():
                acc[f"shape_{f}"].append(max_cos(S[idx]))
                acc[f"res_{f}"].append(max_euc(res[idx]))
        for k in acc:
            out[k].append(float(np.mean(acc[k])))
    return out


def growth(ns, y):
    if 40 not in ns or ns[-1] <= 40:
        return None
    return y[-1] / y[ns.index(40)]


def r2_sqrtlog(ns, y):
    x = np.sqrt(np.log(np.asarray(ns, float)))
    y = np.asarray(y)
    A = np.vstack([x, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss = ((y - y.mean()) ** 2).sum()
    return float(1 - ((y - pred) ** 2).sum() / ss) if ss > 0 else None


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--cache-from", default=None)
    p.add_argument("--out", default="out_boundary")
    p.add_argument("--only", nargs="+", default=None)
    p.add_argument("--skip-mnist", action="store_true")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "PREDICCION.json"), "w") as f:
        json.dump(PREDICTION, f, indent=1)

    per = {}
    for dom, sub, X, tag, quot, n_pool, series in C.concepts(
            a.data_root, a.cache_from, a.only, a.skip_mnist):
        X = np.asarray(X, float)
        mu, Vt, cum = pca(X)
        ks = {f: (mu, Vt, int(np.searchsorted(cum, f) + 1)) for f in FRACS}
        c = curves(X, tag, ks)
        c["k"] = {str(f): ks[f][2] for f in FRACS}
        c["dim"] = int(X.shape[1])
        per.setdefault(dom, {})[sub or "_"] = c
        print(f"    {tag:28s} N={len(X):6d}  k99={ks[PRIMARY][2]:3d}/{X.shape[1]}",
              flush=True)

    res = {"prediction": PREDICTION, "domains": {}}
    for dom, subs in per.items():
        keys = list(subs)
        ns = min((subs[k]["ns"] for k in keys), key=len)
        m = len(ns)
        agg = {q: np.mean([subs[k][q][:m] for k in keys], axis=0).tolist()
               for q in subs[keys[0]] if q not in ("ns", "k", "dim")}
        d = {"ns": ns, "n_concepts": len(keys), "curves": agg,
             "k": {k: subs[k]["k"] for k in keys}}
        g_raw = growth(ns, agg["raw"])
        d["G"] = {"raw": g_raw}
        for f in FRACS:
            d["G"][f"shape_{f}"] = growth(ns, agg[f"shape_{f}"])
            d["G"][f"res_{f}"] = growth(ns, agg[f"res_{f}"])
        gs = d["G"][f"shape_{PRIMARY}"]
        d["P1"] = (None if g_raw is None or gs is None
                   else bool(gs - 1 <= 0.5 * (g_raw - 1)))
        d["R2_res_sqrtlog"] = r2_sqrtlog(ns, agg[f"res_{PRIMARY}"])
        d["R2_raw_sqrtlog"] = r2_sqrtlog(ns, agg["raw"])
        d["P2"] = (None if d["R2_res_sqrtlog"] is None
                   else bool(d["R2_res_sqrtlog"] >= 0.9))
        res["domains"][dom] = d

    R.jdump(res, os.path.join(a.out, "boundary_noise.json"))
    print(f"\n  {'dominio':22s} {'n_max':>6s}  {'G crudo':>8s}  "
          + "  ".join(f"{'G forma '+str(f):>13s}" for f in FRACS)
          + f"  {'P1':>5s}  {'R2 res':>6s}  {'P2':>5s}")
    for dom, d in res["domains"].items():
        G = d["G"]
        fmt = lambda v: "--" if v is None else f"{v:.2f}"
        print(f"  {dom:22s} {d['ns'][-1]:6d}  {fmt(G['raw']):>8s}  "
              + "  ".join(f"{fmt(G['shape_'+str(f)]):>13s}" for f in FRACS)
              + f"  {str(d['P1']):>5s}  {fmt(d['R2_res_sqrtlog']):>6s}  "
              f"{str(d['P2']):>5s}")


if __name__ == "__main__":
    main()
