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

    ref_path = d / "asset_reference.json"
    if ref_path.exists() and "B" in R["configs"]:
        A = json.loads(ref_path.read_text())["speeds"]
        md.append("\n### Viabilidad: modelo compartido (OEM) frente a modelo "
                  "específico del activo — configuración B\n")
        md.append("Referencia específica: un autoencoder por condición, "
                  "entrenado y umbralizado (p98) con todas sus sanas, como la "
                  "Tabla 7 publicada. OEM: un solo autoencoder entrenado solo "
                  "con simulación, radio calibrado localmente sin etiquetas.\n")
        rows = []
        for s in SPEEDS:
            r = A[s]
            rows.append([s, "específico del activo (todas las sanas)",
                         r["n_healthy"], f(r["far"]),
                         *[f(r[f"{fam}_dr"]) for fam in FAM],
                         f(min(r[f"{fam}_auroc"] for fam in FAM), 3)])
            a = R["configs"]["B"][s]["ae"]
            o = a["oracle"]
            rows.append([s, "OEM + radio local (todas las sanas)",
                         R["configs"]["B"][s]["windows"]["healthy"],
                         f(o["far"]), *[f(o[f"{fam}_dr"]) for fam in FAM],
                         f(min(a["auroc"].values()), 3)])
            c = a["certified"]
            rows.append([s, "OEM + radio certificado (49 primeras sanas)",
                         c["n_cal"],
                         f(c["far_heldout"]) + f" (en {c['n_heldout']})",
                         *[f(c[f"{fam}_dr"]) for fam in FAM], "—"])
        md.append(table(["rpm", "modelo", "sanas usadas", "FAR (%)"] +
                        [f"DR {FAM_ES[x]} (%)" for x in FAM] +
                        ["AUROC mín."], rows))
        md.append("\nGeneralización de la referencia (val_loss / train_loss): " +
                  ", ".join(f"{s}: {A[s]['generalisation_gap']:.2f}"
                            for s in SPEEDS) + ".\n")

    lim_path = d / "limited_data.json"
    if lim_path.exists():
        from scipy.stats import beta as _b
        Lm = json.loads(lim_path.read_text())
        nb = Lm["n_budget"]
        md.append(f"\n### Igualdad de datos: {nb} ventanas sanas para ambos "
                  "— configuración B\n")
        md.append(f"Los dos modelos disponen solo de las {nb} primeras "
                  "ventanas sanas de cada condición. Específico: entrenado "
                  "con ellas y radio r_(k) sobre sus propios residuos de esas "
                  "ventanas (no hay más datos para calibrar). OEM: entrenado "
                  "solo con simulación, radio r_(k) sobre las mismas ventanas. "
                  "FAR medida en las sanas posteriores, que ninguno vio. "
                  f"Específico con {len(Lm['seeds'])} semillas.\n")
        rows = []
        for s in SPEEDS:
            e = Lm["speeds"][s]
            o = e["oem"]
            k, n = o["far_k"], o["far_n"]
            lo = 0.0 if k == 0 else _b.ppf(0.025, k, n - k + 1)
            hi = 1.0 if k == n else _b.ppf(0.975, k + 1, n - k)
            rows.append([s, "OEM + radio local", "—",
                         f"{k}/{n} = {f(100 * k / n, 1)}% "
                         f"[{f(100 * lo, 1)}; {f(100 * hi, 1)}]"
                         if n >= 10 else "n/d",
                         " / ".join(f(o[f"{x}_dr"], 1) for x in FAM)])
            ok = [r for r in e["asset"] if r["learned"]]
            bad = len(e["asset"]) - len(ok)
            if ok:
                fars = [100 * r["far_k"] / r["far_n"] for r in ok
                        if r["far_n"]]
                far_txt = (f"{f(min(fars), 1)}–{f(max(fars), 1)}% "
                           f"(mediana {f(float(np.median(fars)), 1)}%; "
                           f"sobre {ok[0]['far_n']} sanas)"
                           if fars and ok[0]["far_n"] >= 10 else "n/d")
                dr = " / ".join(
                    f"{f(min(r[f'{x}_dr'] for r in ok), 1)}"
                    for x in FAM)
            else:
                far_txt, dr = "—", "—"
            rows.append([s, "específico (mismas ventanas)",
                         f"{len(ok)} de {len(e['asset'])}"
                         + (f" ({bad} no aprendió)" if bad else ""),
                         far_txt, dr])
        md.append(table(["rpm", "modelo", "semillas que aprenden",
                         "FAR en sanas no vistas",
                         "DR mín. bola / int. / ext. (%)"], rows))
        gaps = [r["gap"] for e in Lm["speeds"].values() for r in e["asset"]
                if r["learned"]]
        md.append(f"\nGeneralización del específico (val_loss / train_loss): "
                  f"{f(min(gaps))}–{f(max(gaps))}.\n")

    rq_path = d / "raw_vs_quotient.json"
    if rq_path.exists():
        Q = json.loads(rq_path.read_text())
        md.append("\n### Crudo frente a cociente, mismo tiempo de puesta en "
                  "marcha\n")
        md.append(f"Puesta en marcha: las {Q['n_commission']} primeras "
                  "ventanas en órdenes (147 vueltas) o los mismos segundos "
                  "de señal cruda. FAR en las sanas posteriores; detección "
                  "sobre todos los fallos DE48. Modelos locales con "
                  f"{len(Q['seeds'])} semillas (rango).\n")

        def rng_far(runs):
            ok = [r for r in runs if r.get("learned")]
            if not ok or not ok[0]["far_n"]:
                return "n/d", ok
            v = [100 * r["far_k"] / r["far_n"] for r in ok]
            txt = (f"{f(min(v), 1)}–{f(max(v), 1)}% (de {ok[0]['far_n']})"
                   if min(v) != max(v) else
                   f"{f(v[0], 1)}% (de {ok[0]['far_n']})")
            return txt, ok

        def rng_dr(ok):
            return " / ".join(f(min(r[f"{x}_dr"] for r in ok), 1)
                              for x in FAM) if ok else "—"

        rows = []
        for s in SPEEDS:
            e = Q["speeds"][s]
            full = [r for r in e["raw_local_full"] if r.get("learned")]
            rows.append([s, "crudo, local, todo el historial (referencia "
                         "Tabla 7)", "—",
                         (f"{f(min(r['far_insample'] for r in full), 1)}% "
                          "(en la muestra de entrenamiento)") if full else "—",
                         rng_dr(full)])
            txt, ok = rng_far(e["raw_local"])
            rows.append([s, "crudo, local, solo puesta en marcha",
                         e["raw_cal_windows"], txt, rng_dr(ok)])
            txt, ok = rng_far(e["quot_local"])
            rows.append([s, "cociente, local (aumentado sobre G)",
                         Q["n_commission"], txt, rng_dr(ok)])
            o = e["quot_oem"]
            rows.append([s, "cociente, OEM (simulación)", Q["n_commission"],
                         f"{f(100 * o['far_k'] / o['far_n'], 1)}% "
                         f"(de {o['far_n']})" if o["far_n"] >= 10 else "n/d",
                         " / ".join(f(o[f"{x}_dr"], 1) for x in FAM)])
        md.append(table(["rpm", "modelo", "ventanas de puesta en marcha",
                         "FAR en sanas no vistas",
                         "DR mín. bola / int. / ext. (%)"], rows))
        fails = {k: sum(1 for e in Q["speeds"].values() for r in e[k]
                        if not r.get("learned"))
                 for k in ("raw_local_full", "raw_local", "quot_local")}
        md.append("\nEntrenamientos que no aprendieron: " +
                  ", ".join(f"{k}: {v}" for k, v in fails.items()) + ".\n")

    ab_path = d / "quotient_ablation.json"
    if ab_path.exists() and lim_path.exists() and rq_path.exists():
        Ab = json.loads(ab_path.read_text())
        Lm = json.loads(lim_path.read_text())
        Q = json.loads(rq_path.read_text())
        names = {"G0": "solo proyección", "G1": "+ fase", "G2": "+ ganancia",
                 "G3": "+ offset", "G4": "+ ruido (grupo completo)"}
        src = {"G0": "datos limitados (49 ventanas, sin aumento)",
               "G4": "crudo frente a cociente (quot_local)"}
        sp = list(Ab["speeds"])
        runs = {}
        for s in sp:
            runs[("G0", s)] = Lm["speeds"][s]["asset"]
            runs[("G4", s)] = Q["speeds"][s]["quot_local"]
            for lv in Ab["levels"]:
                runs[(lv, s)] = Ab["speeds"][s][lv]
        levels = ["G0"] + list(Ab["levels"]) + ["G4"]
        md.append("\n### Describir mejor el cociente: modelo local con "
                  "subconjuntos crecientes del grupo\n")
        md.append("Mismos ~5 s de puesta en marcha; solo cambia la "
                  "descripción del grupo. Radio r_(k) sobre las 49 ventanas "
                  "de puesta en marcha; FAR en las sanas posteriores (rango "
                  "sobre semillas). G1–G3: "
                  f"{Ab['n_aug']} ventanas aumentadas, semillas "
                  f"{', '.join(str(s) for s in Ab['seeds'])}. "
                  "G0 y G4 vienen de experimentos anteriores con el mismo "
                  "protocolo: " + "; ".join(f"{k}: {v}" for k, v in src.items())
                  + ".\n")
        rows = []
        for lv in levels:
            row = [lv, names[lv]]
            for s in sp:
                allr = runs[(lv, s)]
                ok = [r for r in allr if r.get("learned")]
                if not ok:
                    row.append("no aprende")
                    continue
                v = [100 * r["far_k"] / r["far_n"] for r in ok]
                txt = (f"{f(min(v), 1)}–{f(max(v), 1)}%" if min(v) != max(v)
                       else f"{f(v[0], 1)}%") + f" (de {ok[0]['far_n']})"
                bad = len(allr) - len(ok)
                row.append(txt + (f"; {bad} no aprende" if bad else ""))
            row.append(str(max(len(runs[(lv, s)]) for s in sp)))
            dr = [min(r[f"{x}_dr"] for s in sp for r in runs[(lv, s)]
                      if r.get("learned")) for x in FAM]
            row.append(" / ".join(f(v, 1) for v in dr))
            rows.append(row)
        md.append(table(["nivel", "grupo"] + [f"FAR {s} rpm" for s in sp]
                        + ["semillas", "DR mín. bola / int. / ext. (%)"],
                        rows))

    seeds_path = d / "oem_seeds.json"
    if seeds_path.exists() and "B" in R["configs"]:
        Sd = json.loads(seeds_path.read_text())
        runs = {"42": {"speeds": R["configs"]["B"]}}
        runs.update(Sd["seeds"])
        md.append("\n### OEM en el cociente: variabilidad entre semillas "
                  "(configuración B)\n")
        md.append("Mismo protocolo que la tabla de calibraciones; el "
                  "operador se reentrena con cada semilla. Rango sobre "
                  f"semillas ({', '.join(runs)}). FAR certificada: radio "
                  "r_(k) sobre las 49 primeras sanas, FAR en las "
                  "posteriores.\n")
        rows = []
        for s in SPEEDS:
            def get(seed, path):
                x = runs[seed]["speeds"][s]
                x = x["ae"] if "ae" in x else x
                for k in path:
                    x = x[k]
                return x
            au = [min(get(k, ["auroc"]).values()) for k in runs]
            far = [get(k, ["certified", "far_heldout"]) for k in runs]
            n_h = get("42", ["certified", "n_heldout"])
            dr = [min(get(k, ["certified", f"{x}_dr"]) for x in FAM)
                  for k in runs]
            tau = [get(k, ["oracle", "tau"]) for k in runs]
            far_txt = (f"{f(min(far), 1)}–{f(max(far), 1)}% (de {n_h})"
                       if n_h >= 10 else "n/d")
            rows.append([s, f"{f(min(au), 3)}–{f(max(au), 3)}", far_txt,
                         f"{f(min(dr), 1)}–{f(max(dr), 1)}",
                         f"{f(min(tau), 4)}–{f(max(tau), 4)}"])
        md.append(table(["rpm", "AUROC mín. por semilla",
                         "FAR certificada n=49", "DR mín. (%)",
                         "τ oráculo"], rows))

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

    md.append("\n### FAR en sanas no vistas, con IC 95% de Clopper–Pearson "
              "(operador compartido)\n")
    from scipy.stats import beta as _beta

    def cp(k, n):
        lo = 0.0 if k == 0 else _beta.ppf(0.025, k, n - k + 1)
        hi = 1.0 if k == n else _beta.ppf(0.975, k + 1, n - k)
        return 100 * lo, 100 * hi

    rows = []
    for c in cfgs:
        for s in SPEEDS:
            a = R["configs"][c][s]["ae"]
            cells = [c, s]
            for arm, key, nk in (("certified", "far_heldout", "n_heldout"),
                                 ("online", "far_post", "n_post")):
                x = a.get(arm, {})
                if arm == "online" and not x.get("converged"):
                    cells.append("no converge")
                    continue
                n = x[nk]
                if not n:
                    cells.append("—")
                    continue
                k = int(round(x[key] * n / 100))
                lo, hi = cp(k, n)
                extra = f" (n calib. = {x['n']})" if arm == "online" else ""
                cells.append(f"{k}/{n} = {f(x[key], 1)}% "
                             f"[{f(lo, 1)}; {f(hi, 1)}]{extra}")
            rows.append(cells)
    md.append(table(["config", "rpm", "certificado n=49",
                     "online (regla publicada)"], rows))

    md.append("\n### Deriva cronológica de las sanas (Spearman índice–residuo, "
              "operador compartido)\n")
    from scipy.stats import spearmanr
    rows = []
    for c in cfgs:
        for s in SPEEDS:
            h = S[f"{c}/{s}/healthy/ae"]
            rho, p = spearmanr(np.arange(len(h)), h)
            rows.append([c, s, len(h), f(float(rho), 3), f"{p:.2g}"])
    md.append(table(["config", "rpm", "n sanas", "ρ", "p"], rows))

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
