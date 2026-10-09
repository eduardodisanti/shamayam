#!/usr/bin/env python3
"""
control_tides.py -- mareas con el pool completo (complemento de control_sup.py).

    python control_tides.py --data-root <datasets> --out out_tides \
        --reference-extra <run>/cache/conv_extra.npz

Por que existe
--------------
En control_sup.py las mareas son el unico dominio que NO PASA el criterio fijado
de antemano, y no pasan solo por la clausula del pool: con ~159 ciclos por
estacion, el 10% del pool son 16 realizaciones, n95(L-inf) = 16, y el propio
coseno (n95 = 25) incumple la misma clausula. A ese tamano el criterio casi no
puede discriminar. La pregunta de este script es una sola: el fallo, ¿es del
tamano del dominio o de la metrica?

La etapa de mareas del paper lee 6 archivos mensuales por estacion
(TIDE_MONTHS). En disco hay 24 (2022-01 a 2023-12). Aqui se mide lo mismo con
los 24.

El diseno: cambia UNA variable, el numero de meses
--------------------------------------------------
Mismas nueve estaciones, misma lectura (_tide_series), mismo fiducial
PRE-REGISTRADO (_tide_argmax), mismo cociente (l2), misma medicion
(control_sup.measure: coseno via reproduce._conv_one, L2, L-inf, L-inf con
mediana-3), mismas etiquetas de semilla, mismo criterio (control_sup.CRITERION,
sin cambios). Solo cambia TIDE_MONTHS.

El brazo "6 meses" se recalcula aqui en vez de leerse, y con --reference-extra
se comprueba que las realizaciones coinciden a precision de maquina con las de
conv_extra.npz, es decir, con las que midio el paper (el cache se escribio en
otra maquina; la diferencia maxima medida es ~6e-17 y n95 sale identico). Si no coinciden, el control no compara
lo que dice comparar y el script lo dice.

El NO PASA original NO se reemplaza. Se reporta tal cual en control_sup, y
esto se reporta al lado como la respuesta a "¿es el tamano?".

PREDICCION -- fijada ANTES de correr, 2026-09-23
------------------------------------------------
Con 24 meses el pool crece ~4x (~160 -> ~650 ciclos por estacion).
  P1  n95 no escala con el pool: para coseno y para L-inf, n95(24m) <= 2*n95(6m).
  P2  en consecuencia L-inf PASA el criterio de control_sup con 24 meses.
Si n95 crece en proporcion al pool (~4x o mas), P1 falla: con estos datos la
saturacion de las mareas no se alcanza, y se reporta asi, sin reinterpretar.
"""
from __future__ import annotations

import argparse, hashlib, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import control_sup as C                    # noqa: E402
R = C.R
from run_experiment import l2_normalise    # noqa: E402

PREDICTION = {
    "fixed_on": "2026-09-23",
    "P1": "n95(24m) <= 2*n95(6m), for cos and for linf",
    "P2": "linf PASSES control_sup.CRITERION with 24 months",
    "fail": "n95 growing ~4x or more with the pool -> tides do not saturate "
            "with this data; reported as such",
}
STATIONS = {"Boston": "8443970", "The Battery NY": "8518750",
            "Atlantic City": "8534720", "Key West": "8724580",
            "Galveston": "8771450", "San Diego": "9410170",
            "San Francisco": "9414290", "Anchorage": "9455920",
            "Honolulu": "1612340"}          # identico a stage_tides
PAPER_MONTHS = list(R.TIDE_MONTHS)


def all_months(base):
    """Todos los meses presentes para TODAS las estaciones, ordenados."""
    sets = []
    for sid in STATIONS.values():
        fs = [os.path.basename(f) for f in
              __import__("glob").glob(f"{base}/{sid}_*/{sid}_*.csv")]
        sets.append({f.split("_")[1].split(".")[0] for f in fs})
    return sorted(set.intersection(*sets))


def realisations(base, months):
    """Las realizaciones de cada estacion con los meses dados, construidas con
    el codigo de stage_tides: _tide_series + _tide_argmax + l2."""
    R.TIDE_MONTHS = list(months)
    per = int(R.TIDE_PERIOD_H / 0.1)
    out = {}
    try:
        for nom, sid in STATIONS.items():
            x = R._tide_series(base, sid)
            if x is not None:
                out[nom] = l2_normalise(R._tide_argmax(x, per))
    finally:
        R.TIDE_MONTHS = PAPER_MONTHS
    return out


