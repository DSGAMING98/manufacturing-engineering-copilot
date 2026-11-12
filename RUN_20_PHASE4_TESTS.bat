@echo off
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 exit /b %errorlevel%
.\.venv\Scripts\python.exe -m phase4.benchmark
exit /b %errorlevel%
