@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m phase3.evaluate_model --split validation --tag base
pause
