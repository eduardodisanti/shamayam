"""
Layer B: the field archives.

Separated from the rest of `mssp_repro` because everything here needs data
that is not redistributed with the package. Importing this subpackage is
cheap and safe; calling into it requires the archives, and the loaders say so
plainly when they are absent.
"""

from .paths import resolve_ci, find_archive
from .ims import (IMS_CHANNELS, IMS_SAMPLE_RATE_HZ,
                  IMS_RECORDING_INTERVAL_HOURS, parse_ims_timestamp,
                  load_experiment, load_bearing, make_windows)
from .residuals import (IMS_EXPERIMENT, compute_ims_residuals, save_cache,
                        load_cache, compare_to_cache)
from .cwru import (CWRU_SPEEDS, CWRU_REGIMES, CWRU_SAMPLE_RATE_HZ,
                   load_signal, load_asset_windows)

__all__ = ["resolve_ci", "find_archive", "IMS_CHANNELS",
           "IMS_SAMPLE_RATE_HZ", "IMS_RECORDING_INTERVAL_HOURS",
           "parse_ims_timestamp", "load_experiment", "load_bearing",
           "make_windows", "CWRU_SPEEDS", "CWRU_REGIMES",
           "CWRU_SAMPLE_RATE_HZ", "load_signal", "load_asset_windows",
           "IMS_EXPERIMENT", "compute_ims_residuals", "save_cache",
           "load_cache", "compare_to_cache"]
