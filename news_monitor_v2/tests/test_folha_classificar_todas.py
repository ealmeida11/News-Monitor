# -*- coding: utf-8 -*-
"""
Teste: coleta notícias da Folha de S.Paulo das últimas 24 horas (botão "Ver mais"),
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


def _extrair_categoria_folha(link):
    """Categoria a partir da URL da Folha."""
    categorias_map = {
        "poder": "Política", "mercado": "Economia", "cotidiano": "Cotidiano",
        "mundo": "Mundo", "esporte": "Esporte", "ilustrada": "Cultura",
        "f5": "Entretenimento", "ambiente": "Ambiente", "ciencia": "Ciência",
        "equilibrioesaude": "Saúde", "educacao": "Educação", "tecnologia": "Tecnologia",
    }
    url_match = re.search(r"folha\.uol\.com\.br/([^/]+)/", link or "")
    if url_match:
        categoria_url = url_match.group(1).lower()
        return categorias_map.get(categoria_url, categoria_url.replace("-", " ").title())
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

    URL_BASE = "https://www1.folha.uol.com.br/ultimas-noticias/"

    agora = datetime.now()
    limite_24h = agora - timedelta(hours=24)
    print("=" * 70)
    print("  COLETA E CLASSIFICACAO - FOLHA DE S.PAULO (ultimas 24 horas)")
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
    for arg in ["--disable-logging", "--log-level=3", "--silent"]:
        chrome_options.add_argument(arg)

    driver = None
    noticias_coletadas = []
    titulos_unicos = set()
    categorias_excluidas_folha = {"Mundo", "Esporte", "Cultura", "Entretenimento", "Educação"}

    try:
        service = ChromeService(ChromeDriverManager().install(), log_output=os.devnull)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        driver.get(URL_BASE)
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
                    print("  AVISO: conexao com o browser caiu; usando noticias ja coletadas.")
                break

            novas_nesta_rodada = 0
            antigas_nesta_rodada = 0
            repetidas_nesta_rodada = 0

            # Notícia principal (só na primeira rodada)
            if clique == 0:
                main_headline = soup.find("a", class_="c-main-headline__url")
                if main_headline:
                    try:
                        titulo_el = main_headline.find("h2", class_="c-main-headline__title")
                        if titulo_el:
                            titulo = titulo_el.get_text(strip=True)
                            if titulo and titulo not in titulos_unicos:
                                link = main_headline.get("href") or "#"
                                categoria = _extrair_categoria_folha(link)
                                if categoria not in categorias_excluidas_folha:
                                    time_el = main_headline.find("time", class_="c-headline__dateline")
                                    if time_el:
                                        data_hora = _processar_data_folha(time_el.get_text(strip=True))
                                        if data_hora and noticia_dentro_24h(data_hora[0], data_hora[1]):
                                            resumo_el = main_headline.find("p", class_="c-headline__standfirst")
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
                    categoria = _extrair_categoria_folha(link)
                    if categoria in categorias_excluidas_folha:
                        continue
                    time_el = artigo.find("time", class_="c-headline__dateline")
                    if not time_el:
                        continue
                    data_hora = _processar_data_folha(time_el.get_text(strip=True))
                    if not data_hora:
                        continue
                    if not noticia_dentro_24h(data_hora[0], data_hora[1]):
                        antigas_nesta_rodada += 1
                        continue
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

            print(f"  Rodada (clique {clique}): {novas_nesta_rodada} novas, {antigas_nesta_rodada} antigas, {repetidas_nesta_rodada} repetidas")

            if antigas_nesta_rodada >= 5:
                print("  PARADA: muitas noticias antigas (fora de 24h)")
                break
            if duplicatas_consecutivas >= 2:
                print("  PARADA: muitas noticias repetidas (ja coletadas)")
                break
            if novas_nesta_rodada == 0:
                tentativas_sem_novas += 1
                if tentativas_sem_novas >= 3:
                    print("  PARADA: 3 rodadas sem noticias novas")
                    break
            else:
                tentativas_sem_novas = 0
            if clique >= max_cliques:
                print("  PARADA: limite de cliques em Ver mais")
                break

            # Clicar em "Ver mais"
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                driver.execute_script("""
                    var b = document.querySelectorAll('.banner, [id*="banner"], [class*="banner"], [class*="lgpd"], [id*="lgpd"]');
                    for(var i=0;i<b.length;i++) b[i].remove();
                """)
                botoes = driver.find_elements(By.CSS_SELECTOR, "button.c-button--expand[data-pagination-trigger]")
                if not botoes:
                    print("  PARADA: botao Ver mais nao encontrado")
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
                    print("  AVISO: conexao com o browser caiu; usando noticias ja coletadas.")
                else:
                    print("  PARADA: botao Ver mais nao clicavel:", str(e)[:50])
                break

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

        out_dir = Path(__file__).resolve().parent / "output"
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
        print(f"  JSON: {arq_json}")
        print(f"  HTML: {arq_html}")
        print("=" * 70)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
