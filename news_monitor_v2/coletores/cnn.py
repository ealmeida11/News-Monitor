# -*- coding: utf-8 -*-
"""
Teste: coleta notícias da CNN Brasil das últimas 24 horas (paginação por "próxima página"),
classifica cada uma por tema e gera JSON/HTML como nos outros portais.

URL: https://www.cnnbrasil.com.br/ultimas-noticias/
Título: <h2 class="text-xl font-bold"> dentro de <a>
Categoria: <span class="text-base font-medium text-gray-400">
Data/hora: formato DD/MM/YYYY | HH:MM no bloco da notícia
Paginação: próxima página por URL pagina/2/, pagina/3/ ou botão com seta.
"""

import io
import json
import re
import sys
import time
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classificador.lexico_classifier import classificar, NAO_CLASSIFICADO


def noticia_dentro_24h(data, hora):
    """Verifica se está dentro das últimas 24 horas. data=DD/MM/YYYY, hora=HH:MM."""
    try:
        data_hora_str = f"{data} {hora}"
        data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
        limite_24h = datetime.now() - timedelta(hours=24)
        return data_hora_noticia >= limite_24h
    except Exception:
        return False


def _parse_data_hora_cnn(texto):
    """
    Extrai (data, hora) do texto da CNN. Formato: "12/02/2026 | 17:16" ou "12/02/2026 | 17:04".
    Retorna (data, hora) em DD/MM/YYYY e HH:MM, ou (None, None).
    """
    if not texto:
        return None, None
    m = re.search(r"(\d{2}/\d{2}/\d{4})\s*\|\s*(\d{1,2}:\d{2})\b", texto.strip())
    if m:
        return m.group(1), m.group(2)
    return None, None


def _gerar_html(noticias_por_tema, nao_classificadas, total_coletado, arq_html, limite_24h=None, intervalo_noticias=None):
    """Gera HTML do relatório (por tema + não classificadas) para análise."""
    from html import escape
    linhas = []
    linhas.append("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>CNN Brasil - Classificação (24h)</title><style>")
    linhas.append("body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;} .container{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}")
    linhas.append("h1{color:#cc0000;} h2{margin-top:28px;color:#2c3e50;} .meta{color:#666;font-size:0.9em;margin-bottom:20px;} .meta.janela{background:#e8f4f8;padding:8px 12px;border-radius:6px;margin-bottom:12px;}")
    linhas.append(".noticia{margin:12px 0;padding:12px;background:#f9f9f9;border-left:4px solid #cc0000;border-radius:4px;} .noticia.nao{border-left-color:#95a5a6;}")
    linhas.append(".noticia a{color:#2980b9;text-decoration:none;} .resumo{color:#555;font-size:0.95em;margin:6px 0;} .info{font-size:0.85em;color:#7f8c8d;}")
    linhas.append("</style></head><body><div class='container'>")
    linhas.append("<h1>CNN Brasil – Classificação por tema (últimas 24h)</h1>")
    linhas.append("<p class='meta'><strong>CNN Brasil:</strong> coleta em /ultimas-noticias/ com paginação por página. Classificação pelo título.</p>")
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


