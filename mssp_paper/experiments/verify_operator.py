#!/usr/bin/env python3
"""
Verify the ported shared operator against the published run.

WHAT THIS ANSWERS
-----------------
Layer B stage 2 rebuilds the "OEM" autoencoder: trained only on synthetic
nominal windows, then transferred frozen to real bearings. Two things have to
be true before anything downstream is worth computing.

  1. The training data is reproduced EXACTLY. It comes from the simulator
     through numpy's legacy global RNG, so it is bit-checkable, and this
     script checks it against a literal transcription of the notebook loop
     rather than against itself.

  2. The trained operator lands in the same place. It cannot be bit-checked --
     TensorFlow is not reproducible across builds or backends -- so the check
     is against the published threshold, tau_MC(p98) = 0.012016, with a stated
     tolerance, plus the first epochs of the published loss trace.

WHY THE SECOND CHECK MATTERS MORE THAN IT LOOKS
-----------------------------------------------
The architecture regularises the latent layer, and Keras changed how that
penalty is reduced over a batch. Under the summed convention the code
collapses, the decoder emits a constant, and `fit` still returns normally with
a monotone loss curve settling at the variance of the input. Residuals, radii
and false-alarm rates all remain computable and none of them look wrong.
`BatchMeanL1` fixes the reduction and `assert_operator_learned` refuses a
collapsed operator, but this script is what confirms the fix on YOUR build.

    python3 verify_operator.py              # full: trains 100 epochs, minutes
    python3 verify_operator.py --quick      # data checks + 3 epochs only

Exit status is 0 when every check passes, 1 otherwise, so it can gate a
pipeline run.
"""

import argparse
import platform
import sys
import time

import numpy as np

from mssp_repro.bearing_simulator import NASA_PARAMS, BearingSignalSimulator
from mssp_repro.field.ims import make_windows
from mssp_repro.field.shared_operator import (LEARNING_RATE, PUBLISHED_TAU_MC,
                                              SharedFieldOperator,
                                              generate_oem_windows)

# First three epochs of the published NASA run, read from the notebook's saved
# cell output. Backend differences move these by a few per cent; a collapsed
# operator sits at 1.0000, so the comparison is not delicate.
PUBLISHED_LOSS = [0.2315, 0.0363, 0.0243]
PUBLISHED_VAL_LOSS = [0.0540, 0.0280, 0.0217]

# The published tau_MC is a percentile of a finite validation draw under a
# different backend. Ten per cent is loose enough to absorb that and tight
# enough to catch a wrong operator: a collapsed one is off by two orders.
TAU_TOLERANCE = 0.10

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def notebook_generate(n, sim):
    """Literal transcription of `generate_oem_healthy` from the notebook."""
    samples = []
    while len(samples) < n:
        signal = sim.sample(regime="healthy", mc=True, coverage="wide",
                            asset_signature=np.random.uniform(0.8, 1.2, 5))
        samples.extend(make_windows(signal, win=1200, step=1200))
    return np.asarray(samples[:n], dtype=np.float32)


def check_training_data():
    print("\nTraining data (bit-exact, no TensorFlow needed)")
    n = 4000

    np.random.seed(42)
    reference = notebook_generate(n, BearingSignalSimulator(NASA_PARAMS))
    np.random.seed(42)
    ported = generate_oem_windows(n, archive="nasa")
    check("port reproduces the notebook's training windows exactly",
          np.array_equal(reference, ported), f"shape {ported.shape}")

    np.random.seed(42)
    again = generate_oem_windows(n, archive="nasa")
    check("generation is reproducible under the seed",
          np.array_equal(ported, again))

    np.random.seed(43)
    other = generate_oem_windows(200, archive="nasa")
    check("a different seed gives different data",
          not np.array_equal(ported[:200], other))

    check("17 windows per IMS-length recording",
          make_windows(np.zeros(20480)).shape[0] == 17)


