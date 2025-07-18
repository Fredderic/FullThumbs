@echo off
:: This batch file automates running the full-thumbs.py application.

:: 1. Change the current directory to the location of this batch file.
::    %~dp0 is a special variable that expands to the drive and path of the script.
cd /d "%~dp0"

:: Define the path to the virtual environment's activation script.
set VENV_ACTIVATE_SCRIPT=.venv\Scripts\activate.bat

:: 2. Check if the virtual environment exists and activate it.
if not exist "%VENV_ACTIVATE_SCRIPT%" (
    echo ERROR: Virtual environment not found at %VENV_ACTIVATE_SCRIPT%
    echo Please make sure you have created a venv in the '.venv' folder.
    pause
    exit /b
)

echo Activating the virtual environment...
call "%VENV_ACTIVATE_SCRIPT%"

:: 3. Run the Python application.
echo Starting full-thumbs.py...
python full-thumbs.py

:: 4. Check the exit code from the Python script.
::    %ERRORLEVEL% stores the exit code of the last command.
::    A non-zero exit code usually indicates an error.
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Python script exited with an error code: %ERRORLEVEL%
    echo Press any key to close this window...
    pause
) else (
    echo.
    echo Script finished successfully.
)
