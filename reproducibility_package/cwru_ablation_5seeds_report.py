#!/usr/bin/env python3
"""
CWRU quotient-description ablation, five seeds per level (16-oct extension of
cwru_quotient_ablation.py; the registered 2-seed run is kept as it was).

  python3 cwru_quotient_ablation.py --seeds 0,1,2,3,4 --levels G1,G2,G3,G4 \
      --name quotient_ablation_5seeds.json
  python3 cwru_ablation_5seeds_report.py   # -> notas/tablas_cwru_ablacion_5semillas.md

G0 (projection only, the 49 commissioning windows) is the asset-specific arm
of cwru_limited_data_reference.py, already run with five seeds (reported in
tablas_cwru_proyeccion.md); it is not repeated here.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from bench_report import fmt, mr, table

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "cwru_projection" / "quotient_ablation_5seeds.json"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_cwru_ablacion_5semillas.md"
LEVEL_TEXT = {"G1": "+ fase", "G2": "+ ganancia", "G3": "+ offset",
              "G4": "+ ruido (grupo completo)"}
FAMILIES = ("ball", "inner_race", "outer_race")


def to_markdown(rep):
    L = ["# CWRU: describir mejor el cociente, con cinco semillas por nivel", "",
         "*Generado por `reproducibility_package/cwru_ablation_5seeds_report.py` "
         "desde `results/cwru_projection/quotient_ablation_5seeds.json`. Mismo "
         "protocolo que la ablación registrada (49 ventanas de puesta en marcha, "
         f"{rep['n_aug']} ventanas aumentadas, radio r₍ₖ₎), con las semillas "
         f"{', '.join(map(str, rep['seeds']))}. No editar a mano.*", "",
         "FAR: media [mín–máx] sobre semillas, en las ventanas sanas que siguen a "
         "la puesta en marcha. Detección: % de ventanas de fallo por encima del radio.", ""]
    rows = []
    for rpm, entry in rep["speeds"].items():
        for lv in rep["levels"]:
            rs = [r for r in entry.get(lv, []) if r["learned"]]
            n = len(entry.get(lv, []))
            if not rs:
                rows.append([rpm, f"{lv} {LEVEL_TEXT[lv]}", f"0/{n}", "—", "—", "—", "—"])
                continue
            rows.append([rpm, f"{lv} {LEVEL_TEXT[lv]}", f"{len(rs)}/{n}",
                         mr([100 * r["far_k"] / r["far_n"] for r in rs], pct=True)
                         + f" (n = {rs[0]['far_n']})"]
                        + [mr([r[f"{f}_dr"] for r in rs], pct=True) for f in FAMILIES])
    L.append(table(["rpm", "nivel", "aprenden", "FAR", "bola", "pista interior",
                    "pista exterior"], rows))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--res", type=Path, default=RES)
    args = ap.parse_args()
    md = to_markdown(json.loads(args.res.read_text()))
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
