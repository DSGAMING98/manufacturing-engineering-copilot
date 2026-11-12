@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m phase3.train_v2 --smoke
pause
