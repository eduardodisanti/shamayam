#!/usr/bin/env python3
"""
Registered protocol v3 (mssp_paper/notas/10_protocolo_banco_v3.md, 16-oct):
the factory model learned on the CWRU bench with the FULL quotient of v2
(cepstral prewhitening per record in Hz, then angular resampling), but seen
through a representation the autoencoder can reconstruct: the squared-
envelope spectrum (SES) in orders. v1 and v2 are untouched.

  python3 bench_transfer_v3.py train      # bench, controls, ceiling; diagnostics
  python3 bench_transfer_v3.py evaluate   # IMS, Ottawa and XJTU

Representation s of a 30-revolution window (12000 samples at 400/rev):
  squared envelope |hilbert(x)|^2 of the window; its spectrum by Welch (Hann
  segments of 10 rev, hop 5 rev, mean removed per segment), the 1200 bins of
  orders 0.1 ... 120 (no DC), s = log(SES / median(SES)). 1200 values: the
  input length of the published architecture, which is not changed.

Models (5 seeds each; architecture, schedule, split, augmentation and
collapse check of v1/v2):
  bench_s    CWRU healthy (prewhitened + angular)            (H1v3, H2v3, H3v3)
  noise_s    control: white Gaussian noise, same representation
  sim_s      control: the simulator (Ottawa parameters, records of 2.2 s for
             30 revolutions), prewhitened before resampling at its known speed
  local_s    ceiling: per-machine model on Ottawa's four trial-1 records
Classical references on the same 30-rev prewhitened windows, no training:
kurtosis (kurt_s) and the envelope indicator, orders 2-20 (env_s).

Model weights go under $SHAMAYAM_RUNS/models/bench_v3 so that, this time,
they are kept.
"""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
from scipy.signal import hilbert
from scipy.stats import kurtosis

import bench_transfer as v1
import bench_transfer_v2 as v2
from mssp_repro.datasets import loader_root, provenance
from mssp_repro.field.order_domain import (SAMPLES_PER_REV, angular_resample,
                                           angular_resample_varying,
                                           order_windows, prewhiten)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "bench_v3"
RUNS = Path(os.environ.get("SHAMAYAM_RUNS", "/Volumes/SAMSUNG-1/shamayam_runs"))
MODELS = RUNS / "models" / "bench_v3"
SEEDS = (42, 0, 1, 2, 3)
LOCAL_SEEDS = (0, 1, 2, 3, 4)
VARIANTS = ("bench_s", "noise_s", "sim_s")
PROTOCOL = "10_protocolo_banco_v3.md (16-oct)"
REVS = 30
WIN = REVS * SAMPLES_PER_REV            # 12000
SEG_REVS, HOP_REVS = 10, 5
SEG, HOP = SEG_REVS * SAMPLES_PER_REV, HOP_REVS * SAMPLES_PER_REV
N_BINS = 1200                           # orders 0.1 ... 120 (resolution 1/10)
SIM_DURATION = 2.2                      # s; >= 30 rev at the slowest draw
ENV_ORDERS = (2.0, 20.0)
CHUNK = 500


# ------------------------------------------------------------------ representation

def ses(W):
    """(n, 12000) time windows -> (n, 1200): log of the squared-envelope
    spectrum over its median, orders 0.1 ... 120. The envelope is taken on the
    whole 30-rev window; its spectrum is a Welch estimate (Hann segments of
    10 rev, hop 5 rev: 5 segments), which divides the variance of a bin by
    about four with respect to a single periodogram."""
    out = np.empty((len(W), N_BINS), dtype=np.float32)
    han = np.hanning(SEG)
    starts = range(0, WIN - SEG + 1, HOP)
    for i in range(0, len(W), CHUNK):
        X = np.asarray(W[i:i + CHUNK], dtype=np.float64)
        X = X - X.mean(axis=1, keepdims=True)
        env = np.abs(hilbert(X, axis=1)) ** 2
        P = 0.0
        for s0 in starts:
            seg = env[:, s0:s0 + SEG]
            seg = seg - seg.mean(axis=1, keepdims=True)
            P = P + np.abs(np.fft.rfft(seg * han, axis=1)) ** 2
        P = P[:, 1:N_BINS + 1]
        med = np.median(P, axis=1, keepdims=True)
        out[i:i + CHUNK] = np.log(np.maximum(P, 1e-12 * med) / med)
    return out


