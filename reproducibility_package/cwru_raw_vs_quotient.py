#!/usr/bin/env python3
"""
What the method is for: raw asset-specific model vs working in the quotient.

The reference a practitioner would build without the method is an
autoencoder trained on the bearing's RAW signal: native sampling rate, time
windows, no projection, no nuisance model. This script compares it, at an
equal commissioning TIME, with the two ways of working in the quotient:

  raw_local_full   raw windows, trained on the complete healthy record,
                   p98 on the same record (published Table 7 protocol)
  raw_local        raw windows, trained on the commissioning period only,
                   radius r_(k) on the same windows
  quot_local       order-domain windows (angular projection), trained on the
                   commissioning period augmented over the nuisance group the
                   simulator uses (phase via sliding windows, gain, offset,
                   noise), radius r_(k) on the 49 commissioning windows
  quot_oem         order-domain windows, frozen simulator-trained operator
                   (committed scores), radius r_(k) on the same 49 windows

Commissioning period = the first 49 order-domain windows (147 revolutions,
about 5 s); for the raw arms, the same seconds of signal. False alarms are
measured on the healthy signal AFTER that period; detection on all DE48 fault
windows (configuration B data).

Usage: python3 cwru_raw_vs_quotient.py [--cwru-root PATH]
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from mssp_repro.datasets import dataset_arg
from cwru_projection_experiment import FAMILIES, FS, _files
from mssp_repro.calibration import certified_order_statistic, interpolated_quantile
from mssp_repro.field.cwru import CWRU_SPEEDS
from mssp_repro.field.cwru_operator import AssetSpecificOperator
from mssp_repro.field.ims import make_windows
from mssp_repro.field.order_domain import (ORDER_WINDOW, REVS_PER_WINDOW,
                                           order_windows, project_signal)

N_COMMISSION = 49                      # order-domain windows
RAW_WIN = 1200
SEEDS = (0, 1, 2)
N_AUG = 4000
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "cwru_projection"


def de(path):
    with np.load(path) as d:
        return np.asarray(d["DE"], dtype=np.float64).reshape(-1)


def augment(segment, n, rng):
    """Windows drawn from the commissioning record over the nuisance group:
    random start (phase, no seam), gain U(0.75, 1.25), offset U(-0.1, 0.1)
    and additive noise U(0, 0.05), both relative to the segment RMS --
    the ranges of the simulator's 'wide' coverage."""
    rms = float(np.sqrt(np.mean(segment ** 2)))
    starts = rng.integers(0, len(segment) - ORDER_WINDOW + 1, size=n)
    W = np.stack([segment[s:s + ORDER_WINDOW] for s in starts])
    W = W * rng.uniform(0.75, 1.25, (n, 1))
    W = W + rng.uniform(-0.1, 0.1, (n, 1)) * rms
    W = W + rng.standard_normal(W.shape) * rng.uniform(0, 0.05, (n, 1)) * rms
    return W.astype(np.float32)


def metrics(s_cal, s_rest, s_faults, tau):
    out = {"tau": float(tau), "far_k": int(np.sum(s_rest > tau)),
           "far_n": int(len(s_rest))}
    for fam, s in s_faults.items():
        out[f"{fam}_dr"] = float(100 * np.mean(s > tau))
    return out


