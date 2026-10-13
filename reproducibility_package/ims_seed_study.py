#!/usr/bin/env python3
"""
IMS: seed variability of the learning-curve comparison.

Adds seeds to ims_quotient_learning_curve.py (whose run is seed 0 for the
per-machine arms and seed 42 for the OEM operator), with the identical
protocol:

  oem_q   OEM operator in the quotient, retrained with each seed; all four
          bearings, all commissioning lengths
  raw     per-machine autoencoder on raw windows      } bearings 1 and 4
  quot    per-machine autoencoder in the quotient     } (where the arms
                                                        differ), all lengths

Bearings 2 and 3 are left out of the per-machine arms: every arm gives about
0% false alarms on them in the seed-0 run, so further seeds there would add
time without information.

Usage: python3 ims_seed_study.py [--ims-root PATH]
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from mssp_repro.datasets import dataset_arg
import ims_quotient_learning_curve as lc
from mssp_repro.field.cwru_operator import AssetSpecificOperator
from mssp_repro.field.ims import (IMS_CHANNELS, IMS_SAMPLE_RATE_HZ,
                                  load_experiment, make_windows)
from mssp_repro.field.order_domain import angular_resample, order_windows
from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                        flag_inactive_recordings, load_cache)

OEM_SEEDS = (0, 1, 2, 3)            # 42 is in learning_curve.json
LOCAL_SEEDS = (1, 2, 3, 4)          # 0 is in learning_curve.json
LOCAL_BEARINGS = (1, 4)
HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "ims_quotient" / "seeds.json"


def bearing_views(signals, pub, b):
    (col,) = IMS_CHANNELS[2][b]
    X = signals[:, :, col].astype(np.float64)
    n_active = X.shape[0]
    inactive = flag_inactive_recordings(pub[b - 1],
                                        warmup=FIELD_WARMUP_RECORDINGS)
    while n_active > 0 and inactive[n_active - 1]:
        n_active -= 1
    P = np.stack([angular_resample(x, IMS_SAMPLE_RATE_HZ, lc.SHAFT_HZ)
                  for x in X])
    WQ = np.stack([order_windows(p) for p in P]).astype(np.float32)
    WR = np.stack([make_windows(x, 1200, 1200) for x in X]).astype(np.float32)
    return n_active, P, WQ, WR


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ims-root", **dataset_arg("NASA_IMS_Bearings"))
    ap.add_argument("--cache-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    t0 = time.time()
    log = lambda m: print(f"{m} [{time.time() - t0:.0f}s]", flush=True)
    signals, _, _ = load_experiment(args.ims_root, 2, cache_dir=args.cache_dir)
    pub = np.asarray(load_cache(HERE / "results" / "field_residuals_ims.npz")
                     ["scores"], dtype=float)
    rep = {"ns": list(lc.NS), "far_window": list(lc.FAR_WINDOW),
           "oem_q": {}, "raw": {}, "quot": {}}

    def save():
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, indent=1) + "\n")

    views = {}
    for b in (1, 2, 3, 4):
        views[b] = bearing_views(signals, pub, b)
    log("projected all bearings")

    for seed in OEM_SEEDS:
        oem = lc.OrderDomainNasaOperator(archive="nasa", seed=seed).fit()
        e = {"training": {k: v for k, v in oem.history_.items()
                          if k not in ("loss", "val_loss")}, "bearings": {}}
        for b, (n_active, P, WQ, WR) in views.items():
            s = lc.recording_scores(lambda w: oem._window_mse(
                oem.scaler_.transform(w).astype(np.float32)[..., None]),
                WQ, WQ.shape[1])
            e["bearings"][str(b)] = [lc.evaluate(s, n, n_active)
                                     for n in lc.NS]
        rep["oem_q"][str(seed)] = e
        save()
        log(f"oem_q seed {seed}: {oem.describe_training()}")

    import mssp_repro.field.cwru_operator as co
    co.assert_operator_learned = lc._lenient_gate
    for seed in LOCAL_SEEDS:
        for arm in ("raw", "quot"):
            rep[arm].setdefault(str(seed), {})
        for b in LOCAL_BEARINGS:
            n_active, P, WQ, WR = views[b]
            for arm in ("raw", "quot"):
                rows = []
                for n in lc.NS:
                    if arm == "raw":
                        Xtr = WR[:n].reshape(-1, WR.shape[-1])
                    else:
                        Xtr = lc.augment(P[:n], lc.N_AUG, np.random.default_rng(
                            100000 * seed + 1000 * b + n))
                    try:
                        op = AssetSpecificOperator(seed=seed).fit(Xtr)
                    except RuntimeError:
                        rows.append({"n": n, "learned": False})
                        log(f"[s{seed} b{b} n={n} {arm}] collapsed")
                        continue
                    W = WR if arm == "raw" else WQ
                    sc = lc.recording_scores(op.scores, W, W.shape[1])
                    r = lc.evaluate(sc, n, n_active)
                    r.update(learned=True,
                             gap=op.history_["generalisation_gap"],
                             unexplained=lc._gate.get("unexplained"))
                    rows.append(r)
                    log(f"[s{seed} b{b} n={n} {arm}] FAR "
                        f"{r['far_k']}/{r['far_n']} dep {r['departure']}")
                rep[arm][str(seed)][str(b)] = rows
                save()
    log("wrote " + str(args.out))


if __name__ == "__main__":
    main()