def windows30(y):
    return order_windows(y, revs=REVS)


def augment(records, n, rng):
    """v1's augmentation (phase, gain, offset, noise) on 30-rev windows."""
    lens = np.array([len(r) for r in records])
    rms = float(np.sqrt(np.mean(np.concatenate(records) ** 2)))
    r = rng.choice(len(records), size=n, p=lens / lens.sum())
    out = np.empty((n, WIN), dtype=np.float32)
    for j, i in enumerate(r):
        s = rng.integers(0, lens[i] - WIN + 1)
        out[j] = records[i][s:s + WIN]
    out *= rng.uniform(0.75, 1.25, (n, 1))
    out += rng.uniform(-0.1, 0.1, (n, 1)) * rms
    out += rng.standard_normal(out.shape) * rng.uniform(0, 0.05, (n, 1)) * rms
    return out


def sim_windows(n):
    from ottawa_variable_speed import OTTAWA_PARAMS
    from mssp_repro.field.order_domain import OrderDomainSimulator
    sim = OrderDomainSimulator(OTTAWA_PARAMS, duration=SIM_DURATION)
    out = np.empty((n, WIN), dtype=np.float32)
    for i in range(n):
        sig = np.random.uniform(0.8, 1.2, 5)
        x = sim.sim.sample(regime="healthy", mc=True, coverage="wide",
                           asset_signature=sig)
        shaft = sim.params.shaft_freq * sim.sim.last_speed
        y = angular_resample(prewhiten(x), sim.params.fs, shaft)
        if len(y) < sim.offset + WIN:
            raise ValueError("simulated record too short for 30 revolutions")
        out[i] = y[sim.offset:sim.offset + WIN]
    return out


def build_sets(variant, seed, train, val):
    rng = np.random.default_rng(7000 + seed)
    if variant == "noise_s":
        return (ses(rng.standard_normal((v1.N_TRAIN, WIN))),
                ses(rng.standard_normal((v1.N_VAL, WIN))))
    if variant == "sim_s":
        np.random.seed(9000 + seed)
        return ses(sim_windows(v1.N_TRAIN)), ses(sim_windows(v1.N_VAL))
    return ses(augment(train, v1.N_TRAIN, rng)), ses(augment(val, v1.N_VAL, rng))


# ------------------------------------------------------------------ training

def _save(name, ae, scaler):
    p = MODELS / name
    p.mkdir(parents=True, exist_ok=True)
    ae.save_weights(p / "ae.weights.h5")
    np.savez(p / "scaler.npz", mean=scaler.mean_, scale=scaler.scale_)


def train_shared(variant, seed, train, val, kw):
    import mssp_repro.field.shared_operator as so
    Xtr, Xva = build_sets(variant, seed, train, val)
    queue, gate = [Xtr, Xva], {}

    def gen(n, **k):
        X = queue.pop(0)
        assert len(X) == n
        return X

    def lenient(mse, var, validation_mse=None, name="operator"):
        gate["unexplained_val"] = float(mse / var)
        if variant != "noise_s" and mse / var > v1.COLLAPSE_LEVEL:
            raise RuntimeError("collapsed")

    orig = so.generate_oem_windows, so.assert_operator_learned
    so.generate_oem_windows, so.assert_operator_learned = gen, lenient
    try:
        op = v1.make_operator(seed, **kw).fit(n_train=v1.N_TRAIN, n_val=v1.N_VAL)
    except RuntimeError:
        op = None
    finally:
        so.generate_oem_windows, so.assert_operator_learned = orig
    d = {"model": variant, "seed": seed, "learned": op is not None, **gate}
    if op is not None:
        h = op.history_
        d.update(epochs_run=h["epochs_run"], best_val_loss=h["best_val_loss"],
                 generalisation_gap=float(h["best_val_loss"] / min(h["loss"])))
        _save(f"{variant}_seed{seed}", op.ae_, op.scaler_)
    return d