def fit_local(windows, seed):
    try:
        return AssetSpecificOperator(seed=seed).fit(windows), None
    except RuntimeError as e:          # assert_operator_learned refused it
        return None, str(e).split(":")[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cwru-root", **dataset_arg("CWRU_Bearing_NumPy"))
    ap.add_argument("--out", type=Path, default=RESULTS)
    args = ap.parse_args()
    S = np.load(RESULTS / "scores.npz")
    t0 = time.time()
    rep = {"n_commission": N_COMMISSION, "seeds": list(SEEDS),
           "raw_window": RAW_WIN, "n_aug": N_AUG, "speeds": {}}

    for rpm in CWRU_SPEEDS:
        folder = args.cwru_root / f"{rpm} RPM"
        nominal = int(rpm) / 60.0
        xN = de(folder / f"{rpm}_Normal.npz")
        yN, shaft = project_signal(xN, FS["Normal"], nominal)
        HQ = order_windows(yN).astype(np.float32)

        # commissioning period, in seconds and in raw samples
        seconds = N_COMMISSION * REVS_PER_WINDOW / shaft
        cut = int(round(seconds * FS["Normal"]))
        Hraw_cal = make_windows(xN[:cut], win=RAW_WIN, step=RAW_WIN)
        Hraw_rest = make_windows(xN[cut:], win=RAW_WIN, step=RAW_WIN) \
            if len(xN) - cut >= RAW_WIN else np.empty((0, RAW_WIN))
        Fraw = {fam: np.concatenate([make_windows(de(p), win=RAW_WIN,
                                                  step=RAW_WIN)
                                     for p in _files(folder, rpm, tag, "DE48")])
                for fam, tag in FAMILIES.items()}
        Hraw_all = make_windows(xN, win=RAW_WIN, step=RAW_WIN)

        e = {"shaft_hz": shaft, "commission_seconds": seconds,
             "raw_cal_windows": int(len(Hraw_cal)),
             "raw_rest_windows": int(len(Hraw_rest)),
             "quot_rest_windows": int(len(HQ) - N_COMMISSION),
             "raw_local_full": [], "raw_local": [], "quot_local": []}

        # OEM in the quotient: committed scores
        sH = S[f"B/{rpm}/healthy/ae"]
        tau = certified_order_statistic(sH[:N_COMMISSION])
        e["quot_oem"] = metrics(sH[:N_COMMISSION], sH[N_COMMISSION:],
                                {f: S[f"B/{rpm}/{f}/ae"] for f in FAMILIES},
                                tau)

        for seed in SEEDS:
            # raw, complete history (Table 7 protocol)
            op, err = fit_local(Hraw_all, seed)
            if op is None:
                e["raw_local_full"].append({"seed": seed, "learned": False})
            else:
                s = op.scores(Hraw_all)
                tau = interpolated_quantile(s)
                r = {"seed": seed, "learned": True, "tau": float(tau),
                     "far_insample": float(100 * np.mean(s > tau))}
                for fam in FAMILIES:
                    r[f"{fam}_dr"] = float(100 * np.mean(
                        op.scores(Fraw[fam]) > tau))
                e["raw_local_full"].append(r)

            # raw, commissioning period only
            op, err = fit_local(Hraw_cal, seed)
            if op is None:
                e["raw_local"].append({"seed": seed, "learned": False})
            else:
                r = metrics(None, op.scores(Hraw_rest) if len(Hraw_rest)
                            else np.empty(0),
                            {f: op.scores(Fraw[f]) for f in FAMILIES},
                            certified_order_statistic(op.scores(Hraw_cal)))
                r.update(seed=seed, learned=True,
                         gap=op.history_["generalisation_gap"])
                e["raw_local"].append(r)

            # quotient, local, augmented over the nuisance group
            rng = np.random.default_rng(seed)
            seg = yN[:N_COMMISSION * ORDER_WINDOW]
            op, err = fit_local(augment(seg, N_AUG, rng), seed)
            if op is None:
                e["quot_local"].append({"seed": seed, "learned": False})
            else:
                from cwru_projection_experiment import load_config
                if seed == SEEDS[0]:
                    dataB, _ = load_config(args.cwru_root, rpm, "B")
                r = metrics(None, op.scores(HQ[N_COMMISSION:]),
                            {f: op.scores(dataB[f]) for f in FAMILIES},
                            certified_order_statistic(
                                op.scores(HQ[:N_COMMISSION])))
                r.update(seed=seed, learned=True,
                         gap=op.history_["generalisation_gap"])
                e["quot_local"].append(r)
            print(f"[{rpm} seed {seed}] raw_full "
                  f"{e['raw_local_full'][-1].get('far_insample')} | raw "
                  f"{e['raw_local'][-1].get('far_k')}/{e['raw_local'][-1].get('far_n')} "
                  f"| quot_local {e['quot_local'][-1].get('far_k')}/"
                  f"{e['quot_local'][-1].get('far_n')} | oem "
                  f"{e['quot_oem']['far_k']}/{e['quot_oem']['far_n']} "
                  f"[{time.time() - t0:.0f}s]", flush=True)
        rep["speeds"][rpm] = e

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "raw_vs_quotient.json").write_text(json.dumps(rep, indent=1)
                                                   + "\n")
    print("wrote", args.out / "raw_vs_quotient.json")


if __name__ == "__main__":
    main()
