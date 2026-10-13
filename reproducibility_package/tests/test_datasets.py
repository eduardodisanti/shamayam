"""
The dataset registry: every dataset the experiments read is pinned by a
committed manifest, and the copy on disk is checked against it.
"""

import hashlib
import json

import pytest

import mssp_repro.datasets as ds


def test_every_manifest_matches_its_registry_entry():
    for name, spec in ds.registry()["datasets"].items():
        path = ds.REGISTRY_DIR / spec["manifest"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == spec["manifest_sha256"], name
        assert len(ds.read_manifest(name)) == spec["files"], name


def test_manifest_paths_are_relative_and_unique():
    for name in ds.registry()["datasets"]:
        rels = [rel for _, rel in ds.read_manifest(name)]
        assert len(rels) == len(set(rels)), name
        assert all(not r.startswith(("/", "..")) for r in rels), name


# ------------------------------------------------- behaviour on a toy dataset

@pytest.fixture
def toy(tmp_path, monkeypatch):
    """A one-dataset registry with two files, wired into the module."""
    reg_dir = tmp_path / "registry"
    (reg_dir / "manifests").mkdir(parents=True)
    root = tmp_path / "data"
    (root / "Toy" / "sub").mkdir(parents=True)
    files = {"a.bin": b"alpha", "sub/b.bin": b"beta"}
    for rel, content in files.items():
        (root / "Toy" / rel).write_bytes(content)
    manifest = "".join(f"{hashlib.sha256(c).hexdigest()}  {rel}\n"
                       for rel, c in sorted(files.items()))
    (reg_dir / "manifests" / "Toy.sha256").write_text(manifest)
    spec = {"title": "toy", "manifest": "manifests/Toy.sha256",
            "manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
            "files": 2, "bytes": 9, "loader_subdir": "sub"}
    (reg_dir / "registry.json").write_text(json.dumps(
        {"default_roots": [], "datasets": {"Toy": spec}}))
    monkeypatch.setattr(ds, "REGISTRY_DIR", reg_dir)
    monkeypatch.setenv("MSSP_DATA_ROOT", str(root))
    return root / "Toy"


def test_resolution_follows_the_environment(toy):
    assert ds.dataset_dir("Toy") == toy
    assert ds.loader_root("Toy") == toy / "sub"


def test_a_faithful_copy_verifies(toy):
    (toy / "SOURCE.md").write_text("provenance, ignored")
    (toy / ".DS_Store").write_bytes(b"ignored")
    assert ds.verify("Toy") == []
    assert ds.verify("Toy", deep=True) == []


def test_verify_reports_missing_unexpected_and_changed_files(toy):
    (toy / "a.bin").write_bytes(b"ALPHA")          # same size, new content
    (toy / "extra.bin").write_bytes(b"x")
    (toy / "sub" / "b.bin").unlink()
    problems = ds.verify("Toy", deep=True)
    assert "missing: sub/b.bin" in problems
    assert "unexpected: extra.bin" in problems
    assert "content differs: a.bin" in problems


def test_unknown_dataset_and_missing_root_are_explicit(toy, monkeypatch):
    with pytest.raises(KeyError):
        ds.dataset_dir("Nope")
    monkeypatch.setenv("MSSP_DATA_ROOT", str(toy.parent / "absent"))
    with pytest.raises(FileNotFoundError):
        ds.data_root()
    assert ds.dataset_dir("Toy", required=False) is None


# ------------------------------------------------- the real copies, if present

@pytest.mark.parametrize("name", sorted(ds.registry()["datasets"]))
def test_registered_copy_matches_its_manifest(name):
    if ds.dataset_dir(name, required=False) is None:
        pytest.skip(f"{name} not present under a data root")
    assert ds.verify(name) == []


@pytest.mark.slow
@pytest.mark.parametrize("name", sorted(ds.registry()["datasets"]))
def test_registered_copy_is_byte_identical(name):
    if ds.dataset_dir(name, required=False) is None:
        pytest.skip(f"{name} not present under a data root")
    assert ds.verify(name, deep=True) == []
