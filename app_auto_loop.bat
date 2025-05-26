@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Monitor de Noticias - Loop Automatico
echo ========================================

:loop
echo.
echo [%date% %time%] Iniciando nova execucao...

REM Copiar arquivos Python para diretorio temporario
set TEMP_DIR=%TEMP%\MonitorNoticias
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

copy /Y "scraper.py" "%TEMP_DIR%\" >nul
copy /Y "app.py" "%TEMP_DIR%\" >nul
copy /Y "main.py" "%TEMP_DIR%\" >nul

REM Executar scraper no diretorio temporario (modo rapido otimizado)
cd /d "%TEMP_DIR%"
python scraper.py

REM Copiar resultados de volta para o diretorio original
copy /Y "*.json" "\\jgprjfileserver\Research\Economics\Ealmeida\Brasil\News\" >nul
copy /Y "*.html" "\\jgprjfileserver\Research\Economics\Ealmeida\Brasil\News\" >nul

REM Usar PowerShell para comandos Git (suporta UNC paths)
powershell -Command "cd '\\jgprjfileserver\Research\Economics\Ealmeida\Brasil\News'; if (git status --porcelain) { $timestamp = Get-Date -Format 'ddd MM/dd/yyyy_HH:mm:ss.ff'; git add .; git commit -m \"Atualizacao automatica $timestamp\"; git push; Write-Host 'Commit realizado com sucesso!' } else { Write-Host 'Nenhuma alteracao detectada.' }"

REM Iniciar servidor web em background se nao estiver rodando
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq Monitor*" 2>nul | find /I "python.exe" >nul
if errorlevel 1 (
    echo Iniciando servidor web...
    start "Monitor Web Server" python app.py
) else (
    echo Servidor web ja esta rodando.
)

echo [%date% %time%] Execucao concluida. Aguardando 60 segundos...
timeout /t 60 /nobreak >nul

goto loop 