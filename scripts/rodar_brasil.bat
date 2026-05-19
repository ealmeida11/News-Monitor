@echo off
setlocal
set PYTHONUNBUFFERED=1
echo === rodar_brasil.bat starting ===
cd /d "%~dp0.."
call pipeline\.venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo [warn] venv pipeline\.venv nao encontrado, usando python global
)
python -u -m pipeline.peak.scraper_app
set EXITCODE=%ERRORLEVEL%
echo.
echo === rodar_brasil.bat done (exit=%EXITCODE%^) ===
echo.
pause
endlocal
exit /b %EXITCODE%
