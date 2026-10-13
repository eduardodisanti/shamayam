"""
Angular (order-domain) projection: an explicit section of the quotient map.

WHY THIS MODULE EXISTS
----------------------
The nuisance group of the paper includes shaft speed. Declaring that group in
the quotient space does not make the operator invariant to it: the residual of
the autoencoder is not G-invariant (Remarks 14-15). This module implements the
invariance BEFORE the operator, by choosing one canonical representative of
each speed orbit: the signal resampled to a fixed number of samples per shaft
revolution and cut into windows of a fixed number of revolutions.

The same projection also removes the acquisition sampling rate, which is what
the CWRU archive requires: its Normal Baseline was acquired at 48 kHz, while
the DE12 fault files the original pipeline used were acquired at 12 kHz.
Read at a common nominal rate, healthy and faulty windows differed by a factor
of four in time scale, which a trivial zero-crossing count separates without
any fault content (see NOTAS in the experiment output).

WHAT IS EXACT AND WHAT IS NOT
-----------------------------
* Components locked to the shaft -- harmonics and the bearing fault orders --
  land on fixed orders, so the projection is exact for them.
* Structural resonances are fixed in Hz. In the order domain their carrier
  moves by the relative speed change (about 4% across 1730-1797 rpm). The
  projection is therefore approximate for resonance-borne content; the paper
  must say so.
* A frequency-dependent difference between acquisition chains is NOT in the
  group and is NOT removed. Healthy and faulty data must come from the same
  acquisition (Normal + DE48), and both pass through this same projection.

CONVENTIONS
-----------
400 samples per revolution and 3 revolutions per window give 1200-sample
windows, the input length of the published operator. At 1797 rpm this is
equivalent to a 12 kHz acquisition; the usable band is 200 orders (~6 kHz).
"""

from dataclasses import dataclass, replace
from fractions import Fraction

import numpy as np
from scipy.signal import resample_poly

from ..bearing_simulator import BearingSignalSimulator

__all__ = ["SAMPLES_PER_REV", "REVS_PER_WINDOW", "ORDER_WINDOW",
           "estimate_shaft_frequency", "angular_resample", "project_signal",
           "angular_resample_varying",
           "order_windows", "OrderDomainSimulator"]

SAMPLES_PER_REV = 400
REVS_PER_WINDOW = 3
ORDER_WINDOW = SAMPLES_PER_REV * REVS_PER_WINDOW        # 1200

SEARCH_FRACTION = 0.04          # search nominal speed +/- 4%
HARMONICS = (1, 2, 3)
GRID_STEP_HZ = 0.002
MAX_DENOMINATOR = 2000          # rational approximation of the rate ratio


