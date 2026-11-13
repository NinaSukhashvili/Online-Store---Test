@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo             WIGNIERI - START
echo ============================================
where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py
) else (
    set PYTHON=python
)
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto error
)
call ".venv\Scripts\activate.bat"
echo Installing project requirements...
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -r requirements.txt
if errorlevel 1 goto error
echo Applying database migrations...
python manage.py migrate
if errorlevel 1 goto error
echo Starting local website...
echo Open http://127.0.0.1:8000/ in your browser.
python manage.py runserver
 goto end
:error
echo.
echo Startup failed. Check that Python is installed and internet is available for package installation.
pause
:end
endlocal
