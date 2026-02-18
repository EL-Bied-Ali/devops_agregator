@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%PY%" set "PY=python"

cd /d "%ROOT%"
"%PY%" jobs_viewer.py --input data/adzuna_jobs_filtered_strict_enriched.csv --output data/job_viewer.html --market be --ch-focus all --filter-mode strict

endlocal
