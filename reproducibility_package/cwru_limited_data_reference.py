#!/usr/bin/env python3
"""
Equal data budget on corrected CWRU: asset-specific model trained on the
commissioning windows only, against the shared OEM model calibrated on them.

The realistic alternative to an OEM-style model on a NEW asset is not a model
trained on that asset's complete history -- the history does not exist yet --
but one trained on whatever nominal data the commissioning period provides.
Both arms here get exactly the same data: the first n = 49 healthy windows of
each operating condition (configuration B: Normal + DE48, order domain).

  asset-specific  autoencoder (published architecture and schedule) trained on
                  the n windows; radius r_(k) on its own residuals of those
                  same windows, since there is nothing else to calibrate on
  OEM             frozen simulator-trained operator (scores from
                  cwru_projection_experiment.py, results/cwru_projection/
                  scores.npz); radius r_(k) on the same n windows

False alarms are measured on the healthy windows that FOLLOW the n used
(never seen by either arm). The asset-specific arm is trained with several
seeds because 49 windows make its training noisy; the OEM arm has no
per-asset training and therefore no seed to vary here.

Usage: python3 cwru_limited_data_reference.py --cwru-root PATH/Data
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from cwru_projection_experiment import FAMILIES, load_config
from mssp_repro.calibration import certified_order_statistic
from mssp_repro.field.cwru import CWRU_SPEEDS
from mssp_repro.field.cwru_operator import AssetSpecificOperator

N_BUDGET = 49
SEEDS = (0, 1, 2, 3, 4)
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "cwru_projection"


def arm_metrics(s_cal, s_rest, s_faults):
    tau = certified_order_statistic(s_cal)
    out = {"tau": float(tau), "far_k": int(np.sum(s_rest > tau)),
           "far_n": int(len(s_rest))}
    for fam, s in s_faults.items():
        out[f"{fam}_dr"] = float(100 * np.mean(s > tau))
        if len(s_rest) >= 10:
            y = np.r_[np.zeros(len(s_rest)), np.ones(len(s))]
            out[f"{fam}_auroc"] = float(roc_auc_score(y, np.r_[s_rest, s]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cwru-root", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=RESULTS)
    args = ap.parse_args()
    S = np.load(RESULTS / "scores.npz")
    t0 = time.time()
    report = {"n_budget": N_BUDGET, "seeds": list(SEEDS), "config": "B",
              "speeds": {}}
    for rpm in CWRU_SPEEDS:
        data, _ = load_config(args.cwru_root, rpm, "B")
        H = data["healthy"]
        cal, rest = H[:N_BUDGET], H[N_BUDGET:]
        entry = {"n_healthy": int(len(H))}

        # OEM: same windows, scores already computed by the frozen operator
        sH = S[f"B/{rpm}/healthy/ae"]
        assert len(sH) == len(H)
        entry["oem"] = arm_metrics(
            sH[:N_BUDGET], sH[N_BUDGET:],
            {f: S[f"B/{rpm}/{f}/ae"] for f in FAMILIES})

        runs = []
        for seed in SEEDS:
            try:
                op = AssetSpecificOperator(seed=seed).fit(cal)
            except RuntimeError as e:
                # assert_operator_learned refused the model: with this little
                # data training can fail outright. Recorded, not hidden.
                runs.append({"seed": seed, "learned": False,
                             "reason": str(e).split(":")[0]})
                print(f"[{rpm} seed {seed}] did not learn", flush=True)
                continue
            r = arm_metrics(op.scores(cal), op.scores(rest),
                            {f: op.scores(data[f]) for f in FAMILIES})
            r.update(seed=seed, learned=True,
                     gap=op.history_["generalisation_gap"])
            runs.append(r)
            print(f"[{rpm} seed {seed}] FAR {r['far_k']}/{r['far_n']} "
                  f"DR {[round(r[f + '_dr'], 1) for f in FAMILIES]} "
                  f"gap {r['gap']:.2f} [{time.time() - t0:.0f}s]", flush=True)
        entry["asset"] = runs
        report["speeds"][rpm] = entry
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "limited_data.json").write_text(json.dumps(report, indent=1)
                                                + "\n")
    print("wrote", args.out / "limited_data.json")


if __name__ == "__main__":
    main()
