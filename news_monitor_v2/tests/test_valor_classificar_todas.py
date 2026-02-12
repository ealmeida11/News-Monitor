# -*- coding: utf-8 -*-
"""
Teste: coleta TODAS as notícias do Valor das últimas 24 horas,
classifica cada uma por tema e mostra agrupadas por tema.

Também mostra as não classificadas para identificar gaps nas palavras-chave.
"""

import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Dependências do projeto principal
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Importar classificador
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classificador.lexico_classifier import classificar, NAO_CLASSIFICADO


def _gerar_html(noticias_por_tema, nao_classificadas, total_coletado, arq_html):
    """Gera um HTML simples com o relatório por tema e não classificadas."""
    from html import escape
    linhas = []
    linhas.append('<!DOCTYPE html>')
    linhas.append('<html lang="pt-BR">')
    linhas.append('<head><meta charset="UTF-8"><title>Valor - Classificação por tema (24h)</title>')
    linhas.append('<style>')
    linhas.append('body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;}')
    linhas.append('.container{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}')
    linhas.append('h1{color:#1a5276;border-bottom:2px solid #1a5276;padding-bottom:8px;}')
    linhas.append('h2{margin-top:28px;color:#2c3e50;}')
    linhas.append('.meta{color:#666;font-size:0.9em;margin-bottom:20px;}')
    linhas.append('.noticia{margin:12px 0;padding:12px;background:#f9f9f9;border-left:4px solid #3498db;border-radius:4px;}')
    linhas.append('.noticia.nao{border-left-color:#95a5a6;}')
    linhas.append('.noticia a{color:#2980b9;text-decoration:none;}')
    linhas.append('.noticia a:hover{text-decoration:underline;}')
    linhas.append('.resumo{color:#555;font-size:0.95em;margin:6px 0;}')
    linhas.append('.info{font-size:0.85em;color:#7f8c8d;}')
    linhas.append('</style>')
    linhas.append('</head><body><div class="container">')
    linhas.append('<h1>Valor Econômico – Classificação por tema</h1>')
    linhas.append(f'<p class="meta">Últimas 24 horas | Total coletado: {total_coletado} | '
                  f'Classificadas: {total_coletado - len(nao_classificadas)} | '
                  f'Não classificadas: {len(nao_classificadas)}</p>')

    for tema in sorted(noticias_por_tema.keys()):
        lista = noticias_por_tema[tema]
        linhas.append(f'<h2>{escape(tema)} ({len(lista)})</h2>')
        for n in lista:
            titulo = escape(n.get("titulo", ""))
            link = escape(n.get("link", "#"))
            resumo = escape((n.get("resumo") or "")[:300])
            info = f"{n.get('categoria', '')} | {n.get('hora', '')} | score {n.get('score', 0)}"
            linhas.append('<div class="noticia">')
            linhas.append(f'<a href="{link}" target="_blank">{titulo}</a>')
            if resumo:
                linhas.append(f'<p class="resumo">{resumo}</p>')
            linhas.append(f'<p class="info">{escape(info)}</p>')
            linhas.append('</div>')

    linhas.append(f'<h2>Não classificadas ({len(nao_classificadas)})</h2>')
    for n in nao_classificadas:
        titulo = escape(n.get("titulo", ""))
        link = escape(n.get("link", "#"))
        resumo = escape((n.get("resumo") or "")[:300])
        info = f"{n.get('categoria', '')} | {n.get('hora', '')}"
        linhas.append('<div class="noticia nao">')
        linhas.append(f'<a href="{link}" target="_blank">{titulo}</a>')
        if resumo:
            linhas.append(f'<p class="resumo">{resumo}</p>')
        linhas.append(f'<p class="info">{escape(info)}</p>')
        linhas.append('</div>')

    linhas.append('</div></body></html>')
    with open(arq_html, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def noticia_dentro_24h(data, hora):
    """Verifica se uma notícia está dentro das últimas 24 horas."""
    try:
        data_hora_str = f"{data} {hora}"
        data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
        limite_24h = datetime.now() - timedelta(hours=24)
        return data_hora_noticia >= limite_24h
    except:
        return False


def main():
    import os
    os.environ['WDM_LOG_LEVEL'] = '0'

    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup

    URL_BASE = "https://valor.globo.com/ultimas-noticias/"

    print("=" * 70)
    print("  COLETA E CLASSIFICAÇÃO - VALOR (últimas 24 horas)")
    print("=" * 70)
    print(f"  URL: {URL_BASE}")
    print(f"  Período: últimas 24 horas (desde {datetime.now() - timedelta(hours=24):%d/%m/%Y %H:%M})")
    print()

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    for arg in ["--disable-logging", "--log-level=3", "--silent"]:
        chrome_options.add_argument(arg)

    driver = None
    noticias_coletadas = []
    titulos_unicos = set()

    try:
        service = ChromeService(ChromeDriverManager().install(), log_output=os.devnull)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        pagina = 1
        limite_paginas = 50  # Aumentado para garantir coleta completa

        while pagina <= limite_paginas:
            if pagina == 1:
                url = URL_BASE
            else:
                url = f"https://valor.globo.com/ultimas-noticias/index/feed/pagina-{pagina}"

            print(f"  Acessando página {pagina}...")
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
                )
                time.sleep(2)
            except Exception as e:
                print(f"    ERRO ao acessar página {pagina}: {type(e).__name__}")
                print(f"    Continuando com o que já foi coletado...")
                break

            soup = BeautifulSoup(driver.page_source, "html.parser")
            artigos = soup.find_all("div", class_="feed-post-body")

            novas_nesta_pagina = 0
            antigas_nesta_pagina = 0

            for artigo in artigos:
                try:
                    link_element = artigo.find("a", class_="feed-post-link")
                    if not link_element:
                        continue

                    titulo = link_element.text.strip()
                    if titulo in titulos_unicos:
                        continue

                    link = link_element.get("href")
                    categoria_element = artigo.find("span", class_="feed-post-metadata-section")
                    categoria = categoria_element.text.strip() if categoria_element else "Não especificada"

                    # Filtrar categorias que não queremos coletar
                    categorias_excluidas_valor = {"ESG", "Carreira", "Empresas", "Eu &"}
                    if categoria in categorias_excluidas_valor:
                        continue

                    data_element = artigo.find("span", class_="feed-post-datetime")
                    if not data_element:
                        continue

                    data_hora_texto = data_element.text.strip()
                    data_match = re.search(r"(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})", data_hora_texto)
                    if not data_match:
                        continue

                    data = data_match.group(1)
                    hora = data_match.group(2)

                    # Filtrar por 24 horas
                    if not noticia_dentro_24h(data, hora):
                        antigas_nesta_pagina += 1
                        continue

                    # Resumo
                    resumo_element = artigo.find("p", class_="feed-post-body-resumo")
                    resumo = (resumo_element.text.strip() if resumo_element else None) or None

                    noticia = {
                        "titulo": titulo,
                        "resumo": resumo,
                        "categoria": categoria,
                        "fonte": "Valor Econômico",
                        "data": data,
                        "hora": hora,
                        "link": link,
                    }

                    titulos_unicos.add(titulo)
                    noticias_coletadas.append(noticia)
                    novas_nesta_pagina += 1

                except Exception as e:
                    continue

            print(f"    Página {pagina}: {novas_nesta_pagina} novas, {antigas_nesta_pagina} antigas")

            # Parar apenas se encontrar muitas notícias antigas (fora de 24h) consecutivas
            # Isso indica que chegamos em notícias antigas e não há mais novas nas próximas páginas
            if antigas_nesta_pagina >= 5:
                print("    PARADA: muitas notícias antigas detectadas (fora de 24h)")
                break
            
            # Se não encontrou nenhum artigo na página (erro de parsing ou página vazia), continuar
            # Só parar se chegou no limite de páginas

            pagina += 1

        print()
        print(f"  Total coletado: {len(noticias_coletadas)} notícias")
        print()

        # Classificar cada notícia
        print("  Classificando notícias...")
        noticias_por_tema = defaultdict(list)
        nao_classificadas = []

        for noticia in noticias_coletadas:
            # Se categoria do site for "Mundo", classificar automaticamente como Mundo
            categoria_site = noticia.get('categoria', '')
            if categoria_site == 'Mundo':
                tema = 'Mundo'
                noticia['tema_classificado'] = tema
                noticia['score'] = 1
                noticia['scores_todos'] = {'Mundo': 1}
                noticias_por_tema[tema].append(noticia)
            else:
                # Classificar normalmente com léxico
                resultado = classificar(noticia['titulo'], resumo=noticia.get('resumo', ''))
                tema = resultado['tema']
                noticia['tema_classificado'] = tema
                noticia['score'] = resultado['score']
                noticia['scores_todos'] = resultado['scores']

                if tema == NAO_CLASSIFICADO:
                    nao_classificadas.append(noticia)
                else:
                    noticias_por_tema[tema].append(noticia)

        # Mostrar resultados
        print()
        print("=" * 70)
        print("  RESULTADO DA CLASSIFICAÇÃO")
        print("=" * 70)
        print()

        # Por tema
        for tema in sorted(noticias_por_tema.keys()):
            lista = noticias_por_tema[tema]
            print(f"  [{len(lista)}] {tema}")
            print("-" * 70)
            for n in lista:
                print(f"    - {n['titulo'][:75]}...")
                if n.get('resumo'):
                    print(f"      Resumo: {n['resumo'][:70]}...")
                print(f"      Score: {n['score']} | Categoria site: {n['categoria']} | {n['hora']}")
            print()

        # Não classificadas
        print(f"  [{len(nao_classificadas)}] NÃO CLASSIFICADAS")
        print("-" * 70)
        if nao_classificadas:
            for n in nao_classificadas:
                print(f"    - {n['titulo'][:75]}...")
                if n.get('resumo'):
                    print(f"      Resumo: {n['resumo'][:70]}...")
                print(f"      Categoria site: {n['categoria']} | {n['hora']}")
        else:
            print("    (nenhuma)")
        print()

        # Resumo estatístico
        print("=" * 70)
        print("  RESUMO ESTATÍSTICO")
        print("=" * 70)
        print(f"  Total coletado: {len(noticias_coletadas)}")
        print(f"  Classificadas: {len(noticias_coletadas) - len(nao_classificadas)}")
        print(f"  Não classificadas: {len(nao_classificadas)}")
        print()
        print("  Por tema:")
        for tema in sorted(noticias_por_tema.keys()):
            print(f"    {tema}: {len(noticias_por_tema[tema])}")

        # Salvar JSON completo (sempre com o mesmo nome)
        out_dir = Path(__file__).resolve().parent / "output"
        out_dir.mkdir(exist_ok=True)
        
        # Limpar arquivos antigos com timestamp
        for arq_antigo in out_dir.glob("valor_classificado_*_*.json"):
            try:
                arq_antigo.unlink()
            except:
                pass
        for arq_antigo in out_dir.glob("valor_classificado_*_*.html"):
            try:
                arq_antigo.unlink()
            except:
                pass
        
        # Nomes fixos (sem timestamp)
        arq_json = out_dir / "valor_classificado_24h.json"
        arq_html = out_dir / "valor_classificado_24h.html"
        
        resultado_completo = {
            "data_coleta": datetime.now().isoformat(),
            "periodo_horas": 24,
            "total_coletado": len(noticias_coletadas),
            "por_tema": {tema: lista for tema, lista in noticias_por_tema.items()},
            "nao_classificadas": nao_classificadas,
        }
        with open(arq_json, "w", encoding="utf-8") as f:
            json.dump(resultado_completo, f, ensure_ascii=False, indent=2)
        print()
        print(f"  JSON completo salvo em: {arq_json}")

        # Gerar HTML simples para abrir no navegador
        _gerar_html(noticias_por_tema, nao_classificadas, len(noticias_coletadas), arq_html)
        print(f"  Relatório HTML salvo em: {arq_html}")
        print("=" * 70)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
