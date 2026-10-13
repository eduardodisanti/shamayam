#!/usr/bin/env python3
"""
Fetch, check and describe the datasets in datasets/registry.json.

  python3 datasets_tool.py status              # where each dataset is, quick check
  python3 datasets_tool.py verify --deep       # re-hash every file against its manifest
  python3 datasets_tool.py fetch CWRU_Bearing_NumPy
  python3 datasets_tool.py describe NAME       # write SOURCE.md + MANIFEST.sha256 beside the data

The data root is MSSP_DATA_ROOT, or the first existing default root in the
registry (the author's MyDrive/datasets). A dataset counts as reproducible
only when `verify --deep` passes.
"""

import argparse
import sys
import tarfile
import urllib.request
from pathlib import Path

from mssp_repro.datasets import (REGISTRY_DIR, data_root, read_manifest,
                                 registry, verify)


def cmd_status(names, deep=False):
    root = data_root(required=False)
    print(f"data root: {root if root else '(none found; set MSSP_DATA_ROOT)'}")
    bad = 0
    for name in names:
        d = root / name if root else None
        if d is None or not d.is_dir():
            print(f"  {name:22s} absent")
            bad += 1
            continue
        problems = verify(name, deep=deep, root=root)
        tag = "verified (sha256)" if deep else "files and sizes match"
        print(f"  {name:22s} {tag if not problems else 'MISMATCH'}")
        for p in problems[:10]:
            print(f"      {p}")
        if len(problems) > 10:
            print(f"      ... and {len(problems) - 10} more")
        bad += bool(problems)
    return 1 if bad else 0


def cmd_fetch(name):
    spec = registry()["datasets"][name]
    fetch = spec["fetch"]
    root = data_root(required=True)
    dest = root / name
    if fetch["kind"] == "github_tarball":
        if dest.exists() and any(dest.iterdir()):
            sys.exit(f"{dest} exists and is not empty; refusing to overwrite")
        url = (f"https://codeload.github.com/{fetch['repo']}/tar.gz/"
               f"{fetch['commit']}")
        print(f"streaming {url}\n      -> {dest}")
        dest.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as resp:
            with tarfile.open(fileobj=resp, mode="r|gz") as tar:
                for member in tar:
                    parts = Path(member.name).parts[1:]   # drop "<repo>-<sha>/"
                    if not parts or not member.isfile():
                        continue
                    out = dest.joinpath(*parts)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as src, open(out, "wb") as f:
                        while chunk := src.read(1 << 20):
                            f.write(chunk)
    else:
        print(f"{name} cannot be fetched automatically.\n"
              f"  source: {spec['source']}\n  {fetch['instructions']}\n"
              f"  destination: {dest}")
        return 1
    return cmd_status([name], deep=True)


def cmd_describe(name):
    spec = registry()["datasets"][name]
    dest = data_root(required=True) / name
    (dest / "MANIFEST.sha256").write_text(
        (REGISTRY_DIR / spec["manifest"]).read_text())
    lines = [f"# {name}", "", spec["title"], "",
             f"- Source: {spec['source']}",
             f"- Version: {spec['version']}",
             f"- Original: {spec['original']}",
             f"- License: {spec['license']}",
             f"- Files: {spec['files']} ({spec['bytes'] / 1e6:.0f} MB); "
             f"SHA-256 of every file in MANIFEST.sha256",
             f"- Manifest SHA-256: {spec['manifest_sha256']}", "",
             "Registered in the reproducibility package of the MSSP paper "
             "(github.com/eduardodisanti/shamayam, "
             "reproducibility_package/datasets/registry.json). Check with "
             "`python3 datasets_tool.py verify --deep`. Do not edit files "
             "here: a changed file is a different dataset.", ""]
    (dest / "SOURCE.md").write_text("\n".join(lines))
    print(f"wrote {dest / 'SOURCE.md'} and MANIFEST.sha256 "
          f"({len(read_manifest(name))} files)")
    return 0


def main():
    names = list(registry()["datasets"])
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("names", nargs="*", default=names)
    v = sub.add_parser("verify")
    v.add_argument("names", nargs="*", default=names)
    v.add_argument("--deep", action="store_true")
    f = sub.add_parser("fetch")
    f.add_argument("name", choices=names)
    d = sub.add_parser("describe")
    d.add_argument("name", choices=names)
    a = ap.parse_args()
    if a.cmd == "status":
        return cmd_status(a.names)
    if a.cmd == "verify":
        return cmd_status(a.names, deep=a.deep)
    if a.cmd == "fetch":
        return cmd_fetch(a.name)
    return cmd_describe(a.name)


if __name__ == "__main__":
    sys.exit(main())
