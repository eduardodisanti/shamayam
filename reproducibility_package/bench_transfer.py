#!/usr/bin/env python3
"""
Factory model learned on a real test bench (CWRU healthy data) and deployed on
machines it never saw (IMS, Ottawa). Registered protocol:
mssp_paper/notas/06_protocolo_banco.md (v1, approved 14-oct). Nothing here may
be tuned after looking at the target results without a new protocol version.

Two stages, run separately so the bench diagnostics are read before any
target is scored:

  python3 bench_transfer.py train      # bench models + bench-only diagnostics
  python3 bench_transfer.py evaluate   # score IMS and Ottawa

Variants (same architecture and schedule as the published shared operator):
  bench_q    CWRU healthy, angular projection, augmented over G
  bench_qg   the same, then per-window offset/gain normalisation (section qg)
  noise_qg   control: Gaussian white noise, normalised (a bench with no
             structure); separates learned bench shape from architecture
Seeds: 42, 0, 1, 2, 3 (those of the simulator OEM runs).

Bench data: {rpm}_Normal.npz, DE channel, 48 kHz, the four loads. Speed
estimated per record; 400 samples/rev, 3-rev windows. First 80% of each
projected record for training, last 20% for validation, no overlap; 4000 and
1000 augmented windows (any start = phase; gain U(0.75,1.25); offset
+-0.1 RMS; noise 0-5% RMS). Learning check: collapse only (> 0.98
unexplained), recorded; not applied to the noise control.
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

from mssp_repro.datasets import loader_root, provenance
from mssp_repro.field.order_domain import (ORDER_WINDOW, angular_resample,
                                           order_windows, project_signal)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "bench"
# Weights are not committed. SHAMAYAM_MODELS_ROOT relocates them (16-oct);
# unset, the location of the registered run is kept.
MODELS = Path(os.environ.get("SHAMAYAM_MODELS_ROOT", "/home/claude/work")) / "bench_models"
SEEDS = (42, 0, 1, 2, 3)
VARIANTS = ("bench_q", "bench_qg", "noise_qg")
RPMS = ("1797", "1772", "1750", "1730")
FS_NORMAL = 48000
TRAIN_FRACTION = 0.8
N_TRAIN, N_VAL = 4000, 1000
COLLAPSE_LEVEL = 0.98


def gain_section(W):
    W = W - W.mean(axis=1, keepdims=True)
    return (W / np.sqrt(np.mean(W ** 2, axis=1, keepdims=True))).astype(np.float32)


def augment(records, n, rng):
    lens = np.array([len(r) for r in records])
    rms = float(np.sqrt(np.mean(np.concatenate(records) ** 2)))
    r = rng.choice(len(records), size=n, p=lens / lens.sum())
    out = np.empty((n, ORDER_WINDOW), dtype=np.float32)
    for j, i in enumerate(r):
        s = rng.integers(0, lens[i] - ORDER_WINDOW + 1)
        out[j] = records[i][s:s + ORDER_WINDOW]
    out *= rng.uniform(0.75, 1.25, (n, 1))
    out += rng.uniform(-0.1, 0.1, (n, 1)) * rms
    out += rng.standard_normal(out.shape) * rng.uniform(0, 0.05, (n, 1)) * rms
    return out


def bench_records():
    root = loader_root("CWRU_Bearing_NumPy")
    train, val, meta = [], [], []
    for rpm in RPMS:
        with np.load(root / f"{rpm} RPM" / f"{rpm}_Normal.npz") as d:
            x = np.asarray(d["DE"], dtype=np.float64).reshape(-1)
        y, shaft = project_signal(x, FS_NORMAL, int(rpm) / 60.0)
        cut = int(TRAIN_FRACTION * len(y))
        train.append(y[:cut])
        val.append(y[cut:])
        meta.append({"rpm": rpm, "shaft_hz": shaft, "seconds": len(x) / FS_NORMAL,
                     "train_samples": cut, "val_samples": len(y) - cut})
    return train, val, meta


def build_sets(variant, seed, train, val):
    rng = np.random.default_rng(7000 + seed)
    if variant == "noise_qg":
        Xtr = rng.standard_normal((N_TRAIN, ORDER_WINDOW))
        Xva = rng.standard_normal((N_VAL, ORDER_WINDOW))
        return gain_section(Xtr), gain_section(Xva)
    Xtr, Xva = augment(train, N_TRAIN, rng), augment(val, N_VAL, rng)
    if variant == "bench_qg":
        return gain_section(Xtr), gain_section(Xva)
    return Xtr, Xva


def make_operator(seed, **kw):
    from mssp_repro.field.shared_operator import SharedFieldOperator
    return SharedFieldOperator(archive="nasa", seed=seed, **kw)


def train_one(variant, seed, train, val, kw):
    import mssp_repro.field.shared_operator as so
    Xtr, Xva = build_sets(variant, seed, train, val)
    queue = [Xtr, Xva]
    gate = {}

    def gen(n, **k):
        X = queue.pop(0)
        assert len(X) == n, (len(X), n)
        return X

    def lenient(mse, var, validation_mse=None, name="operator"):
        gate["unexplained_val"] = float(mse / var)
        if variant != "noise_qg" and mse / var > COLLAPSE_LEVEL:
            raise RuntimeError(f"collapsed ({mse / var:.3f})")

    orig_gen, orig_gate = so.generate_oem_windows, so.assert_operator_learned
    so.generate_oem_windows, so.assert_operator_learned = gen, lenient
    try:
        op = make_operator(seed, **kw).fit(n_train=N_TRAIN, n_val=N_VAL)
        learned = True
    except RuntimeError:
        op, learned = None, False
    finally:
        so.generate_oem_windows, so.assert_operator_learned = orig_gen, orig_gate
    diag = {"variant": variant, "seed": seed, "learned": learned, **gate}
    if op is not None:
        h = op.history_
        diag.update(epochs_run=h["epochs_run"], best_val_loss=h["best_val_loss"],
                    best_train_loss=float(min(h["loss"])),
                    generalisation_gap=float(h["best_val_loss"] / min(h["loss"])))
        d = MODELS / f"{variant}_seed{seed}"
        d.mkdir(parents=True, exist_ok=True)
        op.ae_.save_weights(d / "ae.weights.h5")
        np.savez(d / "scaler.npz", mean=op.scaler_.mean_, scale=op.scaler_.scale_)
    return diag


class LoadedOperator:
    def __init__(self, variant, seed):
        from mssp_repro.conv_autoencoder import build_autoencoder
        from mssp_repro.field.shared_operator import LATENT_DIM, SIG_LEN
        d = MODELS / f"{variant}_seed{seed}"
        self.ae, _ = build_autoencoder(SIG_LEN, LATENT_DIM)
        self.ae.load_weights(d / "ae.weights.h5")
        z = np.load(d / "scaler.npz")
        self.mean, self.scale = z["mean"], z["scale"]
        self.qg = variant.endswith("_qg")

    def scores(self, W):
        W = gain_section(W) if self.qg else np.asarray(W, dtype=np.float32)
        X = ((W - self.mean) / self.scale).astype(np.float32)[..., None]
        rec = self.ae.predict(X, verbose=0, batch_size=512)
        return np.mean(np.square(X - rec), axis=(1, 2))


def cmd_train(args):
    MODELS.mkdir(parents=True, exist_ok=True)
    train, val, meta = bench_records()
    kw = {} if args.epochs is None else {"epochs": args.epochs}
    rep = {"protocol": "06_protocolo_banco.md v1 (14-oct)",
           "bench": provenance("CWRU_Bearing_NumPy"), "records": meta,
           "n_train": N_TRAIN, "n_val": N_VAL, "seeds": list(SEEDS),
           "diagnostics": []}
    t0 = time.time()
    for variant in VARIANTS:
        for seed in SEEDS:
            d = train_one(variant, seed, train, val, kw)
            rep["diagnostics"].append(d)
            print(f"[{variant} seed {seed}] {d} [{time.time() - t0:.0f}s]",
                  flush=True)
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "training.json").write_text(json.dumps(rep, indent=1) + "\n")


def cmd_evaluate(args):
    import ims_quotient_learning_curve as lc
    import ottawa_variable_speed as ov
    from mssp_repro.field.ims import IMS_CHANNELS, IMS_SAMPLE_RATE_HZ, load_experiment
    from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                            flag_inactive_recordings, load_cache)
    t0 = time.time()
    log = lambda m: print(f"{m} [{time.time() - t0:.0f}s]", flush=True)
    diag = json.loads((OUT / "training.json").read_text())["diagnostics"]
    ok = {(d["variant"], d["seed"]) for d in diag if d["learned"]}

    # ---- IMS: projected windows per bearing
    signals, _, _ = load_experiment(loader_root("NASA_IMS_Bearings"), 2)
    pub = np.asarray(load_cache(HERE / "results" / "field_residuals_ims.npz")
                     ["scores"], dtype=float)
    ims = {}
    for b in (1, 2, 3, 4):
        (col,) = IMS_CHANNELS[2][b]
        X = signals[:, :, col].astype(np.float64)
        WQ = np.stack([order_windows(angular_resample(x, IMS_SAMPLE_RATE_HZ,
                                                      lc.SHAFT_HZ)) for x in X])
        inactive = flag_inactive_recordings(pub[b - 1], warmup=FIELD_WARMUP_RECORDINGS)
        n_active = X.shape[0]
        while n_active > 0 and inactive[n_active - 1]:
            n_active -= 1
        ims[b] = (WQ.astype(np.float32), n_active)
    log("IMS projected")

    # ---- Ottawa
    data = ov.load_all(loader_root("Ottawa_Bearing_TimeVaryingSpeed"), log)
    test_h = [f"H-{p}-{t}" for p in ov.PROFILES for t in (2, 3)]
    faults = {c: [f"{c}-{p}-{t}" for p in ov.PROFILES for t in ov.TRIALS]
              for c in ov.FAULTS}

    rep = {"protocol": "06_protocolo_banco.md v1 (14-oct)",
           "ims_ns": list(lc.NS), "far_window": list(lc.FAR_WINDOW),
           "runs": {}}
    window_scores = {}
    for variant in VARIANTS:
        for seed in SEEDS:
            if (variant, seed) not in ok:
                rep["runs"][f"{variant}/{seed}"] = {"learned": False}
                continue
            op = LoadedOperator(variant, seed)
            run = {"learned": True, "ims": {}, "ottawa": {}}
            for b, (WQ, n_active) in ims.items():
                s = op.scores(WQ.reshape(-1, WQ.shape[-1])).reshape(WQ.shape[:2]).mean(1)
                run["ims"][str(b)] = [lc.evaluate(s, n, n_active) for n in lc.NS]
                window_scores[f"ims/{variant}/{seed}/{b}"] = s.astype(np.float32)
            ov.SCORES.clear()
            cache = {}

            def f(d, r, op=op, cache=cache):
                if d["key"] not in cache:
                    cache[d["key"]] = op.scores(d["WQ"])
                return cache[d["key"]]
            for sc, profiles in (("ABCD1", ["A", "B", "C", "D"]), ("A1", ["A"])):
                comm = [f"H-{p}-1" for p in profiles]
                run["ottawa"][sc] = ov.evaluate(f, "q", data, comm, test_h, faults,
                                                label=sc)
            for k, v in cache.items():
                window_scores[f"ottawa/{variant}/{seed}/{k}"] = v.astype(np.float32)
            rep["runs"][f"{variant}/{seed}"] = run
            r1 = run["ims"]["1"][1]
            log(f"[{variant} {seed}] IMS b1 n=99 dep {r1['departure']} FAR "
                f"{r1['far_k']}/{r1['far_n']} | Ottawa ABCD1 FAR "
                f"{run['ottawa']['ABCD1']['far_k']}/{run['ottawa']['ABCD1']['far_n']}")
            (OUT / "evaluation.json").write_text(json.dumps(rep, indent=1) + "\n")
    for k, v in data.items():
        window_scores[f"ottawa_speed/{k}"] = v["S"].astype(np.float32)
    np.savez_compressed(OUT / "window_scores.npz", **window_scores)
    (OUT / "evaluation.json").write_text(json.dumps(rep, indent=1) + "\n")
    log("wrote " + str(OUT))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=("train", "evaluate"))
    ap.add_argument("--epochs", type=int, default=None, help="smoke tests only")
    ap.add_argument("--smoke", action="store_true",
                    help="one seed per variant, into a scratch folder")
    args = ap.parse_args()
    if args.smoke:
        global SEEDS, OUT, MODELS
        SEEDS, OUT, MODELS = (42,), Path("/tmp/claude-0/bench_smoke"), \
            Path("/tmp/claude-0/bench_smoke/models")
    cmd_train(args) if args.stage == "train" else cmd_evaluate(args)


if __name__ == "__main__":
    main()
