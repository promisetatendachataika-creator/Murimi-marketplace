@echo off
REM ============================================================
REM  Murimi Marketplace - start the server on this laptop
REM  Double-click this file, or run .\start-windows.bat in PowerShell
REM  from C:\murimi-market
REM ============================================================
setlocal
cd /d "%~dp0"

REM 1. Find Python (python, or the Windows "py" launcher)
set "PY=python"
where python >nul 2>nul || set "PY=py -3"

REM 2. Make the private Python box (.venv) if it is missing or broken
if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Creating .venv ...
    if exist ".venv" rmdir /s /q ".venv"
    %PY% -m venv .venv || goto :fail
) else (
    echo [1/5] .venv found
)

REM 3. Install the packages listed in requirements.txt
echo [2/5] Checking packages ...
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto :fail

REM 4. Make a .env with a fresh secret key the first time only
if not exist ".env" (
    echo [3/5] Creating .env with a new secret key ...
    copy /y ".env.example" ".env" >nul
    ".venv\Scripts\python.exe" -c "from django.core.management.utils import get_random_secret_key as k; open('.env','a',encoding='utf-8').write('DJANGO_SECRET_KEY='+k()+'\n')" || goto :fail
) else (
    echo [3/5] .env found
)

REM 5. Bring the database tables up to date
echo [4/5] Applying migrations ...
".venv\Scripts\python.exe" manage.py migrate || goto :fail

REM 6. Start the server
echo [5/5] Starting server at http://127.0.0.1:8000  (Ctrl+C to stop)
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
goto :eof

:fail
echo.
echo Something went wrong above. Read the last red lines, then ask Claude.
pause
exit /b 1
