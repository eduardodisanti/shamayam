#!/usr/bin/env python3
"""
Ottawa appendix: what speed does beyond time scaling, and what conditioning
the radius on speed can and cannot do. Analysis only -- no method is
proposed here, and nothing is trained.

Reads
  * the dataset (healthy records only), for the amplitude-speed relation;
  * results/ottawa/results_seed{0..4}.json and scores_seed{0..4}.npz, written
    by ottawa_variable_speed.py --tag _seedN (window scores and window speeds).

Writes results/ottawa/appendix.json, from which ottawa_report.py builds the
appendix tables.

1. Amplitude follows speed. For every healthy record: correlation between
   the RMS of the time windows and their speed, and the exponent alpha of
   RMS ~ speed^alpha (least squares in log-log).
2. Speed-conditioned radius (analysis). For each commissioning scenario,
   arm and seed, the commissioning windows are split by speed band; a band
   gets its own r_(k) only if it holds at least 49 windows (below that no
   distribution-free 0.98 radius exists). Healthy test windows are judged
   against their band's radius; windows in a band without a radius are
   counted separately as 'not covered'.

Usage: python3 ottawa_speed_appendix.py [--ottawa-root PATH]
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from mssp_repro.calibration import certified_order_statistic
from mssp_repro.datasets import dataset_arg
from mssp_repro.field.ims import make_windows
from mssp_repro.field.ottawa import (OTTAWA_FS, PROFILES, TRIALS,
                                     encoder_angle, load_record)

HERE = Path(__file__).resolve().parent
RES = HERE / "results" / "ottawa"
SEEDS = (0, 1, 2, 3, 4)
TIME_FS = 8000
BANDS = ((10, 15), (15, 20), (20, 25), (25, 30))
TIME_ARMS = ("rms_t", "raw", "raw_aug")
MIN_N = 49


def amplitude_speed(root):
    out = {}
    for p in PROFILES:
        for t in TRIALS:
            x, e = load_record(root, "H", p, t)
            xt = resample_poly(x, 1, OTTAWA_FS // TIME_FS)
            W = make_windows(xt, 1200, 1200)
            te, th = encoder_angle(e)
            lag = 64
            c = (np.arange(len(W)) * 1200 + 600) / TIME_FS
            v = np.interp(c, 0.5 * (te[lag:] + te[:-lag]),
                          (th[lag:] - th[:-lag]) / (te[lag:] - te[:-lag]))
            rms = np.sqrt(np.mean(W ** 2, axis=1))
            alpha = np.polyfit(np.log(v), np.log(rms), 1)[0]
            out[f"H-{p}-{t}"] = {"corr": float(np.corrcoef(v, rms)[0, 1]),
                                 "alpha": float(alpha),
                                 "speed_min": float(v.min()),
                                 "speed_max": float(v.max())}
    return out


def band_of(v):
    b = np.full(len(v), -1)
    for i, (lo, hi) in enumerate(BANDS):
        b[(v >= lo) & (v < hi)] = i
    return b


def conditioned(R, S, scenario, arm):
    """Global versus speed-conditioned radius for one run."""
    comm = R["scenarios"][scenario]["commissioning"]
    test = R["test_healthy"]
    key = "speed_t" if arm in TIME_ARMS else "speed"
    pre = f"{scenario}/{arm}/"
    if pre + comm[0] not in S:
        return None
    sc = np.concatenate([S[pre + k] for k in comm])
    vc = np.concatenate([S[f"{key}/{k}"][:len(S[pre + k])] for k in comm])
    st = np.concatenate([S[pre + k] for k in test])
    vt = np.concatenate([S[f"{key}/{k}"][:len(S[pre + k])] for k in test])
    tau = float(certified_order_statistic(sc))
    bc, bt = band_of(vc), band_of(vt)
    bands = []
    cond_k = cond_n = not_cov = 0
    for i, b in enumerate(BANDS):
        nb = int(np.sum(bc == i))
        tb = st[bt == i]
        rb = (float(certified_order_statistic(sc[bc == i]))
              if nb >= MIN_N else None)
        row = {"band": list(b), "n_comm": nb, "n_test": int(len(tb)),
               "tau": rb, "k_global": int(np.sum(tb > tau))}
        if rb is None:
            row["k_cond"] = None
            not_cov += len(tb)
        else:
            row["k_cond"] = int(np.sum(tb > rb))
            cond_k += row["k_cond"]
            cond_n += len(tb)
        bands.append(row)
    return {"tau": tau, "far_global_k": int(np.sum(st > tau)),
            "far_global_n": int(len(st)), "far_cond_k": cond_k,
            "far_cond_n": cond_n, "not_covered": int(not_cov), "bands": bands}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--ottawa-root", **dataset_arg("Ottawa_Bearing_TimeVaryingSpeed"))
    args = ap.parse_args()
    out = {"bands": [list(b) for b in BANDS], "min_n": MIN_N,
           "amplitude_speed": amplitude_speed(args.ottawa_root),
           "conditioned": {}}
    for s in SEEDS:
        rf, sf = RES / f"results_seed{s}.json", RES / f"scores_seed{s}.npz"
        if not (rf.exists() and sf.exists()):
            continue
        R = json.loads(rf.read_text())
        with np.load(sf) as z:
            S = {k: z[k] for k in z.files}
        for scenario, res in R["scenarios"].items():
            for arm, e in res.items():
                if arm == "commissioning" or not e.get("learned", True):
                    continue
                c = conditioned(R, S, scenario, arm)
                if c is not None:
                    out["conditioned"].setdefault(scenario, {}).setdefault(
                        arm, {})[str(s)] = c
    (RES / "appendix.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", RES / "appendix.json")


if __name__ == "__main__":
    main()
