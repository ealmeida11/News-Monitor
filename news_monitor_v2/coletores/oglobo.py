# -*- coding: utf-8 -*-
"""
Teste: coleta notícias do O Globo das últimas 24 horas (paginação por URL),
classifica cada uma por tema e mostra: por tema + não classificadas.

Objetivo: analisar classificação e dar instruções para ajustes.
Não incluído no painel até revisão e aprovação.
"""

import io
import json
import re
import sys
import time
from collections import defaultdict

# Evitar UnicodeEncodeError no console Windows (cp1252)
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


def _calcular_tempo_absoluto(tempo_relativo, referencia=None):
    """
    Converte tempo relativo do O Globo para (data, hora).
    Aceita: "agora", "poucos instantes", "há N minutos", "há N horas".
    Retorna (data, hora) em DD/MM/YYYY e HH:MM, ou (None, None).
    Só retorna se a data calculada estiver dentro das últimas 24h (não só "hoje").
    """
    ref = referencia or datetime.now()
    texto = (tempo_relativo or "").strip().lower()
    try:
        if "agora" in texto or "poucos instantes" in texto:
            tempo_calculado = ref
        elif "minuto" in texto:
            m = re.search(r"\d+", texto)
            minutos = int(m.group()) if m else 0
            tempo_calculado = ref - timedelta(minutes=minutos)
        elif "hora" in texto:
            m = re.search(r"\d+", texto)
            horas = int(m.group()) if m else 0
            tempo_calculado = ref - timedelta(hours=horas)
        else:
            return None, None

        data = tempo_calculado.strftime("%d/%m/%Y")
        hora = tempo_calculado.strftime("%H:%M")
        if not noticia_dentro_24h(data, hora):
            return None, None
        return data, hora
    except Exception:
        return None, None


def _gerar_html(noticias_por_tema, nao_classificadas, total_coletado, arq_html, intervalo_noticias=None):
    """Gera HTML do relatório (por tema + não classificadas) para análise."""
    from html import escape
    linhas = []
    linhas.append("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>O Globo - Classificação (24h)</title><style>")
    linhas.append("body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;} .container{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}")
    linhas.append("h1{color:#c4161c;} h2{margin-top:28px;color:#2c3e50;} .meta{color:#666;font-size:0.9em;margin-bottom:20px;} .meta.janela{background:#e8f4f8;padding:8px 12px;border-radius:6px;margin-bottom:12px;}")
    linhas.append(".noticia{margin:12px 0;padding:12px;background:#f9f9f9;border-left:4px solid #3498db;border-radius:4px;} .noticia.nao{border-left-color:#95a5a6;}")
    linhas.append(".noticia a{color:#2980b9;text-decoration:none;} .resumo{color:#555;font-size:0.95em;margin:6px 0;} .info{font-size:0.85em;color:#7f8c8d;}")
    linhas.append("</style></head><body><div class='container'>")
    linhas.append("<h1>O Globo – Classificação por tema (últimas 24h)</h1>")
    linhas.append("<p class='meta'><strong>O Globo:</strong> data/hora em tempo relativo (há N min/horas). Categorias excluídas: Mundo, Colunas, Colunistas, Esportes.</p>")
    if intervalo_noticias:
        de_dt, ate_dt = intervalo_noticias
        linhas.append(f"<p class='meta janela'><strong>Intervalo das notícias:</strong> de {escape(de_dt.strftime('%d/%m/%Y %H:%M'))} até {escape(ate_dt.strftime('%d/%m/%Y %H:%M'))}.</p>")
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


# Colunistas do O Globo (feed-post-metadata-section) que entram na categoria Editorial
EDITORIAL_AUTORES_GLOBO = {"Bela Megale", "Fábio Graner", "Fabio Graner", "Lauro Jardim", "Miriam Leitão"}

