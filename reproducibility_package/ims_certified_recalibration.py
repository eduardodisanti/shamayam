#!/usr/bin/env python3
"""
NASA IMS: re-commissioning from the committed residual cache with certified
radii.

The published Table 10 commissioned each bearing with the interpolated
quantile and an adaptive stopping rule (the A1 configuration), which does not
carry the guarantee of the coverage proposition. This script keeps the frozen
shared operator, the residuals and the 8-of-10 persistence rule exactly as
published, and replaces only the radius:

  published     interpolated quantile, adaptive stopping (reproduces Table 10)
  r_(k), n=49   coverage >= 0.98 in expectation, the commissioning floor
  r_(k), n=99   first length with an interior order statistic
  r_(k), n=149  coverage >= 0.98 in expectation, larger sample
  tol,   n=149  coverage >= 0.98 with probability >= 0.95 (Wilks)

Only bearing 1 fails in IMS Experiment 2 (outer race). Bearings 2-4 are
reported as departures from their nominal neighbourhood, not as failures.

Everything is pure numpy on a 31 kB array, so the run is deterministic and
the Markdown it emits is checked byte for byte by tests/test_generated_notes.py.

Usage:
  python3 ims_certified_recalibration.py                      # write files
  python3 ims_certified_recalibration.py --print              # stdout only
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from mssp_repro.calibration import (certified_order_statistic,
                                    tolerance_order_statistic, tolerance_rank)
from mssp_repro.dynamics import first_persistent_departure
from mssp_repro.field.ims import IMS_RECORDING_INTERVAL_HOURS
from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                        describe_trajectory,
                                        flag_inactive_recordings, load_cache)

HERE = Path(__file__).resolve().parent
CACHE = HERE / "results" / "field_residuals_ims.npz"
OUT_JSON = HERE / "results" / "ims_certified" / "results.json"
OUT_MD = HERE.parent / "mssp_paper" / "notas" / "tablas_ims_certificado.md"

Q, P = 8, 10                              # persistence rule, as published
FAILED_BEARING = 1                        # outer race, IMS Experiment 2
ARMS = (("r_(k), n=49", "certified", 49),
        ("r_(k), n=99", "certified", 99),
        ("r_(k), n=149", "certified", 149),
        ("tolerancia 0,98/0,95, n=149", "tolerance", 149))


def active_length(s):
    """Recordings before the trailing ones taken with the rig stopped."""
    inactive = flag_inactive_recordings(s, warmup=FIELD_WARMUP_RECORDINGS)
    n = s.size
    while n > 0 and inactive[n - 1]:
        n -= 1
    return n


def evaluate_arm(s, kind, n):
    cal = s[:n]
    tau = (certified_order_statistic(cal) if kind == "certified"
           else tolerance_order_statistic(cal))
    n_act = active_length(s)
    act = s[:n_act]
    d = first_persistent_departure(act > tau, q=Q, p=P, start=n)
    healthy = s[n:FIELD_WARMUP_RECORDINGS]
    k = int(np.sum(healthy > tau))
    out = {"n": n, "tau": float(tau),
           "rank": (int(np.ceil(0.98 * (n + 1))) if kind == "certified"
                    else tolerance_rank(n)),
           "far_k": k, "far_n": int(healthy.size),
           "far": float(100 * k / healthy.size) if healthy.size else None,
           "departure": d,
           "lead_hours": (float((n_act - d) * IMS_RECORDING_INTERVAL_HOURS)
                          if d is not None else None),
           "exceedance_post": (float(100 * np.mean(act[d:] > tau))
                               if d is not None else None)}
    return out


def run():
    c = load_cache(CACHE)
    S = np.asarray(c["scores"], dtype=float)
    res = {"cache": CACHE.name, "persistence": [Q, P],
           "failed_bearing": FAILED_BEARING, "bearings": {}}
    for i, s in enumerate(S, start=1):
        pub = describe_trajectory(s)
        b = {"published": {
            "n": pub["n"], "tau": pub["tau"], "departure": pub["departure"],
            "lead_hours": pub["lead_hours"],
            "exceedance_post": 100 * pub["exceedance_post"],
            "far": 100 * pub["far_commissioned"]},
            "n_active": active_length(s)}
        for label, kind, n in ARMS:
            b[label] = evaluate_arm(s, kind, n)
        rho, p = spearmanr(np.arange(149), s[:149])
        b["spearman_first149"] = {"rho": float(rho), "p": float(p)}
        res["bearings"][str(i)] = b
    return res


def fmt(x, nd=2):
    if x is None:
        return "—"
    return f"{x:.{nd}f}".replace(".", ",")


def to_markdown(res):
    L = ["# IMS: recalibración certificada desde la caché de residuos", "",
         "*Generado por `reproducibility_package/ims_certified_recalibration.py` "
         "a partir de `results/field_residuals_ims.npz`. No editar a mano: "
         "`tests/test_generated_notes.py` comprueba que coincide byte a byte.*",
         "",
         f"Operador compartido, residuos y regla de persistencia "
         f"({Q} de {P}) idénticos a los publicados; solo cambia el radio. "
         "La FAR se mide en los registros sanos entre el final de la "
         f"calibración y el registro {FIELD_WARMUP_RECORDINGS}. "
         "Solo el bearing 1 falla (pista exterior); en 2–4 la salida es de "
         "su vecindad nominal, no un fallo documentado.", ""]
    head = ("| bearing | radio | n calib. | rango k | τ | FAR sanas (%) | "
            "salida (registro) | antelación (h) | excedencia tras salida (%) |")
    L += [head, "|" + "---|" * 9]
    for b, r in res["bearings"].items():
        tag = f"{b} (fallo)" if int(b) == res["failed_bearing"] else b
        p = r["published"]
        L.append(f"| {tag} | publicado (cuantil interpolado, parada adaptativa) "
                 f"| {p['n']} | — | {fmt(p['tau'], 6)} | {fmt(p['far'])} | "
                 f"{p['departure']} | {fmt(p['lead_hours'])} | "
                 f"{fmt(p['exceedance_post'])} |")
        for label, _, _ in ARMS:
            a = r[label]
            far = (f"{fmt(a['far'])} ({a['far_k']}/{a['far_n']})"
                   if a["far_n"] else "—")
            L.append(f"| {tag} | {label} | {a['n']} | {a['rank']} | "
                     f"{fmt(a['tau'], 6)} | {far} | {a['departure'] if a['departure'] is not None else '—'} | "
                     f"{fmt(a['lead_hours'])} | {fmt(a['exceedance_post'])} |")
    L += ["", "## Intercambiabilidad en la calibración", "",
          "Spearman entre el índice temporal y el residuo en los 149 primeros "
          "registros (prueba de deriva cronológica, en lugar de la ablación "
          "por permutación).", "",
          "| bearing | ρ | p |", "|---|---|---|"]
    for b, r in res["bearings"].items():
        sp = r["spearman_first149"]
        L.append(f"| {b} | {fmt(sp['rho'], 3)} | {sp['p']:.2g} |".replace(".", ","))
    L += ["", f"Registros activos por bearing (sin los finales con el banco "
          f"parado): " + ", ".join(f"{b}: {r['n_active']}"
                                   for b, r in res["bearings"].items()) + ".",
          f"Intervalo entre registros: {IMS_RECORDING_INTERVAL_HOURS * 60:.0f} min.",
          ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    res = run()
    md = to_markdown(res)
    if args.print:
        print(md)
        return
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(res, indent=1) + "\n")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md)
    print("wrote", OUT_JSON, "and", OUT_MD)


if __name__ == "__main__":
    main()
