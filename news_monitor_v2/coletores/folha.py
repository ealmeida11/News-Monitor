# -*- coding: utf-8 -*-
"""
Teste: coleta notícias da Folha de S.Paulo das últimas 24 horas (botão "Ver mais"),
classifica cada uma por tema e mostra: por tema + não classificadas.

Objetivo: analisar classificação e dar instruções para ajustes.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s", datefmt="%d/%m/%Y %H:%M:%S")
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classificador.lexico_classifier import classificar, NAO_CLASSIFICADO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(SCRIPT_DIR, "folha_login.json")


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


def _extrair_categoria_folha(link):
    """Categoria a partir da URL da Folha."""
    link_lower = (link or "").lower()
    # Coluna Mônica Bergamo costuma ser política/notícia relevante — incluir (não tratar como Colunas)
    if "monica-bergamo" in link_lower or "mônica-bergamo" in link_lower or "bergamo" in link_lower:
        return "Política"
    categorias_map = {
        "poder": "Política", "mercado": "Economia", "cotidiano": "Cotidiano",
        "mundo": "Mundo", "esporte": "Esporte", "ilustrada": "Cultura",
        "f5": "Entretenimento", "ambiente": "Ambiente", "ciencia": "Ciência",
        "equilibrioesaude": "Saúde", "educacao": "Educação", "tecnologia": "Tecnologia",
    }
    url_match = re.search(r"folha\.uol\.com\.br/([^/]+)/", link_lower)
    if url_match:
        categoria_url = url_match.group(1).lower()
        return categorias_map.get(categoria_url, categoria_url.replace("-", " ").title())
    return "Não especificada"


def _ajustar_fuso(data, hora, delta_horas=-3):
    """Ajusta data/hora pelo fuso do servidor (UTC -> BRT)."""
    dt = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M")
    dt += timedelta(hours=delta_horas)
    return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")


def noticia_dentro_24h(data, hora):
    """Verifica se está dentro das últimas 24 horas. data=DD/MM/YYYY, hora=HH:MM."""
    try:
        data_hora_str = f"{data} {hora}"
        data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
        limite_24h = datetime.now() - timedelta(hours=24)
        return data_hora_noticia >= limite_24h
    except Exception:
        return False


def _processar_data_folha(data_hora_texto):
    """Processa data da Folha: '25.abr.2025 às 12h22' ou com encoding quebrado (Ã s). Retorna (data, hora) ou None."""
    texto = (data_hora_texto or "").replace("Ã s", "às").replace("Ã¡", "á").replace("Ã£", "ã").replace("Ã³", "ó").strip()
    patterns = [
        r"(\d{1,2})\.(\w{3})\.(\d{4})\s+às\s+(\d{1,2})h(\d{2})",
        r"(\d{1,2})\.(\w{3})\.(\d{4})\s+(\d{1,2})h(\d{2})",
    ]
    meses = {
        "jan": "01", "fev": "02", "mar": "03", "abr": "04", "mai": "05", "jun": "06",
        "jul": "07", "ago": "08", "set": "09", "out": "10", "nov": "11", "dez": "12",
    }
    for pattern in patterns:
        m = re.search(pattern, texto, re.I)
        if m:
            dia = m.group(1).zfill(2)
            mes_texto = m.group(2).lower()
            ano = m.group(3)
            h, minu = m.group(4).zfill(2), m.group(5)
            if mes_texto in meses:
                return (f"{dia}/{meses[mes_texto]}/{ano}", f"{h}:{minu}")
    return None


# Colunas/colunistas da Folha (colunaseblogs) que entram na categoria Editorial
# href contém o slug; valor é o nome exibido no título "Autor: titulo"
EDITORIAL_COLUNAS_FOLHA = {
    "painel": "Painel",
    "adriana-fernandes": "Adriana Fernandes",
    "monica-bergamo": "Mônica Bergamo",
}
URL_FOLHA_COLUNAS = "https://www1.folha.uol.com.br/colunaseblogs/"


def _extrair_editoriais_colunaseblogs(soup, titulos_unicos, links_unicos, limite_24h):
    """
    Extrai da página colunaseblogs itens cuja coluna está em EDITORIAL_COLUNAS_FOLHA.
    Procura links para colunas/painel, colunas/adriana-fernandes, colunas/monica-bergamo e no mesmo card o link do artigo.
    """
    noticias = []
    for a_col in soup.find_all("a", href=re.compile(r"colunas/(painel|adriana-fernandes|monica-bergamo)", re.I)):
        href_col = (a_col.get("href") or "").lower()
        autor_editorial = None
        for slug, nome in EDITORIAL_COLUNAS_FOLHA.items():
            if f"colunas/{slug}" in href_col:
                autor_editorial = nome
                break
        if not autor_editorial:
            continue
        container = a_col.find_parent("article") or a_col.find_parent("div", class_=re.compile(r"card|headline|list|item|c-headline", re.I)) or a_col.find_parent("li") or a_col.find_parent("div")
        if not container:
            continue
        # No mesmo container, link do artigo (.shtml)
        a_art = container.find("a", href=re.compile(r"folha\.uol\.com\.br.*\.shtml"))
        if not a_art:
            continue
        titulo_el = a_art.find("h2") or a_art.find("h3") or a_art
        titulo = (titulo_el.get_text(strip=True) if titulo_el else "").strip()
        if not titulo or len(titulo) < 10 or titulo in titulos_unicos:
            continue
        link = (a_art.get("href") or "").strip()
        if not link.startswith("http"):
            link = "https://www1.folha.uol.com.br" + link if link.startswith("/") else "https://www1.folha.uol.com.br/" + link
        if link in links_unicos:
            continue
        time_el = container.find("time", class_=re.compile(r"dateline|date|time", re.I)) or container.find("time")
        data_hora = _processar_data_folha(time_el.get_text(strip=True)) if time_el else None
        if not data_hora:
            continue
        data_hora = _ajustar_fuso(data_hora[0], data_hora[1])
        if not noticia_dentro_24h(data_hora[0], data_hora[1]):
            continue
        titulos_unicos.add(titulo)
        links_unicos.add(link)
        noticias.append({
            "titulo": titulo,
            "resumo": "",
            "categoria": "Editorial",
            "fonte": "Folha de S.Paulo",
            "data": data_hora[0],
            "hora": data_hora[1],
            "link": link,
            "autor_editorial": autor_editorial,
        })
    return noticias


def _gerar_html(noticias_por_tema, nao_classificadas, total_coletado, arq_html, limite_24h=None, intervalo_noticias=None):
    """Gera HTML do relatório (por tema + não classificadas) para análise."""
    from html import escape
    linhas = []
    linhas.append("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Folha - Classificação (24h)</title><style>")
    linhas.append("body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;} .container{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}")
    linhas.append("h1{color:#0066cc;} h2{margin-top:28px;color:#2c3e50;} .meta{color:#666;font-size:0.9em;margin-bottom:20px;} .meta.janela{background:#e8f4f8;padding:8px 12px;border-radius:6px;margin-bottom:12px;}")
    linhas.append(".noticia{margin:12px 0;padding:12px;background:#f9f9f9;border-left:4px solid #3498db;border-radius:4px;} .noticia.nao{border-left-color:#95a5a6;}")
    linhas.append(".noticia a{color:#2980b9;text-decoration:none;} .resumo{color:#555;font-size:0.95em;margin:6px 0;} .info{font-size:0.85em;color:#7f8c8d;}")
    linhas.append("</style></head><body><div class='container'>")
    linhas.append("<h1>Folha de S.Paulo – Classificação por tema (últimas 24h)</h1>")
    linhas.append("<p class='meta'><strong>Folha:</strong> categorias excluídas da coleta: Mundo, Esporte, Cultura, Entretenimento, Educação.</p>")
    if limite_24h is not None and intervalo_noticias is not None:
        de_dt, ate_dt = intervalo_noticias
        linhas.append(f"<p class='meta janela'><strong>Janela de 24h:</strong> incluídas notícias entre {escape(limite_24h.strftime('%d/%m/%Y %H:%M'))} e agora. "
                      f"<strong>Intervalo das notícias:</strong> de {escape(de_dt.strftime('%d/%m/%Y %H:%M'))} até {escape(ate_dt.strftime('%d/%m/%Y %H:%M'))}.</p>")
    temas_visiveis = {t: lst for t, lst in noticias_por_tema.items() if t != "Mundo"}
    total_class = sum(len(lst) for lst in temas_visiveis.values())
    linhas.append(f"<p class='meta'>Total coletado: {total_coletado} | Classificadas: {total_class} | Não classificadas: {len(nao_classificadas)}</p>")
    for tema in sorted(temas_visiveis.keys()):
        lista = temas_visiveis[tema]
        linhas.append(f"<h2>{escape(tema)} ({len(lista)})</h2>")
        for n in lista:
            titulo = escape(n.get("titulo", ""))
            link = escape(n.get("link", "#"))
            resumo = escape((n.get("resumo") or "")[:300])
            info = f"{n.get('categoria', '')} | {n.get('hora', '')} | score {n.get('score', 0)}"
            linhas.append("<div class='noticia'>")
            linhas.append(f"<a href='{link}' target='_blank'>{titulo}</a>")
            if resumo:
                linhas.append(f"<p class='resumo'>{resumo}</p>")
            linhas.append(f"<p class='info'>{escape(info)}</p></div>")
    linhas.append(f"<h2>Não classificadas ({len(nao_classificadas)})</h2>")
    for n in nao_classificadas:
        titulo = escape(n.get("titulo", ""))
        link = escape(n.get("link", "#"))
        resumo = escape((n.get("resumo") or "")[:300])
        info = f"{n.get('categoria', '')} | {n.get('hora', '')}"
        linhas.append("<div class='noticia nao'>")
        linhas.append(f"<a href='{link}' target='_blank'>{titulo}</a>")
        if resumo:
            linhas.append(f"<p class='resumo'>{resumo}</p>")
        linhas.append(f"<p class='info'>{escape(info)}</p></div>")
    linhas.append("</div></body></html>")
    with open(arq_html, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def main():
    t0 = time.time()

    import os
    os.environ["WDM_LOG_LEVEL"] = "0"
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

    URL_BASE = "https://www1.folha.uol.com.br/ultimas-noticias/"

    agora = datetime.now()
    limite_24h = agora - timedelta(hours=24)
    log.info("=" * 60)
    log.info("COLETA - FOLHA DE S.PAULO (últimas 24h)")
    log.info("URL: %s", URL_BASE)
    log.info("Período: %s -> %s", limite_24h.strftime("%d/%m/%Y %H:%M"), agora.strftime("%d/%m/%Y %H:%M"))
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
    categorias_excluidas_folha = {"Mundo", "Esporte", "Cultura", "Entretenimento", "Educação", "Colunas", "Colunistas"}
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

        driver.get(URL_BASE)
        if carregar_cookies(driver):
            log.info("  Recarregando página com cookies...")
            driver.refresh()
            time.sleep(2)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "c-main-headline__title"))
        )
        time.sleep(2)

        clique = 0
        tentativas_sem_novas = 0
        duplicatas_consecutivas = 0
        max_cliques = 15

        while True:
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
            except Exception as e:
                err = str(e).lower()
                if "connection" in err or "refused" in err or "10061" in err or "target machine" in err:
                    log.warning("  conexao com o browser caiu; usando noticias ja coletadas.")
                break

            novas_nesta_rodada = 0
            antigas_nesta_rodada = 0
            repetidas_nesta_rodada = 0

            # Notícia principal / destaque (só na primeira rodada) — estrutura pode variar (c-main-headline ou primeiro bloco com título+data)
            if clique == 0:
                main_headline = (
                    soup.find("a", class_="c-main-headline__url")
                    or soup.find("a", class_=re.compile(r"c-main-headline.*url|main-headline.*url", re.I))
                    or soup.find("a", attrs={"class": lambda c: c and "main-headline" in " ".join(c).lower() and "url" in " ".join(c).lower()})
                )
                if not main_headline:
                    # Fallback: primeiro link para a Folha que tenha h2/h1 + time (destaque pode ter classe/URL diferente da lista)
                    for a in soup.find_all("a", href=re.compile(r"folha\.uol\.com\.br/")):
                        h2 = a.find("h2") or a.find("h1")
                        time_el = a.find("time")
                        if h2 and time_el and h2.get_text(strip=True) and time_el.get_text(strip=True):
                            main_headline = a
                            break
                if main_headline:
                    try:
                        titulo_el = (
                            main_headline.find("h2", class_="c-main-headline__title")
                            or main_headline.find("h2", class_=re.compile(r"main-headline|headline.*title", re.I))
                            or main_headline.find("h2") or main_headline.find("h1")
                        )
                        if titulo_el:
                            titulo = titulo_el.get_text(strip=True)
                            if titulo and titulo not in titulos_unicos:
                                link = main_headline.get("href") or "#"
                                if "folha.uol.com.br" not in link:
                                    link = ("https://www.folha.uol.com.br" + link) if link.startswith("/") else link
                                if "f5.folha.uol.com.br" in link:
                                    continue
                                categoria = _extrair_categoria_folha(link)
                                if categoria not in categorias_excluidas_folha:
                                    time_el = (
                                        main_headline.find("time", class_="c-headline__dateline")
                                        or main_headline.find("time", class_=re.compile(r"dateline|date|time", re.I))
                                        or main_headline.find("time")
                                    )
                                    if time_el:
                                        data_hora = _processar_data_folha(time_el.get_text(strip=True))
                                        if data_hora:
                                            data_hora = _ajustar_fuso(data_hora[0], data_hora[1])
                                        if data_hora and noticia_dentro_24h(data_hora[0], data_hora[1]):
                                            if links_existentes and link in links_existentes:
                                                ja_no_banco_consecutivos += 1
                                                if ja_no_banco_consecutivos >= 5:
                                                    parar_por_banco = True
                                            else:
                                                ja_no_banco_consecutivos = 0
                                                resumo_el = (
                                                    main_headline.find("p", class_="c-headline__standfirst")
                                                    or main_headline.find("p", class_=re.compile(r"standfirst|resumo|summary", re.I))
                                                    or main_headline.find("p")
                                                )
                                                resumo = (resumo_el.get_text(strip=True) if resumo_el else "")[:500] or ""
                                                noticias_coletadas.append({
                                                    "titulo": titulo, "resumo": resumo, "categoria": categoria,
                                                    "fonte": "Folha de S.Paulo", "data": data_hora[0], "hora": data_hora[1], "link": link,
                                                })
                                                titulos_unicos.add(titulo)
                                                novas_nesta_rodada += 1
                    except Exception:
                        pass

            # Notícias da lista (links .shtml com h2.c-headline__title e time)
            artigos = soup.find_all("a", href=re.compile(r"folha\.uol\.com\.br/.*\.shtml"))
            for artigo in artigos:
                try:
                    titulo_el = artigo.find("h2", class_="c-headline__title")
                    if not titulo_el:
                        continue
                    titulo = titulo_el.get_text(strip=True)
                    if not titulo:
                        continue
                    if titulo in titulos_unicos:
                        repetidas_nesta_rodada += 1
                        continue
                    link = artigo.get("href") or "#"
                    if "f5.folha.uol.com.br" in link:
                        continue
                    categoria = _extrair_categoria_folha(link)
                    if categoria in categorias_excluidas_folha:
                        continue
                    time_el = artigo.find("time", class_="c-headline__dateline")
                    if not time_el:
                        continue
                    data_hora = _processar_data_folha(time_el.get_text(strip=True))
                    if not data_hora:
                        continue
                    data_hora = _ajustar_fuso(data_hora[0], data_hora[1])
                    if not noticia_dentro_24h(data_hora[0], data_hora[1]):
                        antigas_nesta_rodada += 1
                        continue
                    if links_existentes and link in links_existentes:
                        ja_no_banco_consecutivos += 1
                        if ja_no_banco_consecutivos >= 5:
                            parar_por_banco = True
                            break
                        continue
                    ja_no_banco_consecutivos = 0
                    # Resumo: verificar se existe elemento na lista (ex.: c-headline__kicker ou similar)
                    resumo_el = artigo.find("p", class_="c-headline__standfirst")
                    resumo = (resumo_el.get_text(strip=True) if resumo_el else "")[:500] or ""
                    noticias_coletadas.append({
                        "titulo": titulo, "resumo": resumo, "categoria": categoria,
                        "fonte": "Folha de S.Paulo", "data": data_hora[0], "hora": data_hora[1], "link": link,
                    })
                    titulos_unicos.add(titulo)
                    novas_nesta_rodada += 1
                except Exception:
                    continue

            if repetidas_nesta_rodada >= 5:
                duplicatas_consecutivas += 1
            else:
                duplicatas_consecutivas = 0

            log.info("  Rodada (clique %d): %d novas, %d antigas, %d repetidas", clique, novas_nesta_rodada, antigas_nesta_rodada, repetidas_nesta_rodada)

            if parar_por_banco:
                log.info("  Parada: 3 noticias ja estavam no banco")
                break
            if antigas_nesta_rodada >= 5:
                log.info("  Parada: muitas noticias antigas (fora de 24h)")
                break
            if duplicatas_consecutivas >= 2:
                log.info("  Parada: muitas noticias repetidas (ja coletadas)")
                break
            if novas_nesta_rodada == 0:
                tentativas_sem_novas += 1
                if tentativas_sem_novas >= 3:
                    log.info("  Parada: 3 rodadas sem noticias novas")
                    break
            else:
                tentativas_sem_novas = 0
            if clique >= max_cliques:
                log.info("  Parada: limite de cliques em Ver mais")
                break

            # Clicar em "Ver mais" (ultimas-noticias)
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                driver.execute_script("""
                    var b = document.querySelectorAll('.banner, [id*="banner"], [class*="banner"], [class*="lgpd"], [id*="lgpd"]');
                    for(var i=0;i<b.length;i++) b[i].remove();
                """)
                botoes = driver.find_elements(By.CSS_SELECTOR, "button.c-button--expand[data-pagination-trigger]")
                if not botoes:
                    log.info("  Parada: botao Ver mais nao encontrado")
                    break
                botao = botoes[0]
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", botao)
                time.sleep(3)
                clique += 1
            except Exception as e:
                err = str(e).lower()
                if "connection" in err or "refused" in err or "10061" in err or "target machine" in err:
                    log.warning("  conexao com o browser caiu; usando noticias ja coletadas.")
                else:
                    log.info("  Parada: botao Ver mais nao clicavel: %s", str(e)[:50])
                break

        # Coleta editorial: colunaseblogs (Painel, Adriana Fernandes, Mônica Bergamo)
        log.info("")
        log.info("  Coletando editoriais (colunaseblogs)...")
        try:
            driver.get(URL_FOLHA_COLUNAS)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='colunas/']"))
            )
            time.sleep(2)
            for _ in range(2):
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    b = driver.find_elements(By.CSS_SELECTOR, "button.c-button--expand[data-pagination-trigger]")
                    if b:
                        driver.execute_script("arguments[0].click();", b[0])
                        time.sleep(2)
                except Exception:
                    break
            soup = BeautifulSoup(driver.page_source, "html.parser")
            links_unicos = {n.get("link") for n in noticias_coletadas if n.get("link")}
            editoriais = _extrair_editoriais_colunaseblogs(soup, titulos_unicos, links_unicos, limite_24h)
            for n in editoriais:
                if links_existentes and n.get("link") in links_existentes:
                    continue
                noticias_coletadas.append(n)
            log.info("    Editoriais colunaseblogs: %d (total: %d)", len(editoriais), len(noticias_coletadas))
        except Exception as e:
            log.warning("  erro ao coletar colunaseblogs: %s", e)

        log.info("")
        log.info("  Total coletado: %d noticias", len(noticias_coletadas))
        log.info("")
        log.info("  Classificando noticias...")

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
            resultado = classificar(noticia["titulo"], resumo=noticia.get("resumo") or "")
            tema = resultado["tema"]
            if tema == "Mundo":
                continue
            noticia["tema_classificado"] = tema
            noticia["score"] = resultado["score"]
            noticia["scores_todos"] = resultado["scores"]
            if tema == NAO_CLASSIFICADO:
                nao_classificadas.append(noticia)
            else:
                noticias_por_tema[tema].append(noticia)

        temas_visiveis = {t: lst for t, lst in noticias_por_tema.items() if t != "Mundo"}

        log.info("")
        log.info("Classificação")
        log.info("-" * 60)
        for tema in sorted(temas_visiveis.keys()):
            log.info("  %-20s %4d", tema, len(temas_visiveis[tema]))
        log.info("  %-20s %4d", "Não classificadas", len(nao_classificadas))

        out_dir = Path(__file__).resolve().parent.parent / "output"
        out_dir.mkdir(exist_ok=True)
        arq_json = out_dir / "folha_classificado_24h.json"
        arq_html = out_dir / "folha_classificado_24h.html"
        resultado_completo = {
            "data_coleta": datetime.now().isoformat(),
            "periodo_horas": 24,
            "total_coletado": len(noticias_coletadas),
            "por_tema": dict(noticias_por_tema),
            "nao_classificadas": nao_classificadas,
        }
        with open(arq_json, "w", encoding="utf-8") as f:
            json.dump(resultado_completo, f, ensure_ascii=False, indent=2)
        intervalo_noticias = None
        if noticias_coletadas:
            datas_ord = sorted(
                datetime.strptime(f"{n['data']} {n['hora']}", "%d/%m/%Y %H:%M") for n in noticias_coletadas
            )
            intervalo_noticias = (datas_ord[0], datas_ord[-1])
        _gerar_html(noticias_por_tema, nao_classificadas, len(noticias_coletadas), arq_html, limite_24h=limite_24h, intervalo_noticias=intervalo_noticias)
        log.info("  JSON: %s", arq_json)
        log.info("  HTML: %s", arq_html)
        log.info("Concluído (%.1fs)", time.time() - t0)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
