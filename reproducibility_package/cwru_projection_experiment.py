#!/usr/bin/env python3
"""
CWRU before/after the sampling-rate fix, under one shared representation.

THE PROBLEM THIS RUN ADDRESSES
------------------------------
The published CWRU arm compared the Normal Baseline (acquired at 48 kHz) with
the DE12 fault files (12 kHz), reading both as 12 kHz. Healthy and faulty
windows therefore differed by a factor of four in time scale, and every
detector -- including a zero-crossing count -- separated them perfectly.

THREE CONFIGURATIONS, SAME PROTOCOL
-----------------------------------
  A  original     Normal read as 12 kHz + DE12 faults, time-domain windows,
                  operator trained on time-domain simulation (as published).
  B  corrected    Normal + DE48 faults (same acquisition), both projected to
                  the order domain (400 samples/rev, 3-rev windows); operator
                  trained on order-domain simulation.
  C  chain check  Normal + DE12 faults, both projected. Speed and rate are
                  removed; the acquisition chain is not. Shows what remains of
                  the confound when only the projection is applied.

For every configuration and speed:
  * shared operator, calibrations: direct transfer, oracle (all healthy,
    interpolated p98, as published), online stopping rule (as published),
    certified r_(k) on a 49-window chronological prefix with FAR measured on
    the windows that follow;
  * baselines with the same calibrations: RMS, kurtosis, zero-crossing rate,
    each scored as |feature - healthy median|;
  * threshold-free separability: AUROC healthy vs each fault family.

Usage:  python3 cwru_projection_experiment.py [--cwru-root PATH] [--out DIR]
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import kurtosis
from sklearn.metrics import roc_auc_score

from mssp_repro.datasets import dataset_arg
from mssp_repro.bearing_simulator import CWRU_PARAMS
from mssp_repro.calibration import (AdaptiveOperationalRadius,
                                    certified_order_statistic,
                                    find_convergence_index,
                                    interpolated_quantile)
from mssp_repro import (CONVERGENCE_CONSECUTIVE, CONVERGENCE_LOOKBACK,
                        CONVERGENCE_TOLERANCE, MAX_CALIBRATION_SIZE,
                        MIN_CALIBRATION_SIZE, MIN_WARMUP_SAMPLES)
from mssp_repro.field.cwru import CWRU_SPEEDS, load_asset_windows
from mssp_repro.field.ims import make_windows
from mssp_repro.field.order_domain import (OrderDomainSimulator,
                                           order_windows, project_signal)
from mssp_repro.field.shared_operator import (N_TRAIN, N_VAL, OEM_SEED,
                                              THRESHOLD_PERCENTILE,
                                              SharedFieldOperator,
                                              seed_everything)

CERT_N = 49                       # floor of the coverage corollary at alpha=0.02
FAMILIES = {"ball": "B", "inner_race": "IR", "outer_race": "OR"}
FS = {"DE12": 12000, "DE48": 48000, "Normal": 48000}


# ---------------------------------------------------------------- operators

class OrderDomainSharedOperator(SharedFieldOperator):
    """The published shared operator and schedule, trained on simulated
    windows that went through the same angular projection as field data."""

    def _generate(self, n):
        return OrderDomainSimulator(CWRU_PARAMS).windows(n)

    def fit(self, n_train=N_TRAIN, n_val=N_VAL):
        import mssp_repro.field.shared_operator as so
        original = so.generate_oem_windows
        so.generate_oem_windows = lambda n, **kw: self._generate(n)
        try:
            return super().fit(n_train=n_train, n_val=n_val)
        finally:
            so.generate_oem_windows = original


def window_scores(op, windows, batch=2048):
    w = op.scaler_.transform(np.asarray(windows, np.float32).reshape(
        len(windows), -1)).astype(np.float32)[..., np.newaxis]
    out = np.empty(len(w))
    for s in range(0, len(w), batch):
        out[s:s + batch] = op._window_mse(w[s:s + batch])
    return out


# ---------------------------------------------------------------- data

def _files(folder, rpm, family, acq):
    pat = f"{rpm}_{family}*_{acq}.npz" if family != "OR" else \
        f"{rpm}_OR@*_{acq}.npz"
    return sorted(folder.glob(pat))


MIN_SECONDS_FOR_SPEED = 3.0      # shorter records borrow the Normal's speed


def projected_file(path, fs, nominal_hz, *, fallback_hz=None):
    """
    Project one file. Records shorter than MIN_SECONDS_FOR_SPEED do not
    resolve the shaft line well enough (1797_IR_14_DE48 is 1.3 s and its
    estimate lands 3% low); they use the speed estimated on the Normal record
    of the same operating condition instead, and are flagged.
    """
    with np.load(path) as d:
        x = np.asarray(d["DE"], dtype=np.float64).reshape(-1)
    short = len(x) / fs < MIN_SECONDS_FOR_SPEED and fallback_hz is not None
    y, shaft = project_signal(x, fs, nominal_hz,
                              shaft_hz=fallback_hz if short else None)
    return order_windows(y).astype(np.float32), shaft, bool(short)


def load_config(root, rpm, config):
    """{family: windows}, plus per-file metadata."""
    folder = root / f"{rpm} RPM"
    meta = []
    if config == "A":
        w = load_asset_windows(root, rpm)
        return {"healthy": w["healthy"], **{k: w[k] for k in FAMILIES}}, meta

    nominal = int(rpm) / 60.0
    out = {}
    h, normal_shaft, _ = projected_file(folder / f"{rpm}_Normal.npz",
                                        FS["Normal"], nominal)
    out["healthy"] = h
    meta.append({"file": f"{rpm}_Normal.npz", "shaft_hz": normal_shaft,
                 "windows": len(h), "speed_fallback": False})
    acq = "DE48" if config == "B" else "DE12"
    for fam, tag in FAMILIES.items():
        parts = []
        for p in _files(folder, rpm, tag, acq):
            w, shaft, fb = projected_file(p, FS[acq], nominal,
                                          fallback_hz=normal_shaft)
            parts.append(w)
            meta.append({"file": p.name, "family": fam, "shaft_hz": shaft,
                         "windows": len(w), "speed_fallback": fb})
        out[fam] = np.concatenate(parts)
    return out, meta


# ---------------------------------------------------------------- scoring

def zcr(W):
    W = W - W.mean(axis=1, keepdims=True)
    return (np.diff(np.sign(W), axis=1) != 0).mean(axis=1)


FEATURES = {
    "rms": lambda W: np.sqrt(np.mean(np.square(W), axis=1)),
    "kurtosis": lambda W: kurtosis(W, axis=1, fisher=False),
    "zcr": zcr,
}


def pct(x):
    return float(100.0 * np.mean(x))


def evaluate_scores(score_fn, data, *, tau_direct=None, online=False):
    """
    `score_fn(windows, reference)` returns anomaly scores; `reference` is the
    healthy set the score is centred on (ignored by the operator residual).
    """
    H = data["healthy"]
    res = {"n_healthy": int(len(H))}

    # oracle: everything, as published
    sH = score_fn(H, H)
    tau = interpolated_quantile(sH)
    arm = {"tau": tau, "far": pct(sH > tau)}
    for f in FAMILIES:
        arm[f"{f}_dr"] = pct(score_fn(data[f], H) > tau)
    res["oracle"] = arm

    # AUROC, threshold-free
    res["auroc"] = {}
    for f in FAMILIES:
        sF = score_fn(data[f], H)
        y = np.r_[np.zeros(len(sH)), np.ones(len(sF))]
        res["auroc"][f] = float(roc_auc_score(y, np.r_[sH, sF]))

    # certified r_(k) on a chronological prefix, FAR on what follows
    cal = H[:CERT_N]
    s_cal = score_fn(cal, cal)
    tau_c = certified_order_statistic(s_cal)
    rest = H[CERT_N:]
    arm = {"n_cal": CERT_N, "tau": tau_c, "n_heldout": int(len(rest)),
           "far_heldout": pct(score_fn(rest, cal) > tau_c) if len(rest) else None}
    for f in FAMILIES:
        arm[f"{f}_dr"] = pct(score_fn(data[f], cal) > tau_c)
    res["certified"] = arm

    if tau_direct is not None:
        arm = {"tau": tau_direct, "far": pct(sH > tau_direct)}
        for f in FAMILIES:
            arm[f"{f}_dr"] = pct(score_fn(data[f], H) > tau_direct)
        res["direct"] = arm

    if online:
        early = sH[:MAX_CALIBRATION_SIZE]
        trace = AdaptiveOperationalRadius(
            interpolated_quantile, window_size=MAX_CALIBRATION_SIZE,
            min_samples=MIN_WARMUP_SAMPLES).warmup_trace(early)
        idx = find_convergence_index(
            trace, lookback=CONVERGENCE_LOOKBACK,
            tolerance=CONVERGENCE_TOLERANCE,
            consecutive=CONVERGENCE_CONSECUTIVE,
            min_index=MIN_CALIBRATION_SIZE - 1)
        if idx is None:
            res["online"] = {"converged": False,
                             "n_available": int(len(early))}
        else:
            t = float(trace[idx])
            post = sH[idx + 1:]
            arm = {"converged": True, "n": int(idx + 1), "tau": t,
                   "far_all": pct(sH > t),
                   "far_post": pct(post > t) if len(post) else None,
                   "n_post": int(len(post))}
            for f in FAMILIES:
                arm[f"{f}_dr"] = pct(score_fn(data[f], H) > t)
            res["online"] = arm
    return res


def feature_score(name):
    feat = FEATURES[name]

    def fn(W, ref):
        return np.abs(feat(W) - np.median(feat(ref)))
    return fn


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--cwru-root", **dataset_arg("CWRU_Bearing_NumPy"))
    ap.add_argument("--out", type=Path,
                    default=Path("results/cwru_projection"))
    ap.add_argument("--configs", default="A,B,C")
    ap.add_argument("--seed", type=int, default=OEM_SEED)
    ap.add_argument("--epochs", type=int, default=None)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    configs = args.configs.split(",")

    report = {"seed": args.seed, "cert_n": CERT_N, "configs": {},
              "operators": {}}
    ops = {}
    t0 = time.time()
    need_time = "A" in configs
    need_order = any(c in configs for c in ("B", "C"))
    kw = {} if args.epochs is None else {"epochs": args.epochs}
    if need_time:
        ops["time"] = SharedFieldOperator(archive="cwru", seed=args.seed,
                                          **kw).fit()
        report["operators"]["time"] = ops["time"].history_
        print("time-domain operator:", ops["time"].describe_training(),
              f"[{time.time() - t0:.0f}s]", flush=True)
    if need_order:
        ops["order"] = OrderDomainSharedOperator(archive="cwru",
                                                 seed=args.seed, **kw).fit()
        report["operators"]["order"] = ops["order"].history_
        print("order-domain operator:", ops["order"].describe_training(),
              f"[{time.time() - t0:.0f}s]", flush=True)

    for key, op in ops.items():
        op.ae_.save(args.out / f"operator_{key}.keras")
        np.savez(args.out / f"scaler_{key}.npz", mean=op.scaler_.mean_,
                 scale=op.scaler_.scale_, tau_mc=op.tau_mc_)

    scores = {}
    for cfg in configs:
        op = ops["time" if cfg == "A" else "order"]
        report["configs"][cfg] = {}
        for rpm in CWRU_SPEEDS:
            data, meta = load_config(args.cwru_root, rpm, cfg)
            entry = {"meta": meta,
                     "windows": {k: int(len(v)) for k, v in data.items()}}
            entry["ae"] = evaluate_scores(
                lambda W, ref: window_scores(op, W), data,
                tau_direct=op.tau_mc_, online=True)
            for fam, W in data.items():
                scores[f"{cfg}/{rpm}/{fam}/ae"] = window_scores(op, W)
                for name, feat in FEATURES.items():
                    scores[f"{cfg}/{rpm}/{fam}/{name}"] = feat(W)
            # per-file detection at the oracle radius (defect-size breakdown)
            if meta:
                tau = entry["ae"]["oracle"]["tau"]
                for fam in FAMILIES:
                    s = window_scores(op, data[fam])
                    at = 0
                    for m in (m for m in meta if m.get("family") == fam):
                        seg = s[at:at + m["windows"]]
                        m["ae_oracle_dr"] = pct(seg > tau)
                        m["ae_median"] = float(np.median(seg))
                        at += m["windows"]
            for name in FEATURES:
                entry[name] = evaluate_scores(feature_score(name), data)
            # raw feature medians, to show WHAT separates
            entry["feature_medians"] = {
                name: {k: float(np.median(FEATURES[name](v)))
                       for k, v in data.items()} for name in FEATURES}
            report["configs"][cfg][rpm] = entry
            a = entry["ae"]
            print(f"[{cfg} {rpm}] n_h={entry['windows']['healthy']} "
                  f"AUROC ae={a['auroc']} zcr={entry['zcr']['auroc']} "
                  f"[{time.time() - t0:.0f}s]", flush=True)

    np.savez_compressed(args.out / "scores.npz", **scores)
    path = args.out / "results.json"
    path.write_text(json.dumps(report, indent=1))
    print("wrote", path)


if __name__ == "__main__":
    main()