def ottawa_data(log):
    """Per record: prewhitened in Hz, encoder projection, 30-rev windows."""
    import ottawa_variable_speed as ov
    from mssp_repro.field.ottawa import OTTAWA_FS, encoder_angle, load_record
    root = loader_root("Ottawa_Bearing_TimeVaryingSpeed")
    data = {}
    for cond in ("H",) + ov.FAULTS:
        for p in ov.PROFILES:
            for t in ov.TRIALS:
                x, e = load_record(root, cond, p, t)
                tt, th = encoder_angle(e, OTTAWA_FS)
                y, speed = angular_resample_varying(prewhiten(x), OTTAWA_FS, tt, th)
                W = windows30(y)
                key = f"{cond}-{p}-{t}"
                data[key] = dict(key=key, T=W.astype(np.float32), WQ=ses(W),
                                 S=windows30(speed).mean(axis=1), y=y)
    log("Ottawa prewhitened, projected, 30-rev windows")
    return data


def train_local(seed, data, kw):
    import ims_quotient_learning_curve as lc
    import mssp_repro.field.cwru_operator as co
    from mssp_repro.field.cwru_operator import AssetSpecificOperator
    rng = np.random.default_rng(1000 + seed)
    comm = [f"H-{p}-1" for p in ("A", "B", "C", "D")]
    Xtr = ses(augment([data[k]["y"] for k in comm], v1.N_TRAIN, rng))
    co.assert_operator_learned = lc._lenient_gate
    try:
        op = AssetSpecificOperator(seed=seed, **kw).fit(Xtr)
    except RuntimeError:
        return {"model": "local_s", "seed": seed, "learned": False}, None
    return {"model": "local_s", "seed": seed, "learned": True,
            "unexplained": lc._gate.get("unexplained"),
            "generalisation_gap": op.history_["generalisation_gap"]}, op


def cmd_train(args):
    MODELS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    kw = {} if args.epochs is None else {"epochs": args.epochs}
    t0 = time.time()
    tpath = OUT / "training.json"
    train, val, meta = v2.bench_records()
    rep = json.loads(tpath.read_text()) if tpath.exists() else {
        "protocol": PROTOCOL, "bench": provenance("CWRU_Bearing_NumPy"),
        "records": meta, "diagnostics": []}
    done = {(d["model"], d["seed"]) for d in rep["diagnostics"]}
    for variant in VARIANTS:
        for seed in SEEDS:
            if (variant, seed) in done:
                continue
            d = train_shared(variant, seed, train, val, kw)
            rep["diagnostics"].append(d)
            print(f"[{variant} {seed}] {d} [{time.time() - t0:.0f}s]", flush=True)
            tpath.write_text(json.dumps(rep, indent=1) + "\n")
    lpath = MODELS / "local_scores.npz"
    local_scores = dict(np.load(lpath)) if lpath.exists() else {}
    data = None
    for seed in LOCAL_SEEDS:
        if ("local_s", seed) in done:
            continue
        data = data or ottawa_data(lambda m: print(m, flush=True))
        d, op = train_local(seed, data, kw)
        rep["diagnostics"].append(d)
        print(f"[local_s {seed}] {d} [{time.time() - t0:.0f}s]", flush=True)
        if op is not None:
            for k, v in data.items():
                local_scores[f"ottawa/local_s/{seed}/{k}"] = \
                    op.scores(v["WQ"]).astype(np.float32)
        np.savez_compressed(lpath, **local_scores)
        tpath.write_text(json.dumps(rep, indent=1) + "\n")


# ------------------------------------------------------------------ evaluation

