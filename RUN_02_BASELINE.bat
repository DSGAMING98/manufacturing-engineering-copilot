@echo off
cd /d "%~dp0"
python -m src.evaluate --split validation
if errorlevel 1 (echo BASELINE FAILED. & exit /b 1)
echo Baseline results saved in results\
