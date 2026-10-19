"""
What must hold after retraining on ANY platform.

Training a network is bit-identical only within one TensorFlow build on CPU
(D15). On another build or device the same seed gives a different operator,
as another seed would, and every number that depends on one trained operator
moves by about what a change of seed moves it. Those numbers are pinned by the
tests marked `reference_exact`, which are expected to fail there.

This file holds the claims that were checked to survive a change of platform
(Metal GPU with TF 2.16-2.19 against CPU with TF 2.21, notes 11 and D15), so
a reader who retrains can run

    pytest -m "not reference_exact"

and get a meaningful pass or fail. The departure of IMS bearing 1 at record
539 under every radius, and the n - k contamination law, are checked in
test_generated_notes.py and belong to this level too.
"""

import hashlib
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
RES = HERE / "results"

# Layer A1 needs no training and no TensorFlow; its section of the results
# file is identical byte for byte between the Metal run and the CPU run.
A1_SHA256 = "24eba1b58f80fc4f758c9478dfca3127a4c514b3db4200b8fa739aa9cbbad617"


def a1_section(text):
    lines = text.splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if "# LAYER A1" in l) - 1
    end = next(i for i, l in enumerate(lines) if "# LAYER A2" in l) - 1
    return "".join(lines[start:end])


def test_layer_a1_is_platform_independent():
    path = RES / "layer_a_results.txt"
    if not path.exists():
        pytest.skip("run run_all.py first")
    digest = hashlib.sha256(a1_section(path.read_text()).encode()).hexdigest()
    assert digest == A1_SHA256


def test_bench_v1_verdicts():
    import bench_report as br
    res = RES / "bench"
    if not (res / "analysis.json").exists():
        pytest.skip("bench results absent")
    T, E, _, _ = br.load(res)
    A = json.loads((res / "analysis.json").read_text())
    h1 = br.h1_verdict((A["all"]["res"], A["all"]["n_ok"]),
                       (A["band"]["res"], A["band"]["n_ok"]))
    assert h1 == "no se detecta transferencia con este método"
    assert br.h2_analysis(E)[1] is True                 # H2: opera


def test_bench_v2_verdicts():
    import bench_report_v2 as br
    res = RES / "bench_v2"
    if not (res / "analysis_v2.json").exists():
        pytest.skip("bench v2 results absent")
    T, E, _ = br.load(res)
    A = json.loads((res / "analysis_v2.json").read_text())
    assert br.verdict(T, A).startswith("no evaluable con este autoencoder")
    assert br.h2(E)[1] is False                         # H2v2: no cumple
