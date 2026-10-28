#!/usr/bin/env bash
set -euo pipefail
# A git hook exports GIT_* vars that would point the tests' own git calls at this repo.
unset $(git rev-parse --local-env-vars)
cd "$(git rev-parse --show-toplevel)"
python3 -m unittest discover -s tests
python3 scripts/check_plugins.py
claude plugin validate .
