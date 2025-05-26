@echo off
echo Monitor de Noticias - Executando localmente para evitar problemas com UNC paths
echo.

REM Definir pasta temporária local
set TEMP_DIR=%TEMP%\MonitorNoticias
set SOURCE_DIR=%~dp0

echo Criando pasta temporaria: %TEMP_DIR%
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

echo Copiando arquivos para pasta temporaria...
copy "%SOURCE_DIR%*.py" "%TEMP_DIR%\" > nul
copy "%SOURCE_DIR%requirements.txt" "%TEMP_DIR%\" > nul

REM Mudar para a pasta temporária
cd /d "%TEMP_DIR%"

echo Executando scraper na pasta temporaria...
python app.py

echo.
echo Copiando resultados de volta...
if exist "monitor_noticias.html" copy "monitor_noticias.html" "%SOURCE_DIR%" > nul
if exist "noticias_valor.json" copy "noticias_valor.json" "%SOURCE_DIR%" > nul
if exist "noticias_estadao.json" copy "noticias_estadao.json" "%SOURCE_DIR%" > nul
if exist "noticias_folha.json" copy "noticias_folha.json" "%SOURCE_DIR%" > nul
if exist "noticias_oglobo.json" copy "noticias_oglobo.json" "%SOURCE_DIR%" > nul
if exist "noticias_combinadas.json" copy "noticias_combinadas.json" "%SOURCE_DIR%" > nul

echo.
echo Limpando pasta temporaria...
cd /d "%SOURCE_DIR%"
rmdir /s /q "%TEMP_DIR%"

echo.
echo Processo concluido! Arquivos salvos na pasta original.
pause 