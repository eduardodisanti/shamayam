"""
The angular projection removes speed and sampling rate, and nothing else.

These tests use synthetic signals whose order content is known, so the
invariance can be checked exactly rather than argued.
"""

import numpy as np
import pytest

from mssp_repro.bearing_simulator import CWRU_PARAMS
from mssp_repro.field.order_domain import (ORDER_WINDOW, SAMPLES_PER_REV,
                                           OrderDomainSimulator,
                                           estimate_shaft_frequency,
                                           order_windows, project_signal)


def shaft_locked(fs, shaft_hz, seconds, *, noise=0.0, seed=0):
    """Harmonics 1-5 and an impulse-like component at order 3.6, all locked
    to the shaft angle, so their order content is independent of speed."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(fs * seconds)) / fs
    theta = 2 * np.pi * shaft_hz * t                    # shaft angle
    x = sum(0.6 ** (k - 1) * np.sin(k * theta + 0.3 * k) for k in range(1, 6))
    x += 0.4 * np.sin(3.6 * theta) ** 15                 # sharp, order 3.6
    return x + noise * rng.standard_normal(len(t))


@pytest.mark.parametrize("fs,shaft", [(12000, 29.95), (48000, 28.76),
                                      (48000, 29.91), (20000, 33.33)])
def test_speed_estimate_within_a_fraction_of_a_percent(fs, shaft):
    x = shaft_locked(fs, shaft, 5.0, noise=0.5)
    est = estimate_shaft_frequency(x, fs, nominal_hz=round(shaft))
    assert abs(est - shaft) / shaft < 2e-3


def _projected(fs, shaft, seconds=5.0):
    y, _ = project_signal(shaft_locked(fs, shaft, seconds), fs, shaft,
                          shaft_hz=shaft)
    w = order_windows(y)
    return w[2:6]                                        # away from edges


def test_projection_removes_speed():
    a = _projected(12000, 28.76)
    b = _projected(12000, 29.95)
    err = np.linalg.norm(a - b) / np.linalg.norm(a)
    assert err < 0.02


def test_projection_removes_sampling_rate():
    a = _projected(12000, 29.95)
    b = _projected(48000, 29.95)
    err = np.linalg.norm(a - b) / np.linalg.norm(a)
    assert err < 0.02


def test_unprojected_signals_differ_strongly():
    """Control: without the projection the same two records do NOT agree,
    so the tests above are not passing trivially."""
    a = shaft_locked(12000, 28.76, 1.0)[:ORDER_WINDOW]
    b = shaft_locked(12000, 29.95, 1.0)[:ORDER_WINDOW]
    assert np.linalg.norm(a - b) / np.linalg.norm(a) > 0.2


def test_window_shape():
    w = order_windows(np.zeros(ORDER_WINDOW * 3 + 17))
    assert w.shape == (3, ORDER_WINDOW)


def test_simulator_windows_sit_on_shaft_orders():
    np.random.seed(0)
    w = OrderDomainSimulator(CWRU_PARAMS).windows(20)
    assert w.shape == (20, ORDER_WINDOW) and np.all(np.isfinite(w))
    # 3 revolutions per window: order 1 is FFT bin 3, whatever the speed draw
    spec = np.abs(np.fft.rfft(w - w.mean(axis=1, keepdims=True), axis=1))
    assert np.all(np.argmax(spec[:, 1:40], axis=1) + 1 == 3)
    assert SAMPLES_PER_REV * 3 == ORDER_WINDOW


# ------------------------------------------------- speed varying within a record

from mssp_repro.field.order_domain import angular_resample_varying   # noqa: E402
from mssp_repro.field.ottawa import encoder_angle                     # noqa: E402


def _sweep(fs, f0, f1, seconds, cpr=1024):
    """Shaft angle (rev) for a linear speed sweep, an order-locked signal on
    it, and the square-wave encoder the Ottawa rig records."""
    t = np.arange(int(fs * seconds)) / fs
    theta = f0 * t + 0.5 * (f1 - f0) / seconds * t ** 2          # revolutions
    ph = 2 * np.pi * theta
    x = sum(0.6 ** (k - 1) * np.sin(k * ph + 0.3 * k) for k in range(1, 6))
    x += 0.4 * np.sin(3.57 * ph / 2) ** 16                       # order 3.57
    enc = np.where(np.sin(2 * np.pi * cpr * theta) > 0, 4.3, 0.04)
    return x, enc, theta


def test_encoder_angle_recovers_the_shaft_angle():
    fs = 200_000
    _, enc, theta_true = _sweep(fs, 12.0, 28.0, 2.0)
    t, theta = encoder_angle(enc, fs)
    truth = np.interp(t, np.arange(len(theta_true)) / fs, theta_true)
    err = (theta - theta[0]) - (truth - truth[0])
    assert np.max(np.abs(err)) < 1e-3                    # revolutions


def _project_sweep(f0, f1):
    fs = 200_000
    x, enc, _ = _sweep(fs, f0, f1, 3.0)
    t, theta = encoder_angle(enc, fs)
    y, speed = angular_resample_varying(x, fs, t, theta)
    return y, speed


def test_varying_speed_projection_is_speed_invariant():
    """The same order-locked signal under opposite sweeps (12->28 Hz and
    28->12 Hz) projects to the same windows: speed is removed even when it
    changes within a window."""
    ya, sa = _project_sweep(12.0, 28.0)
    yb, sb = _project_sweep(28.0, 12.0)
    assert sa[100] < 15 and sb[100] > 25
    # Both start at the first encoder edge (zero angle) on the same signal
    # phase; compare away from the record ends (filter transients).
    n = min(len(ya), len(yb))
    a, b = ya[2 * ORDER_WINDOW:n - 2 * ORDER_WINDOW], yb[2 * ORDER_WINDOW:n - 2 * ORDER_WINDOW]
    assert np.sqrt(np.mean((a - b) ** 2)) / np.sqrt(np.mean(a ** 2)) < 0.02


def test_varying_speed_projection_matches_the_angle_domain_signal():
    fs = 200_000
    x, enc, theta_true = _sweep(fs, 12.0, 28.0, 3.0)
    t, theta = encoder_angle(enc, fs)
    y, _ = angular_resample_varying(x, fs, t, theta)
    ph = 2 * np.pi * (np.arange(len(y)) / SAMPLES_PER_REV + np.ceil(theta[0]))
    ref = sum(0.6 ** (k - 1) * np.sin(k * ph + 0.3 * k) for k in range(1, 6))
    sl = slice(2 * ORDER_WINDOW, len(y) - 2 * ORDER_WINDOW)
    # harmonics 1-5 only: compare after removing the order-3.57 component
    # through a projection onto the harmonic basis
    basis = np.stack([f(k * ph[sl]) for k in range(1, 6) for f in (np.sin, np.cos)], 1)
    coef, *_ = np.linalg.lstsq(basis, y[sl], rcond=None)
    fit = basis @ coef
    assert np.sqrt(np.mean((fit - ref[sl]) ** 2)) / np.sqrt(np.mean(ref[sl] ** 2)) < 0.02
