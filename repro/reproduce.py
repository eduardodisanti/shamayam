#!/usr/bin/env python3
"""
Blueprints v8 — regenerate EVERY number, table and figure from scratch.

    python reproduce.py                 # datos en ./data, salida en ./out
    python reproduce.py --data-root /otra/ruta --out run_a

Determinism is the point. Every stage takes an explicit seed; nothing depends on
wall-clock time, filesystem order, or hash randomisation. The run ends by writing
MANIFEST.json with a SHA-256 of every artefact, so two runs can be compared
byte for byte:

    python reproduce.py --out run_a && python reproduce.py --out run_b
    python reproduce.py --compare run_a run_b

MNIST is fetched from OpenML and cached to <out>/cache/mnist.npz on first use;
if the network is unavailable the MNIST stages are skipped and recorded as
skipped in the manifest rather than silently omitted.
"""
from __future__ import annotations

import argparse, glob, hashlib, json, os, subprocess, sys, time
import numpy as np

SEED = 0
DATA_ROOT_FOR_FIGS = [None]   # set in main(); figures need the raw signals
# Tides and solar are built inside their own stages from files the convergence
# stage does not otherwise read. Rather than parse those files twice, each
# stage leaves its realisations here, keyed by domain and then by subset, and
# the convergence stage measures them with the same code as every other
# domain. Empty when those stages are skipped.
CONV_EXTRA = {}
L = 160                      # common time grid for the physical domains
ORDERS = 5                   # arrival orders for every net measurement
REPS = 20                    # random subsets per size in the contrast
N_GRID = [5, 10, 20, 40, 80, 160, 320, 640]
EPS_MNIST = [0.366, 0.436, 0.478, 0.521]
BUDGETS = [1, 2, 4, 8, 16, 32, 64]
NMAX_PHYS = 600
SUBSAMPLES = 10              # independent draws of size NMAX_PHYS per domain
CONV_STEPS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 32, 40, 50, 64,
              80, 100, 120, 160, 200, 320, 500, 800, 1300,
              2000, 3200, 5000, 8000, 12800, 20000]
# La escalera empieza en 1 y no en 5 a proposito. Con el primer punto en 5 no se
# puede distinguir "el codo esta en 5" de "el codo esta en 5 o antes y el
# procedimiento no sabe decir mas": el estimador devolveria su propio piso. Y se
# densifica por debajo de 200 porque ahi esta el codo: con la escalera anterior
# un cruce reportado en n=20 solo significaba "entre 12 y 20".
CONV_REPS = 20               # independent draws per step
CONV_REPS_LOW = 100          # ...salvo abajo, donde la dispersion entre sorteos
CONV_LOW_UPTO = 32           # es grande y es justo donde se lee el codo
CONV_HELD = 200              # encounters held out of every draw
CONV_HELD_MIN = 50           # a step is measured only if this many are left
CONV_NMAX = 20000            # ceiling on n, so one domain cannot dominate
PM_SETS = ("J1_normal_to_reverse", "J1_reverse_to_normal",
           "J2_normal_to_reverse", "J2_reverse_to_normal")

# --- deteccion de anomalias en ECG (mitdb, un sujeto por curva) -------------
ECG_L = 160                  # misma grilla que los dominios fisicos
ECG_NS = [1, 2, 3, 4, 5, 6, 8, 12, 20, 30, 50]
ECG_REPS = 300               # draws de referencia independientes por punto
ECG_HELD_MIN = 60            # normales que deben quedar fuera para el p95
ECG_MIN_ANO = 5              # un registro se mide solo con esto de cada clase
ECG_MIN_NRM = 80
ECG_HALF_S = 0.25            # media ventana fija, en segundos, para (a)
ECG_RR_FRAC = 0.28           # media ventana de (c), como fraccion del R-R
ECG_PACED = ("102", "104", "107", "217")   # marcapasos: excluidos, AAMI
ECG_BEAT_SYMBOLS = set("NLRejAaJSVEF/fQ")  # anotaciones de latido
ECG_NORMAL_SYMBOLS = set("NLRej")           # clase N de AAMI EC57: normal mas
                                           # bloqueos de rama. Con "N" a secas,
                                           # el 109 y el 111 (todo L) y el 118
                                           # (todo R) quedan con CERO normales y
                                           # sus miles de latidos de conduccion
                                           # se cuentan como anomalias.

SPOKEN_DIR = "gemo_of_int_mnist/audio_data/recordings"   # FSDD, beside datasets/
CONV_AT = [5, 20, 50, 200]   # sample sizes quoted in the summary table
CONV_EPS_POOL = 600          # eps is estimated from this many points, ALWAYS.
                             # The pairwise matrix is the only O(n^2) object in
                             # this stage and it is what produced a bus error
                             # earlier: 100953 ECG beats would ask for 76 GB.
                             # Capping the pool is a declared choice, not an
                             # optimisation -- the median it estimates is a
                             # functional of the measure (prop:bulk(i)), so 600
                             # draws already fix it.
# No numeric convergence criterion is declared here. What the figures support
# is that the radius CONVERGES -- it stops changing -- and for now that is read
# from the curve, not from a threshold. A threshold has to be chosen, and the
# three this project has used disagree; one of them returns the first point of
# its own grid for half the tidal stations, which is censoring reported as
# measurement.
TIDE_MONTHS = ["20220101", "20220401", "20220701", "20221001",
               "20230101", "20230401"]
TIDE_PERIOD_H = 24.8412      # lunar day; the calendar day is not a tidal cycle
TIDE_L = 128
TIDE_PRE = 0.35              # where the fiducial high water sits in the window
SOLAR_CLEAR = 1.0            # TotCC in tenths: at or below this, a clear day
SOLAR_CLOUDY = 8.0           # at or above this, an overcast day
# NSRDB writes a sentinel, not a NaN, when a value is missing: -9900 for an
# irradiance and -99 for a tenth of cloud cover. Both sit inside the numeric
# range of their column and neither is NaN, so a NaN screen never sees them.
# The screen has to be the PHYSICAL RANGE of each quantity, declared before
# measuring and not chosen by looking at the answer.
SOLAR_GLO_MAX = 1500.0       # W/m^2. Above the solar constant at the surface.
SOLAR_KT_MAX = 1.5           # clearness index; >1 only under cloud enhancement
SOLAR_CC_MAX = 10.0          # total cloud cover is reported in tenths
SOLAR_MAX_FILES = 60         # station-years actually read, sampled with a seed
SOLAR_NMAX = 600             # days per covering computation, as for the
                             # physical domains. A greedy net needs an n-by-n
                             # distance matrix: at 438k days that is 1.5 TB and
                             # the process dies with SIGBUS, not an exception.
LC_GRID = [1, 2, 5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560, 5000]
LC_REPS = 10                 # independent training draws per point
LC_TAIL_FROM = 640           # above this the curve is flat and the spread is
LC_REPS_TAIL = 3             # tiny, so fewer draws buy the same picture. The
                             # count used at every point is recorded in
                             # learning.json; it is not silently varied.
LC_MED_NMAX = 640            # the within-class median is a functional of the
                             # measure and has settled long before this. Beyond
                             # it the n x n matrix is the only quadratic object
                             # in the stage: 5000 samples would ask for a 200 MB
                             # matrix per class per draw, for a number that no
                             # longer moves.
OP_PCTL = [0.5, 1, 2, 5, 10, 20, 35, 50, 70]   # tau grid, as within-class
                             # distance percentiles: derived, never guessed
OP_TARGETS = (0.80, 0.90, 0.95, 0.99)          # the "titles" that can be requested
OP_REPS = 5                  # independent train/test splits
LC_TARGETS = (0.85, 0.90, 0.95)   # absolute accuracies, common to every
                             # condition: "how many samples to reach 0.90" is
                             # comparable across quotients, whereas a knee at
                             # 95%% of each condition's OWN maximum is not
LC_KNEE = 0.95               # knee := smallest n reaching this fraction of the
                             # accuracy at the largest n. Declared, not fitted.
LC_MED_TOL = (0.05, 0.02, 0.01)   # the representation knee is reported at three
                             # tolerances, not one: the within-class median barely
                             # moves at all, so a single threshold would hide how
                             # much the answer depends on the threshold

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))


def _strkeys(o):
    """JSON object keys must be strings; make the coercion explicit and
    order-stable so two runs serialise identically."""
    if isinstance(o, dict):
        return {str(k): _strkeys(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_strkeys(v) for v in o]
    return o


def jdump(obj, path):
    with open(path, "w") as f:
        json.dump(_strkeys(obj), f, indent=1, sort_keys=True)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def reps_for(n):
    """Mas sorteos donde la varianza esta: en n chico. Un solo numero de
    repeticiones gasta esfuerzo arriba, donde la curva ya es plana, y lo
    escatima abajo, donde se decide la lectura."""
    return CONV_REPS_LOW if n <= CONV_LOW_UPTO else CONV_REPS


def seed_for(*parts):
    """A stable seed from a label.

    Python's built-in hash() is randomised per process for strings, so it must
    never appear anywhere that a result depends on. SHA-256 is stable across
    processes, machines and versions.
    """
    key = "|".join(str(p) for p in parts).encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16)


def array_sha(A):
    """Content hash of an array: shape, dtype and bytes."""
    h = hashlib.sha256()
    A = np.ascontiguousarray(A)
    h.update(str(A.shape).encode())
    h.update(str(A.dtype).encode())
    h.update(A.tobytes())
    return h.hexdigest()


def savefig(fig, path):
    """Deterministic PNG: no timestamp, no software tag."""
    fig.savefig(path, dpi=160, facecolor="#fcfcfb",
                metadata={"Software": None, "Creation Time": None})


# --------------------------------------------------------------------------- #

def load_physical(root):
    import pandas as pd
    from run_experiment import l2_normalise, z_normalise

    def grid(A):
        A = np.asarray(A, float)
        if A.shape[1] == L:
            return A
        xo, xn = np.linspace(0, 1, A.shape[1]), np.linspace(0, 1, L)
        return np.stack([np.interp(xn, xo, r) for r in A])

    def pm(pat, sets=PM_SETS):
        """All four nominal manoeuvres, not one.

        Until v8 this read only J1_normal_to_reverse, which is 2226 of the 8788
        records section 7.1 has always reported. The four populations are

            J1 normal->reverse  2226      J2 normal->reverse  2151
            J1 reverse->normal  2246      J2 reverse->normal  2165

        and pm_pooling.py measured what happens when they go in together. At
        any fixed tolerance the pooled covering number is 1.06 to 1.25 times
        the largest single population, never four times it: the four overlap
        so heavily that they are one set, not four. The radius converges on
        the pooled set with the same shape and the same speed. So they go in
        together, and stage_pm_populations emits the table that shows why.

        The one thing pooling does change is the ruler. Epsilon is the median
        distance WITHIN the set, so a pooled epsilon is the median of a
        mixture and comes out larger than any one population's own -- here
        1.33x the largest. |S| for the pooled set is therefore not comparable
        with |S| for one population unless both are measured at the same
        epsilon, which is exactly what the cross-tabulation does.
        """
        # sets=None means every record in the folder. The anomalous archive is
        # read that way on purpose: its 137 manoeuvres include transitions into
        # and out of the fault position, which carry different names and are
        # precisely the ones that leave the nominal region. Filtering them to
        # the four nominal names would drop the anomalies the test is for.
        pats = [f"{n}_*.parquet" for n in sets] if sets else ["*.parquet"]
        out = []
        for name in pats:
            for f in sorted(glob.glob(f"{root}/pm/{pat}/{name}")):
                p = pd.read_parquet(f)["Power"].to_numpy(float)
                out.append(np.interp(np.linspace(0, 1, L),
                                     np.linspace(0, 1, len(p)), p))
        if not out:
            raise SystemExit(f"no PM parquet under {root}/pm/{pat} for {sets}")
        return np.stack(out)

    return {
        "PM real (nominal)":   (grid(pm("kaggle_nominal")), "l2"),
        "PM simulated":        (grid(np.load(f"{root}/pm/mc_pm_dataset.npy")), "l2"),
        "ECG real (MIT-BIH)":  (grid(np.load(f"{root}/ecg/field_ecg_dataset_aligned_normalized.npy")), "l2"),
        "ECG simulated":       (grid(np.load(f"{root}/ecg/mc_ecg_gaussian_dataset.npy")), "l2"),
        "Battery real (NASA)": (grid(np.load(f"{root}/batteries/field_discharges_dataset.npy")), "znorm"),
    }, grid, pm


