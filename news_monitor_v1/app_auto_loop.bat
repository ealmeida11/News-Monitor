@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
REM Monitor V1 - SOURCE_DIR = esta pasta (v1); REPO_ROOT = raiz do repo (News) para index.html e Git
set SOURCE_DIR=%~dp0
set REPO_ROOT=%~dp0..
cls
echo ================================================================================
echo                    MONITOR DE NOTICIAS V1 - BRASIL (legado)
echo ================================================================================
echo Fontes: Valor, Estadao, Folha, O Globo
echo Pasta: %SOURCE_DIR%
echo Index para GitHub: %REPO_ROOT%\index.html
echo ================================================================================
echo Pressione Ctrl+C para parar
echo.

:start
set TEMP_DIR=%TEMP%\MonitorNoticiasV1
if not defined EXECUCOES set EXECUCOES=0
set /a EXECUCOES+=1
echo ================================================================================
echo                           EXECUCAO #%EXECUCOES%  -  %DATE% %TIME%
echo ================================================================================

echo [1/6] Preparando ambiente...
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%" 2>nul
mkdir "%TEMP_DIR%" 2>nul
copy "%SOURCE_DIR%*.py" "%TEMP_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%requirements.txt" "%TEMP_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%categorias_excluidas.txt" "%TEMP_DIR%\" >nul 2>&1

echo [2/6] Executando scraper...
set DB_PATH=%SOURCE_DIR%noticias.db
cd /d "%TEMP_DIR%"
python scraper_otimizado.py 2>nul
cd /d "%SOURCE_DIR%"

echo [3/6] Copiando resultados para V1...
if exist "%TEMP_DIR%\monitor_noticias.html" copy "%TEMP_DIR%\monitor_noticias.html" "%SOURCE_DIR%" >nul 2>&1
if exist "%TEMP_DIR%\noticias_valor.json" copy "%TEMP_DIR%\noticias_valor.json" "%SOURCE_DIR%" >nul 2>&1
if exist "%TEMP_DIR%\noticias_estadao.json" copy "%TEMP_DIR%\noticias_estadao.json" "%SOURCE_DIR%" >nul 2>&1
if exist "%TEMP_DIR%\noticias_folha.json" copy "%TEMP_DIR%\noticias_folha.json" "%SOURCE_DIR%" >nul 2>&1
if exist "%TEMP_DIR%\noticias_oglobo.json" copy "%TEMP_DIR%\noticias_oglobo.json" "%SOURCE_DIR%" >nul 2>&1
if exist "%TEMP_DIR%\noticias_combinadas.json" copy "%TEMP_DIR%\noticias_combinadas.json" "%SOURCE_DIR%" >nul 2>&1

echo [4/6] Copiando index.html para raiz do repo (GitHub Pages)...
if exist "%SOURCE_DIR%monitor_noticias.html" (
    copy /y "%SOURCE_DIR%monitor_noticias.html" "%REPO_ROOT%\index.html" >nul 2>&1
    echo    OK: index.html atualizado em %REPO_ROOT%
)

echo [5/6] Enviando para GitHub...
cd /d "%REPO_ROOT%"
git add index.html news_monitor_v1\ 2>nul
git commit -m "Monitor V1: atualizacao %DATE% %TIME%" 2>nul
git push origin main 2>nul
if %ERRORLEVEL% EQU 0 (echo    OK: GitHub atualizado) else (echo    Aviso: git push falhou ou sem alteracoes)

echo [6/6] Aguardando 5 minutos...
echo Acesso: https://ealmeida11.github.io/Brasil-News/
for /l %%i in (300,-1,1) do (
    set /a "min=%%i/60"
    set /a "sec=%%i%%60"
    echo Aguardando !min!:!sec!...
    ping 127.0.0.1 -n 2 >nul
)
goto :start