class Loaded:
    def __init__(self, name):
        from mssp_repro.conv_autoencoder import build_autoencoder
        from mssp_repro.field.shared_operator import LATENT_DIM, SIG_LEN
        p = MODELS / name
        self.ae, _ = build_autoencoder(SIG_LEN, LATENT_DIM)
        self.ae.load_weights(p / "ae.weights.h5")
        z = np.load(p / "scaler.npz")
        self.mean, self.scale = z["mean"], z["scale"]

    def scores(self, S):
        X = ((np.asarray(S, dtype=np.float32) - self.mean) / self.scale
             ).astype(np.float32)[..., None]
        rec = self.ae.predict(X, verbose=0, batch_size=512)
        return np.mean(np.square(X - rec), axis=(1, 2))


def ims_data(log):
    import ims_quotient_learning_curve as lc
    from mssp_repro.field.ims import IMS_CHANNELS, IMS_SAMPLE_RATE_HZ, load_experiment
    from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                            flag_inactive_recordings, load_cache)
    signals, _, _ = load_experiment(loader_root("NASA_IMS_Bearings"), 2)
    pub = np.asarray(load_cache(HERE / "results" / "field_residuals_ims.npz")
                     ["scores"], dtype=float)
    ims = {}
    for b in (1, 2, 3, 4):
        (col,) = IMS_CHANNELS[2][b]
        X = signals[:, :, col].astype(np.float64)
        T = np.stack([windows30(angular_resample(prewhiten(x), IMS_SAMPLE_RATE_HZ,
                                                 lc.SHAFT_HZ)) for x in X])
        inactive = flag_inactive_recordings(pub[b - 1], warmup=FIELD_WARMUP_RECORDINGS)
        n_active = X.shape[0]
        while n_active > 0 and inactive[n_active - 1]:
            n_active -= 1
        ims[b] = dict(T=T.astype(np.float32),
                      S=ses(T.reshape(-1, WIN)).reshape(T.shape[0], T.shape[1], N_BINS),
                      n_active=n_active)
    log("IMS prewhitened, projected, 30-rev windows")
    return ims


def xjtu_data(log, bearings):
    """{bearing: {channel: (T record windows, S ses)}} with T only for the
    classical references (per record, first 30-rev window)."""
    from mssp_repro.field.xjtu import CHANNELS, XJTU_FS, load_bearing, shaft_hz
    import xjtu_experiment as xe
    root = loader_root("XJTU-SY_Bearing_Datasets")
    out = {}
    for b in bearings:
        X = load_bearing(root, b, cache_dir=xe.CACHE)
        out[b] = {}
        for c, ch in enumerate(CHANNELS):
            T = np.stack([windows30(angular_resample(prewhiten(x), XJTU_FS, shaft_hz(b)))
                          for x in np.asarray(X[:, :, c], dtype=np.float64)])
            out[b][ch] = dict(
                kurt=kurtosis(T.reshape(-1, WIN), axis=1).reshape(T.shape[:2]).mean(1),
                env=v2.envelope_indicator(T.reshape(-1, WIN), ENV_ORDERS
                                          ).reshape(T.shape[:2]).mean(1),
                S=ses(T.reshape(-1, WIN)).reshape(T.shape[0], T.shape[1], N_BINS))
        log(f"XJTU {b} prewhitened, projected")
    return out


