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
