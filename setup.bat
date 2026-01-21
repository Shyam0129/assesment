@echo off
REM Automated Setup Script for LinkedIn Scraper
REM Run this script to set up the project automatically

echo ============================================
echo LinkedIn Scraper - Automated Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from python.org
    pause
    exit /b 1
)

echo [1/5] Python detected...
python --version
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
    echo Virtual environment created.
)
echo.

REM Activate virtual environment and install dependencies
echo [3/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo.

REM Setup .env file
echo [4/5] Setting up environment file...
if exist .env (
    echo .env file already exists, skipping...
) else (
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env file with your LinkedIn credentials
    echo File location: %cd%\.env
    notepad .env
)
echo.

REM Final instructions
echo [5/5] Setup complete!
echo.
echo ============================================
echo NEXT STEPS:
echo ============================================
echo 1. Make sure your LinkedIn credentials are saved in .env
echo 2. Run the scraper with:
echo    python scraper.py --profile PROFILE_ID
echo.
echo Example:
echo    python scraper.py --profile williamhgates
echo.
echo For help:
echo    python scraper.py --help
echo.
echo ============================================
pause