def check_training(epochs, n_train, n_val):
    print(f"\nTraining ({epochs} epochs, {n_train} train / {n_val} val)")
    t0 = time.perf_counter()
    try:
        op = SharedFieldOperator(archive="nasa", epochs=epochs,
                                 verbose=0).fit(n_train=n_train, n_val=n_val)
    except RuntimeError as exc:
        check("the operator learned", False, "")
        print("\n" + str(exc))
        return None
    except ModuleNotFoundError as exc:
        print(f"  SKIP: {exc}")
        return None
    elapsed = time.perf_counter() - t0

    h = op.history_
    check("the operator learned (latent did not collapse)", True,
          f"best val_loss {h['best_val_loss']:.5f}")

    print(f"\n  first epochs against the published trace")
    print(f"    {'epoch':>6}{'loss':>10}{'published':>11}"
          f"{'val_loss':>11}{'published':>11}")
    for i in range(min(3, len(h["loss"]))):
        print(f"    {i+1:6d}{h['loss'][i]:10.4f}{PUBLISHED_LOSS[i]:11.4f}"
              f"{h['val_loss'][i]:11.4f}{PUBLISHED_VAL_LOSS[i]:11.4f}")

    check("first-epoch loss is in the published regime, not collapsed",
          h["loss"][0] < 0.5,
          f"{h['loss'][0]:.4f} (collapsed would be ~1.0)")

    if epochs >= 100:
        rel = abs(op.tau_mc_ - PUBLISHED_TAU_MC) / PUBLISHED_TAU_MC
        check(f"tau_MC matches the published {PUBLISHED_TAU_MC:.6f} "
              f"to {100*TAU_TOLERANCE:.0f}%",
              rel <= TAU_TOLERANCE,
              f"got {op.tau_mc_:.6f}, off by {100*rel:.1f}%")
    else:
        print(f"    tau_MC after {epochs} epochs: {op.tau_mc_:.6f} "
              f"(not comparable; the published value needs the full 100)")

    print(f"\n  {op.describe_training()}")
    print(f"  elapsed {elapsed:.0f} s")
    return op


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true",
                    help="3 epochs instead of 100. The training set stays at "
                         "its full size, because the first-epoch loss is only "
                         "comparable to the published trace at the same "
                         "number of samples")
    args = ap.parse_args()

    print("=" * 72)
    print("Layer B stage 2 -- verification of the ported shared operator")
    print("=" * 72)
    try:
        import tensorflow as tf
        import keras
        print(f"  TensorFlow {tf.__version__}, Keras {keras.__version__}")
        # The compute device is provenance, not trivia: a run on Apple's Metal
        # backend and a run on CPU do not agree bit for bit, and Metal is a
        # PluggableDevice, for which enable_op_determinism() gives no
        # guarantee at all. The published tau_MC came off Metal.
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            names = ", ".join(
                tf.config.experimental.get_device_details(g).get(
                    "device_name", g.name) for g in gpus)
            print(f"  compute device: {names}  "
                  f"(op determinism is not guaranteed on pluggable devices)")
        else:
            print("  compute device: CPU")
    except ModuleNotFoundError:
        print("  TensorFlow not installed; only the data checks will run")
    print(f"  Python {sys.version.split()[0]} on {platform.platform()}")
    print(f"  numpy {np.__version__}")

    check_training_data()
    # The data size is NOT reduced in quick mode. Shrinking it changes the
    # first-epoch loss for reasons that have nothing to do with the port --
    # a quarter of the samples starts around 0.67 rather than 0.26 -- and the
    # comparison against the published trace is the whole point of the check.
    check_training(3 if args.quick else 100, 4000, 1000)

    passed = sum(1 for _, ok in results if ok)
    print("\n" + "=" * 72)
    print(f"  {passed}/{len(results)} checks passed")
    if passed != len(results):
        print("\n  A failure here means the port does not reproduce the "
              "published operator.\n  Do NOT run the downstream pipeline "
              "until it is understood: every field\n  number depends on this "
              "operator, and none of them would look wrong.")
    print("=" * 72)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