def estimate_shaft_frequency(x, fs, nominal_hz, *, search=SEARCH_FRACTION,
                             harmonics=HARMONICS, step_hz=GRID_STEP_HZ):
    """
    Shaft frequency of a constant-speed record, from its spectrum.

    Harmonic-sum estimator: for each candidate f in nominal*(1 +/- search),
    sum log|X(h f)| over the harmonics, and take the maximiser. Summing
    harmonics makes the estimate robust to any single harmonic being masked
    by a nearby line, which happens in CWRU (the 2x line is sometimes beaten
    by a neighbouring component). Spectrum is zero-padded x4 and read by
    linear interpolation, so the resolution is set by `step_hz`, not by the
    record length; the accuracy is still limited by it (about 0.1-0.2 Hz for
    5-10 s records, i.e. under 1% of shaft speed, i.e. under 0.03 rev of
    drift over a 3-revolution window).
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    x = x - x.mean()
    n = len(x)
    nfft = 1 << int(np.ceil(np.log2(4 * n)))
    mag = np.abs(np.fft.rfft(x * np.hanning(n), nfft))
    freqs = np.fft.rfftfreq(nfft, 1.0 / fs)
    logmag = np.log(mag + 1e-12 * mag.max())

    grid = np.arange(nominal_hz * (1 - search), nominal_hz * (1 + search),
                     step_hz)
    score = np.zeros_like(grid)
    for h in harmonics:
        score += np.interp(h * grid, freqs, logmag)
    return float(grid[int(np.argmax(score))])


def angular_resample(x, fs, shaft_hz, spr=SAMPLES_PER_REV):
    """
    Resample a constant-speed record to `spr` samples per revolution.

    Polyphase resampling with its anti-aliasing filter, at a rational
    approximation of the rate ratio. The relative error of the ratio is below
    1/MAX_DENOMINATOR**2, negligible against the speed-estimation error.
    """
    target_fs = spr * shaft_hz
    ratio = Fraction(target_fs / fs).limit_denominator(MAX_DENOMINATOR)
    return resample_poly(np.asarray(x, dtype=np.float64), ratio.numerator,
                         ratio.denominator)


def project_signal(x, fs, nominal_hz, *, spr=SAMPLES_PER_REV, shaft_hz=None):
    """
    Estimate the speed (unless given) and resample. Returns (y, shaft_hz).
    """
    if shaft_hz is None:
        shaft_hz = estimate_shaft_frequency(x, fs, nominal_hz)
    return angular_resample(x, fs, shaft_hz, spr=spr), float(shaft_hz)


FINE_SPR_FACTOR = 8             # intermediate angular rate: 8 x 400 = 3200/rev
SPEED_LAG = 64                  # encoder references per speed estimate


def angular_resample_varying(x, fs, t_ref, theta_ref, *, spr=SAMPLES_PER_REV,
                             fine_factor=FINE_SPR_FACTOR):
    """
    Resample a record whose speed varies, given the shaft angle at known times.

    `t_ref` (s, increasing) and `theta_ref` (revolutions, increasing) sample the
    shaft angle, e.g. at the rising edges of an encoder. Returns
    `(y, speed)`: `y` at `spr` samples per revolution over the angular span
    covered by the references, and `speed` the shaft speed (Hz) at each
    output sample.

    Two-stage anti-aliasing (computed order tracking):
      1. a fixed low-pass in time at 0.4 * fine_spr * f_min, where f_min is the
         lowest speed in the record, then linear interpolation onto a fine
         uniform angle grid of `fine_factor * spr` samples per revolution;
      2. polyphase decimation by `fine_factor` IN THE ANGLE DOMAIN, whose filter
         is therefore fixed in orders and identical at every speed.
    Stage 2 sets the usable band (spr/2 orders) independently of speed; stage
    1 only has to keep the fine grid free of aliasing, which its cutoff does
    with a wide margin at every speed in the record.
    """
    from scipy.signal import butter, sosfiltfilt

    x = np.asarray(x, dtype=np.float64).reshape(-1)
    t_ref = np.asarray(t_ref, dtype=np.float64)
    theta_ref = np.asarray(theta_ref, dtype=np.float64)
    fine = int(fine_factor) * int(spr)
    # Speed over SPEED_LAG references: a single encoder period is a few
    # samples long, so per-edge speed is dominated by timing quantisation.
    lag = min(SPEED_LAG, len(t_ref) - 1)
    dtheta = (theta_ref[lag:] - theta_ref[:-lag]) / (t_ref[lag:] - t_ref[:-lag])
    t_mid = 0.5 * (t_ref[lag:] + t_ref[:-lag])
    f_min = float(dtheta.min())
    cutoff = 0.4 * fine * f_min
    if cutoff < 0.5 * fs:
        sos = butter(8, cutoff, fs=fs, output="sos")
        x = sosfiltfilt(sos, x)
    t = np.arange(len(x)) / fs
    grid = np.arange(np.ceil(theta_ref[0] * fine), np.floor(theta_ref[-1] * fine)) / fine
    t_grid = np.interp(grid, theta_ref, t_ref)
    y_fine = np.interp(t_grid, t, x)
    y = resample_poly(y_fine, 1, int(fine_factor))
    speed_fine = np.interp(t_grid, t_mid, dtheta)
    speed = speed_fine[::int(fine_factor)][:len(y)]
    return y, speed


def order_windows(y, *, revs=REVS_PER_WINDOW, spr=SAMPLES_PER_REV):
    """Non-overlapping windows of `revs` revolutions, as (n, revs*spr)."""
    y = np.asarray(y)
    win = revs * spr
    n = len(y) // win
    if n == 0:
        raise ValueError(f"record of {len(y)} samples holds no window of {win}")
    return y[:n * win].reshape(n, win)


class _SpeedRecordingSimulator(BearingSignalSimulator):
    """The vendored simulator, recording the speed factor of each draw."""

    last_speed = None

    def _healthy_base(self, amp=1.0, phase=0.0, speed_scale=1.0,
                      asset_signature=None):
        self.last_speed = float(speed_scale)
        return super()._healthy_base(amp, phase, speed_scale, asset_signature)


class OrderDomainSimulator:
    """
    Simulated windows passed through the SAME projection as field data.

    The simulator draws a random speed factor internally; it is recorded and
    used as the known shaft frequency, so the simulated speed nuisance is
    removed exactly while resonance-borne content moves in order exactly as
    it does on a real machine. Signals are drawn longer than one window and a
    window is cut away from both ends, so the resampler's edge transient never
    enters the training data.
    """

    def __init__(self, params, *, duration=0.2, offset_samples=200,
                 spr=SAMPLES_PER_REV, revs=REVS_PER_WINDOW):
        self.params = replace(params, duration=float(duration))
        self.sim = _SpeedRecordingSimulator(self.params)
        self.spr, self.revs = int(spr), int(revs)
        self.offset = int(offset_samples)

    def window(self, regime="healthy", *, asset_signature=None):
        x = self.sim.sample(regime=regime, mc=True, coverage="wide",
                            asset_signature=asset_signature)
        shaft = self.params.shaft_freq * self.sim.last_speed
        y = angular_resample(x, self.params.fs, shaft, spr=self.spr)
        win = self.spr * self.revs
        if len(y) < self.offset + win:
            raise ValueError("simulated record too short for one window")
        return y[self.offset:self.offset + win]

    def windows(self, n, regime="healthy"):
        """`n` windows, one per draw, each with its own asset signature
        drawn uniformly from [0.8, 1.2]^5 as in the published generator."""
        out = np.empty((n, self.spr * self.revs), dtype=np.float32)
        for i in range(n):
            sig = np.random.uniform(0.8, 1.2, 5)
            out[i] = self.window(regime, asset_signature=sig)
        return out
