@echo off
setlocal

echo.
echo ^> Starting project setup...
echo.

:: --- 1. Check for Python 3.8+ ---
echo ^>^> Checking for Python 3.8+...
python --version >NUL 2>NUL
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.8 or higher.
    goto :eof
)

python -c "import sys; assert sys.version_info >= (3, 8), 'Python 3.8+ is required. You have ' + sys.version"
if %errorlevel% neq 0 (
    echo [ERROR] Python version check failed. Please ensure you have Python 3.8 or higher.
    goto :eof
)
echo [SUCCESS] Python version check passed.
echo.

:: --- 2. Create Virtual Environment ---
set VENV_DIR=.venv
if exist %VENV_DIR% (
    echo [INFO] Virtual environment '%VENV_DIR%' already exists.
) else (
    echo ^>^> Creating Python virtual environment in '%VENV_DIR%'...
    python -m venv %VENV_DIR%
    echo [SUCCESS] Virtual environment created.
)
echo.

:: --- 3. Install Dependencies ---
echo ^>^> Installing dependencies from requirements.txt...
call %VENV_DIR%\Scripts\pip.exe install --upgrade pip > NUL
call %VENV_DIR%\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    goto :eof
)
echo [SUCCESS] Dependencies installed.
echo.

:: --- 4. Set up DVC ---
set DVC_STORAGE_DIR=..\customer-churn-dvc-storage
echo ^>^> Setting up DVC remote storage...
if not exist %DVC_STORAGE_DIR% mkdir %DVC_STORAGE_DIR%

call %VENV_DIR%\Scripts\dvc.exe remote modify myremote url %DVC_STORAGE_DIR%
echo [SUCCESS] DVC remote 'myremote' configured.
echo.

echo ^>^> Pulling data with DVC...
call %VENV_DIR%\Scripts\dvc.exe pull -q
echo [SUCCESS] Data pulled successfully.
echo.

:: --- 5. Final Instructions ---
echo.
echo ======================================================================
echo  Setup complete!
echo.
echo  To activate the virtual environment, run:
echo     %VENV_DIR%\Scripts\activate
echo.
echo  Then, you can run the pipeline with:
echo     python src/orchestrate.py
echo ======================================================================
echo.

endlocal