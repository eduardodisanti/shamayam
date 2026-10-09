"""
Surrogate hierarchy for the one-class null (Theiler et al. 1992;
Schreiber & Schmitz 1996).

Each surrogate is generated PER SIGNAL, so it inherits that signal's own
statistics. What it does NOT inherit is the phase structure -- and the shape of
a waveform (idle - inrush - plateau - drop) IS a phase relationship. If the
compression we measure comes from shared shape, surrogates must not compress.

  shuffle  permute the time axis.
           preserves: amplitude distribution.
           destroys : everything else, including the spectrum.
           null     : "it is not white noise with these amplitudes."  WEAK.

  ft       randomise Fourier phases, keep the amplitude spectrum.
           preserves: the power spectrum exactly, hence all linear correlation.
           destroys : phase structure, i.e. waveform shape and nonlinearity.
           null     : "it is not a linear Gaussian process with this spectrum."

  iaaft    iteratively impose BOTH the amplitude spectrum and the amplitude
           distribution (Schreiber & Schmitz 1996).
           preserves: spectrum AND marginal distribution.
           destroys : phase structure.
           null     : the strongest standard one. STRONG.
"""
import numpy as np


def surrogate_shuffle(X, rng):
    return np.stack([r[rng.permutation(len(r))] for r in X])


def surrogate_ft(X, rng):
    """Phase randomisation. Keeps |FFT| exactly; DC and Nyquist stay real."""
    out = np.empty_like(X)
    for i, r in enumerate(X):
        F = np.fft.rfft(r)
        ph = rng.uniform(0, 2 * np.pi, len(F))
        ph[0] = 0.0                                  # DC real
        if len(r) % 2 == 0:
            ph[-1] = 0.0                             # Nyquist real
        out[i] = np.fft.irfft(np.abs(F) * np.exp(1j * ph), n=len(r))
    return out


def surrogate_iaaft(X, rng, iters=100, tol=1e-8):
    """
    Iterative amplitude-adjusted Fourier transform.
    Alternates: impose the target amplitude spectrum, then rank-remap onto the
    target amplitude distribution. Converges to a series matching both.
    """
    out = np.empty_like(X)
    for i, r in enumerate(X):
        n = len(r)
        target_amp = np.abs(np.fft.rfft(r))
        sorted_vals = np.sort(r)
        s = rng.permutation(r)                        # start from a shuffle
        prev = None
        for _ in range(iters):
            F = np.fft.rfft(s)
            s = np.fft.irfft(target_amp * np.exp(1j * np.angle(F)), n=n)
            ranks = np.argsort(np.argsort(s))         # remap to the marginal
            s = sorted_vals[ranks]
            if prev is not None and np.max(np.abs(s - prev)) < tol:
                break
            prev = s.copy()
        out[i] = s
    return out


SURROGATES = {"shuffle": surrogate_shuffle,
              "ft": surrogate_ft,
              "iaaft": surrogate_iaaft}
