@echo off
REM Reaction Markdown Generator - Windows Batch Script
REM This script provides an easy way to run the Reaction Markdown Generator

echo =============================================
echo    Reaction Markdown Generator
echo =============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check command line arguments
if "%~1"=="" goto GUI_MODE
if "%~2"=="" goto GUI_MODE

:CLI_MODE
echo Running in command-line mode...
echo Input folder: %~1
echo Output file: %~2
echo.
python reaction_markdown_generator.py --folder "%~1" --output "%~2"
goto END

:GUI_MODE
echo Launching GUI interface...
echo.
python reaction_markdown_generator.py --gui

:END
echo.
echo Done!
pause
