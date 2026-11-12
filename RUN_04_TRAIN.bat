@echo off
cd /d "%~dp0"
python -m src.train
if errorlevel 1 (echo TRAINING FAILED. & exit /b 1)
echo Adapter saved to models\qa_qlora\adapter\
