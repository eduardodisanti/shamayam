#!/usr/bin/env bash
# Superseded by datasets_tool.py, which fetches the pinned versions listed in
# datasets/registry.json and verifies every file against its manifest.
set -e
cd "$(dirname "$0")"
python3 datasets_tool.py fetch CWRU_Bearing_NumPy || true
python3 datasets_tool.py fetch NASA_IMS_Bearings || true
python3 datasets_tool.py verify --deep
