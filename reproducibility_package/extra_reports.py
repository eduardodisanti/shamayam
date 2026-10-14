#!/usr/bin/env python3
"""
Markdown tables for ims_classical_features.py and commissioning_contamination.py,
generated from their JSON.

  python3 extra_reports.py            # write both notes tables
  python3 extra_reports.py --print    # stdout only
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent / "mssp_paper" / "notas"
CLASSICAL = HERE / "results" / "ims_classical" / "results.json"
CONTAM = HERE / "results" / "contamination" / "results.json"
MULTI = HERE / "results" / "multispace" / "results.json"

IND = (("oem_pub", "OEM publicado (autoencoder, referencia)"),
       ("rms", "RMS"), ("kurtosis", "curtosis"), ("crest", "factor de cresta"),
       ("envelope", "envolvente (pico/mediana, órdenes 2–20)"))


def fmt(x, nd=1):
    return "—" if x is None else f"{x:.{nd}f}".replace(".", ",")


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def classical_markdown(R):
    a, b = R["far_window"]
    bs = list(R["bearings"])
    L = ["# IMS: indicadores clásicos con la misma calibración local", "",
         "*Generado por `reproducibility_package/extra_reports.py` desde "
         "`results/ims_classical/results.json` (`ims_classical_features.py`). "
         "No editar a mano: `tests/test_generated_notes.py` lo comprueba byte "
         "a byte.*", "",
         "Sin entrenamiento: un valor por registro de 1 s (dominio temporal, "
         "banda completa, 20 kHz). Radio r_(k) sobre los n primeros registros; "
         f"FAR sobre los registros {a}–{b - 1}; salida: primera persistente "
         "(8 de 10). La envolvente no usa la geometría del rodamiento: pico "
         "sobre mediana del espectro de la envolvente en los órdenes "
         f"{fmt(R['envelope_orders'][0], 0)}–{fmt(R['envelope_orders'][1], 0)}. "
         "Solo el bearing 1 falla.", "",
         "## Falsas alarmas en la vida sana", ""]
    rows = []
    for key, name in IND:
        for i, n in enumerate(R["ns"]):
            row = [name, str(n)]
            for bb in bs:
                r = R["bearings"][bb][key][i]
                row.append(f"{fmt(100 * r['far_k'] / r['far_n'])}% "
                           f"({r['far_k']}/{r['far_n']})")
            rows.append(row)
    L.append(table(["indicador", "n"] + [f"bearing {bb}" + (" (fallo)" if bb == "1" else "")
                                        for bb in bs], rows))
    L += ["", "## Salida de lo normal (registro y antelación al final)", ""]
    rows = []
    for key, name in IND:
        for i, n in enumerate(R["ns"]):
            row = [name, str(n)]
            for bb in bs:
                r = R["bearings"][bb][key][i]
                row.append("sin salida" if r["departure"] is None else
                           f"{r['departure']} ({fmt(r['lead_hours'], 2)} h)")
            rows.append(row)
    L.append(table(["indicador", "n"] + [f"bearing {bb}" for bb in bs], rows))
    L.append("")
    return "\n".join(L)


def contamination_markdown(R):
    L = ["# Puesta en marcha contaminada por un fallo ya presente", "",
         "*Generado por `reproducibility_package/extra_reports.py` desde "
         "`results/contamination/results.json` "
         "(`commissioning_contamination.py`). No editar a mano: "
         "`tests/test_generated_notes.py` lo comprueba byte a byte.*", "",
         f"IMS, bearing {R['bearing']} (el único fallo real). Se sustituyen m "
         "de los n registros de puesta en marcha por registros elegidos al azar "
         f"entre los últimos {R['pool_last']} activos (fallo inequívoco), se "
         "recalcula el radio y se busca la salida persistente (8 de 10) en la "
         f"secuencia real. {R['draws']} sorteos por casilla (semilla "
         f"{R['seed']}). Tolera = n − k: contaminaciones que el radio absorbe "
         "sin cambiar, si quedan por encima de todo lo sano.", ""]
    for name, rows_in in R["scores"].items():
        L += [f"## {name}", ""]
        rows = []
        for r in rows_in:
            rows.append([r["radius"], str(r["tolerates"]), str(r["m"]),
                         f"{fmt(100 * r['lost'] / r['draws'])}%",
                         fmt(r["lead_median_h"]), fmt(r["inflation_median"], 2)])
        L.append(table(["radio", "tolera", "m contaminados",
                        "fallo no detectado", "antelación mediana (h)",
                        "radio / radio limpio (mediana)"], rows))
        L.append("")
    return "\n".join(L)


def _mr(v, nd=1, pct=False):
    import numpy as np
    if not v:
        return "—"
    s = "%" if pct else ""
    if len(v) == 1 or min(v) == max(v):
        return fmt(v[0], nd) + s
    return f"{fmt(float(np.mean(v)), nd)}{s} [{fmt(min(v), nd)}–{fmt(max(v), nd)}]"


def multispace_markdown(R):
    names = {"I": "pista interior", "O": "pista exterior", "B": "bola",
             "C": "combinado"}
    scen = {"ABCD1": "los cuatro ensayos 1", "A1": "A-1"}
    L = ["# Varios espacios cociente a la vez, con la garantía", "",
         "*Generado por `reproducibility_package/extra_reports.py` desde "
         "`results/multispace/results.json` (`multispace_union.py`). No editar a "
         "mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*", "",
         "Alarma si cualquiera de los K espacios supera su radio. Cada radio se "
         f"toma al nivel 1 − {fmt(R['alpha'], 2)}/K (Bonferroni), de modo que la "
         f"falsa alarma total queda acotada por {fmt(R['alpha'], 2)} sin suponer "
         "nada sobre la dependencia entre espacios. Precio: con K = 2 hacen falta "
         "al menos 99 observaciones de puesta en marcha. Nada se entrena: "
         "puntuaciones ya guardadas.", "",
         "## Ottawa (5 semillas del OEM; la curtosis no depende de la semilla)", "",
         "FAR por ventana y registros sanos con alarma persistente (de 8); por tipo "
         "de fallo, registros detectados (de 12). Media [mín–máx] sobre semillas.", ""]
    rows = []
    for sc, combos in R["ottawa"].items():
        for name, runs in combos.items():
            ok = [r for r in runs if r["certifiable"]]
            if not ok:
                rows.append([scen[sc], name, "no certificable (pocas observaciones)"]
                            + ["—"] * 5)
                continue
            rows.append([scen[sc], name,
                         _mr([100 * r["far_k"] / r["far_n"] for r in ok], pct=True),
                         _mr([r["rec_false"] for r in ok])]
                        + [_mr([r["detection"][c]["rec"] for r in ok]) for c in names])
    L.append(table(["puesta en marcha", "espacios", "FAR ventanas",
                    "registros sanos con alarma"] + list(names.values()), rows))
    L += ["", "## IMS (salida y FAR en los registros 200–499)", ""]
    rows = []
    for b, combos in R["ims"].items():
        for name, rs in combos.items():
            rows.append([b, name] + [
                "no certificable" if not r["certifiable"] else
                (("sin salida" if r["departure"] is None else
                  f"{r['departure']} ({fmt(r['lead_hours'], 2)} h)")
                 + f"; FAR {fmt(100 * r['far_k'] / r['far_n'])}%") for r in rs])
    L.append(table(["bearing", "espacios", "n = 49", "n = 99", "n = 149", "n = 200"],
                   rows))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    out = {NOTES / "tablas_ims_clasicos.md":
           classical_markdown(json.loads(CLASSICAL.read_text())),
           NOTES / "tablas_contaminacion.md":
           contamination_markdown(json.loads(CONTAM.read_text())),
           NOTES / "tablas_multiespacio.md":
           multispace_markdown(json.loads(MULTI.read_text()))}
    for path, md in out.items():
        if args.print:
            print(md)
        else:
            path.write_text(md)
            print("wrote", path)


if __name__ == "__main__":
    main()
