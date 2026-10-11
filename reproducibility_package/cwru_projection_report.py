#!/usr/bin/env python3
"""
Markdown tables for the CWRU projection experiment, generated from its output.

Reads results.json and scores.npz written by cwru_projection_experiment.py and
prints Markdown. No number in the notes is typed by hand.

Usage: python3 cwru_projection_report.py RESULTS_DIR > tables.md
"""

import json
import sys
from pathlib import Path

import numpy as np

from mssp_repro.calibration import interpolated_quantile

SPEEDS = ("1730", "1750", "1772", "1797")
FAM = ("ball", "inner_race", "outer_race")
FAM_ES = {"ball": "bola", "inner_race": "pista int.", "outer_race": "pista ext."}
CFG_ES = {"A": "A · original (Normal 48k leída a 12k + DE12)",
          "B": "B · corregida (Normal + DE48, proyección angular)",
          "C": "C · control de cadena (Normal + DE12, proyección angular)"}


def f(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, float) and np.isnan(x):
        return "n/d"
    return f"{x:.{nd}f}"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main(d):
    R = json.loads((d / "results.json").read_text())
    S = np.load(d / "scores.npz")
    cfgs = list(R["configs"])
    md = []

    md.append("### Operadores compartidos\n")
    rows = []
    for k, h in R["operators"].items():
        rows.append([k, f"{h['epochs_run']}/{h['budget']}", h["stop_reason"],
                     f(h["best_val_loss"], 5), f(h["tau_mc"], 4)])
    md.append(table(["dominio", "épocas", "parada", "mejor val_loss",
                     "τ_MC (p98)"], rows))

    md.append("\n### Ventanas por configuración\n")
    rows = []
    for c in cfgs:
        for s in SPEEDS:
            w = R["configs"][c][s]["windows"]
            rows.append([c, s, w["healthy"], w["ball"], w["inner_race"],
                         w["outer_race"]])
    md.append(table(["config", "rpm", "sanas", "bola", "pista int.",
                     "pista ext."], rows))

    md.append("\n### AUROC sano vs fallo (sin umbral)\n")
    md.append("Valores por velocidad; 1,00 = separación perfecta. "
              "Los descriptores triviales se puntúan como |valor − mediana sana|.\n")
    for c in cfgs:
        md.append(f"\n**{CFG_ES[c]}**\n")
        rows = []
        for det in ("ae", "rms", "kurtosis", "zcr"):
            row = [det]
            for fam in FAM:
                v = [R["configs"][c][s][det]["auroc"][fam] for s in SPEEDS]
                row.append(" / ".join(f(x, 3) for x in v))
            rows.append(row)
        md.append(table(["detector"] + [f"{FAM_ES[x]} (1730/1750/1772/1797)"
                                        for x in FAM], rows))

    md.append("\n### Operador compartido: calibraciones\n")
    for c in cfgs:
        md.append(f"\n**{CFG_ES[c]}**\n")
        rows = []
        for s in SPEEDS:
            a = R["configs"][c][s]["ae"]
            for arm, lab in (("direct", "transferencia directa"),
                             ("oracle", "oráculo (todo el registro)"),
                             ("online", "online (regla de parada)"),
                             ("certified", "certificado r_(k), n=49")):
                x = a.get(arm)
                if x is None:
                    continue
                if arm == "online" and not x.get("converged"):
                    rows.append([s, lab, "—", "no converge", "—", "—", "—",
                                 "—"])
                    continue
                far = {"direct": x.get("far"), "oracle": x.get("far"),
                       "online": x.get("far_post"),
                       "certified": x.get("far_heldout")}[arm]
                n = {"online": x.get("n"), "certified": x.get("n_cal")}.get(
                    arm, "—")
                held = {"online": x.get("n_post"),
                        "certified": x.get("n_heldout")}.get(arm, "—")
                rows.append([s, lab, f(x["tau"], 4), f(far), n, held] +
                            [f(x[f"{fam}_dr"]) for fam in FAM])
        md.append(table(["rpm", "calibración", "τ", "FAR sanas (%)",
                         "n calib.", "n sanas evaluadas"] +
                        [f"DR {FAM_ES[x]} (%)" for x in FAM], rows))
    md.append("\nFAR: en el oráculo y la transferencia directa, sobre todas "
              "las sanas (incluidas las de calibración); en online, solo "
              "las posteriores a la convergencia; en el certificado, solo "
              "las posteriores a las 49 de calibración.\n")

    md.append("\n### Descriptores triviales con calibración certificada (n=49)\n")
    for c in cfgs:
        md.append(f"\n**{CFG_ES[c]}**\n")
        rows = []
        for det in ("rms", "kurtosis", "zcr"):
            for s in SPEEDS:
                x = R["configs"][c][s][det]["certified"]
                rows.append([det, s, f(x["far_heldout"]), x["n_heldout"]] +
                            [f(x[f"{fam}_dr"]) for fam in FAM])
        md.append(table(["detector", "rpm", "FAR sanas (%)",
                         "n sanas evaluadas"] +
                        [f"DR {FAM_ES[x]} (%)" for x in FAM], rows))

    md.append("\n### Medianas de los descriptores (qué separa)\n")
    for c in cfgs:
        md.append(f"\n**{CFG_ES[c]}**\n")
        rows = []
        for det in ("rms", "kurtosis", "zcr"):
            for s in SPEEDS:
                m = R["configs"][c][s]["feature_medians"][det]
                rows.append([det, s, f(m["healthy"], 3)] +
                            [f(m[fam], 3) for fam in FAM])
        md.append(table(["descriptor", "rpm", "sanas"] +
                        [FAM_ES[x] for x in FAM], rows))

    md.append("\n### Transferencia del radio entre velocidades (solo sanas)\n")
    md.append("Radio oráculo (p98 interpolado) calibrado con las sanas de la "
              "fila y aplicado a las sanas de la columna; celda = % de sanas "
              "fuera del radio. Diagonal ≈ 2% por construcción. Si la "
              "proyección hace invariante la velocidad, las celdas fuera de la "
              "diagonal deberían quedar cerca del 2%.\n")
    for c in cfgs:
        for det in ("ae", "rms"):
            rows = []
            for si in SPEEDS:
                hi = S[f"{c}/{si}/healthy/{det}"]
                if det != "ae":
                    med = np.median(hi)
                    hi_s = np.abs(hi - med)
                else:
                    hi_s = hi
                tau = interpolated_quantile(hi_s)
                row = [si]
                for sj in SPEEDS:
                    hj = S[f"{c}/{sj}/healthy/{det}"]
                    hj_s = np.abs(hj - med) if det != "ae" else hj
                    row.append(f(100 * np.mean(hj_s > tau), 1))
                rows.append(row)
            md.append(f"\n**{CFG_ES[c]} — {det}**\n")
            md.append(table(["calibrada en \\ evaluada en"] + list(SPEEDS),
                            rows))

    md.append("\n### Detección por fichero (radio oráculo, operador compartido)\n")
    for c in cfgs:
        rows = []
        for s in SPEEDS:
            for m in R["configs"][c][s]["meta"]:
                if "family" not in m:
                    continue
                rows.append([s, m["file"], m["windows"], f(m["shaft_hz"], 3),
                             "sí" if m.get("speed_fallback") else "",
                             f(m["ae_oracle_dr"], 1)])
        if rows:
            md.append(f"\n**{CFG_ES[c]}**\n")
            md.append(table(["rpm", "fichero", "ventanas",
                             "velocidad estimada (Hz)",
                             "velocidad de la Normal", "DR (%)"], rows))

    md.append("\n### Velocidad estimada de las Normal\n")
    rows = []
    for c in cfgs:
        for s in SPEEDS:
            for m in R["configs"][c][s]["meta"]:
                if "family" not in m:
                    rows.append([c, s, f(int(s) / 60, 3), f(m["shaft_hz"], 3),
                                 f(100 * (m["shaft_hz"] / (int(s) / 60) - 1),
                                   2)])
    if rows:
        md.append(table(["config", "rpm nominal", "nominal (Hz)",
                         "estimada (Hz)", "desvío (%)"], rows))
    print("\n".join(md))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
