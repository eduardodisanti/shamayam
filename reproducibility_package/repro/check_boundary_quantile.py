#!/usr/bin/env python3
"""
check_boundary_quantile.py -- ¿el maximo lo ponen unas pocas realizaciones?

    python check_boundary_quantile.py --data-root <datasets> --cache-from <run> \
        --out out_quantile [--only ...]

La hipotesis (Eduardo, 2026-09-23)
----------------------------------
La variedad nominal es compacta y su borde se asienta. Los pools "nominales"
contienen una fraccion pequena de realizaciones anomalas. Con n chico casi
nunca entra una; al crecer n entra alguna con probabilidad -> 1 y el maximo
salta a su nivel. El maximo mide la anomalia mas rara de la muestra, no el
borde de la variedad.

Lo que se mide, y lo que cada cosa puede y no puede decir
---------------------------------------------------------
1. Cuantiles de la distancia por pares (p50, p99, p99.9) y el maximo, contra n.
   ADVERTENCIA, fijada antes de correr: que un cuantil se asiente NO prueba la
   hipotesis. Un cuantil es un funcional de la medida y converge por la ley de
   los grandes numeros con o sin anomalias -- es la misma trampa de la
   objecion 3. Se reporta como contexto, no como prueba.
2. CONCENTRACION -- esto si discrimina. Si el maximo lo ponen anomalias raras,
   los pares que realizan el maximo en sorteos independientes con n grande
   involucran una y otra vez a las MISMAS pocas realizaciones. Si el maximo es
   el borde liso de una variedad con densidad, los pares extremos cambian de
   sorteo a sorteo. Se mide la fraccion de los pares maximos (n >= 1280,
   todas las repeticiones) que involucran a alguna de las 5 realizaciones mas
   frecuentes, y se compara con lo que daria el azar si los extremos fueran
   distintos en cada sorteo.
3. Las realizaciones que mas aparecen se guardan (indice en el pool y curva)
   para que un experto del dominio las lea. El juicio "esto es una anomalia"
   es del experto y queda documentado aparte; este script no lo emite.

PREDICCION -- fijada ANTES de correr, 2026-09-23
------------------------------------------------
  C1  en cada dominio de serie temporal, las 5 realizaciones mas frecuentes
      participan en al menos el 50% de los pares maximos con n >= 1280.
Si no se cumple en un dominio, ahi el maximo no lo ponen unas pocas
realizaciones, y la hipotesis de contaminacion no lo explica.
"""
from __future__ import annotations

import argparse, json, os, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import control_sup as C          # noqa: E402
R = C.R

NS = [40, 80, 160, 320, 640, 1280, 2560, 5000]
REPS = 10
BIG = 1280
TOPK = 5
PREDICTION = {"fixed_on": "2026-09-23",
              "C1": "top-5 realisations take part in >= 50% of the maximum pairs "
                    "at n >= 1280, in every time-series domain",
              "warning": "a settling quantile is a functional of the measure and "
                         "does not by itself support the hypothesis"}


def stats(A):
    G = A @ A.T
    iu = np.triu_indices(len(A), 1)
    d = 1.0 - G[iu]
    k = int(np.argmax(d))
    q = np.quantile(d, [0.5, 0.99, 0.999])
    return q, float(d[k]), (int(iu[0][k]), int(iu[1][k]))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--cache-from", default=None)
    p.add_argument("--out", default="out_quantile")
    p.add_argument("--only", nargs="+", default=None)
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "PREDICCION.json"), "w") as f:
        json.dump(PREDICTION, f, indent=1)

    res = {"prediction": PREDICTION, "domains": {}}
    offenders_curves = {}
    for dom, sub, X, tag, quot, n_pool, series in C.concepts(
            a.data_root, a.cache_from, a.only, True):
        if not series or sub not in (None, "_"):
            # un concepto por dominio: los dominios con subconjuntos (mareas,
            # solar) se miden en su subconjunto mas grande, ver abajo
            if not series:
                continue
        X = np.asarray(X, float)
        key = dom if sub in (None, "_") else f"{dom}|{sub}"
        N = len(X)
        ns = [n for n in NS if n <= N]
        rows = {"n": [], "p50": [], "p99": [], "p999": [], "max": []}
        pairs_big = []
        for n in ns:
            acc = []
            for rep in range(REPS):
                g = np.random.default_rng(R.seed_for(R.SEED, tag, "quantile", n, rep))
                idx = g.choice(N, n, replace=False)
                q, mx, (i, j) = stats(X[idx])
                acc.append([*q, mx])
                if n >= BIG:
                    pairs_big.append((int(idx[i]), int(idx[j])))
            m = np.mean(acc, 0)
            rows["n"].append(n)
            for k_, v in zip(("p50", "p99", "p999", "max"), m):
                rows[k_].append(float(v))
        tails = {k_: rows[k_][-1] / rows[k_][-2] - 1 for k_ in ("p50", "p99", "p999", "max")}
        d = {"N": N, "curves": rows, "tail_last_doubling": tails}
        if pairs_big:
            cnt = Counter(i for pr in pairs_big for i in pr)
            top = [i for i, _ in cnt.most_common(TOPK)]
            share = sum(1 for pr in pairs_big if pr[0] in top or pr[1] in top) / len(pairs_big)
            d.update({"n_max_pairs": len(pairs_big), "distinct_in_max_pairs": len(cnt),
                      "top": [[i, c] for i, c in cnt.most_common(10)],
                      "top5_share": share, "C1": bool(share >= 0.5)})
            offenders_curves[key] = {"typical": X[np.argsort(1 - X @ (X.mean(0) / np.linalg.norm(X.mean(0))))[N // 2]].tolist(),
                                     "top": {str(i): X[i].tolist() for i in top}}
        res["domains"][key] = d
        print(f"    {key:30s} N={N:6d}  tail p99 {100*tails['p99']:+5.1f}%  max "
              f"{100*tails['max']:+5.1f}%  " + (f"top5 {100*d['top5_share']:5.1f}% de "
              f"{d['n_max_pairs']} pares ({d['distinct_in_max_pairs']} distintas)"
              if pairs_big else "(n < 1280)"), flush=True)

    R.jdump(res, os.path.join(a.out, "boundary_quantile.json"))
    R.jdump(offenders_curves, os.path.join(a.out, "offenders.json"))
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        keys = list(offenders_curves)
        fig, axs = plt.subplots(len(keys), 1, figsize=(8, 2.2 * len(keys)), squeeze=False)
        for ax, k in zip(axs[:, 0], keys):
            o = offenders_curves[k]
            ax.plot(o["typical"], color="0.6", lw=2, label="typical")
            for i, y in o["top"].items():
                ax.plot(y, lw=0.9, label=f"#{i}")
            ax.set_title(k, fontsize=9); ax.legend(fontsize=6, ncol=6)
        plt.tight_layout(); plt.savefig(os.path.join(a.out, "offenders.png"), dpi=110)
    except Exception as e:
        print(f"  figura omitida: {e}")


if __name__ == "__main__":
    main()
