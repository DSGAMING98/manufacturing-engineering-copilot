@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo ERROR: Project .venv not found. Run from the manufacturing-copilot repository root.
 exit /b 1
)
".venv\Scripts\python.exe" -m src.hybrid_chat --adapter models/qa_qlora/adapter
if errorlevel 1 (echo HYBRID CHAT FAILED. & exit /b 1)
