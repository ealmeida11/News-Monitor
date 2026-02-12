# -*- coding: utf-8 -*-
"""
Teste: coleta SOMENTE a última (mais recente) notícia do Valor Econômico
na página de últimas notícias, no formato atual.

Objetivo: ver exatamente quais informações conseguimos extrair hoje.
"""

import json
import re
import sys
from pathlib import Path

# Dependências do projeto principal
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    import time
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

    URL = "https://valor.globo.com/ultimas-noticias/"

    print("=" * 60)
    print("  TESTE VALOR – UMA NOTÍCIA (a mais recente na página)")
    print("=" * 60)
    print(f"  URL: {URL}")
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
    try:
        service = ChromeService(ChromeDriverManager().install(), log_output=os.devnull)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        print("  Acessando página...")
        driver.get(URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "feed-post-body"))
        )
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        artigos = soup.find_all("div", class_="feed-post-body")

        if not artigos:
            print("  Nenhum elemento 'feed-post-body' encontrado.")
            return

        # Pegar só o primeiro artigo (última notícia)
        artigo = artigos[0]

        # --- Extração no formato atual do scraper ---
        link_element = artigo.find("a", class_="feed-post-link")
        titulo = link_element.text.strip() if link_element else None
        link = link_element.get("href") if link_element else None

        categoria_element = artigo.find("span", class_="feed-post-metadata-section")
        categoria = categoria_element.text.strip() if categoria_element else None

        data_element = artigo.find("span", class_="feed-post-datetime")
        data_hora_texto = data_element.text.strip() if data_element else None
        data, hora = None, None
        if data_hora_texto:
            data_match = re.search(r"(\d{2}/\d{2}/\d{4}),\s*(\d{2}:\d{2})", data_hora_texto)
            if data_match:
                data = data_match.group(1)
                hora = data_match.group(2)

        # Resumo (feed-post-body-resumo)
        resumo_element = artigo.find("p", class_="feed-post-body-resumo")
        resumo = resumo_element.text.strip() if resumo_element else None

        # Objeto no formato que usamos hoje + resumo
        noticia = {
            "titulo": titulo,
            "resumo": resumo,
            "categoria": categoria,
            "fonte": "Valor Econômico",
            "data": data,
            "hora": hora,
            "link": link,
        }

        # Remover chaves com valor None para ficar claro o que veio vazio
        noticia_limpa = {k: v for k, v in noticia.items() if v is not None}

        print("  O QUE CONSEGUIMOS PEGAR NO FORMATO ATUAL:")
        print("-" * 60)
        for chave, valor in noticia_limpa.items():
            print(f"  {chave}:")
            print(f"    {valor}")
        print("-" * 60)
        print("  JSON (formato atual):")
        print(json.dumps(noticia_limpa, ensure_ascii=False, indent=2))
        print()

        # Salvar em arquivo para inspeção
        out_dir = Path(__file__).resolve().parent / "output"
        out_dir.mkdir(exist_ok=True)
        arq_json = out_dir / "valor_uma_noticia_formato_atual.json"
        with open(arq_json, "w", encoding="utf-8") as f:
            json.dump(noticia_limpa, f, ensure_ascii=False, indent=2)
        print(f"  Salvo em: {arq_json}")

        # Opcional: salvar HTML do primeiro bloco para ver se há mais dados
        arq_html = out_dir / "valor_uma_noticia_bloco_html.txt"
        with open(arq_html, "w", encoding="utf-8") as f:
            f.write(artigo.prettify())
        print(f"  HTML do bloco da notícia salvo em: {arq_html}")
        print("  (abrir para inspecionar se existe mais algum campo útil na página)")
        print("=" * 60)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