def _extrair_noticias_pagina(soup, titulos_unicos, limite_24h, categorias_excluidas):
    """
    Extrai notícias de uma página já parseada (BeautifulSoup).
    Retorna lista de dicts (titulo, link, categoria, data, hora, resumo, fonte).
    Só inclui notícias nas últimas 24h e não duplicadas.
    """
    noticias = []
    # Título está em <a href="..."><h2 class="text-xl font-bold">...</h2></a>
    # Categoria em <span class="text-base font-medium text-gray-400">...</span>
    # Data/hora no formato "DD/MM/YYYY | HH:MM" no mesmo bloco
    for a in soup.find_all("a", href=True):
        if "cnnbrasil.com.br" not in (a.get("href") or ""):
            continue
        h2 = a.find("h2", class_=re.compile(r"text-xl\s+font-bold|font-bold\s+text-xl"))
        if not h2:
            continue
        titulo = (h2.get_text(strip=True) or "").strip()
        if not titulo or titulo in titulos_unicos:
            continue
        link = (a.get("href") or "").strip()
        if not link.startswith("http"):
            link = "https://www.cnnbrasil.com.br" + link if link.startswith("/") else "https://www.cnnbrasil.com.br/" + link
        # Container: subir até um li, article ou div que tenha categoria e data
        container = a.find_parent("li") or a.find_parent("article") or a.find_parent("div", class_=re.compile(r"card|item|post|noticia", re.I))
        if not container:
            container = a.find_parent("div")
        categoria = ""
        data, hora = None, None
        if container:
            span_cat = container.find("span", class_=re.compile(r"text-base\s+font-medium\s+text-gray-400|text-gray-400"))
            if span_cat:
                categoria = (span_cat.get_text(strip=True) or "").strip()
            # Data/hora: texto no formato DD/MM/YYYY | HH:MM
            for elem in container.find_all(string=re.compile(r"\d{2}/\d{2}/\d{4}\s*\|\s*\d{1,2}:\d{2}")):
                texto = str(elem).strip() if elem else ""
                if texto:
                    data, hora = _parse_data_hora_cnn(texto)
                    if data and hora:
                        break
            if not data or not hora:
                for tag in container.find_all(["span", "time", "p"]):
                    texto = tag.get_text(strip=True) or ""
                    if re.search(r"\d{2}/\d{2}/\d{4}\s*\|\s*\d{1,2}:\d{2}", texto):
                        data, hora = _parse_data_hora_cnn(texto)
                        break
        if not data or not hora:
            continue
        if not noticia_dentro_24h(data, hora):
            continue
        if categoria in categorias_excluidas:
            continue
        titulos_unicos.add(titulo)
        noticias.append({
            "titulo": titulo,
            "resumo": "",
            "categoria": categoria or "Não especificada",
            "fonte": "CNN Brasil",
            "data": data,
            "hora": hora,
            "link": link,
        })
    return noticias


# Colunistas da CNN Blogs que entram na categoria Editorial (titulo = "Autor: titulo")
EDITORIAL_AUTORES_CNN = {
    "Caio Junqueira", "Matheus Teixeira", "Teo Cury", "Larissa Rodrigues",
    "Gustavo Uribe", "Isabel Mega", "Thaís Herédia", "Débora Bergamasco",
}
URL_CNN_BLOGS = "https://www.cnnbrasil.com.br/blogs/"
# Blogs individuais (coleta direta na página de cada autor)
EDITORIAL_BLOGS_CNN = [
    ("https://www.cnnbrasil.com.br/blogs/caio-junqueira/", "Caio Junqueira"),
    ("https://www.cnnbrasil.com.br/blogs/matheus-teixeira/", "Matheus Teixeira"),
    ("https://www.cnnbrasil.com.br/blogs/teo-cury/", "Teo Cury"),
    ("https://www.cnnbrasil.com.br/blogs/larissa-rodrigues/", "Larissa Rodrigues"),
    ("https://www.cnnbrasil.com.br/blogs/gustavo-uribe/", "Gustavo Uribe"),
    ("https://www.cnnbrasil.com.br/blogs/isabel-mega/", "Isabel Mega"),
    ("https://www.cnnbrasil.com.br/blogs/thais-heredia/", "Thaís Herédia"),
    ("https://www.cnnbrasil.com.br/blogs/debora-bergamasco/", "Débora Bergamasco"),
]


def _extrair_editoriais_blogs(soup, titulos_unicos, limite_24h):
    """
    Extrai da página de blogs da CNN apenas itens cujo autor está em EDITORIAL_AUTORES_CNN.
    Retorna lista de dicts com autor_editorial preenchido (titulo = "Autor: titulo" será aplicado na classificação).
    """
    noticias = []
    for a in soup.find_all("a", href=True):
        if "cnnbrasil.com.br" not in (a.get("href") or ""):
            continue
        h2 = a.find("h2", class_=re.compile(r"text-xl\s+font-bold|font-bold\s+text-xl"))
        if not h2:
            continue
        titulo = (h2.get_text(strip=True) or "").strip()
        if not titulo or titulo in titulos_unicos:
            continue
        link = (a.get("href") or "").strip()
        if not link.startswith("http"):
            link = "https://www.cnnbrasil.com.br" + link if link.startswith("/") else "https://www.cnnbrasil.com.br/" + link
        container = a.find_parent("li") or a.find_parent("article") or a.find_parent("div", class_=re.compile(r"card|item|post|noticia", re.I))
        if not container:
            container = a.find_parent("div")
        autor = None
        data, hora = None, None
        if container:
            # Autor: span com font-normal text-sm leading-normal text-gray-400 (nome do colunista)
            for span in container.find_all("span", class_=re.compile(r"text-gray-400|font-normal")):
                txt = (span.get_text(strip=True) or "").strip()
                if txt in EDITORIAL_AUTORES_CNN:
                    autor = txt
                    break
            for elem in container.find_all(string=re.compile(r"\d{2}/\d{2}/\d{4}\s*\|\s*\d{1,2}:\d{2}")):
                texto = str(elem).strip() if elem else ""
                if texto:
                    data, hora = _parse_data_hora_cnn(texto)
                    if data and hora:
                        break
            if not data or not hora:
                for tag in container.find_all(["span", "time", "p"]):
                    texto = tag.get_text(strip=True) or ""
                    if re.search(r"\d{2}/\d{2}/\d{4}\s*\|\s*\d{1,2}:\d{2}", texto):
                        data, hora = _parse_data_hora_cnn(texto)
                        break
        if not autor or not data or not hora:
            continue
        if not noticia_dentro_24h(data, hora):
            continue
        titulos_unicos.add(titulo)
        noticias.append({
            "titulo": titulo,
            "resumo": "",
            "categoria": "Editorial",
            "fonte": "CNN Brasil",
            "data": data,
            "hora": hora,
            "link": link,
            "autor_editorial": autor,
        })
    return noticias


