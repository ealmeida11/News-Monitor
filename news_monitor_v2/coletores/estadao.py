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
        "/opiniao/": "Opinião", "/colunas/": "Colunas", "/colunistas/": "Colunistas",
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


def _parse_data_hora_estadao(data_hora_texto, referencia=None):
    """
    Extrai (data, hora) do texto de data do Estadão.
    Formato do site: português, hora 0-24 (24h = meia-noite do dia seguinte).
    Aceita: "12/02/2026, 14h30" ou "12/02/2026 | 14h30" ou "14h5"; "Hoje, 10h41"; "Ontem, 18h00".
    Retorna (data, hora) no formato DD/MM/YYYY e HH:MM, ou (None, None) se não reconhecer.
    """
    ref = referencia or datetime.now()
    # Data explícita: DD/MM/YYYY , ou |  HhMM (hora 0-24)
    m = re.search(r"(\d{2}/\d{2}/\d{4})\s*[,|]\s*(\d{1,2})h(\d{1,2})\b", data_hora_texto.strip())
    if m:
        data = m.group(1)
        h, minu = int(m.group(2)), int(m.group(3))
        if h == 24:  # 24h em PT = meia-noite do dia seguinte
            dt = datetime.strptime(data, "%d/%m/%Y") + timedelta(days=1)
            data = dt.strftime("%d/%m/%Y")
            h = 0
        hora = f"{h:02d}:{minu:02d}"
        return data, hora
    # Hoje, 10h41 ou Hoje 10h41
    m_hoje = re.search(r"hoje\s*[,|]?\s*(\d{1,2})h(\d{1,2})\b", data_hora_texto.strip(), re.I)
    if m_hoje:
        data = ref.strftime("%d/%m/%Y")
        h, minu = int(m_hoje.group(1)), int(m_hoje.group(2))
        if h == 24:
            dt = ref + timedelta(days=1)
            data = dt.strftime("%d/%m/%Y")
            h = 0
        hora = f"{h:02d}:{minu:02d}"
        return data, hora
    # Ontem, 18h00
    m_ontem = re.search(r"ontem\s*[,|]?\s*(\d{1,2})h(\d{1,2})\b", data_hora_texto.strip(), re.I)
    if m_ontem:
        ontem = ref - timedelta(days=1)
        data = ontem.strftime("%d/%m/%Y")
        h, minu = int(m_ontem.group(1)), int(m_ontem.group(2))
        if h == 24:
            data = ref.strftime("%d/%m/%Y")
            h = 0
        hora = f"{h:02d}:{minu:02d}"
        return data, hora
    return None, None


