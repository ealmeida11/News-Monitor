@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cls
echo.
echo   --------------------------------------------------------
echo   Monitor Macro Brasil  v2   (loop continuo, sem espera)
echo   Ctrl+C para parar
echo   --------------------------------------------------------
echo.

:start
if not defined EXECUCOES set EXECUCOES=0
set /a EXECUCOES+=1

set SOURCE_DIR=%~dp0
set PYTHONPATH=%SOURCE_DIR%;%SOURCE_DIR%news_monitor_v2
cd /d "%SOURCE_DIR%"

echo   --- Execucao #%EXECUCOES%  %DATE% %TIME% ---
echo.
python news_monitor_v2/run_coleta.py
echo.

echo   Git
echo   --------------------------------------------------------
git add index.html news_monitor_v2/output/painel_dashboard.html 2>nul
git add -u 2>nul
git status -s
git commit -m "Monitor V2: %DATE% %TIME%" 2>nul
git push origin main 2>nul
echo.

echo   proxima execucao  ^|  https://ealmeida11.github.io/Brasil-News/
echo.
goto :start
