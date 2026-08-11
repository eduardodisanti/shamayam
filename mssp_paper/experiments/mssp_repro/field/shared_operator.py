"""
Layer B, stage 2: the shared simulator-trained operator.

This is the "OEM" autoencoder of the field experiments. It is trained ONLY on
synthetic nominal windows from the simulator, matched to the target archive's
sampling rate, and then transferred frozen to real bearings. No measured data
enters its fitting, which is what makes the per-asset radius the only thing
estimated from the field.

WHY THIS IS NOT `conv_autoencoder.ConvAEResidualOperator`
---------------------------------------------------------
The architectures are identical -- verified by test -- but the training
schedules are not, and the schedule is part of the published experiment:

                      Layer A2 operator     this (field, published)
    epoch budget      500                   100
    early stopping    patience 40           patience 10
    LR patience       15                    5
    LR floor          1e-7                  1e-6
    validation        0.2 split of train    separate 1000-window draw

Layer A2 uses the longer schedule deliberately, at the author's request, to
anneal to a floor. Reproducing the FIELD results requires the schedule those
results were produced under, so the two are kept apart rather than unified
behind a parameter with a convenient default. Using A2's numbers here would
silently produce a different operator and therefore different residuals,
different radii and different lead times.

REPRODUCIBILITY, AND ITS LIMIT
------------------------------
Data generation uses numpy's legacy global RNG, because the simulator does.
That is not a style choice one may quietly modernize: `np.random.seed(42)`
plus the exact order of draws is what makes the synthetic training set
reproducible, and `default_rng` would produce a different set. The order below
is transcribed from the notebook, including the fact that the asset signature
is drawn BEFORE `sample()` is called, since Python evaluates arguments first.

Training reproducibility is weaker and the docstring says so rather than
implying otherwise. `enable_op_determinism` makes repeated runs agree within
one TensorFlow build; it does not make a Linux x86 build agree with a macOS
ARM one. The published threshold is recorded as `PUBLISHED_TAU_MC` and the
tests compare against it with a tolerance, not for equality.
"""

import numpy as np

from ..bearing_simulator import NASA_PARAMS, CWRU_PARAMS, BearingSignalSimulator
from ..conv_autoencoder import assert_operator_learned
from .ims import make_windows

__all__ = ["OEM_SEED", "SIG_LEN", "LATENT_DIM", "THRESHOLD_PERCENTILE",
           "N_TRAIN", "N_VAL", "PUBLISHED_TAU_MC", "generate_oem_windows",
           "SharedFieldOperator"]

OEM_SEED = 42
SIG_LEN = 1200
LATENT_DIM = 16
THRESHOLD_PERCENTILE = 98.0

N_TRAIN = 4000
N_VAL = 1000

# Training hyperparameters, transcribed. Named constants rather than defaults
# buried in a signature, so a diff against the notebook is one glance.
EPOCHS = 100
BATCH_SIZE = 32
LEARNING_RATE = 1e-3
ES_PATIENCE = 10
LR_FACTOR = 0.5
LR_PATIENCE = 5
MIN_LR = 1e-6

# The Monte Carlo threshold reported by the published NASA run, kept as the
# reference the port is checked against. Cross-build training is not
# bit-reproducible, so the check asserts agreement to a stated tolerance.
#
# VERIFIED. `verify_operator.py` on the author's machine -- macOS ARM, Metal,
# TensorFlow 2.19.1 / Keras 3.15.1 -- reproduces it to 3.7% (0.011571 against
# 0.012016), with best val_loss 0.00693 against the notebook's 0.0073 and a
# matching first-epoch trace.
#
# Note the version. The published run used TensorFlow 2.16.2, and 2.19 is
# already past the change in how activity regularisation is reduced. The
# notebook as written would therefore no longer reproduce its own results on
# the machine that produced them; this port does, because `BatchMeanL1` states
# the reduction instead of inheriting it.
PUBLISHED_TAU_MC = 0.012016

PARAMS = {"nasa": NASA_PARAMS, "cwru": CWRU_PARAMS}



