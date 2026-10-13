#!/usr/bin/env python3
"""
Failure mode: commissioning contaminated by a fault that is already present.

If some commissioning observations come from a faulty machine, the radius is
inflated and the fault may never be flagged. For the order-statistic radius
the tolerance is exact and distribution-free: r_(k) is unaffected by up to
n - k contaminated observations that lie above every healthy one, and set by
them beyond that. The menu of commissioning lengths therefore also fixes how
much contamination each length survives:

  r_(k), n=49   k=49   tolerates 0
  r_(k), n=99   k=98   tolerates 1
  r_(k), n=149  k=147  tolerates 2
  tolerance, n=149  k=149   tolerates 0  (confidence is paid for in robustness)

This script measures it on the one real failure (IMS Experiment 2, bearing 1,
outer race). m of the first n recordings are replaced by recordings drawn at
random from the last 100 active recordings, where the fault is unambiguous;
the radius is recomputed; the fault is looked for in the real sequence after
commissioning (persistent departure, 8 of 10). Scores: the published shared
operator (residual cache) and two classical indicators (RMS and the envelope
indicator of ims_classical_features.py). Pure numpy; deterministic.

Usage: python3 commissioning_contamination.py
"""

import json
from pathlib import Path

import numpy as np

from mssp_repro.calibration import (certified_order_statistic,
                                    tolerance_order_statistic, tolerance_rank)
from mssp_repro.dynamics import first_persistent_departure
from mssp_repro.field.ims import IMS_RECORDING_INTERVAL_HOURS
from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                        flag_inactive_recordings, load_cache)

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "contamination" / "results.json"
BEARING = 1
LAST = 100
MS = (0, 1, 2, 3, 5)
DRAWS = 1000
SEED = 20261013
RADII = (("r_(k), n=49", "certified", 49), ("r_(k), n=99", "certified", 99),
         ("r_(k), n=149", "certified", 149),
         ("tolerancia, n=149", "tolerance", 149))


def radius(a, kind):
    return (certified_order_statistic(a) if kind == "certified"
            else tolerance_order_statistic(a))


def rank(n, kind):
    return int(np.ceil(0.98 * (n + 1))) if kind == "certified" else tolerance_rank(n)


def run(scores, n_active, rng):
    out = []
    pool = np.arange(n_active - LAST, n_active)
    for label, kind, n in RADII:
        tau0 = radius(scores[:n], kind)
        k = rank(n, kind)
        for m in MS:
            lost, leads, infl = 0, [], []
            for _ in range(DRAWS if m else 1):
                cal = scores[:n].copy()
                if m:
                    pos = rng.choice(n, size=m, replace=False)
                    cal[pos] = scores[rng.choice(pool, size=m, replace=False)]
                tau = radius(cal, kind)
                infl.append(tau / tau0)
                d = first_persistent_departure(scores[:n_active] > tau,
                                               q=8, p=10, start=n)
                if d is None:
                    lost += 1
                else:
                    leads.append((n_active - d) * IMS_RECORDING_INTERVAL_HOURS)
            draws = DRAWS if m else 1
            out.append({"radius": label, "n": n, "k": k, "tolerates": n - k,
                        "m": m, "draws": draws, "lost": lost,
                        "lead_median_h": (float(np.median(leads))
                                          if leads else None),
                        "inflation_median": float(np.median(infl))})
    return out


def main():
    pub = np.asarray(load_cache(HERE / "results" / "field_residuals_ims.npz")
                     ["scores"], dtype=float)
    feats = np.load(HERE / "results" / "ims_classical" / "features.npz")
    s_pub = pub[BEARING - 1]
    inactive = flag_inactive_recordings(s_pub, warmup=FIELD_WARMUP_RECORDINGS)
    n_active = len(s_pub)
    while n_active > 0 and inactive[n_active - 1]:
        n_active -= 1
    rng = np.random.default_rng(SEED)
    rep = {"bearing": BEARING, "n_active": int(n_active), "pool_last": LAST,
           "draws": DRAWS, "seed": SEED, "scores": {}}
    for name, s in (("OEM publicado", s_pub),
                    ("RMS", feats[f"{BEARING}/rms"]),
                    ("envolvente", feats[f"{BEARING}/envelope"])):
        rep["scores"][name] = run(np.asarray(s, dtype=float), n_active, rng)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
