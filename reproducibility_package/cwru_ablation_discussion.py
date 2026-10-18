#!/usr/bin/env python3
"""
CWRU 5-seed ablation: descriptive tables for DISCUSSION, made after seeing the
results (cwru_ablation_5seeds_report.py is the plain report). Not a verdict.

  python3 cwru_ablation_discussion.py   # -> notas/tablas_cwru_ablacion_discusion.md

Per seed, false alarms are counted in windows (of 47 / 49 / 50 healthy windows
after commissioning). Level comparisons are paired by seed and speed: same
training seed, same commissioning and test windows; the augmentation draws
differ between levels. Exact two-sided sign test on the non-tied pairs.
"""

import argparse
import json
from math import comb
from pathlib import Path

from bench_report import fmt, table

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "cwru_projection" / "quotient_ablation_5seeds.json"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_cwru_ablacion_discusion.md"


def sign_test(pos, neg):
    n, k = pos + neg, min(pos, neg)
    if n == 0:
        return None
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def to_markdown(rep):
    L = ["# CWRU, ablación con 5 semillas: tablas para discutir", "",
         "*Generado por `reproducibility_package/cwru_ablation_discussion.py` desde "
         "`results/cwru_projection/quotient_ablation_5seeds.json`. Hecho después de "
         "ver los resultados; **no es un veredicto**. No editar a mano.*", "",
         "## 1. Falsas alarmas por semilla, en ventanas", ""]
    rows = []
    for rpm, e in rep["speeds"].items():
        for lv in rep["levels"]:
            rs = sorted(e[lv], key=lambda r: r["seed"])
            rows.append([rpm, lv, rs[0]["far_n"]] +
                        [r["far_k"] if r["learned"] else "—" for r in rs])
    seeds = sorted(r["seed"] for r in next(iter(rep["speeds"].values()))[rep["levels"][0]])
    L.append(table(["rpm", "nivel", "sanas"] + [f"semilla {s}" for s in seeds], rows))
    L += ["", "## 2. Comparación pareada con G1 (misma semilla y velocidad)", "",
          "Diferencia en ventanas con falsa alarma (nivel − G1) en los 15 pares "
          "(3 velocidades × 5 semillas). Test de signos exacto, bilateral, sobre "
          "los pares no empatados; sin corregir por comparaciones múltiples.", ""]
    rows = []
    for lv in rep["levels"]:
        if lv == "G1":
            continue
        d = []
        for rpm, e in rep["speeds"].items():
            a = {r["seed"]: r["far_k"] for r in e["G1"] if r["learned"]}
            b = {r["seed"]: r["far_k"] for r in e[lv] if r["learned"]}
            d += [b[s] - a[s] for s in a if s in b]
        pos, neg = sum(x > 0 for x in d), sum(x < 0 for x in d)
        p = sign_test(pos, neg)
        rows.append([f"{lv} − G1", len(d), pos, neg, len(d) - pos - neg,
                     f"{min(d)} a {max(d)}", "—" if p is None else fmt(p, 3)])
    L.append(table(["comparación", "pares", "peor", "mejor", "igual",
                    "rango (ventanas)", "p (signos)"], rows))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    md = to_markdown(json.loads(RES.read_text()))
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
