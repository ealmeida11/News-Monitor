@echo off
echo Monitor de Noticias - Valor Economico, Estadao, Folha e O Globo
echo Atualizando Github a cada minuto enquanto o servidor web roda
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

REM Executando o scraper para gerar arquivos atualizados inicialmente
echo Executando scraper para gerar arquivos atualizados...
python scraper.py

REM Copiando resultados de volta
echo Copiando resultados de volta...
if exist "monitor_noticias.html" copy "monitor_noticias.html" "%SOURCE_DIR%" > nul
if exist "noticias_valor.json" copy "noticias_valor.json" "%SOURCE_DIR%" > nul
if exist "noticias_estadao.json" copy "noticias_estadao.json" "%SOURCE_DIR%" > nul
if exist "noticias_folha.json" copy "noticias_folha.json" "%SOURCE_DIR%" > nul
if exist "noticias_oglobo.json" copy "noticias_oglobo.json" "%SOURCE_DIR%" > nul
if exist "noticias_combinadas.json" copy "noticias_combinadas.json" "%SOURCE_DIR%" > nul

REM Voltar para a pasta original
cd /d "%SOURCE_DIR%"

REM Renomeando o arquivo para index.html
echo Copiando monitor_noticias.html para index.html...
copy /Y monitor_noticias.html index.html

REM Primeiro push para o GitHub
echo Enviando versao inicial para o GitHub...
git add index.html noticias_valor.json noticias_estadao.json noticias_folha.json noticias_oglobo.json noticias_combinadas.json
git commit -m "Atualizacao automatica inicial %DATE%_%TIME%"
git push origin main

REM Iniciando o servidor web em segundo plano
echo Iniciando servidor web em segundo plano...
start /b "Monitor de Noticias - Servidor Web" python app.py -w -a

REM Loop principal para atualizar o GitHub
echo Iniciando loop de atualizacao do GitHub. Pressione Ctrl+C para encerrar.
echo.

:loop
REM Esperando 60 segundos
timeout /t 60 /nobreak > nul

REM Mudar para a pasta temporária
cd /d "%TEMP_DIR%"

REM Executando o scraper para atualizar os arquivos
echo [%TIME%] Atualizando arquivos...
python scraper.py

REM Copiando resultados de volta
if exist "monitor_noticias.html" copy "monitor_noticias.html" "%SOURCE_DIR%" > nul
if exist "noticias_valor.json" copy "noticias_valor.json" "%SOURCE_DIR%" > nul
if exist "noticias_estadao.json" copy "noticias_estadao.json" "%SOURCE_DIR%" > nul
if exist "noticias_folha.json" copy "noticias_folha.json" "%SOURCE_DIR%" > nul
if exist "noticias_oglobo.json" copy "noticias_oglobo.json" "%SOURCE_DIR%" > nul
if exist "noticias_combinadas.json" copy "noticias_combinadas.json" "%SOURCE_DIR%" > nul

REM Voltar para a pasta original
cd /d "%SOURCE_DIR%"

REM Renomeando o arquivo para index.html
copy /Y monitor_noticias.html index.html > nul

REM Adiciona os arquivos específicos para o commit
echo [%TIME%] Enviando para o GitHub...
git add index.html noticias_valor.json noticias_estadao.json noticias_folha.json noticias_oglobo.json noticias_combinadas.json > nul

REM Se houver mudanças, cria um commit
git diff --quiet HEAD
if %ERRORLEVEL% neq 0 (
    git commit -m "Atualizacao automatica %DATE%_%TIME%" > nul
    git push origin main > nul
    echo [%TIME%] GitHub atualizado com sucesso!
) else (
    echo [%TIME%] Nenhuma mudanca desde a ultima atualizacao.
)

REM Continuar o loop
goto loop 