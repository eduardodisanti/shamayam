#!/usr/bin/env python3
"""
Is the spread in the operational radius a property of the method, an artefact
of the estimator, or an artefact of the L1 regulariser?

WHY THIS EXPERIMENT EXISTS
--------------------------
Reproducing Table 8 from the ported pipeline gave commissioning lengths,
relative errors and three of four lead times that match the published run, but
absolute radii 15-46% higher. The notebook contains a stability study across
five training seeds which shows radius spreads of 6-13%, and the temptation is
to conclude that the discrepancy is just that spread.

That conclusion does not follow. The notebook's stability study measures the
ASSET-SPECIFIC detector -- one autoencoder per bearing, fitted on 1,700 windows
of real data. Table 8 comes from the SHARED operator -- one autoencoder fitted
on 4,000 synthetic windows and transferred frozen. They are different objects
and there is no reason their seed sensitivity should agree. Reasoning from one
to the other is the same move that produced a phantom discrepancy in the
persistence rule earlier in this project.

So this measures the shared operator, and it is built to SEPARATE three
explanations rather than to confirm one.

  H1  THE ESTIMATOR. The radius is a 98th percentile of a modest sample, and
      Corollary [cor:degenerate_range] says such an estimator can be the sample
      maximum and therefore maximally variable. If so, the spread is the
      paper's own phenomenon appearing in the field experiment, and holding
      the operator fixed while resampling the commissioning window will
      reproduce it.

  H2  THE REGULARISER. The latent layer carries an L1 activity penalty, which
      induces SPARSE solutions. Different initialisations can retain different
      latent units -- discrete optima, not noise around one. That would explain
      the observed pattern better than a Gaussian spread does: in the
      notebook's study four seeds agree closely and exactly one departs, with
      a different seed departing for each bearing. If so, the latent support
      will differ across seeds and will track the radius.

  H3  THE METHOD. Genuine sensitivity of the transfer, with no artefact.

THE MEASUREMENT THAT MATTERS MOST
---------------------------------
A fourth possibility cuts across all three, and it is the one the earlier
comparison hints at. If a seed changes the operator's overall SCALE, every
residual moves together: nominal and degraded, calibration and monitoring.
The radius moves with them, and the DECISION -- does this recording exceed the
frozen radius -- does not change at all. That would explain why three of four
lead times matched while the radii differed by a third.

So the script reports the radius twice: absolute, and normalised by the median
early-life residual of the same bearing under the same seed. If the absolute
spread is large and the normalised spread is small, the variability is a gauge
freedom of the operator and carries no diagnostic consequence. If both are
large, it is real and Table 8 has to report it.

    python3 stability_experiment.py                     # 5 seeds, ~30 min
    python3 stability_experiment.py --seeds 42,7 --epochs 30   # first look
    python3 stability_experiment.py --no-field          # operator only, no archive
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from mssp_repro import (MAX_CALIBRATION_SIZE, MIN_CALIBRATION_SIZE,
                        MIN_WARMUP_SAMPLES, CONVERGENCE_CONSECUTIVE,
                        CONVERGENCE_LOOKBACK, CONVERGENCE_TOLERANCE,
                        AdaptiveOperationalRadius, find_convergence_index,
                        interpolated_quantile)
from mssp_repro.dynamics import first_persistent_departure
from mssp_repro.field import find_archive
from mssp_repro.field.residuals import compute_ims_residuals
from mssp_repro.field.shared_operator import (N_TRAIN, N_VAL,
                                              SharedFieldOperator,
                                              generate_oem_windows,
                                              seed_everything)

HERE = Path(__file__).parent
OUT = HERE / "results" / "stability.json"

# The seeds of the notebook's own stability study, so the two are comparable.
DEFAULT_SEEDS = [7, 21, 42, 84, 126]

# A latent unit counts as active if its standard deviation over nominal data
# exceeds this fraction of the largest unit's. The L1 penalty drives unused
# units towards a constant, not towards exactly zero, so a relative threshold
# is the honest criterion and the result is reported for two of them.
ACTIVE_THRESHOLDS = (0.01, 0.10)


def latent_support(operator, X):
    """
    Which latent units carry information, and how concentrated the code is.

    Returns the per-unit standard deviation over `X`, the active count at each
    threshold, and the participation ratio -- an inverse participation measure
    that is `d` when all units contribute equally and 1 when a single unit
    carries everything, and which needs no threshold at all.
    """
    z = operator.encoder_.predict(X, verbose=0)
    sd = np.std(z, axis=0)
    peak = sd.max() if sd.max() > 0 else 1.0
    counts = {f"active@{t}": int(np.sum(sd > t * peak)) for t in ACTIVE_THRESHOLDS}
    v = sd ** 2
    pr = float((v.sum() ** 2) / (v ** 2).sum()) if (v ** 2).sum() > 0 else 0.0
    return sd, counts, pr


def commission(series):
    """Adaptive commissioning of one bearing, as in the published pipeline."""
    early = series[:MAX_CALIBRATION_SIZE]
    trace = AdaptiveOperationalRadius(
        interpolated_quantile, window_size=MAX_CALIBRATION_SIZE,
        min_samples=MIN_WARMUP_SAMPLES).warmup_trace(early)
    idx = find_convergence_index(
        trace, lookback=CONVERGENCE_LOOKBACK, tolerance=CONVERGENCE_TOLERANCE,
        consecutive=CONVERGENCE_CONSECUTIVE, min_index=MIN_CALIBRATION_SIZE - 1)
    if idx is None:
        return None
    return {"n": int(idx + 1), "tau": float(trace[idx]),
            "oracle": float(interpolated_quantile(early)),
            "early_median": float(np.median(early))}


def estimator_only_spread(series, tau_reference, *, reps=400, rng=None):
    """
    H1: hold the operator FIXED and resample the commissioning window.

    Any spread here is the estimator's, not the training's. If it is of the
    same order as the seed-to-seed spread, H1 explains the observation without
    invoking the network at all.
    """
    rng = rng or np.random.default_rng(0)
    early = series[:MAX_CALIBRATION_SIZE]
    n = 49                                    # the commissioning length observed
    taus = [interpolated_quantile(early[rng.choice(len(early), n, replace=False)])
            for _ in range(reps)]
    taus = np.asarray(taus, dtype=float)
    return {"mean": float(taus.mean()), "sd": float(taus.std(ddof=1)),
            "rel_sd": float(taus.std(ddof=1) / taus.mean()),
            "rel_to_reference": float(abs(taus.mean() - tau_reference)
                                      / tau_reference)}


def run_seed(seed, epochs, ims_root, n_train, n_val):
    print(f"\n  seed {seed}: training...", flush=True)
    t0 = time.perf_counter()
    op = SharedFieldOperator(archive="nasa", seed=seed, epochs=epochs).fit(
        n_train=n_train, n_val=n_val)

    seed_everything(seed)
    X = generate_oem_windows(1000, archive="nasa")
    X = op.scaler_.transform(X).astype(np.float32)[..., None]
    sd, counts, pr = latent_support(op, X)

    row = {"seed": seed, "tau_mc": op.tau_mc_,
           "val_loss": op.history_["best_val_loss"],
           "latent_sd": [float(v) for v in sd],
           "participation_ratio": pr, **counts,
           "train_seconds": time.perf_counter() - t0}
    print(f"    tau_MC {op.tau_mc_:.6f}  val_loss "
          f"{op.history_['best_val_loss']:.5f}  "
          f"latent active {counts[f'active@{ACTIVE_THRESHOLDS[0]}']}/"
          f"{len(sd)}  participation {pr:.2f}")

    if ims_root is not None:
        res = compute_ims_residuals(op, ims_root)
        row["bearings"] = res["bearings"]
        row["field"] = []
        for i, b in enumerate(res["bearings"]):
            s = res["scores"][i]
            c = commission(s)
            if c is None:
                row["field"].append({"bearing": b, "converged": False})
                continue
            d = first_persistent_departure(s > c["tau"], q=8, p=10, start=c["n"])
            c.update({
                "bearing": b, "converged": True,
                "tau_normalised": c["tau"] / c["early_median"],
                "departure": None if d is None else int(d),
                "lead_hours": None if d is None else (len(s) - d) * 10 / 60,
                "series_median": float(np.median(s)),
            })
            row["field"].append(c)
            print(f"      bearing {b}: tau {c['tau']:.6f}  "
                  f"tau/median {c['tau_normalised']:.4f}  N {c['n']}  "
                  f"departure {c['departure']}  "
                  f"lead {c['lead_hours'] if d else float('nan'):.2f} h")
        row["_scores"] = res["scores"].tolist()
    return row


def report(rows):
    print("\n" + "=" * 74)
    print("  RESULTS")
    print("=" * 74)

    def spread(vals):
        v = np.asarray([x for x in vals if x is not None], dtype=float)
        if v.size < 2:
            return float("nan"), float("nan")
        return float(v.mean()), float(v.std(ddof=1) / v.mean())

    print("\n  Operator level (synthetic validation)")
    m, r = spread([x["tau_mc"] for x in rows])
    print(f"    tau_MC          mean {m:.6f}   relative sd {100*r:5.1f}%")
    m, r = spread([x["val_loss"] for x in rows])
    print(f"    val_loss        mean {m:.6f}   relative sd {100*r:5.1f}%")

    print("\n  H2 -- latent support (L1 sparsity)")
    print(f"    {'seed':>6}{'active@1%':>11}{'active@10%':>12}"
          f"{'participation':>15}{'tau_MC':>11}")
    for x in rows:
        print(f"    {x['seed']:>6}{x[f'active@{ACTIVE_THRESHOLDS[0]}']:>11}"
              f"{x[f'active@{ACTIVE_THRESHOLDS[1]}']:>12}"
              f"{x['participation_ratio']:>15.2f}{x['tau_mc']:>11.6f}")
    pr = np.array([x["participation_ratio"] for x in rows])
    tm = np.array([x["tau_mc"] for x in rows])
    rel_pr = pr.std(ddof=1) / pr.mean() if len(pr) > 1 else 0.0
    print(f"    participation ratio varies by {100*rel_pr:.1f}% across seeds "
          f"(out of {len(rows[0]['latent_sd'])} latent units)")
    if len(rows) < 3:
        # Say what is missing rather than implying a conclusion. Two points
        # cannot distinguish "the support is stable" from "we did not look".
        print(f"    too few seeds to correlate support against radius; "
              f"run at least 3")
    elif rel_pr < 0.02:
        print(f"    the L1 support does NOT move across seeds, so H2 -- "
              f"different latent units surviving -- is ruled out")
    else:
        print(f"    correlation between participation ratio and tau_MC: "
              f"{np.corrcoef(pr, tm)[0,1]:+.3f}  "
              f"(strong correlation would support H2)")

    if "field" not in rows[0]:
        print("\n  (field stage skipped)")
        return

    print("\n  THE DECISIVE COMPARISON -- absolute against normalised radius")
    print(f"    {'bearing':>8}{'tau mean':>12}{'rel sd':>9}"
          f"{'tau/median mean':>18}{'rel sd':>9}")
    bearings = rows[0]["bearings"]
    for i, b in enumerate(bearings):
        abs_m, abs_r = spread([x["field"][i].get("tau") for x in rows])
        nrm_m, nrm_r = spread([x["field"][i].get("tau_normalised") for x in rows])
        print(f"    {b:>8}{abs_m:12.6f}{100*abs_r:8.1f}%"
              f"{nrm_m:18.4f}{100*nrm_r:8.1f}%")
    print("\n    If the absolute spread is large and the normalised one small,"
          "\n    the seed sets an overall gauge and no decision depends on it.")

    print("\n  Invariants across seeds")
    print(f"    {'bearing':>8}{'N':>18}{'departure':>22}{'lead h':>22}")
    for i, b in enumerate(bearings):
        ns = [x["field"][i].get("n") for x in rows]
        ds = [x["field"][i].get("departure") for x in rows]
        ls = [x["field"][i].get("lead_hours") for x in rows]
        f = lambda v: "/".join("-" if q is None else f"{q:g}" for q in v)
        print(f"    {b:>8}{f(ns):>18}{f(ds):>22}{f(ls):>22}")

    print("\n  H1 -- estimator-only spread (operator FIXED, commissioning "
          "resampled)")
    ref = rows[0]
    scores = np.asarray(ref["_scores"])
    print(f"    {'bearing':>8}{'rel sd of tau':>16}   (compare with the "
          f"absolute seed spread above)")
    for i, b in enumerate(bearings):
        e = estimator_only_spread(scores[i], ref["field"][i]["tau"])
        print(f"    {b:>8}{100*e['rel_sd']:15.1f}%")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--n-train", type=int, default=N_TRAIN)
    ap.add_argument("--n-val", type=int, default=N_VAL)
    ap.add_argument("--no-field", action="store_true",
                    help="operator diagnostics only; no archive needed")
    ap.add_argument("--ims-root", default=None)
    args = ap.parse_args()

    seeds = [int(s) for s in args.seeds.split(",")]
    ims_root = None
    if not args.no_field:
        root = find_archive("NASA_bearing", explicit=args.ims_root)
        if root is None:
            raise SystemExit("NASA IMS archive not found; pass --ims-root or "
                             "use --no-field")
        ims_root = root / "IMS" if (root / "IMS").exists() else root

    print("=" * 74)
    print("  Seed stability of the SHARED field operator")
    print("=" * 74)
    print(f"  seeds {seeds}   epochs {args.epochs}   "
          f"train/val {args.n_train}/{args.n_val}")

    rows = [run_seed(s, args.epochs, ims_root, args.n_train, args.n_val)
            for s in seeds]
    report(rows)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"seeds": seeds, "epochs": args.epochs,
                               "rows": rows}, indent=1))
    print(f"\n  wrote {OUT.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
