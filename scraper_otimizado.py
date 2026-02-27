#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import pandas as pd
import re
import json
import warnings
import os
import sqlite3
import hashlib
import atexit
import signal
import sys
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Suprimir warnings desnecessários
warnings.filterwarnings("ignore")
os.environ['WDM_LOG_LEVEL'] = '0'

# Variável global para rastrear instâncias do driver
_driver_instance = None

class UnifiedNewsScraper:
    def __init__(self):
        global _driver_instance
        
        self.noticias = []
        self.hoje = datetime.now().strftime("%d/%m/%Y")
        # Calcular data de 24 horas atrás
        self.ontem = (datetime.now() - timedelta(hours=24)).strftime("%d/%m/%Y")
        self.titulos_atuais = set()
        
        # Carregar categorias excluídas do arquivo de configuração
        self.categorias_excluidas = self.carregar_categorias_excluidas()
        
        # Inicializar banco de dados
        self.db_path = 'noticias.db'
        self.inicializar_banco_dados()
        
        # Configurar o driver do Chrome uma única vez
        self.driver = self.configurar_driver()
        _driver_instance = self.driver  # Rastrear instância global
    
    def carregar_categorias_excluidas(self):
        """Carrega as categorias excluídas do arquivo de configuração"""
        categorias = set()
        arquivo_config = 'categorias_excluidas.txt'
        
        try:
            if os.path.exists(arquivo_config):
                with open(arquivo_config, 'r', encoding='utf-8') as f:
                    for linha in f:
                        linha = linha.strip()
                        # Ignorar linhas vazias e comentários
                        if linha and not linha.startswith('#'):
                            categorias.add(linha)
                print(f"Carregadas {len(categorias)} categorias excluídas do arquivo {arquivo_config}")
            else:
                print(f"Arquivo {arquivo_config} não encontrado. Usando lista padrão.")
                # Lista padrão caso o arquivo não exista
                categorias = {
                    'Ambiente', 'Astrologia', 'Blogs', 'Capital', 'Celebridades', 'Ciência', 
                    'Colunas', 'Cotidiano', 'Cultura', 'Educação', 'Ela', 'Espiritualidade e Bem-estar',
                    'Esporte', 'Esportes', 'Eu &', 'Flamengo', 'Folha Social Mais', 'Impresso',
                    'Leo Aversa', 'Marketing', 'Meio ambiente', 'Niterói', 'Novelas', 'Não especificada',
                    'Play', 'Podcasts', 'Tec', 'Tecnologia', 'Tv', 'Um só planeta', 'Vasco', 
                    'Voceviu', 'Época', 'Boa Viagem', 'Clima Extremo', 'Equilibrio', 'Futebol 2025',
                    'Gente', 'Ilustrissima', 'Rio', 'Saideira', 'Saúde', 'Shows e concertos',
                    'Sustentabilidade', 'São Paulo'
                }
        except Exception as e:
            print(f"Erro ao carregar categorias excluídas: {e}")
            categorias = set()
        
        return categorias
    
    def inicializar_banco_dados(self):
        """Inicializa o banco de dados SQLite e cria a tabela se não existir"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Habilitar WAL mode para melhor concorrência
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA synchronous=NORMAL')
            cursor.execute('PRAGMA temp_store=MEMORY')
            cursor.execute('PRAGMA cache_size=-64000')  # 64MB cache
            
            # Criar tabela de notícias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS noticias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    fonte TEXT NOT NULL,
                    data TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    link TEXT UNIQUE NOT NULL,
                    hash_titulo TEXT UNIQUE NOT NULL,
                    data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Criar índices separadamente
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash_titulo ON noticias (hash_titulo)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_coleta ON noticias (data_coleta)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fonte ON noticias (fonte)')
            
            conn.commit()
            conn.close()
            print(f"Banco de dados inicializado: {self.db_path}")
        except Exception as e:
            print(f"Erro ao inicializar banco de dados: {e}")
    
    def gerar_hash_titulo(self, titulo):
        """Gera um hash único para o título da notícia"""
        return hashlib.md5(titulo.encode('utf-8')).hexdigest()
    
    def noticia_ja_existe(self, titulo):
        """Verifica se uma notícia já existe no banco de dados"""
        max_retries = 3
        for tentativa in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                hash_titulo = self.gerar_hash_titulo(titulo)
                cursor.execute('SELECT COUNT(*) FROM noticias WHERE hash_titulo = ?', (hash_titulo,))
                count = cursor.fetchone()[0]
                
                conn.close()
                return count > 0
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and tentativa < max_retries - 1:
                    time.sleep(0.5)  # Aguardar antes de tentar novamente
                    continue
                else:
                    print(f"Erro ao verificar notícia existente: {e}")
                    return False
            except Exception as e:
                print(f"Erro ao verificar notícia existente: {e}")
                return False
        return False
    
    def salvar_noticia_banco(self, noticia):
        """Salva uma notícia no banco de dados"""
        max_retries = 3
        for tentativa in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                cursor = conn.cursor()
                
                hash_titulo = self.gerar_hash_titulo(noticia['titulo'])
                
                cursor.execute('''
                    INSERT OR IGNORE INTO noticias 
                    (titulo, categoria, fonte, data, hora, link, hash_titulo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    noticia['titulo'],
                    noticia['categoria'],
                    noticia['fonte'],
                    noticia['data'],
                    noticia['hora'],
                    noticia['link'],
                    hash_titulo
                ))
                
                conn.commit()
                conn.close()
                return True
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and tentativa < max_retries - 1:
                    time.sleep(0.5)  # Aguardar antes de tentar novamente
                    continue
                else:
                    print(f"Erro ao salvar notícia no banco: {e}")
                    return False
            except Exception as e:
                print(f"Erro ao salvar notícia no banco: {e}")
                return False
        return False
    
    def contar_duplicatas_encontradas(self, titulos):
        """Conta quantas notícias dos títulos fornecidos já existem no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            duplicatas = 0
            for titulo in titulos:
                if self.noticia_ja_existe(titulo):
                    duplicatas += 1
            
            conn.close()
            return duplicatas
        except Exception as e:
            print(f"Erro ao contar duplicatas: {e}")
            return 0
    
    def buscar_noticias_banco_6h(self):
        """Busca notícias do banco de dados publicadas até 6 horas atrás do momento atual"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # Calcular 6 horas atrás do momento atual
            agora = datetime.now()
            limite_6h = agora - timedelta(hours=6)
            
            # Buscar todas as notícias do banco
            cursor.execute('''
                SELECT titulo, categoria, fonte, data, hora, link, data_coleta
                FROM noticias 
                ORDER BY data_coleta DESC
            ''')
            
            noticias_banco = []
            for row in cursor.fetchall():
                # Verificar se a notícia foi publicada até 6 horas atrás
                try:
                    data_hora_str = f"{row[3]} {row[4]}"  # data + hora
                    data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
                    
                    # Se a notícia foi publicada até 6 horas atrás, incluir
                    if data_hora_noticia >= limite_6h:
                        noticia = {
                            'titulo': row[0],
                            'categoria': row[1],
                            'fonte': row[2],
                            'data': row[3],
                            'hora': row[4],
                            'link': row[5],
                            'data_coleta': row[6]
                        }
                        noticias_banco.append(noticia)
                except:
                    # Se houver erro na conversão, pular a notícia
                    continue
            
            conn.close()
            print(f"   Carregadas {len(noticias_banco)} notícias do banco de dados (publicadas até 6h atrás desde {limite_6h.strftime('%d/%m/%Y %H:%M')})")
            return noticias_banco
        except Exception as e:
            print(f"Erro ao buscar notícias do banco: {e}")
            return []
    
    def noticia_dentro_24h(self, data, hora):
        """Verifica se uma notícia está dentro das últimas 24 horas"""
        try:
            # Converter data e hora para datetime
            data_hora_str = f"{data} {hora}"
            data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
            
            # Calcular 24 horas atrás
            limite_24h = datetime.now() - timedelta(hours=24)
            
            # Verificar se a notícia está dentro das últimas 24 horas
            return data_hora_noticia >= limite_24h
        except:
            # Se houver erro na conversão, considerar como válida
            return True
    
    def configurar_driver(self):
        """Configura o driver do Chrome para a automação"""
        print("Configurando driver do Chrome...")
        
        # Configurações otimizadas para melhor performance e estabilidade
        chrome_args = [
            #"--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080",
            "--disable-extensions",
            "--disable-logging",
            "--log-level=3",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-blink-features=AutomationControlled",
            "--disable-images",
            "--disable-plugins",
            "--disable-default-apps",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-ipc-flooding-protection",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--mute-audio",
            "--no-first-run",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-hang-monitor",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-domain-reliability",
            "--disable-features=TranslateUI",
            "--aggressive-cache-discard",
            "--memory-pressure-off",
            # Suprimir erros WebGL e GPU
            "--disable-software-rasterizer",
            "--disable-webgl",
            "--disable-webgl2",
            "--disable-3d-apis",
            "--disable-accelerated-2d-canvas",
            "--disable-accelerated-video-decode",
            "--use-gl=swiftshader",
            "--enable-unsafe-swiftshader",
            # Suprimir mais warnings
            "--silent",
            "--disable-infobars",
            "--disable-notifications"
        ]
        
        # Tentar configurar Chrome
        try:
            chrome_options = ChromeOptions()
            for arg in chrome_args:
                chrome_options.add_argument(arg)
            # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            # chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Suprimir logs do ChromeDriver
            os.environ['WDM_LOG'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
            os.environ['WDM_LOG_LEVEL'] = '0'
            
            # Tentar baixar driver automaticamente
            # print("Baixando ChromeDriver automaticamente...")
            # service = ChromeService(
            #     ChromeDriverManager().install(),
            #     log_output=os.devnull  # Suprimir logs do ChromeDriver
            # )
            # driver = webdriver.Chrome(service=service, options=chrome_options)
            driver = webdriver.Chrome(command_executor="http://airflow.jgp.com.br:4445", options=chrome_options)
            
            # Configurar timeouts otimizados
            driver.set_page_load_timeout(180)  # 3 minutos para carregar página
            driver.implicitly_wait(15)  # 15 segundos para encontrar elementos
            driver.set_script_timeout(60)  # 60 segundos para scripts
            
            print("Chrome configurado com sucesso!")
            return driver
            
        except Exception as e:
            print(f"Erro ao baixar ChromeDriver automaticamente: {e}")
            print("Tentando usar Chrome do sistema...")
            
            try:
                # Tentar usar Chrome do sistema
                chrome_options = ChromeOptions()
                for arg in chrome_args:
                    chrome_options.add_argument(arg)
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                service = ChromeService(log_output=os.devnull)  # Suprimir logs
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Configurar timeouts otimizados
                driver.set_page_load_timeout(180)
                driver.implicitly_wait(15)
                driver.set_script_timeout(60)
                
                print("Chrome do sistema configurado com sucesso!")
                return driver
                
            except Exception as e2:
                print(f"Erro ao usar Chrome do sistema: {e2}")
                raise Exception("Não foi possível configurar o Chrome. Verifique se o Chrome está instalado e se há conectividade com a internet.")
    
    def fechar_driver(self):
        """Fecha o driver do navegador e mata processos Chrome residuais"""
        if self.driver:
            try:
                self.driver.quit()
                print("Driver fechado.")
            except Exception as e:
                print(f"Erro ao fechar driver: {e}")
        
        # Garantir que todos os processos do Chrome sejam fechados
        try:
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                # Matar processos chromedriver.exe e chrome.exe residuais
                subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("Processos Chrome residuais finalizados.")
        except Exception as e:
            print(f"Aviso: Não foi possível matar processos residuais: {e}")
    
    def reinicializar_driver(self):
        """Reinicializa o driver em caso de problemas"""
        print("Reinicializando driver...")
        self.fechar_driver()
        time.sleep(3)  # Aguardar um pouco antes de reinicializar
        self.driver = self.configurar_driver()
        print("Driver reinicializado com sucesso!")
    
    def acessar_pagina_com_retry(self, url, max_tentativas=3, timeout=180):
        """Acessa uma página com retry em caso de timeout"""
        for tentativa in range(max_tentativas):
            try:
                print(f"   Tentativa {tentativa + 1}/{max_tentativas}: Acessando {url}")
                self.driver.set_page_load_timeout(timeout)
                
                # Limpar cache e cookies antes de cada tentativa
                if tentativa > 0:
                    try:
                        self.driver.delete_all_cookies()
                        self.driver.execute_script("window.localStorage.clear();")
                        self.driver.execute_script("window.sessionStorage.clear();")
                    except:
                        pass  # Ignorar erros de limpeza
                
                self.driver.get(url)
                
                # Aguardar um pouco para garantir que a página carregou completamente
                time.sleep(2)
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f"   Erro na tentativa {tentativa + 1}: {error_msg[:100]}...")
                
                # Se for timeout específico ou erro de conexão, tentar reinicializar o driver
                if ("timeout" in error_msg.lower() or "timed out" in error_msg.lower() or 
                    "connection" in error_msg.lower() or "refused" in error_msg.lower()) and tentativa == 1:
                    print("   Tentando reinicializar driver...")
                    try:
                        self.reinicializar_driver()
                    except Exception as reinicializar_error:
                        print(f"   Erro ao reinicializar driver: {reinicializar_error}")
                
                # Se for timeout específico, aguardar mais tempo
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    wait_time = 10 + (tentativa * 5)  # Aumentar tempo de espera progressivamente
                else:
                    wait_time = 5
                
                if tentativa < max_tentativas - 1:
                    print(f"   Aguardando {wait_time} segundos antes da próxima tentativa...")
                    time.sleep(wait_time)
                else:
                    print(f"   Falha após {max_tentativas} tentativas")
                    return False
        return False
    
    def extrair_valor_economico(self):
        """Extrai notícias do Valor Econômico até encontrar notícias do dia anterior"""
        print("\n>> VALOR ECONOMICO")
        print("   Acessando site...")
        url_base = "https://valor.globo.com/ultimas-noticias/"
        
        if not self.acessar_pagina_com_retry(url_base):
            print("   ERRO: Não foi possível acessar o site do Valor Econômico")
            return []
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
        )
        
        noticias_valor = []
        pagina = 1
        noticias_dia_anterior_encontradas = False
        duplicatas_consecutivas = 0
        
        while not noticias_dia_anterior_encontradas:
            if pagina > 1:
                url = f"https://valor.globo.com/ultimas-noticias/index/feed/pagina-{pagina}"
                if not self.acessar_pagina_com_retry(url):
                    print(f"   ERRO: Não foi possível acessar página {pagina}")
                    break
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
                    )
                except:
                    break
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            artigos = soup.find_all('div', class_='feed-post-body')
            
            novas_noticias = 0
            noticias_dia_anterior_nesta_pagina = 0
            
            for artigo in artigos:
                try:
                    link_element = artigo.find('a', class_='feed-post-link')
                    if not link_element:
                        continue
                        
                    titulo = link_element.text.strip()
                    if titulo in self.titulos_atuais:
                        continue
                        
                    link = link_element['href']
                    categoria_element = artigo.find('span', class_='feed-post-metadata-section')
                    categoria = categoria_element.text.strip() if categoria_element else "Não especificada"
                    
                    data_element = artigo.find('span', class_='feed-post-datetime')
                    if not data_element:
                        continue
                        
                    data_hora_texto = data_element.text.strip()
                    data_match = re.search(r'(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})', data_hora_texto)
                    
                    if data_match:
                        data = data_match.group(1)
                        hora = data_match.group(2)
                        
                        # Verificar se a notícia está dentro das últimas 24 horas
                        if not self.noticia_dentro_24h(data, hora):
                            noticias_dia_anterior_nesta_pagina += 1
                            continue
                        
                        # Verificar se a notícia já existe no banco
                        if self.noticia_ja_existe(titulo):
                            duplicatas_consecutivas += 1
                            continue
                        
                        noticia = {
                            'titulo': titulo,
                            'categoria': categoria,
                            'fonte': 'Valor Econômico',
                            'data': data,
                            'hora': hora,
                            'link': link
                        }
                        
                        # Salvar no banco de dados
                        if self.salvar_noticia_banco(noticia):
                            noticias_valor.append(noticia)
                            self.titulos_atuais.add(titulo)
                            novas_noticias += 1
                            duplicatas_consecutivas = 0  # Reset contador de duplicatas
                except:
                    continue
            
            if pagina == 1:
                print(f"   Pagina {pagina}: {novas_noticias} noticias encontradas")
            elif novas_noticias > 0:
                print(f"   Pagina {pagina}: +{novas_noticias} noticias")
            
            # Se encontrou muitas notícias do dia anterior nesta página, parar
            if noticias_dia_anterior_nesta_pagina >= 3:
                print("   PARADA: noticias antigas detectadas")
                noticias_dia_anterior_encontradas = True
            elif novas_noticias == 0 and pagina > 1:
                noticias_dia_anterior_encontradas = True
            
            pagina += 1
            
            # Limite de segurança para evitar loop infinito
            if pagina > 20:
                break
        
        print(f"   TOTAL: {len(noticias_valor)} noticias")
        return noticias_valor
    
    def extrair_estadao(self):
        """Extrai notícias do Estadão até encontrar notícias do dia anterior"""
        print("\n>> ESTADAO")
        print("   Acessando site...")
        url = "https://www.estadao.com.br/ultimas/"
        
        if not self.acessar_pagina_com_retry(url):
            print("   ERRO: Não foi possível acessar o site do Estadão")
            return []
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-component-name='lista-ultimas']"))
        )
        
        noticias_estadao = []
        clique = 0
        tentativas_sem_novas = 0
        noticias_dia_anterior_encontradas = False
        duplicatas_consecutivas = 0
        
        while not noticias_dia_anterior_encontradas:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            artigos = soup.find_all('a', attrs={'data-component-name': 'lista-ultimas'})
            
            novas_noticias = 0
            noticias_dia_anterior_nesta_iteracao = 0
            
            for artigo in artigos:
                try:
                    titulo = artigo.get('title', '').strip()
                    if not titulo or titulo in self.titulos_atuais:
                        continue
                        
                    link = artigo.get('href', '#')
                    categoria = self.extrair_categoria_estadao(link)
                    
                    parent_div = artigo.find_parent('div')
                    data_element = None
                    if parent_div:
                        data_element = parent_div.find('span', class_='date')
                    
                    if not data_element:
                        continue
                    
                    data_hora_texto = data_element.text.strip()
                    data_match = re.search(r'(\d{2}/\d{2}/\d{4}),\s*(\d{1,2})h(\d{2})', data_hora_texto)
                    
                    if data_match:
                        data = data_match.group(1)
                        hora = f"{data_match.group(2)}:{data_match.group(3)}"
                        
                        # Verificar se a notícia está dentro das últimas 24 horas
                        if not self.noticia_dentro_24h(data, hora):
                            noticias_dia_anterior_nesta_iteracao += 1
                            continue
                        
                        # Verificar se a notícia já existe no banco
                        if self.noticia_ja_existe(titulo):
                            duplicatas_consecutivas += 1
                            continue
                        
                        noticia = {
                            'titulo': titulo,
                            'categoria': categoria,
                            'fonte': 'Estadão',
                            'data': data,
                            'hora': hora,
                            'link': link
                        }
                        
                        # Salvar no banco de dados
                        if self.salvar_noticia_banco(noticia):
                            noticias_estadao.append(noticia)
                            self.titulos_atuais.add(titulo)
                            duplicatas_consecutivas = 0  # Reset contador de duplicatas
                        novas_noticias += 1
                except:
                    continue
            
            if clique == 0:
                print(f"   Pagina inicial: {novas_noticias} noticias encontradas")
            elif novas_noticias > 0:
                print(f"   Carregamento {clique}: +{novas_noticias} noticias")
                tentativas_sem_novas = 0
            else:
                tentativas_sem_novas += 1
            
            # Verificar se deve parar
            if noticias_dia_anterior_nesta_iteracao >= 3:
                print("   PARADA: noticias antigas detectadas")
                noticias_dia_anterior_encontradas = True
            elif duplicatas_consecutivas >= 2:
                print("   PARADA: muitas duplicatas encontradas (notícias já coletadas)")
                noticias_dia_anterior_encontradas = True
            elif tentativas_sem_novas >= 3:
                noticias_dia_anterior_encontradas = True
            elif clique >= 15:  # Limite de segurança
                noticias_dia_anterior_encontradas = True
            else:
                # Tentar clicar em "Carregar mais"
                if not self.clicar_carregar_mais_estadao():
                    noticias_dia_anterior_encontradas = True
                else:
                    clique += 1
                    time.sleep(1)
        
        print(f"   TOTAL: {len(noticias_estadao)} noticias")
        return noticias_estadao
    
    def extrair_categoria_estadao(self, link):
        """Extrai categoria baseada na URL do Estadão"""
        url_categories = {
            '/politica/': 'Política', '/economia/': 'Economia', '/esportes/': 'Esportes',
            '/cultura/': 'Cultura', '/internacional/': 'Internacional', '/sustentabilidade/': 'Sustentabilidade',
            '/educacao/': 'Educação', '/saude/': 'Saúde', '/brasil/': 'Brasil', '/tecnologia/': 'Tecnologia',
            '/jornal-do-carro/': 'Automóveis', '/sao-paulo/': 'São Paulo', '/estadao-verifica/': 'Fato ou Fake',
            '/opiniao/': 'Opinião'
        }
        
        for url_path, cat_name in url_categories.items():
            if url_path in link.lower():
                return cat_name
        return "Não especificada"
    
    def clicar_carregar_mais_estadao(self):
        """Clica no botão carregar mais do Estadão"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            self.driver.execute_script("""
                var banners = document.querySelectorAll('.banner__container, .banner, [id="banner"]');
                for(var i=0; i<banners.length; i++) { banners[i].remove(); }
            """)
            
            botao = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.see-more[data-component-name='lista-ultimas']"))
            )
            
            self.driver.execute_script("arguments[0].click();", botao)
            time.sleep(2)
            return True
        except:
            return False
    
    def extrair_folha(self):
        """Extrai notícias da Folha até encontrar notícias do dia anterior"""
        print("\n>> FOLHA DE S.PAULO")
        print("   Acessando site...")
        url = "https://www1.folha.uol.com.br/ultimas-noticias/"
        
        if not self.acessar_pagina_com_retry(url):
            print("   ERRO: Não foi possível acessar o site da Folha")
            return []
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "c-main-headline__title"))
        )
        
        noticias_folha = []
        clique = 0
        tentativas_sem_novas = 0
        noticias_dia_anterior_encontradas = False
        duplicatas_consecutivas = 0
        
        while not noticias_dia_anterior_encontradas:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extrair notícia principal (apenas na primeira iteração)
            if clique == 0:
                main_headline = soup.find('a', class_='c-main-headline__url')
                if main_headline:
                    try:
                        titulo_element = main_headline.find('h2', class_='c-main-headline__title')
                        if titulo_element:
                            titulo = titulo_element.text.strip()
                            link = main_headline['href']
                            categoria = self.extrair_categoria_folha(link)
                            
                            data_element = main_headline.find('time', class_='c-headline__dateline')
                            if data_element:
                                data_hora = self.processar_data_folha(data_element.text.strip())
                                if data_hora and self.noticia_dentro_24h(data_hora[0], data_hora[1]):
                                    # Verificar se a notícia já existe no banco
                                    if not self.noticia_ja_existe(titulo):
                                        noticia = {
                                            'titulo': titulo,
                                            'categoria': categoria,
                                            'fonte': 'Folha de S.Paulo',
                                            'data': data_hora[0],
                                            'hora': data_hora[1],
                                            'link': link
                                        }
                                        
                                        # Salvar no banco de dados
                                        if self.salvar_noticia_banco(noticia):
                                            noticias_folha.append(noticia)
                                            self.titulos_atuais.add(titulo)
                    except:
                        pass
            
            # Extrair notícias secundárias - corrigido para funcionar corretamente
            artigos = soup.find_all('a', href=re.compile(r"folha\.uol\.com\.br/.*\.shtml"))
            novas_noticias = 0
            noticias_dia_anterior_nesta_iteracao = 0
            
            for artigo in artigos:
                try:
                    # Procurar por h2 com c-headline__title dentro do link
                    titulo_element = artigo.find('h2', class_='c-headline__title')
                    if not titulo_element:
                        continue
                    
                    titulo = titulo_element.text.strip()
                    if not titulo or titulo in self.titulos_atuais:
                        continue
                    
                    link = artigo['href']
                    categoria = self.extrair_categoria_folha(link)
                    
                    # Procurar por time com c-headline__dateline dentro do link
                    data_element = artigo.find('time', class_='c-headline__dateline')
                    if not data_element:
                        continue
                    
                    data_hora = self.processar_data_folha(data_element.text.strip())
                    if not data_hora:
                        continue
                    
                    # Verificar se a notícia está dentro das últimas 24 horas
                    if not self.noticia_dentro_24h(data_hora[0], data_hora[1]):
                        noticias_dia_anterior_nesta_iteracao += 1
                        continue
                    
                    # Verificar se a notícia já existe no banco
                    if self.noticia_ja_existe(titulo):
                        duplicatas_consecutivas += 1
                        continue
                    
                    noticia = {
                        'titulo': titulo,
                        'categoria': categoria,
                        'fonte': 'Folha de S.Paulo',
                        'data': data_hora[0],
                        'hora': data_hora[1],
                        'link': link
                    }
                    
                    # Salvar no banco de dados
                    if self.salvar_noticia_banco(noticia):
                        noticias_folha.append(noticia)
                        self.titulos_atuais.add(titulo)
                        novas_noticias += 1
                        duplicatas_consecutivas = 0  # Reset contador de duplicatas
                except Exception as e:
                    # Log do erro para debug
                    continue
            
            if clique == 0:
                print(f"   Pagina inicial: {len(noticias_folha)} noticias encontradas")
            elif novas_noticias > 0:
                print(f"   Carregamento {clique}: +{novas_noticias} noticias")
                tentativas_sem_novas = 0
            else:
                tentativas_sem_novas += 1
            
            # Verificar se deve parar
            if noticias_dia_anterior_nesta_iteracao >= 5:
                print("   PARADA: noticias antigas detectadas")
                noticias_dia_anterior_encontradas = True
            elif duplicatas_consecutivas >= 2:
                print("   PARADA: muitas duplicatas encontradas (notícias já coletadas)")
                noticias_dia_anterior_encontradas = True
            elif tentativas_sem_novas >= 3:
                noticias_dia_anterior_encontradas = True
            elif clique >= 10:  # Limite de segurança
                noticias_dia_anterior_encontradas = True
            else:
                # Tentar clicar em "Ver mais"
                if not self.clicar_ver_mais_folha():
                    noticias_dia_anterior_encontradas = True
                else:
                    clique += 1
                    time.sleep(1)
        
        print(f"   TOTAL: {len(noticias_folha)} noticias")
        return noticias_folha
    
    def extrair_categoria_folha(self, link):
        """Extrai categoria baseada na URL da Folha"""
        categorias_map = {
            'poder': 'Política', 'mercado': 'Economia', 'cotidiano': 'Cotidiano',
            'mundo': 'Mundo', 'esporte': 'Esporte', 'ilustrada': 'Cultura',
            'f5': 'Entretenimento', 'ambiente': 'Ambiente', 'ciencia': 'Ciência',
            'equilibrioesaude': 'Saúde', 'educacao': 'Educação', 'tecnologia': 'Tecnologia'
        }
        
        url_match = re.search(r'folha\.uol\.com\.br/([^/]+)/', link)
        if url_match:
            categoria_url = url_match.group(1)
            return categorias_map.get(categoria_url, categoria_url.replace('-', ' ').title())
        return "Não especificada"
    
    def processar_data_folha(self, data_hora_texto):
        """Processa data da Folha no formato "25.abr.2025 às 12h22" ou "25.abr.2025 Ã s 12h22" """
        # Normalizar texto para lidar com problemas de codificação
        texto_normalizado = data_hora_texto.replace('Ã s', 'às').replace('Ã¡', 'á').replace('Ã£', 'ã').replace('Ã³', 'ó')
        
        # Tentar diferentes padrões de regex
        patterns = [
            r'(\d{1,2})\.(\w{3})\.(\d{4})\s+às\s+(\d{1,2})h(\d{2})',  # Formato normal
            r'(\d{1,2})\.(\w{3})\.(\d{4})\s+(\d{1,2})h(\d{2})',      # Sem "às"
        ]
        
        for pattern in patterns:
            data_match = re.search(pattern, texto_normalizado)
            if data_match:
                dia = data_match.group(1).zfill(2)  # Garantir 2 dígitos
                mes_texto = data_match.group(2).lower()
                ano = data_match.group(3)
                hora = data_match.group(4).zfill(2)  # Garantir 2 dígitos
                minuto = data_match.group(5)
                
                meses = {
                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
                    'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                }
                
                if mes_texto in meses:
                    mes = meses[mes_texto]
                    data_formatada = f"{dia}/{mes}/{ano}"
                    hora_formatada = f"{hora}:{minuto}"
                    return (data_formatada, hora_formatada)
        return None
    
    def clicar_ver_mais_folha(self):
        """Clica no botão ver mais da Folha"""
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            self.driver.execute_script("""
                var banners = document.querySelectorAll('.banner, [id*="banner"], [class*="banner"], [class*="lgpd"], [id*="lgpd"]');
                for(var i=0; i<banners.length; i++) { banners[i].remove(); }
            """)
            
            botoes = self.driver.find_elements(By.CSS_SELECTOR, "button.c-button--expand[data-pagination-trigger]")
            if not botoes:
                return False
                
            botao = botoes[0]
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
            time.sleep(1)
            
            self.driver.execute_script("arguments[0].click();", botao)
            time.sleep(3)
            return True
        except Exception as e:
            return False
    
    def extrair_oglobo(self):
        """Extrai notícias de O Globo até encontrar notícias do dia anterior"""
        print("\n>> O GLOBO")
        print("   Acessando site...")
        url_base = "https://oglobo.globo.com/ultimas-noticias/"
        
        if not self.acessar_pagina_com_retry(url_base):
            print("   ERRO: Não foi possível acessar o site do O Globo")
            return []
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
        )
        
        noticias_oglobo = []
        pagina = 1
        noticias_dia_anterior_encontradas = False
        duplicatas_consecutivas = 0
        
        while not noticias_dia_anterior_encontradas:
            if pagina > 1:
                url = f"https://oglobo.globo.com/ultimas-noticias/index/feed/pagina-{pagina}.ghtml"
                if not self.acessar_pagina_com_retry(url):
                    print(f"   ERRO: Não foi possível acessar página {pagina}")
                    break
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
                    )
                except:
                    break
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            artigos = soup.find_all('div', class_='feed-post-body')
            
            novas_noticias = 0
            noticias_dia_anterior_nesta_pagina = 0
            
            for artigo in artigos:
                try:
                    link_element = artigo.find('a', class_='feed-post-link')
                    if not link_element:
                        continue
                        
                    titulo = link_element.text.strip()
                    link = link_element['href']
                    categoria_element = artigo.find('span', class_='feed-post-metadata-section')
                    categoria = categoria_element.text.strip() if categoria_element else "Não especificada"
                    
                    tempo_element = artigo.find('span', class_='feed-post-datetime')
                    if not tempo_element:
                        continue
                    
                    tempo_relativo = tempo_element.text.strip()
                    data_hora = self.calcular_tempo_absoluto(tempo_relativo)
                    
                    if data_hora[0] and data_hora[1]:
                        # Verificar se a notícia está dentro das últimas 24 horas
                        if not self.noticia_dentro_24h(data_hora[0], data_hora[1]):
                            noticias_dia_anterior_nesta_pagina += 1
                            continue
                        
                        # Verificar se a notícia já existe no banco
                        if self.noticia_ja_existe(titulo):
                            duplicatas_consecutivas += 1
                            continue
                        
                        noticia = {
                            'titulo': titulo,
                            'categoria': categoria,
                            'fonte': 'O Globo',
                            'data': data_hora[0],
                            'hora': data_hora[1],
                            'link': link
                        }
                        
                        # Salvar no banco de dados
                        if self.salvar_noticia_banco(noticia):
                            noticias_oglobo.append(noticia)
                            self.titulos_atuais.add(titulo)
                            novas_noticias += 1
                            duplicatas_consecutivas = 0  # Reset contador de duplicatas
                except:
                    continue
            
            if pagina == 1:
                print(f"   Pagina {pagina}: {novas_noticias} noticias encontradas")
            elif novas_noticias > 0:
                print(f"   Pagina {pagina}: +{novas_noticias} noticias")
            
            # Se encontrou muitas notícias do dia anterior nesta página, parar
            if noticias_dia_anterior_nesta_pagina >= 3:
                print("   PARADA: noticias antigas detectadas")
                noticias_dia_anterior_encontradas = True
            elif duplicatas_consecutivas >= 2:
                print("   PARADA: muitas duplicatas encontradas (notícias já coletadas)")
                noticias_dia_anterior_encontradas = True
            elif novas_noticias == 0 and pagina > 1:
                noticias_dia_anterior_encontradas = True
            
            pagina += 1
            
            # Limite de segurança para evitar loop infinito
            if pagina > 20:
                break
        
        print(f"   TOTAL: {len(noticias_oglobo)} noticias")
        return noticias_oglobo
    
    def calcular_tempo_absoluto(self, tempo_relativo):
        """Converte tempo relativo para absoluto"""
        agora = datetime.now()
        tempo_relativo = tempo_relativo.lower()
        
        try:
            if 'agora' in tempo_relativo or 'poucos instantes' in tempo_relativo:
                tempo_calculado = agora
            elif 'minuto' in tempo_relativo:
                minutos = int(re.search(r'\d+', tempo_relativo).group())
                tempo_calculado = agora - timedelta(minutes=minutos)
            elif 'hora' in tempo_relativo:
                horas = int(re.search(r'\d+', tempo_relativo).group())
                tempo_calculado = agora - timedelta(hours=horas)
            else:
                return None, None
            
            data_calculada_str = tempo_calculado.strftime("%d/%m/%Y")
            if data_calculada_str != self.hoje:
                return None, None
            
            return tempo_calculado.strftime("%d/%m/%Y"), tempo_calculado.strftime("%H:%M")
        except:
            return None, None
    
    def extrair_todas_noticias(self):
        """Extrai notícias de todas as fontes usando um único driver"""
        print("INICIANDO EXTRACAO DE NOTICIAS")
        print(f"Data de hoje: {self.hoje}")
        print(f"Capturando notícias das últimas 24 horas (desde: {self.ontem})")
        print("=" * 50)
        
        start_time = time.time()
        
        # Extrair de cada fonte sequencialmente
        noticias_valor = self.extrair_valor_economico()
        noticias_estadao = self.extrair_estadao()
        noticias_folha = self.extrair_folha()
        noticias_oglobo = self.extrair_oglobo()
        
        # Buscar notícias do banco de dados publicadas até 6 horas atrás
        print("\nCARREGANDO NOTÍCIAS DO BANCO DE DADOS...")
        noticias_banco = self.buscar_noticias_banco_6h()
        
        # Filtrar notícias com categorias excluídas (coletadas + banco)
        noticias_coletadas = noticias_valor + noticias_estadao + noticias_folha + noticias_oglobo
        noticias_banco_filtradas = [noticia for noticia in noticias_banco if noticia['categoria'] not in self.categorias_excluidas]
        noticias_coletadas_filtradas = [noticia for noticia in noticias_coletadas if noticia['categoria'] not in self.categorias_excluidas]
        
        # Combinar notícias coletadas com as do banco (evitando duplicatas)
        todas_noticias = noticias_coletadas_filtradas + noticias_banco_filtradas
        
        # Remover duplicatas baseado no título
        titulos_unicos = set()
        noticias_unicas = []
        for noticia in todas_noticias:
            if noticia['titulo'] not in titulos_unicos:
                titulos_unicos.add(noticia['titulo'])
                noticias_unicas.append(noticia)
        
        self.noticias = noticias_unicas
        
        total_antes_filtro = len(noticias_coletadas) + len(noticias_banco)
        total_filtradas = total_antes_filtro - len(noticias_unicas)
        
        print(f"\nFILTRAGEM APLICADA:")
        print(f"   Total antes do filtro: {total_antes_filtro}")
        print(f"   Noticias filtradas (excluidas): {total_filtradas}")
        print(f"   Total apos filtro: {len(noticias_unicas)}")
        
        print("\nSALVANDO ARQUIVOS...")
        # Salvar arquivos individuais
        self.salvar_json(noticias_valor, 'noticias_valor.json')
        self.salvar_json(noticias_estadao, 'noticias_estadao.json')
        self.salvar_json(noticias_folha, 'noticias_folha.json')
        self.salvar_json(noticias_oglobo, 'noticias_oglobo.json')
        
        # Criar DataFrame combinado
        if self.noticias:
            df_combinado = pd.DataFrame(self.noticias)
            df_combinado = df_combinado.drop_duplicates(subset=['titulo'])
            
            # Ordenar por data e hora
            try:
                df_combinado['data_hora'] = pd.to_datetime(df_combinado['data'] + ' ' + df_combinado['hora'], format='%d/%m/%Y %H:%M', errors='coerce')
                df_combinado = df_combinado.dropna(subset=['data_hora'])
                df_combinado = df_combinado.sort_values(by='data_hora', ascending=False)
                df_combinado = df_combinado.drop('data_hora', axis=1)
            except Exception as e:
                pass
            
            # Salvar arquivo combinado
            self.salvar_json(df_combinado.to_dict('records'), 'noticias_combinadas.json')
            
            # Gerar HTML
            print("Gerando pagina HTML...")
            self.gerar_html_completo(df_combinado)
            
            end_time = time.time()
            tempo_execucao = end_time - start_time
            
            print("\n" + "=" * 50)
            print("EXTRACAO CONCLUIDA COM SUCESSO!")
            print(f"Total de noticias (últimas 6h): {len(df_combinado)}")
            print(f"Tempo de execucao: {tempo_execucao:.1f} segundos")
            print("=" * 50)
            
            return df_combinado
        else:
            print("Nenhuma noticia foi encontrada.")
            return None
    
    def salvar_json(self, dados, nome_arquivo):
        """Salva dados em formato JSON"""
        try:
            if isinstance(dados, list):
                df = pd.DataFrame(dados)
            else:
                df = dados
            
            if not df.empty:
                df.to_json(nome_arquivo, orient='records', force_ascii=False)
                print(f"   OK: {nome_arquivo}")
        except Exception as e:
            print(f"   ERRO: {nome_arquivo}")
    
    def gerar_html_completo(self, df):
        """Gera arquivo HTML com todas as notícias"""
        try:
            data_atual = datetime.now().strftime("%d/%m/%Y")
            hora_atual = datetime.now().strftime("%H:%M:%S")
            total_noticias = len(df)
            
            # Mapa de cores para categorias
            cores_categorias = {
                'Empresas': '#4CAF50', 'Política': '#2196F3', 'Brasil': '#FF9800',
                'Finanças': '#9C27B0', 'Mundo': '#E91E63', 'Agronegócios': '#8BC34A',
                'Carreira': '#00BCD4', 'Tecnologia': '#673AB7', 'Legislação': '#795548',
                'Opinião': '#607D8B', 'Não especificada': '#9E9E9E', 'Futebol': '#FF5722',
                'Esportes': '#FF5722', 'Cultura': '#009688', 'Educação': '#3F51B5',
                'Saúde': '#F44336', 'Internacional': '#E91E63', 'Economia': '#FFC107',
                'Eleições': '#03A9F4', 'Celebridades': '#D500F9', 'Ciência': '#00BFA5',
                'Automóveis': '#827717', 'Entretenimento': '#FF4081', 'Negócios': '#1976D2',
                'Sustentabilidade': '#388E3C', 'São Paulo': '#C62828', 'Rio de Janeiro': '#6A1B9A',
                'História': '#37474F', 'Televisão': '#D81B60', 'Mídia e Marketing': '#7B1FA2'
            }
            
            html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor de Notícias - Brasil</title>

    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">

    <!-- DataTables CSS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css">

    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a5276; text-align: center; margin-bottom: 30px; }}
        .data-atualizacao {{ text-align: center; color: #666; margin-bottom: 20px; font-style: italic; }}
        a {{ color: #2980b9; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .categoria {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: white; }}
        .hora {{ white-space: nowrap; color: #666; }}
        .fonte {{ white-space: nowrap; color: #666; font-weight: bold; }}
        .stats {{ margin-top: 30px; text-align: center; color: #666; }}

        /* Estilos responsivos para celulares */
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .container {{ padding: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Monitor de Notícias - Brasil</h1>
        <div class="data-atualizacao">Atualizado em: {data_atual} às {hora_atual}</div>
        <table id="tabela-noticias" class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>Título</th>
                    <th>Categoria</th>
                    <th>Fonte</th>
                    <th>Hora</th>
                </tr>
            </thead>
            <tbody>"""
            
            if df.empty:
                html_content += "<tr><td colspan='4' style='text-align: center;'>Nenhuma notícia encontrada</td></tr>"
            else:
                for _, noticia in df.iterrows():
                    hora = noticia.get('hora', 'N/D')
                    categoria = noticia.get('categoria', 'Não especificada')
                    titulo = noticia.get('titulo', 'N/D')
                    link = noticia.get('link', '#')
                    fonte = noticia.get('fonte', 'Desconhecida')
                    
                    cor_categoria = cores_categorias.get(categoria, '#9E9E9E')
                    
                    html_content += f"""
                <tr>
                    <td><a href='{link}' target='_blank'>{titulo}</a></td>
                    <td><span class='categoria' style='background-color: {cor_categoria};'>{categoria}</span></td>
                    <td class='fonte'>{fonte}</td>
                    <td class='hora'>{hora}</td>
                </tr>"""
            
            html_content += f"""
            </tbody>
        </table>
        <div class="stats">Total de notícias: {total_noticias}</div>
    </div>

    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>

    <!-- DataTables JS -->
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>

    <script>
        $(document).ready(function() {{
            $('#tabela-noticias').DataTable({{
                language: {{
                    url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                }},
                pageLength: 50,
                order: [],
                responsive: true,
                lengthMenu: [10, 25, 50, 100]
            }});
            
            // Auto-reload silencioso a cada 5 minutos
            console.log('Auto-reload iniciado: atualização a cada 5 minutos');
            setInterval(() => {{
                window.location.reload();
            }}, 300000);
        }});
    </script>
</body>
</html>"""
            
            with open('monitor_noticias.html', 'w', encoding='utf-8-sig') as f:
                f.write(html_content)
            
            print("   OK: monitor_noticias.html")
            return True
        except Exception as e:
            print("   ERRO: ao gerar HTML")
            return False

# Função de limpeza global para garantir fechamento do Chrome
def limpar_processos_chrome():
    """Limpa todos os processos do Chrome e ChromeDriver"""
    global _driver_instance
    
    try:
        if _driver_instance:
            _driver_instance.quit()
            _driver_instance = None
    except:
        pass
    
    try:
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Processos Chrome finalizados na saída.")
    except:
        pass

# Registrar função de limpeza para ser executada na saída do programa
atexit.register(limpar_processos_chrome)

# Handler para Ctrl+C e outros sinais
def signal_handler(sig, frame):
    print("\nInterrompido pelo usuário. Fechando Chrome...")
    limpar_processos_chrome()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Função principal
def extrair_todas_noticias():
    scraper = None
    try:
        scraper = UnifiedNewsScraper()
        return scraper.extrair_todas_noticias()
    except Exception as e:
        print(f"Erro durante extração: {e}")
        raise
    finally:
        if scraper:
            scraper.fechar_driver()
        # Garantir limpeza adicional
        limpar_processos_chrome()

if __name__ == "__main__":
    extrair_todas_noticias() 