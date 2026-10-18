#!/usr/bin/env python3
"""
XJTU-SY: descriptive tables for DISCUSSION, made after seeing the results of
09_protocolo_xjtu.md. Nothing here is a verdict and nothing changes the
registered ones (xjtu_report.py); these tables only help to read them.

  python3 xjtu_discussion.py        # -> notas/tablas_xjtu_discusion.md

Reads only committed results (results/xjtu/report.json, classical.npz).
"""

import argparse
import json
from pathlib import Path

import numpy as np

from bench_report import fmt, table
from mssp_repro.field.xjtu import FAULT_ELEMENT, LIFE_RECORDS
from xjtu_report import BAND_BEARINGS, FALLO, band, commissionable

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "xjtu"
OUT = HERE.parent / "mssp_paper" / "notas" / "tablas_xjtu_discusion.md"
OEM_SEEDS = (42, 0, 1, 2, 3)
LOCAL_SEEDS = (0, 1, 2, 3, 4)
FRACTIONS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
HALF_WIDTH = 5           # records on each side for the running median


def _dep(S, key, b):
    r = S.get(key, {}).get("bearings", {}).get(b)
    return None if r is None else r["departure"]


def _rng(v):
    v = [x for x in v if x is not None]
    if not v:
        return "no sale"
    return str(min(v)) if min(v) == max(v) else f"{min(v)}–{max(v)}"


def profile(series, life, base_n=99):
    base = float(np.median(series[:base_n]))
    out = []
    for f in FRACTIONS:
        i = int(f * life)
        out.append(float(np.median(series[max(0, i - HALF_WIDTH):i + HALF_WIDTH])) / base)
    return out


