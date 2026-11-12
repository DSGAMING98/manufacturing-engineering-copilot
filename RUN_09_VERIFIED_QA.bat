@echo off
.venv\Scripts\python.exe -m src.verified_qa --nominal 20.00 --measured 20.03 --tolerance 0.05
pause
