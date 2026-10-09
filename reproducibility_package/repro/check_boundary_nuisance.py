#!/usr/bin/env python3
"""
check_boundary_nuisance.py -- lo que no se asienta, ¿es la variedad?

    python check_boundary_nuisance.py --data-root <datasets> --cache-from <run> \
        --out out_nuisance [--only ...]

La pregunta
-----------
El paper dice que el maximo de las distancias por pares dentro de una clase
"sube a todo n". La teoria dice que el borde de una variedad compacta es finito
y que el maximo acumulado converge a el. Mirando el par mas lejano de cada
dominio (de 5000) se ve que el maximo NO lo pone la forma: en PM es la misma
curva desplazada unas muestras en el tiempo --- un desfase que el cociente
declarado no quita --- y en ECG real es un latido roto, plano en cero desde la
mitad de la ventana. La hipotesis es entonces:

    lo que no se asienta no es la variedad: son los nuisances que el cociente
    no quita y los registros que no son realizaciones del proceso.

El diseno: dos correcciones declaradas, una por cada causa
----------------------------------------------------------
  ALINEAR  cociente por traslacion temporal. Cada realizacion se desplaza
           (con relleno por el valor del borde, no circular) el entero s en
           [-S, S] que maximiza su producto con la plantilla del pool; la
           plantilla se recalcula con las alineadas y se repite dos veces,
           como el fiducial corregido de las mareas. S = 10% de la ventana.
           Despues se vuelve a aplicar el cociente declarado del dominio.
           Solo series temporales.
  DEPURAR  fuera los registros que no son realizaciones del proceso, con un
           criterio de ARTEFACTO fijado antes de medir y que no mira ninguna
           distancia: una racha de valores exactamente iguales consecutivos
           de al menos el 25% de la ventana (relleno, recorte, sensor
           colgado). Un criterio por distancia quitaria el borde por
           definicion y no se usa.

Se mide el maximo por pares (coseno, como el paper) en cuatro condiciones:
crudo, alineado, depurado, alineado+depurado, sobre subconjuntos al azar de la
misma escalera y con las mismas semillas en las cuatro.

PREDICCIONES -- fijadas ANTES de correr, 2026-09-23
---------------------------------------------------
  G    = max(n mayor) / max(n = 40)          crecimiento en la ventana
  tail = max(n mayor) / max(n mayor / 2) - 1 crecimiento en la ultima duplicacion

  P1  PM real: alinear quita al menos la mitad del crecimiento:
      (G_alin - 1) <= 0.5 (G_crudo - 1).
  P2  ECG real: alinear+depurar quita al menos la mitad del crecimiento.
  P3  en la condicion corregida (alinear+depurar) el maximo se asienta:
      tail <= 5%, en cada dominio de serie temporal.
Un dominio que no cumple se reporta tal cual: ahi el maximo sigue subiendo
por algo que estas dos correcciones no explican.
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
SHIFT_FRAC = 0.10
FLAT_FRAC = 0.25
PREDICTION = {"fixed_on": "2026-09-23",
              "G": "max(n_largest)/max(n=40)",
              "tail": "max(n_largest)/max(n_largest/2) - 1",
              "P1": "PM real: (G_align - 1) <= 0.5 (G_raw - 1)",
              "P2": "ECG real: (G_align+screen - 1) <= 0.5 (G_raw - 1)",
              "P3": "align+screen: tail <= 0.05 in every time-series domain",
              "shift": "S = 10% of window, edge padding, 2 template iterations",
              "screen": "longest run of identical consecutive values >= 25% of window"}


def shifted(X, s):
    if s == 0:
        return X
    Y = np.empty_like(X)
    if s > 0:
        Y[:, s:] = X[:, :-s]; Y[:, :s] = X[:, :1]
    else:
        Y[:, :s] = X[:, -s:]; Y[:, s:] = X[:, -1:]
    return Y


def align(X, quot, iters=2):
    L = X.shape[1]
    S = max(1, int(round(SHIFT_FRAC * L)))
    shifts = list(range(-S, S + 1))
    A = X.copy()
    best = np.zeros(len(X), int)
    for _ in range(iters):
        T = A.mean(0)
        T = T / max(np.linalg.norm(T), 1e-12)
        sc = np.stack([shifted(X, s) @ T for s in shifts], 1)
        best = np.asarray(shifts)[sc.argmax(1)]
        A = np.empty_like(X)
        for s in np.unique(best):
            m = best == s
            A[m] = shifted(X[m], int(s))
    return C.Q[quot](A), best


def longest_flat(X):
    eq = np.diff(X, axis=1) == 0
    out = np.zeros(len(X), int)
    run = np.zeros(len(X), int)
    for j in range(eq.shape[1]):
        run = np.where(eq[:, j], run + 1, 0)
        out = np.maximum(out, run)
    return out + 1


def max_cos(A):
    G = A @ A.T
    np.fill_diagonal(G, np.inf)
    return float(1.0 - G.min())


def curve(X, tag, cond):
    N = len(X)
    ns = [n for n in NS if n <= N]
    ys = []
    for n in ns:
        v = []
        for rep in range(REPS):
            g = np.random.default_rng(R.seed_for(R.SEED, tag, "nuisance", n, rep))
            v.append(max_cos(X[g.choice(N, n, replace=False)]))
        ys.append(float(np.mean(v)))
    return ns, ys


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--cache-from", default=None)
    p.add_argument("--out", default="out_nuisance")
    p.add_argument("--only", nargs="+", default=None)
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "PREDICCION.json"), "w") as f:
        json.dump(PREDICTION, f, indent=1)

    per = {}
    for dom, sub, X, tag, quot, n_pool, series in C.concepts(
            a.data_root, a.cache_from, a.only, True):
        if not series:
            continue
        X = np.asarray(X, float)
        L = X.shape[1]
        flat = longest_flat(X)
        keep = flat < FLAT_FRAC * L
        Xa, sh = align(X, quot)
        conds = {"raw": X, "align": Xa, "screen": X[keep], "align+screen": Xa[keep]}
        c = {"N": len(X), "screened_out": int((~keep).sum()),
             "shift_hist": {int(s): int((sh == s).sum()) for s in np.unique(sh)},
             "curves": {}}
        for k, Y in conds.items():
            ns, ys = curve(Y, tag, k)
            c["curves"][k] = {"ns": ns, "max": ys}
        per.setdefault(dom, {})[sub or "_"] = c
        print(f"    {tag:28s} N={len(X):6d}  fuera={int((~keep).sum()):4d}  "
              f"|desfase| medio={np.abs(sh).mean():.2f}", flush=True)

    def G(ns, y):
        return y[-1] / y[ns.index(40)] if 40 in ns and ns[-1] > 40 else None

    def tail(ns, y):
        return y[-1] / y[-2] - 1 if len(ns) >= 2 else None

    res = {"prediction": PREDICTION, "domains": {}}
    for dom, subs in per.items():
        keys = list(subs)
        d = {"n_concepts": len(keys),
             "screened_out": sum(subs[k]["screened_out"] for k in keys),
             "N": sum(subs[k]["N"] for k in keys), "cond": {}}
        for cond in ("raw", "align", "screen", "align+screen"):
            ns = min((subs[k]["curves"][cond]["ns"] for k in keys), key=len)
            y = np.mean([subs[k]["curves"][cond]["max"][:len(ns)] for k in keys], 0).tolist()
            d["cond"][cond] = {"ns": ns, "max": y, "G": G(ns, y), "tail": tail(ns, y)}
        gr = d["cond"]["raw"]["G"]
        ok = lambda g: None if (g is None or gr is None) else bool(g - 1 <= 0.5 * (gr - 1))
        if dom == "PM real (nominal)":
            d["P1"] = ok(d["cond"]["align"]["G"])
        if dom == "ECG real (MIT-BIH)":
            d["P2"] = ok(d["cond"]["align+screen"]["G"])
        t = d["cond"]["align+screen"]["tail"]
        d["P3"] = None if t is None else bool(t <= 0.05)
        res["domains"][dom] = d

    R.jdump(res, os.path.join(a.out, "boundary_nuisance.json"))
    fmt = lambda v: "--" if v is None else f"{v:.2f}"
    pct = lambda v: "--" if v is None else f"{100*v:+.1f}%"
    print(f"\n  {'dominio':22s} {'fuera':>6s}   " + "   ".join(
        f"{c+' G/tail':>20s}" for c in ("raw", "align", "screen", "align+screen"))
        + "   P1/P2   P3")
    for dom, d in res["domains"].items():
        cells = "   ".join(f"{fmt(d['cond'][c]['G']):>11s}/{pct(d['cond'][c]['tail']):>8s}"
                           for c in ("raw", "align", "screen", "align+screen"))
        pp = d.get("P1", d.get("P2", ""))
        print(f"  {dom:22s} {d['screened_out']:6d}   {cells}   {str(pp):>5s}  {str(d['P3']):>5s}")
        m = {c: [round(x, 3) for x in d['cond'][c]['max']] for c in d['cond']}
        print(f"      max crudo {m['raw']}\n      max corr. {m['align+screen']}")


if __name__ == "__main__":
    main()
