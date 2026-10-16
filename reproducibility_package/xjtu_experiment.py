#!/usr/bin/env python3
"""
XJTU-SY: fifteen real run-to-failure bearings. Registered protocol:
mssp_paper/notas/09_protocolo_xjtu.md (16-oct). Nothing here may be tuned
after looking at XJTU results without a new protocol version.

Stages (each resumable; results/xjtu/ is written after every unit of work):

  python3 xjtu_experiment.py cache        # parse the CSVs once into .npy
  python3 xjtu_experiment.py classical    # RMS, kurtosis, crest, envelope
  python3 xjtu_experiment.py factory      # oem_q and bench_q, 5 seeds each
  python3 xjtu_experiment.py local --seed S   # per-machine raw / quot, H only

Section q (as IMS): nominal shaft speed of the condition, angular resampling
to 400 samples/rev, 3-rev windows (14, 16, 17 per record), one score per
record = mean window residual. Both channels for training-free and factory
arms; per-machine arms on the horizontal channel only (fixed in advance, for
compute). Verdicts are in xjtu_report.py.

Heavy artefacts (parsed cache, model weights) go under $SHAMAYAM_RUNS
(default /Volumes/SAMSUNG-1/shamayam_runs), never into the repository.
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

from mssp_repro.datasets import dataset_arg, provenance
from mssp_repro.field.order_domain import angular_resample, order_windows
from mssp_repro.field.xjtu import (BEARINGS, CHANNELS, LIFE_RECORDS, XJTU_FS,
                                   load_bearing, shaft_hz)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "xjtu"
RUNS = Path(os.environ.get("SHAMAYAM_RUNS", "/Volumes/SAMSUNG-1/shamayam_runs"))
CACHE = RUNS / "cache" / "xjtu"
MODELS = RUNS / "models" / "xjtu"
DATASET = "XJTU-SY_Bearing_Datasets"

FACTORY_SEEDS = (42, 0, 1, 2, 3)
LOCAL_SEEDS = (0, 1, 2, 3, 4)
LOCAL_NS = (49, 99)
PERSIST = 10                 # records needed after commissioning (8 of 10)
N_AUG = 4000


def commissionable(n):
    return [b for b in BEARINGS if LIFE_RECORDS[b] >= n + PERSIST]


def projected(X, b, channels=CHANNELS):
    """{channel: (P, WQ)} with P the projected records, WQ their windows."""
    out = {}
    for c, ch in enumerate(CHANNELS):
        if ch not in channels:
            continue
        P = np.stack([angular_resample(x, XJTU_FS, shaft_hz(b))
                      for x in np.asarray(X[:, :, c], dtype=np.float64)])
        out[ch] = (P, np.stack([order_windows(p) for p in P]).astype(np.float32))
    return out


def record_scores(score_windows, WQ):
    s = score_windows(WQ.reshape(-1, WQ.shape[-1]))
    return np.asarray(s, dtype=np.float64).reshape(WQ.shape[:2]).mean(axis=1)


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1) + "\n")
    tmp.replace(path)


def _savez(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez_compressed(tmp, **d)
    tmp.replace(path)


# ------------------------------------------------------------------ stages

def cmd_cache(args, log):
    for b in args.bearings:
        X = load_bearing(args.root, b, cache_dir=CACHE)
        log(f"cache {b}: {X.shape}")


def cmd_classical(args, log):
    from ims_classical_features import ORDERS, envelope_peak_ratio
    from scipy.stats import kurtosis
    series = {}
    for b in args.bearings:
        X = load_bearing(args.root, b, cache_dir=CACHE)
        for c, ch in enumerate(CHANNELS):
            x = np.asarray(X[:, :, c], dtype=np.float64)
            rms = np.sqrt(np.mean(x ** 2, axis=1))
            series[f"{b}/{ch}/rms"] = rms
            series[f"{b}/{ch}/kurtosis"] = kurtosis(x, axis=1)
            series[f"{b}/{ch}/crest"] = np.max(np.abs(x), axis=1) / rms
            series[f"{b}/{ch}/envelope"] = np.array(
                [envelope_peak_ratio(r, fs=XJTU_FS, shaft=shaft_hz(b)) for r in x])
        log(f"classical {b}")
    _savez(OUT / "classical.npz", series)
    _write(OUT / "classical.json", {"protocol": "09_protocolo_xjtu.md",
                                    "data": provenance(DATASET),
                                    "envelope_orders": list(ORDERS),
                                    "bearings": args.bearings})


def _factory_models(kw, log, done):
    """Yield (name, seed, score_windows, diagnostics); trains what is missing."""
    import bench_transfer as v1
    import ims_quotient_learning_curve as lc
    v1.MODELS = MODELS / "bench_v1"
    train = val = None
    for seed in FACTORY_SEEDS:
        if f"oem_q/{seed}" not in done:
            oem = lc.OrderDomainNasaOperator(archive="nasa", seed=seed, **kw).fit()
            d = MODELS / f"oem_q_seed{seed}"
            d.mkdir(parents=True, exist_ok=True)
            oem.ae_.save_weights(d / "ae.weights.h5")
            np.savez(d / "scaler.npz", mean=oem.scaler_.mean_, scale=oem.scaler_.scale_)
            diag = {"model": "oem_q", "seed": seed, "learned": True,
                    **{k: v for k, v in oem.history_.items()
                       if k not in ("loss", "val_loss")}}
            log(f"oem_q seed {seed}: {oem.describe_training()}")
            yield "oem_q", seed, (lambda W, o=oem: o._window_mse(
                o.scaler_.transform(W).astype(np.float32)[..., None])), diag
    for seed in FACTORY_SEEDS:
        if f"bench_q/{seed}" not in done:
            if train is None:
                train, val, _ = v1.bench_records()
            diag = v1.train_one("bench_q", seed, train, val, kw)
            diag = {"model": "bench_q", **{k: v for k, v in diag.items()
                                           if k != "variant"}}
            log(f"bench_q seed {seed}: {diag}")
            fn = v1.LoadedOperator("bench_q", seed).scores if diag["learned"] else None
            yield "bench_q", seed, fn, diag


def cmd_factory(args, log):
    kw = {} if args.epochs is None else {"epochs": args.epochs}
    tpath, spath = OUT / "factory_training.json", OUT / "factory_scores.npz"
    T = json.loads(tpath.read_text()) if tpath.exists() else {
        "protocol": "09_protocolo_xjtu.md", "data": provenance(DATASET),
        "bench": provenance("CWRU_Bearing_NumPy"), "diagnostics": []}
    S = dict(np.load(spath)) if spath.exists() else {}
    done = {f"{d['model']}/{d['seed']}" for d in T["diagnostics"]}
    views = {}
    for name, seed, fn, diag in _factory_models(kw, log, done):
        if fn is not None:
            for b in args.bearings:
                if b not in views:
                    views[b] = {ch: WQ for ch, (_, WQ) in projected(
                        load_bearing(args.root, b, cache_dir=CACHE), b).items()}
                for ch in CHANNELS:
                    S[f"{name}/{seed}/{b}/{ch}"] = record_scores(
                        fn, views[b][ch]).astype(np.float32)
        T["diagnostics"].append(diag)
        _savez(spath, S)
        _write(tpath, T)
        log(f"scored {name} seed {seed}")


def cmd_local(args, log):
    import ims_quotient_learning_curve as lc
    import mssp_repro.field.cwru_operator as co
    from mssp_repro.field.cwru_operator import AssetSpecificOperator
    from mssp_repro.field.ims import make_windows
    kw = {} if args.epochs is None else {"epochs": args.epochs}
    co.assert_operator_learned = lc._lenient_gate
    seed = args.seed
    path = OUT / "local" / f"seed{seed}.json"
    rep = json.loads(path.read_text()) if path.exists() else {
        "protocol": "09_protocolo_xjtu.md", "data": provenance(DATASET),
        "seed": seed, "channel": "H", "ns": list(LOCAL_NS), "n_aug": N_AUG,
        "runs": {}}
    order = list(BEARINGS)
    for b in args.bearings:
        todo = [(n, arm) for n in LOCAL_NS if b in commissionable(n)
                for arm in ("raw", "quot") if f"{b}/{n}/{arm}" not in rep["runs"]]
        if not todo:
            continue
        X = load_bearing(args.root, b, cache_dir=CACHE)
        xh = np.asarray(X[:, :, 0], dtype=np.float64)
        P, WQ = projected(X, b, ("H",))["H"]
        WR = np.stack([make_windows(x, 1200, 1200) for x in xh]).astype(np.float32)
        for n, arm in todo:
            t1 = time.time()
            if arm == "raw":
                Xtr = WR[:n].reshape(-1, WR.shape[-1])
            else:
                Xtr = lc.augment(P[:n], N_AUG, np.random.default_rng(
                    100000 * seed + 1000 * order.index(b) + n))
            try:
                op = AssetSpecificOperator(seed=seed, **kw).fit(Xtr)
                W = WR if arm == "raw" else WQ
                r = {"learned": True, "unexplained": lc._gate.get("unexplained"),
                     "gap": op.history_["generalisation_gap"],
                     "epochs_run": op.history_["epochs_run"],
                     "scores": [float(v) for v in record_scores(op.scores, W)]}
            except RuntimeError:
                r = {"learned": False}
            r["seconds"] = round(time.time() - t1, 1)
            rep["runs"][f"{b}/{n}/{arm}"] = r
            _write(path, rep)
            log(f"[seed {seed} {b} n={n} {arm}] learned={r['learned']} "
                f"({r['seconds']} s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=("cache", "classical", "factory", "local"))
    ap.add_argument("--root", **dataset_arg(DATASET))
    ap.add_argument("--bearings", default=",".join(BEARINGS))
    ap.add_argument("--seed", type=int, default=0, help="local stage")
    ap.add_argument("--epochs", type=int, default=None, help="smoke tests only")
    ap.add_argument("--out", type=Path, default=None, help="smoke tests only")
    args = ap.parse_args()
    args.bearings = [b for b in args.bearings.split(",") if b]
    global OUT
    if args.out is not None:
        OUT = args.out
    t0 = time.time()
    log = lambda m: print(f"{m} [{time.time() - t0:.0f}s]", flush=True)
    {"cache": cmd_cache, "classical": cmd_classical, "factory": cmd_factory,
     "local": cmd_local}[args.stage](args, log)


if __name__ == "__main__":
    main()
