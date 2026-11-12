@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m phase3.compare --split validation
pause
