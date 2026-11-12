@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m phase6.plot_results
) else (
  python -m phase6.plot_results
)
if errorlevel 1 (echo Figure generation FAILED. Install matplotlib from requirements-phase6.txt & exit /b 1)
echo Publication figures saved under paper_figures\.
