@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m phase3.validate_data && .venv\Scripts\python.exe -m unittest discover -s tests -v
pause
