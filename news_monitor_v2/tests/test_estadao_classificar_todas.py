# -*- coding: utf-8 -*-
"""
Teste: coleta notícias do Estadão das últimas 24 horas (botão "Carregar mais"),
classifica cada uma por tema e mostra: por tema + não classificadas.

Objetivo: analisar classificação e dar instruções para ajustes.
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


def _extrair_categoria_estadao(link):
    """Categoria a partir da URL do Estadão."""
    url_categories = {
        "/politica/": "Política", "/economia/": "Economia", "/esportes/": "Esportes",
        "/cultura/": "Cultura", "/internacional/": "Internacional", "/sustentabilidade/": "Sustentabilidade",
        "/educacao/": "Educação", "/saude/": "Saúde", "/brasil/": "Brasil", "/tecnologia/": "Tecnologia",
        "/jornal-do-carro/": "Automóveis", "/sao-paulo/": "São Paulo", "/estadao-verifica/": "Fato ou Fake",
        "/opiniao/": "Opinião",
    }
    link_lower = (link or "").lower()
    for url_path, cat_name in url_categories.items():
        if url_path in link_lower:
            return cat_name
    return "Não especificada"


def noticia_dentro_24h(data, hora):
    """Verifica se está dentro das últimas 24 horas. data=DD/MM/YYYY, hora=HH:MM."""
    try:
        data_hora_str = f"{data} {hora}"
        data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
        limite_24h = datetime.now() - timedelta(hours=24)
        return data_hora_noticia >= limite_24h
    except Exception:
        return False


def _gerar_html(noticias_por_tema, nao_classificadas, total_coletado, arq_html):
    """Gera HTML do relatório (por tema + não classificadas) para análise."""
    from html import escape
    linhas = []
    linhas.append("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Estadão - Classificação (24h)</title>")
    linhas.append("body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;} .container{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}")
    linhas.append("h1{color:#c0392b;} h2{margin-top:28px;color:#2c3e50;} .meta{color:#666;font-size:0.9em;margin-bottom:20px;}")
    linhas.append(".noticia{margin:12px 0;padding:12px;background:#f9f9f9;border-left:4px solid #3498db;border-radius:4px;} .noticia.nao{border-left-color:#95a5a6;}")
    linhas.append(".noticia a{color:#2980b9;text-decoration:none;} .resumo{color:#555;font-size:0.95em;margin:6px 0;} .info{font-size:0.85em;color:#7f8c8d;}")
    linhas.append("</style></head><body><div class='container'>")
    linhas.append("<h1>Estadão – Classificação por tema (últimas 24h)</h1>")
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

    URL_BASE = "https://www.estadao.com.br/ultimas/"

    print("=" * 70)
    print("  COLETA E CLASSIFICACAO - ESTADAO (ultimas 24 horas)")
    print("=" * 70)
    print(f"  URL: {URL_BASE}")
    print(f"  Periodo: ultimas 24 horas (desde {datetime.now() - timedelta(hours=24):%d/%m/%Y %H:%M})")
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

        driver.get(URL_BASE)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-component-name='lista-ultimas']"))
        )
        time.sleep(2)

        clique = 0
        tentativas_sem_novas = 0
        antigas_consecutivas = 0
        max_cliques = 15

        while True:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            artigos = soup.find_all("a", attrs={"data-component-name": "lista-ultimas"})

            novas_nesta_rodada = 0
            antigas_nesta_rodada = 0

            for artigo in artigos:
                try:
                    titulo = (artigo.get("title") or "").strip()
                    if not titulo or titulo in titulos_unicos:
                        continue

                    link = artigo.get("href") or "#"
                    categoria = _extrair_categoria_estadao(link)

                    # Excluir categoria "Internacional" (equivalente a Mundo) se quiser; por ora mantemos para análise
                    # categorias_excluidas_estadao = {"Esportes", "Automóveis", "Cultura"}
                    # if categoria in categorias_excluidas_estadao: continue

                    parent_div = artigo.find_parent("div")
                    data_element = parent_div.find("span", class_="date") if parent_div else None
                    if not data_element:
                        continue

                    data_hora_texto = data_element.get_text(strip=True)
                    # Formato: "12/02/2026, 14h30" ou "12/02/2026, 9h05"
                    data_match = re.search(r"(\d{2}/\d{2}/\d{4}),\s*(\d{1,2})h(\d{2})", data_hora_texto)
                    if not data_match:
                        continue

                    data = data_match.group(1)
                    h, m = data_match.group(2), data_match.group(3)
                    hora = f"{int(h):02d}:{m}"

                    if not noticia_dentro_24h(data, hora):
                        antigas_nesta_rodada += 1
                        continue

                    # Estadão não expõe resumo na lista; deixamos None
                    noticia = {
                        "titulo": titulo,
                        "resumo": None,
                        "categoria": categoria,
                        "fonte": "Estadão",
                        "data": data,
                        "hora": hora,
                        "link": link,
                    }
                    titulos_unicos.add(titulo)
                    noticias_coletadas.append(noticia)
                    novas_nesta_rodada += 1
                except Exception:
                    continue

            if antigas_nesta_rodada >= 3:
                antigas_consecutivas += 1
            else:
                antigas_consecutivas = 0

            print(f"  Rodada (clique {clique}): {novas_nesta_rodada} novas, {antigas_nesta_rodada} antigas")

            if antigas_nesta_rodada >= 3:
                print("  PARADA: muitas noticias antigas (fora de 24h)")
                break
            if novas_nesta_rodada == 0:
                tentativas_sem_novas += 1
                if tentativas_sem_novas >= 3:
                    print("  PARADA: 3 rodadas sem noticias novas")
                    break
            else:
                tentativas_sem_novas = 0
            if clique >= max_cliques:
                print("  PARADA: limite de cliques em Carregar mais")
                break

            # Clicar em "Carregar mais"
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                driver.execute_script("""
                    var b = document.querySelectorAll('.banner__container, .banner, [id="banner"]');
                    for(var i=0;i<b.length;i++) b[i].remove();
                """)
                botao = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.see-more[data-component-name='lista-ultimas']"))
                )
                botao.click()
                time.sleep(2)
                clique += 1
            except Exception:
                print("  PARADA: botao Carregar mais nao encontrado ou nao clicavel")
                break

        print()
        print(f"  Total coletado: {len(noticias_coletadas)} noticias")
        print()
        print("  Classificando noticias...")

        noticias_por_tema = defaultdict(list)
        nao_classificadas = []

        for noticia in noticias_coletadas:
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
            for n in lista:
                tit = (n.get("titulo") or "")[:75]
                print(f"    - {tit}{'...' if len(n.get('titulo') or '') > 75 else ''}")
                print(f"      Categoria site: {n.get('categoria', '')} | {n.get('hora', '')} | score {n.get('score', 0)}")
            print()

        print(f"  [{len(nao_classificadas)}] NAO CLASSIFICADAS")
        print("-" * 70)
        if nao_classificadas:
            for n in nao_classificadas:
                tit = (n.get("titulo") or "")[:75]
                print(f"    - {tit}{'...' if len(n.get('titulo') or '') > 75 else ''}")
                print(f"      Categoria site: {n.get('categoria', '')} | {n.get('hora', '')}")
        else:
            print("    (nenhuma)")
        print()

        print("=" * 70)
        print("  RESUMO ESTATISTICO")
        print("=" * 70)
        print(f"  Total coletado: {len(noticias_coletadas)}")
        print(f"  Classificadas: {len(noticias_coletadas) - len(nao_classificadas)}")
        print(f"  Nao classificadas: {len(nao_classificadas)}")
        print()
        print("  Por tema:")
        for tema in sorted(temas_visiveis.keys()):
            print(f"    {tema}: {len(temas_visiveis[tema])}")
        print()

        out_dir = Path(__file__).resolve().parent / "output"
        out_dir.mkdir(exist_ok=True)
        arq_json = out_dir / "estadao_classificado_24h.json"
        arq_html = out_dir / "estadao_classificado_24h.html"

        resultado_completo = {
            "data_coleta": datetime.now().isoformat(),
            "periodo_horas": 24,
            "total_coletado": len(noticias_coletadas),
            "por_tema": dict(noticias_por_tema),
            "nao_classificadas": nao_classificadas,
        }
        with open(arq_json, "w", encoding="utf-8") as f:
            json.dump(resultado_completo, f, ensure_ascii=False, indent=2)
        _gerar_html(noticias_por_tema, nao_classificadas, len(noticias_coletadas), arq_html)

        print(f"  JSON: {arq_json}")
        print(f"  HTML: {arq_html}")
        print("=" * 70)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
