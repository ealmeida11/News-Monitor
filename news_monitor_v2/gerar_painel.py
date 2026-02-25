# -*- coding: utf-8 -*-
"""
Gera painel HTML estilo card — layout limpo, mobile-friendly.
Exibe: fonte, título (link embutido), categoria, horário.
Exclui tema Mundo.

Uso direto: python gerar_painel.py (lê JSONs de output/).
Ou: gerar_painel_de_lista(todas, ...) para dados do banco.
"""

import json
from pathlib import Path
from datetime import datetime
from html import escape

# output/ fica em news_monitor_v2/output/
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
ARQUIVOS_JSON = [
    OUTPUT_DIR / "valor_classificado_24h.json",
    OUTPUT_DIR / "estadao_classificado_24h.json",
    OUTPUT_DIR / "folha_classificado_24h.json",
    OUTPUT_DIR / "oglobo_classificado_24h.json",
    OUTPUT_DIR / "cnn_classificado_24h.json",
    OUTPUT_DIR / "metropoles_classificado_24h.json",
]
ARQUIVO_PAINEL = OUTPUT_DIR / "painel_dashboard.html"

CORES_TEMAS = {
    "Governo/Congresso": "#2980b9",
    "Fiscal": "#c0392b",
    "Eleições": "#8e44ad",
    "Inflação": "#d35400",
    "Banco Central": "#16a085",
    "Mercado": "#27ae60",
    "Editorial": "#7f8c8d",
    "Atividade": "#1abc9c",
    "STF": "#2c3e50",
    "Caso Master": "#6c3483",
    "Política": "#2980b9",
    "Economia": "#27ae60",
}


def _chave_ordem(n):
    d = n.get("data", "")
    h = n.get("hora", "00:00")
    try:
        return datetime.strptime(f"{d} {h}", "%d/%m/%Y %H:%M")
    except Exception:
        return datetime.min


def _hora_relativa(data_str, hora_str):
    """Retorna horário em formato relativo: HH:MM, ontem HH:MM, ou DD/MM HH:MM."""
    try:
        dt = datetime.strptime(f"{data_str} {hora_str}", "%d/%m/%Y %H:%M")
        agora = datetime.now()
        if dt.date() == agora.date():
            return hora_str
        elif dt.date() == agora.date().replace(day=agora.day - 1):
            return f"ontem {hora_str}"
        else:
            return f"{dt.strftime('%d/%m')} {hora_str}"
    except Exception:
        return hora_str or ""


def gerar_painel_de_lista(todas, data_formatada=None, periodo_horas=24, arquivo_saida=None):
    """
    Gera o HTML do painel a partir de uma lista de notícias (ex.: vindas do banco).
    Cada item deve ter: titulo, resumo, fonte, categoria, data, hora, link, tema.
    """
    if not todas:
        return
    if data_formatada is None:
        data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")
    if arquivo_saida is None:
        arquivo_saida = ARQUIVO_PAINEL
    arquivo_saida = Path(arquivo_saida)
    _escrever_html_painel(todas, data_formatada, periodo_horas, arquivo_saida)


