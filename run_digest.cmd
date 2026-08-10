@echo off
rem Daily board digest launcher. Called by the "arcy daily digest" task.
cd /d "%~dp0"
if not exist "%~dp0logs" mkdir "%~dp0logs"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set DT=%%i
"C:\Users\subodh\AppData\Local\Programs\Python\Python312\python.exe" tracker.py --digest >> "%~dp0logs\digest-%DT%.log" 2>&1
