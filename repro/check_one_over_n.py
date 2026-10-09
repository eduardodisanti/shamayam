#!/usr/bin/env python3
"""
check_one_over_n.py -- ¿el calendario de convergencia del radio es 1/n?

    python check_one_over_n.py --data-root <datasets> --cache-from <run> \
        --convergence <run>/convergence.json --out out_one_over_n

La cuenta
---------
Lo que mide stage_convergence es r(n) = media, sobre realizaciones no vistas h,
de la distancia coseno 1 - h.c_n/|c_n|, con c_n el centroide de n realizaciones
sacadas SIN reposicion de un pool de N; el limite es r_inf = 1 - |c|, con c la
media del pool (exacto: los vectores estan en la esfera unidad).

Desarrollando a segundo orden en el error del centroide, y teniendo en cuenta
que h sale del mismo pool que la muestra (E[h | S] = (N c - n c_n)/(N - n)):

    r(n) - r_inf  ~=  tr(Sigma_perp) / (2 n |c|)  *  (N + n)/(N - 1)

con Sigma_perp la covarianza del pool proyectada fuera de la direccion de c.
Relativo al limite:

    residuo(n)  ~=  tr(Sigma_perp) / (2 n |c| (1 - |c|))  *  (N + n)/(N - 1)

Para un conjunto concentrado (|c| -> 1), tr(Sigma) = 1 - |c|^2 ~ 2(1 - |c|) y
casi toda la varianza es perpendicular, asi que residuo(n) -> 1/n: la
dispersion del conjunto se cancela entre numerador y denominador. Este script
no supone eso: calcula |c| y tr(Sigma_perp) de cada concepto y compara tres
predicciones con la curva medida del run (convergence.json, sin tocarla):

    A  1/n                      universal, sin datos
    B  formula sin pool         tr(S_perp)/(2 n |c| (1-|c|))
    C  formula con pool finito  B * (N+n)/(N-1)

Los conceptos se reconstruyen con el mismo codigo que control_sup (que
reproduce el run al bit). Para dominios con varios conceptos la curva se
agrega como en reproduce._conv_aggregate: media de r(n) y media de r_inf.
Nada se ajusta: no hay ningun parametro libre.
"""
from __future__ import annotations

import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import control_sup as C          # noqa: E402
R = C.R


def stats(X):
    """|c|, tr(Sigma_perp) del pool, y N. X en la esfera unidad."""
    X = np.asarray(X, float)
    N = len(X)
    c = X.mean(0)
    nc = float(np.linalg.norm(c))
    u = c / nc
    tr = float(1.0 - nc ** 2)                 # tr(Sigma) = E|x|^2 - |c|^2
    par = float(((X @ u) - nc) @ ((X @ u) - nc) / N)   # varianza a lo largo de c
    return {"N": N, "c_norm": nc, "r_inf": 1.0 - nc, "tr_sigma": tr,
            "tr_perp": tr - par}


def predict(s, n):
    """r(n) predicho por B y por C, en unidades absolutas."""
    b = s["tr_perp"] / (2.0 * n * s["c_norm"])
    return {"B": s["r_inf"] + b,
            "C": s["r_inf"] + b * (s["N"] + n) / (s["N"] - 1)}


