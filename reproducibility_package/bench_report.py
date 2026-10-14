#!/usr/bin/env python3
"""
Report and verdicts for bench_transfer.py, applying the criteria registered in
mssp_paper/notas/06_protocolo_banco.md (v1, approved 14-oct) as code, written
before the full run:

H1 (shape transfers), per fault type, in Ottawa with the qg section:
  1. mean window AUROC of bench_qg over the 5 seeds >= 0.80;
  2. in >= 4 of 5 seeds, the 95% record-bootstrap interval of the paired
     difference AUROC(bench_qg) - AUROC(control) lies above 0 for both
     controls (noise_qg and the simulator OEM in qg).
  H1 holds if it holds for >= 2 of inner race, ball, combined. Speed check:
  the same rule on windows of 15-25 Hz only; if H1 holds on all windows but
  not in that band, the verdict is 'no concluyente'.
H2 (operates), IMS bearing 1 with bench_q at n=99: departure <= 539 + 10 and
  FAR <= 2% in >= 4 of 5 seeds.

  python3 bench_report.py            # write notas/tablas_banco.md
  python3 bench_report.py --print
"""

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "bench"
OTT = HERE / "results" / "ottawa"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_banco.md"

SEEDS = (42, 0, 1, 2, 3)              # bench seeds; Ottawa files seed0..4 hold
OTT_FILE = {42: 0, 0: 1, 1: 2, 2: 3, 3: 4}   # the simulator OEM with these seeds
FAULTS = {"I": "pista interior", "B": "bola", "C": "combinado", "O": "pista exterior"}
H1_FAULTS = ("I", "B", "C")
PROFILES = ("A", "B", "C", "D")
TEST_H = [f"H-{p}-{t}" for p in PROFILES for t in (2, 3)]
FAULT_RECS = {c: [f"{c}-{p}-{t}" for p in PROFILES for t in (1, 2, 3)] for c in FAULTS}
BOOT = 2000
AUROC_MIN = 0.80
SEEDS_MIN = 4
BAND = (15.0, 25.0)
H2_SLACK = 10
H2_FAR = 0.02
PUBLISHED_DEPARTURE = 539


def fmt(x, nd=1):
    return "—" if x is None else f"{x:.{nd}f}".replace(".", ",")


def mr(v, nd=1, pct=False):
    if not v:
        return "—"
    s = "%" if pct else ""
    if len(v) == 1:
        return fmt(v[0], nd) + s
    return f"{fmt(float(np.mean(v)), nd)}{s} [{fmt(min(v), nd)}–{fmt(max(v), nd)}]"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


# ------------------------------------------------------------------ H1

def _windows(get, recs, speed, band):
    parts = []
    for r in recs:
        s = get(r)
        if band is not None:
            v = speed[r][:len(s)]
            s = s[(v >= band[0]) & (v < band[1])]
        parts.append(s)
    return parts


def _auc(h_parts, f_parts):
    h, f = np.concatenate(h_parts), np.concatenate(f_parts)
    return float(roc_auc_score(np.r_[np.zeros(len(h)), np.ones(len(f))],
                               np.r_[h, f]))


