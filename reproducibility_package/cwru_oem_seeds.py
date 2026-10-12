#!/usr/bin/env python3
"""
CWRU (configuration B): seed variability of the OEM operator in the quotient.

The OEM-style operator of cwru_projection_experiment.py was trained once
(seed 42). Here it is retrained with further seeds, each evaluated exactly as
before on the corrected data: AUROC healthy vs each fault family, the oracle
radius, and the certified r_(k) radius on the first 49 healthy windows with
false alarms on the windows that follow.

Usage: python3 cwru_oem_seeds.py --cwru-root PATH/Data
"""

import argparse
import json
import time
from pathlib import Path

from cwru_projection_experiment import (OrderDomainSharedOperator,
                                        evaluate_scores, load_config,
                                        window_scores)
from mssp_repro.field.cwru import CWRU_SPEEDS

SEEDS = (0, 1, 2, 3)              # seed 42 is the run in results.json
HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "cwru_projection" / "oem_seeds.json"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cwru-root", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    t0 = time.time()
    data = {rpm: load_config(args.cwru_root, rpm, "B")[0]
            for rpm in CWRU_SPEEDS}
    rep = {"config": "B", "seeds": {}}
    for seed in SEEDS:
        op = OrderDomainSharedOperator(archive="cwru", seed=seed).fit()
        e = {"training": {k: v for k, v in op.history_.items()
                          if k not in ("loss", "val_loss")}, "speeds": {}}
        for rpm in CWRU_SPEEDS:
            r = evaluate_scores(lambda W, ref: window_scores(op, W),
                                data[rpm], tau_direct=op.tau_mc_)
            e["speeds"][rpm] = {k: r[k] for k in
                                ("n_healthy", "oracle", "auroc", "certified",
                                 "direct")}
        rep["seeds"][str(seed)] = e
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, indent=1) + "\n")
        print(f"[seed {seed}] {op.describe_training()} "
              f"[{time.time() - t0:.0f}s]", flush=True)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
