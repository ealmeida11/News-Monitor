@echo off
echo Monitor de Noticias - Servidor Web
echo Acesse do seu celular conectando-se na mesma rede WiFi
echo.
echo Instalando Flask se necessario...
pip install flask
echo.
echo Iniciando servidor web com atualizacao automatica a cada 1 minuto...
C:\Users\erica\AppData\Local\Programs\Python\Launcher\py.exe app.py -w -a
pause 