#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import pandas as pd
import re
import os
import json
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from bs4 import BeautifulSoup
from io import StringIO
import concurrent.futures
import threading
import random

# Pool global de drivers para reutilização
driver_pool = []
driver_lock = threading.Lock()

def criar_driver_otimizado():
    """
    Cria um driver Edge otimizado para performance
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--disable-images")  # Não carregar imagens para ser mais rápido
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-features=BlinkGenPropertyTrees")
    # Configurações adicionais para melhor conectividade
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--max_old_space_size=4096")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.set_page_load_timeout(25)  # Aumentado para 25 segundos para O Globo
    driver.implicitly_wait(5)  # Aumentado para 5 segundos
    return driver

def obter_driver():
    """
    Obtém um driver do pool ou cria um novo
    """
    with driver_lock:
        if driver_pool:
            return driver_pool.pop()
        else:
            return criar_driver_otimizado()

def retornar_driver(driver):
    """
    Retorna um driver para o pool
    """
    with driver_lock:
        if len(driver_pool) < 4:  # Máximo 4 drivers no pool
            driver_pool.append(driver)
        else:
            driver.quit()

class ValorEconomicoScraper:
    def __init__(self):
        self.url = "https://valor.globo.com/ultimas-noticias/"
        self.noticias = []
        self.hoje = datetime.now().strftime("%d/%m/%Y")
        self.titulos_atuais = set()
        self.driver = None
        
    def configurar_driver(self):
        """
        Obtém um driver do pool
        """
        print("Configurando o driver do Microsoft Edge...")
        self.driver = obter_driver()
        return self.driver
    
    def fechar_driver(self):
        """
        Retorna o driver para o pool
        """
        if self.driver:
            retornar_driver(self.driver)
            self.driver = None
            print("Driver do Edge retornado ao pool.")
    
    def obter_pagina(self, url):
        """
        Carrega a página usando o Selenium com timeout otimizado e retry
        """
        try:
            if not carregar_pagina_com_retry(self.driver, url):
                return None
            
            # Aguardar o carregamento dos elementos principais com timeout menor
            WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
            )
            
            return self.driver.page_source
        except Exception as e:
            print(f"Erro ao aguardar elementos da página: {e}")
            return None
    
    def extrair_noticias(self, html):
        """
        Extrai as notícias do HTML usando BeautifulSoup com parada inteligente
        """
        if not html:
            return 0, False
            
        soup = BeautifulSoup(html, 'html.parser')
        artigos = soup.find_all('div', class_='feed-post-body')
        print(f"Encontrados {len(artigos)} artigos na página")
        
        data_atual = self.hoje
        novas_noticias = 0
        noticias_batch = []
        encontrou_noticia_antiga = False
        
        for artigo in artigos:
            try:
                link_element = artigo.find('a', class_='feed-post-link')
                if not link_element:
                    continue
                    
                titulo = link_element.text.strip()
                
                if titulo in self.titulos_atuais:
                    continue
                    
                link = link_element['href']
                fonte = 'Valor Econômico' if 'valor.globo.com' in link else 'Desconhecida'
                
                categoria_element = artigo.find('span', class_='feed-post-metadata-section')
                if not categoria_element:
                    categoria_element = artigo.find('a', class_='feed-post-header-chapeu')
                if not categoria_element:
                    categoria_element = artigo.find('span', class_='feed-post-header-chapeu')
                    
                categoria = categoria_element.text.strip() if categoria_element else "Não especificada"
                
                data_element = artigo.find('span', class_='feed-post-datetime')
                if not data_element:
                    continue
                    
                data_hora_texto = data_element.text.strip()
                data_match = re.search(r'(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})', data_hora_texto)
                
                if data_match:
                    data = data_match.group(1)
                    hora = data_match.group(2)
                    
                    if data != data_atual:
                        # Encontrou notícia antiga - sinalizar para parar
                        encontrou_noticia_antiga = True
                        break
                    
                    noticias_batch.append({
                        'titulo': titulo,
                        'categoria': categoria,
                        'fonte': fonte,
                        'data': data,
                        'hora': hora,
                        'link': link
                    })
                    self.titulos_atuais.add(titulo)
                    novas_noticias += 1
                    
            except Exception as e:
                print(f"Erro ao processar artigo: {e}")
                continue
        
        if noticias_batch:
            self.noticias.extend(noticias_batch)
            print(f"Adicionadas {novas_noticias} novas notícias")
                
        return novas_noticias, encontrou_noticia_antiga
    
    def navegar_para_proxima_pagina(self, pagina_atual):
        """
        Navega diretamente para a próxima página
        """
        try:
            proxima_pagina = pagina_atual + 1
            url_proxima = f"https://valor.globo.com/ultimas-noticias/index/feed/pagina-{proxima_pagina}"
            
            print(f"Navegando para página {proxima_pagina}: {url_proxima}")
            self.driver.get(url_proxima)
            
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
            )
            return True
        except Exception as e:
            print(f"Erro ao navegar para a próxima página: {e}")
            return False
    
    def extrair_todas_noticias(self, max_paginas=10):  # Reduzido de 15 para 10
        """
        Extrai notícias com parada inteligente quando encontra notícias antigas
        """
        if not self.driver:
            self.configurar_driver()
            
        html = self.obter_pagina(self.url)
        if not html:
            print("Erro: Não foi possível carregar a primeira página.")
            return
        
        novas_noticias, encontrou_antiga = self.extrair_noticias(html)
        print(f"Notícias encontradas até agora: {len(self.noticias)}")
        
        # Se já encontrou notícia antiga na primeira página, não precisa continuar
        if encontrou_antiga:
            print("Encontradas notícias antigas na primeira página. Parando extração.")
            return
        
        pagina_atual = 1
        paginas_sem_noticias = 0
        
        while pagina_atual < max_paginas and paginas_sem_noticias < 2:  # Para após 2 páginas sem notícias
            if not self.navegar_para_proxima_pagina(pagina_atual):
                break
            
            html = self.obter_pagina(self.driver.current_url)
            if not html:
                paginas_sem_noticias += 1
                pagina_atual += 1
                continue
            
            novas_noticias, encontrou_antiga = self.extrair_noticias(html)
            
            if encontrou_antiga:
                print(f"Encontradas notícias antigas na página {pagina_atual + 1}. Parando extração.")
                break
                
            if novas_noticias == 0:
                paginas_sem_noticias += 1
            else:
                paginas_sem_noticias = 0
                
            print(f"Notícias encontradas até agora: {len(self.noticias)}")
            pagina_atual += 1
        
        print(f"Extração do Valor Econômico finalizada após verificar {pagina_atual} páginas. Total: {len(self.noticias)} notícias")
    
    def salvar_noticias(self, formato='json'):
        """
        Salva as notícias extraídas em diferentes formatos
        """
        # Verificar se temos notícias
        if not self.noticias:
            print("Nenhuma notícia foi encontrada para salvar.")
            df = pd.DataFrame(columns=['titulo', 'categoria', 'fonte', 'data', 'hora', 'link'])
            return df
            
        # Criar DataFrame das notícias
        df = pd.DataFrame(self.noticias)
        
        # Remover duplicatas
        df = df.drop_duplicates(subset=['titulo'])
        
        # Ordenar por hora (mais recente primeiro)
        if 'hora' in df.columns:
            try:
                df['data_hora'] = pd.to_datetime(df['data'] + ' ' + df['hora'], format='%d/%m/%Y %H:%M', errors='coerce')
                df = df.sort_values(by='data_hora', ascending=False)
                df = df.drop('data_hora', axis=1)
            except Exception as e:
                print(f"Erro ao ordenar por hora: {e}")
        
        # Salvar em formato JSON
        try:
            df.to_json('noticias_valor.json', orient='records', force_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar JSON: {e}")
            
        # Gerar arquivo HTML
        self.gerar_html_otimizado(df)
        
        return df
    
    def gerar_html_otimizado(self, df):
        """
        Gera um arquivo HTML com a tabela de notícias - versão otimizada com encoding corrigido
        """
        try:
            # Obter data e hora atual
            data_atual = datetime.now().strftime("%d/%m/%Y")
            hora_atual = datetime.now().strftime("%H:%M:%S")
            total_noticias = len(df)
            
            # Criar um conjunto de categorias para atribuir cores diferentes
            categorias = set()
            for _, noticia in df.iterrows():
                categoria = noticia.get('categoria', 'Não especificada')
                categorias.add(categoria)
                
            # Mapa de cores amigáveis para categorias
            cores_categorias = {
                'Empresas': '#4CAF50',        # Verde
                'Política': '#2196F3',        # Azul
                'Brasil': '#FF9800',          # Laranja
                'Finanças': '#9C27B0',        # Roxo
                'Mundo': '#E91E63',           # Rosa
                'Agronegócios': '#8BC34A',    # Verde claro
                'Carreira': '#00BCD4',        # Ciano
                'Tecnologia': '#673AB7',      # Índigo
                'Legislação': '#795548',      # Marrom
                'Opinião': '#607D8B',         # Azul acinzentado
                'Não especificada': '#9E9E9E' # Cinza
            }
            
            # Cor padrão para categorias não mapeadas
            cor_padrao = '#9E9E9E' # Cinza
            
            # Conteúdo HTML completo em uma única string
            html_content = """<!DOCTYPE html>
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
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #1a5276; text-align: center; margin-bottom: 30px; }
        .data-atualizacao { text-align: center; color: #666; margin-bottom: 20px; font-style: italic; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #2c3e50; color: white; padding: 12px; text-align: left; cursor: pointer; }
        th:hover { background: #1a252f; }
        th::after { content: ""; float: right; margin-top: 7px; border-width: 5px; border-style: solid; border-color: transparent; }
        th.asc::after { border-bottom-color: white; margin-top: 2px; }
        th.desc::after { border-top-color: white; margin-top: 12px; }
        td { padding: 12px; border-bottom: 1px solid #ddd; }
        tr:hover { background: #f9f9f9; }
        a { color: #2980b9; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .categoria { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: white; }
        .hora { white-space: nowrap; color: #666; }
        .fonte { white-space: nowrap; color: #666; font-weight: bold; }
        .stats { margin-top: 30px; text-align: center; color: #666; }
        
        /* Estilos responsivos para celulares */
        @media (max-width: 768px) {
            body { padding: 10px; }
            .container { padding: 10px; }
            th, td { padding: 8px; }
            th { font-size: 0.9em; }
            td { font-size: 0.9em; }
            .categoria { font-size: 0.8em; }
        }
        
        @media (max-width: 480px) {
            th, td { padding: 6px; }
            th { font-size: 0.8em; }
            td { font-size: 0.8em; }
            .categoria { font-size: 0.7em; padding: 3px 6px; }
        }
    </style>
    <script>
        // Função para ordenar a tabela
        function ordenarTabela(n) {
            const tabela = document.getElementById('tabela-noticias');
            let linhas, i, x, y, trocando = true;
            let direcao = "asc";
            let contador = 0;
            
            // Definir direção da ordenação
            const cabecalho = tabela.getElementsByTagName("TH")[n];
            
            // Limpar todas as classes dos cabeçalhos
            const cabecalhos = tabela.getElementsByTagName("TH");
            for (i = 0; i < cabecalhos.length; i++) {
                cabecalhos[i].classList.remove("asc", "desc");
            }
            
            // Alternar direção se o mesmo cabeçalho for clicado novamente
            if (cabecalho.getAttribute("data-ordem") === "asc") {
                direcao = "desc";
                cabecalho.setAttribute("data-ordem", "desc");
                cabecalho.classList.add("desc");
            } else {
                direcao = "asc";
                cabecalho.setAttribute("data-ordem", "asc");
                cabecalho.classList.add("asc");
            }
            
            // Resetar outros cabeçalhos
            for (i = 0; i < cabecalhos.length; i++) {
                if (i !== n) cabecalhos[i].removeAttribute("data-ordem");
            }
            
            // Loop para ordenar
            while (trocando) {
                trocando = false;
                linhas = tabela.rows;
                
                for (i = 1; i < (linhas.length - 1); i++) {
                    x = linhas[i].getElementsByTagName("TD")[n];
                    y = linhas[i + 1].getElementsByTagName("TD")[n];
                    
                    // Comparar valores
                    if (direcao === "asc" && x.textContent.toLowerCase() > y.textContent.toLowerCase() ||
                        direcao === "desc" && x.textContent.toLowerCase() < y.textContent.toLowerCase()) {
                        // Trocar linhas
                        linhas[i].parentNode.insertBefore(linhas[i + 1], linhas[i]);
                        trocando = true;
                        contador++;
                    }
                }
                
                // Limitar número de trocas para evitar loops infinitos
                if (contador > 1000) break;
            }
        }

        // Script para atualização automática da página sem mostrar contagem
        document.addEventListener('DOMContentLoaded', function() {
            // Calcular o tempo até o próximo minuto exato e configurar recarregamento
            function configurarRecarregamento() {
                const agora = new Date();
                const segundosRestantes = 60 - agora.getSeconds();
                const milissegundosRestantes = segundosRestantes * 1000;
                
                setTimeout(function() {
                    // Salvar posição de rolagem
                    const scrollPos = window.scrollY;
                    sessionStorage.setItem('scrollPos', scrollPos);
                    
                    // Recarregar a página
                    location.reload();
                }, milissegundosRestantes);
            }
            
            // Configurar o recarregamento automático
            configurarRecarregamento();
            
            // Salvar posição de rolagem no sessionStorage antes de recarregar
            window.addEventListener('beforeunload', function() {
                sessionStorage.setItem('scrollPos', window.scrollY);
            });
        });
        
        // Restaurar posição de rolagem após o carregamento da página
        window.addEventListener('load', function() {
            const scrollPos = sessionStorage.getItem('scrollPos');
            if (scrollPos) {
                window.scrollTo(0, parseInt(scrollPos));
            }
        });
    </script>
</head>
<body>
    <div class="container">
        <h1>Monitor de Notícias - Brasil</h1>"""
            
            # Adicionar data e hora
            html_content += f'        <div class="data-atualizacao">Atualizado em: {data_atual} às {hora_atual}</div>\n'
            
            # Adicionar tabela de notícias
            html_content += """        <table id="tabela-noticias">
            <thead>
                <tr>
                    <th onclick="ordenarTabela(0)">Título</th>
                    <th onclick="ordenarTabela(1)">Categoria</th>
                    <th onclick="ordenarTabela(2)">Fonte</th>
                    <th onclick="ordenarTabela(3)">Hora</th>
                </tr>
            </thead>
            <tbody>
"""
            
            # Verificar se o DataFrame está vazio
            if df.empty:
                html_content += "<tr><td colspan='4' style='text-align: center;'>Nenhuma notícia encontrada</td></tr>\n"
            else:
                # Gerar linhas da tabela eficientemente
                for _, noticia in df.iterrows():
                    hora = noticia.get('hora', 'N/D')
                    categoria = noticia.get('categoria', 'Não especificada')
                    titulo = noticia.get('titulo', 'N/D')
                    link = noticia.get('link', '#')
                    
                    # Obter cor da categoria ou usar cor padrão
                    cor_categoria = cores_categorias.get(categoria, cor_padrao)
                    
                    html_content += f"""                <tr>
                    <td><a href='{link}' target='_blank'>{titulo}</a></td>
                    <td><span class='categoria' style='background-color: {cor_categoria};'>{categoria}</span></td>
                    <td class='fonte'>{noticia.get('fonte', 'Desconhecida')}</td>
                    <td class='hora'>{hora}</td>
                </tr>
"""
            
            # Finalizar o HTML
            html_content += f"""            </tbody>
        </table>
        <div class="stats">Total de notícias: {total_noticias}</div>
    </div>
</body>
</html>"""
            
            # Salvar o arquivo HTML com encoding UTF-8 e BOM
            with open('monitor_noticias.html', 'w', encoding='utf-8-sig') as f:
                f.write(html_content)
            
            print("HTML gerado com sucesso")
            return True
        except Exception as e:
            print(f"ERRO ao gerar arquivo HTML: {e}")
            # Tentativa de gerar um HTML muito simples em caso de erro
            try:
                with open('monitor_noticias_erro.html', 'w', encoding='utf-8-sig') as f:
                    f.write(f"<html><body><h1>Erro</h1><p>{e}</p></body></html>")
            except:
                pass
            return False

class EstadaoScraper:
    def __init__(self):
        self.url = "https://www.estadao.com.br/ultimas/"
        self.noticias = []
        self.hoje = datetime.now().strftime("%d/%m/%Y")
        self.titulos_atuais = set()
        self.driver = None
    
    def configurar_driver(self):
        """
        Obtém um driver do pool
        """
        print("Configurando o driver do Microsoft Edge...")
        self.driver = obter_driver()
        return self.driver
    
    def fechar_driver(self):
        """
        Retorna o driver para o pool
        """
        if self.driver:
            retornar_driver(self.driver)
            self.driver = None
            print("Driver do Edge retornado ao pool.")
    
    def obter_pagina(self, url):
        """
        Carrega a página usando o Selenium com timeout otimizado e retry
        """
        try:
            if not carregar_pagina_com_retry(self.driver, url):
                return None
            
            # Aguardar o carregamento dos elementos principais com timeout menor
            WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-component-name='lista-ultimas']"))
            )
            
            return self.driver.page_source
        except Exception as e:
            print(f"Erro ao aguardar elementos da página: {e}")
            return None
    
    def extrair_noticias(self, html):
        """
        Extrai as notícias do HTML usando BeautifulSoup com parada inteligente
        """
        if not html:
            return 0, False
            
        soup = BeautifulSoup(html, 'html.parser')
        artigos = soup.find_all('a', attrs={'data-component-name': 'lista-ultimas'})
        print(f"Encontrados {len(artigos)} artigos na página")
        
        data_atual = self.hoje
        novas_noticias = 0
        noticias_batch = []
        encontrou_noticia_antiga = False
        
        for artigo in artigos:
            try:
                titulo = artigo.get('title', '').strip()
                if not titulo:
                    continue
                
                if titulo in self.titulos_atuais:
                    continue
                    
                link = artigo.get('href', '#')
                categoria = artigo.text.strip()
                
                # Remover duplicatas de categorias
                if categoria and artigo.find_previous('a', attrs={'data-component-name': 'lista-ultimas'}) and artigo.find_previous('a', attrs={'data-component-name': 'lista-ultimas'}).text.strip() == categoria:
                    continue
                
                # Mapear categoria baseado na URL se necessário
                if not categoria or categoria == "" or len(categoria) > 30:
                    url_categories = {
                        '/politica/': 'Política',
                        '/economia/': 'Economia',
                        '/esportes/': 'Esportes',
                        '/cultura/': 'Cultura',
                        '/internacional/': 'Internacional',
                        '/brasil/': 'Brasil',
                        '/tecnologia/': 'Tecnologia',
                        '/futebol/': 'Futebol',
                        '/sao-paulo/': 'São Paulo',
                        '/opiniao/': 'Opinião'
                    }
                    
                    categoria_encontrada = False
                    for url_path, cat_name in url_categories.items():
                        if url_path in link.lower():
                            categoria = cat_name
                            categoria_encontrada = True
                            break
                    
                    if not categoria_encontrada:
                        categoria = "Não especificada"
                
                # Encontrar a data e hora
                data_element = None
                parent_div = artigo.find_parent('div')
                if parent_div:
                    data_element = parent_div.find('span', class_='date')
                
                if not data_element:
                    next_element = artigo.find_next_sibling()
                    if next_element and next_element.name == 'span' and 'date' in next_element.get('class', []):
                        data_element = next_element
                
                if not data_element:
                    continue
                
                data_hora_texto = data_element.text.strip()
                data_match = re.search(r'(\d{2}/\d{2}/\d{4}),\s*(\d{1,2})h(\d{2})', data_hora_texto)
                
                if data_match:
                    data = data_match.group(1)
                    hora = f"{data_match.group(2)}:{data_match.group(3)}"
                    
                    if data != data_atual:
                        # Encontrou notícia antiga - sinalizar para parar
                        encontrou_noticia_antiga = True
                        break
                    
                    noticias_batch.append({
                        'titulo': titulo,
                        'categoria': categoria,
                        'fonte': 'Estadão',
                        'data': data,
                        'hora': hora,
                        'link': link
                    })
                    self.titulos_atuais.add(titulo)
                    novas_noticias += 1
                    
            except Exception as e:
                print(f"Erro ao processar artigo: {e}")
                continue
        
        if noticias_batch:
            self.noticias.extend(noticias_batch)
            print(f"Adicionadas {novas_noticias} novas notícias do Estadão")
                
        return novas_noticias, encontrou_noticia_antiga
    
    def obter_categoria_da_pagina(self, url):
        """
        Acessa a página da notícia para extrair a categoria diretamente da página
        """
        try:
            # Carregar a página da notícia
            self.driver.get(url)
            
            # Aguardar carregamento
            time.sleep(2)
            
            # Tentar várias estratégias para encontrar a categoria
            try:
                # Estratégia 1: Breadcrumb
                breadcrumb = self.driver.find_element(By.CLASS_NAME, 'breadcrumb')
                if breadcrumb:
                    links = breadcrumb.find_elements(By.TAG_NAME, 'a')
                    if links and len(links) > 0:
                        categoria = links[0].text.strip()
                        if categoria and len(categoria) < 30:
                            return categoria
                        
                # Estratégia 2: Header da seção
                section_header = self.driver.find_element(By.CLASS_NAME, 'section-header')
                if section_header:
                    categoria = section_header.text.strip()
                    if categoria and len(categoria) < 30:
                        return categoria
                        
                # Estratégia 3: Meta tag
                meta_keywords = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="keywords"]')
                if meta_keywords:
                    keywords = meta_keywords.get_attribute('content').split(',')
                    if keywords and len(keywords) > 0:
                        categoria = keywords[0].strip()
                        if categoria and len(categoria) < 30:
                            return categoria
            except:
                pass
                
            return "Não especificada"
        except Exception as e:
            print(f"Erro ao acessar página para obter categoria: {e}")
            return "Não especificada"
        
    def clicar_carregar_mais(self):
        """
        Clica no botão 'Carregar mais notícias' para exibir mais artigos
        """
        try:
            # Rolar até o final da página para garantir que o botão seja visível
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Aguardar o scroll terminar
            
            # Tenta remover banners ou elementos que possam estar bloqueando
            try:
                self.driver.execute_script("""
                    // Remover banners
                    var banners = document.querySelectorAll('.banner__container, .banner, [id="banner"]');
                    for(var i=0; i<banners.length; i++) {
                        banners[i].remove();
                    }
                    
                    // Remover navbars fixas
                    var navbars = document.querySelectorAll('.navbar-content');
                    for(var i=0; i<navbars.length; i++) {
                        navbars[i].remove();
                    }
                    
                    // Remover iframe de LGPD
                    var lgpdIframe = document.getElementById('lgpd');
                    if(lgpdIframe) {
                        lgpdIframe.remove();
                    }
                    
                    // Remover qualquer outro iframe que possa estar bloqueando
                    var iframes = document.querySelectorAll('iframe');
                    for(var i=0; i<iframes.length; i++) {
                        iframes[i].remove();
                    }
                    
                    // Remover elementos com posição fixed ou absolute
                    var fixedElements = document.querySelectorAll('*[style*="position: fixed"], *[style*="position:fixed"], *[style*="position: absolute"], *[style*="position:absolute"]');
                    for(var i=0; i<fixedElements.length; i++) {
                        fixedElements[i].remove();
                    }
                    
                    // Ajustar z-index do botão para garantir que esteja no topo
                    var botao = document.querySelector('button.see-more[data-component-name="lista-ultimas"]');
                    if(botao) {
                        botao.style.position = 'relative';
                        botao.style.zIndex = '99999';
                    }
                """)
                print("Elementos bloqueadores removidos")
            except Exception as e:
                print(f"Aviso: Não foi possível remover elementos bloqueadores: {e}")
            
            # Localizar o botão
            botao = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.see-more[data-component-name='lista-ultimas']"))
            )
            
            # Rolar um pouco para cima para evitar a barra de navegação
            self.driver.execute_script("window.scrollBy(0, -150);")
            time.sleep(0.5)
            
            # Tentar clicar diretamente no botão
            try:
                print("Tentando clicar no botão 'Carregar mais notícias'...")
                botao.click()
            except Exception as e:
                print(f"Erro ao clicar diretamente no botão: {e}")
                # Se falhar, usar JavaScript para clicar no botão
                print("Tentando clicar via JavaScript...")
                self.driver.execute_script("arguments[0].click();", botao)
            
            # Aguardar o carregamento de novos artigos
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"Erro ao clicar no botão 'Carregar mais notícias': {e}")
            return False
    
    def extrair_todas_noticias(self, max_cliques=8):  # Reduzido de 10 para 8
        """
        Extrai notícias com parada inteligente quando encontra notícias antigas
        """
        if not self.driver:
            self.configurar_driver()
            
        html = self.obter_pagina(self.url)
        if not html:
            print("Erro: Não foi possível carregar a primeira página do Estadão.")
            return
        
        novas_noticias, encontrou_antiga = self.extrair_noticias(html)
        print(f"Notícias do Estadão encontradas até agora: {len(self.noticias)}")
        
        # Se já encontrou notícia antiga na primeira página, não precisa continuar
        if encontrou_antiga:
            print("Encontradas notícias antigas na primeira página do Estadão. Parando extração.")
            return
        
        cliques_realizados = 0
        cliques_sem_noticias = 0
        
        while cliques_realizados < max_cliques and cliques_sem_noticias < 2:  # Para após 2 cliques sem notícias
            if not self.clicar_carregar_mais():
                print("Não foi possível clicar em 'Carregar mais' ou botão não encontrado.")
                break
            
            # Aguardar carregamento das novas notícias
            time.sleep(2)  # Reduzido de 3 para 2 segundos
            
            html = self.driver.page_source
            novas_noticias, encontrou_antiga = self.extrair_noticias(html)
            
            if encontrou_antiga:
                print(f"Encontradas notícias antigas após {cliques_realizados + 1} cliques no Estadão. Parando extração.")
                break
                
            if novas_noticias == 0:
                cliques_sem_noticias += 1
                print(f"Nenhuma nova notícia após clique {cliques_realizados + 1}. Tentativa {cliques_sem_noticias}/2")
            else:
                cliques_sem_noticias = 0
                print(f"Notícias do Estadão encontradas até agora: {len(self.noticias)}")
            
            cliques_realizados += 1
        
        print(f"Extração do Estadão finalizada após {cliques_realizados} cliques. Total: {len(self.noticias)} notícias")
    
    def salvar_noticias(self):
        """
        Salva as notícias extraídas em formato JSON
        """
        # Verificar se temos notícias
        if not self.noticias:
            print("Nenhuma notícia foi encontrada para salvar.")
            df = pd.DataFrame(columns=['titulo', 'categoria', 'fonte', 'data', 'hora', 'link'])
            return df
            
        # Criar DataFrame das notícias
        df = pd.DataFrame(self.noticias)
        
        # Remover duplicatas
        df = df.drop_duplicates(subset=['titulo'])
        
        # Ordenar por hora (mais recente primeiro)
        if 'hora' in df.columns:
            try:
                df['data_hora'] = pd.to_datetime(df['data'] + ' ' + df['hora'], format='%d/%m/%Y %H:%M', errors='coerce')
                df = df.sort_values(by='data_hora', ascending=False)
                df = df.drop('data_hora', axis=1)
            except Exception as e:
                print(f"Erro ao ordenar por hora: {e}")
        
        # Salvar em formato JSON
        try:
            df.to_json('noticias_estadao.json', orient='records', force_ascii=False)
            print(f"Dados salvos em noticias_estadao.json")
        except Exception as e:
            print(f"Erro ao salvar JSON: {e}")
            
        return df

class FolhaScraper:
    def __init__(self):
        self.url = "https://www1.folha.uol.com.br/ultimas-noticias/"
        self.noticias = []
        self.hoje = datetime.now().strftime("%d/%m/%Y")
        self.titulos_atuais = set()
        self.driver = None
    
    def configurar_driver(self):
        """
        Obtém um driver do pool
        """
        print("Configurando o driver do Microsoft Edge...")
        self.driver = obter_driver()
        return self.driver
    
    def fechar_driver(self):
        """
        Retorna o driver para o pool
        """
        if self.driver:
            retornar_driver(self.driver)
            self.driver = None
            print("Driver do Edge retornado ao pool.")
    
    def obter_pagina(self, url):
        """
        Carrega a página usando o Selenium e retorna o conteúdo HTML
        """
        try:
            print(f"Carregando a página da Folha: {url}")
            self.driver.get(url)
            
            # Aguardar o carregamento dos elementos principais
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "c-main-headline__title"))
            )
            
            # Retornar o HTML da página
            return self.driver.page_source
        except Exception as e:
            print(f"Erro ao carregar página da Folha: {e}")
            return None
    
    def extrair_noticias(self, html):
        """
        Extrai as notícias do HTML usando BeautifulSoup
        """
        if not html:
            return 0
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Data atual para filtrar notícias
        data_atual = self.hoje
        
        novas_noticias = 0
        noticias_batch = []
        
        # 1. Encontrar a notícia principal (main headline)
        main_headline = soup.find('a', class_='c-main-headline__url')
        if main_headline:
            try:
                # Extrair título diretamente
                titulo_element = main_headline.find('h2', class_='c-main-headline__title')
                if titulo_element:
                    titulo = titulo_element.text.strip()
                    
                    # Verificar se o título já existe
                    if titulo not in self.titulos_atuais:
                        # Extrair link diretamente do atributo href
                        link = main_headline['href']
                        
                        # Determinar a fonte
                        fonte = 'Folha de S.Paulo'
                        
                        # Extrair categoria - procurar no elemento principal ou na URL
                        categoria = "Não especificada"
                        
                        # Primeiro, tentar encontrar a categoria no link da editoria
                        section_element = None
                        parent_section = main_headline.find_parent('section')
                        if parent_section:
                            # Buscar link de editoria direto na seção
                            section_element = parent_section.find('a', href=re.compile(r"folha\.uol\.com\.br/[^/]+/$"))
                        
                        if section_element:
                            # Extrair o texto direto
                            categoria_text = section_element.get_text().strip()
                            # Remover comentários HTML
                            categoria = re.sub(r'<!--.*?-->', '', categoria_text).strip()
                            print(f"Categoria encontrada para notícia principal: '{categoria}'")
                        else:
                            # Se não encontrou, usar método padrão baseado na URL
                            url_match = re.search(r'folha\.uol\.com\.br/([^/]+)/', link)
                            if url_match:
                                categoria_url = url_match.group(1)
                                # Mapear categorias da URL
                                categorias_map = {
                                    'poder': 'Política',
                                    'mercado': 'Economia', 
                                    'cotidiano': 'Cotidiano',
                                    'mundo': 'Mundo',
                                    'esporte': 'Esporte',
                                    'ilustrada': 'Cultura',
                                    'f5': 'Entretenimento',
                                    'ambiente': 'Ambiente',
                                    'ciencia': 'Ciência',
                                    'equilibrioesaude': 'Saúde',
                                    'educacao': 'Educação',
                                    'tecnologia': 'Tecnologia',
                                    'ilustrissima': 'Ilustríssima',
                                    'comida': 'Gastronomia',
                                    'tec': 'Tecnologia',
                                    'podcasts': 'Podcasts',
                                    'folhinha': 'Folhinha',
                                    'empreendedorismo': 'Empreendedorismo'
                                }
                                categoria = categorias_map.get(categoria_url, categoria_url.replace('-', ' ').title())
                        
                        # Extrair data e hora da notícia principal
                        data_element = main_headline.find('time', class_='c-headline__dateline')
                        if data_element:
                            data_hora_texto = data_element.text.strip()
                            
                            # Extrair data e hora do formato "25.abr.2025 às 12h22"
                            data_match = re.search(r'(\d{2})\.(\w{3})\.(\d{4})\s+às\s+(\d{1,2})h(\d{2})', data_hora_texto)
                            if data_match:
                                dia = data_match.group(1)
                                mes_texto = data_match.group(2).lower()
                                ano = data_match.group(3)
                                hora = data_match.group(4)
                                minuto = data_match.group(5)
                                
                                # Converter nome do mês para número
                                meses = {
                                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                                    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                                    'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                                }
                                
                                if mes_texto in meses:
                                    mes = meses[mes_texto]
                                    data_formatada = f"{dia}/{mes}/{ano}"
                                    hora_formatada = f"{hora}:{minuto}"
                                    
                                    # Adicionar à lista
                                    noticias_batch.append({
                                        'titulo': titulo,
                                        'categoria': categoria,
                                        'fonte': fonte,
                                        'data': data_formatada,
                                        'hora': hora_formatada,
                                        'link': link
                                    })
                                    self.titulos_atuais.add(titulo)
                                    novas_noticias += 1
                                    print(f"Notícia principal adicionada: {titulo[:50]}...")
            except Exception as e:
                print(f"Erro ao processar notícia principal da Folha: {e}")
        
        # 2. Encontrar as notícias secundárias (headlines normais)
        artigos = soup.find_all('a', href=re.compile(r"folha\.uol\.com\.br/.*\.shtml"))
        print(f"Encontrados {len(artigos)} artigos na página da Folha")
        
        for artigo in artigos:
            try:
                # Verificar se é um link de notícia válido (contém título)
                titulo_element = artigo.find('h2', class_='c-headline__title')
                if not titulo_element:
                    # Talvez seja a notícia principal que já processamos
                    continue
                
                # Extrair título
                titulo = titulo_element.text.strip()
                
                # Verificar se o título já existe na lista de notícias
                if titulo in self.titulos_atuais:
                    continue
                
                # Extrair link
                link = artigo['href']
                
                # Determinar a fonte
                fonte = 'Folha de S.Paulo'
                
                # Extrair categoria - método melhorado
                categoria = self.extrair_categoria_folha(artigo, link)
                
                # Extrair data e hora
                data_element = artigo.find('time', class_='c-headline__dateline')
                if not data_element:
                    continue
                
                data_hora_texto = data_element.text.strip()
                
                # Extrair data e hora do formato "25.abr.2025 às 12h22"
                data_match = re.search(r'(\d{2})\.(\w{3})\.(\d{4})\s+às\s+(\d{1,2})h(\d{2})', data_hora_texto)
                if data_match:
                    dia = data_match.group(1)
                    mes_texto = data_match.group(2).lower()
                    ano = data_match.group(3)
                    hora = data_match.group(4)
                    minuto = data_match.group(5)
                    
                    # Converter nome do mês para número
                    meses = {
                        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                    }
                    
                    if mes_texto in meses:
                        mes = meses[mes_texto]
                        data_formatada = f"{dia}/{mes}/{ano}"
                        hora_formatada = f"{hora}:{minuto}"
                        
                        # Verificar se a notícia é do dia atual
                        # Para teste, vamos pegar todas as notícias, independente da data
                        # if data_formatada != data_atual:
                        #     continue
                        
                        # Adicionar à lista temporária
                        noticias_batch.append({
                            'titulo': titulo,
                            'categoria': categoria,
                            'fonte': fonte,
                            'data': data_formatada,
                            'hora': hora_formatada,
                            'link': link
                        })
                        self.titulos_atuais.add(titulo)
                        novas_noticias += 1
            except Exception as e:
                print(f"Erro ao processar artigo da Folha: {e}")
                continue
        
        # Adicionar o lote de notícias à lista principal
        if noticias_batch:
            self.noticias.extend(noticias_batch)
            print(f"Adicionadas {novas_noticias} novas notícias da Folha")
                
        return novas_noticias
    
    def extrair_categoria_folha(self, artigo_element, link):
        """
        Método especializado para extrair a categoria de notícias da Folha
        """
        categoria = "Não especificada"
        
        # 1. Tentar encontrar link de categoria próximo (com padrão folha-topicos)
        try:
            # Buscar em todo o documento, mas primeiro próximo ao elemento
            categoria_elements = []
            
            # Procurar no próprio elemento e seus pais
            parent = artigo_element.parent
            while parent and parent.name != 'body':
                # Procurar em irmãos ou filhos dos pais também
                for sibling in parent.find_all_previous('a', href=re.compile(r"folha\.uol\.com\.br/folha-topicos/"), limit=3):
                    categoria_elements.append(sibling)
                parent = parent.parent
            
            # Procurar também por links diretos de seção
            kicker_elements = artigo_element.find_previous('h3', class_='c-headline__kicker')
            if kicker_elements:
                categoria_text = kicker_elements.text.strip()
                # Remover comentários e espaços extras
                categoria = re.sub(r'<!--.*?-->', '', categoria_text).strip()
                if categoria:
                    return categoria
            
            # Se encontrou elementos de categoria
            if categoria_elements:
                # Pegar o primeiro elemento e extrair o texto real (sem comentários)
                categoria_text = categoria_elements[0].get_text().strip()
                # Remover comentários HTML e espaços extras
                categoria = re.sub(r'<!--.*?-->', '', categoria_text).strip()
                if categoria:
                    return categoria
        except Exception as e:
            print(f"Erro ao buscar categoria por link: {e}")
        
        # 2. Tentar extrair da URL, usando o padrão de editoria ou folha-topicos
        try:
            # Verificar se é um link de tópico específico
            topic_match = re.search(r'folha\.uol\.com\.br/folha-topicos/([^/]+)/', link)
            if topic_match:
                return topic_match.group(1).replace('-', ' ').title()
            
            # Verificar se é um link de editoria normal
            url_match = re.search(r'folha\.uol\.com\.br/([^/]+)/', link)
            if url_match:
                categoria_url = url_match.group(1)
                # Mapear categorias da URL
                categorias_map = {
                    'poder': 'Política',
                    'mercado': 'Economia', 
                    'cotidiano': 'Cotidiano',
                    'mundo': 'Mundo',
                    'esporte': 'Esporte',
                    'ilustrada': 'Cultura',
                    'f5': 'Entretenimento',
                    'ambiente': 'Ambiente',
                    'ciencia': 'Ciência',
                    'equilibrioesaude': 'Saúde',
                    'educacao': 'Educação',
                    'tecnologia': 'Tecnologia',
                    'ilustrissima': 'Ilustríssima',
                    'comida': 'Gastronomia',
                    'tec': 'Tecnologia',
                    'podcasts': 'Podcasts',
                    'folhinha': 'Folhinha',
                    'empreendedorismo': 'Empreendedorismo'
                }
                categoria = categorias_map.get(categoria_url, categoria_url.replace('-', ' ').title())
                if categoria:
                    return categoria
        except Exception as e:
            print(f"Erro ao extrair categoria da URL: {e}")
        
        return categoria
    
    def clicar_ver_mais(self):
        """
        Clica no botão 'Ver mais' para exibir mais artigos
        """
        try:
            # Rolar até o final da página para garantir que o botão seja visível
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Aguardar o scroll terminar
            
            # Tenta remover banners ou elementos que possam estar bloqueando
            try:
                self.driver.execute_script("""
                    // Remover banners
                    var banners = document.querySelectorAll('.banner, [id*="banner"], [class*="banner"], [class*="lgpd"], [id*="lgpd"]');
                    for(var i=0; i<banners.length; i++) {
                        banners[i].remove();
                    }
                    
                    // Remover elementos com posição fixed ou absolute
                    var fixedElements = document.querySelectorAll('*[style*="position: fixed"], *[style*="position:fixed"], *[style*="position: absolute"], *[style*="position:absolute"]');
                    for(var i=0; i<fixedElements.length; i++) {
                        fixedElements[i].remove();
                    }
                """)
                print("Elementos bloqueadores removidos da página da Folha")
            except Exception as e:
                print(f"Aviso: Não foi possível remover elementos bloqueadores: {e}")
            
            # Verificar se o botão existe
            botoes = self.driver.find_elements(By.CSS_SELECTOR, "button.c-button--expand[data-pagination-trigger]")
            if not botoes:
                print("Botão 'Ver mais' não encontrado na página da Folha")
                return False
                
            botao = botoes[0]
            print(f"Botão 'Ver mais' encontrado: {botao.text}")
            
            # Rolar para o botão
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
            time.sleep(1)
            
            # Tentar clicar diretamente no botão
            try:
                print("Tentando clicar no botão 'Ver mais' da Folha...")
                botao.click()
                print("Clique realizado com sucesso")
            except Exception as e:
                print(f"Erro ao clicar diretamente no botão da Folha: {e}")
                # Se falhar, usar JavaScript para clicar no botão
                print("Tentando clicar via JavaScript...")
                self.driver.execute_script("arguments[0].click();", botao)
                print("Clique via JavaScript realizado")
            
            # Aguardar o carregamento de novos artigos
            time.sleep(3)
            
            return True
        except Exception as e:
            print(f"Erro ao clicar no botão 'Ver mais' da Folha: {e}")
            return False
    
    def extrair_todas_noticias(self, max_cliques=8):
        """
        Extrai notícias clicando no botão 'Ver mais' várias vezes
        
        Args:
            max_cliques: Número máximo de vezes para clicar no botão
        """
        # Carregar a primeira página
        html = self.obter_pagina(self.url)
        if not html:
            print("Não foi possível carregar a página inicial da Folha.")
            return
        
        # Extrair notícias da primeira página
        novas_noticias = self.extrair_noticias(html)
        print(f"Notícias encontradas na página inicial da Folha: {novas_noticias}")
        
        # Clique no botão "Ver mais" várias vezes
        cliques_realizados = 0
        tentativas_sem_novas = 0
        
        while cliques_realizados < max_cliques:
            # Clicar no botão para carregar mais notícias
            if self.clicar_ver_mais():
                # Extrair as novas notícias carregadas
                novas_noticias = self.extrair_noticias(self.driver.page_source)
                cliques_realizados += 1
                
                print(f"Clique {cliques_realizados}/{max_cliques} realizado na Folha.")
                
                if novas_noticias > 0:
                    print(f"Notícias da Folha encontradas até agora: {len(self.noticias)}")
                    tentativas_sem_novas = 0
                else:
                    tentativas_sem_novas += 1
                    print(f"Nenhuma nova notícia após o clique {cliques_realizados}. Tentativa {tentativas_sem_novas}/3")
                    
                    # Se não encontrarmos novas notícias em 3 tentativas consecutivas, paramos
                    if tentativas_sem_novas >= 3:
                        print("Três tentativas sem novas notícias da Folha. Finalizando.")
                        break
            else:
                print("Não foi possível carregar mais notícias da Folha. Finalizando.")
                break
            
            # Pequena pausa para não sobrecarregar o site
            time.sleep(1)
                
        print(f"Extração da Folha finalizada após {cliques_realizados} cliques. Total: {len(self.noticias)} notícias")
    
    def salvar_noticias(self):
        """
        Salva as notícias extraídas em formato JSON
        """
        # Verificar se temos notícias
        if not self.noticias:
            print("Nenhuma notícia da Folha foi encontrada para salvar.")
            df = pd.DataFrame(columns=['titulo', 'categoria', 'fonte', 'data', 'hora', 'link'])
            return df
            
        # Criar DataFrame das notícias
        df = pd.DataFrame(self.noticias)
        
        # Remover duplicatas
        df = df.drop_duplicates(subset=['titulo'])
        
        # Ordenar por hora (mais recente primeiro)
        if 'hora' in df.columns:
            try:
                df['data_hora'] = pd.to_datetime(df['data'] + ' ' + df['hora'], format='%d/%m/%Y %H:%M', errors='coerce')
                df = df.sort_values(by='data_hora', ascending=False)
                df = df.drop('data_hora', axis=1)
            except Exception as e:
                print(f"Erro ao ordenar por hora: {e}")
        
        # Salvar em formato JSON
        try:
            df.to_json('noticias_folha.json', orient='records', force_ascii=False)
            print(f"Dados da Folha salvos em noticias_folha.json")
        except Exception as e:
            print(f"Erro ao salvar JSON da Folha: {e}")
            
        return df

class OGloboScraper:
    def __init__(self):
        self.url = "https://oglobo.globo.com/ultimas-noticias/"
        self.noticias = []
        self.hoje = datetime.now().strftime("%d/%m/%Y")
        self.titulos_atuais = set()
        self.driver = None
    
    def configurar_driver(self):
        """
        Obtém um driver do pool
        """
        print("Configurando o driver do Microsoft Edge...")
        self.driver = obter_driver()
        return self.driver
    
    def fechar_driver(self):
        """
        Retorna o driver para o pool
        """
        if self.driver:
            retornar_driver(self.driver)
            self.driver = None
            print("Driver do Edge retornado ao pool.")
    
    def obter_pagina(self, url):
        """
        Carrega a página usando o Selenium com retry e retorna o conteúdo HTML
        """
        try:
            print(f"Carregando a página de O Globo: {url}")
            
            # Usar a função de retry com timeout maior específico para O Globo
            if not carregar_pagina_com_retry(self.driver, url, max_tentativas=4, timeout=30):
                return None
            
            # Aguardar o carregamento dos elementos principais com timeout maior
            WebDriverWait(self.driver, 25).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
            )
            
            # Aguardar um pouco mais para garantir carregamento completo
            time.sleep(3)
            
            # Retornar o HTML da página
            return self.driver.page_source
        except Exception as e:
            print(f"Erro ao carregar página de O Globo: {e}")
            return None
            
    def calcular_tempo_absoluto(self, tempo_relativo):
        """
        Converte o tempo relativo (ex: 'Há 5 minutos') para data e hora absolutas.
        Retorna uma tupla (data_formatada, hora_formatada) ou (None, None) se falhar.
        """
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
                # Tentar extrair data e hora se for um formato diferente
                # Exemplo: 25/04/2025 às 13:30 (se houver)
                match = re.search(r'(\d{2}/\d{2}/\d{4})[\s às]+(\d{2}:\d{2})', tempo_relativo)
                if match:
                    return match.group(1), match.group(2)
                else:
                     print(f"Formato de tempo relativo não reconhecido: {tempo_relativo}")
                     return None, None # Formato não reconhecido

            # Verificar se a data calculada é de hoje
            data_calculada_str = tempo_calculado.strftime("%d/%m/%Y")
            if data_calculada_str != self.hoje:
                 print(f"Notícia de data anterior encontrada ({data_calculada_str}), ignorando.")
                 return None, None # Notícia de dia anterior

            return tempo_calculado.strftime("%d/%m/%Y"), tempo_calculado.strftime("%H:%M")
        except Exception as e:
            print(f"Erro ao calcular tempo absoluto para '{tempo_relativo}': {e}")
            return None, None

    def extrair_noticias(self, html):
        """
        Extrai as notícias do HTML usando BeautifulSoup
        """
        if not html:
            return 0
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Encontrar todos os artigos de notícias (baseado na estrutura do Valor)
        artigos = soup.find_all('div', class_='feed-post-body')
        print(f"Encontrados {len(artigos)} artigos na página de O Globo")
        
        novas_noticias = 0
        noticias_batch = []
        
        for artigo in artigos:
            try:
                # Extrair título e link
                link_element = artigo.find('a', class_='feed-post-link')
                if not link_element:
                    continue
                    
                titulo = link_element.text.strip()
                link = link_element['href']
                
                # Verificar se o título já existe
                if titulo in self.titulos_atuais:
                    continue
                
                # Extrair categoria
                categoria_element = artigo.find('span', class_='feed-post-metadata-section')
                categoria = categoria_element.text.strip() if categoria_element else "Não especificada"
                
                # Extrair tempo relativo
                tempo_element = artigo.find('span', class_='feed-post-datetime')
                if not tempo_element:
                    continue
                
                tempo_relativo = tempo_element.text.strip()
                
                # Calcular data e hora absolutas
                data_abs, hora_abs = self.calcular_tempo_absoluto(tempo_relativo)
                
                if data_abs is None or hora_abs is None:
                    # Se não conseguiu calcular ou é de dia anterior, pula para a próxima
                    continue 
                
                # Adicionar à lista temporária
                noticias_batch.append({
                    'titulo': titulo,
                    'categoria': categoria,
                    'fonte': 'O Globo',
                    'data': data_abs,
                    'hora': hora_abs,
                    'link': link
                })
                self.titulos_atuais.add(titulo)
                novas_noticias += 1
            except Exception as e:
                print(f"Erro ao processar artigo de O Globo: {e}")
                continue
        
        # Adicionar o lote de notícias à lista principal
        if noticias_batch:
            self.noticias.extend(noticias_batch)
            print(f"Adicionadas {novas_noticias} novas notícias de O Globo")
                
        return novas_noticias
    
    def navegar_para_proxima_pagina(self, pagina_atual):
        """
        Navega diretamente para a próxima página usando URL com retry
        """
        try:
            # Construir a URL para a próxima página
            proxima_pagina = pagina_atual + 1
            url_proxima = f"https://oglobo.globo.com/ultimas-noticias/index/feed/pagina-{proxima_pagina}.ghtml"
            # Note a extensão .ghtml, diferente do Valor
            
            print(f"Navegando para página {proxima_pagina} de O Globo: {url_proxima}")
            
            # Usar a função de retry com timeout maior
            if not carregar_pagina_com_retry(self.driver, url_proxima, max_tentativas=4, timeout=30):
                return False
            
            # Verificar se a página carregou corretamente com timeout maior
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
            )
            return True
        except Exception as e:
            # Verificar se o erro é por página não encontrada (fim da paginação)
            if "net::ERR_ABORTED" in str(e) or "StatusCode.NOT_FOUND" in str(e) or "TimeoutException" in str(e):
                 print(f"Página {proxima_pagina} não encontrada ou não carregou a tempo. Fim da paginação?")
            else:
                print(f"Erro ao navegar para a próxima página de O Globo: {e}")
            return False
    
    def extrair_todas_noticias(self, max_paginas=15):
        """
        Extrai notícias de várias páginas usando navegação direta
        """
        # Carregar a primeira página
        html = self.obter_pagina(self.url)
        if not html:
            print("Não foi possível carregar a página inicial de O Globo.")
            return
        
        # Extrair notícias da primeira página
        self.extrair_noticias(html)
        print(f"Notícias de O Globo encontradas até agora: {len(self.noticias)}")
        
        # Carregar mais páginas navegando diretamente para as URLs
        pagina_atual = 1
        tentativas_sem_novas = 0
        
        while pagina_atual < max_paginas:
            if self.navegar_para_proxima_pagina(pagina_atual):
                novas_noticias = self.extrair_noticias(self.driver.page_source)
                pagina_atual += 1
                
                if novas_noticias > 0:
                    print(f"Notícias de O Globo encontradas até agora: {len(self.noticias)}")
                    tentativas_sem_novas = 0
                else:
                    tentativas_sem_novas += 1
                    print(f"Nenhuma nova notícia na página {pagina_atual} de O Globo. Tentativa {tentativas_sem_novas}/2")
                    if tentativas_sem_novas >= 2:
                        print("Duas tentativas sem novas notícias de O Globo. Finalizando.")
                        break
            else:
                print("Não foi possível carregar mais páginas de O Globo. Finalizando.")
                break
                
        print(f"Extração de O Globo finalizada após verificar {pagina_atual} páginas. Total: {len(self.noticias)} notícias")
    
    def salvar_noticias(self):
        """
        Salva as notícias extraídas em formato JSON
        """
        # Verificar se temos notícias
        if not self.noticias:
            print("Nenhuma notícia de O Globo foi encontrada para salvar.")
            df = pd.DataFrame(columns=['titulo', 'categoria', 'fonte', 'data', 'hora', 'link'])
            return df
            
        # Criar DataFrame das notícias
        df = pd.DataFrame(self.noticias)
        
        # Remover duplicatas
        df = df.drop_duplicates(subset=['titulo'])
        
        # Ordenar por hora (mais recente primeiro)
        if 'hora' in df.columns:
            try:
                df['data_hora'] = pd.to_datetime(df['data'] + ' ' + df['hora'], format='%d/%m/%Y %H:%M', errors='coerce')
                df = df.sort_values(by='data_hora', ascending=False)
                df = df.drop('data_hora', axis=1)
            except Exception as e:
                print(f"Erro ao ordenar notícias de O Globo por hora: {e}")
        
        # Salvar em formato JSON
        try:
            df.to_json('noticias_oglobo.json', orient='records', force_ascii=False)
            print(f"Dados de O Globo salvos em noticias_oglobo.json")
        except Exception as e:
            print(f"Erro ao salvar JSON de O Globo: {e}")
            
        return df

def extrair_noticias_valor():
    """
    Função otimizada para extrair notícias do Valor Econômico
    """
    print("Iniciando extração de notícias do Valor Econômico...")
    scraper = ValorEconomicoScraper()
    try:
        scraper.configurar_driver()
        scraper.extrair_todas_noticias()
        df = scraper.salvar_noticias()
        print(f"Extração de Valor Econômico concluída. Foram encontradas {len(scraper.noticias)} notícias.")
        return df
    except Exception as e:
        print(f"Erro na extração do Valor Econômico: {e}")
        return None
    finally:
        scraper.fechar_driver()

def extrair_noticias_estadao():
    """
    Função otimizada para extrair notícias do Estadão
    """
    print("Iniciando extração de notícias do Estadão...")
    scraper = EstadaoScraper()
    try:
        scraper.configurar_driver()
        scraper.extrair_todas_noticias(max_cliques=8)  # Reduzido de 10 para 8
        df = scraper.salvar_noticias()
        print(f"Extração de Estadão concluída. Foram encontradas {len(scraper.noticias)} notícias.")
        return df
    except Exception as e:
        print(f"Erro na extração do Estadão: {e}")
        return None
    finally:
        scraper.fechar_driver()

def extrair_noticias_folha():
    """
    Função otimizada para extrair notícias da Folha
    """
    print("Iniciando extração de notícias da Folha...")
    scraper = FolhaScraper()
    try:
        scraper.configurar_driver()
        scraper.extrair_todas_noticias(max_cliques=8)  # Reduzido de 10 para 8
        df = scraper.salvar_noticias()
        print(f"Extração de Folha concluída. Foram encontradas {len(scraper.noticias)} notícias.")
        return df
    except Exception as e:
        print(f"Erro na extração da Folha: {e}")
        return None
    finally:
        scraper.fechar_driver()

def extrair_noticias_oglobo():
    """
    Função otimizada para extrair notícias de O Globo
    """
    print("Iniciando extração de notícias de O Globo...")
    scraper = OGloboScraper()
    try:
        scraper.configurar_driver()
        scraper.extrair_todas_noticias(max_paginas=10)  # Reduzido de 15 para 10
        df = scraper.salvar_noticias()
        print(f"Extração de O Globo concluída. Foram encontradas {len(scraper.noticias)} notícias.")
        return df
    except Exception as e:
        print(f"Erro na extração de O Globo: {e}")
        return None
    finally:
        scraper.fechar_driver()

def extrair_todas_noticias(modo_rapido=False):
    """
    Extrai notícias de todas as fontes em paralelo para maior eficiência
    
    Args:
        modo_rapido: Se True, reduz o número de páginas/cliques para atualizações mais frequentes
    """
    print("=== INICIANDO EXTRAÇÃO PARALELA DE NOTÍCIAS ===")
    if modo_rapido:
        print("Modo rápido ativado - menos páginas por fonte")
    
    start_time = time.time()
    
    # Ajustar parâmetros baseado no modo
    max_paginas = 5 if modo_rapido else 10
    max_cliques = 4 if modo_rapido else 8
    
    # Lista de funções de extração com parâmetros otimizados
    def extrair_valor_otimizado():
        scraper = ValorEconomicoScraper()
        try:
            scraper.configurar_driver()
            scraper.extrair_todas_noticias(max_paginas=max_paginas)
            df = scraper.salvar_noticias()
            print(f"Extração de Valor Econômico concluída. Foram encontradas {len(scraper.noticias)} notícias.")
            return df
        except Exception as e:
            print(f"Erro na extração do Valor Econômico: {e}")
            return None
        finally:
            scraper.fechar_driver()
    
    def extrair_estadao_otimizado():
        scraper = EstadaoScraper()
        try:
            scraper.configurar_driver()
            scraper.extrair_todas_noticias(max_cliques=max_cliques)
            df = scraper.salvar_noticias()
            print(f"Extração de Estadão concluída. Foram encontradas {len(scraper.noticias)} notícias.")
            return df
        except Exception as e:
            print(f"Erro na extração do Estadão: {e}")
            return None
        finally:
            scraper.fechar_driver()
    
    def extrair_folha_otimizado():
        scraper = FolhaScraper()
        try:
            scraper.configurar_driver()
            scraper.extrair_todas_noticias(max_cliques=max_cliques)
            df = scraper.salvar_noticias()
            print(f"Extração de Folha concluída. Foram encontradas {len(scraper.noticias)} notícias.")
            return df
        except Exception as e:
            print(f"Erro na extração da Folha: {e}")
            return None
        finally:
            scraper.fechar_driver()
    
    def extrair_oglobo_otimizado():
        scraper = OGloboScraper()
        try:
            scraper.configurar_driver()
            scraper.extrair_todas_noticias(max_paginas=max_paginas)
            df = scraper.salvar_noticias()
            print(f"Extração de O Globo concluída. Foram encontradas {len(scraper.noticias)} notícias.")
            return df
        except Exception as e:
            print(f"Erro na extração de O Globo: {e}")
            return None
        finally:
            scraper.fechar_driver()
    
    funcoes_extracao = [
        extrair_valor_otimizado,
        extrair_estadao_otimizado,
        extrair_folha_otimizado,
        extrair_oglobo_otimizado
    ]
    
    # Executar extrações em paralelo
    resultados = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Submeter todas as tarefas
        futures = [executor.submit(func) for func in funcoes_extracao]
        
        # Coletar resultados conforme completam
        for future in concurrent.futures.as_completed(futures):
            try:
                resultado = future.result(timeout=180 if modo_rapido else 300)  # Timeout menor no modo rápido
                if resultado is not None and not resultado.empty:
                    resultados.append(resultado)
            except concurrent.futures.TimeoutError:
                print("Timeout em um dos scrapers - continuando com os outros")
            except Exception as e:
                print(f"Erro em um dos scrapers: {e}")
    
    # Combinar os dataframes
    if resultados:
        df_combinado = pd.concat(resultados, ignore_index=True)
        
        # Remover duplicatas (caso haja notícias com títulos idênticos)
        df_combinado = df_combinado.drop_duplicates(subset=['titulo'])
        
        # Ordenar por data e hora (mais recente primeiro)
        try:
            df_combinado['data_hora'] = pd.to_datetime(df_combinado['data'] + ' ' + df_combinado['hora'], format='%d/%m/%Y %H:%M', errors='coerce')
            # Remover linhas onde a data/hora não pôde ser convertida
            df_combinado = df_combinado.dropna(subset=['data_hora'])
            df_combinado = df_combinado.sort_values(by='data_hora', ascending=False)
            df_combinado = df_combinado.drop('data_hora', axis=1)
        except Exception as e:
            print(f"Erro ao ordenar dataframe combinado por hora: {e}")
        
        # Salvar o dataframe combinado
        try:
            df_combinado.to_json('noticias_combinadas.json', orient='records', force_ascii=False)
            print(f"Dados combinados salvos em noticias_combinadas.json")
        except Exception as e:
            print(f"Erro ao salvar JSON combinado: {e}")
        
        # Gerar HTML com as notícias combinadas
        gerar_html_completo(df_combinado)
        
        end_time = time.time()
        tempo_total = end_time - start_time
        print(f"Total de notícias combinadas: {len(df_combinado)}")
        print(f"Tempo total de execução: {tempo_total:.2f} segundos")
        
        # Limpar pool de drivers
        limpar_pool_drivers()
        
        return df_combinado
    else:
        print("Não foi possível combinar as notícias, pois nenhum scraper retornou dados válidos.")
        # Gerar HTML vazio ou com mensagem de erro
        gerar_html_completo(pd.DataFrame(columns=['titulo', 'categoria', 'fonte', 'data', 'hora', 'link'])) 
        
        # Limpar pool de drivers
        limpar_pool_drivers()
        
        return None

def limpar_pool_drivers():
    """
    Limpa o pool de drivers fechando todos
    """
    with driver_lock:
        while driver_pool:
            driver = driver_pool.pop()
            try:
                driver.quit()
            except:
                pass
        print("Pool de drivers limpo.")

def gerar_html_completo(df):
    """
    Gera um arquivo HTML com a tabela de notícias de todas as fontes
    """
    try:
        # Obter data e hora atual
        data_atual = datetime.now().strftime("%d/%m/%Y")
        hora_atual = datetime.now().strftime("%H:%M:%S")
        total_noticias = len(df)
        
        # Criar um conjunto de categorias para atribuir cores diferentes
        categorias = set()
        for _, noticia in df.iterrows():
            categoria = noticia.get('categoria', 'Não especificada')
            categorias.add(categoria)
            
        # Mapa de cores amigáveis expandido para categorias
        cores_categorias = {
            'Empresas': '#4CAF50',        # Verde
            'Política': '#2196F3',        # Azul
            'Brasil': '#FF9800',          # Laranja
            'Finanças': '#9C27B0',        # Roxo
            'Mundo': '#E91E63',           # Rosa
            'Agronegócios': '#8BC34A',    # Verde claro
            'Carreira': '#00BCD4',        # Ciano
            'Tecnologia': '#673AB7',      # Índigo
            'Legislação': '#795548',      # Marrom
            'Opinião': '#607D8B',         # Azul acinzentado
            'Não especificada': '#9E9E9E', # Cinza
            'Futebol': '#FF5722',         # Laranja escuro
            'Esportes': '#FF5722',        # Laranja escuro
            'Cultura': '#009688',         # Verde-azulado
            'Educação': '#3F51B5',        # Índigo
            'Saúde': '#F44336',           # Vermelho
            'Internacional': '#E91E63',   # Rosa
            'Economia': '#FFC107',        # Amarelo
            'Eleições': '#03A9F4',        # Azul claro
            'Celebridades': '#D500F9',    # Roxo claro
            'Ciência': '#00BFA5',         # Turquesa
            'Automóveis': '#827717',      # Verde oliva
            'Entretenimento': '#FF4081',  # Rosa claro
            'Negócios': '#1976D2',        # Azul escuro
            'Sustentabilidade': '#388E3C', # Verde escuro
            'São Paulo': '#C62828',       # Vermelho escuro
            'Rio de Janeiro': '#6A1B9A',  # Roxo escuro
            'História': '#37474F',        # Cinza escuro
            'Televisão': '#D81B60',       # Magenta
            'Mídia e Marketing': '#7B1FA2' # Roxo médio
        }
        
        # Cor padrão para categorias não mapeadas
        cor_padrao = '#9E9E9E' # Cinza
        
        # Gerar cores aleatórias para categorias que não estão no mapa
        for categoria in categorias:
            if categoria not in cores_categorias:
                # Gerar cor HSL para garantir boa saturação e luminosidade
                h = random.randint(0, 360)
                s = random.randint(60, 90)
                l = random.randint(45, 65)
                
                # Converter HSL para RGB e depois para HEX
                def hsl_to_rgb(h, s, l):
                    h /= 360
                    s /= 100
                    l /= 100
                    
                    if s == 0:
                        r = g = b = l
                    else:
                        def hue_to_rgb(p, q, t):
                            if t < 0: t += 1
                            if t > 1: t -= 1
                            if t < 1/6: return p + (q - p) * 6 * t
                            if t < 1/2: return q
                            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                            return p
                        
                        q = l * (1 + s) if l < 0.5 else l + s - l * s
                        p = 2 * l - q
                        r = hue_to_rgb(p, q, h + 1/3)
                        g = hue_to_rgb(p, q, h)
                        b = hue_to_rgb(p, q, h - 1/3)
                    
                    r = int(r * 255)
                    g = int(g * 255)
                    b = int(b * 255)
                    
                    return f'#{r:02x}{g:02x}{b:02x}'
                
                cores_categorias[categoria] = hsl_to_rgb(h, s, l)
        
        # Conteúdo HTML completo em uma única string
        html_content = """<!DOCTYPE html>
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
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #1a5276; text-align: center; margin-bottom: 30px; }
        .data-atualizacao { text-align: center; color: #666; margin-bottom: 20px; font-style: italic; }
        a { color: #2980b9; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .categoria { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; color: white; }
        .hora { white-space: nowrap; color: #666; }
        .fonte { white-space: nowrap; color: #666; font-weight: bold; }
        .stats { margin-top: 30px; text-align: center; color: #666; }
        
        /* Estilos responsivos para celulares */
        @media (max-width: 768px) {
            body { padding: 10px; }
            .container { padding: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Monitor de Notícias - Brasil</h1>"""
        
        # Adicionar data e hora
        html_content += f'        <div class="data-atualizacao">Atualizado em: {data_atual} às {hora_atual}</div>\n'
        
        # Adicionar tabela de notícias com DataTables
        html_content += """        <table id="tabela-noticias" class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>Título</th>
                    <th>Categoria</th>
                    <th>Fonte</th>
                    <th>Hora</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Verificar se o DataFrame está vazio
        if df.empty:
            html_content += "<tr><td colspan='4' style='text-align: center;'>Nenhuma notícia encontrada</td></tr>\n"
        else:
            # Gerar linhas da tabela eficientemente
            for _, noticia in df.iterrows():
                hora = noticia.get('hora', 'N/D')
                categoria = noticia.get('categoria', 'Não especificada')
                titulo = noticia.get('titulo', 'N/D')
                link = noticia.get('link', '#')
                
                # Obter cor da categoria ou usar cor padrão
                cor_categoria = cores_categorias.get(categoria, cor_padrao)
                
                html_content += f"""                <tr>
                <td><a href='{link}' target='_blank'>{titulo}</a></td>
                <td><span class='categoria' style='background-color: {cor_categoria};'>{categoria}</span></td>
                <td class='fonte'>{noticia.get('fonte', 'Desconhecida')}</td>
                <td class='hora'>{hora}</td>
            </tr>
"""
        
        # Finalizar o HTML
        html_content += f"""            </tbody>
        </table>
        <div class="stats">Total de notícias: {total_noticias}</div>
    </div>
    
    <!-- jQuery e Bootstrap JS -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- DataTables JS -->
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
    
    <script>
        // Inicializar DataTables
        $(document).ready(function() {{
            $('#tabela-noticias').DataTable({{
                language: {{
                    url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/pt-BR.json'
                }},
                pageLength: 50,
                order: [], // Sem ordenação inicial
                responsive: true,
                lengthMenu: [10, 25, 50, 100]
            }});
        }});

        // Script para atualização automática da página sem mostrar contagem
        document.addEventListener('DOMContentLoaded', function() {{
            // Calcular o tempo até o próximo minuto exato e configurar recarregamento
            function configurarRecarregamento() {{
                const agora = new Date();
                const segundosRestantes = 60 - agora.getSeconds();
                const milissegundosRestantes = segundosRestantes * 1000;
                
                setTimeout(function() {{
                    // Salvar posição de rolagem
                    const scrollPos = window.scrollY;
                    sessionStorage.setItem('scrollPos', scrollPos);
                    
                    // Recarregar a página
                    location.reload();
                }}, milissegundosRestantes);
            }}
            
            // Configurar o recarregamento automático
            configurarRecarregamento();
            
            // Salvar posição de rolagem no sessionStorage antes de recarregar
            window.addEventListener('beforeunload', function() {{
                sessionStorage.setItem('scrollPos', window.scrollY);
            }});
        }});
        
        // Restaurar posição de rolagem após o carregamento da página
        window.addEventListener('load', function() {{
            const scrollPos = sessionStorage.getItem('scrollPos');
            if (scrollPos) {{
                window.scrollTo(0, parseInt(scrollPos));
            }}
        }});
    </script>
</body>
</html>"""
        
        # Salvar o arquivo HTML com encoding UTF-8 e BOM
        with open('monitor_noticias.html', 'w', encoding='utf-8-sig') as f:
            f.write(html_content)
        
        print("HTML gerado com sucesso")
        return True
    except Exception as e:
        print(f"ERRO ao gerar arquivo HTML: {e}")
        # Tentativa de gerar um HTML muito simples em caso de erro
        try:
            with open('monitor_noticias_erro.html', 'w', encoding='utf-8-sig') as f:
                f.write(f"<html><body><h1>Erro</h1><p>{e}</p></body></html>")
        except:
            pass
        return False

def carregar_pagina_com_retry(driver, url, max_tentativas=3, timeout=25):
    """
    Tenta carregar uma página com múltiplas tentativas em caso de timeout
    """
    for tentativa in range(max_tentativas):
        try:
            print(f"Carregando página (tentativa {tentativa + 1}/{max_tentativas}): {url}")
            
            # Configurar timeout específico para esta tentativa
            driver.set_page_load_timeout(timeout)
            driver.get(url)
            
            # Aguardar um pouco para garantir carregamento
            time.sleep(1)
            return True
        except Exception as e:
            print(f"Erro na tentativa {tentativa + 1}: {e}")
            if tentativa < max_tentativas - 1:
                # Aumentar timeout progressivamente
                timeout_progressivo = timeout + (tentativa * 10)
                print(f"Tentando novamente em 3 segundos com timeout de {timeout_progressivo}s...")
                time.sleep(3)
                driver.set_page_load_timeout(timeout_progressivo)
            else:
                print(f"Falha ao carregar {url} após {max_tentativas} tentativas")
                return False
    return False

# Atualizar o final do arquivo para incluir o novo scraper se executado diretamente
if __name__ == "__main__":
    start_time = time.time()
    # Usar modo rápido por padrão para atualizações mais frequentes
    extrair_todas_noticias(modo_rapido=True)
    end_time = time.time()
    print(f"Tempo total de execução: {end_time - start_time:.2f} segundos") 