def h1_analysis(W, ott, band=None):
    """W: bench window scores; ott: {seed: Ottawa npz dict}."""
    speed = {r: W[f"ottawa_speed/{r}"] for r in TEST_H + sum(FAULT_RECS.values(), [])}
    res = {}
    for c in FAULTS:
        per = []
        for i, seed in enumerate(SEEDS):
            key_b = f"ottawa/bench_qg/{seed}/"
            key_n = f"ottawa/noise_qg/{seed}/"
            if key_b + TEST_H[0] not in W or key_n + TEST_H[0] not in W:
                per.append(None)
                continue
            O = ott.get(OTT_FILE[seed])
            models = {"bench": lambda r: W[key_b + r], "noise": lambda r: W[key_n + r]}
            if O is not None:
                models["sim"] = lambda r, O=O: O[f"ABCD1/oem_qg/{r}"]
                if f"ABCD1/quotg/{TEST_H[0]}" in O:
                    models["local"] = lambda r, O=O: O[f"ABCD1/quotg/{r}"]
                models["kurt"] = lambda r, O=O: O[f"ABCD1/kurt_q/{r}"]
            H = {m: _windows(g, TEST_H, speed, band) for m, g in models.items()}
            F = {m: _windows(g, FAULT_RECS[c], speed, band) for m, g in models.items()}
            auc = {m: _auc(H[m], F[m]) for m in models}
            rng = np.random.default_rng(20261014 + i)
            diffs = {"noise": [], "sim": []}
            for _ in range(BOOT):
                hi = rng.integers(0, len(TEST_H), len(TEST_H))
                fi = rng.integers(0, len(FAULT_RECS[c]), len(FAULT_RECS[c]))
                a = {m: _auc([H[m][j] for j in hi], [F[m][j] for j in fi])
                     for m in ("bench", "noise", "sim") if m in H}
                for m in diffs:
                    if m in a:
                        diffs[m].append(a["bench"] - a[m])
            ci = {m: ([float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
                      if d else None) for m, d in diffs.items()}
            per.append({"seed": seed, "auroc": auc, "ci_diff": ci})
        ok = [p for p in per if p is not None]
        mean_b = float(np.mean([p["auroc"]["bench"] for p in ok])) if ok else None
        wins = sum(1 for p in ok if all(p["ci_diff"][m] is not None and p["ci_diff"][m][0] > 0
                                        for m in ("noise", "sim")))
        seeds_pass = sum(1 for p in ok if p["auroc"]["bench"] >= AUROC_MIN and all(
            p["ci_diff"][m] is not None and p["ci_diff"][m][0] > 0 for m in ("noise", "sim")))
        res[c] = {"per_seed": per, "mean_bench": mean_b, "seeds_beating_controls": wins,
                  "seeds_passing": seeds_pass,
                  "transfers": bool(ok) and mean_b >= AUROC_MIN and wins >= SEEDS_MIN}
    n_ok = sum(res[c]["transfers"] for c in H1_FAULTS)
    return res, n_ok


def h1_verdict(all_w, band_w):
    _, n_all = all_w
    _, n_band = band_w
    if n_all >= 2 and n_band < 2:
        return "no concluyente (se cumple con todas las ventanas pero no en 15–25 Hz)"
    if n_all >= 2:
        return "la forma se transfiere"
    # partial: the rule holds for one fault type, or holds only in part of
    # the seeds (a seed passes with AUROC >= 0.80 and both intervals above 0)
    if n_all == 1 or any(all_w[0][c]["seeds_passing"] > 0 for c in H1_FAULTS):
        return "evidencia parcial"
    return "no se detecta transferencia con este método"


# ------------------------------------------------------------------ H2

def h2_analysis(E):
    i99 = E["ims_ns"].index(99)
    good, rows = 0, []
    for seed in SEEDS:
        run = E["runs"].get(f"bench_q/{seed}", {})
        if not run.get("learned"):
            rows.append((seed, None, None, False))
            continue
        r = run["ims"]["1"][i99]
        far = r["far_k"] / r["far_n"]
        ok = (r["departure"] is not None
              and r["departure"] <= PUBLISHED_DEPARTURE + H2_SLACK and far <= H2_FAR)
        good += ok
        rows.append((seed, r["departure"], far, ok))
    return rows, good >= SEEDS_MIN


# ------------------------------------------------------------------ report

def to_markdown(T, E, W, ott):
    L = ["# Banco de pruebas (CWRU) → IMS y Ottawa", "",
         "*Generado por `reproducibility_package/bench_report.py` desde "
         "`results/bench/` (`bench_transfer.py`). Criterios del protocolo "
         "registrado `06_protocolo_banco.md` v1, aplicados como código. No "
         "editar a mano: `tests/test_generated_notes.py` lo comprueba byte a "
         "byte.*", "",
         "## Banco y entrenamiento (diagnósticos solo del banco)", ""]
    rows = [[r["rpm"], fmt(r["shaft_hz"], 2), fmt(r["seconds"], 1)] for r in T["records"]]
    L.append(table(["carga (rpm)", "eje estimado (Hz)", "segundos"], rows))
    L.append("")
    rows = []
    for d in T["diagnostics"]:
        rows.append([d["variant"], d["seed"], "sí" if d["learned"] else "colapso",
                     fmt(d.get("unexplained_val"), 3), d.get("epochs_run", "—"),
                     fmt(d.get("generalisation_gap"), 2)])
    L.append(table(["variante", "semilla", "aprende", "no reconstruida (validación)",
                    "épocas", "val / train"], rows))

    L += ["", "## H2: opera en IMS (banco en q, n = 99)", ""]
    h2rows, h2 = h2_analysis(E)
    L.append(table(["semilla", "salida bearing 1", "FAR bearing 1", "cumple"],
                   [[s, "—" if d is None else d, "—" if f is None else fmt(100 * f) + "%",
                     "sí" if ok else "no"] for s, d, f, ok in h2rows]))
    L += ["", f"**Veredicto H2:** {'opera' if h2 else 'no cumple el criterio'} "
          f"(criterio: salida ≤ {PUBLISHED_DEPARTURE + H2_SLACK} y FAR ≤ "
          f"{fmt(100 * H2_FAR, 0)}% en al menos {SEEDS_MIN} de 5 semillas).", ""]

    L += ["## IMS: todas las variantes", "",
          "Media [mín–máx] sobre semillas. FAR en los registros "
          f"{E['far_window'][0]}–{E['far_window'][1] - 1}; salida: rango de registros.", ""]
    rows = []
    for v in ("bench_q", "bench_qg", "noise_qg"):
        for i, n in enumerate(E["ims_ns"]):
            row = [v, n]
            for b in ("1", "2", "3", "4"):
                rs = [E["runs"][f"{v}/{s}"]["ims"][b][i] for s in SEEDS
                      if E["runs"].get(f"{v}/{s}", {}).get("learned")]
                far = [100 * r["far_k"] / r["far_n"] for r in rs]
                dep = [r["departure"] for r in rs if r["departure"] is not None]
                row.append(f"{mr(far, pct=True)}; "
                           + (f"{min(dep)}–{max(dep)}" if dep else "sin salida")
                           + (f" ({len(rs) - len(dep)} sin salida)" if dep and len(dep) < len(rs) else ""))
            rows.append(row)
    L.append(table(["variante", "n"] + [f"bearing {b}" for b in "1234"], rows))

    L += ["", "## Ottawa: operación", "",
          "Media [mín–máx] sobre semillas.", ""]
    rows = []
    for v in ("bench_q", "bench_qg", "noise_qg"):
        for sc in ("ABCD1", "A1"):
            rs = [E["runs"][f"{v}/{s}"]["ottawa"][sc] for s in SEEDS
                  if E["runs"].get(f"{v}/{s}", {}).get("learned")]
            rows.append([v, "los cuatro ensayos 1" if sc == "ABCD1" else "A-1",
                         mr([100 * r["far_k"] / r["far_n"] for r in rs], pct=True),
                         mr([r["rec_false"] for r in rs])]
                        + [mr([r["detection"][c]["auroc"] for r in rs], 3) for c in FAULTS])
    L.append(table(["variante", "puesta en marcha", "FAR ventanas",
                    "registros sanos con alarma (de 8)"]
                   + [f"AUROC {n}" for n in FAULTS.values()], rows))

    all_w, band_w = h1_analysis(W, ott), h1_analysis(W, ott, band=BAND)
    L += ["", "## H1: ¿se transfiere la forma? (sección qg, Ottawa)", "",
          f"AUROC ventana a ventana, media [mín–máx] sobre 5 semillas. "
          f"Intervalos por bootstrap de registros ({BOOT} remuestreos). "
          "'Supera controles': semillas en que el intervalo de la diferencia "
          "pareada con C-ruido y con C-simulador queda entero por encima de 0.", ""]
    for label, (res, n_ok) in (("Todas las ventanas", all_w),
                               (f"Solo ventanas de {fmt(BAND[0], 0)}–{fmt(BAND[1], 0)} Hz", band_w)):
        L += [f"### {label}", ""]
        rows = []
        for c, name in FAULTS.items():
            ok = [p for p in res[c]["per_seed"] if p is not None]
            col = lambda m: mr([p["auroc"][m] for p in ok if m in p["auroc"]], 3)
            rows.append([name, col("bench"), col("noise"), col("sim"), col("local"),
                         col("kurt"), f"{res[c]['seeds_beating_controls']}/{len(ok)}",
                         ("sí" if res[c]["transfers"] else "no")
                         + ("" if c in H1_FAULTS else " (no entra en H1)")])
        L.append(table(["fallo", "banco qg", "C-ruido qg", "C-simulador qg",
                        "por máquina qg (techo)", "curtosis", "supera controles",
                        "se transfiere"], rows))
        L.append("")
    L += [f"**Veredicto H1:** {h1_verdict(all_w, band_w)}.", ""]
    return "\n".join(L)


def load(res_dir=RES, ott_dir=OTT):
    T = json.loads((res_dir / "training.json").read_text())
    E = json.loads((res_dir / "evaluation.json").read_text())
    with np.load(res_dir / "window_scores.npz") as z:
        W = {k: z[k] for k in z.files}
    ott = {}
    for i in range(5):
        f = ott_dir / f"scores_seed{i}.npz"
        if f.exists():
            with np.load(f) as z:
                ott[i] = {k: z[k] for k in z.files}
    return T, E, W, ott


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--res", type=Path, default=RES)
    args = ap.parse_args()
    md = to_markdown(*load(args.res))
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