def _gerar_html(noticias_por_tema, nao_classificadas, total_coletado, arq_html, limite_24h=None, intervalo_noticias=None):
    """Gera HTML do relatório (por tema + não classificadas) para análise."""
    from html import escape
    linhas = []
    linhas.append("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'><title>Estadão - Classificação (24h)</title><style>")
    linhas.append("body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;} .container{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}")
    linhas.append("h1{color:#c0392b;} h2{margin-top:28px;color:#2c3e50;} .meta{color:#666;font-size:0.9em;margin-bottom:20px;} .meta.janela{background:#e8f4f8;padding:8px 12px;border-radius:6px;margin-bottom:12px;}")
    linhas.append(".noticia{margin:12px 0;padding:12px;background:#f9f9f9;border-left:4px solid #3498db;border-radius:4px;} .noticia.nao{border-left-color:#95a5a6;}")
    linhas.append(".noticia a{color:#2980b9;text-decoration:none;} .resumo{color:#555;font-size:0.95em;margin:6px 0;} .info{font-size:0.85em;color:#7f8c8d;}")
    linhas.append("</style></head><body><div class='container'>")
    linhas.append("<h1>Estadão – Classificação por tema (últimas 24h)</h1>")
    linhas.append("<p class='meta'><strong>Estadão:</strong> sem resumo no site; classificação apenas pelo título. Categorias excluídas da coleta: Esportes, Cultura, Automóveis, Internacional, Educação, São Paulo.</p>")
    if limite_24h is not None and intervalo_noticias is not None:
        de_dt, ate_dt = intervalo_noticias
        linhas.append(f"<p class='meta janela'><strong>Janela de 24h:</strong> incluídas notícias entre {escape(limite_24h.strftime('%d/%m/%Y %H:%M'))} e agora. "
                      f"<strong>Intervalo das notícias neste relatório:</strong> de {escape(de_dt.strftime('%d/%m/%Y %H:%M'))} até {escape(ate_dt.strftime('%d/%m/%Y %H:%M'))}.</p>")
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
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup

    SELENIUM_GRID_URL = "http://airflow.jgp.com.br:4445"

    URL_BASE = "https://www.estadao.com.br/ultimas/"

    agora = datetime.now()
    limite_24h = agora - timedelta(hours=24)
    print("=" * 70)
    print("  COLETA E CLASSIFICACAO - ESTADAO (ultimas 24 horas)")
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
    for arg in ["--disable-logging", "--silent"]:
        chrome_options.add_argument(arg)

    driver = None
    noticias_coletadas = []
    titulos_unicos = set()
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

        driver.get(URL_BASE)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-component-name='lista-ultimas']"))
        )
        time.sleep(2)

        clique = 0
        tentativas_sem_novas = 0
        antigas_consecutivas = 0
        duplicatas_consecutivas = 0
        max_cliques = 30  # Aumentado para pegar mais notícias das 24h

        while True:
            try:
                soup = BeautifulSoup(driver.page_source, "html.parser")
            except Exception as e:
                err = str(e).lower()
                if "connection" in err or "refused" in err or "10061" in err or "target machine" in err:
                    print("  AVISO: conexao com o browser caiu; usando noticias ja coletadas.")
                break
            artigos = soup.find_all("a", attrs={"data-component-name": "lista-ultimas"})

            novas_nesta_rodada = 0
            antigas_nesta_rodada = 0
            repetidas_nesta_rodada = 0  # já estavam em titulos_unicos (como no stop por "banco" do scraper)

            for artigo in artigos:
                try:
                    titulo = (artigo.get("title") or "").strip()
                    if not titulo:
                        continue
                    if titulo in titulos_unicos:
                        repetidas_nesta_rodada += 1
                        continue

                    link = artigo.get("href") or "#"
                    categoria = _extrair_categoria_estadao(link)

                    # Excluir categorias que geram classificação indevida (ex.: Esportes -> Governo/Congresso por "MP-SP")
                    categorias_excluidas_estadao = {"Esportes", "Automóveis", "Cultura", "Internacional", "Educação", "São Paulo", "Colunas", "Colunistas"}
                    if categoria in categorias_excluidas_estadao:
                        continue

                    parent_div = artigo.find_parent("div")
                    data_element = parent_div.find("span", class_="date") if parent_div else None
                    if not data_element:
                        continue

                    data_hora_texto = data_element.get_text(strip=True)
                    data, hora = _parse_data_hora_estadao(data_hora_texto, referencia=agora)
                    if not data or not hora:
                        continue

                    if not noticia_dentro_24h(data, hora):
                        antigas_nesta_rodada += 1
                        continue

                    if links_existentes and link in links_existentes:
                        ja_no_banco += 1
                        if ja_no_banco >= 3:
                            parar_por_banco = True
                            break
                        continue

                    # Estadão não tem resumo na lista; usamos apenas título na classificação
                    noticia = {
                        "titulo": titulo,
                        "resumo": "",
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

            # Stop por duplicatas: 2 rodadas seguidas com muitas notícias já vistas (como no scraper com banco)
            if repetidas_nesta_rodada >= 5:
                duplicatas_consecutivas += 1
            else:
                duplicatas_consecutivas = 0

            print(f"  Rodada (clique {clique}): {novas_nesta_rodada} novas, {antigas_nesta_rodada} antigas, {repetidas_nesta_rodada} repetidas")

            if parar_por_banco:
                print("  PARADA: 3 noticias ja estavam no banco")
                break
            if antigas_nesta_rodada >= 3:
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
                print("  PARADA: limite de cliques em Carregar mais")
                break

            # Clicar no botão "Carregar mais notícias": <button data-component-name="lista-ultimas" type="button" class="see-more">Carregar mais notícias</button>
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                driver.execute_script("""
                    var b = document.querySelectorAll('.banner__container, .banner, [id="banner"]');
                    for(var i=0;i<b.length;i++) b[i].remove();
                """)
                botao = None
                # Seletor exato do botão do Estadão
                for seletor in [
                    "button.see-more[data-component-name='lista-ultimas']",
                    "button[data-component-name='lista-ultimas'].see-more",
                ]:
                    try:
                        botao = WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                        )
                        break
                    except Exception:
                        continue
                # Fallback: botão cujo texto contém "Carregar mais notícias"
                if not botao:
                    try:
                        botao = driver.find_element(By.XPATH, "//button[contains(., 'Carregar mais notícias')]")
                    except Exception:
                        pass
                if not botao:
                    print("  PARADA: botao Carregar mais nao encontrado")
                    break
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", botao)
                time.sleep(2.5)
                clique += 1
            except Exception as e:
                err = str(e).lower()
                if "connection" in err or "refused" in err or "10061" in err or "target machine" in err:
                    print("  AVISO: conexao com o browser caiu; usando noticias ja coletadas.")
                else:
                    print("  PARADA: botao Carregar mais nao clicavel:", str(e)[:50])
                break

        print()
        print(f"  Total coletado: {len(noticias_coletadas)} noticias")
        # Mostrar intervalo real das notícias coletadas (para confirmar que são das últimas 24h)
        if noticias_coletadas:
            datas_ord = sorted(
                (datetime.strptime(f"{n['data']} {n['hora']}", "%d/%m/%Y %H:%M") for n in noticias_coletadas),
                reverse=True,
            )
            mais_recente = datas_ord[0]
            mais_antiga = datas_ord[-1]
            print(f"  Intervalo das noticias: de {mais_antiga:%d/%m/%Y %H:%M} ate {mais_recente:%d/%m/%Y %H:%M}")
            if mais_antiga < limite_24h:
                print("  AVISO: alguma noticia coletada esta fora da janela de 24h (verifique parsing da data).")
        print()
        print("  Classificando noticias...")

        noticias_por_tema = defaultdict(list)
        nao_classificadas = []

        for noticia in noticias_coletadas:
            # Estadão: sem resumo; classificação só pelo título
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

        out_dir = Path(__file__).resolve().parent.parent / "output"
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
        intervalo_noticias = None
        if noticias_coletadas:
            datas_ord = sorted(
                datetime.strptime(f"{n['data']} {n['hora']}", "%d/%m/%Y %H:%M") for n in noticias_coletadas
            )
            intervalo_noticias = (datas_ord[0], datas_ord[-1])  # (mais_antiga, mais_recente)
        _gerar_html(noticias_por_tema, nao_classificadas, len(noticias_coletadas), arq_html, limite_24h=limite_24h, intervalo_noticias=intervalo_noticias)

        print(f"  JSON: {arq_json}")
        print(f"  HTML: {arq_html}")
        print("=" * 70)

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
