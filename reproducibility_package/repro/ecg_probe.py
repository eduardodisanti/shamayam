"""Sonda ECG: ¿cuántos latidos normales de UN paciente fijan su variedad normal?

Diseno, decidido antes de medir:
  - mitdb SOLA. Nunca mezclar con nsrdb: bases distintas, sujetos distintos,
    128 Hz contra 360 Hz. Un detector armado asi separa equipos de grabacion.
  - POR PACIENTE. Corazones distintos son procesos distintos. La referencia y
    las anomalias salen del mismo sujeto: misma derivacion, mismo equipo.
  - Umbral = p95 de las distancias de los normales RETENIDOS, recalculado en
    cada draw. Eso clava la tasa de falsas alarmas en 5% para todo n, y pone
    la linea de azar del grafico en 5%.
  - Cociente de amplitud: l2 (la isoelectrica es un estado real, no una
    convencion de escala).

Tres observables, que es lo que la sonda compara. El cociente TEMPORAL se
declara con el mismo criterio que el de amplitud: el pico R es una convencion
de alineacion, el intervalo R-R es un estado del proceso.

  (a) ventana fija alrededor de R      -> el R-R no existe en la representacion
  (c) ancho proporcional al R-R        -> R-R como forma, sin tocar los vecinos
  (b) de R anterior a R siguiente      -> R-R como forma + contexto de ritmo

Uso:
    python ecg_probe.py --data-dir <carpeta con los .dat/.hea/.atr de mitdb>
    python ecg_probe.py --data-dir ./mitdb --records 100 106 119 201 208

Descarga (physionet esta bloqueado desde el contenedor, hay que bajarlo local):
    pip install wfdb
    python -c "import wfdb; wfdb.dl_database('mitdb','./mitdb')"
"""
from __future__ import annotations
import argparse, collections, os, glob
import numpy as np

L = 160
NS = (1, 2, 3, 5, 8, 12, 20, 30, 50)
REPS = 300
SEED = 0
BEATS = set("NLRejAaJSVEF/fQ")     # anotaciones de latido; el resto es ritmo/ruido
NORMALS = set("N")                  # todo lo demas es anomalo para esta prueba


def l2(X):
    n = np.linalg.norm(X, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return X / n


def resample(seg):
    return np.interp(np.linspace(0, 1, L), np.linspace(0, 1, len(seg)), seg)


def build(record_path):
    """Devuelve los tres observables y las etiquetas de un registro."""
    import wfdb
    rec = wfdb.rdrecord(record_path)
    ann = wfdb.rdann(record_path, "atr")
    sig = rec.p_signal[:, 0]
    fs = rec.fs
    idx = [(s, y) for s, y in zip(ann.sample, ann.symbol) if y in BEATS]
    half = int(0.25 * fs)
    A, B, C, Y = [], [], [], []
    for k in range(1, len(idx) - 1):
        s, y = idx[k]
        sp, sn = idx[k - 1][0], idx[k + 1][0]
        rr = s - sp
        w = int(0.28 * rr)
        if s - half < 0 or s + half >= len(sig): continue
        if s - w < 0 or s + w >= len(sig) or w < 8: continue
        if sp < 0 or sn >= len(sig) or sn - sp < 16: continue
        A.append(resample(sig[s - half:s + half]))
        C.append(resample(sig[s - w:s + w]))
        B.append(resample(sig[sp:sn]))
        Y.append(y)
    if not Y:
        return None
    return (l2(np.array(A)), l2(np.array(C)), l2(np.array(B)),
            np.array(Y), rec.sig_name[0], fs)


def sweep(X, nrm_idx, ano_idx, ns=NS, reps=REPS, seed=SEED):
    """Deteccion contra n, con la FPR clavada en 5% en cada draw."""
    rng = np.random.default_rng(seed)
    out = {}
    for n in ns:
        if len(nrm_idx) <= n + 20:
            out[n] = (float("nan"), float("nan")); continue
        det = []
        for _ in range(reps):
            pick = rng.choice(nrm_idx, n, replace=False)
            ref = X[pick]
            held = np.setdiff1d(nrm_idx, pick)
            d_nom = (1 - X[held] @ ref.T).min(1)
            d_ano = (1 - X[ano_idx] @ ref.T).min(1)
            det.append(float((d_ano > np.percentile(d_nom, 95)).mean()))
        out[n] = (float(np.mean(det)) * 100, float(np.std(det)) * 100)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--records", nargs="*", default=None)
    ap.add_argument("--reps", type=int, default=REPS)
    args = ap.parse_args()

    recs = args.records or sorted(
        os.path.basename(f)[:-4] for f in glob.glob(f"{args.data_dir}/*.hea"))
    if not recs:
        raise SystemExit(f"no hay .hea en {args.data_dir}")

    labels = ("(a) ventana fija", "(c) escala R-R", "(b) R-a-R")
    acc = {lab: {n: [] for n in NS} for lab in labels}
    print(f"{'rec':>5} {'lead':>6} {'latidos':>8} {'anom':>5}  composicion anomala")
    for r in recs:
        built = build(os.path.join(args.data_dir, r))
        if built is None:
            print(f"{r:>5}  sin latidos usables"); continue
        A, C, B, Y, lead, fs = built
        nrm = np.isin(Y, list(NORMALS))
        ni, ai = np.where(nrm)[0], np.where(~nrm)[0]
        comp = dict(collections.Counter(Y[~nrm]))
        print(f"{r:>5} {lead:>6} {len(Y):>8} {len(ai):>5}  {comp}")
        if len(ai) < 5 or len(ni) < 80:
            print(f"      -> salteado (pocos casos)"); continue
        for lab, X in zip(labels, (A, C, B)):
            for n, (m, _) in sweep(X, ni, ai, reps=args.reps).items():
                if not np.isnan(m): acc[lab][n].append(m)

    print(f"\nDeteccion media entre pacientes, FPR clavada en 5%, {args.reps} draws")
    print(f"{'n':>4} " + " ".join(f"{lab:>18}" for lab in labels))
    for n in NS:
        row = []
        for lab in labels:
            v = acc[lab][n]
            row.append(f"{np.mean(v):>17.1f}%" if v else f"{'--':>18}")
        print(f"{n:>4} " + " ".join(row))
    k = len(acc[labels[0]][NS[0]])
    print(f"\npacientes agregados: {k}")


if __name__ == "__main__":
    main()
