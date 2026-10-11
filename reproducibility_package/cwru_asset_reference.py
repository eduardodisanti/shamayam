#!/usr/bin/env python3
"""
Asset-specific reference on corrected CWRU (configuration B).

The feasibility claim of the paper is that a shared, OEM-style model --
trained without any data of the asset and calibrated locally without labels --
reaches the operating point of a model built from the asset's own history.
This script builds that reference exactly as the published Table 7 did: one
autoencoder per operating condition, trained on that condition's complete
healthy record, thresholded at the 98th percentile of the same record. The
only change is the data: Normal + DE48, both projected to the order domain.

It is deliberately favourable to the reference (no held-out data, as
published). The shared-model numbers to compare against are in results.json
of cwru_projection_experiment.py.

Usage: python3 cwru_asset_reference.py --cwru-root PATH/Data --out DIR
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from cwru_projection_experiment import FAMILIES, load_config
from mssp_repro.field.cwru import CWRU_SPEEDS
from mssp_repro.field.cwru_operator import AssetSpecificOperator


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cwru-root", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path("results/cwru_projection"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    t0 = time.time()
    report = {"seed": args.seed, "config": "B", "speeds": {}}
    for rpm in CWRU_SPEEDS:
        data, _ = load_config(args.cwru_root, rpm, "B")
        op = AssetSpecificOperator(seed=args.seed).fit(data["healthy"])
        sH = op.scores(data["healthy"])
        r = {"n_healthy": int(len(sH)), "tau": op.tau_,
             "far": float(100 * np.mean(sH > op.tau_)), **op.history_}
        for fam in FAMILIES:
            sF = op.scores(data[fam])
            r[f"{fam}_dr"] = float(100 * np.mean(sF > op.tau_))
            y = np.r_[np.zeros(len(sH)), np.ones(len(sF))]
            r[f"{fam}_auroc"] = float(roc_auc_score(y, np.r_[sH, sF]))
        report["speeds"][rpm] = r
        print(f"[{rpm}] n={r['n_healthy']} tau={r['tau']:.4f} FAR={r['far']:.2f} "
              f"DR={[round(r[f + '_dr'], 2) for f in FAMILIES]} "
              f"gap={r['generalisation_gap']:.2f} [{time.time() - t0:.0f}s]",
              flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "asset_reference.json").write_text(json.dumps(report, indent=1))
    print("wrote", args.out / "asset_reference.json")


if __name__ == "__main__":
    main()
