"""
University of Ottawa bearing data under time-varying speed (Huang & Baddour,
Mendeley Data v43hmbwxpm v2): loading, and the shaft angle from the encoder.

Each file is 10 s at 200 kHz with two channels: Channel_1 the accelerometer,
Channel_2 the raw encoder output, a square wave of 1024 cycles per
revolution. The shaft angle is read from the rising edges of that wave, with
sub-sample timing from linear interpolation of the threshold crossing.

File names are <condition>-<profile>-<trial>.mat:
  condition  H healthy, I inner race, O outer race, B ball, C combined
  profile    A increasing, B decreasing, C increasing then decreasing,
             D decreasing then increasing
  trial      1-3
"""

from pathlib import Path

import numpy as np

from .order_domain import angular_resample_varying, order_windows

__all__ = ["OTTAWA_FS", "OTTAWA_CPR", "CONDITIONS", "PROFILES", "TRIALS",
           "record_path", "load_record", "encoder_angle", "project_record"]

OTTAWA_FS = 200_000
OTTAWA_CPR = 1024
CONDITIONS = {"H": "1 Data collected from a healthy bearing",
              "I": "2 Data collected from a bearing with inner race fault",
              "O": "3 Data collected from a bearing with outer race fault",
              "B": "4 Data collected from a bearing with ball fault",
              "C": "5 Data collected from a bearing with a combination of faults"}
PROFILES = {"A": "increasing", "B": "decreasing",
            "C": "increasing then decreasing", "D": "decreasing then increasing"}
TRIALS = (1, 2, 3)
ENCODER_THRESHOLD = 2.0          # volts; the wave swings between ~0 and ~4.3


def record_path(root, condition, profile, trial):
    return Path(root) / CONDITIONS[condition] / f"{condition}-{profile}-{trial}.mat"


def load_record(root, condition, profile, trial):
    """(vibration, encoder) as float64 arrays."""
    from scipy.io import loadmat
    d = loadmat(record_path(root, condition, profile, trial))
    return (np.asarray(d["Channel_1"], dtype=np.float64).ravel(),
            np.asarray(d["Channel_2"], dtype=np.float64).ravel())


def encoder_angle(encoder, fs=OTTAWA_FS, cpr=OTTAWA_CPR,
                  threshold=ENCODER_THRESHOLD):
    """
    (t, theta): times (s) of the rising edges and the shaft angle there, in
    revolutions from the first edge.
    """
    e = np.asarray(encoder, dtype=np.float64)
    above = e > threshold
    i = np.flatnonzero(~above[:-1] & above[1:])          # e[i] <= thr < e[i+1]
    frac = (threshold - e[i]) / (e[i + 1] - e[i])
    t = (i + frac) / fs
    theta = np.arange(len(t)) / cpr
    return t, theta


def project_record(x, encoder, fs=OTTAWA_FS, cpr=OTTAWA_CPR, **kw):
    """Order-domain windows of one record and the mean speed of each window."""
    t, theta = encoder_angle(encoder, fs, cpr)
    y, speed = angular_resample_varying(x, fs, t, theta, **kw)
    W = order_windows(y)
    S = order_windows(speed).mean(axis=1)
    return W, S
