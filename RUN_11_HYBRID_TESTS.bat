@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo ERROR: Project .venv not found.
 exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 (echo TESTS FAILED. & exit /b 1)
