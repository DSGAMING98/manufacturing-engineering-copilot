@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo  Manufacturing Copilot - NVIDIA GPU setup for Windows
echo ========================================================
echo.
if /I not "%CONDA_DEFAULT_ENV%"=="mfgcopilot" (
    echo ERROR: Activate the dedicated environment first:
    echo   conda create -n mfgcopilot python=3.12 -y
    echo   conda activate mfgcopilot
    echo Run SETUP_WINDOWS.bat again in Anaconda PowerShell Prompt.
    exit /b 1
)
python -c "import sys; assert sys.version_info[:2] == (3,12), 'Python 3.12 required for this setup'"
if errorlevel 1 exit /b 1
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
echo.
echo Installing GPU PyTorch for CUDA 13.0 runtime (supported by newer NVIDIA drivers).
python -m pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu130
if errorlevel 1 (
    echo ERROR: PyTorch installation failed. Check the official Unsloth Windows guide.
    exit /b 1
)
echo.
echo Installing Unsloth and compatible training libraries.
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo.
python -m src.preflight
if errorlevel 1 exit /b 1
echo.
echo SETUP COMPLETE - now run RUN_01_CHECKS.bat
endlocal
