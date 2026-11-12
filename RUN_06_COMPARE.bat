@echo off
cd /d "%~dp0"
python -m src.compare
if errorlevel 1 (echo COMPARISON FAILED. & exit /b 1)
