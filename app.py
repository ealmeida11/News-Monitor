#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Monitor de Notícias
Script simplificado para execução do scraper de notícias
"""

import os
import sys
import time
import threading
import webbrowser
import argparse
import socket
from datetime import datetime
from scraper import extrair_todas_noticias

# Variável global para armazenar o app Flask
flask_app = None

def criar_app_flask():
    """
    Cria e configura o aplicativo Flask para servir o monitor de notícias
    """
    try:
        from flask import Flask, send_file
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return send_file('monitor_noticias.html')
        
        @app.route('/noticias.json')
        def noticias_json():
            return send_file('noticias_valor.json')
        
        return app
    except ImportError:
        print("[!] Erro: Flask não está instalado. Instale com 'pip install flask'")
        return None

def get_local_ip():
    """
    Obtém o endereço IP local da máquina para acesso pela rede
    """
    try:
        # Criar um socket e conectar-se a um servidor externo
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"  # Fallback para localhost

def executar_servidor_web(porta=5000, auto_update=False, intervalo=60):
    """
    Executa o servidor web Flask
    
    Args:
        porta: Porta onde o servidor será executado (padrão: 5000)
        auto_update: Define se o monitor deve atualizar automaticamente
        intervalo: Intervalo em segundos entre cada atualização
    """
    global flask_app
    
    # Criar app Flask se ainda não existe
    if flask_app is None:
        flask_app = criar_app_flask()
        if flask_app is None:
            return
    
    # Verificar se já existe um arquivo HTML para servir
    if not os.path.exists('monitor_noticias.html'):
        print("[*] Arquivo HTML não encontrado. Extraindo notícias primeiro...")
        extrair_todas_noticias()
    
    ip_local = get_local_ip()
    
    print(f"\n[+] Servidor web iniciado:")
    print(f"[+] Acesse localmente em: http://localhost:{porta}")
    print(f"[+] Acesse na rede em: http://{ip_local}:{porta}")
    print(f"[+] Para acessar do celular, conecte-se à mesma rede WiFi e use o link acima.")
    
    if auto_update:
        # Iniciar a atualização automática em segundo plano
        threading.Thread(target=lambda: executar_automaticamente(intervalo, False), daemon=True).start()
        print(f"[+] Atualização automática ativada (a cada {intervalo} segundos)")
    
    # Iniciar o servidor Flask
    flask_app.run(host='0.0.0.0', port=porta, debug=False)

def executar_automaticamente(intervalo=60, abrir_navegador=True):
    """
    Executa a extração de notícias automaticamente em intervalos regulares
    
    Args:
        intervalo: Tempo em segundos entre cada extração (padrão: 60 segundos)
        abrir_navegador: Se deve abrir o navegador na primeira execução
    """
    parar_execucao = threading.Event()
    
    def extrair_periodicamente():
        while not parar_execucao.is_set():
            hora_atual = datetime.now().strftime("%H:%M:%S")
            print(f"\n[*] Execução automática em {hora_atual}")
            
            # Executar extração
            extrair_todas_noticias()
            
            # Atualizar a página no navegador (apenas na primeira execução)
            if abrir_navegador and not navegador_aberto[0]:
                arquivo_html = "monitor_noticias.html"
                if os.path.exists(arquivo_html):
                    caminho_absoluto = os.path.abspath(arquivo_html)
                    webbrowser.open('file://' + caminho_absoluto, new=2)
                    navegador_aberto[0] = True
            
            # Aguardar pelo intervalo ou até que o evento de parada seja acionado
            parar_execucao.wait(intervalo)
    
    # Variável para controlar se o navegador já foi aberto
    navegador_aberto = [False]
    
    # Iniciar thread para execução periódica
    thread = threading.Thread(target=extrair_periodicamente)
    thread.daemon = True  # Thread será encerrada quando o programa principal terminar
    thread.start()
    
    if not abrir_navegador:
        # Se estiver rodando como parte do servidor web, apenas retornar
        return
    
    print(f"\n[+] Modo automático iniciado. Atualizando a cada {intervalo} segundos.")
    print("[+] Pressione Ctrl+C para interromper.\n")
    
    try:
        # Manter o programa em execução
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Capturar Ctrl+C para encerrar corretamente
        parar_execucao.set()
        print("\n[+] Interrompendo modo automático...")
        thread.join(timeout=2)
        print("[+] Programa encerrado pelo usuário.")

def executar_uma_vez():
    """
    Função que executa o scraper uma vez e abre o resultado no navegador
    """
    print("=" * 60)
    print(" " * 15 + "MONITOR DE NOTÍCIAS")
    print("=" * 60)
    print("\nIniciando extração de notícias...\n")
    
    # Executar o scraper
    extrair_todas_noticias()
    
    # Verificar se o arquivo HTML foi gerado
    arquivo_html = "monitor_noticias.html"
    if os.path.exists(arquivo_html):
        print(f"\nAbrindo o arquivo {arquivo_html} no navegador...")
        # Obter o caminho absoluto do arquivo
        caminho_absoluto = os.path.abspath(arquivo_html)
        # Abrir o arquivo HTML no navegador padrão
        webbrowser.open('file://' + caminho_absoluto, new=2)
    else:
        print(f"\nErro: O arquivo {arquivo_html} não foi gerado!")
    
    print("\nProcesso concluído!")

def main():
    """
    Função principal que processa argumentos e executa as funções adequadas
    """
    parser = argparse.ArgumentParser(description='Monitor de Notícias - Versão simplificada')
    parser.add_argument('-a', '--auto', action='store_true', help='Executar em modo automático')
    parser.add_argument('-i', '--intervalo', type=int, default=60, help='Intervalo em segundos para o modo automático')
    parser.add_argument('-w', '--web', action='store_true', help='Iniciar servidor web para acesso remoto')
    parser.add_argument('-p', '--porta', type=int, default=5000, help='Porta para o servidor web')
    
    args = parser.parse_args()
    
    if args.web:
        # Iniciar servidor web com atualização automática se solicitado
        executar_servidor_web(args.porta, args.auto, args.intervalo)
    elif args.auto:
        # Iniciar apenas o modo automático
        executar_automaticamente(args.intervalo)
    else:
        # Executar uma única vez
        executar_uma_vez()

if __name__ == "__main__":
    main() 