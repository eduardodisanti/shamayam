#!/usr/bin/env python3
"""
Ottawa (Huang & Baddour): shaft speed varying WITHIN each record, 10-29 Hz.

The validation the bearing archives used so far cannot give: in CWRU each file
has one speed and IMS runs at a constant 2000 rpm, so the speed part of the
nuisance group was only exercised between records. Here every 10 s record
sweeps the speed (increasing, decreasing, up-down, down-up), and vibration
amplitude follows the speed (RMS correlation with speed above 0.95 in every
healthy record), so speed acts on the signal both as a time scaling and as a
gain.

Sections of the quotient compared
  time   no section: windows of 1200 samples at 8 kHz (about 3 rev at 20 Hz)
  q      angular projection from the encoder (400 samples/rev, 3 rev windows)
  qg     q followed by per-window offset and gain normalisation (subtract the
         mean, divide by the RMS): a section for the offset and gain parts of G

Arms (one autoencoder architecture throughout, the published 847,601-parameter
Conv1D)
  raw       per-machine, time windows of the commissioning records
  raw_aug   per-machine, time windows augmented over phase (any start), gain,
            offset and noise; differs from `quot` only by the angular section
  quot      per-machine, projected windows, same augmentation (IMS protocol)
  quotg     per-machine, as `quot` then normalised (section qg)
  oem_q     shared operator trained only on simulation, projected the same way
  oem_qg    the same with the qg normalisation, simulated and real alike
  rms_t     RMS of time windows (classical, no training)
  kurt_q    kurtosis of projected windows (classical, gain invariant)

Commissioning: the healthy windows of trial 1 of one speed profile (one 10 s
record, about 66 windows), or of the four trial-1 records together. Radius
r_(k), k = ceil(0.98 (n+1)), on the commissioning windows. Healthy test: the
eight records of trials 2 and 3 (never used for commissioning). Faults: all
48 fault records. Persistence: 8 of 10 consecutive windows.

The simulator for the shared operator uses the documented acquisition facts
(200 kHz; nominal shaft 20 Hz, the middle of the recorded range) and the
simulator's defaults for everything else; nothing is fitted to the data.

Usage: python3 ottawa_variable_speed.py [--ottawa-root PATH] [--seed 0]
"""

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly
from scipy.stats import kurtosis
from sklearn.metrics import roc_auc_score

from mssp_repro.datasets import dataset_arg, provenance
from mssp_repro.bearing_simulator import BearingParams
from mssp_repro.calibration import certified_order_statistic
from mssp_repro.dynamics import first_persistent_departure
from mssp_repro.field.cwru_operator import AssetSpecificOperator
from mssp_repro.field.ims import make_windows
from mssp_repro.field.order_domain import ORDER_WINDOW, OrderDomainSimulator
from mssp_repro.field.ottawa import (OTTAWA_FS, PROFILES, TRIALS,
                                     encoder_angle, load_record,
                                     project_record)
from mssp_repro.field.shared_operator import SharedFieldOperator

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "ottawa"
TIME_FS = 8000
FAULTS = ("I", "O", "B", "C")
SCENARIOS = {"A1": ["A"], "B1": ["B"], "C1": ["C"], "D1": ["D"],
             "ABCD1": ["A", "B", "C", "D"]}
SPEED_BANDS = ((10, 15), (15, 20), (20, 25), (25, 30))
N_AUG = 4000
OTTAWA_PARAMS = BearingParams(fs=OTTAWA_FS, duration=0.3, shaft_freq=20.0)
COLLAPSE_LEVEL = 0.98
_gate = {}


def _lenient_gate(mse, var, validation_mse=None, name="operator"):
    """Rejects only collapse, as in the IMS per-machine arms."""
    _gate.clear()
    _gate.update(unexplained=float(mse / var))
    if mse / var > COLLAPSE_LEVEL:
        raise RuntimeError(f"{name}: collapsed (unexplained {mse / var:.3f})")


def gain_section(W):
    W = W - W.mean(axis=1, keepdims=True)
    return (W / np.sqrt(np.mean(W ** 2, axis=1, keepdims=True))).astype(np.float32)


def augment(records, n, rng):
    """Windows from any start inside the commissioning records (phase), then
    gain, offset and noise over the simulator's 'wide' ranges."""
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