def measure_arm(label, reals):
    per = {}
    for nom, X in reals.items():
        tag = f"NOAA tides|{nom}"            # la etiqueta de stage_convergence
        t = time.time()
        r = C.measure(X, tag, "l2", len(X), ["cos", "l2", "linf", "linf_med3"])
        for arm, v in r.items():
            per.setdefault(arm, {})[nom] = v
        line = "  ".join(f"{k} n95={v['crossings'].get('within_5pct')}"
                         for k, v in r.items())
        print(f"    {label:10s} {nom:16s} n={len(X):4d}  {line}   "
              f"({time.time() - t:.0f}s)", flush=True)
    d = {arm: C._aggregate(subs) for arm, subs in per.items()}
    d["verdict"] = {arm: C.verdict(d["cos"], d[arm])
                    for arm in ("linf", "linf_med3")}
    d["per_station_n95"] = {
        nom: {arm: per[arm][nom]["crossings"].get("within_5pct")
              for arm in per} for nom in reals}
    d["n_per_station"] = {nom: int(len(X)) for nom, X in reals.items()}
    return d


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data-root", default="data")
    p.add_argument("--out", default="out_control_tides")
    p.add_argument("--reference-extra", default=None,
                   help="conv_extra.npz del run del paper, para verificar que "
                        "el brazo de 6 meses reproduce sus realizaciones")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "PREDICCION.json"), "w") as f:
        json.dump({"prediction": PREDICTION, "criterion": C.CRITERION}, f,
                  indent=1)

    base = R._find_dir(a.data_root, "data/noaa_tides")
    if base is None:
        raise SystemExit("no encuentro data/noaa_tides desde --data-root")
    months = all_months(base)
    print(f"  meses del paper: {PAPER_MONTHS}\n"
          f"  meses en disco (comunes a las 9 estaciones): {len(months)}  "
          f"{months[0]} .. {months[-1]}", flush=True)

    r6, r24 = realisations(base, PAPER_MONTHS), realisations(base, months)

    check = None
    if a.reference_extra:
        z = np.load(a.reference_extra)
        check = {}
        # Precision de maquina, no igualdad de bits: el cache del paper se
        # escribio en otra maquina (otra libm/BLAS), y interp + norma difieren
        # en el ultimo ulp (~3e-17). Lo que se exige es que sean el mismo
        # conjunto de realizaciones; la diferencia maxima queda registrada.
        for nom, X in r6.items():
            k = f"NOAA tides||{nom}"
            ok = k in z.files and z[k].shape == X.shape
            err = float(np.abs(z[k] - X).max()) if ok else None
            check[nom] = {"same_shape": bool(ok), "max_abs_diff": err,
                          "ok": bool(ok and err < 1e-12)}
        good = all(v["ok"] for v in check.values())
        worst = max(v["max_abs_diff"] or 0 for v in check.values())
        print("  6 meses vs realizaciones del paper: " +
              (f"IGUALES a precision de maquina (max |diff| = {worst:.1e})"
               if good else f"DIFIEREN {check}"), flush=True)

    t0 = time.time()
    res = {"prediction": PREDICTION, "criterion": C.CRITERION,
           "months_paper": PAPER_MONTHS, "months_all": months,
           "code": {f: hashlib.sha256(open(os.path.join(HERE, f), "rb")
                                      .read()).hexdigest()
                    for f in ("control_tides.py", "control_sup.py")},
           "realisations_match_paper": check, "domains": {}}
    res["domains"]["NOAA tides (6 months, paper)"] = measure_arm("6 meses", r6)
    res["domains"]["NOAA tides (24 months)"] = measure_arm("24 meses", r24)

    d6 = res["domains"]["NOAA tides (6 months, paper)"]
    d24 = res["domains"]["NOAA tides (24 months)"]
    n = lambda d, arm: d[arm]["crossings"].get("within_5pct")
    p1 = {arm: (n(d24, arm) is not None and n(d6, arm) is not None
                and n(d24, arm) <= 2 * n(d6, arm)) for arm in ("cos", "linf")}
    res["outcome"] = {
        "P1": {"holds": all(p1.values()), "by_arm": p1,
               "n95_6m": {arm: n(d6, arm) for arm in ("cos", "l2", "linf")},
               "n95_24m": {arm: n(d24, arm) for arm in ("cos", "l2", "linf")},
               "pool_6m": d6["cos"]["n_pool"], "pool_24m": d24["cos"]["n_pool"]},
        "P2": {"holds": d24["verdict"]["linf"]["verdict"] == "PASS",
               "verdict_24m": d24["verdict"]["linf"]},
    }
    C.emit(res, a.out)
    o = res["outcome"]
    print(f"\n  P1 (n95 no escala con el pool): "
          f"{'SE SOSTIENE' if o['P1']['holds'] else 'NO'}   {o['P1']['n95_6m']} -> "
          f"{o['P1']['n95_24m']}   pool {o['P1']['pool_6m']} -> {o['P1']['pool_24m']}")
    print(f"  P2 (L-inf pasa con 24 meses):   "
          f"{'SE SOSTIENE' if o['P2']['holds'] else 'NO'}")
    print(f"\n  {time.time() - t0:.0f}s, salida en {a.out}")


if __name__ == "__main__":
    main()
