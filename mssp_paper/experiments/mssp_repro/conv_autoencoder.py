"""
The Conv1D representation operator of the technical note.

WHY THIS ARCHITECTURE AND NOT ANOTHER
-------------------------------------
The architecture below is transcribed verbatim from
`journal_paper/bearing_autoencoder_cwru_per_asset.ipynb` and yields the same
847,601 trainable parameters reported there. It is reproduced rather than
replaced for two reasons, one procedural and one substantive.

Procedurally, the paper describes this operator, so a package that
demonstrated a different one would be demonstrating a different system.

Substantively, the convolution is not an implementation detail here. An
observation window is a delay-coordinate vector [rem:delay_embedding], and a
phase shift acts on the reconstructed orbit as the flow itself
[rem:nuisance_on_attractor]. Translation equivariance is therefore the
inductive bias that matches the nuisance group the framework quotients out. A
fully connected network of equal capacity would have to learn that structure
from data; a convolutional one has it by construction. Choosing the
architecture for packaging convenience rather than for this alignment would
invert the priorities.

DETERMINISM
-----------
`tf.config.experimental.enable_op_determinism()` is activated in `configure`,
together with `keras.utils.set_random_seed`. With both in force, repeated runs
on the same machine and the same TensorFlow build produce bit-identical
weights and residuals; `tests/test_conv_autoencoder.py` pins this. Two
caveats are worth stating plainly rather than discovering later.

First, determinism is guaranteed within a build, not across them: a different
TensorFlow version, a different CPU instruction set or a GPU backend may
produce different results in the last bits, because op determinism constrains
the order of reductions but not the kernels chosen by a different library.
Second, op determinism costs speed, sometimes considerably, because it
disables non-deterministic fast paths. Both are accepted here: this operator
is used for demonstration rather than for the theory verification, which is in
the framework-free part of the package and is bit-exact by construction.
"""

import os

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("PYTHONHASHSEED", "0")

# Deterministic cuDNN/oneDNN reductions where the backend honours it.
os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
os.environ.setdefault("TF_CUDNN_DETERMINISTIC", "1")

LATENT_DIM = 16
EXPECTED_PARAMS = 847_601          # as reported in the technical note


def configure(seed=42):
    """Seed every generator and switch on deterministic kernels."""
    import tensorflow as tf
    from tensorflow import keras

    keras.backend.clear_session()
    keras.utils.set_random_seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:                                   # older builds
        pass
    return tf, keras


# An autoencoder that leaves this fraction of the input variance
# unreconstructed has not learned the data. Healthy runs of both layers sit
# below 0.01; the collapsed runs described in `assert_operator_learned` sit
# above 0.7, so the threshold is not delicate.
MAX_UNEXPLAINED_VARIANCE = 0.5


LATENT_L1 = 1.5e-4


class BatchMeanL1:
    """
    L1 activity regularisation reduced by the MEAN over the batch.

    WHY THIS EXISTS RATHER THAN `keras.regularizers.l1`
    ---------------------------------------------------
    Keras changed how activity regularisation is reduced. Under TensorFlow
    2.16, which produced the published results, the penalty is effectively
    averaged over the batch; later releases sum it, making it batch-size times
    larger -- 32 here. Summed, it overwhelms the reconstruction term, the
    latent code collapses to zero and the decoder emits a constant, while
    `fit` returns normally and the loss curve looks monotone and healthy.

    The obvious response is to pin TensorFlow to 2.16. That was the first fix
    and it was the wrong one: a reproducibility package whose results depend
    on a frozen version of a fast-moving library has a short shelf life, and
    the reader who most needs it is the one furthest in the future, on a
    Python for which no 2.16 wheel exists.

    Stating the reduction explicitly makes the operator version-independent
    instead. Measured against the published trace (loss 0.2315, 0.0363, 0.0243
    over the first three epochs) this reproduces the optimisation regime under
    TensorFlow 2.21 to 0.2589, 0.0304, 0.0178 -- agreement to the level that
    backend and initialisation differences allow, and nothing like the 1.0000
    of a collapsed run.

    `assert_operator_learned` remains as the backstop, because the next
    convention change will not announce itself either.
    """

    def __init__(self, l1=LATENT_L1):
        self.l1 = float(l1)

    def __call__(self, x):
        import tensorflow as tf
        n = tf.cast(tf.shape(x)[0], x.dtype)
        return self.l1 * tf.reduce_sum(tf.abs(x)) / n

    def get_config(self):
        return {"l1": self.l1}


