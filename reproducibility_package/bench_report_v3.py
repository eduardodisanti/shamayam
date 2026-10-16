#!/usr/bin/env python3
"""
Report and verdicts for bench_transfer_v3.py, applying the criteria of
mssp_paper/notas/10_protocolo_banco_v3.md (16-oct) as code, written
and committed before the full run. Same rules as v1 and v2 (bench_report.py), on the
full quotient seen through the squared-envelope spectrum (s):

H1v3, per fault type, Ottawa, variant bench_s:
  1. mean window AUROC over the 5 seeds >= 0.80;
  2. in >= 4 of 5 seeds the 95% record-bootstrap interval of the paired
     difference with noise_s and with sim_s lies above 0.
  Holds if it holds for >= 2 of inner race, ball, combined. Speed check on
  15-25 Hz windows ('no concluyente' if it holds on all windows only).
  Evaluability (fixed before the run): if fewer than 4 of the 5 bench_s
  models learned with an unexplained fraction <= 0.95 on the bench
  validation, H1v3 is 'no evaluable con este autoencoder'.
H2v3: IMS bearing 1, bench_s, n = 99: departure <= 549 and FAR <= 2% in >= 4
  of 5 seeds.

  python3 bench_report_v3.py            # analysis + notas/tablas_banco_v3.md
  python3 bench_report_v3.py --reuse    # render from analysis_v3.json
"""

import argparse
import json
from pathlib import Path

import numpy as np

from bench_report import (AUROC_MIN, BAND, BOOT, FAULTS, H1_FAULTS, H2_FAR,
                          H2_SLACK, PUBLISHED_DEPARTURE, SEEDS_MIN, FAULT_RECS,
                          TEST_H, _auc, _windows, fmt, mr, table)

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "bench_v3"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_banco_v3.md"
SEEDS = (42, 0, 1, 2, 3)
LOCAL_SEEDS = (0, 1, 2, 3, 4)
EVALUABLE_UNEXPLAINED = 0.95


def evaluable(T):
    good = [d for d in T["diagnostics"] if d["model"] == "bench_s" and d["learned"]
            and d.get("unexplained_val", 1.0) <= EVALUABLE_UNEXPLAINED]
    return len(good) >= SEEDS_MIN, len(good)


