#!/usr/bin/env python3
"""
Markdown tables for ottawa_variable_speed.py, generated from its JSON.

Usage:
  python3 ottawa_report.py            # write the notes table
  python3 ottawa_report.py --print    # stdout only
"""

import argparse
import json
from pathlib import Path

from scipy.stats import beta

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "ottawa"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_ottawa.md"

ARMS = (("rms_t", "RMS, tiempo (clásico)"),
        ("kurt_q", "curtosis, cociente (clásico)"),
        ("raw", "por máquina, crudo"),
        ("raw_aug", "por máquina, crudo + aumento"),
        ("quot", "por máquina, cociente"),
        ("quotg", "por máquina, cociente + ganancia"),
        ("oem_q", "OEM, cociente"),
        ("oem_qg", "OEM, cociente + ganancia"))
LOCAL = ("raw", "raw_aug", "quot", "quotg")
FAULT_NAMES = {"I": "pista interior", "O": "pista exterior", "B": "bola",
               "C": "combinado"}
SCEN_NAMES = {"A1": "A-1 (creciente)", "B1": "B-1 (decreciente)",
              "C1": "C-1 (sube y baja)", "D1": "D-1 (baja y sube)",
              "ABCD1": "los cuatro ensayos 1"}


def fmt(x, nd=1):
    return "—" if x is None else f"{x:.{nd}f}".replace(".", ",")


def cp(k, n):
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 1, n - k)
    return 100 * lo, 100 * hi


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _cell(e, what):
    if e is None:
        return "—"
    if not e.get("learned", True):
        return "no aprende"
    return what(e)


def to_markdown(R):
    sc = list(R["scenarios"])
    arms = [(a, n) for a, n in ARMS if any(a in R["scenarios"][s] for s in sc)]
    L = ["# Ottawa: velocidad variable dentro del registro", "",
         "*Generado por `reproducibility_package/ottawa_report.py` desde "
         "`results/ottawa/results.json` (`ottawa_variable_speed.py`). No "
         "editar a mano: `tests/test_generated_notes.py` lo comprueba byte a "
         "byte.*", "",
         f"Datos: `{R['dataset']['dataset']}`, {R['dataset']['version'].split(';')[0]}; "
         f"manifiesto `{R['dataset']['manifest_sha256'][:12]}…`. "
         "Puesta en marcha: ventanas sanas del ensayo 1 de un perfil (un "
         "registro de 10 s) o de los cuatro; radio r_(k) sobre esas ventanas. "
         f"Sanos de prueba: {len(R['test_healthy'])} registros de los ensayos "
         "2 y 3, nunca usados en la puesta en marcha. Fallos: 12 registros por "
         "tipo. Persistencia: 8 de 10 ventanas consecutivas. Semilla de los "
         f"modelos por máquina {R['seed']}, del OEM {R['oem_seed']}; "
         f"{R['n_aug']} ventanas aumentadas.", ""]
    for k in ("oem_q", "oem_qg"):
        h = R.get(f"{k}_training")
        if h:
            L.append(f"- {dict(ARMS)[k]}: {h['epochs_run']}/{h['budget']} "
                     f"épocas, mejor val_loss {fmt(h['best_val_loss'], 5)}.")
    L.append("")

    L += ["## Velocidad de cada registro sano (Hz)", ""]
    rows = []
    for k, v in R["records"].items():
        if k.startswith("H-"):
            rows.append([k, f"{fmt(v['speed_min'])}–{fmt(v['speed_max'])}",
                         v["windows_q"], v["windows_t"]])
    L.append(table(["registro", "velocidad", "ventanas cociente",
                    "ventanas tiempo"], rows))

    L += ["", "## Falsas alarmas en sanos de prueba (ventanas)", "",
          "Porcentaje de ventanas sobre el radio, con intervalo Clopper–Pearson "
          "al 95%. Columnas: con qué registro(s) se hizo la puesta en marcha.", ""]
    rows = []
    for a, name in arms:
        row = [name]
        for s in sc:
            e = R["scenarios"][s].get(a)
            row.append(_cell(e, lambda e: "{}% [{}–{}]".format(
                fmt(100 * e["far_k"] / e["far_n"]),
                *(fmt(v) for v in cp(e["far_k"], e["far_n"])))))
        rows.append(row)
    L.append(table(["modelo"] + [SCEN_NAMES[s] for s in sc], rows))

    L += ["", "## Registros sanos de prueba con alarma persistente", ""]
    rows = []
    for a, name in arms:
        rows.append([name] + [_cell(R["scenarios"][s].get(a),
                                    lambda e: f"{e['rec_false']}/{e['rec_n']}")
                              for s in sc])
    L.append(table(["modelo"] + [SCEN_NAMES[s] for s in sc], rows))

    L += ["", "## Falsas alarmas por banda de velocidad", "",
          "Ventanas sanas de prueba sobre el radio, por velocidad media de la "
          "ventana. Entre paréntesis, el rango de velocidad que cubrió la "
          "puesta en marcha.", ""]
    for s in sc:
        comm = R["scenarios"][s]["commissioning"]
        lo = min(R["records"][k]["speed_min"] for k in comm)
        hi = max(R["records"][k]["speed_max"] for k in comm)
        L += [f"### {SCEN_NAMES[s]} ({fmt(lo)}–{fmt(hi)} Hz)", ""]
        rows = []
        for a, name in arms:
            e = R["scenarios"][s].get(a)
            if e is None or not e.get("learned", True):
                rows.append([name] + ["—"] * len(R["speed_bands"]))
                continue
            rows.append([name] + [f"{fmt(100 * b['k'] / b['n']) if b['n'] else '—'}% "
                                  f"({b['k']}/{b['n']})" for b in e["bands"]])
        L.append(table(["modelo"] + [f"{b[0]}–{b[1]} Hz"
                                     for b in R["speed_bands"]], rows))
        L.append("")

    L += ["## Detección por tipo de fallo", "",
          "Registros con alarma persistente (de 12) y AUROC ventana a ventana "
          "frente a los sanos de prueba (el AUROC no depende del radio).", ""]
    for s in sc:
        L += [f"### Puesta en marcha: {SCEN_NAMES[s]}", ""]
        rows = []
        for a, name in arms:
            e = R["scenarios"][s].get(a)
            if e is None or not e.get("learned", True):
                rows.append([name] + ["—"] * 4)
                continue
            rows.append([name] + [f"{d['rec']}/{d['rec_n']}; {fmt(d['auroc'], 3)}"
                                  for d in (e["detection"][c] for c in FAULT_NAMES)])
        L.append(table(["modelo"] + list(FAULT_NAMES.values()), rows))
        L.append("")

    L += ["## Modelos por máquina: entrenamiento", "",
          "Ventanas de entrenamiento; varianza no reconstruida (se rechaza solo "
          "el colapso, > 0,98); val_loss / train_loss.", ""]
    rows = []
    for s in sc:
        for a in LOCAL:
            e = R["scenarios"][s].get(a)
            if e is None:
                continue
            if not e.get("learned", True):
                rows.append([SCEN_NAMES[s], dict(ARMS)[a], "—", "colapso", "—"])
                continue
            rows.append([SCEN_NAMES[s], dict(ARMS)[a], e["n_train"],
                         fmt(e["unexplained"], 2), fmt(e["gap"], 2)])
    L.append(table(["puesta en marcha", "modelo", "ventanas", "no reconstruida",
                    "generalización"], rows))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    md = to_markdown(json.loads((RES / "results.json").read_text()))
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
