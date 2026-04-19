#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-/home/pier/miniconda3/envs/py39_cuda12.4/bin/python}"

"${PYTHON_BIN}" -m streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port 9555
