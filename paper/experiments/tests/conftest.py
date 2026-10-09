"""
Shared fixtures. Layer B tests need archives that are not redistributed, so
they locate them once here and skip cleanly when they are absent -- a reader
without the data should see skips, not failures.
"""

import os

import pytest

from mssp_repro.field import find_archive


def _archive(name, env):
    return find_archive(name, explicit=os.environ.get(env))


@pytest.fixture(scope="session")
def ims_root():
    root = _archive("NASA_bearing", "MSSP_IMS_ROOT")
    if root is None:
        pytest.skip("NASA IMS archive not found; set MSSP_IMS_ROOT to enable "
                    "layer B tests")
    return root / "IMS" if (root / "IMS").exists() else root


@pytest.fixture(scope="session")
def cwru_root():
    root = _archive("CWRU_Bearing_NumPy-main", "MSSP_CWRU_ROOT")
    if root is None:
        pytest.skip("CWRU archive not found; set MSSP_CWRU_ROOT to enable "
                    "layer B tests")
    return root
