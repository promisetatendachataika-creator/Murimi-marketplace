@echo off
REM ============================================================
REM  Murimi Market - open the site to your PHONE as well as this laptop
REM
REM  Use this instead of start-windows.bat when you want to try the site
REM  on your phone. Both devices must be on the SAME network:
REM    - the same Wi-Fi, OR
REM    - the phone plugged in by USB with "USB tethering" switched on
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Run start-windows.bat first, to set everything up.
    pause
    exit /b 1
)

REM --- Find this laptop's addresses on the network -------------------------
set "HOSTS=127.0.0.1,localhost"
set "FOUND="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set "IP=%%a"
    set "IP=!IP: =!"
    if not "!IP!"=="127.0.0.1" (
        set "HOSTS=!HOSTS!,!IP!"
        set "FOUND=!FOUND! !IP!"
    )
)

if "%FOUND%"=="" (
    echo.
    echo This laptop has no network address, so your phone can't reach it.
    echo Connect to Wi-Fi, or plug the phone in and switch on USB tethering.
    echo.
    pause
    exit /b 1
)

set "DJANGO_ALLOWED_HOSTS=%HOSTS%"

echo.
echo ============================================================
echo  On your PHONE, open a browser and type ONE of these:
echo.
for %%i in (%FOUND%) do echo        http://%%i:8000
echo.
echo  On THIS laptop:  http://127.0.0.1:8000
echo.
echo  If Windows asks "Allow Python to communicate on these
echo  networks?", tick PRIVATE networks and allow it. Without
echo  that, your phone will just see a blank page.
echo.
echo  WhatsApp codes still print in THIS window, so keep it open
echo  if you are registering a new account on the phone.
echo.
echo  Ctrl+C to stop.
echo ============================================================
echo.

".venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
