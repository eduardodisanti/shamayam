#!/usr/bin/env python3
"""
check_border_auc_deskew.py -- el borde de MNIST con el cociente declarado.

    python check_border_auc_deskew.py --cache-from ../../v8/run_o --out ../_work/border/mnist_deskew

POST HOC -- declarado como tal (2026-09-24)
-------------------------------------------
Este brazo se corre DESPUES de ver que MNIST no pasa el criterio del borde
(check_border_auc.py: n_settle = 800 > 25). La corrida original midio MNIST solo
con l2, sin deskew, aunque el paper declara deskew como el cociente de los
digitos escritos. La pregunta es si el fallo se debe a esa invariancia no
declarada. Se reporta junto al brazo original, que NO se reemplaza.

Nada cambia salvo el cociente
-----------------------------
  - criterio: el mismo, importado de check_border_auc (fijado 2026-09-23):
    n_settle = primer n desde el cual |AUC(n) - AUC(final)| <= 0.01 y no sale;
    pasa si n_settle <= 25.
  - sorteos: los mismos (mismo tag por clase -> mismas semillas, mismos n
    vistos, mismos held-out, mismos 200 "no clase").
  - "no clase": las otras nueve clases, con el MISMO cociente aplicado.
  - cociente: deskew(X, 28) y luego l2, exactamente como reproduce.py.
El brazo raw se recalcula aqui y debe reproducir la tabla (0.980, n_settle 800);
si no la reproduce, el brazo deskew no se lee.
"""
from __future__ import annotations

import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "src"))
import check_border_auc as B                         # noqa: E402
from run_experiment import l2_normalise, deskew      # noqa: E402

LABEL = "MNIST 28x28"


def arm(X0, y0, fn):
    Xc = X0 if fn is None else fn(X0, 28)
    per = {}
    classes = {c: l2_normalise(np.asarray(Xc[y0 == c], float)) for c in range(10)}
    for c in range(10):
        A = classes[c]
        others = np.vstack([classes[o] for o in range(10) if o != c])

        def out_fn(seen, g, others=others):
            return others[g.choice(len(others), B.N_OUT, replace=False)]
        r = B.curve(A, f"{LABEL}|{c}", out_fn)
        per[str(c)] = r
        print(f"    {LABEL}|{c}  AUC n=1 {r['auc'][0]:.3f}  "
              f"n={r['steps'][-1]} {r['auc'][-1]:.3f}", flush=True)
    ns = min((per[k]["steps"] for k in per), key=len)
    y = np.mean([per[k]["auc"][:len(ns)] for k in per], 0).tolist()
    return {"steps": ns, "auc": y, "n_settle": B.n_settle(ns, y),
            "auc_final": y[-1], "n_final": ns[-1],
            "auc_at": {n: y[ns.index(n)] for n in (1, 5, 25) if n in ns},
            "pass": (B.n_settle(ns, y) or 10**9) <= B.NSET, "per_class": per}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cache-from", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--arms", nargs="+", default=["raw", "deskew"])
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    crit = dict(B.CRITERION)
    crit["post_hoc"] = ("deskew arm run 2026-09-24 after the raw arm failed the "
                        "criterion; criterion and draws unchanged")
    with open(os.path.join(a.out, "CRITERIO.json"), "w") as f:
        json.dump(crit, f, indent=1)
    path = os.path.join(a.cache_from, "cache", "mnist.npz")
    if not os.path.exists(path):
        raise SystemExit(f"falta {path}: reproduce.py lo escribe al medir MNIST "
                         "(stage 5); pasa --cache-from apuntando a esa corrida.")
    z = np.load(path)
    X0, y0 = z["X"], z["y"]
    res = {"criterion": crit, "arms": {}}
    for nm in a.arms:
        print(f"  brazo {nm}", flush=True)
        res["arms"][nm] = arm(X0, y0, None if nm == "raw" else deskew)
        with open(os.path.join(a.out, "border_auc_deskew.json"), "w") as f:
            json.dump(res, f)
    print(f"\n  {'brazo':8s} {'n=1':>7s} {'n=5':>7s} {'n=25':>7s} {'final':>7s} "
          f"{'(n)':>6s} {'n_settle':>9s}  pasa")
    for nm, d in res["arms"].items():
        g = lambda n: f"{d['auc_at'][n]:.3f}" if n in d["auc_at"] else "-"
        print(f"  {nm:8s} {g(1):>7s} {g(5):>7s} {g(25):>7s} {d['auc_final']:7.3f} "
              f"{d['n_final']:6d} {str(d['n_settle']):>9s}  {d['pass']}")


if __name__ == "__main__":
    main()
