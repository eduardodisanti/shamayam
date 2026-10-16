#!/usr/bin/env python3
"""
Registered protocol v2 (mssp_paper/notas/08_protocolo_banco_v2.md, approved
14-oct): the factory model learned on the CWRU bench, with the FULL quotient
(cepstral prewhitening per record in Hz, then angular resampling, then
optionally per-window gain/offset normalisation), deployed on IMS and Ottawa.
v1 (bench_transfer.py) is untouched and stays as registered.

  python3 bench_transfer_v2.py train      # bench, controls and ceiling; diagnostics
  python3 bench_transfer_v2.py evaluate   # IMS and Ottawa

Models (5 seeds each; same architecture, schedule, augmentation, split and
collapse check as v1):
  bench_w    CWRU healthy, prewhitened + angular            (H2v2)
  bench_wg   the same + per-window normalisation            (H1v2, primary)
  noise_wg   control: white Gaussian noise, same section
  sim_wg     control: the simulator (Ottawa parameters as in the Ottawa
             experiment), prewhitened before the angular resampling with its
             known speed, + normalisation
  local_wg   ceiling: per-machine model on Ottawa's four trial-1 healthy
             records, same section (in-sample, as in v1)
Classical references in the same domain, no training: kurtosis and the
envelope indicator (peak/median of the squared-envelope spectrum, orders
2-20) of each prewhitened window.
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
from mssp_repro.datasets import loader_root, provenance
from mssp_repro.field.order_domain import (ORDER_WINDOW, SAMPLES_PER_REV,
                                           angular_resample,
                                           estimate_shaft_frequency,
                                           order_windows, prewhiten)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "bench_v2"
# Weights are not committed. SHAMAYAM_MODELS_ROOT relocates them (16-oct);
# unset, the location of the registered run is kept.
MODELS = Path(os.environ.get("SHAMAYAM_MODELS_ROOT", "/home/claude/work")) / "bench_models_v2"
SEEDS = (42, 0, 1, 2, 3)
LOCAL_SEEDS = (0, 1, 2, 3, 4)
VARIANTS = ("bench_w", "bench_wg", "noise_wg", "sim_wg")
PROTOCOL = "08_protocolo_banco_v2.md (14-oct)"
ENV_ORDERS = (2.0, 20.0)


gain_section = v1.gain_section


# ------------------------------------------------------------------ sections

def bench_records():
    root = loader_root("CWRU_Bearing_NumPy")
    train, val, meta = [], [], []
    for rpm in v1.RPMS:
        with np.load(root / f"{rpm} RPM" / f"{rpm}_Normal.npz") as d:
            x = np.asarray(d["DE"], dtype=np.float64).reshape(-1)
        shaft = estimate_shaft_frequency(x, v1.FS_NORMAL, int(rpm) / 60.0)
        y = angular_resample(prewhiten(x), v1.FS_NORMAL, shaft)
        cut = int(v1.TRAIN_FRACTION * len(y))
        train.append(y[:cut])
        val.append(y[cut:])
        meta.append({"rpm": rpm, "shaft_hz": shaft,
                     "seconds": len(x) / v1.FS_NORMAL})
    return train, val, meta


def sim_windows(n):
    """Simulated healthy windows through the v2 section (known speed)."""
    from ottawa_variable_speed import OTTAWA_PARAMS
    from mssp_repro.field.order_domain import OrderDomainSimulator
    sim = OrderDomainSimulator(OTTAWA_PARAMS, duration=0.3)
    out = np.empty((n, ORDER_WINDOW), dtype=np.float32)
    for i in range(n):
        sig = np.random.uniform(0.8, 1.2, 5)
        x = sim.sim.sample(regime="healthy", mc=True, coverage="wide",
                           asset_signature=sig)
        shaft = sim.params.shaft_freq * sim.sim.last_speed
        y = angular_resample(prewhiten(x), sim.params.fs, shaft)
        out[i] = y[sim.offset:sim.offset + ORDER_WINDOW]
    return out


def build_sets(variant, seed, train, val):
    rng = np.random.default_rng(7000 + seed)
    if variant == "noise_wg":
        return (gain_section(rng.standard_normal((v1.N_TRAIN, ORDER_WINDOW))),
                gain_section(rng.standard_normal((v1.N_VAL, ORDER_WINDOW))))
    if variant == "sim_wg":
        np.random.seed(9000 + seed)
        return gain_section(sim_windows(v1.N_TRAIN)), gain_section(sim_windows(v1.N_VAL))
    Xtr, Xva = v1.augment(train, v1.N_TRAIN, rng), v1.augment(val, v1.N_VAL, rng)
    if variant == "bench_wg":
        return gain_section(Xtr), gain_section(Xva)
    return Xtr, Xva


# ------------------------------------------------------------------ training

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
        if variant != "noise_wg" and mse / var > v1.COLLAPSE_LEVEL:
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


def _save(name, ae, scaler):
    p = MODELS / name
    p.mkdir(parents=True, exist_ok=True)
    ae.save_weights(p / "ae.weights.h5")
    np.savez(p / "scaler.npz", mean=scaler.mean_, scale=scaler.scale_)


def ottawa_whitened(log):
    """Per record: prewhitened (whole 10 s record) then encoder projection."""
    import ottawa_variable_speed as ov
    from mssp_repro.field.ottawa import load_record, project_record
    root = loader_root("Ottawa_Bearing_TimeVaryingSpeed")
    data = {}
    for cond in ("H",) + ov.FAULTS:
        for p in ov.PROFILES:
            for t in ov.TRIALS:
                x, e = load_record(root, cond, p, t)
                WQ, S = project_record(prewhiten(x), e)
                key = f"{cond}-{p}-{t}"
                data[key] = dict(key=key, WQ=WQ.astype(np.float32), S=S,
                                 yq=WQ.reshape(-1))
    log("Ottawa prewhitened and projected")
    return data


def train_local(seed, data, kw):
    import ims_quotient_learning_curve as lc
    import mssp_repro.field.cwru_operator as co
    from mssp_repro.field.cwru_operator import AssetSpecificOperator
    rng = np.random.default_rng(1000 + seed)
    comm = [f"H-{p}-1" for p in ("A", "B", "C", "D")]
    Xtr = gain_section(v1.augment([data[k]["yq"] for k in comm], v1.N_TRAIN, rng))
    co.assert_operator_learned = lc._lenient_gate
    try:
        op = AssetSpecificOperator(seed=seed, **kw).fit(Xtr)
    except RuntimeError:
        return {"model": "local_wg", "seed": seed, "learned": False}, None
    d = {"model": "local_wg", "seed": seed, "learned": True,
         "unexplained": lc._gate.get("unexplained"),
         "generalisation_gap": op.history_["generalisation_gap"]}
    return d, op


def cmd_train(args):
    MODELS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    kw = {} if args.epochs is None else {"epochs": args.epochs}
    t0 = time.time()
    train, val, meta = bench_records()
    rep = {"protocol": PROTOCOL, "bench": provenance("CWRU_Bearing_NumPy"),
           "records": meta, "diagnostics": []}
    for variant in VARIANTS:
        for seed in SEEDS:
            d = train_shared(variant, seed, train, val, kw)
            rep["diagnostics"].append(d)
            print(f"[{variant} {seed}] {d} [{time.time() - t0:.0f}s]", flush=True)
            (OUT / "training.json").write_text(json.dumps(rep, indent=1) + "\n")
    data = ottawa_whitened(lambda m: print(m, flush=True))
    local_scores = {}
    for seed in LOCAL_SEEDS:
        d, op = train_local(seed, data, kw)
        rep["diagnostics"].append(d)
        print(f"[local_wg {seed}] {d} [{time.time() - t0:.0f}s]", flush=True)
        if op is not None:
            for k, v in data.items():
                local_scores[f"ottawa/local_wg/{seed}/{k}"] = \
                    op.scores(gain_section(v["WQ"])).astype(np.float32)
        (OUT / "training.json").write_text(json.dumps(rep, indent=1) + "\n")
    np.savez_compressed(MODELS / "local_scores.npz", **local_scores)


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
        self.norm = name.split("_seed")[0].endswith("wg")

    def scores(self, W):
        W = gain_section(W) if self.norm else np.asarray(W, dtype=np.float32)
        X = ((W - self.mean) / self.scale).astype(np.float32)[..., None]
        rec = self.ae.predict(X, verbose=0, batch_size=512)
        return np.mean(np.square(X - rec), axis=(1, 2))


def envelope_indicator(W, orders=ENV_ORDERS, spr=SAMPLES_PER_REV):
    env = np.abs(hilbert(W - W.mean(axis=1, keepdims=True), axis=1)) ** 2
    env = env - env.mean(axis=1, keepdims=True)
    spec = np.abs(np.fft.rfft(env * np.hanning(W.shape[1]), axis=1))
    o = np.fft.rfftfreq(W.shape[1], 1.0 / spr)
    band = (o >= orders[0]) & (o <= orders[1])
    return spec[:, band].max(axis=1) / np.median(spec[:, band], axis=1)


def cmd_evaluate(args):
    import ims_quotient_learning_curve as lc
    import ottawa_variable_speed as ov
    from mssp_repro.field.ims import IMS_CHANNELS, IMS_SAMPLE_RATE_HZ, load_experiment
    from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                            flag_inactive_recordings, load_cache)
    t0 = time.time()
    log = lambda m: print(f"{m} [{time.time() - t0:.0f}s]", flush=True)
    T = json.loads((OUT / "training.json").read_text())
    ok = {(d["model"], d["seed"]) for d in T["diagnostics"] if d["learned"]}

    signals, _, _ = load_experiment(loader_root("NASA_IMS_Bearings"), 2)
    pub = np.asarray(load_cache(HERE / "results" / "field_residuals_ims.npz")
                     ["scores"], dtype=float)
    ims = {}
    for b in (1, 2, 3, 4):
        (col,) = IMS_CHANNELS[2][b]
        X = signals[:, :, col].astype(np.float64)
        WQ = np.stack([order_windows(angular_resample(prewhiten(x), IMS_SAMPLE_RATE_HZ,
                                                      lc.SHAFT_HZ)) for x in X])
        inactive = flag_inactive_recordings(pub[b - 1], warmup=FIELD_WARMUP_RECORDINGS)
        n_active = X.shape[0]
        while n_active > 0 and inactive[n_active - 1]:
            n_active -= 1
        ims[b] = (WQ.astype(np.float32), n_active)
    log("IMS prewhitened and projected")
    data = ottawa_whitened(log)
    test_h = [f"H-{p}-{t}" for p in ov.PROFILES for t in (2, 3)]
    faults = {c: [f"{c}-{p}-{t}" for p in ov.PROFILES for t in ov.TRIALS]
              for c in ov.FAULTS}
    rep = {"protocol": PROTOCOL, "ims_ns": list(lc.NS),
           "far_window": list(lc.FAR_WINDOW), "runs": {}}
    W = {}

    def run_model(name, seed, score_windows):
        run = {"learned": True, "ims": {}, "ottawa": {}}
        for b, (WQ, n_active) in ims.items():
            s = score_windows(WQ.reshape(-1, WQ.shape[-1])).reshape(WQ.shape[:2]).mean(1)
            run["ims"][str(b)] = [lc.evaluate(s, n, n_active) for n in lc.NS]
            W[f"ims/{name}/{seed}/{b}"] = s.astype(np.float32)
        cache = {}

        def f(d, r):
            if d["key"] not in cache:
                cache[d["key"]] = score_windows(d["WQ"])
            return cache[d["key"]]
        for sc, profiles in (("ABCD1", ["A", "B", "C", "D"]), ("A1", ["A"])):
            comm = [f"H-{p}-1" for p in profiles]
            run["ottawa"][sc] = ov.evaluate(f, "q", data, comm, test_h, faults)
        for k, v in cache.items():
            W[f"ottawa/{name}/{seed}/{k}"] = np.asarray(v, dtype=np.float32)
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
    run_model("kurt_w", "-", lambda Wn: kurtosis(Wn, axis=1))
    run_model("env_w", "-", envelope_indicator)
    with np.load(MODELS / "local_scores.npz") as z:
        for k in z.files:
            W[k] = z[k]
    for k, v in data.items():
        W[f"ottawa_speed/{k}"] = v["S"].astype(np.float32)
    np.savez_compressed(OUT / "window_scores.npz", **W)
    (OUT / "evaluation.json").write_text(json.dumps(rep, indent=1) + "\n")
    log("wrote " + str(OUT))


def main():
    global SEEDS, LOCAL_SEEDS, OUT, MODELS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("stage", choices=("train", "evaluate"))
    ap.add_argument("--epochs", type=int, default=None, help="smoke tests only")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        SEEDS, LOCAL_SEEDS = (42,), (0,)
        OUT = Path("/tmp/claude-0/bench_v2_smoke")
        MODELS = OUT / "models"
    cmd_train(args) if args.stage == "train" else cmd_evaluate(args)


if __name__ == "__main__":
    main()
