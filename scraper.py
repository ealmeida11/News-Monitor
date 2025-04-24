#!/usr/bin/env C:\Users\erica\AppData\Local\Programs\Python\Launcher\py.exe
# -*- coding: utf-8 -*-

import time
import pandas as pd
import re
import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from bs4 import BeautifulSoup
from io import StringIO

class ValorEconomicoScraper:
    def __init__(self):
        self.url = "https://valor.globo.com/ultimas-noticias/"
        self.noticias = []
        self.hoje = datetime.now().strftime("%d/%m/%Y")
        self.titulos_atuais = set()
        
        # Configurar o driver do Edge
        self.driver = self.configurar_driver()
    
    def configurar_driver(self):
        """
        Configura o driver do Microsoft Edge para a automação
        """
        print("Configurando o driver do Microsoft Edge...")
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
        
        # Instalar/atualizar o driver do Edge automaticamente
        service = Service(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
        
        return driver
    
    def fechar_driver(self):
        """
        Fecha o driver do Edge quando não for mais necessário
        """
        if self.driver:
            self.driver.quit()
            print("Driver do Edge fechado.")
    
    def obter_pagina(self, url):
        """
        Carrega a página usando o Selenium e retorna o conteúdo HTML
        """
        try:
            print(f"Carregando a página: {url}")
            self.driver.get(url)
            
            # Aguardar o carregamento dos elementos principais
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
            )
            
            # Retornar o HTML da página
            return self.driver.page_source
        except Exception as e:
            print(f"Erro ao carregar página: {e}")
            return None
    
    def extrair_noticias(self, html):
        """
        Extrai as notícias do HTML usando BeautifulSoup
        """
        if not html:
            return 0
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Encontrar todos os artigos de notícias
        artigos = soup.find_all('div', class_='feed-post-body')
        print(f"Encontrados {len(artigos)} artigos na página")
        
        # Data atual para filtrar notícias
        data_atual = self.hoje
        
        novas_noticias = 0
        noticias_batch = []
        
        for artigo in artigos:
            try:
                # Extrair título e link
                link_element = artigo.find('a', class_='feed-post-link')
                if not link_element:
                    continue
                    
                titulo = link_element.text.strip()
                
                # Verificar se o título já existe na lista de notícias
                if titulo in self.titulos_atuais:
                    continue
                    
                link = link_element['href']
                
                # Determinar a fonte com base no link
                if 'valor.globo.com' in link:
                    fonte = 'Valor Econômico'
                else:
                    fonte = 'Desconhecida'
                
                # Extrair categoria
                categoria_element = artigo.find('span', class_='feed-post-metadata-section')
                if not categoria_element:
                    categoria_element = artigo.find('a', class_='feed-post-header-chapeu')
                if not categoria_element:
                    categoria_element = artigo.find('span', class_='feed-post-header-chapeu')
                    
                categoria = categoria_element.text.strip() if categoria_element else "Não especificada"
                
                # Extrair data e hora
                data_element = artigo.find('span', class_='feed-post-datetime')
                if not data_element:
                    continue
                    
                data_hora_texto = data_element.text.strip()
                
                # Verificar se contém o formato de data DD/MM/AAAA, HH:MM
                data_match = re.search(r'(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})', data_hora_texto)
                if data_match:
                    data = data_match.group(1)
                    hora = data_match.group(2)
                    
                    # Verificar se a notícia é do dia atual
                    if data != data_atual:
                        # Se encontrarmos uma notícia de data anterior, podemos parar a extração
                        self.noticias_antigas_encontradas = True
                        continue
                    
                    # Adicionar à lista temporária
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
        
        # Adicionar o lote de notícias à lista principal
        if noticias_batch:
            self.noticias.extend(noticias_batch)
            print(f"Adicionadas {novas_noticias} novas notícias")
                
        return novas_noticias
    
    def navegar_para_proxima_pagina(self, pagina_atual):
        """
        Navega diretamente para a próxima página usando URL em vez de clicar no botão
        """
        try:
            # Construir a URL para a próxima página
            proxima_pagina = pagina_atual + 1
            url_proxima = f"https://valor.globo.com/ultimas-noticias/index/feed/pagina-{proxima_pagina}"
            
            print(f"Navegando para página {proxima_pagina}: {url_proxima}")
            self.driver.get(url_proxima)
            
            # Verificar se a página carregou corretamente
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
            )
            return True
        except Exception as e:
            print(f"Erro ao navegar para a próxima página: {e}")
            return False
    
    def extrair_todas_noticias(self, max_paginas=15):
        """
        Extrai notícias de várias páginas usando navegação direta
        """
        # Inicializar variáveis de controle
        self.noticias_antigas_encontradas = False
        
        # Carregar a primeira página
        html = self.obter_pagina(self.url)
        if not html:
            print("Não foi possível carregar a página inicial.")
            return
        
        # Extrair notícias da primeira página
        novas_noticias = self.extrair_noticias(html)
        print(f"Notícias encontradas até agora: {len(self.noticias)}")
        
        # Carregar mais páginas navegando diretamente para as URLs
        pagina_atual = 1
        tentativas_sem_novas = 0
        
        while pagina_atual < max_paginas and not self.noticias_antigas_encontradas:
            if self.navegar_para_proxima_pagina(pagina_atual):
                novas_noticias = self.extrair_noticias(self.driver.page_source)
                pagina_atual += 1
                
                if novas_noticias > 0:
                    print(f"Notícias encontradas até agora: {len(self.noticias)}")
                    tentativas_sem_novas = 0
                else:
                    tentativas_sem_novas += 1
                    print(f"Nenhuma nova notícia na página {pagina_atual}. Tentativa {tentativas_sem_novas}/2")
                    if tentativas_sem_novas >= 2:
                        print("Duas tentativas sem novas notícias. Finalizando.")
                        break
                
                if self.noticias_antigas_encontradas:
                    print("Encontradas notícias de dias anteriores. Finalizando.")
                    break
            else:
                print("Não foi possível carregar mais páginas. Finalizando.")
                break
                
        print(f"Extração finalizada após verificar {pagina_atual} páginas. Total: {len(self.noticias)} notícias")
    
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
    <title>Monitor de Notícias</title>
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
        
        /* Estilo para a informação de contagem regressiva */
        #countdown {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            z-index: 1000;
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

        // Script para atualização automática da página
        document.addEventListener('DOMContentLoaded', function() {
            // Criar elemento para mostrar contagem regressiva
            const countdownDiv = document.createElement('div');
            countdownDiv.id = 'countdown';
            document.body.appendChild(countdownDiv);
            
            let secondsLeft = 60;
            
            // Função para atualizar a contagem regressiva
            function updateCountdown() {
                countdownDiv.textContent = `Atualização em ${secondsLeft}s`;
                secondsLeft--;
                
                if (secondsLeft < 0) {
                    // Salvar posição de rolagem atual
                    const scrollPos = window.scrollY;
                    
                    // Recarregar a página
                    location.reload();
                }
            }
            
            // Iniciar temporizador
            setInterval(updateCountdown, 1000);
            updateCountdown();
            
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
        <h1>Monitor de Notícias</h1>
"""
            
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

# Função principal para executar o scraper
def extrair_noticias_valor():
    print("Iniciando extração de notícias do Valor Econômico...")
    scraper = ValorEconomicoScraper()
    
    try:
        scraper.extrair_todas_noticias()
        df = scraper.salvar_noticias()
        print(f"Extração concluída. Foram encontradas {len(df)} notícias.")
        print(f"Os resultados foram salvos em monitor_noticias.html")
        return df
    finally:
        scraper.fechar_driver()

if __name__ == "__main__":
    start_time = time.time()
    extrair_noticias_valor()
    end_time = time.time()
    print(f"Tempo total de execução: {end_time - start_time:.2f} segundos") 