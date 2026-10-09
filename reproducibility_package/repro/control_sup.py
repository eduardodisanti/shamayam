#!/usr/bin/env python3
"""
control_sup.py -- control de metrica: coseno frente a L-infinito (apendice).

    python control_sup.py --data-root <datasets> --cache-from <run> --out out_sup
    python control_sup.py ... --reference <run>/convergence.json   # verifica el brazo coseno
    python control_sup.py ... --only "PM real" "NOAA tides"         # subconjunto de dominios

La pregunta
-----------
La teoria (Arzela-Ascoli) garantiza finitud en C0([0,T]) con la norma del
supremo. La medicion (stage_convergence en reproduce.py) usa coseno sobre el
cociente. La equivalencia de normas en R^N preserva la topologia pero no las
constantes, y en [0,T] la desigualdad va en contra: ||.||_2 <= sqrt(T)||.||_inf,
asi que N_L2(eps) <= N_sup(eps) y que el coseno sature no implica que sature el
supremo. Este script mide la misma cantidad en L-infinito.

Que L-infinito sobre la malla es la cantidad de la teoria: por equicontinuidad
(Heine-Cantor), el maximo sobre la malla dista del supremo continuo a lo sumo
omega(Delta t), de forma uniforme en toda la familia.

El diseno: cambia UNA variable
-----------------------------
Mismos datos, mismo submuestreo, mismo cociente, mismo observable, MISMOS
SORTEOS (las semillas de _conv_one, por dominio, n y repeticion), misma escalera
CONV_STEPS, mismos held-out. Solo cambia la distancia. Nada de reproduce.py se
modifica: se importa.

Brazos
------
  cos        reproduce._conv_one tal cual. Es el brazo del paper; con
             --reference se comprueba que coincide con convergence.json.
  l2         la misma medicion en L2 (euclidea) sobre el cociente. Descriptivo,
             no entra en el criterio. Existe porque el coseno sobre la esfera
             es ||u-v||^2/2: una distancia AL CUADRADO, cuya fluctuacion
             relativa es el doble que la de la norma. Comparar cruces
             relativos del coseno con los de L-inf mezcla ese factor con el
             efecto de la metrica; L2 frente a L-inf lo aisla.
  linf       la misma medicion en L-infinito (chebyshev) sobre los vectores
             del cociente.
  linf_med3  L-infinito tras una mediana movil de ancho 3 sobre el observable,
             re-proyectada al mismo cociente. Es un cambio de OBSERVABLE, no de
             cociente: el ruido no es una accion de grupo y no se cociente.
             Ancho 3 quita saltos aislados de una muestra (fallo de sensor) y
             nada mas ancho. Solo series temporales; no se aplica a digitos.
             Se reporta al lado del crudo y NUNCA lo sustituye.

Detalles declarados
-------------------
  * Centroide. En coseno la escala del centroide es irrelevante; en L-inf no.
    La media de vectores unitarios tiene norma < 1, y medirla tal cual inflaria
    el radio en supremo por un artefacto nuestro. Se re-proyecta a la esfera
    unidad (l2) antes de medir. Para datos z-normalizados la media ya tiene
    media cero, y la proyeccion l2 coincide con el cociente declarado.
  * eps de la red: la mediana intra-conjunto, como _conv_eps, con la misma
    semilla y el mismo pool, pero en L-inf.
  * La mediana movil es equivariante bajo x -> a x + b (a > 0), asi que
    filtrar el vector ya cocientado y volver a cocientar es lo mismo que
    filtrar la senal cruda y cocientar. Por eso se aplica igual a los dominios
    que llegan ya cocientados desde la cache (mareas, solar).

CRITERIO -- fijado ANTES de correr, 2026-09-23
----------------------------------------------
Para cada dominio, n95 = primer n desde el cual el radio medio entra y SE
MANTIENE dentro del 5% de su limite (crossings()['within_5pct'] de
reproduce.py, sin cambios).

    PASA  si  n95(linf) <= 10 * n95(cos)   y   n95(linf) <= 0.1 * n_pool

Si n95(linf) no existe dentro de la escalera: NO PASA (censurado), y se reporta
como tal. Si n95(cos) no existe, el criterio no se puede evaluar: N/A.
linf_med3 se evalua con el mismo criterio, contra el mismo n95(cos).
"""
from __future__ import annotations

import argparse, hashlib, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reproduce as R                      # noqa: E402  (tambien anade src/ al path)
from run_experiment import l2_normalise, z_normalise, greedy_net   # noqa: E402

