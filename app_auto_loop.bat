@echo off
echo Monitor de Noticias - Valor Economico e Estadao
echo Atualizando Github a cada minuto enquanto o servidor web roda
echo.

REM Executando o scraper para gerar arquivos atualizados inicialmente
echo Executando scraper para gerar arquivos atualizados...
C:\Users\erica\AppData\Local\Programs\Python\Launcher\py.exe scraper.py

REM Renomeando o arquivo para index.html
echo Copiando monitor_noticias.html para index.html...
copy /Y monitor_noticias.html index.html

REM Primeiro push para o GitHub
echo Enviando versao inicial para o GitHub...
git add index.html noticias_valor.json noticias_estadao.json noticias_combinadas.json
git commit -m "Atualizacao automatica inicial %DATE%_%TIME%"
git push origin main

REM Iniciando o servidor web em segundo plano
echo Iniciando servidor web em segundo plano...
start /b "Monitor de Noticias - Servidor Web" C:\Users\erica\AppData\Local\Programs\Python\Launcher\py.exe app.py -w -a

REM Loop principal para atualizar o GitHub
echo Iniciando loop de atualizacao do GitHub. Pressione Ctrl+C para encerrar.
echo.

:loop
REM Esperando 60 segundos
timeout /t 60 /nobreak > nul

REM Executando o scraper para atualizar os arquivos
echo [%TIME%] Atualizando arquivos...
C:\Users\erica\AppData\Local\Programs\Python\Launcher\py.exe scraper.py

REM Renomeando o arquivo para index.html
copy /Y monitor_noticias.html index.html > nul

REM Adiciona os arquivos específicos para o commit
echo [%TIME%] Enviando para o GitHub...
git add index.html noticias_valor.json noticias_estadao.json noticias_combinadas.json > nul

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