def crossing(ns, rel, f):
    """Primer n de la escalera desde el cual |rel| <= f y no vuelve a salir."""
    for i in range(len(ns)):
        if all(abs(v) <= f for v in rel[i:]):
            return ns[i]
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--cache-from", default=None)
    p.add_argument("--convergence", required=True)
    p.add_argument("--out", default="out_one_over_n")
    p.add_argument("--only", nargs="+", default=None)
    p.add_argument("--skip-mnist", action="store_true")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)

    conv = json.load(open(a.convergence))
    pool = {**conv.get("domains", {}), **conv.get("digits", {})}

    per = {}
    for dom, sub, X, tag, quot, n_pool, series in C.concepts(
            a.data_root, a.cache_from, a.only, a.skip_mnist):
        per.setdefault(dom, {})[sub or "_"] = stats(X)

    res = {"domains": {}}
    for dom, subs in per.items():
        m = pool[dom]
        ns = m["steps"]
        meas = np.array([v[0] for v in m["r_mean"]])
        r_inf_meas = m["r_true"]
        keys = list(subs)
        # la agregacion de reproduce: media sobre conceptos
        r_inf = float(np.mean([subs[k]["r_inf"] for k in keys]))
        pB = np.array([np.mean([predict(subs[k], n)["B"] for k in keys]) for n in ns])
        pC = np.array([np.mean([predict(subs[k], n)["C"] for k in keys]) for n in ns])
        rel_meas = (meas - r_inf_meas) / r_inf_meas
        rel_A = 1.0 / np.asarray(ns, float)
        rel_B = (pB - r_inf) / r_inf
        rel_C = (pC - r_inf) / r_inf
        # donde comparar: n >= 2 (en n=1 el desarrollo no vale) y n <= N/4
        Nmin = min(subs[k]["N"] for k in keys)
        w = [i for i, n in enumerate(ns) if 2 <= n <= max(2, Nmin // 4)]
        ratio = lambda pr: float(np.median(rel_meas[w] / pr[w])) if w else None
        d = {"n_concepts": len(keys),
             "c_norm": float(np.mean([subs[k]["c_norm"] for k in keys])),
             "tr_perp_over_tr": float(np.mean([subs[k]["tr_perp"] / subs[k]["tr_sigma"]
                                               for k in keys])),
             "r_inf_check": {"measured": r_inf_meas, "from_pool": r_inf},
             "steps": ns, "rel_measured": rel_meas.tolist(),
             "rel_A": rel_A.tolist(), "rel_B": rel_B.tolist(),
             "rel_C": rel_C.tolist(),
             "median_ratio_measured_over": {"A": ratio(rel_A), "B": ratio(rel_B),
                                            "C": ratio(rel_C)},
             "at": {}, "crossings": {}}
        for n in (5, 20, 50):
            if n in ns:
                i = ns.index(n)
                d["at"][n] = {"measured": float(rel_meas[i]), "A": float(rel_A[i]),
                              "B": float(rel_B[i]), "C": float(rel_C[i])}
        for f in (0.10, 0.05):
            d["crossings"][f"{int(f*100)}pct"] = {
                "measured": m["crossings"].get(f"within_{int(f*100)}pct"),
                "C": crossing(ns, rel_C, f)}
        res["domains"][dom] = d

    R.jdump(res, os.path.join(a.out, "one_over_n.json"))

    print(f"\n  {'dominio':22s} {'|c|':>6s}  {'perp':>5s}   "
          f"{'n=5 med/A/C':>18s}   {'n=20 med/A/C':>18s}   {'n=50 med/A/C':>18s}"
          f"   ratio med/A  med/C   x10% med/C   x5% med/C")
    for dom, d in res["domains"].items():
        def cell(n):
            v = d["at"].get(n)
            return (f"{100*v['measured']:5.1f}/{100*v['A']:4.1f}/{100*v['C']:5.1f}"
                    if v else " " * 18)
        r = d["median_ratio_measured_over"]
        cr = d["crossings"]
        print(f"  {dom:22s} {d['c_norm']:6.3f}  {d['tr_perp_over_tr']:5.2f}   "
              f"{cell(5):>18s}   {cell(20):>18s}   {cell(50):>18s}   "
              f"{r['A']:6.2f}  {r['C']:6.2f}   "
              f"{str(cr['10pct']['measured']):>4s}/{str(cr['10pct']['C']):<4s}   "
              f"{str(cr['5pct']['measured']):>4s}/{str(cr['5pct']['C']):<4s}")

    try:
        figure(res, os.path.join(a.out, "fig_one_over_n.png"))
    except Exception as e:
        print(f"  figura omitida: {type(e).__name__}: {e}")


def figure(res, path):
    import figstyle as fs
    import matplotlib.pyplot as plt
    fs.apply()
    doms = list(res["domains"])
    ncol = 3
    nrow = int(np.ceil(len(doms) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=fs.size(1.0, 1.55 * nrow),
                            squeeze=False)
    for ax, dom in zip(axs.flat, doms):
        d = res["domains"][dom]
        ns = np.asarray(d["steps"], float)
        m = np.asarray(d["rel_measured"])
        ok = m > 0
        ax.plot(ns[ok], m[ok], "o", ms=2.5, color=fs.BLUE, label="measured")
        ax.plot(ns, d["rel_A"], "-", lw=1.0, color=fs.GHOST, label="$1/n$")
        ax.plot(ns, d["rel_C"], "-", lw=1.2, color=fs.ORANGE,
                label="prediction (no free parameter)")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_ylim(1e-3, 3)
        fs.style(ax)
        fs.ident(ax, dom)
    for ax in axs.flat[len(doms):]:
        ax.axis("off")
    for ax in axs[-1]:
        ax.set_xlabel("$n$")
    for ax in axs[:, 0]:
        ax.set_ylabel("residual")
    seen = {}
    for ax in axs.flat:
        for h_, l_ in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(l_, h_)
    fig.legend(list(seen.values()), list(seen), loc="lower center", ncol=3,
               frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fs.save(fig, path)
    plt.close(fig)


if __name__ == "__main__":
    main()
