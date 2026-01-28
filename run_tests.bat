@echo off
REM =============================================================================
REM Tour Manager - Test Runner Script
REM =============================================================================
REM This script ensures tests are run with the virtual environment's Python.
REM Usage: run_tests.bat [pytest options]
REM Example: run_tests.bat -v --cov-report=html
REM =============================================================================

echo ============================================
echo    Tour Manager - Test Suite Runner
echo ============================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then install requirements: venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

REM Activate venv and run tests
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Running pytest with coverage...
echo.

REM Run pytest with any additional arguments passed to the script
python -m pytest tests/ %*

REM Capture exit code
set EXITCODE=%ERRORLEVEL%

echo.
echo ============================================
if %EXITCODE% EQU 0 (
    echo    All tests PASSED!
) else (
    echo    Some tests FAILED - exit code: %EXITCODE%
)
echo ============================================

exit /b %EXITCODE%
