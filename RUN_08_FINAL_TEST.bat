@echo off
cd /d "%~dp0"
echo FINAL TEST: only run ONCE after you have frozen your model/settings.
echo Running baseline then adapter on held-out synthetic template set.
python -m src.evaluate --split test && python -m src.evaluate --split test --adapter models/qa_qlora/adapter
if errorlevel 1 (echo FINAL TEST FAILED. & exit /b 1)
