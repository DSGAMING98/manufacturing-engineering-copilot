@echo off
cd /d "%~dp0"
python -m src.chat --adapter models/qa_qlora/adapter
if errorlevel 1 (echo CHAT FAILED. & exit /b 1)
