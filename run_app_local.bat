@echo off
setlocal
if "%PYTHON_BIN%"=="" set "PYTHON_BIN=python"
"%PYTHON_BIN%" -m streamlit run app.py --server.address 0.0.0.0 --server.port 9555 -- --app-mode local
