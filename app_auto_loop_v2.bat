@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
cls
echo ================================================================================
echo                    MONITOR MACRO BRASIL V2 - Loop automatico
echo ================================================================================
echo Fontes: Valor, Estadão, Folha, O Globo, CNN Brasil
echo Painel: painel_dashboard.html + index.html (GitHub Pages)
echo Intervalo: 30 minutos
echo Data/Hora: %DATE% %TIME%
echo ================================================================================
echo.
echo Pressione Ctrl+C para parar
echo.

:start
if not defined EXECUCOES set EXECUCOES=0
set /a EXECUCOES+=1
echo ================================================================================
echo                           EXECUCAO #%EXECUCOES%  -  %DATE% %TIME%
echo ================================================================================

set SOURCE_DIR=%~dp0
set PYTHONPATH=%SOURCE_DIR%;%SOURCE_DIR%news_monitor_v2

echo.
echo [1/4] Executando coleta e classificacao (run_coleta.py)...
cd /d "%SOURCE_DIR%"
python news_monitor_v2/run_coleta.py
if %ERRORLEVEL% NEQ 0 (
    echo    AVISO: run_coleta.py retornou codigo %ERRORLEVEL%
) else (
    echo    OK: Coleta e painel atualizados.
)
echo.

echo [2/4] Verificando arquivos...
if exist "%SOURCE_DIR%index.html" (
    echo    OK: index.html atualizado
) else (
    echo    AVISO: index.html nao encontrado
)
if exist "%SOURCE_DIR%news_monitor_v2\noticias_v2.db" (
    echo    OK: noticias_v2.db (local, nao enviado ao GitHub)
)
echo.

echo [3/4] Enviando para GitHub...
git add index.html news_monitor_v2/output/painel_dashboard.html 2>nul
git status -s
git commit -m "Monitor V2: atualizacao automatica %DATE% %TIME%" 2>nul
git push origin main 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    OK: GitHub atualizado
) else (
    echo    AVISO: git push falhou ou nao ha alteracoes
)
echo.

echo [4/4] Proxima execucao em 30 minutos...
echo ================================================================================
echo   Acesso: https://ealmeida11.github.io/Brasil-News/
echo ================================================================================
echo.
for /l %%i in (1800,-10,1) do (
    set /a "min=%%i/60"
    set /a "sec=%%i%%60"
    echo Aguardando !min!m !sec!s...
    ping 127.0.0.1 -n 11 >nul
)
echo.
goto :start
