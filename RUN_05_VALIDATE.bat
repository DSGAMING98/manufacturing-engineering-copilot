@echo off
cd /d "%~dp0"
python -m src.evaluate --split validation --adapter models/qa_qlora/adapter
if errorlevel 1 (echo ADAPTER VALIDATION FAILED. & exit /b 1)
echo Fine-tuned validation metrics saved in results\
