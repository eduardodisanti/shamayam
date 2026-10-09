"""
Reproducibility package for

    "Anomaly Detection and Classification as an Inverse Problem over a
     Quotient Space of Nuisance-Invariant Functional Manifolds"

Layer A of this package is fully self-contained: it depends only on numpy,
scipy and scikit-learn, and generates its own data from the vendored
simulator, so it requires no download and no dataset licence. It verifies
the mathematical claims of Sections 5 and 7 of the paper. See README.md.
"""

from .calibration import (
    ALPHA,
    TARGET_PERCENTILE,
    MIN_WARMUP_SAMPLES,
    MIN_CALIBRATION_SIZE,
    MAX_CALIBRATION_SIZE,
    CONVERGENCE_LOOKBACK,
    CONVERGENCE_TOLERANCE,
    CONVERGENCE_CONSECUTIVE,
    interpolated_quantile,
    certified_order_statistic,
    AdaptiveOperationalRadius,
    operational_radius_convergence_trace,
    find_convergence_index,
    stopping_rule_floor,
)
from .coverage import (
    k_alpha,
    is_feasible,
    minimum_commissioning_length,
    exact_coverage,
    coverage_band,
    is_degenerate_maximum,
    degenerate_range,
)
from .exchangeability import permutation_exchangeability_test
from .streams import make_distributions, inject_drift
from .operators import PCAResidualOperator
from .saturation import (RadialProjector, radial_distances, empirical_radius,
                         population_radius)
from .dimension import levina_bickel, predicted_dimension
from .dynamics import (nominal_family, degradation_trajectory,
                       first_persistent_departure,
                       false_declaration_probability, recording_score)
from .probes import distance_proxy_probe, passes_distance_proxy

# The Conv1D operator needs TensorFlow and therefore belongs to layer A2; it is
# imported lazily so that A1 remains usable without a deep-learning framework.
__conv_ae_note__ = (
    "import mssp_repro.conv_autoencoder explicitly; it requires TensorFlow")

__all__ = [
    "ALPHA", "TARGET_PERCENTILE",
    "MIN_WARMUP_SAMPLES", "MIN_CALIBRATION_SIZE", "MAX_CALIBRATION_SIZE",
    "CONVERGENCE_LOOKBACK", "CONVERGENCE_TOLERANCE", "CONVERGENCE_CONSECUTIVE",
    "interpolated_quantile", "certified_order_statistic",
    "AdaptiveOperationalRadius", "operational_radius_convergence_trace",
    "find_convergence_index", "stopping_rule_floor",
    "k_alpha", "is_feasible", "minimum_commissioning_length",
    "exact_coverage", "coverage_band",
    "is_degenerate_maximum", "degenerate_range",
    "permutation_exchangeability_test",
    "make_distributions", "inject_drift",
    "PCAResidualOperator",
    "RadialProjector", "radial_distances", "empirical_radius",
    "population_radius",
    "levina_bickel", "predicted_dimension",
    "nominal_family", "degradation_trajectory", "first_persistent_departure",
    "false_declaration_probability", "recording_score",
    "distance_proxy_probe", "passes_distance_proxy",
]
