@echo off
REM Ultra Temp Cleaner Pro Launcher
REM -------------------------------

REM Change directory to the script's location
cd /d "%~dp0"

REM Check for admin parameter
if "%1"=="--admin" goto run_as_admin
if "%1"=="-a" goto run_as_admin

REM Check if command line arguments were provided for headless mode
set HEADLESS=0
for %%a in (%*) do (
    if "%%a"=="--headless" set HEADLESS=1
)

REM If headless mode, don't check admin rights
if %HEADLESS%==1 goto start_app

REM Check if admin rights are needed but not present
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Regular user detected, launching in regular mode.
    echo For full functionality, consider running as administrator.
    REM Continue without admin rights
)

:start_app
REM Try to run with python command
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Running with python...
    python run.py %*
    goto end
) else (
    REM Try to run with py command
    py --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo Running with py...
        py run.py %*
        goto end
    ) else (
        REM Try to run with specific Python versions
        py -3 --version >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            echo Running with py -3...
            py -3 run.py %*
            goto end
        ) else (
            echo Python not found. Please install Python 3.6 or higher.
            echo Visit https://www.python.org/downloads/ to download and install Python.
            pause
            exit /b 1
        )
    )
)

:run_as_admin
echo Running with administrator privileges...
powershell -Command "Start-Process -Verb RunAs cmd.exe '/c cd /d \"%~dp0\" && python run.py %*'" 
goto end

:end
if %HEADLESS%==0 pause
