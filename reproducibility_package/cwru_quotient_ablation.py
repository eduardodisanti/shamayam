#!/usr/bin/env python3
"""
Describing the quotient better: does a richer nuisance group give a better
local model?

A local autoencoder is trained on the commissioning period of each operating
condition (first 49 order-domain windows, ~5 s; configuration B data),
always on N_AUG windows so that ONLY the description of the nuisance group
changes between levels:

  G0  projection only      the 49 commissioning windows, resampled with
                           replacement (no new variation)
  G1  + phase              windows starting anywhere in the commissioning
                           record (shaft-angle shift, no seam)
  G2  + gain               G1 x gain U(0.75, 1.25)
  G3  + offset             G2 + offset U(-0.1, 0.1) x RMS
  G4  + noise (full)       G3 + noise U(0, 0.05) x RMS  (= quot_local in
                           cwru_raw_vs_quotient.py, with the same ranges)

Ranges are the simulator's 'wide' coverage. Radius r_(k) on the 49
commissioning windows; FAR on the healthy windows that follow; detection on
all DE48 faults. 1797 rpm is skipped: only one healthy window follows.

Usage: python3 cwru_quotient_ablation.py --cwru-root PATH/Data
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from cwru_projection_experiment import FAMILIES, FS, load_config
from mssp_repro.calibration import certified_order_statistic
from mssp_repro.field.cwru_operator import AssetSpecificOperator
from mssp_repro.field.order_domain import ORDER_WINDOW, project_signal

N_COMMISSION = 49
N_AUG = 4000
SEEDS = (0, 1)
SPEEDS = ("1730", "1750", "1772")
LEVELS = ("G0", "G1", "G2", "G3", "G4")
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "cwru_projection"


def make_training_set(level, segment, cal_windows, n, rng):
    if level == "G0":
        return cal_windows[rng.integers(0, len(cal_windows), size=n)]
    rms = float(np.sqrt(np.mean(segment ** 2)))
    starts = rng.integers(0, len(segment) - ORDER_WINDOW + 1, size=n)
    W = np.stack([segment[s:s + ORDER_WINDOW] for s in starts])
    if level in ("G2", "G3", "G4"):
        W = W * rng.uniform(0.75, 1.25, (n, 1))
    if level in ("G3", "G4"):
        W = W + rng.uniform(-0.1, 0.1, (n, 1)) * rms
    if level == "G4":
        W = W + rng.standard_normal(W.shape) * rng.uniform(0, 0.05, (n, 1)) * rms
    return W.astype(np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cwru-root", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=RESULTS)
    args = ap.parse_args()
    t0 = time.time()
    rep = {"n_commission": N_COMMISSION, "n_aug": N_AUG, "seeds": list(SEEDS),
           "levels": list(LEVELS), "speeds": {}}
    for rpm in SPEEDS:
        data, _ = load_config(args.cwru_root, rpm, "B")
        H = data["healthy"]
        with np.load(args.cwru_root / f"{rpm} RPM" / f"{rpm}_Normal.npz") as d:
            x = np.asarray(d["DE"], dtype=np.float64).reshape(-1)
        y, _ = project_signal(x, FS["Normal"], int(rpm) / 60.0)
        segment = y[:N_COMMISSION * ORDER_WINDOW]
        cal, rest = H[:N_COMMISSION], H[N_COMMISSION:]
        entry = {lv: [] for lv in LEVELS}
        for lv in LEVELS:
            for seed in SEEDS:
                rng = np.random.default_rng(1000 * seed + LEVELS.index(lv))
                Xtr = make_training_set(lv, segment, cal, N_AUG, rng)
                try:
                    op = AssetSpecificOperator(seed=seed).fit(Xtr)
                except RuntimeError:
                    entry[lv].append({"seed": seed, "learned": False})
                    continue
                tau = certified_order_statistic(op.scores(cal))
                r = {"seed": seed, "learned": True, "tau": float(tau),
                     "far_k": int(np.sum(op.scores(rest) > tau)),
                     "far_n": int(len(rest)),
                     "gap": op.history_["generalisation_gap"]}
                for fam in FAMILIES:
                    r[f"{fam}_dr"] = float(100 * np.mean(
                        op.scores(data[fam]) > tau))
                entry[lv].append(r)
                print(f"[{rpm} {lv} seed {seed}] FAR {r['far_k']}/{r['far_n']} "
                      f"gap {r['gap']:.2f} [{time.time() - t0:.0f}s]",
                      flush=True)
        rep["speeds"][rpm] = entry
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "quotient_ablation.json").write_text(
            json.dumps(rep, indent=1) + "\n")        # checkpoint per speed
    print("wrote", args.out / "quotient_ablation.json")


if __name__ == "__main__":
    main()
