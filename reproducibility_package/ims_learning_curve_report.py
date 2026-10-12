#!/usr/bin/env python3
"""
Markdown tables for ims_quotient_learning_curve.py, generated from its JSON.

Usage:
  python3 ims_learning_curve_report.py            # write the notes table
  python3 ims_learning_curve_report.py --print    # stdout only
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "ims_quotient" / "learning_curve.json"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_ims_cociente.md"

ARMS = (("raw", "por máquina, señal cruda"),
        ("quot", "por máquina, en el cociente"),
        ("oem_q", "OEM en el cociente (simulación)"),
        ("pub", "OEM publicado (tiempo)"))


def fmt(x, nd=1):
    return "—" if x is None else f"{x:.{nd}f}".replace(".", ",")


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def to_markdown(R):
    bs = list(R["bearings"])
    a, b = R["far_window"]
    hours = R["ns"]
    L = ["# IMS: curva de aprendizaje, por máquina frente a OEM en el cociente",
         "",
         "*Generado por `reproducibility_package/ims_learning_curve_report.py` "
         "desde `results/ims_quotient/learning_curve.json` "
         "(`ims_quotient_learning_curve.py`). No editar a mano: "
         "`tests/test_generated_notes.py` lo comprueba byte a byte.*", "",
         f"Puesta en marcha con los n primeros registros (10 min entre "
         f"registros); radio r_(k) sobre esos n. FAR sobre los registros "
         f"{a}–{b - 1} ({b - a} registros, ~{(b - a) / 6:.0f} h de vida sana). "
         f"Salida: primera persistente (8 de 10) tras la puesta en marcha. "
         f"Solo el bearing 1 falla. Velocidad nominal "
         f"({fmt(R['shaft_hz'] * 60, 0)} rpm). Una semilla por modelo local "
         f"({R['seed']}); por máquina en el cociente con {R['n_aug']} "
         f"ventanas aumentadas.", ""]
    h = R["oem_q_training"]
    L += [f"OEM en el cociente: {h['epochs_run']}/{h['budget']} épocas, "
          f"mejor val_loss {fmt(h['best_val_loss'], 5)}.", ""]

    L += ["## Falsas alarmas en la vida sana", ""]
    rows = []
    for key, name in ARMS:
        for i, n in enumerate(R["ns"]):
            row = [name, f"{n} (~{fmt(n / 6, 1)} h)"]
            for bb in bs:
                r = R["bearings"][bb][key][i]
                if key in ("raw", "quot") and not r.get("learned", True):
                    row.append("no aprende")
                else:
                    row.append(f"{fmt(100 * r['far_k'] / r['far_n'])}% "
                               f"({r['far_k']}/{r['far_n']})")
            rows.append(row)
    L.append(table(["modelo", "n puesta en marcha"] +
                   [f"bearing {bb}" + (" (fallo)" if bb == "1" else "")
                    for bb in bs], rows))

    L += ["", "## Salida de lo normal (registro y antelación al final)", ""]
    rows = []
    for key, name in ARMS:
        for i, n in enumerate(R["ns"]):
            row = [name, str(n)]
            for bb in bs:
                r = R["bearings"][bb][key][i]
                if key in ("raw", "quot") and not r.get("learned", True):
                    row.append("no aprende")
                elif r["departure"] is None:
                    row.append("sin salida")
                else:
                    row.append(f"{r['departure']} ({fmt(r['lead_hours'], 2)} h)")
            rows.append(row)
    L.append(table(["modelo", "n"] + [f"bearing {bb}" for bb in bs], rows))

    L += ["", "## Modelos por máquina: varianza no reconstruida en "
          "entrenamiento", "",
          "La vibración de IMS es casi ruido de banda ancha: un autoencoder "
          "por máquina reconstruye solo parte de la varianza. Se rechaza solo "
          "el colapso (> 0,98, equivalente a predecir una constante).", ""]
    rows = []
    for key, name in ARMS[:2]:
        for i, n in enumerate(R["ns"]):
            rows.append([name, str(n)] + [
                fmt(R["bearings"][bb][key][i].get("unexplained"), 2)
                if R["bearings"][bb][key][i].get("learned") else "—"
                for bb in bs])
    L.append(table(["modelo", "n"] + [f"bearing {bb}" for bb in bs], rows))
    L += ["", "## Generalización de los modelos por máquina "
          "(val_loss / train_loss)", ""]
    rows = []
    for key, name in ARMS[:2]:
        for i, n in enumerate(R["ns"]):
            rows.append([name, str(n)] + [
                fmt(R["bearings"][bb][key][i].get("gap"), 2)
                if R["bearings"][bb][key][i].get("learned") else "—"
                for bb in bs])
    L.append(table(["modelo", "n"] + [f"bearing {bb}" for bb in bs], rows))
    L.append("")
    return "\n".join(L)


def seeds_markdown(R, S):
    """Variability over seeds: seed-0/42 run (R) plus the seed study (S)."""
    import numpy as np
    a, b = R["far_window"]
    L = ["", "## Variabilidad entre semillas", "",
         "Misma configuración; cada modelo se reentrena con cada semilla. "
         "Por máquina: semillas 0 (tabla anterior) y "
         f"{', '.join(S['raw'])}, bearings "
         f"{', '.join(next(iter(S['raw'].values())))}. OEM en el cociente: "
         f"semillas 42 (tabla anterior) y {', '.join(S['oem_q'])}, los "
         "cuatro bearings. Media y rango de la FAR en los registros "
         f"{a}–{b - 1}; entre paréntesis, entrenamientos que colapsaron.", ""]

    def runs(arm, bb):
        out = [R["bearings"][bb][arm]]
        src = S[arm]
        for sd in src:
            rows = (src[sd]["bearings"].get(bb) if arm == "oem_q"
                    else src[sd].get(bb))
            if rows is not None:
                out.append(rows)
        return out

    bs = [bb for bb in R["bearings"]]
    rows = []
    for key, name in ARMS[:3]:
        for i, n in enumerate(R["ns"]):
            row = [name, str(n)]
            for bb in bs:
                rr = runs(key, bb)
                if key != "oem_q" and len(rr) == 1:
                    row.append("—")
                    continue
                vals = [100 * x[i]["far_k"] / x[i]["far_n"] for x in rr
                        if x[i].get("learned", True)]
                col = len(rr) - len(vals)
                if not vals:
                    row.append(f"colapso ({col})")
                    continue
                txt = (f"{fmt(float(np.mean(vals)))}% "
                       f"[{fmt(min(vals))}–{fmt(max(vals))}]")
                row.append(txt + (f" ({col})" if col else ""))
            rows.append(row)
    L.append(table(["modelo", "n"] + [f"bearing {bb}" for bb in bs], rows))

    L += ["", "### Salida del bearing 1 (fallo) por semilla", ""]
    rows = []
    for key, name in ARMS[:3]:
        for i, n in enumerate(R["ns"]):
            deps = [x[i]["departure"] for x in runs(key, "1")
                    if x[i].get("learned", True)]
            deps = [d for d in deps if d is not None]
            rows.append([name, str(n),
                         f"{min(deps)}–{max(deps)}" if deps else "—",
                         str(len(deps))])
    L.append(table(["modelo", "n", "registro de salida (rango)",
                    "semillas"], rows))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    md = to_markdown(json.loads(RES.read_text()))
    seeds = RES.parent / "seeds.json"
    if seeds.exists():
        md = md.rstrip("\n") + "\n" + seeds_markdown(
            json.loads(RES.read_text()), json.loads(seeds.read_text()))
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
