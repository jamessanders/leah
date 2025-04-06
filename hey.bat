@echo off

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Check if at least two arguments were provided (persona and message)
if "%~2"=="" (
    echo Usage: hey persona your message here
    exit /b 1
)

REM Get the persona from first argument
set PERSONA=%~1

REM Shift arguments to remove persona, leaving only the message
shift

REM Pass all remaining arguments to leah.py using absolute path
python "%SCRIPT_DIR%src\leah.py" --persona %PERSONA% %* 