def assert_operator_learned(reconstruction_mse, input_variance):
    """
    Refuse an operator that trained "successfully" without learning anything.

    THE FAILURE THIS CATCHES
    ------------------------
    The architecture puts an L1 `activity_regularizer` on the latent layer.
    Keras changed how activity regularisation is reduced over a batch: the
    published runs (TensorFlow 2.16.2) effectively average it, while later
    releases sum it, multiplying the penalty by the batch size. Under the
    summed convention the penalty overwhelms the reconstruction term and the
    latent is driven towards zero.

    Nothing about that looks like an error. `fit` returns normally and the
    loss curve is monotone; it simply settles near the variance of the input,
    which is what predicting a constant costs. Every downstream quantity --
    residuals, radii, false-alarm rates, lead times -- is then computed from
    an operator that reconstructs nothing, and none of them look obviously
    wrong either. The check is therefore not defensive programming; it is the
    difference between a reproduction and a number-shaped artefact.

    THE CRITERION IS RELATIVE, DELIBERATELY
    ---------------------------------------
    An absolute loss threshold only works on standardised inputs. Layer A2
    fits raw simulator windows whose variance is not 1, and there the same
    collapse shows up as a loss of 0.53 rather than 1.0 -- which an absolute
    rule reads as healthy. What is invariant is the FRACTION of input
    variance left unreconstructed. Observed: 0.004 and 0.007 for the two
    published runs, 0.75 and 0.996 for the same code under a later Keras.
    """
    import sys

    var = float(input_variance)
    if not np.isfinite(var) or var <= 0:
        return
    unexplained = float(reconstruction_mse) / var
    if unexplained <= MAX_UNEXPLAINED_VARIANCE:
        return

    try:
        import tensorflow as tf
        version = f"TensorFlow {tf.__version__}"
    except Exception:                              # pragma: no cover
        version = "unknown TensorFlow"
    raise RuntimeError(
        f"the autoencoder trained but did not learn: it leaves "
        f"{100 * unexplained:.0f}% of the input variance unreconstructed "
        f"(mse {float(reconstruction_mse):.4g} against variance {var:.4g}). "
        f"A working operator leaves under 1%.\n\n"
        f"This is almost certainly the activity-regulariser reduction "
        f"change. You are on {version}; the published results were produced "
        f"under TensorFlow 2.16.2, where the L1 penalty on the latent layer "
        f"is averaged over the batch rather than summed. Summed, it is "
        f"batch-size times larger and crushes the latent code to zero.\n\n"
        f"Install the pinned version (see requirements.txt), or drop the "
        f"activity regulariser knowingly and report that the operator "
        f"differs from the published one.\n"
        f"Python {sys.version.split()[0]}.")


def build_autoencoder(sig_len, latent_dim=LATENT_DIM):
    """
    Transcribed verbatim from the technical note.

    Encoder  Conv1D(32,16,s2) -> Conv1D(64,8,s2) -> Conv1D(128,4,s2)
             -> Flatten -> Dense(latent, l1 activity regulariser)
    Decoder  Dense -> Reshape -> Conv1DTranspose(128,4,s2)
             -> Conv1DTranspose(64,8,s2) -> Conv1DTranspose(32,16,s2)
             -> Conv1D(1,1, linear)  [cropped to sig_len]

    All activations are ReLU except the latent and the output, which are
    linear. A ReLU network is piecewise affine and therefore extrapolates
    affinely outside the training region, which is a legitimate reason to
    doubt that it avoids the pathology of a purely linear operator; the
    distance-proxy probe in `probes.py` settles the question empirically
    rather than by appeal to nonlinearity.
    """
    from tensorflow import keras
    from tensorflow.keras import layers, Model

    inp = keras.Input(shape=(sig_len, 1), name="signal_in")
    x = layers.Conv1D(32, 16, strides=2, padding="same", activation="relu")(inp)
    x = layers.Conv1D(64, 8, strides=2, padding="same", activation="relu")(x)
    x = layers.Conv1D(128, 4, strides=2, padding="same", activation="relu")(x)
    conv_shape = x.shape[1:]
    x = layers.Flatten()(x)
    latent = layers.Dense(
        latent_dim,
        activity_regularizer=BatchMeanL1(LATENT_L1),
        name="latent",
    )(x)

    y = layers.Dense(conv_shape[0] * conv_shape[1], activation="relu")(latent)
    y = layers.Reshape(conv_shape)(y)
    y = layers.Conv1DTranspose(128, 4, strides=2, padding="same",
                               activation="relu")(y)
    y = layers.Conv1DTranspose(64, 8, strides=2, padding="same",
                               activation="relu")(y)
    y = layers.Conv1DTranspose(32, 16, strides=2, padding="same",
                               activation="relu")(y)
    y = layers.Conv1D(1, 1, padding="same", activation="linear",
                      name="signal_out")(y)
    if y.shape[1] > sig_len:
        y = layers.Cropping1D((0, y.shape[1] - sig_len))(y)

    return Model(inp, y, name="bearing_autoencoder"), Model(inp, latent,
                                                            name="encoder")


