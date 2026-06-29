@echo off
cd /d %~dp0
echo Starting Vocal Separator...
echo.
echo Keep this window open while using the app.
echo Closing this window will stop http://127.0.0.1:7860/
echo.
start "" cmd /c "timeout /t 2 >nul & start "" http://127.0.0.1:7860/"
python app.py
echo.
echo Server stopped. Press any key to close this window.
pause > nul
