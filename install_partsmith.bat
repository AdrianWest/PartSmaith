@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo PartSmith's producer environment is missing. Use Python 3.11 or 3.12.
    echo Prepare the repository .venv before running this installer.
    set "PARTSMITH_INSTALL_RESULT=1"
    goto finish
)
".venv\Scripts\python.exe" "scripts\install_kicad.py" %*
set "PARTSMITH_INSTALL_RESULT=%ERRORLEVEL%"
:finish
popd
if /I not "%~1"=="--no-pause" pause
exit /b %PARTSMITH_INSTALL_RESULT%
