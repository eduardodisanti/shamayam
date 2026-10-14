#!/usr/bin/env python3
"""
Several quotient spaces at once, with the guarantee kept.

No single quotient sees every fault: the IMS failure lives in energy, the
Ottawa outer race in impulsiveness (kurtosis), inner race, ball and combined
in energy or shape. Watching K spaces and alarming when ANY of them alarms
keeps a distribution-free bound on the false-alarm rate if each radius is
taken at level alpha/K (Bonferroni; no assumption on the dependence between
spaces). The price is the commissioning floor: k = ceil((1 - alpha/K)(n+1))
must not exceed n, so two spaces at alpha = 0.02 need n >= 99.

Nothing is trained: the scores are those already committed.
  Ottawa  autoencoder in the quotient (OEM, q) + kurtosis in the quotient,
          same windows; commissioning on the four trial-1 records and on A-1;
          OEM seeds as in the seed study
  IMS     RMS + kurtosis, and published OEM + kurtosis, per recording

Usage: python3 multispace_union.py
"""

import json
from pathlib import Path

import numpy as np

from mssp_repro.calibration import certified_order_statistic
from mssp_repro.dynamics import first_persistent_departure
from mssp_repro.field.ims import IMS_RECORDING_INTERVAL_HOURS

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "multispace" / "results.json"
ALPHA = 0.02
PROFILES = ("A", "B", "C", "D")
TEST_H = [f"H-{p}-{t}" for p in PROFILES for t in (2, 3)]
FAULTS = {c: [f"{c}-{p}-{t}" for p in PROFILES for t in (1, 2, 3)]
          for c in ("I", "O", "B", "C")}
SCEN = {"ABCD1": [f"H-{p}-1" for p in PROFILES], "A1": ["H-A-1"]}


def radius(scores, K):
    return certified_order_statistic(scores, alpha=ALPHA / K)


def ottawa(S, sc, spaces):
    K = len(spaces)
    comm = SCEN[sc]
    tau = {s: radius(np.concatenate([S[f"{sc}/{s}/{r}"] for r in comm]), K)
           for s in spaces}
    if any(np.isnan(t) for t in tau.values()):
        return {"certifiable": False}

    def flags(r):
        return np.any([S[f"{sc}/{s}/{r}"] > tau[s] for s in spaces], axis=0)

    fh = [flags(r) for r in TEST_H]
    out = {"certifiable": True, "K": K,
           "far_k": int(sum(f.sum() for f in fh)),
           "far_n": int(sum(len(f) for f in fh)),
           "rec_false": int(sum(first_persistent_departure(f, q=8, p=10) is not None
                                for f in fh)), "detection": {}}
    for c, recs in FAULTS.items():
        ff = [flags(r) for r in recs]
        out["detection"][c] = {
            "k": int(sum(f.sum() for f in ff)), "n": int(sum(len(f) for f in ff)),
            "rec": int(sum(first_persistent_departure(f, q=8, p=10) is not None
                           for f in ff)), "rec_n": len(recs)}
    return out


def ims(series, spaces, n, n_active):
    K = len(spaces)
    tau = {s: radius(series[s][:n], K) for s in spaces}
    if any(np.isnan(t) for t in tau.values()):
        return {"n": n, "certifiable": False}
    fl = np.any([series[s] > tau[s] for s in spaces], axis=0)
    d = first_persistent_departure(fl[:n_active], q=8, p=10, start=n)
    return {"n": n, "certifiable": True, "far_k": int(fl[200:500].sum()),
            "far_n": 300, "departure": d,
            "lead_hours": (float((n_active - d) * IMS_RECORDING_INTERVAL_HOURS)
                           if d is not None else None)}


def main():
    rep = {"alpha": ALPHA, "ottawa": {}, "ims": {}}
    combos = {"OEM (q)": ["oem_q"], "curtosis (q)": ["kurt_q"],
              "OEM (q) + curtosis (q)": ["oem_q", "kurt_q"]}
    for i in range(5):
        f = HERE / "results" / "ottawa" / f"scores_seed{i}.npz"
        with np.load(f) as z:
            S = {k: z[k] for k in z.files}
        for sc in SCEN:
            for name, spaces in combos.items():
                rep["ottawa"].setdefault(sc, {}).setdefault(name, []).append(
                    ottawa(S, sc, spaces))
    from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                            flag_inactive_recordings, load_cache)
    pub = np.asarray(load_cache(HERE / "results" / "field_residuals_ims.npz")
                     ["scores"], dtype=float)
    feats = np.load(HERE / "results" / "ims_classical" / "features.npz")
    icombos = {"RMS": ["rms"], "curtosis": ["kurtosis"], "OEM publicado": ["oem"],
               "RMS + curtosis": ["rms", "kurtosis"],
               "OEM publicado + curtosis": ["oem", "kurtosis"]}
    for b in (1, 2, 3, 4):
        inactive = flag_inactive_recordings(pub[b - 1], warmup=FIELD_WARMUP_RECORDINGS)
        n_active = len(pub[b - 1])
        while n_active > 0 and inactive[n_active - 1]:
            n_active -= 1
        series = {"rms": feats[f"{b}/rms"], "kurtosis": feats[f"{b}/kurtosis"],
                  "oem": pub[b - 1]}
        for name, spaces in icombos.items():
            rep["ims"].setdefault(str(b), {})[name] = [
                ims(series, spaces, n, n_active) for n in (49, 99, 149, 200)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