class OttawaOEM(SharedFieldOperator):
    """Published schedule, simulated windows projected to the order domain
    (known simulated speed), optionally normalised by the qg section."""

    def __init__(self, normalise=False, **kw):
        super().__init__(archive="nasa", **kw)
        self.normalise = normalise

    def fit(self, **kw):
        import mssp_repro.field.shared_operator as so
        sim = OrderDomainSimulator(OTTAWA_PARAMS, duration=0.3)
        gen = ((lambda n, **k: gain_section(sim.windows(n))) if self.normalise
               else (lambda n, **k: sim.windows(n)))
        original = so.generate_oem_windows
        so.generate_oem_windows = gen
        try:
            return super().fit(**kw)
        finally:
            so.generate_oem_windows = original

    def scores(self, W):
        return self._window_mse(
            self.scaler_.transform(W).astype(np.float32)[..., None])


def load_all(root, log):
    """Per record: time windows, projected windows, window speeds, and the
    continuous signals the augmentation draws from."""
    data = {}
    for cond in ("H",) + FAULTS:
        for p in PROFILES:
            for t in TRIALS:
                x, e = load_record(root, cond, p, t)
                WQ, S = project_record(x, e)
                xt = resample_poly(x, 1, OTTAWA_FS // TIME_FS)
                WT = make_windows(xt, 1200, 1200).astype(np.float32)
                te, th = encoder_angle(e)
                lag = 64
                centres = (np.arange(len(WT)) * 1200 + 600) / TIME_FS
                ST = np.interp(centres, 0.5 * (te[lag:] + te[:-lag]),
                               (th[lag:] - th[:-lag]) / (te[lag:] - te[:-lag]))
                yq = WQ.reshape(-1)          # contiguous projected samples
                key = f"{cond}-{p}-{t}"
                data[key] = dict(key=key, WQ=WQ.astype(np.float32), S=S,
                                 WT=WT, ST=ST, yq=yq, xt=xt)
    log(f"loaded {len(data)} records")
    return data


SCORES = {}


def evaluate(score_fn, rep, data, comm_keys, test_h, faults, label=None):
    """Radius on commissioning windows; FAR, persistence and detection.
    With `label`, every record's window scores are kept in SCORES."""
    if label is not None:
        inner = score_fn

        def score_fn(d, r):
            s = inner(d, r)
            SCORES[f"{label}/{d['key']}"] = np.asarray(s, dtype=np.float32)
            return s
    s_comm = np.concatenate([score_fn(data[k], rep) for k in comm_keys])
    tau = float(certified_order_statistic(s_comm))
    out = {"n_comm": int(len(s_comm)), "tau": tau}
    h_scores, h_speed, rec_alarms = [], [], 0
    for k in test_h:
        s = score_fn(data[k], rep)
        h_scores.append(s)
        h_speed.append(data[k]["ST"] if rep == "time" else data[k]["S"])
        rec_alarms += first_persistent_departure(s > tau, q=8, p=10) is not None
    hs, hv = np.concatenate(h_scores), np.concatenate(h_speed)
    out.update(far_k=int(np.sum(hs > tau)), far_n=int(len(hs)),
               rec_false=int(rec_alarms), rec_n=len(test_h),
               bands=[{"band": list(b),
                       "k": int(np.sum((hs > tau) & (hv >= b[0]) & (hv < b[1]))),
                       "n": int(np.sum((hv >= b[0]) & (hv < b[1])))}
                      for b in SPEED_BANDS])
    det = {}
    for c in FAULTS:
        fs, recs = [], 0
        for k in faults[c]:
            s = score_fn(data[k], rep)
            fs.append(s)
            recs += first_persistent_departure(s > tau, q=8, p=10) is not None
        fs = np.concatenate(fs)
        y = np.r_[np.zeros(len(hs)), np.ones(len(fs))]
        det[c] = {"k": int(np.sum(fs > tau)), "n": int(len(fs)),
                  "rec": int(recs), "rec_n": len(faults[c]),
                  "auroc": float(roc_auc_score(y, np.r_[hs, fs]))}
    out["detection"] = det
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--ottawa-root", **dataset_arg("Ottawa_Bearing_TimeVaryingSpeed"))
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--seed", type=int, default=0, help="per-machine arms")
    ap.add_argument("--oem-seed", type=int, default=42)
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--arms", default="raw,raw_aug,quot,quotg")
    ap.add_argument("--no-oem", action="store_true")
    ap.add_argument("--epochs", type=int, default=None, help="smoke tests only")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda m: print(f"{m} [{time.time() - t0:.0f}s]", flush=True)
    kw = {} if args.epochs is None else {"epochs": args.epochs}

    data = load_all(args.ottawa_root, log)
    test_h = [f"H-{p}-{t}" for p in PROFILES for t in (2, 3)]
    faults = {c: [f"{c}-{p}-{t}" for p in PROFILES for t in TRIALS]
              for c in FAULTS}
    rep = {"dataset": provenance("Ottawa_Bearing_TimeVaryingSpeed"),
           "seed": args.seed, "oem_seed": args.oem_seed, "n_aug": N_AUG,
           "time_fs": TIME_FS, "test_healthy": test_h,
           "speed_bands": [list(b) for b in SPEED_BANDS],
           "records": {k: {"windows_q": int(v["WQ"].shape[0]),
                           "windows_t": int(v["WT"].shape[0]),
                           "speed_min": float(v["S"].min()),
                           "speed_max": float(v["S"].max())}
                       for k, v in data.items()},
           "scenarios": {}}
    out_file = args.out / f"results{args.tag}.json"

    def save():
        out_file.write_text(json.dumps(rep, indent=1) + "\n")
        np.savez_compressed(args.out / f"scores{args.tag}.npz", **SCORES,
                            **{f"speed/{k}": v["S"] for k, v in data.items()},
                            **{f"speed_t/{k}": v["ST"] for k, v in data.items()})

    # ---- classical features and shared operators: no per-machine training
    feats = {"rms_t": (lambda d, r: np.sqrt(np.mean(d["WT"] ** 2, axis=1)), "time"),
             "kurt_q": (lambda d, r: kurtosis(d["WQ"], axis=1), "q")}
    oems = {}
    if not args.no_oem:
        for name, norm in (("oem_q", False), ("oem_qg", True)):
            op = OttawaOEM(normalise=norm, seed=args.oem_seed, **kw).fit()
            oems[name] = op
            rep[f"{name}_training"] = {k: v for k, v in op.history_.items()
                                       if k not in ("loss", "val_loss")}
            log(f"{name}: " + op.describe_training())
    cache = {}

    def oem_score(name):
        op = oems[name]

        def f(d, r):
            key = (name, id(d))
            if key not in cache:
                W = gain_section(d["WQ"]) if name == "oem_qg" else d["WQ"]
                cache[key] = op.scores(W)
            return cache[key]
        return f

    for sc in args.scenarios.split(","):
        comm = [f"H-{p}-1" for p in SCENARIOS[sc]]
        res = rep["scenarios"].setdefault(sc, {"commissioning": comm})
        for name, (f, r) in feats.items():
            res[name] = evaluate(f, r, data, comm, test_h, faults,
                                 label=f"{sc}/{name}")
        for name in oems:
            res[name] = evaluate(oem_score(name), "q", data, comm, test_h,
                                 faults, label=f"{sc}/{name}")
        rng = np.random.default_rng(1000 + args.seed)
        for arm in args.arms.split(","):
            if arm == "raw":
                Xtr, r = np.concatenate([data[k]["WT"] for k in comm]), "time"
            elif arm == "raw_aug":
                Xtr, r = augment([data[k]["xt"] for k in comm], N_AUG, rng), "time"
            elif arm == "quot":
                Xtr, r = augment([data[k]["yq"] for k in comm], N_AUG, rng), "q"
            elif arm == "quotg":
                Xtr = gain_section(augment([data[k]["yq"] for k in comm], N_AUG, rng))
                r = "qg"
            import mssp_repro.field.cwru_operator as co
            co.assert_operator_learned = _lenient_gate
            try:
                op = AssetSpecificOperator(seed=args.seed, **kw).fit(Xtr)
            except RuntimeError:
                res[arm] = {"learned": False}
                log(f"[{sc} {arm}] did not learn")
                save()
                continue
            key = {"time": "WT", "q": "WQ", "qg": "WQ"}[r]
            f = ((lambda d, _r, op=op: op.scores(gain_section(d["WQ"])))
                 if r == "qg" else
                 (lambda d, _r, op=op, key=key: op.scores(d[key])))
            e = evaluate(f, "time" if r == "time" else "q", data, comm, test_h,
                         faults, label=f"{sc}/{arm}")
            e.update(learned=True, n_train=int(len(Xtr)),
                     gap=op.history_["generalisation_gap"],
                     unexplained=_gate.get("unexplained"))
            res[arm] = e
            log(f"[{sc} {arm}] FAR {e['far_k']}/{e['far_n']} rec "
                f"{e['rec_false']}/{e['rec_n']} | det " + " ".join(
                    f"{c}:{v['rec']}/{v['rec_n']}" for c, v in e["detection"].items()))
            save()
        log(f"[{sc}] done")
        save()
    log("wrote " + str(out_file))


if __name__ == "__main__":
    main()