def cmd_evaluate(args):
    import ims_quotient_learning_curve as lc
    import ottawa_variable_speed as ov
    t0 = time.time()
    log = lambda m: print(f"{m} [{time.time() - t0:.0f}s]", flush=True)
    T = json.loads((OUT / "training.json").read_text())
    ok = {(d["model"], d["seed"]) for d in T["diagnostics"] if d["learned"]}
    ims = ims_data(log)
    data = ottawa_data(log)
    from mssp_repro.field.xjtu import BEARINGS
    xj = xjtu_data(log, args.xjtu_bearings or list(BEARINGS))
    test_h = [f"H-{p}-{t}" for p in ov.PROFILES for t in (2, 3)]
    faults = {c: [f"{c}-{p}-{t}" for p in ov.PROFILES for t in ov.TRIALS]
              for c in ov.FAULTS}
    rep = {"protocol": PROTOCOL, "ims_ns": list(lc.NS),
           "far_window": list(lc.FAR_WINDOW), "runs": {}}
    W = {}

    def run_model(name, seed, score_S, classical=None):
        run = {"learned": True, "ims": {}, "ottawa": {}}
        for b, d in ims.items():
            if classical:
                s = classical(d["T"].reshape(-1, WIN)).reshape(d["T"].shape[:2]).mean(1)
            else:
                s = score_S(d["S"].reshape(-1, N_BINS)).reshape(d["S"].shape[:2]).mean(1)
            run["ims"][str(b)] = [lc.evaluate(s, n, d["n_active"]) for n in lc.NS]
            W[f"ims/{name}/{seed}/{b}"] = s.astype(np.float32)
        cache = {}

        def f(d, r):
            if d["key"] not in cache:
                cache[d["key"]] = classical(d["T"]) if classical else score_S(d["WQ"])
            return cache[d["key"]]
        for sc, profiles in (("ABCD1", ["A", "B", "C", "D"]), ("A1", ["A"])):
            comm = [f"H-{p}-1" for p in profiles]
            run["ottawa"][sc] = ov.evaluate(f, "q", data, comm, test_h, faults)
        for k, v in cache.items():
            W[f"ottawa/{name}/{seed}/{k}"] = np.asarray(v, dtype=np.float32)
        for b, chans in xj.items():
            for ch, d in chans.items():
                if classical:
                    s = d["kurt"] if name == "kurt_s" else d["env"]
                else:
                    s = score_S(d["S"].reshape(-1, N_BINS)).reshape(d["S"].shape[:2]).mean(1)
                W[f"xjtu/{name}/{seed}/{b}/{ch}"] = np.asarray(s, dtype=np.float32)
        rep["runs"][f"{name}/{seed}"] = run
        r1 = run["ims"]["1"][1]
        log(f"[{name} {seed}] IMS b1 n=99 dep {r1['departure']} FAR {r1['far_k']}/300 | "
            f"Ottawa ABCD1 FAR {run['ottawa']['ABCD1']['far_k']}/{run['ottawa']['ABCD1']['far_n']}")
        (OUT / "evaluation.json").write_text(json.dumps(rep, indent=1) + "\n")

    for variant in VARIANTS:
        for seed in SEEDS:
            if (variant, seed) not in ok:
                rep["runs"][f"{variant}/{seed}"] = {"learned": False}
                continue
            run_model(variant, seed, Loaded(f"{variant}_seed{seed}").scores)
    run_model("kurt_s", "-", None, classical=lambda Tw: kurtosis(Tw, axis=1))
    run_model("env_s", "-", None,
              classical=lambda Tw: v2.envelope_indicator(Tw, ENV_ORDERS))
    lpath = MODELS / "local_scores.npz"
    if lpath.exists():
        with np.load(lpath) as z:
            for k in z.files:
                W[k] = z[k]
    for k, v in data.items():
        W[f"ottawa_speed/{k}"] = np.asarray(v["S"], dtype=np.float32)
    np.savez_compressed(OUT / "window_scores.npz", **W)
    (OUT / "evaluation.json").write_text(json.dumps(rep, indent=1) + "\n")
    log("wrote " + str(OUT))


def main():
    global SEEDS, LOCAL_SEEDS, OUT, MODELS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=("train", "evaluate"))
    ap.add_argument("--epochs", type=int, default=None, help="smoke tests only")
    ap.add_argument("--smoke", type=Path, default=None,
                    help="one seed per model, into this scratch folder")
    ap.add_argument("--xjtu-bearings", default=None, help="smoke tests only")
    args = ap.parse_args()
    if args.xjtu_bearings:
        args.xjtu_bearings = args.xjtu_bearings.split(",")
    if args.smoke:
        SEEDS, LOCAL_SEEDS = (42,), (0,)
        OUT, MODELS = args.smoke, args.smoke / "models"
    cmd_train(args) if args.stage == "train" else cmd_evaluate(args)


if __name__ == "__main__":
    main()
