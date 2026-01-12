@echo off
REM start.bat — stop any running app and start the latest WanderTogether app with hybrid algorithm

echo === WanderTogether App Startup (Hybrid Algorithm) ===
echo Stopping any process listening on port 5001...

REM Kill processes on port 5001
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001 2^>nul') do (
    echo Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill old PID if exists
if exist .app.pid (
    set /p OLD_PID=<.app.pid
    tasklist /FI "PID eq %OLD_PID%" 2>nul | find /i "%OLD_PID%" >nul
    if %errorlevel% equ 0 (
        echo Killing old PID %OLD_PID%
        taskkill /F /PID %OLD_PID% >nul 2>&1
    )
    del .app.pid
)

REM Kill any Python processes running app.py
echo Stopping any Python processes running app.py...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" ^| findstr app.py') do (
    echo Stopping Python process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 1 >nul

echo Starting WanderTogether app with Safety-Enhanced Empirical Hybrid algorithm...
echo Features: Top 8 recommendations, compatibility & trust scores
echo Web interface will be available at: http://127.0.0.1:5001

REM Start app in background and redirect output to logfile
start /B python app.py > app.log 2>&1

echo App started in background
echo Logs: app.log

echo Waiting 2 seconds for server to initialize...
timeout /t 2 >nul

set MAX_WAIT=15
set WAITED=0

echo Checking server health...
:check_server
curl -s "http://127.0.0.1:5001/status" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ✅ Server is responding at http://127.0.0.1:5001/
    echo ✅ Hybrid algorithm is ready for recommendations
    echo ✅ Top 8 recommendations with compatibility & trust scores available
    
    REM Open browser
    start http://127.0.0.1:5001/
    
    echo.
    echo 🚀 WanderTogether is ready!
    echo 📊 Using Safety-Enhanced Empirical Hybrid algorithm
    echo 🎯 Provides top 8 recommendations with detailed scores
    echo 🔒 Trust gate: ≥0.7 for safety
    echo.
    goto :success
)

if %WAITED% geq %MAX_WAIT% (
    echo.
    echo ❌ Server did not respond within %MAX_WAIT% seconds.
    echo 📋 Check app.log for errors:
    echo    type app.log
    echo.
    echo 🔧 Troubleshooting:
    echo    - Check if port 5001 is available: netstat -an ^| findstr 5001
    echo    - Check Python dependencies: pip install flask pandas psycopg2
    echo    - Verify app.py syntax: python -m py_compile app.py
    echo    - Check if Python is installed: python --version
    goto :end
)

echo Waiting for server... (%WAITED%/%MAX_WAIT%)
timeout /t 1 >nul
set /a WAITED+=1
goto :check_server

:success
echo Press any key to exit...
pause >nul
goto :end

:end
echo WanderTogether startup script completed.
