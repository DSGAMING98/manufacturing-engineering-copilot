@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m phase6.reproduce
) else (
  python -m phase6.reproduce
)
if errorlevel 1 (echo Phase 6 checks FAILED & exit /b 1)
echo All Phase 6 checks passed.
