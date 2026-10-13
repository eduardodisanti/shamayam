"""
Where the datasets live, and proof that they are the ones the paper used.

Every dataset the experiments read is listed in `datasets/registry.json` and
lives in its own folder under one data root:

    <data root>/
        CWRU_Bearing_NumPy/     Data/<speed> RPM/*.npz, ...
        NASA_IMS_Bearings/      2nd_test/<984 recordings>
        ...

The data root is `MSSP_DATA_ROOT` when set; otherwise the first of the
registry's `default_roots` that exists (the author's Google Drive folder
`MyDrive/datasets`, then `~/datasets`).

Each dataset has a committed manifest with the SHA-256 of every file, so
"the same data" is a checkable statement rather than a hope: `verify(name)`
compares names and sizes, `verify(name, deep=True)` re-hashes every file.
"""

import glob
import hashlib
import json
import os
from pathlib import Path

__all__ = ["REGISTRY_DIR", "registry", "data_root", "dataset_dir",
           "loader_root", "dataset_arg", "read_manifest", "verify", "provenance"]

REGISTRY_DIR = Path(__file__).resolve().parents[1] / "datasets"
_ENV = "MSSP_DATA_ROOT"


def registry():
    return json.loads((REGISTRY_DIR / "registry.json").read_text())


def _spec(name):
    reg = registry()["datasets"]
    if name not in reg:
        raise KeyError(f"unknown dataset {name!r}; registered: "
                       f"{', '.join(sorted(reg))}")
    return reg[name]


def data_root(*, required=True):
    """The folder holding one subfolder per dataset."""
    env = os.environ.get(_ENV)
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p
        if required:
            raise FileNotFoundError(f"{_ENV}={env} is not a directory")
        return None
    for pattern in registry()["default_roots"]:
        for hit in sorted(glob.glob(os.path.expanduser(pattern))):
            if Path(hit).is_dir():
                return Path(hit)
    if required:
        raise FileNotFoundError(
            "no data root found. Set MSSP_DATA_ROOT to the folder that holds "
            "the dataset folders (see datasets/registry.json), or pass the "
            "path explicitly.")
    return None


def dataset_dir(name, *, required=True):
    """`<data root>/<name>`, checked to exist."""
    _spec(name)
    root = data_root(required=required)
    if root is None:
        return None
    d = root / name
    if not d.is_dir():
        if required:
            raise FileNotFoundError(
                f"{name} not found under {root}. Fetch it with "
                f"`python3 datasets_tool.py fetch {name}`.")
        return None
    return d


def loader_root(name, *, required=True):
    """The path the loaders in `mssp_repro.field` expect for this dataset."""
    d = dataset_dir(name, required=required)
    if d is None:
        return None
    sub = _spec(name).get("loader_subdir") or ""
    return d / sub if sub else d


def read_manifest(name):
    """[(sha256, relative path)] in manifest order."""
    text = (REGISTRY_DIR / _spec(name)["manifest"]).read_text()
    rows = []
    for line in text.splitlines():
        if line.strip():
            digest, rel = line.split("  ", 1)
            rows.append((digest, rel))
    return rows


def _sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def verify(name, *, deep=False, root=None):
    """
    Problems found, as a list of strings; empty means the dataset matches.

    Always checks that the committed manifest is the one the registry names,
    and that the folder holds exactly the manifest's files (hidden files and
    the SOURCE.md / MANIFEST.sha256 written beside the data are ignored).
    `deep=True` also re-hashes every file.
    """
    spec = _spec(name)
    problems = []
    mpath = REGISTRY_DIR / spec["manifest"]
    if _sha256(mpath) != spec["manifest_sha256"]:
        problems.append(f"manifest {mpath.name} does not match the registry")
    d = Path(root) / name if root is not None else dataset_dir(name)
    expected = read_manifest(name)
    want = {rel for _, rel in expected}
    have = {str(p.relative_to(d)) for p in d.rglob("*")
            if p.is_file() and not any(part.startswith(".")
                                       for part in p.relative_to(d).parts)}
    have -= {"SOURCE.md", "MANIFEST.sha256"}
    for rel in sorted(want - have):
        problems.append(f"missing: {rel}")
    for rel in sorted(have - want):
        problems.append(f"unexpected: {rel}")
    if deep:
        for digest, rel in expected:
            p = d / rel
            if p.is_file() and _sha256(p) != digest:
                problems.append(f"content differs: {rel}")
    elif "bytes" in spec and not problems:
        total = sum((d / rel).stat().st_size for _, rel in expected)
        if total != spec["bytes"]:
            problems.append(f"total size {total} != registry {spec['bytes']}")
    return problems


def dataset_arg(name):
    """
    argparse keyword arguments for a `--<dataset>-root` option: defaults to
    the registered location when it exists, required otherwise.
    """
    found = loader_root(name, required=False)
    if found is not None:
        return {"type": Path, "default": found,
                "help": f"default: {found} (registered dataset {name})"}
    return {"type": Path, "required": True,
            "help": f"{name} not found under a data root; set MSSP_DATA_ROOT "
                    f"or pass the path"}


def provenance(name):
    """What to record beside a result: which dataset, pinned how."""
    spec = _spec(name)
    return {"dataset": name, "version": spec.get("version"),
            "manifest_sha256": spec["manifest_sha256"]}
