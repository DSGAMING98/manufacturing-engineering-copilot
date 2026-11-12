@echo off
cd /d "%~dp0"
python -m src.data_validation && python -m unittest discover -s tests -v && python -m src.preflight
if errorlevel 1 (echo CHECKS FAILED. See output above. & exit /b 1)
echo PASS: Dataset, CPU tests, and CUDA available.
