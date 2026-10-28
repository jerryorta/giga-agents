#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
python3 -m unittest discover -s tests
python3 scripts/check_plugins.py
claude plugin validate .
