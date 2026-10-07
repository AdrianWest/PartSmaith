@echo off
setlocal
pushd "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "scripts\install_production.ps1" %*
set "PARTSMITH_INSTALL_RESULT=%ERRORLEVEL%"
popd
pause
exit /b %PARTSMITH_INSTALL_RESULT%