def stage_physical(root, out):
    """|S(eps)| per domain against the full surrogate hierarchy.

    Two things this does NOT do, both of which it used to do:

    (1) It does not share one RNG across domains. Each domain draws its
        subsample from a generator seeded by ITS OWN NAME, so the sample a
        domain gets no longer depends on how many records the domains before it
        happened to have. That coupling is what made two machines with slightly
        different copies of one dataset disagree on every OTHER dataset.

    (2) It does not report a single draw as a point estimate. |S(eps)| is
        measured over SUBSAMPLES independent draws of size n and reported as
        mean +- sd. On the real ECG that spread is 16% of the mean: a single
        draw is not a measurement, it is one sample from a distribution we were
        not showing.
    """
    from run_experiment import (l2_normalise, z_normalise, net_sizes_over_eps,
                                greedy_net)
    from surrogates import SURROGATES
    Q = {"l2": l2_normalise, "znorm": z_normalise}
    DOM, _, _ = load_physical(root)

    res = {}
    for name, (A, q) in DOM.items():
        n = min(NMAX_PHYS, len(A))
        keys = ["real"] + list(SURROGATES)
        draws = {k: [] for k in keys}
        own_eps = {k: [] for k in SURROGATES}
        own_size = {k: [] for k in SURROGATES}
        eps_draws, growths = [], []
        for rep in range(SUBSAMPLES):
            rng = np.random.default_rng(seed_for(SEED, name, "subsample", rep))
            raw = A[rng.choice(len(A), n, replace=False)]
            X = Q[q](raw)
            D = 1 - X @ X.T
            eps = float(np.median(D[np.triu_indices(n, 1)]))
            eps_draws.append(eps)
            draws["real"].append(
                float(net_sizes_over_eps(X, [eps], ORDERS, SEED).mean()))
            # How many exemplars are remembered after n encounters. Measured on
            # every draw, not on the first one: a single arrival order is one
            # trajectory, and a curve with no spread cannot show whether the
            # plateau is the phenomenon or the draw.
            growths.append(greedy_net(X, eps, record_growth=True)[1])
            for k, f in SURROGATES.items():
                g = np.random.default_rng(seed_for(SEED, name, k, rep))
                Xs = Q[q](f(raw.copy(), g))
                draws[k].append(
                    float(net_sizes_over_eps(Xs, [eps], ORDERS, SEED).mean()))
                # The same surrogate measured at ITS OWN resolution. The paper
                # applies the real class's eps to the surrogates unchanged, and
                # says that re-deriving eps on each surrogate would measure
                # nothing. This is that claim turned into a number instead of
                # left as an assertion: a set evaluated at its own median
                # distance reports its shape, not its size, so a structureless
                # surrogate comes out as compact as -- or more compact than --
                # the process it was built from.
                Ds = 1 - Xs @ Xs.T
                eps_s = float(np.median(Ds[np.triu_indices(n, 1)]))
                own_eps[k].append(eps_s)
                own_size[k].append(
                    float(net_sizes_over_eps(Xs, [eps_s], ORDERS, SEED).mean()))

        G = np.stack(growths)
        r = {"n": n, "n_available": int(len(A)), "quotient": q,
             "subsamples": SUBSAMPLES,
             "growth": G.mean(0).tolist(), "growth_sd": G.std(0).tolist(),
             "draws_real": [float(v) for v in draws["real"]],
             "eps": float(np.mean(eps_draws)), "eps_sd": float(np.std(eps_draws)),
             "eps_draws": [float(v) for v in eps_draws]}
        for k in keys:
            v = np.array(draws[k])
            r[k] = float(v.mean())
            r[k + "_sd"] = float(v.std())
        for k in SURROGATES:
            r[k + "_own_eps"] = float(np.mean(own_eps[k]))
            r[k + "_own_eps_sd"] = float(np.std(own_eps[k]))
            r[k + "_own"] = float(np.mean(own_size[k]))
            r[k + "_own_sd"] = float(np.std(own_size[k]))
        r["compression_vs_iaaft"] = r["iaaft"] / max(r["real"], 1e-9)
        res[name] = r
        print(f"    {name:22s} real {r['real']:6.1f} +-{r['real_sd']:4.1f}   "
              f"iaaft {r['iaaft']:6.1f} +-{r['iaaft_sd']:4.1f}   "
              f"{r['compression_vs_iaaft']:5.1f}x   (n={n} de {len(A)})",
              flush=True)

    jdump(res, f"{out}/surrogate_test.json")

    with open(f"{out}/table_surrogates.tex", "w") as f:
        f.write("\\begin{tabular}{llrrrrrr}\n\\toprule\n"
                "& & & \\multicolumn{4}{c}{$|S(\\varepsilon)|$, "
                "mean $\\pm$ s.d. over "
                f"{SUBSAMPLES} independent subsamples}} & \\\\\n"
                "\\cmidrule(lr){4-7}\n"
                "domain & quot. & $n$ & real & \\textsc{shuffle} & \\textsc{ft} & "
                "\\textsc{iaaft} & compression \\\\\n\\midrule\n")
        for k, v in res.items():
            q = "$\\ell_2$" if v["quotient"] == "l2" else "$z$"
            cells = " & ".join(f"${v[c]:.1f} \\pm {v[c + '_sd']:.1f}$"
                               for c in ("real", "shuffle", "ft", "iaaft"))
            f.write(f"{k} & {q} & {v['n']} & {cells} & "
                    f"${v['compression_vs_iaaft']:.0f}\\times$ \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    # Every draw, not just its summary. A mean and a standard deviation are a
    # claim about a distribution; the draws are the evidence for it, and with
    # ten of them there is no reason to make the reader take the summary on
    # trust. Each draw is an independent sample without replacement from the
    # WHOLE dataset, so each row is a statement about the dataset and not
    # about its first n records.
    with open(f"{out}/table_draws.tex", "w") as f:
        cols = "l" + "r" * (SUBSAMPLES + 1)
        f.write(f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n"
                f"& \\multicolumn{{{SUBSAMPLES}}}{{c}}{{$|S(\\varepsilon)|$ "
                f"per independent draw of $n$}} & \\\\\n"
                f"\\cmidrule(lr){{2-{SUBSAMPLES + 1}}}\n"
                "domain & " + " & ".join(str(i + 1) for i in range(SUBSAMPLES))
                + " & mean $\\pm$ s.d. \\\\\n\\midrule\n")
        for k, v in res.items():
            # one decimal, because each entry is itself a mean over ORDERS
            # arrival orders; rounding to an integer would hide that
            d = " & ".join(f"{x:.1f}" for x in v["draws_real"])
            f.write(f"{k} & {d} & ${v['real']:.1f} \\pm "
                    f"{v['real_sd']:.1f}$ \\\\\n")
        f.write("\\midrule\n")
        f.write(f"& \\multicolumn{{{SUBSAMPLES}}}{{c}}{{$\\varepsilon$ "
                "per draw, the within-domain median distance} & \\\\\n")
        f.write(f"\\cmidrule(lr){{2-{SUBSAMPLES + 1}}}\n")
        for k, v in res.items():
            d = " & ".join(f"{x:.3f}" for x in v["eps_draws"])
            f.write(f"{k} & {d} & ${v['eps']:.3f} \\pm "
                    f"{v['eps_sd']:.3f}$ \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    return res


def stage_pm_anomaly(root, out):
    """PM nominal against real field faults.

    Both sides widen in v8. The nominal side is now all four manoeuvres (J1 and
    J2, both directions), 8788 records rather than 2226. The anomalous side is
    the whole anomalous archive, 137 records rather than 19: it includes the
    transitions into and out of the fault position, which carry different names
    and are exactly the manoeuvres that leave the nominal region. Restricting
    them to the four nominal names would discard the anomalies the test exists
    to detect.
    """
    from run_experiment import l2_normalise, run_contrast
    _, _, pm = load_physical(root)
    nom, ano = pm("kaggle_nominal"), pm("kaggle_anomalous", sets=None)
    X = l2_normalise(np.vstack([nom, ano]))
    y = np.r_[np.zeros(len(nom), int), np.ones(len(ano), int)]

    res = run_contrast(X, y, [0], [5, 10, min(19, len(ano))], REPS, SEED)
    Xn_, Xa_ = X[y == 0], X[y == 1]

    # The operational test: hold out a reference set of nominal curves, ask how
    # far every held-out nominal and every fault falls from it. Repeated over
    # independent reference sets -- a single reference set is a draw, not a
    # measurement, and this is precisely the number that disagreed between two
    # machines with different amounts of nominal data.
    n_ref = 20
    det, sep, med_n, med_a, p95s = [], [], [], [], []
    for rep in range(SUBSAMPLES):
        rng = np.random.default_rng(seed_for(SEED, "pm_operational", rep))
        pick = rng.choice(len(Xn_), n_ref, replace=False)
        ref = Xn_[pick]
        held = np.setdiff1d(np.arange(len(Xn_)), pick)
        d_nom = np.array([np.min(1 - ref @ Xn_[i]) for i in held])
        d_ano = np.array([np.min(1 - ref @ x) for x in Xa_])
        p = float(np.percentile(d_nom, 95))
        det.append(float((d_ano > p).sum()))
        med_n.append(float(np.median(d_nom)))
        med_a.append(float(np.median(d_ano)))
        p95s.append(p)
        sep.append(float(np.median(d_ano) / max(np.median(d_nom), 1e-12)))

    res["_operational"] = {
        "n_reference": n_ref, "repeats": SUBSAMPLES,
        "n_nominal_available": int(len(Xn_)), "n_anomalous": int(len(Xa_)),
        "median_nominal": float(np.mean(med_n)),
        "median_nominal_sd": float(np.std(med_n)),
        "p95_nominal": float(np.mean(p95s)),
        "median_anomalous": float(np.mean(med_a)),
        "median_anomalous_sd": float(np.std(med_a)),
        "separation": float(np.mean(sep)), "separation_sd": float(np.std(sep)),
        "detected_above_p95": float(np.mean(det)),
        "detected_above_p95_sd": float(np.std(det)),
        "detected_min": float(np.min(det)), "detected_max": float(np.max(det)),
    }
    o = res["_operational"]
    print(f"    {o['detected_above_p95']:.1f}+-{o['detected_above_p95_sd']:.1f}"
          f"/{o['n_anomalous']} fallas sobre el p95 nominal "
          f"(rango {o['detected_min']:.0f}-{o['detected_max']:.0f}), "
          f"separacion {o['separation']:.1f}+-{o['separation_sd']:.1f}x, "
          f"{o['n_nominal_available']} nominales disponibles", flush=True)
    jdump(res, f"{out}/pm_anomaly.json")
    return res


def stage_ecg_anomaly(root, out):
    """One heart at a time: how many normal beats fix its normal manifold?

    This is the paper's anomaly-detection method, and it replaces the
    point-machine one. Four design choices, all declared before measuring.

    ONE DATABASE. mitdb only. The nsrdb record used by the physical domains is
    a single healthy subject at 128 Hz; mitdb is other subjects at 360 Hz. A
    detector built from nsrdb normals and mitdb arrhythmias would separate
    recording equipment, not beats -- domain shift dressed as detection.

    ONE SUBJECT PER CURVE. Different hearts are different processes. The
    reference and the anomalies come from the same record: same lead, same
    device, same heart, so the only thing that differs is the beat. Records
    are REPLICATES, never a pooled reference; what is reported is the
    distribution over records, not one manifold built from many.

    THE FALSE-ALARM RATE IS PINNED, NOT MEASURED. The threshold is the 95th
    percentile of the HELD-OUT normal distances, recomputed inside every draw.
    So the false-alarm rate is 5% at every n by construction, the curve is a
    detection rate at a fixed operating point, and the chance line sits at 5%
    -- which is what makes n=1 interpretable instead of degenerate.

    THE TEMPORAL QUOTIENT IS DECLARED, by the same criterion as the amplitude
    one: is it a state of the process or a convention of the instrument? The R
    peak is a convention, so beats are aligned to it. The R-R interval is a
    state -- prematurity IS the anomaly for an atrial ectopic beat -- so it is
    normalised BY, never normalised AWAY. Three observables are measured
    because they differ exactly in how they treat it:

        (a) fixed window around R      the R-R is absent from the representation
        (c) width proportional to R-R  the R-R becomes shape, neighbours untouched
        (b) previous R to next R       the R-R becomes shape, plus rhythm context

    (b) spans three beats, so it is an observable of RHYTHM, not of a beat.
    That is coherent for arrhythmia -- the state of the process includes the
    rhythm -- but it has to be said rather than slipped in.

    Paced records are excluded by the AAMI convention, and a record is measured
    only if it has enough of both classes for a held-out percentile to mean
    anything. Both filters are content-independent: they look at the record,
    never at how well the detector did on it.
    """
    d = os.path.join(root, "ecg", "mitdb")
    heas = sorted(glob.glob(f"{d}/*.hea"))
    if not heas:
        print(f"    omitido: no hay mitdb en {d}\n"
              f"    pip install wfdb && python -c \"import wfdb; "
              f"wfdb.dl_database('mitdb', '{d}')\"", flush=True)
        return {"_skipped": "mitdb ausente", "_dir": d}
    try:
        import wfdb
    except ImportError:
        print("    omitido: falta wfdb (pip install wfdb)", flush=True)
        return {"_skipped": "wfdb ausente"}

    import collections
    from run_experiment import l2_normalise

    def resample(seg):
        return np.interp(np.linspace(0, 1, ECG_L),
                         np.linspace(0, 1, len(seg)), seg)

    def observables(path):
        """The three representations of one record, plus its beat labels."""
        rec, ann = wfdb.rdrecord(path), wfdb.rdann(path, "atr")
        sig, fs = rec.p_signal[:, 0], rec.fs
        beats = [(s, y) for s, y in zip(ann.sample, ann.symbol)
                 if y in ECG_BEAT_SYMBOLS]
        half = int(ECG_HALF_S * fs)
        A, C, B, Y = [], [], [], []
        for k in range(1, len(beats) - 1):
            s, y = beats[k]
            sp, sn = beats[k - 1][0], beats[k + 1][0]
            w = int(ECG_RR_FRAC * (s - sp))
            if s - half < 0 or s + half >= len(sig):        continue
            if s - w < 0 or s + w >= len(sig) or w < 8:      continue
            if sp < 0 or sn >= len(sig) or sn - sp < 16:     continue
            A.append(resample(sig[s - half:s + half]))
            C.append(resample(sig[s - w:s + w]))
            B.append(resample(sig[sp:sn]))
            Y.append(y)
        if not Y:
            return None
        return ({"a_fixed": l2_normalise(np.array(A)),
                 "c_rr_scaled": l2_normalise(np.array(C)),
                 "b_rr_context": l2_normalise(np.array(B))},
                np.array(Y), rec.sig_name[0], int(fs))

    def sweep(X, nrm, ano, rid, tag):
        """Detection against reference size, false-alarm rate pinned at 5%."""
        curve = {}
        for n in ECG_NS:
            if len(nrm) <= n + ECG_HELD_MIN:
                continue
            rng = np.random.default_rng(seed_for(SEED, "ecg", rid, tag, n))
            det = []
            for _ in range(ECG_REPS):
                pick = rng.choice(nrm, n, replace=False)
                ref = X[pick]
                held = np.setdiff1d(nrm, pick)
                d_nom = (1 - X[held] @ ref.T).min(1)
                d_ano = (1 - X[ano] @ ref.T).min(1)
                thr = float(np.percentile(d_nom, 95))
                det.append(float((d_ano > thr).mean()))
            curve[n] = [float(np.mean(det)) * 100, float(np.std(det)) * 100]
        return curve

    res, skipped = {}, {}
    for hea in heas:
        rid = os.path.basename(hea)[:-4]
        if rid in ECG_PACED:
            skipped[rid] = "marcapasos (convencion AAMI)"
            continue
        built = observables(hea[:-4])
        if built is None:
            skipped[rid] = "sin latidos usables"
            continue
        X, Y, lead, fs = built
        nrm = np.where(np.isin(Y, list(ECG_NORMAL_SYMBOLS)))[0]
        ano = np.where(~np.isin(Y, list(ECG_NORMAL_SYMBOLS)))[0]
        if len(ano) < ECG_MIN_ANO or len(nrm) < ECG_MIN_NRM:
            skipped[rid] = (f"pocos casos: {len(nrm)} normales, "
                            f"{len(ano)} anomalos")
            continue
        res[rid] = {
            "lead": lead, "fs": fs,
            "n_beats": int(len(Y)),
            "n_normal": int(len(nrm)), "n_anomalous": int(len(ano)),
            "composition": {k: int(v) for k, v in
                            sorted(collections.Counter(Y[ano]).items())},
            "curves": {tag: sweep(X[tag], nrm, ano, rid, tag) for tag in X},
        }
        b = res[rid]["curves"]["b_rr_context"]
        at20 = b.get(20, [float("nan")])[0]
        print(f"    {rid}  {len(nrm):>5} nom  {len(ano):>4} ano   "
              f"(b) n=20: {at20:5.1f}%", flush=True)

    if not res:
        print("    ningun registro con casos suficientes", flush=True)
        return {"_skipped": "sin registros usables", "_records_skipped": skipped}

    agg = {}
    for tag in ("a_fixed", "c_rr_scaled", "b_rr_context"):
        agg[tag] = {}
        for n in ECG_NS:
            v = [r["curves"][tag][n][0] for r in res.values()
                 if n in r["curves"][tag]]
            if v:
                agg[tag][n] = [float(np.mean(v)), float(np.std(v)),
                               float(np.median(v)), len(v)]

    out_res = {"_per_record": res, "_skipped_records": skipped,
               "_aggregate": agg,
               "_design": {
                   "database": "mitdb", "per_patient": True,
                   "fpr_pinned": 0.05, "reps": ECG_REPS,
                   "grid": list(ECG_NS), "L": ECG_L,
                   "amplitude_quotient": "l2",
                   "records_used": len(res)}}
    jdump(out_res, f"{out}/ecg_anomaly.json")

    print(f"\n    {len(res)} registros, media entre pacientes "
          f"(FPR fijada en 5%, {ECG_REPS} draws)")
    print(f"    {'n':>4} {'(a) vent.fija':>15} {'(c) escala R-R':>16} "
          f"{'(b) R-a-R':>12}")
    for n in ECG_NS:
        row = [agg[t].get(n, [float('nan')])[0]
               for t in ("a_fixed", "c_rr_scaled", "b_rr_context")]
        print(f"    {n:>4} {row[0]:>14.1f} {row[1]:>15.1f} {row[2]:>11.1f}",
              flush=True)
    return out_res

def _sep_at(r, n):
    """Mean separability over classes at subset size n.

    run_contrast keys per_n by int; JSON round-trips them to str. Accept both
    so the same helper works on a live result and on a reloaded file.
    """
    vals = [r[c].get(n, r[c].get(str(n)))["separability"][0]
            for c in r if r[c].get(n, r[c].get(str(n))) is not None]
    return float(np.mean(vals))


SPOKEN_LABEL = "Spoken digits (FSDD)"


def _spoken_set(cache):
    """The FSDD log-mel set: a third digit set, and the one that is not an image.

    Ten concepts, three hundred recordings each, in the representation declared
    in src/audio_mnist.py -- 16 kHz, 64 mel bands, log, one second with zero
    padding, flattened. It goes into every digit stage that does not need image
    geometry: the covering-number gate, the intrinsic dimension, the learning
    curves and the one-class operating point.

    Until v8 it appeared only in the convergence stage, so the paper measured
    the geometry of spoken digits and then said nothing about what that geometry
    costs to learn -- the one place where a modality with nothing to do with
    pixels could have contradicted the written digits, and it was not asked.

    What it does NOT get is the deskew condition. Deskew is an operation on
    image axes and a log-mel spectrogram has none; the declared benign group
    here is who is speaking and how fast, and no operation for it is
    implemented. The stages that offer a quotient therefore report the raw
    condition only for this set, and say so rather than faking a second row.

    `cache` is the run's mnist.npz path; the spoken cache sits beside it. Read
    only from cache: the wav files are not needed once it exists.
    """
    path = os.path.join(os.path.dirname(cache), "spoken.npz")
    if not os.path.exists(path):
        return None
    # Through the loader, not around it: the cache holds the raw padded
    # observable and src/audio_mnist.py applies the declared duration quotient
    # on top. Reading the npz directly would silently give the digit stages a
    # different representation from the one the convergence stage measures.
    from audio_mnist import load_spoken
    Xa, ya, _ = load_spoken(None, path)
    X, y = np.asarray(Xa, float), np.asarray(ya).astype(int)
    if len(np.unique(y)) != 10:
        return None
    return X, y


def stage_mnist(out, cache):
    """Contrast and canonicalisation controls on MNIST."""
    from run_experiment import (l2_normalise, deskew, blur_only, randshear,
                                run_contrast)
    if os.path.exists(cache):
        z = np.load(cache)
        X, y = z["X"], z["y"]
    else:
        try:
            from sklearn.datasets import fetch_openml
        except Exception:
            return None
        try:
            X, y = fetch_openml("mnist_784", version=1, return_X_y=True,
                                as_frame=False)
        except Exception as e:
            print(f"    MNIST no alcanzable ({type(e).__name__}); etapa omitida",
                  flush=True)
            return None
        X = X.astype(np.float64) / 255.0
        y = y.astype(np.int64)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        np.savez_compressed(cache, X=X, y=y)

    res = {}
    for cond, fn in (("raw", None), ("deskew", deskew),
                     ("blur", blur_only), ("randshear", randshear)):
        Xc = X if fn is None else (fn(X, 28, SEED) if fn is randshear else fn(X, 28))
        Xn = l2_normalise(Xc)
        r = run_contrast(Xn, y, list(range(10)), N_GRID, REPS, SEED)
        res[cond] = r
        sep = _sep_at(r, N_GRID[-1])
        print(f"    {cond:10s} separabilidad n={N_GRID[-1]}: {sep:.4f}", flush=True)
    jdump(res, f"{out}/mnist_contrast.json")

    with open(f"{out}/table_controls.tex", "w") as f:
        f.write("\\begin{tabular}{lccc}\n\\toprule\ncondition & resampling & "
                "alignment & $P(d_{\\mathrm{within}} < d_{\\mathrm{between}})$ \\\\\n"
                "\\midrule\n")
        for cond, rs, al in (("randshear", "yes", "destroyed"), ("raw", "no", "---"),
                             ("blur", "yes", "none"), ("deskew", "yes", "applied")):
            v = _sep_at(res[cond], N_GRID[-1])
            nm = cond if cond == "raw" else f"\\textsc{{{cond}}}"
            bold = f"\\textbf{{{v:.3f}}}" if cond == "deskew" else f"{v:.3f}"
            f.write(f"{nm} & {rs} & {al} & {bold} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    return res


def stage_gate(out, cache):
    """THE GATE: |S(eps)| of a real class vs an arbitrary class of equal size.

    Both saturate -- everything bounded is totally bounded. The signal is SIZE.
    The eps grid is derived from the within-class distance percentiles of the
    data itself, never guessed: guessing it is exactly the mistake that made an
    earlier version of this experiment read as a null result.

    Runs on the UCI 8x8 digits bundled with scikit-learn (offline, so the gate
    reproduces on any machine) and, when the MNIST cache is present, on MNIST
    as well. Both rows are reported; neither replaces the other.
    """
    from run_experiment import l2_normalise, net_sizes_over_eps
    from sklearn.datasets import load_digits

    sets = {}
    d = load_digits()
    sets["UCI digits 8x8"] = (l2_normalise(d.data.astype(np.float64)), d.target, 8)
    if os.path.exists(cache):
        z = np.load(cache)
        sets["MNIST 28x28"] = (l2_normalise(z["X"]), z["y"], 28)
    sp = _spoken_set(cache)
    if sp is not None:
        sets[SPOKEN_LABEL] = (l2_normalise(sp[0]), sp[1], None)

    res = {}
    for label, (X, y, side) in sets.items():
        n_per = int(min(np.bincount(y).min(), 600))

        # eps grid from the pooled within-class distances
        w = []
        for c in range(10):
            g = np.random.default_rng(seed_for(SEED, label, "grid", c))
            A = X[g.choice(np.where(y == c)[0], min(200, n_per), replace=False)]
            D = 1 - A @ A.T
            w.append(D[np.triu_indices(len(A), 1)])
        w = np.concatenate(w)
        eps = np.percentile(w, [5, 25, 50, 75, 90])

        real, arb, growth = [], [], {}
        for c in range(10):
            g = np.random.default_rng(seed_for(SEED, label, "class", c))
            A = X[g.choice(np.where(y == c)[0], n_per, replace=False)]
            s = net_sizes_over_eps(A, eps, ORDERS, SEED + c).mean(1)
            real.append(s)
            ga = np.random.default_rng(seed_for(SEED, label, "arbitrary", c))
            B = X[ga.choice(len(X), n_per, replace=False)]      # arbitrary class
            arb.append(net_sizes_over_eps(B, eps, ORDERS, 100 + c).mean(1))
        real = np.stack(real).mean(0)
        arb = np.stack(arb).mean(0)
        ratio = arb / np.maximum(real, 1e-9)

        res[label] = {
            "n_per_class": n_per, "side": side,
            "within_median": float(np.median(w)),
            "eps": eps.tolist(), "real": real.tolist(), "arbitrary": arb.tolist(),
            "ratio": ratio.tolist(),
            # No dimension is estimated here. This grid has five points
            # spanning p5..p90 of the within-class distance and does not
            # satisfy the window declared in src/dimension.py; fitting it
            # against the cosine distance, as earlier versions did, also
            # reports roughly HALF the dimension, because cosine distance
            # is quadratic in the angle near zero. The intrinsic dimension
            # of these two sets is measured in stage 6, once, under the
            # declared protocol.
        }
        print(f"    {label:16s} eps {[round(float(e),3) for e in eps]}")
        print(f"    {'':16s} real {[round(float(v),1) for v in real]}")
        print(f"    {'':16s} arb  {[round(float(v),1) for v in arb]}")
        print(f"    {'':16s} ratio {[round(float(r),2) for r in ratio]}",
              flush=True)

    jdump(res, f"{out}/gate.json")

    with open(f"{out}/table_gate.tex", "w") as f:
        f.write("\\begin{tabular}{llrrrrr}\n\\toprule\n"
                "dataset & quantity & \\multicolumn{5}{c}{$\\varepsilon$ "
                "(within-class percentile)} \\\\\n"
                "& & p5 & p25 & p50 & p75 & p90 \\\\\n\\midrule\n")
        for i, (label, r) in enumerate(res.items()):
            if i:
                f.write("\\midrule\n")
            f.write(f"{label} & $\\varepsilon$ & "
                    + " & ".join(f"{e:.3f}" for e in r["eps"]) + " \\\\\n")
            f.write(" & $|S|$ real & "
                    + " & ".join(f"{v:.1f}" for v in r["real"]) + " \\\\\n")
            f.write(" & $|S|$ arbitrary & "
                    + " & ".join(f"{v:.1f}" for v in r["arbitrary"]) + " \\\\\n")
            f.write(" & ratio & "
                    + " & ".join(f"\\textbf{{{v:.2f}}}" for v in r["ratio"])
                    + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    return res


SEP_GRID = [5, 10, 20, 40, 80, 160]   # common to the three digit sets: UCI has
                                      # 174 per class and FSDD 300, so 160 is
                                      # the largest size all three reach.


def stage_separability(out, cache):
    """Each class against the other NINE, which is the comparison a classifier
    makes -- not against one pooled bag of everything.

    The gate of stage_gate contrasts a real class with an ARBITRARY class of the
    same size, drawn from the pool of all ten digits. That control answers "does
    the covering number see a concept at all", and it is the right control for
    that question. It is the wrong instrument for a different question that was
    being asked of it: whether the ten classes can be told apart. When all ten
    share a large common component the pooled bag comes out as narrow as any one
    class, the ratio collapses towards one, and the number says nothing about
    separability.

    What answers that question is already in the package and is what this stage
    runs: for each class, the within-class distances against the distances to
    the other nine, summarised as

        separability = P(d_within < d_between),   1/2 = chance.

    Reported at every sample size, because the point is that it does not move:
    how separable the classes are is a property of the representation, and five
    realisations per class are enough to know it. That is a statement about the
    cost of ESTIMATING separability, which is this paper's subject; it is not a
    claim that more data cannot help a trained classifier, which is a different
    question about a different object.

    The spoken set is reported under both observables -- with the zero padding
    and with the declared duration quotient -- because the difference between
    them is the evidence for Contribution 5 in a domain with no pixels.
    """
    from run_experiment import l2_normalise, run_contrast
    from sklearn.datasets import load_digits

    sets = {}
    dg = load_digits()
    sets["UCI digits 8x8"] = l2_normalise(dg.data.astype(np.float64))
    ys = {"UCI digits 8x8": dg.target}
    if os.path.exists(cache):
        z = np.load(cache)
        sets["MNIST 28x28"] = l2_normalise(z["X"]); ys["MNIST 28x28"] = z["y"]
    spath = os.path.join(os.path.dirname(cache), "spoken.npz")
    if os.path.exists(spath):
        from audio_mnist import quotient_duration
        z = np.load(spath, allow_pickle=True)
        Xp = np.asarray(z["X"], float); yv = np.asarray(z["y"]).astype(int)
        sets["Spoken digits, zero-padded"] = l2_normalise(Xp)
        ys["Spoken digits, zero-padded"] = yv
        sets["Spoken digits (FSDD)"] = l2_normalise(quotient_duration(Xp))
        ys["Spoken digits (FSDD)"] = yv

    res = {"grid": SEP_GRID, "reps": REPS, "datasets": {}}
    for label, X in sets.items():
        y = ys[label]
        import io as _io, contextlib as _cl
        with _cl.redirect_stdout(_io.StringIO()):        # run_contrast prints
            r = run_contrast(X, y, list(range(10)), SEP_GRID, REPS, SEED)
        per = {}
        for c in range(10):
            d = r[c] if c in r else r[str(c)]
            per[str(c)] = {str(n): (d[n] if n in d else d[str(n)])
                           for n in SEP_GRID if n in d or str(n) in d}
        ns = sorted({int(n) for c in per for n in per[c]})
        mean = {str(n): float(np.mean([per[str(c)][str(n)]["separability"][0]
                                       for c in range(10)])) for n in ns}
        big = str(ns[-1])
        res["datasets"][label] = {
            "per_class": per, "mean_separability": mean,
            "within_median": float(np.mean([per[str(c)][big]["within_med"][0]
                                            for c in range(10)])),
            "between_median": float(np.mean([per[str(c)][big]["between_med"][0]
                                             for c in range(10)]))}
        print(f"    {label:28s} " + "  ".join(f"{mean[str(n)]:.3f}" for n in ns),
              flush=True)

    jdump(res, f"{out}/separability.json")
    with open(f"{out}/table_separability.tex", "w") as f:
        ns = res["datasets"][list(res["datasets"])[0]]["mean_separability"]
        cols = sorted(int(n) for n in ns)
        f.write("\\begin{tabular}{l" + "r" * len(cols) + "rr}\n\\toprule\n"
                "& \\multicolumn{%d}{c}{separability at $n$ per class} & "
                "within & between \\\\\n" % len(cols))
        f.write("\\cmidrule(lr){2-%d}\n" % (len(cols) + 1))
        f.write("dataset & " + " & ".join(str(n) for n in cols)
                + " & median & median \\\\\n\\midrule\n")
        for label, e in res["datasets"].items():
            f.write(label + " & "
                    + " & ".join(f"{e['mean_separability'][str(n)]:.3f}"
                                 for n in cols)
                    + f" & {e['within_median']:.3f} & {e['between_median']:.3f}"
                    + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% separability = P(d_within < d_between), mean over the ten\n"
                "%   classes; 0.5 is chance. Each class against the other nine.\n"
                "% The medians are at the largest n.\n")
    return res


SEL_BUDGETS = [1, 2, 3, 5, 8, 12, 20, 32, 50]


def stage_selector(out, cache):
    """The negative result: geometry sets the BUDGET, it does not set the CHOICE.

    The epsilon-net is used throughout this paper as an instrument for measuring
    a set -- how many exemplars are needed to cover it at a stated resolution.
    It is tempting to promote it from instrument to rule: if a net of size k
    covers the class, keep those k as the class's prototypes. We tried that and
    it loses, and reporting the loss is the point.

    At every budget the same k prototypes per class are chosen two ways: at
    random, and by the greedy net. Everything else is identical -- the same
    split, the same 1-NN decision over the ten prototype sets, the same seeds.
    A greedy net deliberately walks to the EXTREMES of a set, because that is
    what covering means; a nearest-neighbour rule wants the bulk, because that
    is where the mass is. So the instrument that measures the set best is the
    wrong rule for using it, and the honest reading is that what the geometry
    licenses is the SIZE of the memory, not which exemplars go in it.

    That is also the stronger claim. "k exemplars suffice, whichever they are"
    says the structure is in the class; "the right k suffice" would say it is in
    a clever selection.
    """
    from run_experiment import l2_normalise, greedy_net
    from sklearn.datasets import load_digits
    from scipy.spatial.distance import cdist

    sets = {}
    dg = load_digits()
    sets["UCI digits 8x8"] = (l2_normalise(dg.data.astype(np.float64)), dg.target)
    if os.path.exists(cache):
        z = np.load(cache)
        sets["MNIST 28x28"] = (l2_normalise(z["X"]), z["y"])
    spath = os.path.join(os.path.dirname(cache), "spoken.npz")
    if os.path.exists(spath):
        from audio_mnist import load_spoken
        Xa, ya, _ = load_spoken(None, spath)
        sets["Spoken digits (FSDD)"] = (l2_normalise(np.asarray(Xa, float)),
                                        np.asarray(ya).astype(int))

    res = {"budgets": SEL_BUDGETS, "reps": 10, "datasets": {}}
    for label, (X, y) in sets.items():
        n_test = int(min(2000, len(X) // 3))
        acc = {"random": {k: [] for k in SEL_BUDGETS},
               "net": {k: [] for k in SEL_BUDGETS}}
        for rep in range(10):
            g = np.random.default_rng(seed_for(SEED, label, "selector", rep))
            perm = g.permutation(len(X))
            te, tr = perm[:n_test], perm[n_test:]
            Xte, yte, Xtr, ytr = X[te], y[te], X[tr], y[tr]
            pool = {c: np.where(ytr == c)[0] for c in range(10)}
            cap = min(len(v) for v in pool.values())
            for k in SEL_BUDGETS:
                if k > cap:
                    continue
                for how in ("random", "net"):
                    P, L = [], []
                    for c in range(10):
                        idx = g.choice(pool[c], cap, replace=False)
                        A = Xtr[idx]
                        if how == "random":
                            S = A[:k]
                        else:
                            # the k the greedy net keeps first: the net at the
                            # eps that yields k, taken in one arrival order
                            S = A[greedy_net(A, 0.0, kmax=k)[0]] \
                                if _net_kmax_ok(greedy_net) else A[_net_first_k(A, k, greedy_net)]
                        P.append(S); L.append(np.full(len(S), c))
                    P = np.vstack(P); L = np.concatenate(L)
                    pred = L[cdist(Xte, P, "cosine").argmin(1)]
                    acc[how][k].append(float((pred == yte).mean()))
        res["datasets"][label] = {
            how: {str(k): [float(np.mean(v)), float(np.std(v))]
                  for k, v in d.items() if v} for how, d in acc.items()}
        ks = sorted(int(k) for k in res["datasets"][label]["random"])
        print(f"    {label}", flush=True)
        for how in ("random", "net"):
            r = res["datasets"][label][how]
            print(f"      {how:7s} " + "  ".join(f"k={k}:{r[str(k)][0]:.3f}"
                                                 for k in ks), flush=True)
        jdump(res, f"{out}/selector.json")

    with open(f"{out}/table_selector.tex", "w") as f:
        ks = SEL_BUDGETS
        f.write("\\begin{tabular}{ll" + "r" * len(ks) + "}\n\\toprule\n"
                "& & \\multicolumn{%d}{c}{prototypes per class} \\\\\n" % len(ks))
        f.write("\\cmidrule(lr){3-%d}\n" % (len(ks) + 2))
        f.write("dataset & chosen & " + " & ".join(str(k) for k in ks)
                + " \\\\\n\\midrule\n")
        for label, e in res["datasets"].items():
            # The row names carry the claim, so they are not "random" and
            # "net": "any k" says the k exemplars are not chosen, which is the
            # stronger reading, and "the net's k" names the alternative that
            # loses. Calling the first one "random selection" invited exactly
            # the misreading that it is a selection method.
            for how, nm in (("random", "any $k$"), ("net", "the net's $k$")):
                cells = [(f"{e[how][str(k)][0]:.3f}" if str(k) in e[how] else "---")
                         for k in ks]
                f.write(f"{label} & {nm} & " + " & ".join(cells) + " \\\\\n")
            f.write("\\midrule\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% 1-NN over ten per-class prototype sets, same split and seeds.\n"
                "% The net walks to the extremes; the rule wants the bulk.\n")
    return res


def _net_kmax_ok(fn):
    import inspect
    return "kmax" in inspect.signature(fn).parameters


def _net_first_k(A, k, greedy_net):
    """The first k points a greedy net keeps, without needing an eps.

    Farthest-point traversal: the net's own order. Start from the point
    nearest the centroid and repeatedly take the point farthest from what is
    already kept. That IS the greedy net's arrival order, so this reproduces
    which k it would keep at whatever eps yields k.
    """
    from scipy.spatial.distance import cdist
    c = A.mean(0, keepdims=True)
    first = int(cdist(A, c, "cosine").argmin())
    keep = [first]
    d = cdist(A, A[[first]], "cosine").ravel()
    while len(keep) < min(k, len(A)):
        j = int(d.argmax()); keep.append(j)
        d = np.minimum(d, cdist(A, A[[j]], "cosine").ravel())
    return np.array(keep)


def stage_contrast_physical(root, out):
    """The contrast on the physical domains, under BOTH quotients.

    Each domain is a class. Reported twice -- amplitude-only (l2) and
    amplitude+offset (znorm) -- because for battery discharge the choice of
    quotient is the whole result, not a detail of preprocessing.
    """
    from run_experiment import l2_normalise, z_normalise, run_contrast
    DOM, _, _ = load_physical(root)
    names = list(DOM)
    A = np.vstack([DOM[k][0] for k in names])
    y = np.concatenate([np.full(len(DOM[k][0]), i) for i, k in enumerate(names)])
    grid = [n for n in N_GRID if n <= 320]

    res = {}
    for qname, qfn in (("l2", l2_normalise), ("znorm", z_normalise)):
        print(f"  quotient = {qname}")
        r = run_contrast(qfn(A), y, list(range(len(names))), grid, REPS, SEED)
        res[qname] = {names[i]: r[i] for i in r}
    jdump({"domains": names, "n_grid": grid, **res},
          f"{out}/physical_contrast.json")

    with open(f"{out}/table_quotient.tex", "w") as f:
        f.write("\\begin{tabular}{lrrrr}\n\\toprule\n"
                "& \\multicolumn{2}{c}{$\\ell_2$ (amplitude)} & "
                "\\multicolumn{2}{c}{$z$ (amplitude + offset)} \\\\\n"
                "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\n"
                "domain & within med. & separab. & within med. & separab. \\\\\n"
                "\\midrule\n")
        for nm in names:
            cells = []
            for q in ("l2", "znorm"):
                per_n = res[q][nm]
                k = max(per_n)
                cells += [f"{per_n[k]['within_med'][0]:.5f}",
                          f"{per_n[k]['separability'][0]:.3f}"]
            f.write(f"{nm} & " + " & ".join(cells) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    return res


def stage_dimension(root, out, cache):
    """Intrinsic dimension under the declared protocol, WITH its calibration.

    The protocol lives in src/dimension.py; every choice in it is fixed and
    stated. This stage runs it on the physical domains and on digits, and runs
    the identical protocol on spheres of known dimension at matched n, so the
    number is reported next to the evidence for how far it can be trusted.
    """
    from run_experiment import l2_normalise, z_normalise
    from dimension import dimension, calibrate
    from sklearn.datasets import load_digits

    Q = {"l2": l2_normalise, "znorm": z_normalise}
    DOM, _, _ = load_physical(root)

    res = {"protocol": {"grid_points": 12, "pctl": [1.0, 90.0],
                        "window": ["|S|>=4", "|S|<=n/4"], "metric": "angular",
                        "orders": ORDERS, "seed": SEED},
           "domains": {}, "digits": {}, "calibration": {}}

    for nm, (A, q) in DOM.items():
        n = min(NMAX_PHYS, len(A))
        rng = np.random.default_rng(seed_for(SEED, nm, "subsample", 0))
        X = Q[q](A[rng.choice(len(A), n, replace=False)])
        r = dimension(X, orders=ORDERS, seed=SEED)
        res["domains"][nm] = r
        d, se = r["dim"], r["stderr"]
        shown = "NA (n insuficiente)" if np.isnan(d) else f"{d:5.2f} +- {se:.2f}"
        print(f"    {nm:22s} {shown}   n={r['n']}  pts={r['n_points_used']}",
              flush=True)

    sets = {}
    dg = load_digits()
    sets["UCI digits 8x8"] = (l2_normalise(dg.data.astype(np.float64)), dg.target)
    if os.path.exists(cache):
        z = np.load(cache)
        sets["MNIST 28x28"] = (l2_normalise(z["X"]), z["y"])
    sp = _spoken_set(cache)
    if sp is not None:
        sets[SPOKEN_LABEL] = (l2_normalise(sp[0]), sp[1])

    for label, (X, y) in sets.items():
        n_per = int(min(np.bincount(y).min(), NMAX_PHYS))
        real, arb = [], []
        for c in range(10):
            g = np.random.default_rng(seed_for(SEED, label, "class", c))
            idx = g.choice(np.where(y == c)[0], n_per, replace=False)
            real.append(dimension(X[idx], ORDERS, SEED + c))
            ga = np.random.default_rng(seed_for(SEED, label, "arbitrary", c))
            arb.append(dimension(X[ga.choice(len(X), n_per, replace=False)],
                                 ORDERS, 100 + c))
        rm = float(np.nanmean([r["dim"] for r in real]))
        am = float(np.nanmean([r["dim"] for r in arb]))
        res["digits"][label] = {"n_per_class": n_per, "real": real,
                                "arbitrary": arb, "real_mean": rm,
                                "arbitrary_mean": am, "ratio": am / rm}
        print(f"    {label:16s} real {rm:.2f}   arbitraria {am:.2f}   "
              f"cociente {am / rm:.2f}   n={n_per}", flush=True)

    # calibrate only at sample sizes where the protocol actually returned a
    # number: calibrating at an n that cannot support the fit produces a row of
    # NAs with the odd spurious value, which is worse than no row at all.
    ns = {r["n"] for r in res["domains"].values() if not np.isnan(r["dim"])}
    ns |= {v["n_per_class"] for v in res["digits"].values()}
    for n in sorted(ns):
        res["calibration"][str(n)] = calibrate(n, dims=(1, 2, 3, 4, 5, 6),
                                               orders=ORDERS, seed=SEED)
        c = res["calibration"][str(n)]
        print(f"    calibracion n={n:4d}: "
              + "  ".join(f"{d}->{c[d]['estimate']:.2f}" for d in sorted(c)),
              flush=True)

    jdump(res, f"{out}/dimension.json")

    with open(f"{out}/table_dimension.tex", "w") as f:
        f.write("\\begin{tabular}{lrrrl}\n\\toprule\n"
                "set & $n$ & pts & $\\hat{d}$ & \\\\\n\\midrule\n")
        for nm, r in res["domains"].items():
            v = ("\\textsc{na}" if np.isnan(r["dim"])
                 else f"${r['dim']:.2f} \\pm {r['stderr']:.2f}$")
            note = "" if r["n_points_used"] >= 4 else "sample too small"
            f.write(f"{nm} & {r['n']} & {r['n_points_used']} & {v} & {note} \\\\\n")
        f.write("\\midrule\n")
        for label, v in res["digits"].items():
            f.write(f"{label}, real classes & {v['n_per_class']} & --- & "
                    f"${v['real_mean']:.2f}$ & above calibrated range \\\\\n")
            f.write(f"{label}, arbitrary class & {v['n_per_class']} & --- & "
                    f"${v['arbitrary_mean']:.2f}$ & control \\\\\n")
        f.write("\\midrule\n\\multicolumn{5}{l}{\\emph{calibration: same "
                "protocol on $S^d$, $d$ known}} \\\\\n")
        for n, c in res["calibration"].items():
            f.write(f"$n={n}$ & & & "
                    + ", ".join(f"$d{{=}}{d}\\!\\to\\!{c[d]['estimate']:.2f}$"
                                for d in sorted(c)) + " & \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    return res


def stage_learning(out, cache):
    """Learning curves: do unrelated methods stop improving at the same n?

    The claim under test is NOT that any method here is better than another. It
    is that several methods with nothing in common saturate at the same small
    sample size, and that this size coincides with the sample size at which the
    within-class median stops moving. If that holds, what is being hit is a
    property of the manifold and not of the estimator, and the accuracy above
    that point is bought from the tail -- which, by prop:bulk, does not converge
    at any guaranteed rate. That is what makes it expensive.

    Two conditions per dataset: the raw quotient (l2 only) and the declared
    quotient (deskew, then l2). Both are reported, always.
    """
    from run_experiment import l2_normalise, deskew
    from sklearn.datasets import load_digits
    from sklearn.svm import LinearSVC
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier

    def classifier(name, seed):
        if name == "linear SVM":
            return LinearSVC(C=1.0, max_iter=5000, random_state=seed)
        if name == "logistic":
            return LogisticRegression(max_iter=2000, random_state=seed)
        return KNeighborsClassifier(1, metric="cosine")

    NAMES = ["linear SVM", "logistic", "1-NN"]

    sets = {}
    dg = load_digits()
    sets["UCI digits 8x8"] = (dg.data.astype(np.float64), dg.target, 8, 500)
    if os.path.exists(cache):
        z = np.load(cache)
        sets["MNIST 28x28"] = (z["X"], z["y"], 28, 10000)
    sp = _spoken_set(cache)
    if sp is not None:
        sets[SPOKEN_LABEL] = (sp[0], sp[1], None, 600)

    res = {"grid": LC_GRID, "reps": LC_REPS, "reps_tail": LC_REPS_TAIL,
           "tail_from": LC_TAIL_FROM, "median_nmax": LC_MED_NMAX,
           "knee_fraction": LC_KNEE,
           "median_tolerance": LC_MED_TOL, "datasets": {}}

    for label, (X0, y, side, n_test) in sets.items():
        # Never let the held-out set eat the training pool: a cache smaller than
        # expected would otherwise leave zero training samples and fail deep
        # inside the loop instead of here.
        n_test = int(min(n_test, len(X0) // 3))
        if n_test < 100:
            print(f"    {label}: muestra insuficiente ({len(X0)}), etapa omitida",
                  flush=True)
            continue
        rng = np.random.default_rng(seed_for(SEED, label, "split"))
        perm = rng.permutation(len(X0))
        te, tr = perm[:n_test], perm[n_test:]
        entry = {"n_train": int(len(tr)), "n_test": int(n_test), "conditions": {}}
        conds = [("raw", None)]
        if side is not None:
            conds.append(("quotient (deskew)", deskew))
        else:
            entry["no_quotient"] = ("deskew acts on image axes; a log-mel spectrogram has none. "
                    "The declared benign group for this set is speaker "
                    "and speed, and no operation for it is implemented, "
                    "so only the raw condition is reported.")

        for cond, fn in conds:
            Xc = X0 if fn is None else fn(X0, side)
            Xn = l2_normalise(Xc)
            Xtr, ytr, Xte, yte = Xn[tr], y[tr], Xn[te], y[te]
            avail = int(np.bincount(ytr).min())

            curves = {nm: {} for nm in NAMES}
            unconverged = []
            for n in LC_GRID:
                if n > avail:
                    continue
                accs = {nm: [] for nm in NAMES}
                reps_here = LC_REPS if n <= LC_TAIL_FROM else LC_REPS_TAIL
                for rep in range(reps_here):
                    g = np.random.default_rng(seed_for(SEED, label, cond, n, rep))
                    sel = np.concatenate([
                        g.choice(np.where(ytr == k)[0], n, replace=False)
                        for k in range(10)])
                    for nm in NAMES:
                        if n == 1 and nm != "1-NN":
                            continue          # one sample per class: nothing to fit
                        c = classifier(nm, seed_for(SEED, nm, n, rep) % (2**31))
                        c.fit(Xtr[sel], ytr[sel])
                        # an optimiser that stopped on max_iter has not solved
                        # the problem it was given; record it instead of letting
                        # the number look like a converged fit
                        it = getattr(c, "n_iter_", None)
                        if it is not None:
                            it = int(np.max(it))
                            lim = getattr(c, "max_iter", 0)
                            if lim and it >= lim:
                                unconverged.append([nm, int(n), int(rep), it])
                        accs[nm].append(float(c.score(Xte, yte)))
                for nm in NAMES:
                    if accs[nm]:
                        v = np.array(accs[nm])
                        curves[nm][n] = [float(v.mean()), float(v.std()),
                                         int(len(v))]

            # the accuracy knee, per classifier
            knees = {}
            for nm in NAMES:
                ns = sorted(curves[nm])
                if not ns:
                    continue
                top = curves[nm][ns[-1]][0]
                hit = [n for n in ns if curves[nm][n][0] >= LC_KNEE * top]
                knees[nm] = {"knee_n": int(hit[0]) if hit else None,
                             "acc_at_knee": curves[nm][hit[0]][0] if hit else None,
                             "acc_at_max_n": top, "max_n": int(ns[-1]),
                             "n_to_reach": {
                                 str(t): next((int(n) for n in ns
                                               if curves[nm][n][0] >= t), None)
                                 for t in LC_TARGETS}}

            # the representation knee: where the within-class median settles
            meds = {}
            for n in LC_GRID:
                if n < 2 or n > avail or n > LC_MED_NMAX:
                    continue
                # every class, every rep -- sampling one class at random per
                # rep mixes between-class variance into a within-class statistic
                vals = []
                for k in range(10):
                    for rep in range(LC_REPS):
                        g = np.random.default_rng(
                            seed_for(SEED, label, cond, "med", k, n, rep))
                        A = Xtr[g.choice(np.where(ytr == k)[0], n, replace=False)]
                        D = 1 - A @ A.T
                        vals.append(float(np.median(D[np.triu_indices(n, 1)])))
                meds[n] = float(np.mean(vals))
            ns = sorted(meds)
            final = meds[ns[-1]] if ns else None
            med_knee = {str(t): next((n for n in ns
                                      if abs(meds[n] - final) <= t * final), None)
                        for t in LC_MED_TOL}
            # the threshold-free statement: how much does it move at all?
            med_drift = (abs(meds[ns[0]] - final) / final) if ns else None

            entry["conditions"][cond] = {"curves": curves, "knees": knees,
                                         "within_median": meds,
                                         "median_knee_n": med_knee,
                                         "median_drift": med_drift,
                                         "unconverged_fits": unconverged,
                                         "median_range": [ns[0], ns[-1]] if ns else None}
            ks = "  ".join(f"{nm} codo n={knees[nm]['knee_n']} "
                           f"(->{knees[nm]['acc_at_max_n']:.3f}, "
                           f"n@0.90={knees[nm]['n_to_reach']['0.9']})"
                           for nm in NAMES if nm in knees)
            warn = (f"   [{len(unconverged)} ajustes sin converger]"
                    if unconverged else "")
            print(f"    {label:16s} {cond:18s} mediana se mueve "
                  f"{med_drift * 100:.1f}% de n={ns[0]} a n={ns[-1]}   {ks}{warn}",
                  flush=True)

        res["datasets"][label] = entry

    jdump(res, f"{out}/learning.json")

    with open(f"{out}/table_learning.tex", "w") as f:
        f.write("\\begin{tabular}{llrrrr}\n\\toprule\n"
                "& & \\multicolumn{3}{c}{accuracy knee: smallest $n$ per class "
                f"reaching {int(LC_KNEE * 100)}\\% of its own maximum}} & "
                "within-class \\\\\n\\cmidrule(lr){3-5}\n"
                "dataset & quotient & linear SVM & logistic & 1-NN & "
                "median drift \\\\\n"
                "\\midrule\n")
        for label, e in res["datasets"].items():
            for cond, c in e["conditions"].items():
                cells = " & ".join(
                    (str(c["knees"][nm]["knee_n"]) if nm in c["knees"] else "---")
                    for nm in NAMES)
                f.write(f"{label} & {cond} & {cells} & "
                        f"{c['median_drift'] * 100:.0f}\\% \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")

    with open(f"{out}/table_learning_target.tex", "w") as f:
        cols = "l l " + " ".join("r" * len(LC_TARGETS) * 3)
        f.write(f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n& & "
                + " & ".join("\\multicolumn{%d}{c}{%s}" % (len(LC_TARGETS), nm)
                             for nm in NAMES) + " \\\\\n")
        c0 = 3
        for _ in NAMES:
            f.write("\\cmidrule(lr){%d-%d}" % (c0, c0 + len(LC_TARGETS) - 1))
            c0 += len(LC_TARGETS)
        f.write("\ndataset & quotient & "
                + " & ".join(f"{t:.2f}" for _ in NAMES for t in LC_TARGETS)
                + " \\\\\n\\midrule\n")
        for label, e in res["datasets"].items():
            for cond, c in e["conditions"].items():
                cells = []
                for nm in NAMES:
                    r = c["knees"].get(nm, {}).get("n_to_reach", {})
                    cells += [str(r.get(str(t)) or "---") for t in LC_TARGETS]
                f.write(f"{label} & {cond} & " + " & ".join(cells) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% samples per class needed to reach a COMMON absolute accuracy.\n"
                "% Comparable across quotients; the knee table is not.\n")
    return res


def stage_operating(out, cache):
    """The operating point is REQUESTED, not discovered.

    The recognition rule of Definition~(Recognition) has one parameter, tau,
    and it belongs to the observer: it is set, not fitted. Raising it can only
    admit more, so it trades precision against recall monotonically, and the
    memory the rule needs at that setting is exactly |S(tau)| -- the covering
    number. So a question no trained classifier can answer in advance has an
    answer here: "how much must I store to reach F1 = 0.9?"

    The same table answers the other half. When a target sits above this
    rule's ceiling, no setting of tau reaches it and no extra memory helps:
    lowering tau to keep more exemplars costs recall faster than it buys
    precision, and every one of the five curves peaks in the interior of the
    tau grid rather than at its edge, so the maximum is the rule's and not the
    grid's.

    What that ceiling is NOT is a property of the phenomenon. It belongs to a
    rule that must answer without comparing, at this pool size. On the same
    data and the same observable, the comparative readout of
    stage_learning reaches accuracies this rule cannot -- 0.95 on UCI with
    twenty exemplars per class. The gap between them is the cost of refusing to
    compare, and it is the point of reporting both.
    """
    from run_experiment import l2_normalise, deskew, greedy_net
    from sklearn.datasets import load_digits

    sets = {}
    dg = load_digits()
    sets["UCI digits 8x8"] = (dg.data.astype(np.float64), dg.target, 8, 500)
    if os.path.exists(cache):
        z = np.load(cache)
        sets["MNIST 28x28"] = (z["X"], z["y"], 28, 10000)
    sp = _spoken_set(cache)
    if sp is not None:
        sets[SPOKEN_LABEL] = (sp[0], sp[1], None, 600)

    res = {"percentiles": OP_PCTL, "targets": list(OP_TARGETS), "reps": OP_REPS,
           "datasets": {}}

    for label, (X0, y, side, n_test) in sets.items():
        n_test = int(min(n_test, len(X0) // 3))
        entry = {"conditions": {}}
        conds = [("raw", None)]
        if side is not None:
            conds.append(("quotient (deskew)", deskew))
        else:
            entry["no_quotient"] = ("deskew acts on image axes; a log-mel spectrogram has none. "
                    "The declared benign group for this set is speaker "
                    "and speed, and no operation for it is implemented, "
                    "so only the raw condition is reported.")
        for cond, fn in conds:
            Xn = l2_normalise(X0 if fn is None else fn(X0, side))

            # tau grid from the within-class distances of the training pool
            g0 = np.random.default_rng(seed_for(SEED, label, cond, "taugrid"))
            w = []
            for c in range(10):
                ic = np.where(y == c)[0]
                A = Xn[g0.choice(ic, min(200, len(ic)), replace=False)]
                D = 1 - A @ A.T
                w.append(D[np.triu_indices(len(A), 1)])
            taus = np.percentile(np.concatenate(w), OP_PCTL)

            KEYS = ("S", "P", "R", "F", "uni", "amb", "rej", "acc_uni",
                    "cover", "setsize", "acc_arg")
            acc = {t: {k: [] for k in KEYS} for t in range(len(taus))}
            for rep in range(OP_REPS):
                g = np.random.default_rng(seed_for(SEED, label, cond, "split", rep))
                perm = g.permutation(len(Xn))
                te, tr = perm[:n_test], perm[n_test:]
                Xtr, ytr, Xte, yte = Xn[tr], y[tr], Xn[te], y[te]
                cap = int(min(np.bincount(ytr).min(), NMAX_PHYS))
                for j, tau in enumerate(taus):
                    sz = pr = rc = f1 = 0.0
                    Dmin = np.zeros((len(Xte), 10))
                    for c in range(10):
                        ic = g.choice(np.where(ytr == c)[0], cap, replace=False)
                        A = Xtr[ic]
                        S = A[greedy_net(A, float(tau))[0]]
                        Dmin[:, c] = (1 - Xte @ S.T).min(1)
                        pred = Dmin[:, c] <= tau
                        tp = int((pred & (yte == c)).sum())
                        fp = int((pred & (yte != c)).sum())
                        fn_ = int((~pred & (yte == c)).sum())
                        p_ = tp / max(tp + fp, 1)
                        r_ = tp / max(tp + fn_, 1)
                        sz += len(S) / 10
                        pr += p_ / 10
                        rc += r_ / 10
                        f1 += (2 * p_ * r_ / max(p_ + r_, 1e-9)) / 10
                    acc[j]["S"].append(sz); acc[j]["P"].append(pr)
                    acc[j]["R"].append(rc); acc[j]["F"].append(f1)

                    # The SAME net answers two different questions. Above:
                    # "is this a c?", absolutely, one class at a time. Below:
                    # the candidate SET, and the forced choice by comparison.
                    cand = Dmin <= tau
                    k = cand.sum(1)
                    uni = k == 1
                    acc[j]["uni"].append(float(uni.mean()))
                    acc[j]["amb"].append(float((k >= 2).mean()))
                    acc[j]["rej"].append(float((k == 0).mean()))
                    acc[j]["acc_uni"].append(
                        float((np.argmax(cand[uni], 1) == yte[uni]).mean())
                        if uni.any() else float("nan"))
                    acc[j]["cover"].append(
                        float(cand[np.arange(len(yte)), yte].mean()))
                    acc[j]["setsize"].append(float(k.mean()))
                    acc[j]["acc_arg"].append(float((Dmin.argmin(1) == yte).mean()))

            curve = []
            for j, tau in enumerate(taus):
                a = acc[j]
                curve.append({"tau": float(tau),
                              "exemplars": float(np.mean(a["S"])),
                              "exemplars_sd": float(np.std(a["S"])),
                              "precision": float(np.mean(a["P"])),
                              "recall": float(np.mean(a["R"])),
                              "f1": float(np.mean(a["F"])),
                              "f1_sd": float(np.std(a["F"])),
                              "frac_unique": float(np.mean(a["uni"])),
                              "frac_ambiguous": float(np.mean(a["amb"])),
                              "frac_rejected": float(np.mean(a["rej"])),
                              "acc_on_unique": float(np.nanmean(a["acc_uni"])),
                              "set_coverage": float(np.mean(a["cover"])),
                              "set_size": float(np.mean(a["setsize"])),
                              "acc_forced_choice": float(np.mean(a["acc_arg"])),
                              "acc_forced_sd": float(np.std(a["acc_arg"]))})

            best = max(curve, key=lambda r: r["f1"])
            bestfc = max(curve, key=lambda r: r["acc_forced_choice"])
            request = {}
            for t in OP_TARGETS:
                ok = [r for r in curve if r["f1"] >= t]
                request[str(t)] = (
                    {"tau": min(ok, key=lambda r: r["exemplars"])["tau"],
                     "exemplars": min(ok, key=lambda r: r["exemplars"])["exemplars"]}
                    if ok else None)
            entry["conditions"][cond] = {"curve": curve, "request": request,
                                         "ceiling_f1": best["f1"],
                                         "ceiling_sd": best["f1_sd"],
                                         "ceiling_tau": best["tau"],
                                         "ceiling_exemplars": best["exemplars"],
                                         "forced_choice_best": bestfc}
            got = "  ".join(
                (f"F1>={t}: {request[str(t)]['exemplars']:.0f} ej."
                 if request[str(t)] else f"F1>={t}: --")
                for t in OP_TARGETS)
            print(f"    {label:16s} {cond:18s} techo F1 absoluta "
                  f"{best['f1']:.3f}+-{best['f1_sd']:.3f}   {got}", flush=True)
            # Every set statistic is printed AT THE SAME tau. Reporting the
            # candidate set at one tau and forced choice at another invites the
            # comparison "coverage 0.77 but argmin 0.95", which compares two
            # different operating points and means nothing.
            print(f"    {'':16s} {'':18s} en tau={best['tau']:.3f} "
                  f"({best['exemplars']:.0f} ej.): unica {best['frac_unique']:.2f} / "
                  f"ambigua {best['frac_ambiguous']:.2f} / "
                  f"rechaz {best['frac_rejected']:.2f}, "
                  f"acierto sobre unicas {best['acc_on_unique']:.3f}, "
                  f"cobertura {best['set_coverage']:.3f}, "
                  f"eleccion forzada {best['acc_forced_choice']:.3f}", flush=True)
            print(f"    {'':16s} {'':18s} mejor eleccion forzada "
                  f"{bestfc['acc_forced_choice']:.3f}+-{bestfc['acc_forced_sd']:.3f} "
                  f"en tau={bestfc['tau']:.3f} ({bestfc['exemplars']:.0f} ej., "
                  f"cobertura ahi {bestfc['set_coverage']:.3f})", flush=True)

        res["datasets"][label] = entry

    jdump(res, f"{out}/operating.json")

    with open(f"{out}/table_operating.tex", "w") as f:
        f.write("\\begin{tabular}{llrrrr}\n\\toprule\n"
                "& & \\multicolumn{3}{c}{exemplars per class required} & \\\\\n"
                "\\cmidrule(lr){3-5}\n"
                "dataset & quotient & "
                + " & ".join(f"$F_1\\!\\ge\\!{t:.2f}$" for t in OP_TARGETS[:3])
                + " & ceiling $F_1$ \\\\\n\\midrule\n")
        for label, e in res["datasets"].items():
            for cond, c in e["conditions"].items():
                cells = []
                for t in OP_TARGETS[:3]:
                    r = c["request"][str(t)]
                    cells.append(f"{r['exemplars']:.0f}" if r
                                 else "---")
                f.write(f"{label} & {cond} & " + " & ".join(cells)
                        + f" & ${c['ceiling_f1']:.3f} \\pm "
                          f"{c['ceiling_sd']:.3f}$ \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% One-class rule, one-vs-rest, single global tau.\n"
                "% '---' = the demanded F1 is above this rule's ceiling, given\n"
                "%   in the last column. NOT a claim about the phenomenon: the\n"
                "%   comparative readout of table_learning_target reaches\n"
                "%   accuracies this rule cannot, on the same data.\n"
                "% Every curve peaks inside the tau grid, so the ceiling is the\n"
                "%   rule's and not the grid's.\n")

    with open(f"{out}/table_decision.tex", "w") as f:
        f.write("\\begin{tabular}{llrrrrrr}\n\\toprule\n"
                "& & \\multicolumn{3}{c}{candidate set} & accuracy & set & "
                "forced \\\\\n\\cmidrule(lr){3-5}\n"
                "dataset & quotient & one & several & none & on \\emph{one} & "
                "coverage & choice \\\\\n\\midrule\n")
        for label, e in res["datasets"].items():
            for cond, c in e["conditions"].items():
                b = max(c["curve"], key=lambda r: r["f1"])
                f.write(f"{label} & {cond} & {b['frac_unique']:.2f} & "
                        f"{b['frac_ambiguous']:.2f} & {b['frac_rejected']:.2f} & "
                        f"{b['acc_on_unique']:.3f} & {b['set_coverage']:.3f} & "
                        f"{b['acc_forced_choice']:.3f} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% At the tau maximising one-class F1. Set coverage is how often\n"
                "% the true class is among the candidates; the gap between it and\n"
                "% forced-choice accuracy is the room a decision rule has.\n")
    return res


def _find_dir(root, name):
    """Locate an auxiliary data directory.

    Tides and solar live beside the repository's datasets/ rather than inside
    it, and the layout differs between the author's machine and the container.
    Try the plausible places rather than hard-coding one and failing silently.
    """
    for up in ("", "..", "../..", "../../.."):
        cand = os.path.normpath(os.path.join(root, up, name))
        if os.path.isdir(cand):
            return cand
    return None


def _tide_series(root, sid):
    import pandas as pd
    xs = []
    for m in TIDE_MONTHS:
        f = glob.glob(f"{root}/{sid}_*/{sid}_{m}.csv")
        if f:
            xs.append(pd.to_numeric(pd.read_csv(f[0]).iloc[:, 1],
                                    errors="coerce").to_numpy(float))
    if not xs:
        return None
    x = np.concatenate(xs)
    return x[~np.isnan(x)]


def _tide_argmax(x, per):
    """Fiducial as pre-registered: the highest water in each lunar-day block."""
    w = int(per * TIDE_PRE); A = []
    for k in range(0, len(x) - per, per):
        p = k + int(np.argmax(x[k:k + per]))
        a, b = p - w, p - w + per
        if a < 0 or b > len(x):
            continue
        A.append(np.interp(np.linspace(0, 1, TIDE_L),
                           np.linspace(0, 1, per), x[a:b]))
    return np.stack(A)


def _tide_none(x, per):
    """No fiducial at all: consecutive lunar-day blocks, taken where they fall.

    This is the control for the claim that phase is a nuisance parameter of the
    observation. Sea level on the MSL datum is a zero-mean oscillation, so two
    days sampled at different phase are close to orthogonal under the cosine
    metric, and what the measurement returns is the offset of the recording
    clock rather than the geometry of the tide. The number this produces is
    what the paper compares the aligned realisation against; without it the
    claim is an assertion.
    """
    A = []
    for k in range(0, len(x) - per, per):
        A.append(np.interp(np.linspace(0, 1, TIDE_L),
                           np.linspace(0, 1, per), x[k:k + per]))
    return np.stack(A)


def _tide_template(x, per, iters=2):
    """Corrected fiducial: cross-correlation against a template, as an ECG beat
    is aligned. Specified before it was run; see COMPROMISO_FIDUCIAL.md."""
    A = _tide_argmax(x, per)
    for _ in range(iters):
        T = A.mean(0); T = T - T.mean()
        out = []
        for sig in A:
            sc = sig - sig.mean()
            c = np.correlate(np.r_[sc, sc], T, mode="valid")[:TIDE_L]
            out.append(np.roll(sig, -int(np.argmax(c))))
        A = np.stack(out)
    return A


def _bimodality(A):
    """Sarle's coefficient on the second high water's position after aligning.
    Above ~0.555 the fiducial jumped between two different peaks."""
    from scipy.signal import find_peaks
    pos = []
    for sig in A:
        pk, _ = find_peaks(sig, distance=int(TIDE_L * 0.25))
        if len(pk) >= 2:
            o = pk[np.argsort(sig[pk])[::-1][:2]]
            pos.append(max(o) / TIDE_L)
    if len(pos) < 20:
        return float("nan")
    v = np.array(pos); m, sd = v.mean(), v.std()
    g = ((v - m) ** 3).mean() / sd ** 3
    k = ((v - m) ** 4).mean() / sd ** 4
    return float((g * g + 1) / max(k, 1e-9))


def stage_tides(root, out):
    """Nine NOAA stations, with a pre-registered prediction.

    The declaration, written before any epsilon was computed
    (PREREGISTRO_MAREAS.md): epsilon falls with the station's mean tidal range,
    because the meteorological contribution is roughly constant in absolute
    terms, so its relative weight shrinks as the astronomical range grows.
    Criterion fixed in advance: Spearman <= -0.6.

    Two things this stage does NOT do. It does not min-max the daily curves --
    that erases the spring-neap variation exactly (a 2.6x range becomes 1.0x)
    and was what made an earlier version of this analysis report tides as the
    most compact domain studied. And it does not choose between the two
    fiducials: the body number is the pre-registered one, and the corrected one
    is reported alongside whatever it says.
    """
    from run_experiment import l2_normalise, greedy_net
    from surrogates import SURROGATES
    from scipy.stats import spearmanr

    STATIONS = {"Boston": "8443970", "The Battery NY": "8518750",
                "Atlantic City": "8534720", "Key West": "8724580",
                "Galveston": "8771450", "San Diego": "9410170",
                "San Francisco": "9414290", "Anchorage": "9455920",
                "Honolulu": "1612340"}
    base = _find_dir(root, "data/noaa_tides")
    if base is None:
        print("    no encuentro data/noaa_tides; etapa omitida", flush=True)
        return None
    per = int(TIDE_PERIOD_H / 0.1)
    res = {}
    for nom, sid in STATIONS.items():
        x = _tide_series(base, sid)
        if x is None:
            continue
        rng_d = np.array([np.max(x[k * per:(k + 1) * per]) -
                          np.min(x[k * per:(k + 1) * per])
                          for k in range(len(x) // per)])
        # Diurnal inequality: within each lunar day the two high waters are
        # unequal wherever the diurnal constituents are strong. We operate it
        # as the gap between the highest level in each half of the window,
        # divided by that window's range, and report the median over days.
        # This is our operationalisation and not the harmonic-analysis
        # definition; it is declared here because cause C2 of the
        # pre-registration names this mechanism, and a named cause that is
        # never measured cannot be ruled in or out.
        _ineq = []
        for k in range(len(x) // per):
            w = x[k * per:(k + 1) * per]
            h = len(w) // 2
            if h < 2:
                continue
            span = float(np.max(w) - np.min(w))
            if span <= 0:
                continue
            _ineq.append(abs(float(np.max(w[:h])) - float(np.max(w[h:]))) / span)
        r = {"station_id": sid, "n_days": int(len(rng_d)),
             "range_m": float(rng_d.mean()), "range_sd_m": float(rng_d.std()),
             "diurnal_inequality": float(np.median(_ineq)) if _ineq else float("nan")}
        for tag, fn in (("prereg", _tide_argmax), ("corrected", _tide_template),
                        ("unaligned", _tide_none)):
            A = fn(x, per)
            X = l2_normalise(A)
            D = 1 - X @ X.T
            eps = float(np.median(D[np.triu_indices(len(X), 1)]))
            g = np.random.default_rng(seed_for(SEED, "tides", nom, tag))
            sur = l2_normalise(SURROGATES["iaaft"](A.copy(), g))
            r[tag] = {"eps": eps, "n": int(len(A)),
                      "S": int(len(greedy_net(X, eps)[0])),
                      "iaaft": int(len(greedy_net(sur, eps)[0]))}
            r[tag]["compression"] = r[tag]["iaaft"] / max(r[tag]["S"], 1)
            if tag == "prereg":
                r["bimodality"] = _bimodality(A)
                CONV_EXTRA.setdefault("NOAA tides", {})[nom] = X
        res[nom] = r
        print(f"    {nom:16s} rango {r['range_m']:6.3f} m  "
              f"eps prereg {r['prereg']['eps']:.4f}  "
              f"corregido {r['corrected']['eps']:.4f}  "
              f"SIN alinear {r['unaligned']['eps']:.4f} "
              f"(compresion {r['unaligned']['compression']:.1f}x)  "
              f"bimod {r['bimodality']:.3f}", flush=True)

    if len(res) >= 4:
        # build the test off a snapshot; writing "_test" into res while still
        # iterating over res.values() is how the first version of this crashed
        stations = dict(res)
        R = np.array([v["range_m"] for v in stations.values()])
        t = {}
        for tag in ("prereg", "corrected", "unaligned"):
            E = np.array([v[tag]["eps"] for v in stations.values()])
            rho, pv = spearmanr(R, E)
            t[tag] = {"spearman": float(rho), "p": float(pv)}
        t["criterion"] = -0.6
        t["holds_prereg"] = bool(t["prereg"]["spearman"] <= -0.6)
        # Cause C2 was declared in advance as a deviation mechanism. It is also
        # a rival explanation of the whole ordering, and with nine stations the
        # two may not be separable. Reported either way.
        Iq = np.array([v.get("diurnal_inequality", np.nan)
                       for v in stations.values()])
        Ep = np.array([v["prereg"]["eps"] for v in stations.values()])
        ok = ~np.isnan(Iq)
        if ok.sum() >= 4:
            rho_i, p_i = spearmanr(Iq[ok], Ep[ok])
            rho_p, p_p = spearmanr((R[ok] * (1.0 - Iq[ok])), Ep[ok])
            t["c2_inequality"] = {"spearman": float(rho_i), "p": float(p_i)}
            t["c2_product"] = {"spearman": float(rho_p), "p": float(p_p)}
        res["_test"] = t
        print(f"    Spearman(rango, eps)  preregistrado "
              f"{t['prereg']['spearman']:+.3f} (p={t['prereg']['p']:.4f})   "
              f"corregido {t['corrected']['spearman']:+.3f} "
              f"(p={t['corrected']['p']:.4f})   criterio <= -0.6 -> "
              f"{'SE SOSTIENE' if t['holds_prereg'] else 'NO'}",
              flush=True)
        if "c2_inequality" in t:
            print(f"    C2  Spearman(desigualdad diurna, eps) "
                  f"{t['c2_inequality']['spearman']:+.3f}   "
                  f"producto rango*(1-desig) "
                  f"{t['c2_product']['spearman']:+.3f}   "
                  f"(nueve estaciones: no se separa del rango)",
                  flush=True)

    jdump(res, f"{out}/tides.json")
    with open(f"{out}/table_tides.tex", "w") as f:
        f.write("\\begin{tabular}{lrrrrr}\n\\toprule\n"
                "station & range (m) & $n$ & $\\varepsilon$ & $|S|$ & "
                "compression \\\\\n\\midrule\n")
        for nom, v in sorted(((k, v) for k, v in res.items() if k != "_test"),
                             key=lambda kv: kv[1]["prereg"]["eps"]):
            p = v["prereg"]
            f.write(f"{nom} & {v['range_m']:.3f} & {p['n']} & {p['eps']:.4f} & "
                    f"{p['S']} & ${p['compression']:.1f}\\times$ \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% Realisation: one lunar day aligned to high water, MSL datum,\n"
                "% amplitude NOT normalised. Ordered by the measured epsilon;\n"
                "% the prediction was the ordering by range, declared first.\n")

    # The three fiducials side by side, plus the C5 diagnostic. Committed to in
    # COMPROMISO_FIDUCIAL.md before the corrected fiducial was run: it is
    # reported whatever it says, and it goes to an appendix, not the body.
    with open(f"{out}/table_fiducial.tex", "w") as f:
        f.write("\\begin{tabular}{lrrrrr}\n\\toprule\n"
                "& range & \\multicolumn{3}{c}{$\\varepsilon$ by fiducial} & "
                "bimodality \\\\\n\\cmidrule(lr){3-5}\n"
                "station & (m) & pre-registered & corrected & none & "
                "(C5) \\\\\n\\midrule\n")
        for nom, v in sorted(((k, v) for k, v in res.items() if k != "_test"),
                             key=lambda kv: kv[1]["prereg"]["eps"]):
            b = v["bimodality"]
            mark = "\\textbf{%.3f}" % b if b > 5 / 9 else "%.3f" % b
            f.write(f"{nom} & {v['range_m']:.3f} & {v['prereg']['eps']:.4f} & "
                    f"{v['corrected']['eps']:.4f} & "
                    f"{v['unaligned']['eps']:.4f} & {mark} \\\\\n")
        t = res.get("_test", {})
        if t:
            f.write("\\midrule\nSpearman $\\rho$ & & "
                    + " & ".join(f"${t[k]['spearman']:+.3f}$"
                                 for k in ("prereg", "corrected", "unaligned"))
                    + " & \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% Bimodality is Sarle's coefficient on the position of the\n"
                "%   second high water after alignment; bold exceeds 5/9.\n"
                "% The pre-registered criterion was rho <= -0.6.\n")
    return res


def stage_solar(root, out):
    """Irradiance, split by the cloud cover the file itself reports.

    Irradiance is deterministic; cloud is part of the external conditions, not
    a violation of determinism. Which slice of those conditions an observer
    declares changes the size of the region, and the declaration costs nothing
    here: NSRDB records total cloud cover beside the irradiance.

    Two caps, both announced rather than silent. Only SOLAR_MAX_FILES
    station-years are read, sampled with a fixed seed from whatever is present;
    and each covering number is measured on SOLAR_NMAX days, repeated over
    SUBSAMPLES independent draws and reported as mean +- s.d., exactly as the
    physical domains are.
    """
    from run_experiment import l2_normalise, greedy_net
    from surrogates import SURROGATES
    import pandas as pd

    found = []
    for d in ("data/nsrdb_solar", "data/nsrdb"):
        base = _find_dir(root, d)
        if base:
            found += glob.glob(f"{base}/**/*.csv", recursive=True)
    found = sorted(set(found))
    if not found:
        print("    sin CSV de NSRDB; etapa omitida", flush=True)
        return None

    rng = np.random.default_rng(seed_for(SEED, "solar", "files"))
    take = sorted(rng.choice(len(found), min(SOLAR_MAX_FILES, len(found)),
                             replace=False))
    files = [found[i] for i in take]
    print(f"    {len(found)} station-years encontrados, {len(files)} leidos "
          f"(muestra con semilla)", flush=True)

    NEED = ("Glo Mod (W/m^2)", "ETR (W/m^2)", "TotCC (10ths)")
    glo, etr, cc, skipped = [], [], [], 0
    for f in files:
        try:
            d = pd.read_csv(f)
        except Exception:
            skipped += 1
            continue
        d.columns = [c.strip() for c in d.columns]
        if not all(c in d.columns for c in NEED):
            skipped += 1
            continue
        n = (len(d) // 24) * 24
        if n < 24:
            skipped += 1
            continue
        glo.append(pd.to_numeric(d[NEED[0]][:n], errors="coerce")
                   .to_numpy(float).reshape(-1, 24))
        etr.append(pd.to_numeric(d[NEED[1]][:n], errors="coerce")
                   .to_numpy(float).reshape(-1, 24))
        cc.append(pd.to_numeric(d[NEED[2]][:n], errors="coerce")
                  .to_numpy(float).reshape(-1, 24).mean(1))
    if not glo:
        print("    ningun CSV con las columnas esperadas; etapa omitida",
              flush=True)
        return None
    glo = np.vstack(glo); etr = np.vstack(etr); cc = np.concatenate(cc)
    kt = np.where(etr > 1, glo / np.maximum(etr, 1e-9), 0.0)

    # Until v8 this screened NaN only, and NSRDB's sentinels are not NaN. The
    # consequence was not small. Eleven of the sixty station-years read here
    # carry -9900 in Glo Mod for the whole year, and because a missing cloud
    # cover of -99 averages to -990 -- far below the clear-sky threshold --
    # every one of those days was filed as CLEAR SKY. 3862 of the 7203
    # clear-sky days were fill, the clear-sky radius came out 0.77 against
    # 0.02 to 0.10 everywhere else in the paper, and solar was the only curve
    # in the convergence figure that did not look like the others.
    #
    # A day is kept only if every hour of it is physically possible.
    ok = ~(np.isnan(glo).any(1) | np.isnan(cc) | np.isnan(kt).any(1))
    ok &= (glo >= 0).all(1) & (glo <= SOLAR_GLO_MAX).all(1)
    ok &= (kt >= 0).all(1) & (kt <= SOLAR_KT_MAX).all(1)
    ok &= (cc >= 0) & (cc <= SOLAR_CC_MAX)
    n_drop = int((~ok).sum())
    glo, etr, cc, kt = glo[ok], etr[ok], cc[ok], kt[ok]
    if skipped:
        print(f"    {skipped} archivos salteados (formato inesperado)", flush=True)
    print(f"    {len(glo)} dias utilizables   ({n_drop} descartados por "
          f"salirse del rango fisico declarado)", flush=True)

    def bloque(A, tag):
        """Never let a covering computation see an unbounded n."""
        if len(A) < 24:
            return None
        vals = {k: [] for k in ("eps", "S", "iaaft")}
        for rep in range(SUBSAMPLES):
            g = np.random.default_rng(seed_for(SEED, "solar", tag, rep))
            idx = (g.choice(len(A), SOLAR_NMAX, replace=False)
                   if len(A) > SOLAR_NMAX else np.arange(len(A)))
            B = A[idx]
            X = l2_normalise(B)
            D = 1 - X @ X.T
            eps = float(np.median(D[np.triu_indices(len(X), 1)]))
            sur = l2_normalise(SURROGATES["iaaft"](B.copy(), g))
            vals["eps"].append(eps)
            vals["S"].append(float(len(greedy_net(X, eps)[0])))
            vals["iaaft"].append(float(len(greedy_net(sur, eps)[0])))
            if len(A) <= SOLAR_NMAX:
                break
        r = {"n_available": int(len(A)), "n_per_draw": int(min(len(A), SOLAR_NMAX)),
             "draws": len(vals["eps"])}
        for k, v in vals.items():
            r[k] = float(np.mean(v)); r[k + "_sd"] = float(np.std(v))
        r["compression"] = r["iaaft"] / max(r["S"], 1e-9)
        return r

    res = {"n_files_found": len(found), "n_files_read": len(files),
           "n_days": int(len(glo)), "n_days_dropped": n_drop,
           "range_screen": {"glo_max": SOLAR_GLO_MAX, "kt_max": SOLAR_KT_MAX,
                            "cc_max": SOLAR_CC_MAX},
           "clear_threshold": SOLAR_CLEAR,
           "cloudy_threshold": SOLAR_CLOUDY, "n_max_per_draw": SOLAR_NMAX}
    for var, M in (("glo", glo), ("kt", kt)):
        for cond, mask in (("clear", cc <= SOLAR_CLEAR),
                           ("cloudy", cc >= SOLAR_CLOUDY),
                           ("all", np.ones(len(cc), bool))):
            r = bloque(M[mask], f"{var}_{cond}")
            if r:
                res[f"{var}_{cond}"] = r
                # The three sky conditions are this domain's subsets, the way
                # the ten digits are for MNIST. Only irradiance goes to the
                # convergence stage: the clearness index is a derived variable
                # reported as a control, not a second phenomenon.
                if var == "glo":
                    A = M[mask]
                    if len(A) > CONV_HELD_MIN + 20:
                        g_ = np.random.default_rng(seed_for(SEED, "solar-conv",
                                                            cond))
                        k_ = min(CONV_NMAX + CONV_HELD, len(A))
                        sel = g_.choice(len(A), k_, replace=False)
                        CONV_EXTRA.setdefault("NSRDB solar (GHI)", {})[cond] = \
                            l2_normalise(A[sel])
    a_, b_ = res.get("glo_clear"), res.get("glo_cloudy")
    if a_ and b_:
        res["clear_vs_cloudy_eps_ratio"] = b_["eps"] / max(a_["eps"], 1e-12)
        print(f"    despejados eps {a_['eps']:.4f}+-{a_['eps_sd']:.4f} "
              f"(n={a_['n_available']})   cubiertos {b_['eps']:.4f}"
              f"+-{b_['eps_sd']:.4f} (n={b_['n_available']})   "
              f"cociente {res['clear_vs_cloudy_eps_ratio']:.1f}x", flush=True)

    jdump(res, f"{out}/solar.json")
    with open(f"{out}/table_solar.tex", "w") as f:
        f.write("\\begin{tabular}{llrrrr}\n\\toprule\n"
                "variable & sky & days & $\\varepsilon$ & $|S|$ & "
                "compression \\\\\n\\midrule\n")
        for var, vn in (("glo", "GHI"), ("kt", "$K_t$")):
            for cond, cn in (("clear", "clear"), ("cloudy", "overcast"),
                             ("all", "all")):
                r = res.get(f"{var}_{cond}")
                if r:
                    f.write(f"{vn} & {cn} & {r['n_available']} & "
                            f"${r['eps']:.4f} \\pm {r['eps_sd']:.4f}$ & "
                            f"${r['S']:.1f}$ & "
                            f"${r['compression']:.1f}\\times$ \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n"
                "% The split is declared by the data: NSRDB total cloud cover.\n")
    return res


def _conv_eps(A, tag):
    """Within-set median distance, from a capped pool. See CONV_EPS_POOL."""
    from scipy.spatial.distance import cdist
    k = min(CONV_EPS_POOL, len(A))
    g = np.random.default_rng(seed_for(SEED, tag, "conv-eps"))
    P = A[g.choice(len(A), k, replace=False)]
    w = cdist(P, P, "cosine")
    return float(np.median(w[np.triu_indices(k, 1)]))


def crossings(steps, curve, r_inf, fracs=(0.10, 0.05, 0.01)):
    """Cuantas realizaciones para quedar dentro de f del limite, y quedarse.

    Reemplaza al n_sat con umbral, que dependia de un criterio que el codigo y
    la prosa no compartian (2% con ventana 3 contra 5% con dos pasos). Aqui el
    limite es r_true -- el radio contra el centroide de TODO el conjunto, no el
    ultimo punto de la grilla -- y se exige que la curva entre y NO vuelva a
    salir, para que un cruce afortunado temprano no cuente.
    """
    if not steps or r_inf <= 0:
        return {}
    rel = [abs(v - r_inf) / r_inf for v in curve]
    out = {}
    for f in fracs:
        hit = None
        for i in range(len(steps)):
            if all(rel[j] <= f for j in range(i, len(steps))):
                hit = steps[i]; break
        out[f"within_{int(f*100)}pct"] = hit
    return out


def _conv_one(A, eps, greedy_net, tag, n_pool=None):
    """Two convergence curves for one concept, on the same draws.

    (a) THE GAP. The observer estimates the radius of its own class from the n
        encounters it has had, and we also measure that same radius on
        encounters it has never had. Early on the first is too small -- the
        centre is fitted to the very points it is measured against -- and the
        second is too large. Both land on the radius computed from all the
        data. What converges is the ESTIMATE, not the data: the class radius is
        a constant of the phenomenon and never moves. What the closing gap
        says is that the observer can no longer tell what it has seen from
        what it has not, which is the generalisation gap measured with no
        classifier, no labels, no training and no loss.

    (b) THE COVER. How far a new encounter falls from the nearest exemplar the
        observer actually kept. This needs no centre at all. The distinction
        matters: the centroid of (a) is a point that need not lie in the class
        -- the average of dogs may be no dog -- while every point in (b) is
        something that was really encountered.
    """
    from scipy.spatial.distance import cdist
    c_all = A.mean(0, keepdims=True)
    r_true = float(cdist(A, c_all, "cosine").mean())
    steps = [n for n in CONV_STEPS
             if n + CONV_HELD_MIN <= len(A) and n <= CONV_NMAX]
    out = {k: [] for k in ("r_mean", "r_max", "bbox", "n_net")}
    for n in steps:
        acc = {k: [] for k in out}
        for rep in range(reps_for(n)):
            g = np.random.default_rng(seed_for(SEED, tag, "conv", n, rep))
            p = g.permutation(len(A))
            S, H = A[p[:n]], A[p[n:n + CONV_HELD]]
            ch = S.mean(0, keepdims=True)
            idx, _ = greedy_net(S, eps)
            acc["n_net"].append(len(idx))
            # --- the four curves of the saturation figure -------------------
            # Same four quantities as blueprints.intelligent.saturation_curve,
            # with two corrections. The radius is measured on realisations the
            # centre never saw, which removes the small-sample bias of a
            # centroid fitted to the very points it is scored against. And all
            # four use the cosine metric, the one the rest of the paper
            # declares: the original mixed euclidean for the radius with
            # cosine for the Hausdorff on the same axes.
            D = cdist(H, ch, "cosine")
            acc["r_mean"].append(float(D.mean()))
            acc["r_max"].append(float(D.max()))
            acc["bbox"].append(float(np.sum(S.max(0) - S.min(0))))
        for k in out:
            out[k].append([float(np.mean(acc[k])), float(np.std(acc[k]))])
    return {"steps": steps, "eps": float(eps), "r_true": r_true,
            "crossings": crossings(steps, [v[0] for v in out["r_mean"]], r_true),
            "reps_per_step": {str(n): reps_for(n) for n in steps},
            "n_available": int(len(A)),
            # how many realisations the concept HAS, before this stage capped
            # the measurement at CONV_NMAX. For a domain read whole the two
            # agree; for the ECG they do not, and a column headed "available"
            # that silently reported the cap was the defect this fixes.
            "n_pool": int(n_pool if n_pool is not None else len(A)), **out}



def _conv_aggregate(per, keys):
    """Average the curves of several subsets of one domain.

    Ten digit classes, nine tidal stations: in both cases the concept is the
    subset and the domain is the collection of them, so the domain's curve is
    the mean over subsets and the band is their spread.
    """
    steps = min((per[k]["steps"] for k in keys), key=len)
    agg = {"steps": steps,
           "r_true": float(np.mean([per[k]["r_true"] for k in keys])),
           "eps": float(np.mean([per[k]["eps"] for k in keys])),
           "n_available": int(np.mean([per[k]["n_available"] for k in keys])),
           "n_pool": int(np.mean([per[k].get("n_pool", per[k]["n_available"])
                                  for k in keys])),
           "n_concepts": len(keys)}
    for q in ("r_mean", "r_max", "bbox", "n_net"):
        agg[q] = [[float(np.mean([per[k][q][i][0] for k in keys])),
                   float(np.std([per[k][q][i][0] for k in keys]))]
                  for i in range(len(steps))]
    # Los cruces tambien para el agregado. Sin esto el JSON traia el campo solo
    # en los dominios simples, y un lector -- o yo mismo -- toma la ausencia de
    # la clave por "nunca cruza", que es un error distinto y peor.
    agg["crossings"] = crossings(steps, [v[0] for v in agg["r_mean"]],
                                 agg["r_true"])
    agg["per_subset"] = per
    return agg


def stage_pm_populations(root, out):
    """The four nominal point-machine populations, and why they go in together.

    Section 7.1 has always reported 8788 nominal records. Those are four
    manoeuvres -- two machines, two directions -- and until v8 the package
    measured only one of them. They are pooled now, and this stage is the
    evidence for that decision rather than an argument for it.

    Two things are measured.

    (a) EACH POPULATION WITH ITS OWN RULER. The four tolerances differ by
        about 3x, and the pooled tolerance is larger than all four, because
        epsilon is a median WITHIN the set and pooling makes it the median of
        a mixture. This is why |S| for the pooled set cannot be compared with
        |S| for one population: the ruler changed length. Stated plainly so
        that no reader has to discover it.

    (b) EVERY SET AGAINST EVERY RULER. This is the one that decides. If the
        four populations were four different manifolds, covering their union
        at a fixed tolerance would cost about the SUM of the four. It costs
        between 1.06 and 1.25 times the LARGEST single population, at every
        one of the five tolerances. Four times the data, a tenth more
        exemplars. The four overlap almost entirely: they are one set.

    Read the cross-tabulation down a column, never across a row. A column is
    one tolerance applied to every set, which is the only comparison that
    means anything; a row mixes five different rulers.
    """
    from run_experiment import l2_normalise, net_sizes_over_eps
    _, _, pm = load_physical(root)

    P = {n: pm("kaggle_nominal", sets=(n,)) for n in PM_SETS}
    POOL = np.concatenate([P[n] for n in PM_SETS])
    TAG = "PM real (nominal)"          # the seed stage_physical uses
    order = list(PM_SETS) + ["POOLED"]
    sets = {**P, "POOLED": POOL}

    def ruler(X):
        n = min(NMAX_PHYS, len(X))
        eps_d, s_d = [], []
        for rep in range(SUBSAMPLES):
            rng = np.random.default_rng(seed_for(SEED, TAG, "subsample", rep))
            A = l2_normalise(X[rng.choice(len(X), n, replace=False)])
            D = 1 - A @ A.T
            e = float(np.median(D[np.triu_indices(n, 1)]))
            eps_d.append(e)
            s_d.append(float(net_sizes_over_eps(A, [e], ORDERS, SEED).mean()))
        return {"n": n, "n_available": int(len(X)),
                "eps": float(np.mean(eps_d)), "eps_sd": float(np.std(eps_d)),
                "S": float(np.mean(s_d)), "S_sd": float(np.std(s_d))}

    def net_at(X, eps):
        n = min(NMAX_PHYS, len(X))
        v = []
        for rep in range(SUBSAMPLES):
            rng = np.random.default_rng(seed_for(SEED, TAG, "subsample", rep))
            A = l2_normalise(X[rng.choice(len(X), n, replace=False)])
            v.append(float(net_sizes_over_eps(A, [eps], ORDERS, SEED).mean()))
        return float(np.mean(v)), float(np.std(v))

    def radius_curve(X):
        """Radius on realisations the centre never saw. _conv_one, radius only."""
        A = l2_normalise(X)
        c = A.mean(0, keepdims=True)
        c = c / max(float(np.linalg.norm(c)), 1e-12)
        r_true = float((1 - A @ c.T).mean())
        steps = [k for k in CONV_STEPS if k + CONV_HELD_MIN <= len(A) and k <= 2000]
        rows = []
        for k in steps:
            acc = []
            for rep in range(CONV_REPS):
                g = np.random.default_rng(seed_for(SEED, TAG, "conv", k, rep))
                pmt = g.permutation(len(A))
                S, H = A[pmt[:k]], A[pmt[k:k + CONV_HELD]]
                ch = S.mean(0, keepdims=True)
                ch = ch / max(float(np.linalg.norm(ch)), 1e-12)
                acc.append(float((1 - H @ ch.T).mean()))
            rows.append([float(np.mean(acc)), float(np.std(acc))])
        return {"steps": steps, "r_true": r_true, "r_mean": rows}

    print("  reglas propias", flush=True)
    R = {k: ruler(sets[k]) for k in order}
    eps_ind = [R[k]["eps"] for k in PM_SETS]

    print("  tabla cruzada", flush=True)
    X = {k: [net_at(sets[k], R[r]["eps"])[0] for r in order] for k in order}

    print("  convergencia", flush=True)
    C = {k: radius_curve(sets[k]) for k in order}

    res = {"rulers": order, "own": R, "cross": X, "convergence": C,
           "eps_spread": float(max(eps_ind) / min(eps_ind)),
           "eps_pooled_over_max": float(R["POOLED"]["eps"] / max(eps_ind))}
    jdump(res, f"{out}/pm_populations.json")

    def pretty(k):
        if k == "POOLED":
            return "all four"
        m, _, d = k.partition("_")
        return m + " " + d.replace("_", " ").replace("to", "$\\to$")

    # --- table 1: each population on its own terms ---------------------------
    with open(f"{out}/table_pm_populations.tex", "w") as f:
        f.write("\\begin{tabular}{lrrr" + "r" * len(CONV_AT) + "}\n\\toprule\n"
                "& & & & \\multicolumn{" + str(len(CONV_AT)) + "}{c}{how far the "
                "radius still is from where it settles} \\\\\n"
                f"\\cmidrule(lr){{5-{4 + len(CONV_AT)}}}\n"
                "population & records & $\\varepsilon$ & $|S(\\varepsilon)|$ & "
                + " & ".join(f"$n{{=}}{k}$" for k in CONV_AT) + " \\\\\n\\midrule\n")
        for k in order:
            if k == "POOLED":
                f.write("\\midrule\n")
            c, cells = C[k], []
            for at in CONV_AT:
                if at in c["steps"] and c["r_true"]:
                    v = c["r_mean"][c["steps"].index(at)][0]
                    cells.append(f"{100 * abs(v - c['r_true']) / c['r_true']:.1f}\\%")
                else:
                    cells.append("--")
            f.write(f"{pretty(k)} & {R[k]['n_available']} & {R[k]['eps']:.4f} & "
                    f"{R[k]['S']:.2f} & " + " & ".join(cells) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
        f.write("% Each row uses its OWN epsilon, so the |S| column is not comparable\n"
                "% across rows. That is what the cross-tabulation is for.\n")

    # --- table 2: the cross-tabulation -------------------------------------
    with open(f"{out}/table_pm_crosstab.tex", "w") as f:
        f.write("\\begin{tabular}{l" + "r" * len(order) + "}\n\\toprule\n"
                "& \\multicolumn{" + str(len(order)) + "}{c}{$|S|$ at the tolerance of} "
                "\\\\\n"
                f"\\cmidrule(lr){{2-{1 + len(order)}}}\n"
                "set & " + " & ".join(pretty(k) for k in order) + " \\\\\n"
                "& " + " & ".join(f"{R[k]['eps']:.4f}" for k in order)
                + " \\\\\n\\midrule\n")
        for k in order:
            if k == "POOLED":
                f.write("\\midrule\n")
            f.write(f"{pretty(k)} & " + " & ".join(f"{v:.2f}" for v in X[k])
                    + " \\\\\n")
        f.write("\\midrule\n")
        f.write("sum of the four & " + " & ".join(
            f"{sum(X[s][j] for s in PM_SETS):.2f}" for j in range(len(order)))
            + " \\\\\n")
        f.write("all four / largest & " + " & ".join(
            f"{X['POOLED'][j] / max(X[s][j] for s in PM_SETS):.2f}"
            for j in range(len(order))) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
        f.write("% Read DOWN a column: one tolerance applied to every set. A row\n"
                "% mixes five different rulers and means nothing.\n"
                "% Four different manifolds would put the union near the sum.\n")

    print(f"    epsilon spread {res['eps_spread']:.2f}x ; pooled/max "
          f"{res['eps_pooled_over_max']:.2f}x ; all-four/largest "
          + ", ".join(f"{X['POOLED'][j] / max(X[s][j] for s in PM_SETS):.2f}"
                      for j in range(len(order))), flush=True)
    return res


def _conv_extra_cache(out, save):
    """Tides and solar reach stage_convergence through CONV_EXTRA, a module
    global that stage_tides and stage_solar fill as they run.

    That is fine in a full run and silently wrong in a partial one: rerun the
    convergence stage alone and the global is empty, so the two domains vanish
    from convergence.json and from the summary table without a word. They did
    exactly that once. The realisations are therefore written to the run's
    cache when they are produced and read back when they are not, and if
    neither happens the stage says so loudly instead of quietly measuring
    eight domains where the paper reports ten.
    """
    path = os.path.join(out, "cache", "conv_extra.npz")
    if save:
        if not CONV_EXTRA:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        flat = {f"{lab}||{sub}": X
                for lab, subs in CONV_EXTRA.items() for sub, X in subs.items()}
        np.savez_compressed(path, **flat)
        return
    if CONV_EXTRA or not os.path.exists(path):
        return
    z = np.load(path)
    for k in z.files:
        lab, _, sub = k.partition("||")
        CONV_EXTRA.setdefault(lab, {})[sub] = z[k]
    print(f"    CONV_EXTRA recuperado de cache: "
          f"{', '.join(f'{k} ({len(v)})' for k, v in CONV_EXTRA.items())}",
          flush=True)


def stage_convergence(root, out, cache):
    """When does an observer stop learning anything new about a concept?

    Reported for every physical domain and, averaged over the ten classes, for
    both digit sets. The quantity that carries the claim is the RADIUS,
    measured on realisations the observer has not seen. No convergence
    threshold is applied: the curve is reported and the convergence is read
    from it.
    """
    from scipy.spatial.distance import cdist
    from run_experiment import l2_normalise, z_normalise, greedy_net
    from sklearn.datasets import load_digits

    Q = {"l2": l2_normalise, "znorm": z_normalise}
    res = {"reps": CONV_REPS, "held_out": CONV_HELD,
           "domains": {}, "digits": {}}

    _conv_extra_cache(out, save=False)
    if not CONV_EXTRA:
        print("    AVISO: sin mareas ni solar. Se estan midiendo ocho dominios,\n"
              "           no diez. Corre las etapas tides y solar antes, o usa\n"
              "           --restage convergence, que ya lo hace.", flush=True)

    DOM, _, _ = load_physical(root)
    for nm, (A, q) in DOM.items():
        n = min(CONV_NMAX + CONV_HELD, len(A))
        rng = np.random.default_rng(seed_for(SEED, nm, "conv-subsample"))
        X = Q[q](A[rng.choice(len(A), n, replace=False)])
        res["domains"][nm] = _conv_one(X, _conv_eps(X, nm), greedy_net, nm,
                                       n_pool=len(A))
        r = res["domains"][nm]
        print(f"    {nm:22s} n<={r['steps'][-1]:<6d}   radio "
              f"{r['r_mean'][0][0]:.4f} -> {r['r_mean'][-1][0]:.4f}"
              f"   (converge a {r['r_true']:.4f})", flush=True)

    sets = {"UCI digits 8x8": load_digits(return_X_y=True)}
    if cache and os.path.exists(cache):
        z = np.load(cache)
        sets["MNIST 28x28"] = (z["X"], z["y"])
    # Spoken digits. A different sense, the same construction: ten concepts,
    # one manifold each, the same radius measured the same way. The claim is
    # NOT that a spoken 8 and a written 8 are the same thing -- they share a
    # label and nothing else here. It is that the geometry behaves the same
    # way in a modality that has nothing to do with pixels.
    spoken = _find_dir(root, SPOKEN_DIR)
    spoken_cache = os.path.join(out, "cache", "spoken.npz")
    # The wav directory sits outside the dataset root on some machines. The
    # cache holds the raw declared observable and is hashed in the manifest
    # like any other input, so it is a legitimate source -- but which source
    # was used is printed, because a stage that silently reads a cache when
    # the data is gone is how a curve disappears from a nine-curve paper.
    if spoken or os.path.exists(spoken_cache):
        try:
            from audio_mnist import load_spoken, duration_stats
            Xa, ya, _ = load_spoken(spoken, spoken_cache)
            sets["Spoken digits (FSDD)"] = (Xa, ya)
            print("    spoken MNIST desde " +
                  ("los wav" if spoken else "el cache del run"), flush=True)
            # The four duration figures Section 6.4 quotes were measured and
            # never stored, so they were the only numbers in the paper that had
            # to be recomputed by hand to be checked. They are stored now, from
            # the padded arm, which is what the sentence is about.
            try:
                zc = np.load(spoken_cache)
                res["spoken_duration"] = duration_stats(zc["X"], zc["y"])
            except Exception as e:
                print(f"    duraciones omitidas: {type(e).__name__}: {e}",
                      flush=True)
        except Exception as e:
            print(f"    spoken MNIST omitido: {type(e).__name__}: {e}",
                  flush=True)
    else:
        print(f"    spoken MNIST omitido: no encuentro {SPOKEN_DIR} "
              f"ni {spoken_cache}", flush=True)
    for label, (X0, y0) in sets.items():
        per = {}
        for c in range(10):
            A = l2_normalise(np.asarray(X0[y0 == c], float))
            tag = f"{label}|{c}"
            per[str(c)] = _conv_one(A, _conv_eps(A, tag), greedy_net, tag)
        # the concept is the digit; the domain is the average over the ten
        agg = _conv_aggregate(per, [str(c) for c in range(10)])
        res["digits"][label] = agg
        print(f"    {label:22s} n<={agg['steps'][-1]:<6d}   radio "
              f"{agg['r_mean'][0][0]:.4f} -> {agg['r_mean'][-1][0]:.4f}",
              flush=True)

    # Tides and solar, measured with the same code and reported in the same
    # table as everything else. Their realisations were built by their own
    # stages; nothing is re-derived here.
    for label, subsets in CONV_EXTRA.items():
        per = {}
        for k, X in subsets.items():
            tag = f"{label}|{k}"
            per[k] = _conv_one(np.asarray(X, float), _conv_eps(X, tag),
                               greedy_net, tag)
        if not per:
            continue
        agg = _conv_aggregate(per, list(per))
        res["domains"][label] = agg
        print(f"    {label:22s} n<={agg['steps'][-1]:<6d}   radio "
              f"{agg['r_mean'][0][0]:.4f} -> {agg['r_mean'][-1][0]:.4f}"
              f"   ({len(per)} subconjuntos)", flush=True)

    jdump(res, f"{out}/convergence.json")

    _conv_extra_cache(out, save=True)
    emit_saturation_table(out)
    return res


def emit_saturation_table(out):
    """The cross-domain summary of section 7.7, from convergence.json.

    It quotes no saturation point, because this work does not claim a
    criterion for one. What it reports is how far the radius still is from the
    value it settles on, at a few fixed sample sizes -- a measurement, not a
    threshold, and comparable across domains.

    Two things this reports that the first version did not, both of which a
    reader would otherwise have had to reconstruct.

    (a) THE SPREAD BESIDE THE RESIDUAL. Several rows are not monotone: the
        battery is 0.8% off at n=20 and 2.5% off at n=200. Printed alone that
        reads as the measurement getting worse with more data. It is not. The
        spread over independent draws at those sample sizes is 10% and 14%, so
        the residual is well inside the noise and the ordering between two
        such cells means nothing. That is the strongest form of the claim --
        past n=20 the estimate is unbiased to within its own scatter -- and it
        can only be read if the spread is on the page.

        The spread means two different things and the table says which. For a
        domain measured as one set it is the scatter over CONV_REPS
        independent draws. For a domain averaged over concepts -- ten digit
        classes, nine tidal stations -- it is the scatter ACROSS CONCEPTS, and
        it is large (60% for the tides) because Anchorage and Honolulu have
        genuinely different radii. Those two numbers are not comparable and
        are marked differently.

    (b) HOW MANY RECORDS, AND OF WHAT. The old column headed "available" mixed
        three meanings: the whole domain for the point machine (8788), the
        measurement CAP for the ECG (20200, of 100953 actually held), and the
        per-class count for MNIST (7000) and the spoken digits (300). A reader
        comparing 8788 with 300 would conclude something false. It is now
        split: how many concepts the row averages, how many records each
        concept has, and how far up in n the measurement actually went.
    """
    d = json.load(open(f"{out}/convergence.json"))
    todo = {**d.get("domains", {}), **d.get("digits", {})}
    with open(f"{out}/table_saturation_summary.tex", "w") as f:
        f.write("\\begin{tabular}{lrrrr" + "r" * len(CONV_AT) + "}\n\\toprule\n"
                "& & records & measured & settles & \\multicolumn{"
                + str(len(CONV_AT)) + "}{c}{residual \\% (spread \\%)} \\\\\n"
                f"\\cmidrule(lr){{6-{5 + len(CONV_AT)}}}\n"
                "domain & concepts & each & up to & at & "
                + " & ".join(f"$n{{=}}{k}$" for k in CONV_AT)
                + " \\\\\n\\midrule\n")
        for nm in sorted(todo):
            r = todo[nm]
            st = list(r["steps"])
            rm = r["r_mean"]
            fin = r["r_true"]
            nc = int(r.get("n_concepts", 1))
            pool = int(r.get("n_pool", r["n_available"]))
            cells = []
            for k in CONV_AT:
                if k in st and fin:
                    m, sd = rm[st.index(k)]
                    cells.append(f"{100 * abs(m - fin) / fin:.1f} "
                                 f"({100 * sd / fin:.0f})")
                else:
                    cells.append("--")
            f.write(f"{nm} & {nc} & {pool} & {st[-1]} & {fin:.4f} & "
                    + " & ".join(cells) + " \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
        f.write("% 'settles at' is the radius over every realisation the row uses.\n"
                "% Radii are measured on realisations the observer has not seen.\n"
                "% residual = |r_n - settled| / settled.\n"
                "% spread, concepts=1: scatter over independent draws at that n.\n"
                "% spread, concepts>1: scatter ACROSS concepts -- a different\n"
                "%   quantity, and large where the concepts genuinely differ.\n"
                "% 'records each' is per concept, before the measurement cap;\n"
                "%   'measured up to' is the largest n actually reached.\n"
                "% '--' means the row has no measurement at that n.\n")


def stage_figures(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BLUE, G1, G2, G3 = "#2a78d6", "#c9c9c6", "#9a9a97", "#676764"
    INK, MUTED, GRID, SURF = "#1a1a19", "#6b6b68", "#e2e2df", "#fcfcfb"

    d = json.load(open(f"{out}/surrogate_test.json"))
    names = list(d)
    fig, ax = plt.subplots(figsize=(10.6, 4.6))
    ax.set_facecolor(SURF); ax.grid(True, axis="y", color=GRID, lw=.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    x = np.arange(len(names)); w = .20
    for j, (key, col, lbl) in enumerate([
            ("real", BLUE, "real process"),
            ("shuffle", G1, "shuffle  (amplitudes only)"),
            ("ft", G2, "FT  (+ power spectrum)"),
            ("iaaft", G3, "IAAFT  (+ spectrum \\& marginal)")]):
        v = np.array([d[k][key] for k in names])
        ax.bar(x + (j - 1.5) * w, v, width=w * .92, color=col, zorder=3,
               edgecolor=SURF, linewidth=1.4, label=lbl)
        if key == "real":
            for xi, vi in zip(x, v):
                ax.text(xi - 1.5 * w, vi * 1.12, f"{vi:.0f}", ha="center",
                        color=BLUE, fontsize=9.5, fontweight="bold", zorder=4)
    for xi, k in zip(x, names):
        ax.text(xi + 1.5 * w, d[k]["iaaft"] * 1.10,
                f"{d[k]['compression_vs_iaaft']:.0f}x", ha="center", color=INK,
                fontsize=9.5, fontweight="bold", zorder=4)
    ax.set_yscale("log"); ax.set_ylim(1.5, 3000)
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=8.6,
                       color=MUTED)
    ax.set_ylabel(r"exemplars stored  $|S(\varepsilon)|$", color=INK, fontsize=10)
    ax.set_title("The real process needs 3-26 exemplars. Every surrogate needs all "
                 "of them.", color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=8.8, labelcolor=MUTED, loc="upper left", ncol=2)
    fig.tight_layout()
    savefig(fig, f"{out}/fig_surrogates.png")
    plt.close(fig)

    # ---- the dimension estimator, shown against its own calibration --------
    dm = json.load(open(f"{out}/dimension.json"))
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4))
    for ax in axes:
        ax.set_facecolor(SURF); ax.grid(True, color=GRID, lw=.8, zorder=0)
        ax.set_axisbelow(True)
        for sp in ("top", "right"): ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"): ax.spines[sp].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=9)

    ax = axes[0]
    true_d = [1, 2, 3, 4, 5, 6]
    ax.plot(true_d, true_d, ls="--", lw=1.2, color=MUTED, zorder=2)
    ax.annotate("unbiased", (6, 6), textcoords="offset points", xytext=(-52, 4),
                color=MUTED, fontsize=8.5)
    shades = [G1, G2, G3, BLUE]
    for i, (n, c) in enumerate(sorted(dm["calibration"].items(),
                                      key=lambda kv: int(kv[0]))):
        est = [c[str(d)]["estimate"] for d in true_d]
        col = shades[min(i, len(shades) - 1)]
        ax.plot(true_d, est, "-o", color=col, lw=2, ms=5, zorder=3,
                markeredgecolor=SURF, markeredgewidth=1.4, label=f"$n={n}$")
    ax.set_xlabel("true dimension of $S^d$", color=INK, fontsize=10)
    ax.set_ylabel(r"estimated $\hat{d}$", color=INK, fontsize=10)
    ax.set_title("A \u00b7 The estimator, calibrated against known manifolds",
                 color=INK, fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, labelcolor=MUTED, loc="upper left")

    ax = axes[1]
    items = [(k, v["dim"], v["stderr"]) for k, v in dm["domains"].items()
             if not np.isnan(v["dim"])]
    na = [k for k, v in dm["domains"].items() if np.isnan(v["dim"])]
    items.sort(key=lambda t: t[1])
    ypos = np.arange(len(items))
    ax.barh(ypos, [t[1] for t in items], xerr=[t[2] for t in items],
            color=BLUE, height=.55, zorder=3, error_kw=dict(ecolor=INK, lw=1.2))
    ax.set_yticks(ypos)
    ax.set_yticklabels([t[0] for t in items], fontsize=9, color=MUTED)
    for yi, (_, d, _) in zip(ypos, items):
        ax.text(d + .06, yi, f"{d:.2f}", va="center", color=INK, fontsize=9.5,
                fontweight="bold", zorder=4)
    lab = r"$\hat{d}$   (lower bound; see panel A)"
    if na:
        lab += "\nnot reported, sample too small: " + ", ".join(na)
    ax.set_xlabel(lab, color=INK, fontsize=10)
    ax.set_title("B \u00b7 Measured, physical domains", color=INK, fontsize=11,
                 loc="left")
    ax.grid(False, axis="y")
    ax.set_xlim(0, max(t[1] + t[2] for t in items) * 1.18)
    ax.set_ylim(-.6, len(items) - .4)
    fig.tight_layout()
    savefig(fig, f"{out}/fig_dimension.png")
    plt.close(fig)

    # ---- the central figure: what settles and what does not ---------------
    # Each of the three remaining figures is attempted independently. An
    # earlier version returned as soon as one of them failed, so a single
    # missing module in src/ silently took the other two down with it -- which
    # is exactly what happened: figure_convergence.py was absent on one machine
    # and fig_saturation.png never appeared either, with no message saying why.
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "src"))
    figs = ["fig_surrogates.png", "fig_dimension.png"]
    root = DATA_ROOT_FOR_FIGS[0]

    try:
        from figure_convergence import build as _conv
        _conv(out, f"{out}/fig_convergence.png")
        figs.append("fig_convergence.png")
    except Exception as e:
        print(f"    fig_convergence omitida: {type(e).__name__}: {e}", flush=True)
    try:
        from figure_exemplars import build as _ex
        _ex(root, f"{out}/fig_exemplars.png")
        figs.append("fig_exemplars.png")
    except Exception as e:
        print(f"    fig_exemplars omitida: {type(e).__name__}: {e}", flush=True)
    try:
        from figure_saturation_grid import build as _grid
        _grid(out, f"{out}/fig_saturation_grid.png")
        figs.append("fig_saturation_grid.png")
    except Exception as e:
        print(f"    fig_saturation_grid omitida: {type(e).__name__}: {e}",
              flush=True)
    try:
        from figure_saturation import build as _sat
        info = _sat(out, f"{out}/fig_saturation.png")
        jdump(info, f"{out}/saturation.json")
        figs.append("fig_saturation.png")
    except Exception as e:
        print(f"    fig_saturation omitida: {type(e).__name__}: {e}", flush=True)

    contact_sheet(out, figs)
    return figs


def contact_sheet(out, figs):
    """One page showing every figure the run produced, and naming the ones it
    did not. Reading a figure means seeing it; a directory listing of PNGs is
    not seeing it."""
    missing = [f for f in ("fig_surrogates.png", "fig_dimension.png",
                           "fig_convergence.png", "fig_exemplars.png",
                           "fig_saturation.png") if f not in figs]
    rows = "\n".join(
        f'<figure><figcaption>{f}</figcaption>'
        f'<img src="{f}" alt="{f}"></figure>' for f in figs)
    warn = ("" if not missing else
            '<p class="warn">No se generaron: ' + ", ".join(missing) +
            ' &mdash; mirar el mensaje "omitida" en la consola.</p>')
    html = f"""<!doctype html><meta charset="utf-8">
<title>figuras &middot; {os.path.basename(os.path.abspath(out))}</title>
<style>
 body{{background:#fcfcfb;color:#1a1a19;font:15px/1.5 -apple-system,sans-serif;
      margin:0 auto;padding:32px;max-width:1100px}}
 h1{{font-size:19px;font-weight:600;margin:0 0 4px}}
 .sub{{color:#6b6b68;font-size:13px;margin:0 0 28px}}
 figure{{margin:0 0 34px}}
 figcaption{{color:#6b6b68;font-size:12px;font-family:ui-monospace,monospace;
             margin-bottom:6px}}
 img{{width:100%;border:1px solid #e2e2df;border-radius:3px;display:block}}
 .warn{{background:#fdf1ea;border-left:3px solid #eb6834;padding:10px 14px;
        margin:0 0 28px;font-size:13px}}
</style>
<h1>Figuras de {os.path.basename(os.path.abspath(out))}</h1>
<p class="sub">{len(figs)} de 5. Generado por reproduce.py.</p>
{warn}
{rows}
"""
    with open(f"{out}/figuras.html", "w") as f:
        f.write(html)
    print(f"    contact sheet: {out}/figuras.html  ({len(figs)}/5)", flush=True)


def input_manifest(root, cache):
    """Content hash of every INPUT, not just every output.

    Two machines running the same command got different numbers because one
    copy of the point-machine nominal set had 50 records and the other had 600.
    Nothing in the output manifest could show that: it hashed only what we
    produced. A run that cannot prove what it read is not reproducible, it is
    merely repeatable on one machine.
    """
    import pandas as pd
    inp = {}

    def add(key, A):
        A = np.asarray(A)
        inp[key] = {"shape": list(A.shape), "sha256": array_sha(A.astype(np.float64))}

    for rel in ("pm/mc_pm_dataset.npy",
                "ecg/field_ecg_dataset_aligned_normalized.npy",
                "ecg/mc_ecg_gaussian_dataset.npy",
                "batteries/field_discharges_dataset.npy"):
        f = os.path.join(root, rel)
        add(rel, np.load(f)) if os.path.exists(f) else inp.update({rel: "MISSING"})

    mit = sorted(glob.glob(f"{root}/ecg/mitdb/*.dat"))
    inp["ecg/mitdb"] = ({"records": len(mit),
                         "sha256": hashlib.sha256(
                             "".join(sha(f) for f in mit).encode()).hexdigest()}
                        if mit else "MISSING")

    for pat in ("kaggle_nominal", "kaggle_anomalous"):
        files = sorted(glob.glob(f"{root}/pm/{pat}/J1_normal_to_reverse_*.parquet"))
        if not files:
            inp[f"pm/{pat}"] = "MISSING"
            continue
        h = hashlib.sha256()
        for f in files:
            h.update(os.path.basename(f).encode())
            h.update(pd.read_parquet(f)["Power"].to_numpy(np.float64).tobytes())
        inp[f"pm/{pat}"] = {"n_files": len(files), "sha256": h.hexdigest()}

    if os.path.exists(cache):
        z = np.load(cache)
        add("mnist (cached)", z["X"])
    else:
        inp["mnist (cached)"] = "ABSENT"
    return inp


def manifest(out, inputs=None):
    files = sorted(os.path.relpath(p, out)
                   for p in glob.glob(f"{out}/**/*", recursive=True)
                   if os.path.isfile(p) and not p.endswith("MANIFEST.json")
                   and "/cache/" not in p)
    # Hash ONLY the modules this run actually imported. Hashing every file in
    # src/ would mean that deleting dead code -- code that produced no number in
    # this run -- registers as a code change and makes two runs incomparable.
    here = os.path.dirname(os.path.abspath(__file__))
    srcdir = os.path.join(here, "src")
    code = {"reproduce.py": sha(os.path.abspath(__file__))}
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and os.path.dirname(os.path.abspath(f)) == srcdir:
            code[f"src/{os.path.basename(f)}"] = sha(f)

    m = {"seed": SEED, "orders": ORDERS, "reps": REPS, "code": code,
         "subsamples": SUBSAMPLES, "nmax_phys": NMAX_PHYS,
         "n_grid": N_GRID, "eps_mnist": EPS_MNIST, "budgets": BUDGETS,
         "numpy": np.__version__, "python": sys.version.split()[0],
         "inputs": inputs or {},
         "files": {f: sha(os.path.join(out, f)) for f in files}}
    jdump(m, f"{out}/MANIFEST.json")
    return m


def publish(run, here):
    """Copy a run's tables and figures to paper/generated/.

    One path from data to paper. The paper never reads a loose file from the
    working tree: it \\input{}s only from paper/generated/, and what is in
    paper/generated/ came from exactly one run, named in SOURCE.json together
    with the hash of that run's manifest. A number in the PDF can always be
    traced back to the run that produced it.
    """
    import shutil
    dest = os.path.join(here, "paper", "generated")
    man = os.path.join(run, "MANIFEST.json")
    if not os.path.exists(man):
        sys.exit(f"{run} no tiene MANIFEST.json")
    M = json.load(open(man))
    os.makedirs(dest, exist_ok=True)
    for f in sorted(os.listdir(dest)):
        if f.endswith((".tex", ".png")):
            os.remove(os.path.join(dest, f))
    taken = []
    for f in sorted(M["files"]):
        if f.endswith((".tex", ".png")):
            shutil.copy2(os.path.join(run, f), os.path.join(dest, f))
            taken.append(f)
    jdump({"run": os.path.basename(os.path.abspath(run)),
           "manifest_sha256": sha(man),
           "inputs": M.get("inputs", {}), "code": M.get("code", {}),
           "files": {f: M["files"][f] for f in taken}},
          os.path.join(dest, "SOURCE.json"))
    print(f"paper/generated/ <- {run}   ({len(taken)} artefactos)")
    for f in taken:
        print(f"  {f}")
    print(f"\nmanifest sha256 {sha(man)[:16]}")


def emit_numbers(out, R):
    """Every number that appears in the PROSE, as a LaTeX macro.

    Tables already come from the pipeline. Sentences did not, and a sentence
    that disagrees with the table beside it is the single most common defect in
    the previous version of this paper. With this file the paper cannot say
    something the run did not produce: the text \\input{}s the same artefact.
    """
    n = {}

    DIGITS = str.maketrans({d: w for d, w in zip(
        "0123456789",
        ["Zero", "One", "Two", "Three", "Four",
         "Five", "Six", "Seven", "Eight", "Nine"])})

    def key(k):
        """A LaTeX control sequence may contain letters only. A macro named
        \\numCalNoneSevenFour with a digit in it silently parses as a shorter
        command followed by stray text, which typesets before \\begin{document}
        and fails with a message that names neither the macro nor the file."""
        return str(k).translate(DIGITS)

    def put(k, v, fmt="{:.3f}"):
        n[key(k)] = fmt.format(v) if isinstance(v, float) else str(v)

    sur = R.get("physical") or {}
    for dom, tag in (("ECG real (MIT-BIH)", "EcgReal"),
                     ("ECG simulated", "EcgSim"),
                     ("PM real (nominal)", "PmReal"),
                     ("PM simulated", "PmSim"),
                     ("Battery real (NASA)", "BatReal")):
        if dom in sur:
            r = sur[dom]
            put(f"S{tag}", r["real"], "{:.1f}")
            put(f"Sd{tag}", r["real_sd"], "{:.1f}")
            put(f"Iaaft{tag}", r["iaaft"], "{:.1f}")
            put(f"Comp{tag}", r["compression_vs_iaaft"], "{:.0f}")
            put(f"Navail{tag}", r["n_available"], "{}")
            put(f"Eps{tag}", r["eps"], "{:.3f}")

    pm = (R.get("pm_anomaly") or {}).get("_operational")
    if pm:
        put("PmDetected", pm["detected_above_p95"], "{:.1f}")
        put("PmDetectedSd", pm["detected_above_p95_sd"], "{:.1f}")
        put("PmAnomalous", pm["n_anomalous"], "{}")
        put("PmSeparation", pm["separation"], "{:.1f}")
        put("PmNominalAvail", pm["n_nominal_available"], "{}")

    pop = R.get("pm_populations") or {}
    if pop:
        put("PmPopSpread", pop["eps_spread"], "{:.2f}")
        put("PmPopEpsOverMax", pop["eps_pooled_over_max"], "{:.2f}")
        put("PmPopEpsPooled", pop["own"]["POOLED"]["eps"], "{:.4f}")
        put("PmPopNavail", pop["own"]["POOLED"]["n_available"], "{}")
        # the ratio the cross-tabulation exists to report: covering the union
        # at a fixed tolerance, against covering its largest single part
        rat = [pop["cross"]["POOLED"][j]
               / max(pop["cross"][k][j] for k in PM_SETS)
               for j in range(len(pop["rulers"]))]
        put("PmPopRatioMin", min(rat), "{:.2f}")
        put("PmPopRatioMax", max(rat), "{:.2f}")

    mn = R.get("mnist") or {}
    if mn:
        for cond, tag in (("raw", "Raw"), ("deskew", "Deskew"),
                          ("blur", "Blur"), ("randshear", "Randshear")):
            if cond in mn:
                put(f"Sep{tag}", _sep_at(mn[cond], N_GRID[-1]), "{:.4f}")
        # The decomposition is what makes the control a control, so the three
        # differences are emitted rather than left for the reader to subtract
        # -- and rather than typed into the prose by hand.
        if all(c in mn for c in ("raw", "deskew", "blur", "randshear")):
            g = {c: _sep_at(mn[c], N_GRID[-1])
                 for c in ("raw", "deskew", "blur", "randshear")}
            put("SepGainResample", 100 * (g["blur"] - g["raw"]), "{:.1f}")
            put("SepGainAlign", 100 * (g["deskew"] - g["blur"]), "{:.1f}")
            put("SepLossAntialign", 100 * (g["raw"] - g["randshear"]), "{:.1f}")

    gt = R.get("gate") or {}
    for dset, tag in (("UCI digits 8x8", "Uci"), ("MNIST 28x28", "Mnist")):
        if dset in gt:
            r = gt[dset]
            j = int(np.argmax(r["ratio"]))
            put(f"GateRatio{tag}", r["ratio"][j], "{:.2f}")
            put(f"GateNper{tag}", r["n_per_class"], "{}")

    dm = R.get("dimension") or {}
    for dom, tag in (("ECG real (MIT-BIH)", "EcgReal"),
                     ("ECG simulated", "EcgSim"),
                     ("PM real (nominal)", "PmReal"),
                     ("PM simulated", "PmSim"),
                     ("Battery real (NASA)", "BatReal")):
        d = (dm.get("domains") or {}).get(dom)
        if d and not np.isnan(d.get("dim", float("nan"))):
            put(f"Dim{tag}", d["dim"], "{:.2f}")
            put(f"DimSd{tag}", d["stderr"], "{:.2f}")
    for nn, c in (dm.get("calibration") or {}).items():
        for dd, v in c.items():
            put(f"CalN{nn}D{dd}", v["estimate"], "{:.2f}")

    lc = ((R.get("learning") or {}).get("datasets") or {})
    for ds, tag in (("MNIST 28x28", "Mnist"), ("UCI digits 8x8", "Uci")):
        for cond, ct in (("raw", "Raw"), ("quotient (deskew)", "Desk")):
            c = (lc.get(ds, {}).get("conditions") or {}).get(cond)
            if not c:
                continue
            for nm, mt in (("linear SVM", "Svm"), ("logistic", "Log"),
                           ("1-NN", "Nn")):
                k = c["knees"].get(nm)
                if not k:
                    continue
                put(f"Lc{tag}{ct}{mt}Knee", k["knee_n"], "{}")
                put(f"Lc{tag}{ct}{mt}Max", k["acc_at_max_n"], "{:.3f}")
                v = k["n_to_reach"].get("0.9")
                n[key(f"Lc{tag}{ct}{mt}NNinety")] = str(v) if v else "never"
            put(f"Lc{tag}{ct}Drift", c["median_drift"] * 100, "{:.1f}")

    op = ((R.get("operating") or {}).get("datasets") or {})
    for ds, tag in (("MNIST 28x28", "Mnist"), ("UCI digits 8x8", "Uci")):
        for cond, ct in (("raw", "Raw"), ("quotient (deskew)", "Desk")):
            c = (op.get(ds, {}).get("conditions") or {}).get(cond)
            if not c:
                continue
            put(f"Op{tag}{ct}Ceiling", c["ceiling_f1"], "{:.3f}")
            put(f"Op{tag}{ct}CeilingSd", c["ceiling_sd"], "{:.3f}")
            b = max(c["curve"], key=lambda r: r["f1"])
            put(f"Op{tag}{ct}Cover", b["set_coverage"], "{:.3f}")
            put(f"Op{tag}{ct}AccUni", b["acc_on_unique"], "{:.3f}")
            put(f"Op{tag}{ct}Unique", b["frac_unique"], "{:.2f}")
            put(f"Op{tag}{ct}Amb", b["frac_ambiguous"], "{:.2f}")
            put(f"Op{tag}{ct}Rej", b["frac_rejected"], "{:.2f}")
            fc = c["forced_choice_best"]
            put(f"Op{tag}{ct}Forced", fc["acc_forced_choice"], "{:.3f}")
            put(f"Op{tag}{ct}ForcedEx", fc["exemplars"], "{:.0f}")
            for t in ("0.8", "0.9"):
                r = c["request"].get(t)
                kk = key(f"Op{tag}{ct}Req{'Eighty' if t == '0.8' else 'Ninety'}")
                n[kk] = f"{r['exemplars']:.0f}" if r else "unreachable"
            # the low-memory point where a set-restricted rule has headroom
            head = [r for r in c["curve"]
                    if r["set_coverage"] > r["acc_forced_choice"]]
            if head:
                h = max(head, key=lambda r: r["set_coverage"] - r["acc_forced_choice"])
                put(f"Op{tag}{ct}HeadEx", h["exemplars"], "{:.0f}")
                put(f"Op{tag}{ct}HeadCover", h["set_coverage"], "{:.3f}")
                put(f"Op{tag}{ct}HeadForced", h["acc_forced_choice"], "{:.3f}")

    td = R.get("tides") or {}
    t = td.get("_test")
    if t:
        put("TideSpearman", t["prereg"]["spearman"], "{:.3f}")
        put("TideP", t["prereg"]["p"], "{:.4f}")
        put("TideSpearmanCorr", t["corrected"]["spearman"], "{:.3f}")
        if "unaligned" in t:
            put("TideSpearmanUnal", t["unaligned"]["spearman"], "{:.3f}")
            put("TidePUnal", t["unaligned"]["p"], "{:.4f}")
        put("TidePCorr", t["corrected"]["p"], "{:.4f}")
        put("TideCriterion", t["criterion"], "{:.1f}")
    # The realisation itself is a declared choice, so the prose quotes it from
    # here rather than from the author's memory of what the constant said.
    put("TidePeriod", TIDE_PERIOD_H, "{:.4f}")
    put("TideLen", TIDE_L, "{}")
    put("TidePre", TIDE_PRE, "{:.2f}")
    for st, tag in (("Boston", "Boston"), ("Anchorage", "Anchorage"),
                    ("Galveston", "Galveston"), ("Honolulu", "Honolulu")):
        v = td.get(st)
        if v:
            put(f"Tide{tag}Range", v["range_m"], "{:.3f}")
            put(f"Tide{tag}Eps", v["prereg"]["eps"], "{:.4f}")
            put(f"Tide{tag}EpsCorr", v["corrected"]["eps"], "{:.4f}")
            put(f"Tide{tag}Bimod", v["bimodality"], "{:.3f}")
            if "unaligned" in v:
                put(f"Tide{tag}EpsUnal", v["unaligned"]["eps"], "{:.4f}")
                put(f"Tide{tag}CompUnal", v["unaligned"]["compression"], "{:.1f}")
    if td:
        n_st = len([k for k in td if not k.startswith("_")])
        put("TideStations", n_st, "{}")
        jumped = len([k for k, v in td.items()
                      if not k.startswith("_") and v.get("bimodality", 0) > 0.555])
        put("TideJumped", jumped, "{}")

    so = R.get("solar") or {}
    for cond, tag in (("clear", "Clear"), ("cloudy", "Cloudy"), ("all", "All")):
        v = so.get(f"glo_{cond}")
        if v:
            put(f"Solar{tag}Eps", v["eps"], "{:.4f}")
            put(f"Solar{tag}N", v["n_available"], "{}")
            put(f"Solar{tag}S", v["S"], "{:.1f}")
            put(f"Solar{tag}Comp", v["compression"], "{:.1f}")
        # the clearness index is quoted in the appendix as a control
        w = so.get(f"kt_{cond}")
        if w:
            put(f"SolarKt{tag}Eps", w["eps"], "{:.4f}")
            put(f"SolarKt{tag}Comp", w["compression"], "{:.1f}")
    if so.get("clear_vs_cloudy_eps_ratio"):
        put("SolarRatio", so["clear_vs_cloudy_eps_ratio"], "{:.1f}")
    # How much of the archive was actually read. A sampled cap that the prose
    # does not state is a cap the reader cannot check.
    if so.get("n_files_read"):
        put("SolarFilesRead", so["n_files_read"], "{}")
        put("SolarFilesFound", so["n_files_found"], "{}")

    put("Subsamples", SUBSAMPLES, "{}")
    put("Orders", ORDERS, "{}")
    put("NmaxPhys", NMAX_PHYS, "{}")

    with open(f"{out}/numbers.tex", "w") as f:
        f.write("% Generated by reproduce.py. Do not edit.\n"
                "% Every number quoted in the prose is defined here, so the text\n"
                "% cannot disagree with the tables beside it.\n")
        for k in sorted(n):
            f.write(f"\\newcommand{{\\num{k}}}{{{n[k]}}}\n")
    print(f"    numbers.tex: {len(n)} macros", flush=True)
    return n


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", default="data",
                   help="carpeta de datos; por defecto ./data, relativa al "
                        "directorio de trabajo, para que un revisor pueda "
                        "clonar el paquete, poner los datos al lado y correr "
                        "sin editar nada. Espera pm/, ecg/, batteries/ "
                        "adentro. Una ruta absoluta tambien sirve.")
    p.add_argument("--out", default="out",
                   help="carpeta de salida; se crea si no existe")
    p.add_argument("--skip-mnist", action="store_true")
    p.add_argument("--compare", nargs=2, metavar=("A", "B"),
                   help="compare two MANIFEST.json and exit")
    p.add_argument("--restage", metavar="NAME",
                   help="re-run ONE stage into an existing --out, leaving the "
                        "rest of the run untouched. For a presentation fix "
                        "that needs the measurement repeated but not the "
                        "whole package: 'convergence' is the one this exists "
                        "for. The manifest is rewritten, so provenance still "
                        "reflects what is on disk.")
    p.add_argument("--figures", metavar="RUN",
                   help="redraw the figures of an existing RUN from its JSON, "
                        "without repeating any measurement, and write "
                        "RUN/figuras.html")
    p.add_argument("--publish", metavar="RUN",
                   help="copy RUN's tables and figures to paper/generated/ "
                        "and record their provenance in SOURCE.json")
    a = p.parse_args()

    if a.publish:
        publish(a.publish,
                os.path.dirname(os.path.abspath(__file__)))
        return

    if a.restage:
        def _restage_convergence(root, out, cache):
            """Convergence needs the tidal and solar realisations, which are
            produced by their own stages. Reload them from the run's cache, and
            if the cache predates it, produce them: measuring eight domains
            where the paper reports ten is not an acceptable silent outcome."""
            _conv_extra_cache(out, save=False)
            if not CONV_EXTRA:
                print("  mareas y solar no estan en cache; se rehacen primero",
                      flush=True)
                stage_tides(root, out)
                stage_solar(root, out)
            return stage_convergence(root, out, cache)

        # Se crea igual que en la corrida completa: un revisor que rehace
        # una sola etapa sobre una carpeta nueva no deberia toparse con
        # un FileNotFoundError en vez de un resultado.
        os.makedirs(a.out, exist_ok=True)
        cache = os.path.join(a.out, "cache", "mnist.npz")
        DATA_ROOT_FOR_FIGS[0] = a.data_root
        table_only = {"saturation_table": lambda: emit_saturation_table(a.out)}
        stages = {
            "convergence": lambda: _restage_convergence(a.data_root, a.out,
                                                        cache),
            "pm_populations": lambda: stage_pm_populations(a.data_root, a.out),
            "pm_anomaly": lambda: stage_pm_anomaly(a.data_root, a.out),
            "ecg_anomaly": lambda: stage_ecg_anomaly(a.data_root, a.out),
            "physical": lambda: stage_physical(a.data_root, a.out),
            "solar": lambda: stage_solar(a.data_root, a.out),
            "tides": lambda: stage_tides(a.data_root, a.out),
            "mnist": lambda: stage_mnist(a.out, cache),
            "gate": lambda: stage_gate(a.out, cache),
            "dimension": lambda: stage_dimension(a.data_root, a.out, cache),
            "learning": lambda: stage_learning(a.out, cache),
            "operating": lambda: stage_operating(a.out, cache),
            "separability": lambda: stage_separability(a.out, cache),
            "selector": lambda: stage_selector(a.out, cache),
            "figures": lambda: stage_figures(a.out),
            **table_only,
        }
        if a.restage not in stages:
            raise SystemExit(f"--restage: no conozco '{a.restage}'. "
                             f"Hay: {', '.join(sorted(stages))}")
        t = time.time()
        stages[a.restage]()
        m = manifest(a.out, {})
        print(f"\n{a.restage} rehecha en {time.time() - t:.0f}s, "
              f"{len(m['files'])} artefactos en {a.out}")
        return

    if a.figures:
        # Redraw from an existing run's JSON. No measurement is repeated, so
        # this cannot change a number -- it can only change how one is drawn.
        DATA_ROOT_FOR_FIGS[0] = a.data_root
        stage_figures(a.figures)
        return

    if a.compare:
        MA = json.load(open(f"{a.compare[0]}/MANIFEST.json"))
        MB = json.load(open(f"{a.compare[1]}/MANIFEST.json"))
        # A run made by an older script has no 'inputs'/'code' block at all.
        # Reporting that as "every input differs" is noise; name it for what it is.
        stale = [n for n, M in zip(a.compare, (MA, MB))
                 if "inputs" not in M or "code" not in M]
        if stale:
            print("CORRIDA ANTERIOR AL REGISTRO DE PROCEDENCIA.")
            for n, M in zip(a.compare, (MA, MB)):
                miss = [b for b in ("inputs", "code") if b not in M]
                if miss:
                    print(f"  {n}: sin bloque {'/'.join(miss)} -- generada con "
                          "una version anterior del script.")
            print("  No se puede verificar que datos ni que codigo la "
                  "produjeron.\n")

        ca, cb = MA.get("code", {}), MB.get("code", {})
        diff_code = [k for k in sorted(set(ca) | set(cb)) if ca.get(k) != cb.get(k)]
        if diff_code and not stale:
            print("EL CODIGO DIFIERE entre las dos corridas:")
            for k in diff_code:
                print(f"  {k}")
            print()

        ia, ib = MA.get("inputs", {}), MB.get("inputs", {})
        diff_in = [k for k in sorted(set(ia) | set(ib)) if ia.get(k) != ib.get(k)]
        if diff_in and not stale:
            print("LOS DATOS DE ENTRADA DIFIEREN -- comparar salidas no tiene "
                  "sentido hasta arreglar esto:")
            for k in diff_in:
                print(f"  {k}\n    A: {ia.get(k)}\n    B: {ib.get(k)}")
            print()
        A, B = MA["files"], MB["files"]
        # An artefact present in only one run is a NEW artefact, not a
        # mismatched one. Calling both "DIFF" makes a stage that was added
        # between runs look like a determinism failure.
        shared = sorted(set(A) & set(B))
        only_a = sorted(set(A) - set(B))
        only_b = sorted(set(B) - set(A))
        bad = [k for k in shared if A[k] != B[k]]
        for k in shared:
            print(f"  {'OK  ' if A[k] == B[k] else 'DIFF'}  {k}")
        for k in only_a:
            print(f"  SOLO-A  {k}")
        for k in only_b:
            print(f"  SOLO-B  {k}")
        print(f"\n{len(shared) - len(bad)}/{len(shared)} artefactos comunes "
              f"identicos byte a byte")
        if only_a or only_b:
            print(f"({len(only_a)} solo en {a.compare[0]}, "
                  f"{len(only_b)} solo en {a.compare[1]} -- etapas agregadas o "
                  f"quitadas entre las dos corridas, no es un fallo)")
        if not bad and (diff_code or stale):
            print("Las salidas coinciden igual: el cambio de codigo fue INERTE "
                  "para estos artefactos.")
        if not bad and diff_in and not stale:
            print("ATENCION: las salidas coinciden pero las ENTRADAS difieren. "
                  "Eso no deberia pasar -- revisar antes de confiar en el "
                  "resultado.")
        sys.exit(1 if bad else 0)

    DATA_ROOT_FOR_FIGS[0] = a.data_root
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    print(f"seed={SEED} orders={ORDERS} reps={REPS}  out={a.out}\n")

    cache = os.path.join(a.out, "cache", "mnist.npz")
    R = {}
    print("[1/13] dominios fisicos + jerarquia de sustitutos")
    R["physical"] = stage_physical(a.data_root, a.out)
    print("[2/13] el contraste bajo ambos cocientes")
    R["contrast"] = stage_contrast_physical(a.data_root, a.out)
    print("[3/13] ECG mitdb: un corazon por curva, deteccion vs n")
    R["ecg_anomaly"] = stage_ecg_anomaly(a.data_root, a.out)
    # stage_pm_anomaly ya no corre por defecto: el detector del paper
    # es el de ECG. La medicion de PM sigue disponible con
    #     python reproduce.py --restage pm_anomaly
    # y su material va al trabajo del diagrama de fase.
    print("[4/13] PM: las cuatro poblaciones nominales (apendice)")
    R["pm_populations"] = stage_pm_populations(a.data_root, a.out)
    print("[5/13] MNIST: contraste y controles de canonizacion")
    if a.skip_mnist:
        print("    omitido por --skip-mnist")
    else:
        R["mnist"] = stage_mnist(a.out, cache)
    print("[6/13] la compuerta (digitos)")
    R["gate"] = stage_gate(a.out, cache)
    print("[7/13] dimension intrinseca + calibracion")
    R["dimension"] = stage_dimension(a.data_root, a.out, cache)
    print("[8/13] curvas de aprendizaje")
    R["learning"] = stage_learning(a.out, cache)
    print("[9/13] punto de operacion pedido -> memoria necesaria")
    R["operating"] = stage_operating(a.out, cache)
    print("[10/13] mareas NOAA (test preregistrado)")
    R["tides"] = stage_tides(a.data_root, a.out)
    print("[11/13] solar NSRDB (corte por nubosidad)")
    R["solar"] = stage_solar(a.data_root, a.out)
    print("[12/13] convergencia del radio")
    R["convergence"] = stage_convergence(a.data_root, a.out, cache)
    print("[13/13] figuras y macros")
    stage_figures(a.out)
    emit_numbers(a.out, R)

    m = manifest(a.out, input_manifest(a.data_root, cache))
    print(f"\n{len(m['files'])} artefactos, {time.time() - t0:.0f}s")
    for f, h in m["files"].items():
        print(f"  {h[:12]}  {f}")


if __name__ == "__main__":
    main()
