#!/usr/bin/env python3
"""
Report and verdicts for xjtu_experiment.py, applying the criteria of
mssp_paper/notas/09_protocolo_xjtu.md as code, written and committed before
the full run.

Commissioning: radius r_(k) (alpha = 0.02) on the first n records,
n in {49, 99, 149}, and the 0.98/0.95 tolerance radius with n = 149. Union of
the two channels: each radius at alpha/2, so n >= 99. A bearing is
commissionable for n if its life L >= n + 10. Departure: first persistent
departure (8 of 10) after commissioning; lead time L - d minutes; life
fraction d / L; 'early' if d < L // 2. FAR: declared healthy band, records
[150, L // 2) of bearings 2_1, 2_3, 3_1, 3_2, 3_4, pooled.

H1 (primary): oem_q, union H+V, n = 99, over the 13 commissionable bearings.
  In >= 4 of 5 seeds: departure before the end in >= 10 of 13 AND pooled
  band FAR <= 5%.  opera / opera en parte / no opera.
H2: per-machine models, horizontal channel, n = 49: the IMS reading
  replicates if the median over seeds of the pooled band FAR is > 5% for raw
  and <= 5% for quot.

  python3 xjtu_report.py              # -> results/xjtu/report.json, notas/tablas_xjtu.md
  python3 xjtu_report.py --print
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from bench_report import fmt, table
from mssp_repro.calibration import (certified_order_statistic,
                                    tolerance_order_statistic)
from mssp_repro.dynamics import first_persistent_departure
from mssp_repro.field.xjtu import BEARINGS, CHANNELS, FAULT_ELEMENT, LIFE_RECORDS

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "xjtu"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_xjtu.md"

ALPHA = 0.02
PERSIST = 10
BAND_BEARINGS = ("2_1", "2_3", "3_1", "3_2", "3_4")
BAND_START = 150
FACTORY_SEEDS = (42, 0, 1, 2, 3)
LOCAL_SEEDS = (0, 1, 2, 3, 4)
H1_N, H1_MIN_DET, FAR_MAX, SEEDS_MIN = 99, 10, 0.05, 4
H2_N = 49
FEATURES = ("rms", "kurtosis", "crest", "envelope")
FALLO = {"outer race": "pista exterior", "inner race": "pista interior",
         "cage": "jaula", "inner race and outer race": "pista interior y exterior",
         "inner race, ball, cage and outer race":
             "pista interior, bola, jaula y pista exterior"}
SETTINGS = (("H", 49), ("H", 99), ("H", 149), ("H", "149t"),
            ("V", 49), ("V", 99), ("V", 149), ("V", "149t"),
            ("H+V", 99), ("H+V", 149))


def commissionable(n):
    return [b for b in BEARINGS if LIFE_RECORDS[b] >= n + PERSIST]


def band(b):
    return BAND_START, LIFE_RECORDS[b] // 2


def evaluate_bearing(series, b, n):
    """series: {channel: scores (L,)}; several channels = union (Bonferroni).
    n is an int, or '149t' for the tolerance radius with n = 149."""
    tol = n == "149t"
    m = 149 if tol else int(n)
    L = LIFE_RECORDS[b]
    alpha = ALPHA / len(series)
    flags = np.zeros(L, dtype=bool)
    for s in series.values():
        s = np.asarray(s, dtype=np.float64)[:L]
        tau = tolerance_order_statistic(s[:m]) if tol else \
            certified_order_statistic(s[:m], alpha=alpha)
        if np.isnan(tau):
            raise ValueError(f"radius not certifiable with n={m}, alpha={alpha}")
        flags |= s > tau
    d = first_persistent_departure(flags, q=8, p=10, start=m)
    out = {"departure": d, "lead_min": None if d is None else L - d,
           "life_frac": None if d is None else d / L,
           "early": d is not None and d < L // 2}
    if b in BAND_BEARINGS:
        a, e = band(b)
        out.update(far_k=int(flags[a:e].sum()), far_n=e - a)
    return out


def summarise(get, space, n):
    """get(b, ch) -> scores or None. Evaluates every commissionable bearing."""
    chans = ("H", "V") if space == "H+V" else (space,)
    m = 149 if n == "149t" else n
    per = {}
    for b in commissionable(m):
        series = {ch: get(b, ch) for ch in chans}
        if any(v is None for v in series.values()):
            continue
        per[b] = evaluate_bearing(series, b, n)
    det = sum(r["departure"] is not None for r in per.values())
    fk = sum(r.get("far_k", 0) for r in per.values())
    fn = sum(r.get("far_n", 0) for r in per.values())
    return {"space": space, "n": n, "bearings": per, "n_eval": len(per),
            "n_comm": len(commissionable(m)), "detected": det,
            "early": sum(r["early"] for r in per.values()),
            "far_k": fk, "far_n": fn, "far": fk / fn if fn else None,
            "band_complete": all(b in per for b in BAND_BEARINGS)}


# ------------------------------------------------------------------ loading

def load(res=RES):
    D = {}
    p = res / "classical.npz"
    if p.exists():
        with np.load(p) as z:
            D["classical"] = {k: z[k] for k in z.files}
    p = res / "factory_scores.npz"
    if p.exists():
        with np.load(p) as z:
            D["factory"] = {k: z[k] for k in z.files}
        D["factory_training"] = json.loads((res / "factory_training.json").read_text())
    D["local"] = {}
    for seed in LOCAL_SEEDS:
        p = res / "local" / f"seed{seed}.json"
        if p.exists():
            D["local"][seed] = json.loads(p.read_text())["runs"]
    return D


def arms(D):
    """[(arm, seed, get, local_n)] for every score source present."""
    out = []
    F = D.get("factory", {})
    for name in ("oem_q", "bench_q"):
        for seed in FACTORY_SEEDS:
            if f"{name}/{seed}/1_1/H" in F:
                out.append((name, seed, lambda b, ch, k=f"{name}/{seed}":
                            F.get(f"{k}/{b}/{ch}"), None))
    C = D.get("classical", {})
    for feat in FEATURES:
        if f"1_1/H/{feat}" in C:
            out.append((feat, "-", lambda b, ch, f=feat: C.get(f"{b}/{ch}/{f}"), None))
    for seed, runs in D.get("local", {}).items():
        for arm in ("raw", "quot"):
            for n in (49, 99):
                def get(b, ch, runs=runs, arm=arm, n=n):
                    r = runs.get(f"{b}/{n}/{arm}")
                    if ch != "H" or r is None or not r["learned"]:
                        return None
                    return np.asarray(r["scores"])
                out.append((arm, seed, get, n))
    return out


def analyse(D):
    A = {"settings": {}}
    for arm, seed, get, local_n in arms(D):
        for space, n in SETTINGS:
            if local_n is not None and (space != "H" or n != local_n):
                continue
            A["settings"][f"{arm}/{seed}/{space}/{n}"] = summarise(get, space, n)
    C = D.get("classical", {})
    diag = {}
    for b in BAND_BEARINGS:
        a, e = band(b)
        for ch in CHANNELS:
            s = C.get(f"{b}/{ch}/rms")
            if s is not None:
                rho, p = spearmanr(np.arange(e - a), s[a:e])
                diag[f"{b}/{ch}"] = {"rho": float(rho), "p": float(p)}
    A["band_rms_trend"] = diag
    A["h1"] = h1(A)
    A["h2"] = h2(A)
    return A


def h1(A, arm="oem_q", seeds=FACTORY_SEEDS):
    rows, both, only_det, only_far = [], 0, 0, 0
    for seed in seeds:
        r = A["settings"].get(f"{arm}/{seed}/H+V/{H1_N}")
        if r is None:
            continue
        ok_det = r["detected"] >= H1_MIN_DET
        ok_far = r["far"] is not None and r["band_complete"] and r["far"] <= FAR_MAX
        both += ok_det and ok_far
        only_det += ok_det
        only_far += ok_far
        rows.append({"seed": seed, "detected": r["detected"], "n_eval": r["n_eval"],
                     "far": r["far"], "ok_det": ok_det, "ok_far": ok_far})
    if not rows:
        verdict = "sin datos"
    elif both >= SEEDS_MIN:
        verdict = "opera"
    elif only_det >= SEEDS_MIN or only_far >= SEEDS_MIN or both >= 2:
        verdict = "opera en parte"
    else:
        verdict = "no opera"
    return {"arm": arm, "rows": rows, "seeds_both": both, "seeds_det": only_det,
            "seeds_far": only_far, "verdict": verdict}


def h2(A, n=H2_N):
    med = {}
    for arm in ("raw", "quot"):
        v = [A["settings"][k]["far"] for k in A["settings"]
             if k.startswith(f"{arm}/") and k.endswith(f"/H/{n}")
             and A["settings"][k]["far"] is not None]
        med[arm] = float(np.median(v)) if v else None
    if med["raw"] is None or med["quot"] is None:
        verdict = "sin datos"
    elif med["raw"] > FAR_MAX and med["quot"] <= FAR_MAX:
        verdict = "se replica la lectura de IMS"
    else:
        verdict = "no se replica"
    return {"n": n, "median_far": med, "verdict": verdict}


# ------------------------------------------------------------------ markdown

def _pct(x):
    return "—" if x is None else fmt(100 * x) + "%"


def _range(v, f=lambda x: str(x)):
    v = [x for x in v if x is not None]
    if not v:
        return "—"
    lo, hi = min(v), max(v)
    return f(lo) if lo == hi else f"{f(lo)}–{f(hi)}"


def _partial(G):
    m = min(g["n_eval"] for g in G)
    return "" if m == G[0]["n_comm"] else f" ({m} evaluados)"


def _group(A, arm, space, n):
    return [A["settings"][k] for k in sorted(A["settings"])
            if k.split("/")[0] == arm and k.split("/", 2)[2] == f"{space}/{n}"]


def to_markdown(A, D):
    L = ["# XJTU-SY: quince fallos reales hasta el final de vida", "",
         "*Generado por `reproducibility_package/xjtu_report.py` desde "
         "`results/xjtu/` (`xjtu_experiment.py`). Criterios de "
         "`09_protocolo_xjtu.md`, como código registrado antes de la "
         "ejecución. No editar a mano: lo comprueba un test byte a byte.*", "",
         "Sección q: velocidad nominal, 400 muestras/vuelta, ventanas de 3 "
         "vueltas; un valor por registro (media de las ventanas). Radio r₍ₖ₎ con "
         "α = 0,02 (α/2 por canal en H+V); 149t = tolerancia 0,98/0,95 con n = 149. "
         "FAR en la franja sana declarada: registros [150, ⌊L/2⌋) de 2_1, 2_3, "
         "3_1, 3_2 y 3_4, agregada.", ""]
    h = A["h1"]
    L += ["## H1 (principal): oem_q, H+V, n = 99", ""]
    L.append(table(["semilla", "salen antes del final", "FAR franja", "cumple"],
                   [[r["seed"], f"{r['detected']}/{r['n_eval']}", _pct(r["far"]),
                     "sí" if r["ok_det"] and r["ok_far"] else "no"] for r in h["rows"]]))
    L += ["", f"**Veredicto H1:** {h['verdict']}.", ""]

    L += ["## Por rodamiento: oem_q, H+V, n = 99 (rango sobre semillas)", ""]
    rows = []
    G = _group(A, "oem_q", "H+V", 99)
    for b in BEARINGS:
        rs = [g["bearings"][b] for g in G if b in g["bearings"]]
        if not rs:
            why = "no comisionable" if b not in commissionable(99) else "sin datos"
            rows.append([b, FALLO[FAULT_ELEMENT[b]], LIFE_RECORDS[b], why,
                         "—", "—", "—"])
            continue
        miss = sum(r["departure"] is None for r in rs)
        rows.append([b, FALLO[FAULT_ELEMENT[b]], LIFE_RECORDS[b],
                     _range([r["departure"] for r in rs])
                     + (f" ({miss} sin salida)" if miss else ""),
                     _range([r["lead_min"] for r in rs]),
                     _range([r["life_frac"] for r in rs], lambda x: fmt(x, 2)),
                     f"{sum(r['early'] for r in rs)}/{len(rs)}"])
    L.append(table(["rodamiento", "fallo", "vida (min)", "salida (registro)",
                    "antelación (min)", "fracción de vida", "salida temprana"], rows))

    L += ["", "## Menú de puesta en marcha: todos los modelos sin entrenamiento local", "",
          "Salen = rodamientos comisionables con salida antes del final; rango "
          "sobre semillas cuando hay varias.", ""]
    rows = []
    for arm in ("oem_q", "bench_q") + FEATURES:
        for space, n in SETTINGS:
            G = _group(A, arm, space, n)
            if not G:
                continue
            rows.append([arm, space, n, _range([g["detected"] for g in G])
                         + f"/{G[0]['n_comm']}" + _partial(G),
                         _range([g["far"] for g in G], _pct),
                         _range([g["early"] for g in G])])
    L.append(table(["modelo", "canal", "n", "salen", "FAR franja",
                    "salidas tempranas"], rows))

    L += ["", "## H2: por máquina, canal horizontal (crudo frente a cociente)", ""]
    rows = []
    for arm in ("raw", "quot", "oem_q"):
        for n in (49, 99):
            G = _group(A, arm, "H", n)
            if not G:
                continue
            fars = [g["far"] for g in G if g["far"] is not None]
            rows.append([arm, n, len(G),
                         _pct(float(np.median(fars))) if fars else "—",
                         _range(fars, _pct), _range([g["detected"] for g in G])
                         + f"/{G[0]['n_comm']}"])
    L.append(table(["modelo", "n", "semillas", "FAR franja (mediana)",
                    "FAR franja (rango)", "salen"], rows))
    h2r = A["h2"]
    L += ["", f"**Veredicto H2** (n = {h2r['n']}; mediana raw "
          f"{_pct(h2r['median_far']['raw'])}, quot {_pct(h2r['median_far']['quot'])}):"
          f" {h2r['verdict']}.", ""]

    L += ["## Diagnóstico de la franja sana (sin efecto sobre los veredictos)", "",
          "Tendencia de Spearman del RMS dentro de la franja.", ""]
    L.append(table(["rodamiento", "canal", "registros", "ρ", "p"],
                   [[k.split("/")[0], k.split("/")[1],
                     f"{band(k.split('/')[0])[0]}–{band(k.split('/')[0])[1] - 1}",
                     fmt(v["rho"], 2), f"{v['p']:.1e}"]
                    for k, v in A["band_rms_trend"].items()]))

    T = D.get("factory_training")
    if T:
        L += ["", "## Entrenamiento de los modelos de fábrica", ""]
        L.append(table(["modelo", "semilla", "aprende", "épocas", "no reconstruida"],
                       [[d["model"], d["seed"], "sí" if d["learned"] else "colapso",
                         d.get("epochs_run", "—"), fmt(d.get("unexplained_val"), 3)]
                        for d in T["diagnostics"]]))
    if D.get("local"):
        L += ["", "## Entrenamiento por máquina", ""]
        rows = []
        for seed, runs in sorted(D["local"].items()):
            for arm in ("raw", "quot"):
                rs = [r for k, r in runs.items() if k.endswith(f"/{arm}")]
                rows.append([seed, arm, len(rs), sum(r["learned"] for r in rs),
                             _range([r.get("unexplained") for r in rs if r["learned"]],
                                    lambda x: fmt(x, 3))])
        L.append(table(["semilla", "brazo", "modelos", "aprenden", "no reconstruida"],
                       rows))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--res", type=Path, default=RES)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    D = load(args.res)
    A = json.loads(json.dumps(analyse(D)))
    (args.res / "report.json").write_text(json.dumps(A, indent=1) + "\n")
    md = to_markdown(A, D)
    if args.print:
        print(md)
    else:
        args.out.write_text(md)
        print("wrote", args.out)


if __name__ == "__main__":
    main()