def main():
    import os
    os.environ["WDM_LOG_LEVEL"] = "0"

    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup

    URL_BASE = "https://www.cnnbrasil.com.br/ultimas-noticias/"

    agora = datetime.now()
    limite_24h = agora - timedelta(hours=24)
    categorias_excluidas_cnn = {
        "Esportes", "BBB", "Entretenimento", "Carnaval", "Celebridades", "Música", "Cinema", "Televisão",
        "Streaming", "Shows", "Horóscopo", "Viagem & Gastronomia", "Viagem", "Gastronomia",
        "Olimpíadas", "Minas Gerais", "Internacional", "Ceará",
    }

    print("=" * 70)
    print("  COLETA E CLASSIFICACAO - CNN BRASIL (ultimas 24 horas)")
    print("=" * 70)
    print(f"  URL: {URL_BASE}")
    print(f"  Agora (referencia):  {agora:%d/%m/%Y %H:%M}")
    print(f"  Inclusao: noticias entre {limite_24h:%d/%m/%Y %H:%M} e {agora:%d/%m/%Y %H:%M}")
    print()

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    for arg in ["--disable-logging", "--silent"]:
        chrome_options.add_argument(arg)

    driver = None
    noticias_coletadas = []
    titulos_unicos = set()
    max_paginas = 20
    _out = Path(__file__).resolve().parent.parent / "output"
    _links_file = _out / "links_existentes.txt"
    links_existentes = set()
    if _links_file.exists():
        try:
            with open(_links_file, "r", encoding="utf-8") as f:
                links_existentes = {ln.strip() for ln in f if ln.strip()}
        except Exception:
            pass

    try:
        service = ChromeService(ChromeDriverManager().install(), log_output=os.devnull)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        for num_pag in range(1, max_paginas + 1):
            url = URL_BASE if num_pag == 1 else f"{URL_BASE}pagina/{num_pag}/"
            print(f"  Página {num_pag}: {url}")
            try:
                driver.get(url)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h2"))
                )
                time.sleep(2)
            except Exception as e:
                print(f"  AVISO: erro ao carregar página {num_pag}: {e}")
                break

            soup = BeautifulSoup(driver.page_source, "html.parser")
            novas = _extrair_noticias_pagina(soup, titulos_unicos, limite_24h, categorias_excluidas_cnn)
            noticias_coletadas.extend(novas)
            print(f"    -> {len(novas)} novas nesta página (total acumulado: {len(noticias_coletadas)})")
            if len(novas) == 0 and num_pag > 1:
                print("  PARADA: página sem notícias novas")
                break
            if num_pag >= max_paginas:
                print("  PARADA: limite de páginas")
                break

            # Próxima página: tentar clicar no botão "próxima" (seta) ou seguir por URL
            if num_pag < max_paginas:
                next_url = f"{URL_BASE}pagina/{num_pag + 1}/"
                time.sleep(1)

        # Coleta editorial: blogs individuais CNN (cada página de autor)
        print()
        print("  Coletando editoriais (blogs individuais CNN)...")
        for url_blog, autor_blog in EDITORIAL_BLOGS_CNN:
            try:
                driver.get(url_blog)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                n_blog = 0
                for a_el in soup.find_all("a", href=True):
                    if "cnnbrasil.com.br" not in (a_el.get("href") or ""):
                        continue
                    h2 = a_el.find("h2", class_=re.compile(r"text-xl\s+font-bold|font-bold\s+text-xl"))
                    if not h2:
                        continue
                    titulo = h2.get_text(strip=True)
                    if not titulo or titulo in titulos_unicos:
                        continue
                    link = (a_el.get("href") or "").strip()
                    if not link.startswith("http"):
                        link = "https://www.cnnbrasil.com.br" + link
                    container = a_el.find_parent("li") or a_el.find_parent("article") or a_el.find_parent("div")
                    data, hora = None, None
                    if container:
                        time_el = container.find("time", attrs={"datetime": True})
                        if time_el:
                            dt_str = time_el.get("datetime", "")
                            m = re.search(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})", dt_str)
                            if m:
                                data = f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
                                hora = f"{m.group(4)}:{m.group(5)}"
                    if not data or not hora:
                        continue
                    if not noticia_dentro_24h(data, hora):
                        continue
                    if links_existentes and link in links_existentes:
                        continue
                    titulos_unicos.add(titulo)
                    noticias_coletadas.append({
                        "titulo": titulo, "resumo": "", "categoria": "Editorial",
                        "fonte": "CNN Brasil", "data": data, "hora": hora,
                        "link": link, "autor_editorial": autor_blog,
                    })
                    n_blog += 1
                print(f"    {autor_blog}: {n_blog} artigos")
            except Exception as e:
                print(f"    {autor_blog}: ERRO - {e}")

        # Coleta editorial: listagem geral de blogs CNN
        print()
        print("  Coletando editoriais (listagem blogs CNN)...")
        for num_pag in range(1, 4):
            url_blogs = URL_CNN_BLOGS if num_pag == 1 else f"{URL_CNN_BLOGS}pagina/{num_pag}/"
            try:
                driver.get(url_blogs)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h2"))
                )
                time.sleep(2)
            except Exception as e:
                print(f"  AVISO: erro ao carregar blogs página {num_pag}: {e}")
                break
            soup = BeautifulSoup(driver.page_source, "html.parser")
            editoriais = _extrair_editoriais_blogs(soup, titulos_unicos, limite_24h)
            for n in editoriais:
                if links_existentes and n.get("link") in links_existentes:
                    continue
                noticias_coletadas.append(n)
            print(f"    Blogs p.{num_pag}: {len(editoriais)} editoriais (total acumulado: {len(noticias_coletadas)})")
            if len(editoriais) == 0 and num_pag > 1:
                break
            time.sleep(1)

        print()
        print(f"  Total coletado: {len(noticias_coletadas)} notícias")
        if noticias_coletadas:
            datas_ord = sorted(
                (datetime.strptime(f"{n['data']} {n['hora']}", "%d/%m/%Y %H:%M") for n in noticias_coletadas),
                reverse=True,
            )
            mais_recente = datas_ord[0]
            mais_antiga = datas_ord[-1]
            print(f"  Intervalo: de {mais_antiga:%d/%m/%Y %H:%M} até {mais_recente:%d/%m/%Y %H:%M}")
        print()
        print("  Classificando notícias...")

        noticias_por_tema = defaultdict(list)
        nao_classificadas = []

        for noticia in noticias_coletadas:
            autor_ed = noticia.get("autor_editorial")
            if autor_ed:
                noticia["titulo"] = f"{autor_ed}: {noticia['titulo']}"
                noticia["tema_classificado"] = "Editorial"
                noticia["score"] = 1
                noticia["scores_todos"] = {}
                noticias_por_tema["Editorial"].append(noticia)
                continue
            resultado = classificar(noticia["titulo"], resumo="")
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

        print()
        print("=" * 70)
        print("  RESULTADO DA CLASSIFICACAO")
        print("=" * 70)
        temas_visiveis = {t: lst for t, lst in noticias_por_tema.items() if t != "Mundo"}
        for tema in sorted(temas_visiveis.keys()):
            lista = temas_visiveis[tema]
            print(f"  [{len(lista)}] {tema}")
        print(f"  [{len(nao_classificadas)}] NAO CLASSIFICADAS")
        print()

        out_dir = Path(__file__).resolve().parent.parent / "output"
        out_dir.mkdir(exist_ok=True)
        arq_json = out_dir / "cnn_classificado_24h.json"
        arq_html = out_dir / "cnn_classificado_24h.html"

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
            intervalo_noticias = (datas_ord[-1], datas_ord[0])
        _gerar_html(noticias_por_tema, nao_classificadas, len(noticias_coletadas), arq_html, limite_24h=limite_24h, intervalo_noticias=intervalo_noticias)

        print(f"  JSON: {arq_json}")
        print(f"  HTML: {arq_html}")
        print("=" * 70)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
