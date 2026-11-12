@echo off
cd /d "%~dp0"
echo CAUTION: Only run this ONCE after model selection from validation.
.venv\Scripts\python.exe -m phase3.evaluate_model --split test --adapter models/qa_qlora_v2/adapter --tag v2 --confirm-final-test
pause
