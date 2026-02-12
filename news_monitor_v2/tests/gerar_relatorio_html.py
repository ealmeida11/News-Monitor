# -*- coding: utf-8 -*-
"""
Gera relatório HTML a partir do último JSON de classificação do Valor (18h).
Uso: python gerar_relatorio_html.py
Abra o .html gerado em tests/output/ no navegador.
"""

import json
from pathlib import Path
from html import escape

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def gerar_html(arq_json, arq_html):
    with open(arq_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    noticias_por_tema = data.get("por_tema", {})
    nao_classificadas = data.get("nao_classificadas", [])
    total_coletado = data.get("total_coletado", 0)
    data_coleta = data.get("data_coleta", "")[:19].replace("T", " ")

    linhas = []
    linhas.append("<!DOCTYPE html>")
    linhas.append("<html lang=\"pt-BR\">")
    linhas.append("<head><meta charset=\"UTF-8\"><title>Valor - Classificação por tema (24h)</title>")
    linhas.append("<style>")
    linhas.append("body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;}")
    linhas.append(".container{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}")
    linhas.append("h1{color:#1a5276;border-bottom:2px solid #1a5276;padding-bottom:8px;}")
    linhas.append("h2{margin-top:28px;color:#2c3e50;}")
    linhas.append(".meta{color:#666;font-size:0.9em;margin-bottom:20px;}")
    linhas.append(".noticia{margin:12px 0;padding:12px;background:#f9f9f9;border-left:4px solid #3498db;border-radius:4px;}")
    linhas.append(".noticia.nao{border-left-color:#95a5a6;}")
    linhas.append(".noticia a{color:#2980b9;text-decoration:none;}")
    linhas.append(".noticia a:hover{text-decoration:underline;}")
    linhas.append(".resumo{color:#555;font-size:0.95em;margin:6px 0;}")
    linhas.append(".info{font-size:0.85em;color:#7f8c8d;}")
    linhas.append("</style>")
    linhas.append("</head><body><div class=\"container\">")
    linhas.append("<h1>Valor Econômico – Classificação por tema</h1>")
    periodo = data.get("periodo_horas", 24)
    linhas.append(f"<p class=\"meta\">Coleta: {escape(data_coleta)} | Últimas {periodo}h | Total: {total_coletado} | "
                  f"Classificadas: {total_coletado - len(nao_classificadas)} | "
                  f"Não classificadas: {len(nao_classificadas)}</p>")

    for tema in sorted(noticias_por_tema.keys()):
        lista = noticias_por_tema[tema]
        linhas.append(f"<h2>{escape(tema)} ({len(lista)})</h2>")
        for n in lista:
            titulo = escape(n.get("titulo", ""))
            link = escape(n.get("link", "#"))
            resumo = escape((n.get("resumo") or "")[:300])
            info = f"{n.get('categoria', '')} | {n.get('hora', '')} | score {n.get('score', 0)}"
            linhas.append("<div class=\"noticia\">")
            linhas.append(f"<a href=\"{link}\" target=\"_blank\">{titulo}</a>")
            if resumo:
                linhas.append(f"<p class=\"resumo\">{resumo}</p>")
            linhas.append(f"<p class=\"info\">{escape(info)}</p>")
            linhas.append("</div>")

    linhas.append(f"<h2>Não classificadas ({len(nao_classificadas)})</h2>")
    for n in nao_classificadas:
        titulo = escape(n.get("titulo", ""))
        link = escape(n.get("link", "#"))
        resumo = escape((n.get("resumo") or "")[:300])
        info = f"{n.get('categoria', '')} | {n.get('hora', '')}"
        linhas.append("<div class=\"noticia nao\">")
        linhas.append(f"<a href=\"{link}\" target=\"_blank\">{titulo}</a>")
        if resumo:
            linhas.append(f"<p class=\"resumo\">{resumo}</p>")
        linhas.append(f"<p class=\"info\">{escape(info)}</p>")
        linhas.append("</div>")

    linhas.append("</div></body></html>")
    with open(arq_html, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    # Procurar primeiro pelo arquivo com nome fixo
    arq_json = OUTPUT_DIR / "valor_classificado_24h.json"
    if not arq_json.exists():
        # Fallback: procurar por arquivos com timestamp
        jsons = sorted(OUTPUT_DIR.glob("valor_classificado_24h_*.json"), reverse=True)
        if not jsons:
            jsons = sorted(OUTPUT_DIR.glob("valor_classificado_18h_*.json"), reverse=True)
        if not jsons:
            print("Nenhum arquivo valor_classificado_24h.json encontrado em tests/output/")
            print("Rode antes: python test_valor_classificar_todas.py")
            exit(1)
        arq_json = jsons[0]
    
    arq_html = OUTPUT_DIR / "valor_classificado_24h.html"
    gerar_html(arq_json, arq_html)
    print(f"Relatório gerado: {arq_html}")
    print("Abra esse arquivo no navegador.")
