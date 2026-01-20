@echo off
echo Setting up UltraWork AI Detection MVP...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python first.
    pause
    exit /b 1
)

REM Check if pip is installed
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Pip is not installed. Please install pip first.
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

echo Setup complete!
echo.
echo To run the server:
echo 1. Activate virtual environment: venv\Scripts\activate.bat
echo 2. Run the server: python main.py
echo 3. API will be available at: http://localhost:8000
echo 4. API docs at: http://localhost:8000/docs

pause