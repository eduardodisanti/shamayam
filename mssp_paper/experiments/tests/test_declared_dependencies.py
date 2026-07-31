"""
Every third-party import is declared.

This test exists because of a specific failure: `make_figures.py` was added
last, imported matplotlib, and `requirements.txt` was never updated. Following
the README exactly therefore produced a `ModuleNotFoundError` at the final
step, after the experiments had already run -- the worst place for it, because
it reads as though the reproduction failed when in fact only the redrawing was
blocked.

The instance was one line to fix. The class is not, and a reproducibility
package that cannot be installed from its own instructions is not
reproducible. So the check is mechanical: parse the imports, compare against
what is declared, and fail on anything unaccounted for.
"""

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"

# Import name -> distribution name, where they differ.
ALIASES = {"sklearn": "scikit-learn", "PIL": "pillow", "cv2": "opencv-python",
           "yaml": "pyyaml"}

# Declared in requirements.txt as commented-out optional layers, and guarded
# at every use site. TensorFlow is layer A2, which run_all.py skips when it is
# absent; pytest is the runner and need not be importable by the package.
OPTIONAL = {"tensorflow", "keras"}

# The package's own modules, which are not third-party.
LOCAL = {"mssp_repro", "run_all", "make_figures", "make_tables", "make_macros",
         "conftest"}


def _declared():
    if not REQUIREMENTS.exists():
        pytest.skip(f"{REQUIREMENTS} absent")
    names = set()
    for line in REQUIREMENTS.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        # Strip any version specifier, extras and environment marker.
        names.add(re.split(r"[<>=!~\[;]", line, 1)[0].strip().lower())
    return names


def _sources():
    files = sorted(ROOT.glob("*.py"))
    files += sorted((ROOT / "mssp_repro").glob("*.py"))
    files += sorted((ROOT / "tests").glob("*.py"))
    return files


def _imports(path):
    """Top-level module name of every import in a file, with the line number."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                yield node.module.split(".")[0], node.lineno


def test_every_third_party_import_is_declared():
    declared, undeclared = _declared(), []
    stdlib = getattr(sys, "stdlib_module_names", frozenset())
    if not stdlib:
        pytest.skip("sys.stdlib_module_names requires Python 3.10+")

    for path in _sources():
        for name, lineno in _imports(path):
            if name in stdlib or name in LOCAL or name in OPTIONAL:
                continue
            if ALIASES.get(name, name).lower() in declared:
                continue
            undeclared.append(
                f"{path.relative_to(ROOT)}:{lineno} imports {name!r}")

    assert not undeclared, (
        "imported but not in requirements.txt, so a clean environment "
        "following README.md will fail:\n  " + "\n  ".join(sorted(undeclared)))


def test_optional_dependencies_are_guarded():
    """
    An optional dependency must not be imported at module scope outside a
    guard, or `--layer a1` stops working on a machine without TensorFlow --
    which is the entire point of splitting the layers.
    """
    unguarded = []
    for path in _sources():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in tree.body:                       # module scope only
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            names = ([a.name.split(".")[0] for a in node.names]
                     if isinstance(node, ast.Import)
                     else [(node.module or "").split(".")[0]])
            for name in names:
                if name in OPTIONAL:
                    unguarded.append(
                        f"{path.relative_to(ROOT)}:{node.lineno} imports "
                        f"{name!r} at module scope")
    assert not unguarded, (
        "optional dependencies imported unconditionally at module scope:\n  "
        + "\n  ".join(sorted(unguarded)))
