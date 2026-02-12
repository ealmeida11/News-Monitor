# -*- coding: utf-8 -*-
"""
Gera painel HTML: Destaques por Tema (topo) + Tabela Últimas Notícias (abaixo).
Exclui tema Mundo e notícias cuja categoria do site é Mundo.

Uso:
    python gerar_painel_html.py

Gera tests/output/painel_dashboard.html — abra no navegador (sem servidor).
"""

import json
from pathlib import Path
from datetime import datetime
from html import escape

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
ARQUIVO_JSON = OUTPUT_DIR / "valor_classificado_24h.json"
ARQUIVO_PAINEL = OUTPUT_DIR / "painel_dashboard.html"

# Cores por tema (categoria de classificação) — badges e cards
CORES_TEMAS = {
    "Governo/Congresso": "#2980b9",
    "Fiscal": "#c0392b",
    "Eleições": "#8e44ad",
    "Inflação": "#d35400",
    "Banco Central": "#16a085",
    "Mercado": "#27ae60",
    "Editorial": "#7f8c8d",
    "Atividade": "#1abc9c",
}
ORDEM_TEMAS = [
    "Fiscal", "Banco Central", "Inflação", "Governo/Congresso",
    "Eleições", "Mercado", "Atividade", "Editorial",
]
MAX_POR_TEMA = 3


def _chave_ordem(n):
    d = n.get("data", "")
    h = n.get("hora", "00:00")
    try:
        return datetime.strptime(f"{d} {h}", "%d/%m/%Y %H:%M")
    except Exception:
        return datetime.min