CRITERION = {
    "fixed_on": "2026-09-23",
    "reading": "within_5pct",
    "max_ratio_to_cos": 10.0,
    "max_frac_of_pool": 0.10,
    "text": "PASS iff n95(linf) <= 10*n95(cos) and n95(linf) <= 0.1*n_pool; "
            "censored linf -> FAIL; censored cos -> N/A",
}
MED_WIDTH = 3
Q = {"l2": l2_normalise, "znorm": z_normalise}


# --------------------------------------------------------------------------- #
# la medicion en L-infinito, calcada de reproduce._conv_one

def _proj(c):
    """Centroide re-proyectado a la esfera unidad (ver 'Detalles declarados')."""
    return c / max(float(np.linalg.norm(c)), 1e-12)


def _metric_eps(A, tag, metric):
    """Como reproduce._conv_eps: misma semilla, mismo pool, otra distancia."""
    from scipy.spatial.distance import cdist
    k = min(R.CONV_EPS_POOL, len(A))
    g = np.random.default_rng(R.seed_for(R.SEED, tag, "conv-eps"))
    P = A[g.choice(len(A), k, replace=False)]
    w = cdist(P, P, metric)
    return float(np.median(w[np.triu_indices(k, 1)]))


def _greedy_net(X, eps, metric):
    """Red eps greedy. Misma regla que run_experiment.greedy_net: se guarda x
    si su distancia a todo prototipo supera eps."""
    P = np.empty_like(X)
    P[0] = X[0]
    k = 1
    for i in range(1, len(X)):
        d = np.abs(P[:k] - X[i])
        d = d.max(1) if metric == "chebyshev" else np.sqrt((d * d).sum(1))
        if d.min() > eps:
            P[k] = X[i]
            k += 1
    return k


def _conv_one_metric(A, eps, tag, metric, n_pool=None):
    """reproduce._conv_one con otra distancia y centroide proyectado.
    Las semillas son las mismas, asi que los sorteos son los mismos."""
    from scipy.spatial.distance import cdist
    c_all = _proj(A.mean(0, keepdims=True))
    r_true = float(cdist(A, c_all, metric).mean())
    steps = [n for n in R.CONV_STEPS
             if n + R.CONV_HELD_MIN <= len(A) and n <= R.CONV_NMAX]
    out = {k: [] for k in ("r_mean", "r_max", "bbox", "n_net")}
    for n in steps:
        acc = {k: [] for k in out}
        for rep in range(R.reps_for(n)):
            g = np.random.default_rng(R.seed_for(R.SEED, tag, "conv", n, rep))
            p = g.permutation(len(A))
            S, H = A[p[:n]], A[p[n:n + R.CONV_HELD]]
            ch = _proj(S.mean(0, keepdims=True))
            acc["n_net"].append(_greedy_net(S, eps, metric))
            D = cdist(H, ch, metric)
            acc["r_mean"].append(float(D.mean()))
            acc["r_max"].append(float(D.max()))
            acc["bbox"].append(float(np.sum(S.max(0) - S.min(0))))
        for k in out:
            out[k].append([float(np.mean(acc[k])), float(np.std(acc[k]))])
    return {"steps": steps, "eps": float(eps), "r_true": r_true,
            "crossings": R.crossings(steps, [v[0] for v in out["r_mean"]], r_true),
            "reps_per_step": {str(n): R.reps_for(n) for n in steps},
            "n_available": int(len(A)),
            "n_pool": int(n_pool if n_pool is not None else len(A)), **out}


def _med3(X, quot):
    from scipy.ndimage import median_filter
    return Q[quot](median_filter(X, size=(1, MED_WIDTH), mode="nearest"))


def measure(X, tag, quot, n_pool, arms):
    """Los brazos pedidos sobre un concepto. X ya esta en el cociente."""
    res = {}
    if "cos" in arms:
        res["cos"] = R._conv_one(X, R._conv_eps(X, tag), greedy_net, tag,
                                 n_pool=n_pool)
    for arm, metric in (("l2", "euclidean"), ("linf", "chebyshev")):
        if arm in arms:
            res[arm] = _conv_one_metric(X, _metric_eps(X, tag, metric), tag,
                                        metric, n_pool=n_pool)
    if "linf_med3" in arms:
        Xf = _med3(X, quot)
        res["linf_med3"] = _conv_one_metric(Xf, _metric_eps(Xf, tag, "chebyshev"),
                                            tag, "chebyshev", n_pool=n_pool)
    return res