def seed_everything(seed=OEM_SEED):
    """
    Seed every generator the pipeline touches, in the notebook's order.

    Returns the keras module, or None when TensorFlow is absent -- callers in
    the data-generation path do not need it and should not be forced to
    install it.
    """
    np.random.seed(seed)
    try:
        import tensorflow as tf
        from tensorflow import keras
    except ModuleNotFoundError:
        return None

    keras.backend.clear_session()
    keras.utils.set_random_seed(seed)
    tf.random.set_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        # Older TensorFlow. Recorded rather than raised: determinism is a
        # property to report, not a precondition to enforce.
        pass
    return keras


def generate_oem_windows(n, *, regime="healthy", archive="nasa",
                         win=SIG_LEN, step=SIG_LEN, simulator=None):
    """
    Synthetic windows for training the shared operator.

    Signals are drawn one at a time and cut into windows until `n` are
    available, then truncated to exactly `n`. Each signal carries an
    independent asset signature drawn uniformly from [0.8, 1.2]^5, so the
    training set spans installation variability rather than one nominal unit.

    The draw order is load-bearing. `np.random.uniform(0.8, 1.2, 5)` consumes
    five values from the global stream BEFORE `sample()` consumes its own,
    because Python evaluates the argument first. Reordering these two lines
    changes every window produced, and changes them silently.
    """
    sim = simulator if simulator is not None else BearingSignalSimulator(
        PARAMS[archive])

    windows = []
    while len(windows) < n:
        asset_signature = np.random.uniform(0.8, 1.2, 5)
        signal = sim.sample(regime=regime, mc=True, coverage="wide",
                            asset_signature=asset_signature)
        windows.extend(make_windows(signal, win=win, step=step))
    return np.asarray(windows[:n], dtype=np.float32)


