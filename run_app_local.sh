#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"

"${PYTHON_BIN}" -m streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port 9555 \
  -- \
  --app-mode local
