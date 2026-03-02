# -*- coding: utf-8 -*-
"""
Teste: coleta TODAS as notícias do Valor das últimas 24 horas,
classifica cada uma por tema e mostra agrupadas por tema.

Também mostra as não classificadas para identificar gaps nas palavras-chave.
"""

import io
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict

# Evitar UnicodeEncodeError no console Windows (cp1252)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timedelta
from pathlib import Path

# Dependências do projeto principal
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Importar classificador
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classificador.lexico_classifier import classificar, NAO_CLASSIFICADO

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s", datefmt="%d/%m/%Y %H:%M:%S")
log = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(SCRIPT_DIR, "valor_login.json")


def carregar_cookies(driver):
    """Carrega cookies salvos"""
    if not os.path.exists(COOKIES_FILE):
        return False

    with open(COOKIES_FILE, 'r') as f:
        cookies = json.load(f)

    for cookie in cookies:
        if 'expiry' in cookie:
            cookie['expiry'] = int(cookie['expiry'])
        try:
            driver.add_cookie(cookie)
        except:
            pass  # Ignora cookies inválidos

    log.info("  %d cookies carregados", len(cookies))
    return True


def _gerar_html(noticias_por_tema, nao_classificadas, total_coletado, arq_html):
    """Gera um HTML simples com o relatório por tema (sem Mundo e sem não classificadas)."""
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
    linhas.append('.noticia a{color:#2980b9;text-decoration:none;}')
    linhas.append('.noticia a:hover{text-decoration:underline;}')
    linhas.append('.resumo{color:#555;font-size:0.95em;margin:6px 0;}')
    linhas.append('.info{font-size:0.85em;color:#7f8c8d;}')
    linhas.append('</style>')
    linhas.append('</head><body><div class="container">')
    linhas.append('<h1>Valor Econômico – Classificação por tema</h1>')

    # Filtrar Mundo e contar apenas temas visíveis
    temas_visiveis = {t: lista for t, lista in noticias_por_tema.items() if t != "Mundo"}
    total_classificadas = sum(len(lista) for lista in temas_visiveis.values())

    linhas.append(f'<p class="meta">Últimas 24 horas | Total coletado: {total_coletado} | '
                  f'Classificadas: {total_classificadas}</p>')

    for tema in sorted(temas_visiveis.keys()):
        lista = temas_visiveis[tema]
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

    linhas.append('</div></body></html>')
    with open(arq_html, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def _ajustar_fuso(data, hora, delta_horas=-3):
    """Ajusta data/hora pelo fuso do servidor (UTC -> BRT)."""
    dt = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M")
    dt += timedelta(hours=delta_horas)
    return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")


def noticia_dentro_24h(data, hora):
    """Verifica se uma notícia está dentro das últimas 24 horas."""
    try:
        data_hora_str = f"{data} {hora}"
        data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
        limite_24h = datetime.now() - timedelta(hours=24)
        return data_hora_noticia >= limite_24h
    except:
        return False


# Páginas de colunistas do Valor (categoria Editorial, titulo = "Autor: titulo")
EDITORIAL_AUTORES_VALOR = [
    ("https://valor.globo.com/autores/alex-ribeiro/", "Alex Ribeiro"),
    ("https://valor.globo.com/autores/andrea-jube/", "Andrea Jubé"),
    ("https://valor.globo.com/autores/arthur-cagliari/", "Arthur Cagliari"),
    ("https://valor.globo.com/autores/sergio-lamucci/", "Sergio Lamucci"),
    ("https://valor.globo.com/autores/giordanna-neves/", "Giordanna Neves"),
]


def main():
    import os
    os.environ['WDM_LOG_LEVEL'] = '0'
    logging.getLogger("WDM").setLevel(logging.WARNING)

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup

    # SELENIUM_GRID_URL = "http://airflow.jgp.com.br:4445"

    URL_BASE = "https://valor.globo.com/ultimas-noticias/"

    t0 = time.time()

    log.info("=" * 60)
    log.info("COLETA - VALOR ECONÔMICO (últimas 24h)")
    log.info("URL: %s", URL_BASE)
    log.info("Período: últimas 24h (desde %s)", (datetime.now() - timedelta(hours=24)).strftime("%d/%m/%Y %H:%M"))
    log.info("=" * 60)

    opts = ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-logging")
    opts.add_argument("--silent")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = None
    noticias_coletadas = []
    titulos_unicos = set()
    # Links já no banco (últimos 7 dias): se encontrar 3, para para agilizar o loop
    _out = Path(__file__).resolve().parent.parent / "output"
    _links_file = _out / "links_existentes.txt"
    links_existentes = set()
    if _links_file.exists():
        try:
            with open(_links_file, "r", encoding="utf-8") as f:
                links_existentes = {ln.strip() for ln in f if ln.strip()}
        except Exception:
            pass
    ja_no_banco_consecutivos = 0
    parar_por_banco = False

    try:
        # # --- Selenium Grid (comentado) ---
        # driver = webdriver.Remote(
        #     command_executor=SELENIUM_GRID_URL,
        #     options=chrome_options,
        # )

        # --- Chrome local (mesmo padrão do NewsAI Real Time) ---
        driver_path = ChromeDriverManager().install()
        service = ChromeService(driver_path, log_output=os.devnull)
        driver = webdriver.Chrome(service=service, options=opts)

        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        # Carregar cookies
        driver.get(URL_BASE)
        if carregar_cookies(driver):
            log.info("  Recarregando página com cookies...")
            driver.refresh()
            time.sleep(2)

        pagina = 1
        limite_paginas = 50  # Aumentado para garantir coleta completa

        while pagina <= limite_paginas:
            if parar_por_banco:
                break
            if pagina == 1:
                url = URL_BASE
            else:
                url = f"https://valor.globo.com/ultimas-noticias/index/feed/pagina-{pagina}"

            log.info("  Acessando página %d...", pagina)
            try:
                if pagina > 1:
                    driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
                )
                time.sleep(2)
            except Exception as e:
                log.error("    Erro ao acessar página %d: %s", pagina, type(e).__name__)
                log.info("    Continuando com o que já foi coletado...")
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
                    categorias_excluidas_valor = {"ESG", "Carreira", "Empresas", "Eu &", "Marketing", "Colunas", "Colunistas"}
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
                    data, hora = _ajustar_fuso(data, hora)

                    # Filtrar por 24 horas
                    if not noticia_dentro_24h(data, hora):
                        antigas_nesta_pagina += 1
                        continue

                    # Parar se 5 notícias consecutivas já estiverem no banco
                    if links_existentes and link in links_existentes:
                        ja_no_banco_consecutivos += 1
                        if ja_no_banco_consecutivos >= 5:
                            parar_por_banco = True
                            break
                        continue
                    ja_no_banco_consecutivos = 0

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

            if parar_por_banco:
                log.info("  Parada: 3 notícias já estavam no banco")
                break
            log.info("    Página %d: %d novas, %d antigas", pagina, novas_nesta_pagina, antigas_nesta_pagina)

            # Parar apenas se encontrar muitas notícias antigas (fora de 24h) consecutivas
            # Isso indica que chegamos em notícias antigas e não há mais novas nas próximas páginas
            if antigas_nesta_pagina >= 5:
                log.info("  Parada: muitas notícias antigas detectadas (fora de 24h)")
                break

            # Se não encontrou nenhum artigo na página (erro de parsing ou página vazia), continuar
            # Só parar se chegou no limite de páginas

            pagina += 1

        # Coleta editorial: páginas de autores (Alex Ribeiro, Andrea Jubé)
        log.info("")
        log.info("  Coletando editoriais (páginas de autores)...")
        for url_autor, autor_nome in EDITORIAL_AUTORES_VALOR:
            try:
                driver.get(url_autor)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
                )
                time.sleep(2)
            except Exception as e:
                log.warning("    Aviso: erro ao carregar %s: %s", url_autor, e)
                continue
            soup = BeautifulSoup(driver.page_source, "html.parser")
            artigos = soup.find_all("div", class_="feed-post-body")
            for artigo in artigos:
                try:
                    link_element = artigo.find("a", class_="feed-post-link")
                    if not link_element:
                        continue
                    titulo = link_element.text.strip()
                    if titulo in titulos_unicos:
                        continue
                    link = link_element.get("href")
                    data_element = artigo.find("span", class_="feed-post-datetime")
                    if not data_element:
                        continue
                    data_hora_texto = data_element.text.strip()
                    data_match = re.search(r"(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})", data_hora_texto)
                    if not data_match:
                        continue
                    data = data_match.group(1)
                    hora = data_match.group(2)
                    data, hora = _ajustar_fuso(data, hora)
                    if not noticia_dentro_24h(data, hora):
                        continue
                    if links_existentes and link in links_existentes:
                        continue
                    resumo_element = artigo.find("p", class_="feed-post-body-resumo")
                    resumo = (resumo_element.text.strip() if resumo_element else None) or None
                    noticias_coletadas.append({
                        "titulo": titulo,
                        "resumo": resumo,
                        "categoria": "Editorial",
                        "fonte": "Valor Econômico",
                        "data": data,
                        "hora": hora,
                        "link": link,
                        "autor_editorial": autor_nome,
                    })
                    titulos_unicos.add(titulo)
                except Exception:
                    continue
            log.info("    %s: +%d itens na página", autor_nome, len(artigos))

        log.info("")
        log.info("  Total coletado: %d notícias", len(noticias_coletadas))

        # Classificar cada notícia
        log.info("  Classificando notícias...")
        noticias_por_tema = defaultdict(list)
        nao_classificadas = []

        for noticia in noticias_coletadas:
            if noticia.get("autor_editorial"):
                noticia["titulo"] = f"{noticia['autor_editorial']}: {noticia['titulo']}"
                noticia["tema_classificado"] = "Editorial"
                noticia["score"] = 1
                noticia["scores_todos"] = {}
                noticias_por_tema["Editorial"].append(noticia)
                continue
            # Classificar com léxico
            resultado = classificar(noticia['titulo'], resumo=noticia.get('resumo', ''))
            tema = resultado['tema']

            # Excluir completamente notícias classificadas como Mundo (não coletar)
            if tema == "Mundo":
                continue  # Pula esta notícia, não salva em lugar nenhum

            noticia['tema_classificado'] = tema
            noticia['score'] = resultado['score']
            noticia['scores_todos'] = resultado['scores']

            # Ignorar não classificadas (não aparecem mais)
            if tema == NAO_CLASSIFICADO:
                nao_classificadas.append(noticia)
            else:
                noticias_por_tema[tema].append(noticia)

        # Mostrar classificação
        temas_visiveis = {t: lista for t, lista in noticias_por_tema.items() if t != "Mundo"}

        log.info("")
        log.info("Classificação")
        log.info("-" * 60)
        for tema in sorted(temas_visiveis.keys()):
            log.info("  %-20s %4d", tema, len(temas_visiveis[tema]))
        log.info("  %-20s %4d", "Não classificadas", len(nao_classificadas))

        # Salvar JSON completo (sempre com o mesmo nome)
        out_dir = Path(__file__).resolve().parent.parent / "output"
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

        # Gerar HTML simples para abrir no navegador
        _gerar_html(noticias_por_tema, nao_classificadas, len(noticias_coletadas), arq_html)

        log.info("")
        log.info("Arquivos salvos:")
        log.info("  JSON: %s", arq_json)
        log.info("  HTML: %s", arq_html)
        log.info("=" * 60)
        log.info("Concluído (%.1fs)", time.time() - t0)
        log.info("=" * 60)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
