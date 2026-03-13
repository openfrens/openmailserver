#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install -e ".[dev]"
openmailserver install
openmailserver doctor