# --- default training schedule ---------------------------------------------
# Convergence is decided by the data, not by a fixed epoch count. The budget is
# an upper bound that should not normally be reached: training stops when the
# validation loss has not improved for `PATIENCE` epochs, and the learning rate
# is annealed whenever it plateaus, down to `MIN_LR`, at which point further
# reduction cannot help and early stopping ends the run.
MAX_EPOCHS = 500
PATIENCE = 40                 # early-stopping patience, in epochs
LR_PATIENCE = 15              # plateau patience before annealing
LR_FACTOR = 0.5
MIN_LR = 1e-7                 # annihilation floor for the learning rate
VALIDATION_SPLIT = 0.2
MIN_DELTA = 1e-7


class ConvAEResidualOperator:
    """
    Representation operator with reconstruction-error residual, matching the
    published pipeline. Fitted on nominal windows only.

    TRAINING SCHEDULE
    -----------------
    `epochs` is a ceiling, not a target. Three mechanisms decide when training
    actually ends, and the realised schedule is recorded in `history_` so that
    any table built from this operator can state what was run rather than what
    was requested:

      * ReduceLROnPlateau anneals the learning rate by `lr_factor` after
        `lr_patience` epochs without validation improvement, down to `min_lr`.
        Once the floor is reached, further annealing is impossible and the run
        can only end by early stopping or by exhausting the budget.
      * EarlyStopping halts after `patience` epochs without improvement and
        restores the best weights, so the returned operator is the best seen
        rather than the last.
      * The budget `epochs` caps the whole thing. Reaching it is reported as
        `stop_reason="budget_exhausted"`, which is a signal that the budget was
        too small rather than that training converged.

    Validation uses a held-out split of the nominal data. No fault observation
    enters at any point, so early stopping does not leak fault information: it
    selects for reconstructing nominal data, which is precisely the criterion
    the one-class formulation calls for.
    """

    def __init__(self, latent_dim=LATENT_DIM, seed=42, epochs=MAX_EPOCHS,
                 batch_size=64, learning_rate=1e-3, patience=PATIENCE,
                 lr_patience=LR_PATIENCE, lr_factor=LR_FACTOR, min_lr=MIN_LR,
                 validation_split=VALIDATION_SPLIT, min_delta=MIN_DELTA):
        self.latent_dim = int(latent_dim)
        self.seed = int(seed)
        self.epochs = int(epochs)
        self.batch_size = int(batch_size)
        self.learning_rate = float(learning_rate)
        self.patience = int(patience)
        self.lr_patience = int(lr_patience)
        self.lr_factor = float(lr_factor)
        self.min_lr = float(min_lr)
        self.validation_split = float(validation_split)
        self.min_delta = float(min_delta)
        self._ae = None
        self._enc = None
        self._dec = None
        self._sig_len = None
        self.history_ = None

    def fit(self, X_nominal, verbose=0):
        X = np.asarray(X_nominal, dtype=np.float32)
        if X.ndim != 2:
            raise ValueError("expected a 2-D array of windows")
        _, keras = configure(self.seed)
        self._sig_len = X.shape[1]
        self._ae, self._enc = build_autoencoder(self._sig_len, self.latent_dim)
        self._dec = None
        self._ae.compile(optimizer=keras.optimizers.Adam(self.learning_rate),
                         loss="mse")

        monitor = "val_loss" if self.validation_split > 0 else "loss"
        callbacks = [
            keras.callbacks.ReduceLROnPlateau(
                monitor=monitor, factor=self.lr_factor,
                patience=self.lr_patience, min_lr=self.min_lr,
                min_delta=self.min_delta, verbose=verbose),
            keras.callbacks.EarlyStopping(
                monitor=monitor, patience=self.patience,
                min_delta=self.min_delta, restore_best_weights=True,
                verbose=verbose),
        ]

        hist = self._ae.fit(
            X[..., None], X[..., None], epochs=self.epochs,
            batch_size=self.batch_size, shuffle=True,
            validation_split=self.validation_split,
            callbacks=callbacks, verbose=verbose)

        losses = hist.history.get(monitor, [])
        ran = len(hist.history.get("loss", []))
        lrs = [float(v) for v in hist.history.get("learning_rate",
                                                  hist.history.get("lr", []))]
        if ran >= self.epochs:
            reason = "budget_exhausted"
        elif lrs and lrs[-1] <= self.min_lr * (1.0 + 1e-9):
            reason = "early_stopping_at_lr_floor"
        else:
            reason = "early_stopping"

        self.history_ = {
            "epochs_run": int(ran),
            "epochs_budget": int(self.epochs),
            "stop_reason": reason,
            "monitor": monitor,
            "best_loss": float(min(losses)) if losses else float("nan"),
            "final_loss": float(losses[-1]) if losses else float("nan"),
            "best_epoch": int(int(np.argmin(losses)) + 1) if losses else -1,
            "initial_lr": float(self.learning_rate),
            "final_lr": float(lrs[-1]) if lrs else float(self.learning_rate),
            "lr_reductions": int(sum(1 for a, b in zip(lrs, lrs[1:]) if b < a)),
            "reached_lr_floor": bool(lrs and lrs[-1] <= self.min_lr * (1 + 1e-9)),
        }

        # Layer A2 carries the same activity regulariser as the field
        # operator, so it is exposed to the same silent collapse. Check here
        # too, before any residual is computed from this model.
        assert_operator_learned(float(min(losses)) if losses else float("nan"),
                                float(np.var(X)))
        return self

    def describe_training(self):
        """One-line summary of the realised schedule, for the results file."""
        h = self.history_
        if h is None:
            return "not fitted"
        return (f"{h['epochs_run']}/{h['epochs_budget']} epochs, "
                f"stop={h['stop_reason']}, best {h['monitor']}="
                f"{h['best_loss']:.4g} at epoch {h['best_epoch']}, "
                f"lr {h['initial_lr']:.1e} -> {h['final_lr']:.1e} "
                f"({h['lr_reductions']} reductions"
                f"{', floor reached' if h['reached_lr_floor'] else ''})")

    def residual(self, X):
        if self._ae is None:
            raise RuntimeError("operator not fitted")
        X = np.asarray(X, dtype=np.float32)
        if X.ndim != 2 or X.shape[1] != self._sig_len:
            raise ValueError("feature dimension mismatch")
        rec = self._ae.predict(X[..., None], verbose=0)
        return np.mean((X[..., None] - rec) ** 2, axis=(1, 2)).astype(np.float64)

    def encode(self, X):
        if self._enc is None:
            raise RuntimeError("operator not fitted")
        X = np.asarray(X, dtype=np.float32)
        return self._enc.predict(X[..., None], verbose=0)

    def decode(self, Z):
        """
        Decode latent codes; used by the distance-proxy probe.

        The decoder half is built once and cached. Rebuilding it per call
        creates a fresh `tf.function` each time and triggers the retracing
        warning TensorFlow emits after a handful of distinct traces, which is
        wasteful rather than incorrect but noisy enough to obscure real
        problems in the log.
        """
        if self._ae is None:
            raise RuntimeError("operator not fitted")
        if self._dec is None:
            from tensorflow.keras import Model
            self._dec = Model(self._ae.get_layer("latent").output,
                              self._ae.output)
        return self._dec.predict(np.asarray(Z, dtype=np.float32),
                                 verbose=0)[..., 0]

    @property
    def n_parameters(self):
        return int(self._ae.count_params()) if self._ae is not None else None
