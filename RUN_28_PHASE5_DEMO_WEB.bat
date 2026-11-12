@echo off
cd /d "%~dp0"
echo WARNING: fictional demo excerpts are enabled for this research demo only.
.venv\Scripts\python.exe -m phase5.web_app --include-demo
pause
