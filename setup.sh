#!/bin/bash
set -e
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3.12}"
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