def _escrever_html_painel(todas, data_formatada, periodo_horas, arquivo_saida):
    """Escreve o HTML do painel em arquivo_saida."""
    total = len(todas)
    fontes = sorted(set(n.get("fonte", "") for n in todas if n.get("fonte")))
    fontes_str = ", ".join(fontes) if fontes else "Valor, Estadão, Folha, O Globo, CNN"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <title>Newsflow Macro Brasil</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=DM+Serif+Display&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #fafafa;
      --surface: #ffffff;
      --text: #1a1a1a;
      --text-muted: #5c5c5c;
      --border: #e5e5e5;
      --accent: #1a5276;
      --accent-soft: #e3f2fd;
      --radius: 8px;
      --shadow: 0 1px 3px rgba(0,0,0,.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 0;
      font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
      font-size: 15px; line-height: 1.5;
      color: var(--text); background: var(--bg);
      min-height: 100vh;
    }}
    .wrap {{ max-width: 720px; margin: 0 auto; padding: 24px 20px 48px; }}
    .header {{
      background: var(--surface); border-radius: var(--radius);
      padding: 24px 28px; margin-bottom: 24px;
      box-shadow: var(--shadow); border: 1px solid var(--border);
    }}
    .header h1 {{
      font-family: 'DM Serif Display', Georgia, serif;
      font-size: 1.75rem; font-weight: 400;
      margin: 0 0 12px 0; color: var(--text);
      letter-spacing: -0.02em;
    }}
    .stats {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
    .stat {{
      background: var(--accent-soft); color: var(--accent);
      padding: 5px 12px; border-radius: 6px;
      font-size: 0.8125rem; font-weight: 500;
    }}
    .meta-bar {{
      display: flex; flex-wrap: wrap; gap: 16px 24px;
      font-size: 0.8125rem; color: var(--text-muted);
      padding-top: 16px; border-top: 1px solid var(--border);
    }}
    .meta-bar strong {{ color: var(--text); font-weight: 500; }}
    .card {{
      background: var(--surface); border-radius: var(--radius);
      padding: 16px 20px; margin-bottom: 10px;
      box-shadow: var(--shadow); border: 1px solid var(--border);
      transition: border-color .15s, box-shadow .15s;
    }}
    .card:hover {{ border-color: #ccc; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .card .fonte {{
      font-size: 0.75rem; font-weight: 600; color: var(--accent);
      text-transform: uppercase; letter-spacing: 0.03em;
      margin-bottom: 4px;
    }}
    .card h2 {{ font-size: 0.9375rem; font-weight: 500; margin: 0 0 6px 0; line-height: 1.35; }}
    .card h2 a {{ color: var(--text); text-decoration: none; }}
    .card h2 a:hover {{ color: var(--accent); text-decoration: underline; }}
    .card .meta {{
      font-size: 0.75rem; color: var(--text-muted);
      display: flex; align-items: center; gap: 6px;
    }}
    .card .tag {{
      display: inline-block; padding: 2px 8px;
      border-radius: 4px; font-size: 0.6875rem;
      font-weight: 500; color: #fff; white-space: nowrap;
    }}
    .footer {{
      margin-top: 40px; padding-top: 20px;
      border-top: 1px solid var(--border);
      font-size: 0.75rem; color: var(--text-muted);
      text-align: center;
    }}
    @media (max-width: 600px) {{
      .wrap {{ padding: 16px 14px 32px; }}
      .header {{ padding: 20px 18px; }}
      .header h1 {{ font-size: 1.5rem; }}
      .card {{ padding: 14px 16px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="header">
      <h1>Newsflow Macro Brasil</h1>
      <div class="stats">
        <span class="stat">{total} notícias</span>
        <span class="stat">Últimas {periodo_horas}h</span>
      </div>
      <div class="meta-bar">
        <span><strong>Fontes:</strong> {escape(fontes_str)}</span>
        <span><strong>Atualizado em</strong> {escape(data_formatada)}</span>
      </div>
    </header>
"""

    for n in todas:
        titulo = escape((n.get("titulo") or "").strip())
        tema = (n.get("tema") or "").strip()
        if tema == "Mundo":
            continue
        cor = CORES_TEMAS.get(tema, "#95a5a6")
        fonte = (n.get("fonte") or "").strip()
        link = escape((n.get("link") or "#").strip())
        data = (n.get("data") or "").strip()
        hora = (n.get("hora") or "").strip()
        hora_rel = escape(_hora_relativa(data, hora))
        tema_esc = escape(tema) if tema else ""

        html += f"""    <article class="card">
      <div class="fonte">{escape(fonte)}</div>
      <h2><a href="{link}" target="_blank" rel="noopener">{titulo}</a></h2>
      <div class="meta">
        {f'<span class="tag" style="background:{cor}">{tema_esc}</span>' if tema_esc else ''}
        <span>{hora_rel}</span>
      </div>
    </article>
"""

    html += """    <div class="footer">Newsflow Macro Brasil — atualização automática a cada 30s</div>
  </div>
</body>
</html>"""

    arquivo_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        f.write(html)


def gerar_painel():
    # Carregar e mesclar todos os JSONs disponíveis
    por_tema_merged = {}
    data_coleta = ""
    periodo_horas = 24
    for arq in ARQUIVOS_JSON:
        if not arq.exists():
            continue
        try:
            with open(arq, "r", encoding="utf-8") as f:
                data = json.load(f)
            por_tema_raw = data.get("por_tema", {})
            for k, v in por_tema_raw.items():
                if k == "Mundo":
                    continue
                filtrada = [n for n in v if (n.get("categoria") or "").strip() != "Mundo"]
                if filtrada:
                    por_tema_merged.setdefault(k, []).extend(filtrada)
            dc = data.get("data_coleta", "")
            if dc and (not data_coleta or dc > data_coleta):
                data_coleta = dc
            periodo_horas = data.get("periodo_horas", 24)
        except Exception as e:
            print(f"Aviso: não foi possível carregar {arq.name}: {e}")

    if not por_tema_merged:
        print("Nenhum dado encontrado em valor/estadao/folha/oglobo/cnn_classificado_24h.json")
        print("Rode: python run_coleta.py (ou execute os coletores em coletores/)")
        return

    todas = []
    for tema, lista in por_tema_merged.items():
        for n in lista:
            n_copy = dict(n)
            n_copy["tema"] = tema
            todas.append(n_copy)
    todas.sort(key=_chave_ordem, reverse=True)

    if not data_coleta:
        data_coleta = datetime.now().isoformat()
    try:
        dt = datetime.fromisoformat(data_coleta.replace("Z", "+00:00"))
        data_formatada = dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        data_formatada = data_coleta[:16]

    _escrever_html_painel(todas, data_formatada, periodo_horas, ARQUIVO_PAINEL)
    print(f"Painel gerado: {ARQUIVO_PAINEL}")
    print(f"  Notícias: {len(todas)}")


if __name__ == "__main__":
    gerar_painel()