# Blogs editoriais — páginas individuais (sem data na listagem, precisa entrar no artigo)
EDITORIAL_BLOGS_GLOBO = [
    ("https://oglobo.globo.com/blogs/malu-gaspar/", "Malu Gaspar"),
    ("https://oglobo.globo.com/blogs/miriam-leitao/", "Miriam Leitão"),
    ("https://oglobo.globo.com/blogs/lauro-jardim/", "Lauro Jardim"),
    ("https://oglobo.globo.com/blogs/bela-megale/", "Bela Megale"),
]
# Feeds editoriais — com tempo relativo na listagem
EDITORIAL_FEEDS_GLOBO = [
    ("https://oglobo.globo.com/economia/fabio-graner/", "Fábio Graner"),
]


def main():
    import os
    os.environ["WDM_LOG_LEVEL"] = "0"

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup

    SELENIUM_GRID_URL = "http://airflow.jgp.com.br:4445"

    URL_BASE = "https://oglobo.globo.com/ultimas-noticias/"

    agora = datetime.now()
    limite_24h = agora - timedelta(hours=24)
    print("=" * 70)
    print("  COLETA E CLASSIFICACAO - O GLOBO (ultimas 24 horas)")
    print("=" * 70)
    print(f"  URL: {URL_BASE}")
    print(f"  Agora (referencia):  {agora:%d/%m/%Y %H:%M}")
    print(f"  Inclusao: noticias entre {limite_24h:%d/%m/%Y %H:%M} e {agora:%d/%m/%Y %H:%M}")
    print()

    chrome_options = ChromeOptions()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    for arg in ["--disable-logging", "--silent"]:
        chrome_options.add_argument(arg)

    driver = None
    noticias_coletadas = []
    titulos_unicos = set()
    categorias_excluidas_oglobo = {"Mundo", "Colunas", "Colunistas", "Esportes"}
    _out = Path(__file__).resolve().parent.parent / "output"
    _links_file = _out / "links_existentes.txt"
    links_existentes = set()
    if _links_file.exists():
        try:
            with open(_links_file, "r", encoding="utf-8") as f:
                links_existentes = {ln.strip() for ln in f if ln.strip()}
        except Exception:
            pass
    ja_no_banco = 0
    parar_por_banco = False

    try:
        driver = webdriver.Remote(
            command_executor=SELENIUM_GRID_URL,
            options=chrome_options,
        )
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        # ── Editoriais: blogs (entrar em cada artigo para pegar data) ──
        print("  Coletando editoriais (blogs O Globo)...")
        for url_blog, autor_blog in EDITORIAL_BLOGS_GLOBO:
            try:
                driver.get(url_blog)
                time.sleep(3)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                links_blog = []
                for a_el in soup.select("a.bstn-hl-link"):
                    titulo_el = a_el.select_one("h2.bstn-hl-title")
                    titulo = titulo_el.get_text(strip=True) if titulo_el else a_el.get_text(strip=True)
                    href = a_el.get("href", "")
                    if titulo and href and titulo not in titulos_unicos:
                        links_blog.append((titulo, href))
                for a_el in soup.select("a.feed-post-link"):
                    titulo = a_el.get_text(strip=True)
                    href = a_el.get("href", "")
                    if titulo and href and titulo not in titulos_unicos:
                        links_blog.append((titulo, href))
                n_blog = 0
                for titulo, href in links_blog:
                    try:
                        driver.get(href)
                        time.sleep(1.5)
                        art_soup = BeautifulSoup(driver.page_source, "html.parser")
                        time_el = art_soup.find("time", attrs={"itemprop": "datePublished"})
                        if not time_el:
                            time_el = art_soup.find("time", attrs={"datetime": True})
                        if not time_el:
                            continue
                        dt_str = time_el.get("datetime", "")
                        dt = datetime.fromisoformat(dt_str)
                        data = dt.strftime("%d/%m/%Y")
                        hora = dt.strftime("%H:%M")
                        if not noticia_dentro_24h(data, hora):
                            continue
                        if links_existentes and href in links_existentes:
                            continue
                        titulos_unicos.add(titulo)
                        noticias_coletadas.append({
                            "titulo": titulo, "resumo": "", "categoria": "Editorial",
                            "fonte": "O Globo", "data": data, "hora": hora,
                            "link": href, "autor_editorial": autor_blog,
                        })
                        n_blog += 1
                    except Exception:
                        continue
                print(f"    {autor_blog}: {n_blog} artigos")
            except Exception as e:
                print(f"    {autor_blog}: ERRO - {e}")

        # ── Editoriais: feeds (tempo relativo na listagem) ──
        for url_feed, autor_feed in EDITORIAL_FEEDS_GLOBO:
            try:
                driver.get(url_feed)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                n_feed = 0
                for art in soup.find_all("div", class_="feed-post-body"):
                    try:
                        link_el = art.find("a", class_="feed-post-link")
                        if not link_el:
                            continue
                        titulo = link_el.get_text(strip=True)
                        if not titulo or titulo in titulos_unicos:
                            continue
                        link = link_el.get("href", "")
                        tempo_el = art.find("span", class_="feed-post-datetime")
                        if not tempo_el:
                            continue
                        data, hora = _calcular_tempo_absoluto(tempo_el.get_text(strip=True), referencia=agora)
                        if not data or not hora:
                            break
                        if links_existentes and link in links_existentes:
                            continue
                        titulos_unicos.add(titulo)
                        noticias_coletadas.append({
                            "titulo": titulo, "resumo": "", "categoria": "Editorial",
                            "fonte": "O Globo", "data": data, "hora": hora,
                            "link": link, "autor_editorial": autor_feed,
                        })
                        n_feed += 1
                    except Exception:
                        continue
                print(f"    {autor_feed}: {n_feed} artigos")
            except Exception as e:
                print(f"    {autor_feed}: ERRO - {e}")

        print(f"  Editoriais O Globo: {sum(1 for n in noticias_coletadas if n.get('autor_editorial'))} artigos")
        print()

        # ── Últimas notícias ──
        pagina = 1
        max_paginas = 20
        duplicatas_consecutivas = 0

        while pagina <= max_paginas:
            if pagina == 1:
                url = URL_BASE
            else:
                url = f"https://oglobo.globo.com/ultimas-noticias/index/feed/pagina-{pagina}.ghtml"

            print(f"  Acessando pagina {pagina}...")
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
                )
                time.sleep(2)
            except Exception as e:
                err = str(e).lower()
                if "connection" in err or "refused" in err:
                    print("  AVISO: conexao com o browser caiu; usando noticias ja coletadas.")
                else:
                    print(f"  ERRO ao acessar pagina {pagina}: {type(e).__name__}")
                break

            soup = BeautifulSoup(driver.page_source, "html.parser")
            artigos = soup.find_all("div", class_="feed-post-body")

            novas_nesta_pagina = 0
            antigas_nesta_pagina = 0
            repetidas_nesta_pagina = 0

            for artigo in artigos:
                try:
                    link_el = artigo.find("a", class_="feed-post-link")
                    if not link_el:
                        continue
                    titulo = link_el.get_text(strip=True)
                    if not titulo:
                        continue
                    if titulo in titulos_unicos:
                        repetidas_nesta_pagina += 1
                        continue

                    link = link_el.get("href") or "#"
                    cat_el = artigo.find("span", class_="feed-post-metadata-section")
                    categoria = cat_el.get_text(strip=True) if cat_el else "Não especificada"
                    if categoria in categorias_excluidas_oglobo:
                        continue
                    autor_editorial = categoria if categoria in EDITORIAL_AUTORES_GLOBO else None

                    tempo_el = artigo.find("span", class_="feed-post-datetime")
                    if not tempo_el:
                        continue
                    data, hora = _calcular_tempo_absoluto(tempo_el.get_text(strip=True), referencia=agora)
                    if not data or not hora:
                        antigas_nesta_pagina += 1
                        continue

                    if links_existentes and link in links_existentes:
                        ja_no_banco += 1
                        if ja_no_banco >= 3:
                            parar_por_banco = True
                            break
                        continue

                    resumo_el = artigo.find("p", class_="feed-post-body-resumo")
                    resumo = (resumo_el.get_text(strip=True) if resumo_el else "")[:500] or ""

                    item = {
                        "titulo": titulo, "resumo": resumo, "categoria": categoria,
                        "fonte": "O Globo", "data": data, "hora": hora, "link": link,
                    }
                    if autor_editorial:
                        item["autor_editorial"] = autor_editorial
                    noticias_coletadas.append(item)
                    titulos_unicos.add(titulo)
                    novas_nesta_pagina += 1
                    duplicatas_consecutivas = 0
                except Exception:
                    continue

            if repetidas_nesta_pagina >= 5:
                duplicatas_consecutivas += 1
            else:
                duplicatas_consecutivas = 0

            print(f"    {novas_nesta_pagina} novas, {antigas_nesta_pagina} antigas, {repetidas_nesta_pagina} repetidas")

            if parar_por_banco:
                print("  PARADA: 3 noticias ja estavam no banco")
                break
            if antigas_nesta_pagina >= 3:
                print("  PARADA: muitas noticias antigas (fora de 24h)")
                break
            if duplicatas_consecutivas >= 2:
                print("  PARADA: muitas noticias repetidas (ja coletadas)")
                break
            if novas_nesta_pagina == 0 and pagina > 1:
                print("  PARADA: pagina sem noticias novas")
                break
            pagina += 1

        print()
        print(f"  Total coletado: {len(noticias_coletadas)} noticias")
        if noticias_coletadas:
            datas_ord = sorted(
                (datetime.strptime(f"{n['data']} {n['hora']}", "%d/%m/%Y %H:%M") for n in noticias_coletadas),
                reverse=True,
            )
            print(f"  Intervalo das noticias: de {datas_ord[-1]:%d/%m/%Y %H:%M} ate {datas_ord[0]:%d/%m/%Y %H:%M}")
        print()
        print("  Classificando noticias...")

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

        # Resultado no console
        print()
        print("=" * 70)
        print("  RESULTADO DA CLASSIFICACAO")
        print("=" * 70)
        print()
        temas_visiveis = {t: lst for t, lst in noticias_por_tema.items() if t != "Mundo"}
        for tema in sorted(temas_visiveis.keys()):
            lista = temas_visiveis[tema]
            print(f"  [{len(lista)}] {tema}")
            print("-" * 70)
            for n in lista[:15]:
                tit = (n.get("titulo") or "")[:75]
                print(f"    - {tit}{'...' if len(n.get('titulo') or '') > 75 else ''}")
                print(f"      Categoria site: {n.get('categoria', '')} | {n.get('hora', '')} | score {n.get('score', 0)}")
            if len(lista) > 15:
                print(f"    ... e mais {len(lista) - 15}")
            print()
        print(f"  [{len(nao_classificadas)}] NAO CLASSIFICADAS")
        print("-" * 70)
        for n in nao_classificadas[:20]:
            tit = (n.get("titulo") or "")[:75]
            print(f"    - {tit}{'...' if len(n.get('titulo') or '') > 75 else ''}")
            print(f"      Categoria site: {n.get('categoria', '')} | {n.get('hora', '')}")
        if len(nao_classificadas) > 20:
            print(f"    ... e mais {len(nao_classificadas) - 20}")
        print()
        print("=" * 70)
        print("  RESUMO ESTATISTICO")
        print("=" * 70)
        print(f"  Total coletado: {len(noticias_coletadas)}")
        print(f"  Classificadas: {len(noticias_coletadas) - len(nao_classificadas)}")
        print(f"  Nao classificadas: {len(nao_classificadas)}")
        print("  Por tema:")
        for tema in sorted(temas_visiveis.keys()):
            print(f"    {tema}: {len(temas_visiveis[tema])}")
        print()

        out_dir = Path(__file__).resolve().parent.parent / "output"
        out_dir.mkdir(exist_ok=True)
        arq_json = out_dir / "oglobo_classificado_24h.json"
        arq_html = out_dir / "oglobo_classificado_24h.html"
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
        _gerar_html(noticias_por_tema, nao_classificadas, len(noticias_coletadas), arq_html, intervalo_noticias=intervalo_noticias)
        print(f"  JSON: {arq_json}")
        print(f"  HTML: {arq_html}")
        print("=" * 70)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
