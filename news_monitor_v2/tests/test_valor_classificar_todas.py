# -*- coding: utf-8 -*-
"""
Teste: coleta TODAS as notícias do Valor das últimas 18 horas,
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


def noticia_dentro_18h(data, hora):
    """Verifica se uma notícia está dentro das últimas 18 horas."""
    try:
        data_hora_str = f"{data} {hora}"
        data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
        limite_18h = datetime.now() - timedelta(hours=18)
        return data_hora_noticia >= limite_18h
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
    print("  COLETA E CLASSIFICAÇÃO - VALOR (últimas 18 horas)")
    print("=" * 70)
    print(f"  URL: {URL_BASE}")
    print(f"  Período: últimas 18 horas (desde {datetime.now() - timedelta(hours=18):%d/%m/%Y %H:%M})")
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
        noticias_antigas_consecutivas = 0
        limite_paginas = 20

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

                    data_element = artigo.find("span", class_="feed-post-datetime")
                    if not data_element:
                        continue

                    data_hora_texto = data_element.text.strip()
                    data_match = re.search(r"(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})", data_hora_texto)
                    if not data_match:
                        continue

                    data = data_match.group(1)
                    hora = data_match.group(2)

                    # Filtrar por 18 horas
                    if not noticia_dentro_18h(data, hora):
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

            if antigas_nesta_pagina >= 3:
                print("    PARADA: muitas notícias antigas detectadas")
                break
            if novas_nesta_pagina == 0 and pagina > 1:
                print("    PARADA: nenhuma notícia nova")
                break

            pagina += 1

        print()
        print(f"  Total coletado: {len(noticias_coletadas)} notícias")
        print()

        # Classificar cada notícia
        print("  Classificando notícias...")
        noticias_por_tema = defaultdict(list)
        nao_classificadas = []

        for noticia in noticias_coletadas:
            texto = f"{noticia['titulo']} {noticia.get('resumo', '')}".strip()
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

        # Salvar JSON completo
        out_dir = Path(__file__).resolve().parent / "output"
        out_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arq_json = out_dir / f"valor_classificado_18h_{timestamp}.json"
        resultado_completo = {
            "data_coleta": datetime.now().isoformat(),
            "periodo_horas": 18,
            "total_coletado": len(noticias_coletadas),
            "por_tema": {tema: lista for tema, lista in noticias_por_tema.items()},
            "nao_classificadas": nao_classificadas,
        }
        with open(arq_json, "w", encoding="utf-8") as f:
            json.dump(resultado_completo, f, ensure_ascii=False, indent=2)
        print()
        print(f"  JSON completo salvo em: {arq_json}")
        print("=" * 70)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