# --------------------------------------------------------------------------- #
# los dominios, cargados exactamente como en stage_convergence

def concepts(root, cache_from, only, skip_mnist):
    """Genera (dominio, subconjunto|None, X, tag, cociente, n_pool, serie)."""
    want = (lambda s: True) if not only else \
        (lambda s: any(o.lower() in s.lower() for o in only))

    try:
        DOM, _, _ = R.load_physical(root)
    except (SystemExit, FileNotFoundError, OSError) as e:
        print(f"  AVISO: dominios fisicos NO medidos ({type(e).__name__}: {e}).\n"
              f"         Pasa --data-root apuntando a datasets/.", flush=True)
        DOM = {}
    for nm, (A, q) in DOM.items():
        if not want(nm):
            continue
        n = min(R.CONV_NMAX + R.CONV_HELD, len(A))
        rng = np.random.default_rng(R.seed_for(R.SEED, nm, "conv-subsample"))
        X = Q[q](A[rng.choice(len(A), n, replace=False)])
        yield nm, None, X, nm, q, len(A), True

    cache = os.path.join(cache_from, "cache") if cache_from else None
    sets = {}
    if want("UCI digits 8x8"):
        from sklearn.datasets import load_digits
        sets["UCI digits 8x8"] = load_digits(return_X_y=True)
    if not skip_mnist and want("MNIST 28x28") and cache and \
            os.path.exists(os.path.join(cache, "mnist.npz")):
        z = np.load(os.path.join(cache, "mnist.npz"))
        sets["MNIST 28x28"] = (z["X"], z["y"])
    if want("Spoken digits (FSDD)") and cache and \
            os.path.exists(os.path.join(cache, "spoken.npz")):
        from audio_mnist import load_spoken
        Xa, ya, _ = load_spoken(None, os.path.join(cache, "spoken.npz"))
        sets["Spoken digits (FSDD)"] = (Xa, ya)
    for label, (X0, y0) in sets.items():
        for c in range(10):
            A = l2_normalise(np.asarray(X0[y0 == c], float))
            yield label, str(c), A, f"{label}|{c}", "l2", len(A), False

    path = os.path.join(cache, "conv_extra.npz") if cache else None
    if path and os.path.exists(path):
        z = np.load(path)
        for k in z.files:
            label, _, sub = k.partition("||")
            if want(label):
                X = np.asarray(z[k], float)
                yield label, sub, X, f"{label}|{sub}", "l2", len(X), True
    elif not only or any(want(s) for s in ("NOAA tides", "NSRDB solar (GHI)")):
        print("  AVISO: sin conv_extra.npz -> mareas y solar NO medidos.",
              flush=True)


# --------------------------------------------------------------------------- #
# veredicto, tabla, figura

def verdict(cos, arm):
    n_c = cos["crossings"].get(CRITERION["reading"])
    n_l = arm["crossings"].get(CRITERION["reading"])
    pool = arm["n_pool"]
    if n_c is None:
        return {"n95_cos": None, "n95": n_l, "ratio": None, "verdict": "N/A"}
    if n_l is None:
        return {"n95_cos": n_c, "n95": None, "ratio": None,
                "verdict": "FAIL (censurado)"}
    ok_ratio = n_l <= CRITERION["max_ratio_to_cos"] * n_c
    ok_pool = n_l <= CRITERION["max_frac_of_pool"] * pool
    # Diagnostico, NO parte del criterio: si el propio coseno incumple la
    # clausula del pool, un FAIL por esa clausula no lo causa la metrica sino
    # el tamano del dominio. Se reporta al lado; el veredicto no se toca.
    return {"n95_cos": n_c, "n95": n_l, "ratio": n_l / n_c,
            "ok_ratio": bool(ok_ratio), "ok_pool": bool(ok_pool),
            "cos_ok_pool": bool(n_c <= CRITERION["max_frac_of_pool"] * pool),
            "verdict": "PASS" if (ok_ratio and ok_pool) else "FAIL"}