def gerar_painel():
    if not ARQUIVO_JSON.exists():
        print(f"Arquivo {ARQUIVO_JSON} não encontrado.")
        print("Rode primeiro: python test_valor_classificar_todas.py")
        return

    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    por_tema_raw = data.get("por_tema", {})
    por_tema = {k: v for k, v in por_tema_raw.items() if k != "Mundo"}
    # Excluir notícias cuja categoria do site é Mundo
    por_tema_filtrado = {}
    for tema, lista in por_tema.items():
        filtrada = [n for n in lista if (n.get("categoria") or "").strip() != "Mundo"]
        if filtrada:
            por_tema_filtrado[tema] = filtrada

    # Lista única ordenada (mais novo primeiro) para a tabela
    todas = []
    for tema, lista in por_tema_filtrado.items():
        for n in lista:
            n_copy = dict(n)
            n_copy["tema"] = tema
            todas.append(n_copy)
    todas.sort(key=_chave_ordem, reverse=True)

    data_coleta = data.get("data_coleta", "")
    if data_coleta:
        try:
            dt = datetime.fromisoformat(data_coleta.replace("Z", "+00:00"))
            data_formatada = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_formatada = data_coleta[:16]
    else:
        data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")

    # --- HTML ---
    html = []
    html.append("<!DOCTYPE html>")
    html.append('<html lang="pt-BR">')
    html.append("<head>")
    html.append('<meta charset="UTF-8">')
    html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html.append("<title>Monitor Macro Brasil</title>")
    html.append("<style>")
    html.append("*{margin:0;padding:0;box-sizing:border-box;}")
    html.append("body{font-family:'Segoe UI',-apple-system,sans-serif;background:#f0f2f5;color:#333;line-height:1.5;}")
    html.append(".header{background:linear-gradient(135deg,#1a5276 0%,#2980b9 100%);color:#fff;padding:20px 28px;}")
    html.append(".header h1{font-size:24px;font-weight:600;}")
    html.append(".header .meta{font-size:13px;opacity:.9;margin-top:6px;}")
    html.append(".container{max-width:1400px;margin:0 auto;padding:24px 28px;}")
    html.append("h2{margin:24px 0 16px;font-size:18px;color:#2c3e50;}")
    html.append(".temas-row{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:24px;}")
    html.append(".tema-card{flex:1;min-width:280px;max-width:400px;background:#fff;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.08);overflow:hidden;}")
    html.append(".tema-header{padding:14px 16px;font-size:15px;font-weight:600;color:#fff;display:flex;justify-content:space-between;align-items:center;}")
    html.append(".tema-body{padding:12px 16px;font-size:14px;}")
    html.append(".tema-body a{color:#2980b9;text-decoration:none;display:block;margin-bottom:8px;}")
    html.append(".tema-body a:hover{text-decoration:underline;}")
    html.append(".tema-body .h{color:#666;font-size:12px;margin-bottom:4px;}")
    html.append("table{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,.08);border-radius:8px;overflow:hidden;}")
    html.append("th{text-align:left;padding:12px 14px;background:#1a5276;color:#fff;font-size:13px;font-weight:600;}")
    html.append("td{padding:12px 14px;border-bottom:1px solid #eee;font-size:14px;vertical-align:top;}")
    html.append("tr:hover td{background:#f8f9fa;}")
    html.append("td a{color:#2980b9;text-decoration:none;}")
    html.append("td a:hover{text-decoration:underline;}")
    html.append(".badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:500;color:#fff;}")
    html.append(".resumo-cell{max-width:380px;color:#555;font-size:13px;line-height:1.45;}")
    html.append(".dh{white-space:nowrap;font-size:13px;color:#666;}")
    html.append("</style>")
    html.append("</head><body>")

    html.append('<div class="header">')
    html.append("<h1>Monitor Macro Brasil</h1>")
    html.append(f'<div class="meta">Última atualização: {data_formatada} | Últimas 24h | Valor Econômico</div>')
    html.append("</div>")
    html.append('<div class="container">')

    # --- Seção 1: Destaques por Tema ---
    html.append("<h2>Destaques por Tema</h2>")
    html.append('<div class="temas-row">')
    for tema in ORDEM_TEMAS:
        if tema not in por_tema_filtrado:
            continue
        lista = por_tema_filtrado[tema]
        lista_ord = sorted(lista, key=_chave_ordem, reverse=True)[:MAX_POR_TEMA]
        cor = CORES_TEMAS.get(tema, "#7f8c8d")
        html.append(f'<div class="tema-card">')
        html.append(f'<div class="tema-header" style="background:{cor};">')
        html.append(f'<span>{escape(tema)}</span><span>{len(lista)}</span>')
        html.append("</div>")
        html.append('<div class="tema-body">')
        for n in lista_ord:
            t = (n.get("titulo") or "")[:70] + ("..." if len(n.get("titulo") or "") > 70 else "")
            html.append(f'<span class="h">{n.get("hora","")}</span>')
            html.append(f'<a href="{escape(n.get("link","#"))}" target="_blank">{escape(t)}</a>')
        html.append("</div></div>")
    html.append("</div>")

    # --- Seção 2: Tabela Últimas Notícias ---
    html.append("<h2>Últimas Notícias</h2>")
    html.append("<table>")
    html.append("<thead><tr>")
    html.append("<th>Título</th><th>Resumo</th><th>Categoria</th><th>Link</th><th>Data/Hora</th>")
    html.append("</tr></thead>")
    html.append("<tbody>")
    for n in todas:
        titulo = escape((n.get("titulo") or "").strip())
        resumo = escape((n.get("resumo") or "").strip()[:250])
        if len((n.get("resumo") or "").strip()) > 250:
            resumo += "..."
        tema = (n.get("tema") or "").strip()
        cor = CORES_TEMAS.get(tema, "#95a5a6")
        link = escape((n.get("link") or "#").strip())
        data = (n.get("data") or "").strip()
        hora = (n.get("hora") or "").strip()
        dh = f"{data} {hora}".strip()
        html.append("<tr>")
        html.append(f'<td>{titulo}</td>')
        html.append(f'<td class="resumo-cell">{resumo if resumo else "—"}</td>')
        html.append(f'<td><span class="badge" style="background:{cor};">{escape(tema) or "—"}</span></td>')
        html.append(f'<td><a href="{link}" target="_blank">Abrir</a></td>')
        html.append(f'<td class="dh">{escape(dh)}</td>')
        html.append("</tr>")
    html.append("</tbody></table>")
    html.append("</div></body></html>")

    with open(ARQUIVO_PAINEL, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"Painel gerado: {ARQUIVO_PAINEL}")
    print(f"  Temas: {len(por_tema_filtrado)} | Notícias na tabela: {len(todas)}")


if __name__ == "__main__":
    gerar_painel()
