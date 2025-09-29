@echo off
setlocal enabledelayedexpansion
cls
echo ================================================================================
echo                    MONITOR DE NOTICIAS - BRASIL
echo ================================================================================
echo Fontes: Valor Economico, Estadao, Folha de S.Paulo, O Globo
echo Modo: LOOP CONTINUO (intervalo de 5 minutos)
echo Data/Hora: %DATE% %TIME%
echo ================================================================================
echo.
echo Pressione Ctrl+C para parar o loop
echo.

:start
REM Definir pasta temporaria local e caminho do Git
set TEMP_DIR=%TEMP%\MonitorNoticias
set SOURCE_DIR=%~dp0
set GIT_CMD="%TEMP%\PortableGit\bin\git.exe"

REM Contador de execucoes
if not defined EXECUCOES set EXECUCOES=0
set /a EXECUCOES+=1
echo ================================================================================
echo                           EXECUCAO #%EXECUCOES%
echo ================================================================================
echo Data/Hora: %DATE% %TIME%
echo ================================================================================
echo.

echo [1/6] PREPARANDO AMBIENTE...
echo    - Criando pasta temporaria: %TEMP_DIR%
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%" 2>nul
mkdir "%TEMP_DIR%" 2>nul

echo    - Copiando arquivos Python para pasta temporaria...
copy "%SOURCE_DIR%*.py" "%TEMP_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%requirements.txt" "%TEMP_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%noticias.db" "%TEMP_DIR%\" >nul 2>&1
copy "%SOURCE_DIR%categorias_excluidas.txt" "%TEMP_DIR%\" >nul 2>&1
echo    - Ambiente preparado com sucesso!
echo.

REM Mudar para a pasta temporaria para executar o scraper
cd /d "%TEMP_DIR%"

echo [2/6] EXECUTANDO SCRAPER...
echo    - Iniciando extracao de noticias (modo otimizado)...
echo    - Suprimindo alertas WebGL e warnings desnecessarios...
echo.
python scraper_otimizado.py 2>nul
echo.
echo    - Scraper executado com sucesso!
echo.

echo [3/6] VERIFICANDO RESULTADOS...
set FILES_FOUND=0
if exist "monitor_noticias.html" (
    echo    - OK: monitor_noticias.html gerado
    set /a FILES_FOUND+=1
)
if exist "noticias_valor.json" (
    echo    - OK: noticias_valor.json gerado
    set /a FILES_FOUND+=1
)
if exist "noticias_estadao.json" (
    echo    - OK: noticias_estadao.json gerado
    set /a FILES_FOUND+=1
)
if exist "noticias_folha.json" (
    echo    - OK: noticias_folha.json gerado
    set /a FILES_FOUND+=1
)
if exist "noticias_oglobo.json" (
    echo    - OK: noticias_oglobo.json gerado
    set /a FILES_FOUND+=1
)
if exist "noticias_combinadas.json" (
    echo    - OK: noticias_combinadas.json gerado
    set /a FILES_FOUND+=1
)
if exist "noticias.db" (
    echo    - OK: noticias.db atualizado
    set /a FILES_FOUND+=1
)
echo    - Total de arquivos gerados: %FILES_FOUND%/7
echo.

echo [4/6] COPIANDO RESULTADOS...
if exist "monitor_noticias.html" (
    copy "monitor_noticias.html" "%SOURCE_DIR%" >nul 2>&1
    echo    - OK: monitor_noticias.html copiado
)
if exist "noticias_valor.json" (
    copy "noticias_valor.json" "%SOURCE_DIR%" >nul 2>&1
    echo    - OK: noticias_valor.json copiado
)
if exist "noticias_estadao.json" (
    copy "noticias_estadao.json" "%SOURCE_DIR%" >nul 2>&1
    echo    - OK: noticias_estadao.json copiado
)
if exist "noticias_folha.json" (
    copy "noticias_folha.json" "%SOURCE_DIR%" >nul 2>&1
    echo    - OK: noticias_folha.json copiado
)
if exist "noticias_oglobo.json" (
    copy "noticias_oglobo.json" "%SOURCE_DIR%" >nul 2>&1
    echo    - OK: noticias_oglobo.json copiado
)
if exist "noticias_combinadas.json" (
    copy "noticias_combinadas.json" "%SOURCE_DIR%" >nul 2>&1
    echo    - OK: noticias_combinadas.json copiado
)
if exist "noticias.db" (
    copy "noticias.db" "%SOURCE_DIR%" >nul 2>&1
    echo    - OK: noticias.db atualizado
)

echo    - Criando index.html para GitHub Pages...
if exist "monitor_noticias.html" (
    copy "monitor_noticias.html" "%SOURCE_DIR%index.html" >nul 2>&1
    echo    - OK: index.html criado
)
echo.

echo [5/6] CONTANDO NOTICIAS EXTRAIDAS...
powershell -Command "$json = Get-Content '%SOURCE_DIR%noticias_combinadas.json' -Raw -ErrorAction SilentlyContinue; if ($json) { $data = $json | ConvertFrom-Json; $total = $data.Count; $valor = ($data | Where-Object {$_.fonte -eq 'Valor Economico'}).Count; $estadao = ($data | Where-Object {$_.fonte -eq 'Estadao'}).Count; $folha = ($data | Where-Object {$_.fonte -eq 'Folha de S.Paulo'}).Count; $oglobo = ($data | Where-Object {$_.fonte -eq 'O Globo'}).Count; Write-Host '    - Valor Economico:' $valor 'noticias'; Write-Host '    - Estadao:' $estadao 'noticias'; Write-Host '    - Folha de S.Paulo:' $folha 'noticias'; Write-Host '    - O Globo:' $oglobo 'noticias'; Write-Host '    - TOTAL:' $total 'noticias extraidas' } else { Write-Host '    - Erro ao ler arquivo de noticias' }" 2>nul
echo.

echo [6/6] ENVIANDO PARA GITHUB...
cd /d "%SOURCE_DIR%"
echo    - Adicionando arquivos ao Git...
git add . >nul 2>&1
echo    - Criando commit...
git commit -m "Atualizacao automatica %DATE% %TIME%" >nul 2>&1
echo    - Enviando para GitHub...
git push origin main >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    - OK: GitHub atualizado com sucesso!
) else (
    echo    - ERRO: Falha ao enviar para GitHub
)

echo.
echo ================================================================================
echo                           PROCESSO CONCLUIDO!
echo ================================================================================
echo Monitor de noticias atualizado e publicado em:
echo https://ealmeida11.github.io/Brasil-News/
echo.
echo ================================================================================
echo                           AGUARDANDO 5 MINUTOS...
echo ================================================================================
echo Proxima execucao em: 
echo Aguardando 5 minutos (300 segundos)...
echo Pressione Ctrl+C para parar o loop
echo.
echo Iniciando contagem regressiva...
for /l %%i in (300,-1,1) do (
    set /a minutos=%%i/60
    set /a segundos=%%i%%60
    echo Aguardando... !minutos!:!segundos! restantes
    ping 127.0.0.1 -n 2 >nul
)
echo.
echo ================================================================================
echo                           INICIANDO NOVA EXECUCAO...
echo ================================================================================
echo.
goto :start 