class SharedFieldOperator:
    """
    The frozen simulator-trained operator, with its scaler and threshold.

    `fit()` reproduces the published training run; `residuals()` scores real
    recordings through it. The scaler is fitted on the synthetic training
    windows and applied unchanged to field data, which is the transfer being
    tested: nothing measured adjusts either the operator or its normalisation.
    """

    def __init__(self, *, archive="nasa", seed=OEM_SEED, sig_len=SIG_LEN,
                 latent_dim=LATENT_DIM, epochs=EPOCHS,
                 batch_size=BATCH_SIZE, verbose=0):
        self.archive = archive
        self.seed = int(seed)
        self.sig_len = int(sig_len)
        self.latent_dim = int(latent_dim)
        self.epochs = int(epochs)
        self.batch_size = int(batch_size)
        self.verbose = verbose
        self.scaler_ = None
        self.ae_ = None
        self.tau_mc_ = None
        self.history_ = None

    # -- fitting -------------------------------------------------------

    def fit(self, n_train=N_TRAIN, n_val=N_VAL):
        from sklearn.preprocessing import StandardScaler
        from ..conv_autoencoder import build_autoencoder

        keras = seed_everything(self.seed)
        if keras is None:
            raise ModuleNotFoundError(
                "the shared field operator needs TensorFlow: pip install "
                "tensorflow. Layer A1 does not.")

        sim = BearingSignalSimulator(PARAMS[self.archive])
        X_train_raw = generate_oem_windows(n_train, archive=self.archive,
                                           win=self.sig_len, step=self.sig_len,
                                           simulator=sim)
        X_val_raw = generate_oem_windows(n_val, archive=self.archive,
                                         win=self.sig_len, step=self.sig_len,
                                         simulator=sim)

        self.scaler_ = StandardScaler()
        X_train = self.scaler_.fit_transform(X_train_raw).astype(np.float32)
        X_val = self.scaler_.transform(X_val_raw).astype(np.float32)
        X_train, X_val = X_train[..., np.newaxis], X_val[..., np.newaxis]

        self.ae_, self.encoder_ = build_autoencoder(self.sig_len,
                                                    self.latent_dim)
        self.ae_.compile(optimizer=keras.optimizers.Adam(
            learning_rate=LEARNING_RATE), loss="mse")

        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=ES_PATIENCE,
                restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss", factor=LR_FACTOR, patience=LR_PATIENCE,
                min_lr=MIN_LR),
        ]

        hist = self.ae_.fit(
            X_train, X_train, validation_data=(X_val, X_val),
            epochs=self.epochs, batch_size=self.batch_size, shuffle=True,
            callbacks=callbacks, verbose=self.verbose)

        val_mse = self._window_mse(X_val)

        # Check before anything downstream can consume the operator. Inputs
        # are standardised here, so the variance is 1 by construction; the
        # criterion is expressed as a fraction anyway, so that this call and
        # the Layer A2 one apply the same rule.
        assert_operator_learned(float(min(hist.history["val_loss"])),
                                float(np.var(X_val)))

        self.tau_mc_ = float(np.percentile(val_mse, THRESHOLD_PERCENTILE))

        epochs_run = len(hist.history["loss"])
        self.history_ = {
            "epochs_run": epochs_run,
            "budget": self.epochs,
            "stop_reason": ("budget_exhausted" if epochs_run >= self.epochs
                            else "early_stopping"),
            "best_val_loss": float(min(hist.history["val_loss"])),
            "final_val_loss": float(hist.history["val_loss"][-1]),
            "final_lr": float(hist.history.get("learning_rate",
                                               [LEARNING_RATE])[-1]),
            "tau_mc": self.tau_mc_,
            # Per-epoch curves, kept because the published notebook printed
            # them and they are the only cross-build check available: exact
            # agreement is impossible across TensorFlow builds, but a port
            # that got the data, the scaling or the architecture wrong would
            # diverge in the first few epochs rather than the last.
            "loss": [float(v) for v in hist.history["loss"]],
            "val_loss": [float(v) for v in hist.history["val_loss"]],
        }
        return self

    # -- scoring -------------------------------------------------------

    def _window_mse(self, X):
        rec = self.ae_.predict(X, verbose=0)
        return np.mean(np.square(X - rec), axis=(1, 2))

    def window_residuals(self, signal_1d, *, win=None, step=None):
        """Per-window reconstruction MSE of one raw signal."""
        if self.ae_ is None:
            raise RuntimeError("operator not fitted")
        win = self.sig_len if win is None else win
        step = win if step is None else step
        w = make_windows(np.asarray(signal_1d).reshape(-1), win=win, step=step)
        w = self.scaler_.transform(w.reshape(w.shape[0], -1)).astype(np.float32)
        return self._window_mse(w[..., np.newaxis])

    def recording_residuals(self, recordings, *, mode="mean", win=None,
                            step=None, predict_batch=2048):
        """
        One score per recording, aggregated by `dynamics.recording_score`.

        `recordings` is `(n_recordings, n_samples)`. The aggregation is
        explicit rather than defaulted because calibration and evaluation must
        use the same rule; see the argument in `dynamics.recording_score` for
        why the mean is correct at this window count.

        All windows of all recordings are scored in ONE pass rather than one
        call per recording. The arithmetic is identical -- windows are
        independent -- but the cost is not: an IMS bearing is 984 recordings
        of 17 windows, and paying Keras's per-call overhead 984 times instead
        of once dominates the run. The windows are cut first, scored in
        contiguous blocks, then split back by recording.
        """
        from ..dynamics import recording_score

        recordings = np.asarray(recordings)
        if recordings.ndim != 2:
            raise ValueError(
                f"expected (n_recordings, n_samples), got {recordings.shape}")
        if self.ae_ is None:
            raise RuntimeError("operator not fitted")

        win = self.sig_len if win is None else win
        step = win if step is None else step

        blocks = [make_windows(r, win=win, step=step) for r in recordings]
        counts = [len(b) for b in blocks]
        flat = np.concatenate(blocks, axis=0)
        flat = self.scaler_.transform(flat.reshape(flat.shape[0], -1))
        flat = flat.astype(np.float32)[..., np.newaxis]

        mse = np.empty(flat.shape[0], dtype=float)
        for start in range(0, flat.shape[0], predict_batch):
            chunk = flat[start:start + predict_batch]
            mse[start:start + len(chunk)] = self._window_mse(chunk)

        out, at = np.empty(len(recordings), dtype=float), 0
        for i, n in enumerate(counts):
            out[i] = recording_score(mse[at:at + n], mode=mode)
            at += n
        return out

    def describe_training(self):
        if self.history_ is None:
            return "not fitted"
        h = self.history_
        return (f"{h['epochs_run']}/{h['budget']} epochs, "
                f"stop={h['stop_reason']}, best val_loss="
                f"{h['best_val_loss']:.5f}, final lr {h['final_lr']:.2e}, "
                f"tau_MC(p{THRESHOLD_PERCENTILE:g})={h['tau_mc']:.6f}")
