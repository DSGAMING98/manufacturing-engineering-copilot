@echo off
cd /d "%~dp0"
python -m src.train --max-steps 2
if errorlevel 1 (echo SMOKE TRAINING FAILED. & exit /b 1)
echo Smoke training completed. The adapter can be overwritten by full training.
