#!/usr/bin/env python3
"""
IMS Experiment 2: classical condition indicators as OEM-style models, with
the same local calibration as the autoencoder (decision D7).

Nothing is trained. Each indicator is computed once per one-second recording
(time domain, full band, 20 kHz; IMS runs at constant speed, so the angular
projection would change nothing here):

  rms       root mean square
  kurtosis  excess kurtosis (impulsiveness)
  crest     peak / RMS
  envelope  peak-to-median ratio of the envelope spectrum (Hilbert envelope
            of the full-band signal) over orders 2-20 of the nominal shaft
            speed. Geometry-free on purpose: the defect frequencies of the
            IMS bearings were not taken from the literature, so no band or
            frequency was chosen after looking at the data.

Same protocol as ims_quotient_learning_curve.py: radius r_(k) on the first n
recordings, false alarms on recordings 200-499, first persistent departure
(8 of 10) after commissioning and lead time to the end of the active record.

Writes results/ims_classical/{results.json, features.npz} (one value per
recording and indicator, for the contamination analysis).

Usage: python3 ims_classical_features.py [--ims-root PATH]
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.signal import hilbert
from scipy.stats import kurtosis

from mssp_repro.datasets import dataset_arg
from mssp_repro.calibration import certified_order_statistic
from mssp_repro.dynamics import first_persistent_departure
from mssp_repro.field.ims import (IMS_CHANNELS, IMS_RECORDING_INTERVAL_HOURS,
                                  IMS_SAMPLE_RATE_HZ, load_experiment)
from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                        flag_inactive_recordings, load_cache)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "ims_classical" / "results.json"
SHAFT_HZ = 2000.0 / 60.0
NS = (49, 99, 149, 200)
FAR_WINDOW = (200, 500)
ORDERS = (2.0, 20.0)
FEATURES = ("rms", "kurtosis", "crest", "envelope")


def envelope_peak_ratio(x, fs=IMS_SAMPLE_RATE_HZ, shaft=SHAFT_HZ,
                        orders=ORDERS):
    env = np.abs(hilbert(x - x.mean()))
    env = env - env.mean()
    spec = np.abs(np.fft.rfft(env * np.hanning(len(env))))
    f = np.fft.rfftfreq(len(env), 1.0 / fs)
    band = (f >= orders[0] * shaft) & (f <= orders[1] * shaft)
    return float(spec[band].max() / np.median(spec[band]))


def features(x):
    x = np.asarray(x, dtype=np.float64)
    rms = float(np.sqrt(np.mean(x ** 2)))
    return {"rms": rms, "kurtosis": float(kurtosis(x)),
            "crest": float(np.max(np.abs(x)) / rms),
            "envelope": envelope_peak_ratio(x)}


def evaluate(scores, n, n_active):
    tau = certified_order_statistic(scores[:n])
    a, b = FAR_WINDOW
    k = int(np.sum(scores[a:b] > tau))
    d = first_persistent_departure(scores[:n_active] > tau, q=8, p=10, start=n)
    return {"n": n, "tau": float(tau), "far_k": k, "far_n": b - a,
            "departure": d,
            "lead_hours": (float((n_active - d) * IMS_RECORDING_INTERVAL_HOURS)
                           if d is not None else None)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--ims-root", **dataset_arg("NASA_IMS_Bearings"))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    signals, _, _ = load_experiment(args.ims_root, 2)
    pub = np.asarray(load_cache(HERE / "results" / "field_residuals_ims.npz")
                     ["scores"], dtype=float)
    rep = {"ns": list(NS), "far_window": list(FAR_WINDOW),
           "envelope_orders": list(ORDERS), "bearings": {}}
    series = {}
    for b in (1, 2, 3, 4):
        (col,) = IMS_CHANNELS[2][b]
        F = [features(x) for x in signals[:, :, col]]
        inactive = flag_inactive_recordings(pub[b - 1],
                                            warmup=FIELD_WARMUP_RECORDINGS)
        n_active = len(F)
        while n_active > 0 and inactive[n_active - 1]:
            n_active -= 1
        e = {"n_active": int(n_active),
             "oem_pub": [evaluate(pub[b - 1], n, n_active) for n in NS]}
        for name in FEATURES:
            s = np.array([f[name] for f in F])
            series[f"{b}/{name}"] = s
            e[name] = [evaluate(s, n, n_active) for n in NS]
        rep["bearings"][str(b)] = e
        print(f"bearing {b}: " + "; ".join(
            f"{k} n=99 FAR {e[k][1]['far_k']}/{e[k][1]['far_n']} dep {e[k][1]['departure']}"
            for k in FEATURES), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rep, indent=1) + "\n")
    np.savez_compressed(args.out.parent / "features.npz", **series)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