def to_markdown(S, C):
    L = ["# XJTU-SY: tablas descriptivas para discutir (posteriores a ver los resultados)", "",
         "*Generado por `reproducibility_package/xjtu_discussion.py` desde "
         "`results/xjtu/`. **No son veredictos** ni cambian los de "
         "[`tablas_xjtu.md`](tablas_xjtu.md): se hicieron después de ver los "
         "resultados, para entenderlos. No editar a mano.*", ""]

    L += ["## 1. Falsas alarmas en la franja sana declarada, por rodamiento", "",
          "Porcentaje de registros de la franja [150, ⌊L/2⌋) por encima del radio. "
          "El veredicto H1 usa la suma de los cinco rodamientos.", ""]
    rows = []
    for name, key, seeds in (("OEM, H+V, n = 99 (H1)", "oem_q/{s}/H+V/99", OEM_SEEDS),
                             ("OEM, solo H, n = 99", "oem_q/{s}/H/99", OEM_SEEDS),
                             ("OEM, solo V, n = 99", "oem_q/{s}/V/99", OEM_SEEDS),
                             ("RMS, H+V, n = 99", "rms/{s}/H+V/99", ("-",)),
                             ("por máquina crudo, H, n = 49 (H2)", "raw/{s}/H/49", LOCAL_SEEDS),
                             ("por máquina cociente, H, n = 49 (H2)", "quot/{s}/H/49", LOCAL_SEEDS)):
        row = [name]
        for b in BAND_BEARINGS:
            v = []
            for s in seeds:
                r = S.get(key.format(s=s), {}).get("bearings", {}).get(b)
                if r is not None and "far_k" in r:
                    v.append(100 * r["far_k"] / r["far_n"])
            row.append("—" if not v else (fmt(min(v)) + "%" if fmt(min(v)) == fmt(max(v))
                                          else f"{fmt(min(v))}–{fmt(max(v))}%"))
        rows.append(row)
    L.append(table(["modelo"] + [f"{b} [{band(b)[0]}, {band(b)[1]})" for b in BAND_BEARINGS],
                   rows))

    L += ["", "## 2. Registro de salida por modelo (n = 99)", "",
          "Primer registro con 8 de los 10 últimos por encima del radio. Rango sobre "
          "semillas en los modelos entrenados. Última columna: RMS horizontal en "
          "la salida del OEM (mediana de semillas) dividido por la mediana del RMS "
          "de la puesta en marcha.", ""]
    rows = []
    for b in commissionable(99):
        oem = [_dep(S, f"oem_q/{s}/H+V/99", b) for s in OEM_SEEDS]
        good = [d for d in oem if d is not None]
        ratio = "—"
        if good:
            d = int(np.median(good))
            r = C[f"{b}/H/rms"]
            ratio = fmt(float(r[d] / np.median(r[:99])), 2)
        rows.append([b, FALLO[FAULT_ELEMENT[b]], LIFE_RECORDS[b], _rng(oem),
                     _rng([_dep(S, f"oem_q/{s}/H/99", b) for s in OEM_SEEDS]),
                     _rng([_dep(S, f"oem_q/{s}/V/99", b) for s in OEM_SEEDS]),
                     _rng([_dep(S, f"bench_q/{s}/H+V/99", b) for s in OEM_SEEDS]),
                     _rng([_dep(S, "rms/-/H+V/99", b)]),
                     _rng([_dep(S, "kurtosis/-/H+V/99", b)]),
                     _rng([_dep(S, "envelope/-/H+V/99", b)]), ratio])
    L.append(table(["rod.", "fallo", "vida", "OEM H+V", "OEM H", "OEM V", "banco H+V",
                    "RMS H+V", "curtosis H+V", "envolvente H+V", "RMS H en la salida"],
                   rows))

    L += ["", "## 3. RMS a lo largo de la vida, relativo a la puesta en marcha", "",
          f"RMS del registro dividido por la mediana de los 99 primeros; mediana "
          f"móvil de ±{HALF_WIDTH} registros alrededor de cada fracción de vida.", ""]
    rows = []
    for b in commissionable(99):
        for ch in ("H", "V"):
            rows.append([b, ch] + [fmt(v, 2) for v in profile(C[f"{b}/{ch}/rms"],
                                                             LIFE_RECORDS[b])])
    L.append(table(["rod.", "canal"] + [fmt(f, 2) for f in FRACTIONS], rows))

    L += ["", "## 4. Falsas alarmas por modelo y longitud de puesta en marcha, sin 2_3", "",
          "Igual que la sección 1 pero agregando los cuatro rodamientos con franja "
          "sana sin 2_3 (2_1, 3_1, 3_2, 3_4). Quitar 2_3 es una decisión posterior a "
          "ver los resultados; con 2_3 todas las cifras suben, pero la comparación "
          "entre el OEM y el RMS no cambia de sentido.", ""]
    rows = []
    for space, ns in (("H", (49, 99, 149)), ("V", (49, 99, 149)), ("H+V", (99, 149))):
        for n in ns:
            row = [space, n,
                   _far_range(S, "oem_q/{s}/" + f"{space}/{n}", OEM_SEEDS),
                   _far_range(S, f"rms/-/{space}/{n}", ("-",)),
                   _far_range(S, f"kurtosis/-/{space}/{n}", ("-",)),
                   _far_range(S, f"envelope/-/{space}/{n}", ("-",))]
            for arm in ("raw", "quot"):
                row.append(_far_range(S, arm + "/{s}/" + f"{space}/{n}", LOCAL_SEEDS)
                           if space == "H" and n in (49, 99) else "—")
            rows.append(row)
    L.append(table(["canal", "n", "OEM", "RMS", "curtosis", "envolvente",
                    "por máquina crudo", "por máquina cociente"], rows))

    L += ["", "## 5. Cambio de la puntuación justo después de la puesta en marcha (n = 49)", "",
          "Mediana de la puntuación en los registros 49–148 dividida por la mediana "
          "en los registros 0–48, canal horizontal. Mayor que 1: la puntuación sube "
          "al salir de la puesta en marcha. Rango sobre semillas.", ""]
    rows = []
    for b in BAND_BEARINGS:
        row = [b]
        for arm in ("raw", "quot"):
            row.append(_range2([_jump(L49[s].get(f"{b}/49/{arm}")) for s in LOCAL_SEEDS]))
        row.append(_range2([_jump({"learned": True, "scores": list(F[f"oem_q/{s}/{b}/H"])})
                            for s in OEM_SEEDS]))
        row.append(_range2([_jump({"learned": True, "scores": list(C[f"{b}/H/rms"])})]))
        rows.append(row)
    L.append(table(["rod.", "por máquina crudo", "por máquina cociente", "OEM", "RMS"],
                   rows))
    L.append("")
    return "\n".join(L)


def _far_range(S, key, seeds, excl=("2_3",)):
    v = []
    for s in seeds:
        B = S.get(key.format(s=s), {}).get("bearings", {})
        k = sum(B[b]["far_k"] for b in B if "far_k" in B[b] and b not in excl)
        n = sum(B[b]["far_n"] for b in B if "far_n" in B[b] and b not in excl)
        if n:
            v.append(100 * k / n)
    if not v:
        return "—"
    lo, hi = fmt(min(v)), fmt(max(v))
    return lo + "%" if lo == hi else f"{lo}–{hi}%"


def _jump(r):
    if not r or not r.get("learned"):
        return None
    x = np.asarray(r["scores"], dtype=float)
    return float(np.median(x[49:149]) / np.median(x[:49]))


def _range2(v):
    v = [x for x in v if x is not None]
    if not v:
        return "—"
    lo, hi = fmt(min(v), 2), fmt(max(v), 2)
    return lo if lo == hi else f"{lo}–{hi}"


def load(res=RES):
    global L49, F
    S = json.loads((res / "report.json").read_text())["settings"]
    with np.load(res / "classical.npz") as z:
        C = {k: z[k] for k in z.files}
    with np.load(res / "factory_scores.npz") as z:
        F = {k: z[k] for k in z.files}
    L49 = {s: json.loads((res / "local" / f"seed{s}.json").read_text())["runs"]
           for s in LOCAL_SEEDS}
    return S, C


L49, F = {}, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    md = to_markdown(*load())
    if args.print:
        print(md)
    else:
        OUT.write_text(md)
        print("wrote", OUT)


if __name__ == "__main__":
    main()
