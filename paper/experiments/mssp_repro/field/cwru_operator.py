"""
The CWRU asset-specific detector: one operator per shaft speed.

Ported from `bearing_autoencoder_cwru_per_asset.ipynb`. This is the ORACLE arm
of the CWRU experiments -- each speed fits its own autoencoder on its own
healthy windows and calibrates its own threshold on the same data. It is the
reference the online-calibration arm is compared against, not a deployable
procedure: nothing is held out.

WHY IT IS PORTED SEPARATELY FROM THE SHARED OPERATOR
----------------------------------------------------
Same architecture, different schedule again -- the learning-rate floor here is
1e-5 against 1e-6 for the NASA shared operator -- and, more importantly, a
different object. The shared operator is fitted on synthetic data and
transferred; this one sees the real healthy windows of its own speed. Keeping
them apart is what stopped an earlier confusion in this project, where a
stability figure measured for one was used to reason about the other.

WHAT THIS WAS BUILT TO ANSWER, AND WHAT IT FOUND
------------------------------------------------
The published CWRU table has 1797 RPM as an outlier on three counts: its
threshold is 35% below the mean of the other speeds, its healthy false-alarm
rate is the only one that differs (2.46% against 2.23%), and it is the only
speed not reaching 100% on ball faults. It also has half the healthy data --
203 windows against about 404.

The first hypothesis was that all of it was sample size, and that normalising
the threshold by each speed's own median residual would bring 1797 into line,
as normalising does for the NASA operator across training seeds. It does not.
Normalised, 1797 sits 29% below the others; matching every speed to 203
windows moves it to 51% below and RAISES the overall spread from 19% to 31%.
Sample size was the wrong explanation for the threshold.

What the experiment did establish, by measuring rather than assuming:

  * The false-alarm rate IS sample size. Truncated to 203 windows, all four
    speeds attain exactly 2.46%. At n=203 the 98th percentile is the
    fourth-largest order statistic rather than the eighth of 404; the
    difference is arithmetic and nothing to do with the operating condition.

  * The oracle memorises. Validation loss exceeds training loss by 2.4, 3.9,
    3.2 and 1.5 across the speeds -- 847,601 parameters on roughly 320
    training windows. That is not a defect: the oracle is DEFINED as the
    upper bound that uses everything and holds nothing out. But it means its
    false-alarm rate is optimistic, which makes the online arm's parity with
    it a conservative comparison rather than a flattering one.

  * 1797 is the one speed that does NOT memorise, at a ratio of 1.5. Its
    healthy record is the most homogeneous of the four, so its tighter radius
    is the correct outcome rather than an anomalous one.
"""

import numpy as np

from ..conv_autoencoder import assert_operator_learned, build_autoencoder
from .cwru import CWRU_REGIMES, CWRU_SPEEDS, load_asset_windows

__all__ = ["CWRU_LATENT_DIM", "CWRU_THRESHOLD_PERCENTILE",
           "AssetSpecificOperator", "evaluate_speed"]

CWRU_LATENT_DIM = 16
CWRU_THRESHOLD_PERCENTILE = 98.0

# Transcribed. Note the learning-rate floor: 1e-5 here, 1e-6 for the shared
# NASA operator. Both are the values their own experiments used.
CWRU_EPOCHS = 100
CWRU_BATCH_SIZE = 32
CWRU_LEARNING_RATE = 1e-3
CWRU_ES_PATIENCE = 10
CWRU_LR_FACTOR = 0.5
CWRU_LR_PATIENCE = 5
CWRU_MIN_LR = 1e-5
CWRU_VALIDATION_SPLIT = 0.20


