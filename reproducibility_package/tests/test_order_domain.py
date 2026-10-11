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
