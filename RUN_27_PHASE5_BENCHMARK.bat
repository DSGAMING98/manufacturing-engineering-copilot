@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m phase5.benchmark --output results\phase5_benchmark.json
pause
