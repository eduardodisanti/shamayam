#!/usr/bin/env python3
"""
Bench v3: descriptive table for DISCUSSION, made after seeing the results of
10_protocolo_banco_v3.md. Not a verdict; the registered ones are in
tablas_banco_v3.md and do not change.

What does the noise control (noise_s) compute? Its autoencoder reconstructs
nothing (unexplained fraction 1.000), so its score is close to the distance of
the standardised representation from the white-noise mean. This table measures
how that score ranks windows compared with the classical references computed on
the same 30-revolution windows (Spearman rank correlation, all windows pooled).

  python3 bench_v3_discussion.py      # -> notas/tablas_banco_v3_discusion.md
"""

import argparse
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from bench_report import fmt, table

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "bench_v3"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_banco_v3_discusion.md"
SEEDS = (42, 0, 1, 2, 3)


def pooled(W, prefix, model, seed):
    keys = sorted(k for k in W if k.startswith(f"{prefix}/{model}/{seed}/"))
    return keys, (np.concatenate([np.ravel(W[k]) for k in keys]) if keys else None)


def to_markdown(W):
    L = ["# Banco v3: qué mide el control de ruido (tabla para discutir)", "",
         "*Generado por `reproducibility_package/bench_v3_discussion.py` desde "
         "`results/bench_v3/window_scores.npz`. Hecho después de ver los "
         "resultados; **no es un veredicto** y no cambia los de "
         "[`tablas_banco_v3.md`](tablas_banco_v3.md). No editar a mano.*", "",
         "Correlación de Spearman entre la puntuación de cada modelo y las "
         "referencias clásicas en las mismas ventanas de 30 vueltas, juntando "
         "todos los registros del destino. Rango sobre semillas.", ""]
    rows = []
    for dest, label in (("ottawa", "Ottawa (ventanas)"), ("ims", "IMS (registros)"),
                        ("xjtu", "XJTU (registros, H y V)")):
        for model in ("noise_s", "sim_s"):
            r_k, r_e = [], []
            for seed in SEEDS:
                keys, a = pooled(W, dest, model, seed)
                if a is None:
                    continue
                k = np.concatenate([np.ravel(W[x.replace(f"/{model}/{seed}/", "/kurt_s/-/")])
                                    for x in keys])
                e = np.concatenate([np.ravel(W[x.replace(f"/{model}/{seed}/", "/env_s/-/")])
                                    for x in keys])
                r_k.append(spearmanr(a, k)[0])
                r_e.append(spearmanr(a, e)[0])
            if r_k:
                f = lambda v: fmt(min(v), 2) if fmt(min(v), 2) == fmt(max(v), 2) \
                    else f"{fmt(min(v), 2)}–{fmt(max(v), 2)}"
                rows.append([label, model, f(r_k), f(r_e)])
    L.append(table(["destino", "modelo", "ρ con curtosis", "ρ con envolvente"], rows))
    L.append("")
    return "\n".join(L)


def load(res=RES):
    with np.load(res / "window_scores.npz") as z:
        return {k: z[k] for k in z.files}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    md = to_markdown(load())
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