def h1(W, band=None):
    speed = {r: W[f"ottawa_speed/{r}"] for r in TEST_H + sum(FAULT_RECS.values(), [])}
    res = {}
    for c in FAULTS:
        per = []
        for i, seed in enumerate(SEEDS):
            g = {}
            for name, s in (("bench", f"bench_s/{seed}"), ("noise", f"noise_s/{seed}"),
                            ("sim", f"sim_s/{seed}"),
                            ("local", f"local_s/{LOCAL_SEEDS[i]}"),
                            ("kurt", "kurt_s/-"), ("env", "env_s/-")):
                if f"ottawa/{s}/{TEST_H[0]}" in W:
                    g[name] = (lambda r, s=s: W[f"ottawa/{s}/{r}"])
            H = {m: _windows(f, TEST_H, speed, band) for m, f in g.items()}
            F = {m: _windows(f, FAULT_RECS[c], speed, band) for m, f in g.items()}
            auc = {m: _auc(H[m], F[m]) for m in g}
            if not all(m in g for m in ("bench", "noise", "sim")):
                # references are still reported; no verdict without the bench
                per.append({"seed": seed, "auroc": auc, "ci_diff": None})
                continue
            rng = np.random.default_rng(20261014 + i)
            diffs = {"noise": [], "sim": []}
            for _ in range(BOOT):
                hi = rng.integers(0, len(TEST_H), len(TEST_H))
                fi = rng.integers(0, len(FAULT_RECS[c]), len(FAULT_RECS[c]))
                a = {m: _auc([H[m][j] for j in hi], [F[m][j] for j in fi])
                     for m in ("bench", "noise", "sim")}
                for m in diffs:
                    diffs[m].append(a["bench"] - a[m])
            ci = {m: [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
                  for m, d in diffs.items()}
            per.append({"seed": seed, "auroc": auc, "ci_diff": ci})
        ok = [p for p in per if p is not None and p["ci_diff"] is not None]
        mean_b = float(np.mean([p["auroc"]["bench"] for p in ok])) if ok else None
        wins = sum(1 for p in ok if all(p["ci_diff"][m][0] > 0 for m in ("noise", "sim")))
        passing = sum(1 for p in ok if p["auroc"]["bench"] >= AUROC_MIN
                      and all(p["ci_diff"][m][0] > 0 for m in ("noise", "sim")))
        res[c] = {"per_seed": per, "n_evaluated": len(ok), "mean_bench": mean_b,
                  "seeds_beating_controls": wins, "seeds_passing": passing,
                  "transfers": bool(ok) and mean_b >= AUROC_MIN and wins >= SEEDS_MIN}
    return {"res": res, "n_ok": sum(res[c]["transfers"] for c in H1_FAULTS)}


def analyse(W):
    return {"all": h1(W), "band": h1(W, band=BAND), "xjtu": xjtu_analysis(W)}


def verdict(T, A):
    ev, n = evaluable(T)
    if not ev:
        return f"no evaluable con este autoencoder ({n} de 5 modelos del banco aprenden)"
    n_all, n_band = A["all"]["n_ok"], A["band"]["n_ok"]
    if n_all >= 2 and n_band < 2:
        return "no concluyente (se cumple con todas las ventanas pero no en 15–25 Hz)"
    if n_all >= 2:
        return "la firma se transfiere"
    if n_all == 1 or any(A["all"]["res"][c]["seeds_passing"] > 0 for c in H1_FAULTS):
        return "evidencia parcial"
    return "no se detecta transferencia con este método"


def h2(E):
    i99 = E["ims_ns"].index(99)
    rows, good = [], 0
    for seed in SEEDS:
        run = E["runs"].get(f"bench_s/{seed}", {})
        if not run.get("learned"):
            rows.append([seed, "colapso", "—", "no"])
            continue
        r = run["ims"]["1"][i99]
        far = r["far_k"] / r["far_n"]
        ok = (r["departure"] is not None
              and r["departure"] <= PUBLISHED_DEPARTURE + H2_SLACK and far <= H2_FAR)
        good += ok
        rows.append([seed, "sin salida" if r["departure"] is None else r["departure"],
                     fmt(100 * far) + "%", "sí" if ok else "no"])
    return rows, good >= SEEDS_MIN


def to_markdown(T, E, A):
    L = ["# Protocolo v3: la firma con el cociente completo, vista en el espectro de la envolvente (banco CWRU → IMS, Ottawa y XJTU)", "",
         "*Generado por `reproducibility_package/bench_report_v3.py` desde "
         "`results/bench_v3/` (`bench_transfer_v3.py`). Criterios de "
         "`10_protocolo_banco_v3.md`, como código registrado antes de la "
         "ejecución. No editar a mano: `tests/test_generated_notes.py` lo "
         "comprueba byte a byte.*", "",
         "Sección: preblanqueo cepstral por registro (Hz) → remuestreo angular → "
         "ventanas de 30 vueltas → s = log(SES de Welch / mediana), órdenes 0,1–120.", "",
         "## Entrenamiento (diagnósticos solo del banco, de los controles y del techo)", ""]
    rows = [[d["model"], d["seed"], "sí" if d["learned"] else "colapso",
             fmt(d.get("unexplained_val", d.get("unexplained")), 3),
             d.get("epochs_run", "—"), fmt(d.get("generalisation_gap"), 2)]
            for d in T["diagnostics"]]
    L.append(table(["modelo", "semilla", "aprende", "no reconstruida", "épocas",
                    "val / train"], rows))
    h2rows, h2ok = h2(E)
    L += ["", "## H2v3: IMS, bearing 1, banco s, n = 99", ""]
    L.append(table(["semilla", "salida", "FAR", "cumple"], h2rows))
    L += ["", f"**Veredicto H2v3:** {'opera' if h2ok else 'no cumple el criterio'}.", ""]

    L += ["## IMS: todos los modelos", "",
          "Media [mín–máx] sobre semillas; FAR en los registros 200–499; salida "
          "del bearing 1 (rango).", ""]
    rows = []
    for name in ("bench_s", "noise_s", "sim_s", "kurt_s", "env_s"):
        seeds = ("-",) if name in ("kurt_s", "env_s") else SEEDS
        for i, n in enumerate(E["ims_ns"]):
            rs = [E["runs"][f"{name}/{s}"]["ims"]["1"][i] for s in seeds
                  if E["runs"].get(f"{name}/{s}", {}).get("learned")]
            if not rs:
                rows.append([name, n, "colapso", "—"])
                continue
            dep = [r["departure"] for r in rs if r["departure"] is not None]
            rows.append([name, n, mr([100 * r["far_k"] / r["far_n"] for r in rs], pct=True),
                         (f"{min(dep)}–{max(dep)}" if dep else "sin salida")
                         + (f" ({len(rs) - len(dep)} sin salida)" if dep and len(dep) < len(rs) else "")])
    L.append(table(["modelo", "n", "FAR bearing 1", "salida bearing 1"], rows))

    L += ["", "## Ottawa: operación (los cuatro ensayos 1)", ""]
    rows = []
    for name in ("bench_s", "noise_s", "sim_s", "kurt_s", "env_s"):
        seeds = ("-",) if name in ("kurt_s", "env_s") else SEEDS
        rs = [E["runs"][f"{name}/{s}"]["ottawa"]["ABCD1"] for s in seeds
              if E["runs"].get(f"{name}/{s}", {}).get("learned")]
        if not rs:
            rows.append([name, "colapso"] + ["—"] * 5)
            continue
        rows.append([name, mr([100 * r["far_k"] / r["far_n"] for r in rs], pct=True),
                     mr([r["rec_false"] for r in rs])]
                    + [mr([r["detection"][c]["auroc"] for r in rs], 3) for c in FAULTS])
    L.append(table(["modelo", "FAR ventanas", "registros sanos con alarma"]
                   + [f"AUROC {v}" for v in FAULTS.values()], rows))

    ev, nev = evaluable(T)
    L += ["", "## H1v3: ¿se transfiere la firma? (banco s, Ottawa)", "",
          f"Modelos del banco s que aprenden con no reconstruida ≤ "
          f"{fmt(EVALUABLE_UNEXPLAINED, 2)}: {nev} de 5.", ""]
    for label, key in (("Todas las ventanas", "all"),
                       (f"Solo ventanas de {fmt(BAND[0], 0)}–{fmt(BAND[1], 0)} Hz", "band")):
        res = A[key]["res"]
        L += [f"### {label}", ""]
        rows = []
        for c, name in FAULTS.items():
            ok = [p for p in res[c]["per_seed"] if p is not None]
            col = lambda m: mr([p["auroc"][m] for p in ok if m in p["auroc"]]
                               if m not in ("kurt", "env") else
                               [p["auroc"][m] for p in ok[:1] if m in p["auroc"]], 3)
            rows.append([name, col("bench"), col("noise"), col("sim"), col("local"),
                         col("kurt"), col("env"),
                         f"{res[c]['seeds_beating_controls']}/{res[c]['n_evaluated']}",
                         ("sí" if res[c]["transfers"] else "no")
                         + ("" if c in H1_FAULTS else " (no entra en H1)")])
        L.append(table(["fallo", "banco s", "C-ruido s", "C-simulador s",
                        "por máquina s (techo)", "curtosis (30 vueltas)", "envolvente (30 vueltas)",
                        "supera controles", "se transfiere"], rows))
        L.append("")
    L += [f"**Veredicto H1v3:** {verdict(T, A)}.", ""]
    L += xjtu_section(A)
    return "\n".join(L)


def xjtu_analysis(W):
    """H3v3: the H1 rule of 09_protocolo_xjtu.md, applied to bench_s."""
    import xjtu_report as xr
    out = {"settings": {}}
    for name, seeds in (("bench_s", SEEDS), ("noise_s", SEEDS), ("sim_s", SEEDS),
                        ("kurt_s", ("-",)), ("env_s", ("-",))):
        for seed in seeds:
            if f"xjtu/{name}/{seed}/1_1/H" not in W:
                continue
            get = lambda b, ch, k=f"xjtu/{name}/{seed}": W.get(f"{k}/{b}/{ch}")
            for space, n in xr.SETTINGS:
                out["settings"][f"{name}/{seed}/{space}/{n}"] = xr.summarise(get, space, n)
    out["h3"] = xr.h1(out, arm="bench_s", seeds=SEEDS)
    return out


def xjtu_section(A):
    import xjtu_report as xr
    X = A.get("xjtu")
    if not X or not X["settings"]:
        return []
    L = ["## H3v3 (secundario): XJTU, banco s, H+V, n = 99", ""]
    h = X["h3"]
    L.append(table(["semilla", "salen antes del final", "FAR franja", "cumple"],
                   [[r["seed"], f"{r['detected']}/{r['n_eval']}", xr._pct(r["far"]),
                     "sí" if r["ok_det"] and r["ok_far"] else "no"] for r in h["rows"]]))
    L += ["", f"**Veredicto H3v3:** {h['verdict']}.", "", "### XJTU: todos los modelos", ""]
    rows = []
    for name in ("bench_s", "noise_s", "sim_s", "kurt_s", "env_s"):
        for space, n in xr.SETTINGS:
            G = xr._group(X, name, space, n)
            if G:
                rows.append([name, space, n,
                             xr._range([g["detected"] for g in G]) + f"/{G[0]['n_comm']}",
                             xr._range([g["far"] for g in G], xr._pct)])
    L.append(table(["modelo", "canal", "n", "salen", "FAR franja"], rows))
    L.append("")
    return L


def load(res=RES):
    T = json.loads((res / "training.json").read_text())
    E = json.loads((res / "evaluation.json").read_text())
    with np.load(res / "window_scores.npz") as z:
        W = {k: z[k] for k in z.files}
    return T, E, W


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--res", type=Path, default=RES)
    args = ap.parse_args()
    T, E, W = load(args.res)
    af = args.res / "analysis_v3.json"
    if args.reuse:
        A = json.loads(af.read_text())
    else:
        A = json.loads(json.dumps(analyse(W)))
        af.write_text(json.dumps(A, indent=1) + "\n")
    md = to_markdown(T, E, A)
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
