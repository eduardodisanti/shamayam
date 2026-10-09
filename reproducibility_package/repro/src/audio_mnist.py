"""Spoken digits (Free Spoken Digit Dataset) as a functional domain.

The representation is not ours and is not tuned here: it is the one declared
in audiomnist.ipynb -- 16 kHz, 64 mel bands, hop 160, window 400, one second
with zero padding, log of the mel spectrogram, flattened. Recording it here
rather than re-deriving it keeps the paper's numbers reproducible from the
package instead of from a notebook.

The observer's declared model of the signal is therefore a log-mel
spectrogram. That is a choice about what the observer is assumed to hear, it
is stated, and a different choice would give a different manifold -- which is
the same status the 160-point resampling has in the physical domains.

Benign group, declared before measuring: who is speaking and how fast. The
same digit said by another speaker, or a little quicker, is the same digit.
What is NOT benign is which digit was said.
"""
from __future__ import annotations

import glob
import os
import re

import numpy as np

SR = 16000
N_MELS = 64
HOP = 160
WIN = 400
MAX_SEC = 1.0
NAME = re.compile(r"^(\d)_([a-zA-Z]+)_(\d+)\.wav$")


def quotient_duration(X, n_mels=N_MELS):
    """Quotient by DURATION -- the operation every physical domain already gets.

    Why this exists
    ---------------
    `load_physical` in reproduce.py resamples every physical recording to L
    points regardless of how long it really was: a manoeuvre, a beat and a
    discharge all arrive on the same grid, and their true durations are
    quotiented away. That is a declared nuisance -- gain, offset, time origin,
    duration -- and every physical domain gets it.

    This loader did the opposite. It zero-pads every utterance to one second,
    and the log-mel of a zero-padded tail is EXACTLY the floor value, the same
    constant in every recording. In the FSDD cache the median recording carries
    fifty of its hundred and one frames as pure padding, and 55% of all frames
    in the set are that constant. More than half of every vector therefore says
    one thing only: this recording was shorter than a second.

    After l2-normalisation a large shared constant drags every cosine distance
    towards zero, within-class and between-class alike. It is the same defect
    the z_normalise docstring in run_experiment.py describes for battery
    discharge -- "~3.3 V of constant plus ~0.2 V of signal, so after
    l2-normalisation every curve is nearly the same unit vector and the metric
    measures nothing" -- and the within-class median gives it away: 0.025 for
    the padded spoken set against 0.47 for MNIST.

    What this does, and what it does not
    -----------------------------------
    It drops the padding frames and resamples what is left back onto the SAME
    number of frames the representation already had. There is no threshold: the
    padding frames are exactly equal to the floor, to floating-point equality,
    so they are found and not estimated. There is no new constant either: the
    output has the dimension the input had.

    It is not a de-noising step, not an alignment step, and not tuned. It is
    the duration quotient, declared in the paper's own list, applied to the one
    domain that was not getting it.
    """
    X = np.asarray(X, float)
    T = X.shape[1] // n_mels
    A = X.reshape(len(X), n_mels, T)
    floor = A.min()
    xn = np.linspace(0.0, 1.0, T)
    out = np.empty_like(A)
    for i, a in enumerate(A):
        keep = ~np.all(np.abs(a - floor) < 1e-9, axis=0)
        idx = np.flatnonzero(keep)
        b = a[:, idx[0]:idx[-1] + 1] if len(idx) > 1 else a
        if b.shape[1] == T:
            out[i] = b
        else:
            xo = np.linspace(0.0, 1.0, b.shape[1])
            out[i] = np.stack([np.interp(xn, xo, r) for r in b])
    return out.reshape(len(X), -1)


def duration_stats(X, y, n_mels=N_MELS):
    """How long each spoken digit actually is, before the duration quotient.

    The paper states four numbers from this -- the mean length of a spoken
    *two* and a *seven*, the spread of the ten class means, and the spread
    within one class across speakers -- to argue that duration is real but not
    readable once the speaker is declared benign. They were measured and never
    stored, so they were the only figures in the paper that had to be
    recomputed by hand to be checked. This returns them.

    Duration is the SPAN from the first occupied frame to the last, which is
    exactly what `quotient_duration` above removes; it is not the count of
    occupied frames, which differs when a recording has an internal silence.
    One frame is HOP/SR seconds.
    """
    X = np.asarray(X, float)
    y = np.asarray(y).astype(int)
    T = X.shape[1] // n_mels
    A = X.reshape(len(X), n_mels, T)
    floor = A.min()
    ms = HOP / SR * 1000.0
    span = np.empty(len(A))
    for i, a in enumerate(A):
        idx = np.flatnonzero(~np.all(np.abs(a - floor) < 1e-9, axis=0))
        span[i] = (idx[-1] - idx[0] + 1) * ms if len(idx) else T * ms
    per = {int(d): float(span[y == d].mean()) for d in sorted(set(y.tolist()))}
    return {"frame_ms": ms,
            "mean_ms_per_class": per,
            "spread_of_class_means_ms": float(np.std(list(per.values()))),
            "spread_within_class_ms":
                {int(d): float(span[y == d].std())
                 for d in sorted(set(y.tolist()))},
            # the paper quotes the spread "within a single class, across
            # speakers" as one number: it is the mean of the ten, not any one
            # class. Stored explicitly so the sentence has a field to point at.
            "mean_spread_within_class_ms":
                float(np.mean([span[y == d].std()
                               for d in sorted(set(y.tolist()))]))}


def load_spoken(root, cache=None, quotient="duration"):
    """Return (X, y, speaker) for the FSDD recordings under `root`.

    `root` is the directory holding the wav files. Results are cached to
    `cache` (an .npz) because decoding three thousand files takes longer than
    every other input in the package put together, and the cache is hashed in
    the input manifest like any other dataset.
    """
    def _finish(X, y, spk):
        # The cache stores the RAW declared observable, unchanged, so the
        # padded arm stays reproducible; the quotient is applied on top.
        return (quotient_duration(X) if quotient == "duration" else X), y, spk

    if cache and os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return _finish(z["X"], z["y"], z["spk"])

    import librosa

    files = sorted(glob.glob(os.path.join(root, "*.wav")))
    if not files:
        raise FileNotFoundError(f"sin wav en {root}")

    L = int(SR * MAX_SEC)
    X, y, spk = [], [], []
    for f in files:
        m = NAME.match(os.path.basename(f))
        if not m:
            continue
        audio, _ = librosa.load(f, sr=SR, mono=True)
        audio = (np.pad(audio, (0, L - len(audio))) if len(audio) < L
                 else audio[:L])
        S = librosa.feature.melspectrogram(y=audio, sr=SR, n_mels=N_MELS,
                                           hop_length=HOP, win_length=WIN,
                                           power=2.0)
        X.append(np.log(S + 1e-8).reshape(-1).astype(np.float32))
        y.append(int(m.group(1)))
        spk.append(m.group(2))

    X = np.stack(X)
    y = np.asarray(y, dtype=np.int64)
    spk = np.asarray(spk)
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        np.savez_compressed(cache, X=X, y=y, spk=spk)
    return _finish(X, y, spk)
