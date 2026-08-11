#!/usr/bin/env python3
"""
Layer B stage 3: train the shared operator, score the IMS archive, and write
the residual cache.

    python3 build_field_cache.py                 # full run, ~10 min
    python3 build_field_cache.py --check         # recompute and COMPARE only
    python3 build_field_cache.py --recordings 60 # smoke test on a prefix

WHAT IT DOES
------------
Reads the 984 IMS recordings once, keeping all four channels; trains the
simulator-only operator; scores every recording through it; writes
`results/field_residuals_ims.npz` -- about 31 kB of residual series plus the
provenance needed to judge them.

That small file is what the rest of the paper's field results are computed
from, and it is committed, so a reader without the 523 MB archive can still
regenerate every field table and figure.

WHY `--check` IS THE POINT
--------------------------
A committed intermediate is only honest if something can contradict it.
`--check` recomputes the whole chain from the raw archive and compares against
the committed cache, on three diagnostics chosen because they are what the
paper's conclusions depend on: rank correlation of each residual series, the
relative shift of its median level, and whether the derived first-persistent-
departure index moves. Equality is not checked and would be the wrong test --
TensorFlow does not reproduce across builds, and the reference run was Metal
on macOS ARM.

Run `verify_operator.py` first. If the operator itself is wrong, everything
here is wrong in a way that still looks entirely plausible.
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from mssp_repro.field import find_archive
from mssp_repro.field.residuals import (FIELD_WARMUP_RECORDINGS,
                                        compare_to_cache, compute_ims_residuals,
                                        load_cache, save_cache)
from mssp_repro.field.shared_operator import SharedFieldOperator

HERE = Path(__file__).parent
CACHE = HERE / "results" / "field_residuals_ims.npz"


def locate(explicit):
    root = find_archive("NASA_bearing", explicit=explicit)
    if root is None:
        raise SystemExit(
            "NASA IMS archive not found.\n"
            "  Pass --ims-root /path/to/NASA_bearing, or set MSSP_IMS_ROOT.\n"
            "  Without it, the committed cache in results/ is still enough to "
            "regenerate\n  every field table and figure: run make_tables.py "
            "and make_figures.py.")
    return root / "IMS" if (root / "IMS").exists() else root


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ims-root", default=None)
    ap.add_argument("--check", action="store_true",
                    help="recompute and compare against the committed cache "
                         "instead of overwriting it")
    ap.add_argument("--recordings", type=int, default=None,
                    help="use only the first N recordings (smoke test; the "
                         "result is NOT a valid cache)")
    ap.add_argument("--epochs", type=int, default=100)
    args = ap.parse_args()

    root = locate(args.ims_root)
    print("=" * 72)
    print("Layer B stage 3 -- per-recording residuals")
    print("=" * 72)
    print(f"  archive: {root}")

    t0 = time.perf_counter()
    print(f"\n  training the shared operator ({args.epochs} epochs)...")
    try:
        op = SharedFieldOperator(archive="nasa", epochs=args.epochs).fit()
    except RuntimeError as exc:
        print(f"\n{exc}\n")
        raise SystemExit(
            "the operator did not learn, so no residual computed from it "
            "would mean anything.\nRun verify_operator.py to diagnose.")
    print(f"    {op.describe_training()}")

    print(f"\n  scoring recordings...")
    res = compute_ims_residuals(op, root, max_recordings=args.recordings,
                                progress=print)
    scores = res["scores"]
    print(f"\n    residual series: {scores.shape[0]} bearings x "
          f"{scores.shape[1]} recordings")
    for i, b in enumerate(res["bearings"]):
        s = scores[i]
        early = s[:FIELD_WARMUP_RECORDINGS]
        print(f"      bearing {b}: early-life median {np.median(early):.6f}, "
              f"final median {np.median(s[-50:]):.6f}, "
              f"ratio {np.median(s[-50:]) / np.median(early):.1f}x")

    if args.check:
        if not CACHE.exists():
            raise SystemExit(f"no cache at {CACHE} to check against")
        cached = load_cache(CACHE)
        taus = [op.tau_mc_] * scores.shape[0]
        ok, rows = compare_to_cache(res, cached, tau_per_bearing=taus)
        print(f"\n  against the committed cache "
              f"(generated {cached['meta'].get('generated_utc', '?')}, "
              f"{cached['meta'].get('device', '?')}, "
              f"TF {cached['meta'].get('tensorflow', '?')})")
        print(f"    {'bearing':>8}{'spearman':>11}{'level shift':>13}"
              f"{'departure shift':>17}")
        for r in rows:
            ds = ("-" if r["departure_shift"] is None
                  else f"{r['departure_shift']}")
            print(f"    {str(r['bearing']):>8}{r['spearman']:11.5f}"
                  f"{100*r['level_shift']:12.1f}%{ds:>17}"
                  f"   {'ok' if r['ok'] else 'FAIL'}")
        print(f"\n  {'AGREES' if ok else 'DISAGREES'} with the committed cache")
        return 0 if ok else 1

    if args.recordings is not None:
        print(f"\n  --recordings given: this is a smoke test, not writing "
              f"the cache")
        return 0

    path = save_cache(CACHE, res, op)
    size = path.stat().st_size
    print(f"\n  wrote {path.relative_to(HERE)}  ({size / 1024:.0f} kB)")
    print(f"  elapsed {time.perf_counter() - t0:.0f} s")
    print("\n  Commit this file. It is what lets a reader without the "
          "523 MB archive\n  regenerate every field table and figure, and "
          "what `--check` holds the\n  pipeline to when they do have it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