class AssetSpecificOperator:
    """One autoencoder and one threshold, fitted on one speed's healthy data."""

    def __init__(self, *, seed=42, latent_dim=CWRU_LATENT_DIM,
                 epochs=CWRU_EPOCHS, batch_size=CWRU_BATCH_SIZE, verbose=0):
        self.seed = int(seed)
        self.latent_dim = int(latent_dim)
        self.epochs = int(epochs)
        self.batch_size = int(batch_size)
        self.verbose = verbose
        self.scaler_ = self.ae_ = self.encoder_ = None
        self.tau_ = self.history_ = None

    def fit(self, healthy_windows):
        from sklearn.preprocessing import StandardScaler
        from .shared_operator import seed_everything

        keras = seed_everything(self.seed)
        if keras is None:
            raise ModuleNotFoundError("the CWRU operator needs TensorFlow")

        raw = np.asarray(healthy_windows, dtype=np.float32)
        raw = raw.reshape(len(raw), -1)
        self.scaler_ = StandardScaler()
        X = self.scaler_.fit_transform(raw).astype(np.float32)[..., np.newaxis]

        self.ae_, self.encoder_ = build_autoencoder(X.shape[1], self.latent_dim)
        self.ae_.compile(optimizer=keras.optimizers.Adam(CWRU_LEARNING_RATE),
                         loss="mse")
        hist = self.ae_.fit(
            X, X, validation_split=CWRU_VALIDATION_SPLIT, epochs=self.epochs,
            batch_size=self.batch_size, shuffle=True, verbose=self.verbose,
            callbacks=[
                keras.callbacks.EarlyStopping(
                    monitor="val_loss", patience=CWRU_ES_PATIENCE,
                    restore_best_weights=True),
                keras.callbacks.ReduceLROnPlateau(
                    monitor="val_loss", factor=CWRU_LR_FACTOR,
                    patience=CWRU_LR_PATIENCE, min_lr=CWRU_MIN_LR),
            ])

        # Training loss for the pass/fail test, validation loss for the
        # overfitting warning. This operator memorises its 320-odd windows and
        # that is a property of the experiment, not a defect in the port.
        assert_operator_learned(float(min(hist.history["loss"])),
                                float(np.var(X)),
                                validation_mse=float(min(hist.history["val_loss"])),
                                name="CWRU asset-specific operator")

        healthy_scores = self.scores(healthy_windows)
        self.tau_ = float(np.percentile(healthy_scores,
                                        CWRU_THRESHOLD_PERCENTILE))
        self.history_ = {
            "epochs_run": len(hist.history["loss"]),
            "best_train_loss": float(min(hist.history["loss"])),
            "best_val_loss": float(min(hist.history["val_loss"])),
            "generalisation_gap": float(min(hist.history["val_loss"])
                                        / max(min(hist.history["loss"]), 1e-30)),
            "tau": self.tau_,
            "healthy_median": float(np.median(healthy_scores)),
        }
        return self

    def scores(self, windows):
        w = np.asarray(windows, dtype=np.float32)
        w = self.scaler_.transform(w.reshape(len(w), -1))
        X = w.astype(np.float32)[..., np.newaxis]
        rec = self.ae_.predict(X, verbose=0)
        return np.mean(np.square(X - rec), axis=(1, 2))


def evaluate_speed(data_root, speed, *, seed=42, epochs=CWRU_EPOCHS,
                   verbose=0, n_healthy=None):
    """
    Fit and evaluate one speed, returning everything the 1797 question needs.

    The normalised threshold is the point: `tau / healthy_median` is invariant
    to the operator's overall scale, so comparing it across speeds separates a
    gauge difference from a real one.
    """
    windows = load_asset_windows(data_root, speed)
    # `n_healthy` truncates the healthy set to a common size. That is the
    # controlled version of the comparison: with every speed given the same
    # number of windows, any remaining difference cannot be the sample size.
    if n_healthy is not None:
        windows = dict(windows)
        windows["healthy"] = windows["healthy"][:int(n_healthy)]
    op = AssetSpecificOperator(seed=seed, epochs=epochs, verbose=verbose).fit(
        windows["healthy"])

    out = {"speed": speed, "seed": seed,
           "n_healthy": int(len(windows["healthy"])),
           "tau": op.tau_, **op.history_}
    out["tau_normalised"] = op.tau_ / out["healthy_median"]

    healthy = op.scores(windows["healthy"])
    out["healthy_far"] = float(100 * np.mean(healthy > op.tau_))
    out["healthy_median"] = float(np.median(healthy))
    out["healthy_iqr"] = float(np.subtract(*np.percentile(healthy, [75, 25])))
    for regime in ("ball", "inner_race", "outer_race"):
        s = op.scores(windows[regime])
        out[f"{regime}_dr"] = float(100 * np.mean(s > op.tau_))
        out[f"{regime}_median"] = float(np.median(s))
        # Separation in units of the healthy spread: scale-free, so it is
        # comparable across speeds in a way the raw threshold is not.
        out[f"{regime}_margin"] = float(
            (np.median(s) - out["healthy_median"]) / out["healthy_iqr"])
    return out
