#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Monitor de Notícias
Script principal que oferece uma interface de linha de comando para todas as funcionalidades
"""

import os
import argparse
import webbrowser
import time
import threading
from datetime import datetime
from scraper import extrair_todas_noticias

def imprimir_cabecalho():
    """
    Exibe o cabeçalho do programa
    """
    print("\n" + "=" * 70)
    print(" " * 25 + "MONITOR DE NOTÍCIAS")
    print("=" * 70)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y')} | Hora: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 70 + "\n")

def abrir_no_navegador(arquivo):
    """
    Abre um arquivo HTML no navegador padrão
    """
    if os.path.exists(arquivo):
        caminho_absoluto = os.path.abspath(arquivo)
        webbrowser.open('file://' + caminho_absoluto, new=2)
        return True
    return False

def extrair():
    """
    Executa a extração de notícias
    """
    print("\n[*] Iniciando extração de notícias...\n")
    df = extrair_todas_noticias()
    
    if df is not None and not df.empty:
        print(f"\n[+] Extração concluída com sucesso! Foram encontradas {len(df)} notícias.")
        return True
    else:
        print("\n[!] Nenhuma notícia foi extraída ou ocorreu um erro durante a extração.")
        return False

def executar_automaticamente(intervalo=60):
    """
    Executa a extração de notícias automaticamente em intervalos regulares
    
    Args:
        intervalo: Tempo em segundos entre cada extração (padrão: 60 segundos)
    """
    parar_execucao = threading.Event()
    
    def extrair_periodicamente():
        while not parar_execucao.is_set():
            hora_atual = datetime.now().strftime("%H:%M:%S")
            print(f"\n[*] Execução automática em {hora_atual}")
            
            # Executar extração
            sucesso = extrair()
            
            # Abrir no navegador apenas na primeira execução bem-sucedida
            if sucesso and not navegador_aberto[0]:
                if abrir_no_navegador('monitor_noticias.html'):
                    print("[+] Abrindo monitor_noticias.html no navegador...")
                    navegador_aberto[0] = True
            
            # Aguardar pelo intervalo ou até que o evento de parada seja acionado
            parar_execucao.wait(intervalo)
    
    # Variável para controlar se o navegador já foi aberto
    navegador_aberto = [False]
    
    # Iniciar thread para execução periódica
    thread = threading.Thread(target=extrair_periodicamente)
    thread.daemon = True  # Thread será encerrada quando o programa principal terminar
    thread.start()
    
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

def menu_principal():
    """
    Exibe o menu principal e processa a escolha do usuário
    """
    imprimir_cabecalho()
    
    print("Escolha uma opção:")
    print("1. Extrair notícias")
    print("2. Abrir monitor no navegador")
    print("3. Iniciar modo automático (atualizar a cada 1 minuto)")
    print("0. Sair")
    
    try:
        opcao = int(input("\nOpção: "))
        
        if opcao == 1:
            extrair()
            # Perguntar se deseja abrir o resultado no navegador
            resposta = input("\nDeseja abrir o resultado no navegador? (s/n): ").lower()
            if resposta in ['s', 'sim', 'y', 'yes']:
                if abrir_no_navegador('monitor_noticias.html'):
                    print("[+] Abrindo monitor_noticias.html no navegador...")
                else:
                    print("[!] Erro: Não foi possível abrir o arquivo no navegador.")
        elif opcao == 2:
            if abrir_no_navegador('monitor_noticias.html'):
                print("[+] Abrindo monitor_noticias.html no navegador...")
            else:
                print("[!] Erro: Arquivo monitor_noticias.html não encontrado.")
                print("[!] Execute a extração de notícias primeiro.")
        elif opcao == 3:
            # Iniciar modo automático
            executar_automaticamente(60)  # Atualizar a cada 60 segundos (1 minuto)
            return False  # Não retornar ao menu após iniciar o modo automático
        elif opcao == 0:
            print("\n[+] Encerrando o programa. Até breve!")
            return False
        else:
            print("\n[!] Opção inválida. Tente novamente.")
    except ValueError:
        print("\n[!] Por favor, digite um número válido.")
    
    input("\nPressione Enter para continuar...")
    return True

def processar_argumentos():
    """
    Processa argumentos de linha de comando
    """
    parser = argparse.ArgumentParser(description='Monitor de Notícias')
    
    # Definir argumentos
    parser.add_argument('-e', '--extrair', action='store_true', help='Extrair notícias')
    parser.add_argument('-m', '--monitor', action='store_true', help='Abrir monitor no navegador')
    parser.add_argument('-a', '--auto', action='store_true', help='Iniciar modo automático (atualização a cada 1 minuto)')
    parser.add_argument('-i', '--intervalo', type=int, default=60, help='Intervalo em segundos entre atualizações no modo automático')
    
    # Processar argumentos
    args = parser.parse_args()
    
    # Verificar se algum argumento foi fornecido
    if not any(vars(args).values()):
        return False  # Nenhum argumento fornecido, mostrar menu interativo
    
    # Processar os argumentos fornecidos
    if args.extrair:
        extrair()
        if abrir_no_navegador('monitor_noticias.html'):
            print("[+] Abrindo monitor_noticias.html no navegador...")
    
    if args.monitor:
        if abrir_no_navegador('monitor_noticias.html'):
            print("[+] Abrindo monitor_noticias.html no navegador...")
        else:
            print("[!] Erro: Arquivo monitor_noticias.html não encontrado.")
            print("[!] Execute a extração de notícias primeiro.")
    
    if args.auto:
        # Iniciar modo automático com o intervalo especificado
        executar_automaticamente(args.intervalo)
    
    return True  # Argumentos processados

def main():
    """
    Função principal
    """
    # Verificar se há argumentos de linha de comando
    args_processados = processar_argumentos()
    
    # Se não houver argumentos, mostrar menu interativo
    if not args_processados:
        continuar = True
        while continuar:
            continuar = menu_principal()

if __name__ == "__main__":
    main() 