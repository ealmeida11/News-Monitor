# -*- coding: utf-8 -*-
"""
Gera painel HTML profissional para o monitor de notícias.
Começa apenas com Valor Econômico; outras fontes serão adicionadas depois.

Uso:
    python gerar_painel_html.py

Lê valor_classificado_24h.json e gera painel_dashboard.html
"""

import json
from pathlib import Path
from datetime import datetime
from html import escape

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
ARQUIVO_JSON = OUTPUT_DIR / "valor_classificado_24h.json"
ARQUIVO_PAINEL = OUTPUT_DIR / "painel_dashboard.html"

# Cores por tema (para visualização)
CORES_TEMAS = {
    "Governo/Congresso": "#3498db",
    "Fiscal": "#e74c3c",
    "Eleições": "#9b59b6",
    "Inflação": "#f39c12",
    "Banco Central": "#16a085",
    "Mercado": "#27ae60",
    "Editorial": "#34495e",
    "Atividade": "#1abc9c",
}


def gerar_painel():
    """Gera painel HTML profissional."""
    if not ARQUIVO_JSON.exists():
        print(f"Arquivo {ARQUIVO_JSON} não encontrado.")
        print("Rode primeiro: python test_valor_classificar_todas.py")
        return

    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    noticias_por_tema = data.get("por_tema", {})
    # Filtrar Mundo e não classificadas
    temas_visiveis = {t: lista for t, lista in noticias_por_tema.items() if t != "Mundo"}
    
    # Ordem preferencial dos temas
    ordem_temas = [
        "Governo/Congresso", "Fiscal", "Eleições", "Inflação",
        "Banco Central", "Mercado", "Editorial", "Atividade"
    ]
    temas_ordenados = [t for t in ordem_temas if t in temas_visiveis]
    temas_ordenados.extend([t for t in sorted(temas_visiveis.keys()) if t not in temas_ordenados])

    html = []
    html.append('<!DOCTYPE html>')
    html.append('<html lang="pt-BR">')
    html.append('<head>')
    html.append('<meta charset="UTF-8">')
    html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html.append('<title>Monitor de Notícias - Dashboard</title>')
    html.append('<style>')
    html.append('*{margin:0;padding:0;box-sizing:border-box;}')
    html.append('body{font-family:"Segoe UI",-apple-system,BlinkMacSystemFont,sans-serif;background:#f0f2f5;color:#333;line-height:1.6;}')
    html.append('.header{background:linear-gradient(135deg,#1a5276 0%,#2980b9 100%);color:#fff;padding:24px 32px;box-shadow:0 2px 8px rgba(0,0,0,.15);}')
    html.append('.header h1{font-size:28px;font-weight:600;margin-bottom:8px;}')
    html.append('.header .meta{font-size:14px;opacity:.9;}')
    html.append('.container{max-width:1400px;margin:0 auto;padding:24px 32px;}')
    html.append('.stats-bar{display:flex;gap:16px;margin-bottom:32px;flex-wrap:wrap;}')
    html.append('.stat-card{background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);flex:1;min-width:180px;}')
    html.append('.stat-card .label{font-size:13px;color:#666;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;}')
    html.append('.stat-card .value{font-size:32px;font-weight:700;color:#1a5276;}')
    html.append('.temas-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:24px;margin-bottom:32px;}')
    html.append('.tema-card{background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden;}')
    html.append('.tema-header{padding:20px;border-bottom:3px solid;font-size:18px;font-weight:600;color:#fff;display:flex;justify-content:space-between;align-items:center;}')
    html.append('.tema-count{background:rgba(255,255,255,.2);padding:4px 12px;border-radius:12px;font-size:14px;}')
    html.append('.tema-body{padding:16px;max-height:600px;overflow-y:auto;}')
    html.append('.noticia-item{padding:12px;margin-bottom:12px;border-left:3px solid #ddd;background:#f9f9f9;border-radius:4px;transition:all .2s;}')
    html.append('.noticia-item:hover{border-left-width:4px;background:#f0f0f0;transform:translateX(2px);}')
    html.append('.noticia-item a{color:#2980b9;text-decoration:none;font-weight:500;font-size:15px;display:block;margin-bottom:6px;}')
    html.append('.noticia-item a:hover{text-decoration:underline;}')
    html.append('.noticia-resumo{color:#666;font-size:13px;margin:6px 0;line-height:1.5;}')
    html.append('.noticia-meta{font-size:11px;color:#999;display:flex;gap:12px;margin-top:8px;}')
    html.append('.noticia-meta span{display:flex;align-items:center;gap:4px;}')
    html.append('@media (max-width:768px){.temas-grid{grid-template-columns:1fr;}.container{padding:16px;}.header{padding:20px 16px;}}')
    html.append('</style>')
    html.append('</head><body>')

    # Header
    data_coleta = data.get("data_coleta", "")
    if data_coleta:
        try:
            dt = datetime.fromisoformat(data_coleta.replace("Z", "+00:00"))
            data_formatada = dt.strftime("%d/%m/%Y %H:%M")
        except:
            data_formatada = data_coleta[:16]
    else:
        data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")

    total_coletado = data.get("total_coletado", 0)
    total_classificadas = sum(len(lista) for lista in temas_visiveis.values())

    html.append('<div class="header">')
    html.append('<h1>📰 Monitor de Notícias - Dashboard</h1>')
    html.append(f'<div class="meta">Última atualização: {data_formatada} | Período: últimas 24 horas</div>')
    html.append('</div>')

    html.append('<div class="container">')

    # Temas
    html.append('<div class="temas-grid">')
    for tema in temas_ordenados:
        lista = temas_visiveis[tema]
        cor = CORES_TEMAS.get(tema, "#7f8c8d")
        html.append(f'<div class="tema-card">')
        html.append(f'<div class="tema-header" style="border-color:{cor};background:{cor};">')
        html.append(f'<span>{escape(tema)}</span>')
        html.append(f'<span class="tema-count">{len(lista)}</span>')
        html.append('</div>')
        html.append('<div class="tema-body">')
        
        if not lista:
            html.append('<p style="color:#999;padding:20px;text-align:center;">Nenhuma notícia neste tema</p>')
        else:
            for n in lista:
                titulo = escape(n.get("titulo", ""))
                link = escape(n.get("link", "#"))
                resumo = escape((n.get("resumo") or "")[:200])
                categoria = escape(n.get("categoria", ""))
                hora = escape(n.get("hora", ""))
                fonte = escape(n.get("fonte", "Valor Econômico"))
                
                html.append('<div class="noticia-item">')
                html.append(f'<a href="{link}" target="_blank">{titulo}</a>')
                if resumo:
                    html.append(f'<div class="noticia-resumo">{resumo}...</div>')
                html.append('<div class="noticia-meta">')
                html.append(f'<span>📅 {hora}</span>')
                html.append(f'<span>📂 {categoria}</span>')
                html.append(f'<span>📰 {fonte}</span>')
                html.append('</div>')
                html.append('</div>')
        
        html.append('</div>')
        html.append('</div>')

    html.append('</div>')
    html.append('</div>')
    html.append('</body></html>')

    with open(ARQUIVO_PAINEL, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"Painel gerado: {ARQUIVO_PAINEL}")
    print(f"  Temas: {len(temas_visiveis)}")
    print(f"  Notícias classificadas: {total_classificadas}")


if __name__ == "__main__":
    gerar_painel()