def emit_table(res, path):
    def cell(v):
        if v["n95"] is None:
            return r"--- & ---"
        return f"{v['n95']} & ${v['ratio']:.1f}\\times$" if v["ratio"] else \
            f"{v['n95']} & ---"
    with open(path, "w") as f:
        f.write("% generado por control_sup.py -- no editar a mano\n"
                "\\begin{tabular}{lrrrrrrll}\n\\toprule\n"
                "domain & $n_{\\mathrm{pool}}$ & $n_{95}^{\\cos}$ & "
                "$n_{95}^{L_2}$ & "
                "$n_{95}^{L_\\infty}$ & ratio & "
                "$n_{95}^{L_\\infty,\\mathrm{med3}}$ & verdict & verdict med3 \\\\\n"
                "\\midrule\n")
        for dom, d in res["domains"].items():
            v, vm = d["verdict"]["linf"], d["verdict"].get("linf_med3")
            n_c = v["n95_cos"] if v["n95_cos"] is not None else "---"
            nm3 = (vm["n95"] if vm and vm["n95"] is not None else "---") \
                if vm else "n/a"
            n_2 = d["l2"]["crossings"].get("within_5pct") if "l2" in d else None
            n_2 = "---" if n_2 is None else n_2
            f.write(f"{dom} & {d['cos']['n_pool']} & {n_c} & {n_2} & {cell(v)} & "
                    f"{nm3} & {v['verdict']} & "
                    f"{vm['verdict'] if vm else 'n/a'} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                f"% criterio: {CRITERION['text']}\n")


def figure(res, path):
    import figstyle as fs
    import matplotlib.pyplot as plt
    fs.apply()
    doms = list(res["domains"])
    ncol = 3
    nrow = int(np.ceil(len(doms) / ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=fs.size(1.0, 1.55 * nrow),
                            squeeze=False)
    arms = (("cos", "cosine", fs.BLUE, "-"),
            ("l2", r"$L_2$", fs.GREEN, "-"),
            ("linf", r"$L_\infty$", fs.ORANGE, "-"),
            ("linf_med3", r"$L_\infty$, median-3", fs.VERMILLION, "--"))
    for ax, dom in zip(axs.flat, doms):
        d = res["domains"][dom]
        ax.axhspan(0.95, 1.05, color=fs.GRID, lw=0, zorder=0)
        for key, lab, col, ls in arms:
            if key not in d:
                continue
            a = d[key]
            y = np.array([v[0] for v in a["r_mean"]]) / a["r_true"]
            ax.plot(a["steps"], y, ls, color=col, lw=1.2, label=lab)
        ax.set_xscale("log")
        fs.style(ax)
        fs.ident(ax, dom)
    for ax in axs.flat[len(doms):]:
        ax.axis("off")
    for ax in axs[-1]:
        ax.set_xlabel("$n$")
    for ax in axs[:, 0]:
        ax.set_ylabel(r"$\hat r_n / r_\infty$")
    # Las entradas de la leyenda se juntan de TODOS los paneles: el primero
    # puede ser un dominio de digitos, que no tiene brazo median-3.
    seen = {}
    for ax in axs.flat:
        for h_, l_ in zip(*ax.get_legend_handles_labels()):
            seen.setdefault(l_, h_)
    order = [lab for _, lab, _, _ in arms if lab in seen]
    h, l = [seen[k] for k in order], order
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fs.save(fig, path)
    plt.close(fig)


# --------------------------------------------------------------------------- #

def _aggregate(per):
    keys = list(per)
    return R._conv_aggregate(per, keys) if len(keys) > 1 else per[keys[0]]


def _check_reference(res, ref_path):
    """El brazo coseno debe reproducir convergence.json al bit (mismo codigo,
    mismas semillas). Si no, el control no compara lo que dice comparar."""
    ref = json.load(open(ref_path))
    pool = {**ref.get("domains", {}), **ref.get("digits", {})}
    report = {}
    for dom, d in res["domains"].items():
        if dom not in pool:
            report[dom] = "no esta en la referencia"
            continue
        a = np.array([v[0] for v in d["cos"]["r_mean"]])
        b = np.array([v[0] for v in pool[dom]["r_mean"]])
        m = min(len(a), len(b))
        err = float(np.max(np.abs(a[:m] - b[:m]))) if m else float("nan")
        report[dom] = {"max_abs_diff_r_mean": err, "steps_compared": m,
                       "ok": bool(m and err < 1e-12)}
    return report



def emit(res, out):
    """JSON, tabla, figura y resumen en consola."""
    R.jdump(res, os.path.join(out, "control_sup.json"))
    emit_table(res, os.path.join(out, "table_control_sup.tex"))
    try:
        figure(res, os.path.join(out, "fig_control_sup.png"))
    except Exception as e:                       # la figura no bloquea el numero
        print(f"  figura omitida: {type(e).__name__}: {e}", flush=True)

    print(f"\n  {'dominio':24s} {'pool':>6s} {'n95 cos':>8s} {'n95 Linf':>9s} "
          f"{'ratio':>6s}  {'veredicto':16s} {'cos<=10%pool':>12s} {'n95 L2':>7s}  med3")
    for dom, d in res["domains"].items():
        v, vm = d["verdict"]["linf"], d["verdict"].get("linf_med3")
        rt = f"{v['ratio']:.1f}" if v["ratio"] else "--"
        cp = str(v.get("cos_ok_pool", "--"))
        print(f"  {dom:24s} {d['cos']['n_pool']:>6d} {str(v['n95_cos']):>8s} "
              f"{str(v['n95']):>9s} {rt:>6s}  {v['verdict']:16s} {cp:>12s} "
              f"{str(d['l2']['crossings'].get('within_5pct')) if 'l2' in d else '--':>7s}  "
              f"{(vm['verdict'] + ' (n95=' + str(vm['n95']) + ')') if vm else 'n/a'}")
    if "reference_check" in res:
        bad = {k: v for k, v in res["reference_check"].items()
               if not (isinstance(v, dict) and v["ok"])}
        print("\n  brazo coseno vs referencia: " +
              ("IDENTICO" if not bad else f"DIFIERE en {list(bad)}"))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--cache-from", default=None,
                   help="carpeta de un run de reproduce.py con cache/ "
                        "(mnist.npz, spoken.npz, conv_extra.npz)")
    p.add_argument("--out", default="out_control_sup")
    p.add_argument("--reference", default=None,
                   help="convergence.json contra el que verificar el brazo cos")
    p.add_argument("--only", nargs="+", default=None)
    p.add_argument("--skip-mnist", action="store_true")
    p.add_argument("--no-filter", action="store_true",
                   help="omite el brazo linf_med3")
    p.add_argument("--combine", nargs="+", metavar="JSON", default=None,
                   help="une varios control_sup.json (corridas por lotes) en "
                        "uno solo, con su tabla y su figura; no mide nada")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)

    if a.combine:
        parts = [json.load(open(f)) for f in a.combine]
        if any(p_["criterion"] != CRITERION for p_ in parts):
            raise SystemExit("los lotes no comparten el criterio: no se unen")
        res = {"criterion": CRITERION, "med_width": MED_WIDTH,
               "code": parts[0]["code"], "combined_from": a.combine,
               "combined_by": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
               "domains": {}, "reference_check": {}}
        for p_ in parts:
            if p_["code"] != res["code"]:
                raise SystemExit("los lotes vienen de versiones distintas del "
                                 "script: no se unen")
            res["domains"].update(p_["domains"])
            res["reference_check"].update(p_.get("reference_check", {}))
        if not res["reference_check"]:
            del res["reference_check"]
        emit(res, a.out)
        return

    # El criterio se escribe a disco ANTES de medir nada.
    with open(os.path.join(a.out, "CRITERIO.json"), "w") as f:
        json.dump(CRITERION, f, indent=1)

    t0 = time.time()
    per = {}                  # dominio -> brazo -> subconjunto -> resultado
    for dom, sub, X, tag, quot, n_pool, series in \
            concepts(a.data_root, a.cache_from, a.only, a.skip_mnist):
        arms = ["cos", "l2", "linf"] + (["linf_med3"] if series and not a.no_filter
                                  else [])
        t = time.time()
        r = measure(X, tag, quot, n_pool, arms)
        for arm, v in r.items():
            per.setdefault(dom, {}).setdefault(arm, {})[sub or "_"] = v
        line = "  ".join(f"{k} n95={v['crossings'].get('within_5pct')}"
                         for k, v in r.items())
        print(f"    {tag:28s} {line}   ({time.time() - t:.0f}s)", flush=True)

    res = {"criterion": CRITERION, "med_width": MED_WIDTH,
           "code": {"control_sup.py": hashlib.sha256(
               open(__file__, "rb").read()).hexdigest()},
           "domains": {}}
    for dom, arms in per.items():
        d = {arm: _aggregate(subs) for arm, subs in arms.items()}
        d["verdict"] = {arm: verdict(d["cos"], d[arm])
                        for arm in ("linf", "linf_med3") if arm in d}
        res["domains"][dom] = d
    if a.reference:
        res["reference_check"] = _check_reference(res, a.reference)

    emit(res, a.out)
    print(f"\n  {time.time() - t0:.0f}s, salida en {a.out}")

if __name__ == "__main__":
    main()
