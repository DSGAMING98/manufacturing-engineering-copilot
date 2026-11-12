@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe -m phase3.evaluate_model --split validation --adapter models/qa_qlora_v2/adapter --tag v2
pause
