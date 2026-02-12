# -*- coding: utf-8 -*-
"""
Gera HTML interativo para revisão e treinamento do classificador.
Você pode marcar cada notícia como correta/errada e indicar o tema correto.
Ao salvar, gera um JSON de feedback que pode ser usado para ajustar as keywords.
"""

import json
from pathlib import Path
from html import escape

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
ARQUIVO_JSON = OUTPUT_DIR / "valor_classificado_24h.json"
ARQUIVO_HTML = OUTPUT_DIR / "revisao_classificacao.html"


def gerar_html_revisao():
    """Gera HTML interativo para revisão manual."""
    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    noticias_por_tema = data.get("por_tema", {})
    nao_classificadas = data.get("nao_classificadas", [])
    todos_temas = list(noticias_por_tema.keys()) + ["Não classificado"]
    
    # Temas disponíveis para correção
    temas_disponiveis = [
        "Governo/Congresso", "Fiscal", "Eleições", "Inflação",
        "Banco Central", "Mercado", "Editorial", "Mundo", "Não classificado"
    ]

    html = []
    html.append("<!DOCTYPE html>")
    html.append('<html lang="pt-BR">')
    html.append('<head>')
    html.append('<meta charset="UTF-8">')
    html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html.append('<title>Revisão de Classificação - Valor</title>')
    html.append('<style>')
    html.append('body{font-family:Segoe UI,sans-serif;margin:20px;background:#f5f5f5;}')
    html.append('.container{max-width:1000px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);}')
    html.append('h1{color:#1a5276;border-bottom:2px solid #1a5276;padding-bottom:8px;}')
    html.append('h2{margin-top:28px;color:#2c3e50;border-bottom:1px solid #ddd;padding-bottom:8px;}')
    html.append('.meta{color:#666;font-size:0.9em;margin-bottom:20px;}')
    html.append('.noticia{margin:12px 0;padding:16px;background:#f9f9f9;border-left:4px solid #3498db;border-radius:4px;}')
    html.append('.noticia.nao{border-left-color:#95a5a6;}')
    html.append('.noticia.correta{border-left-color:#27ae60;background:#e8f5e9;}')
    html.append('.noticia.errada{border-left-color:#e74c3c;background:#ffebee;}')
    html.append('.noticia a{color:#2980b9;text-decoration:none;font-weight:bold;}')
    html.append('.noticia a:hover{text-decoration:underline;}')
    html.append('.resumo{color:#555;font-size:0.95em;margin:8px 0;}')
    html.append('.info{font-size:0.85em;color:#7f8c8d;margin:4px 0;}')
    html.append('.controles{margin-top:12px;padding-top:12px;border-top:1px solid #ddd;}')
    html.append('.controles label{margin-right:12px;font-size:0.9em;}')
    html.append('.controles select{margin-right:16px;padding:4px 8px;}')
    html.append('.controles textarea{width:100%;min-height:60px;margin-top:8px;padding:8px;font-family:inherit;font-size:0.9em;}')
    html.append('#salvar{position:fixed;bottom:20px;right:20px;background:#27ae60;color:white;border:none;padding:12px 24px;border-radius:6px;font-size:16px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.3);}')
    html.append('#salvar:hover{background:#229954;}')
    html.append('.stats{background:#ecf0f1;padding:12px;border-radius:4px;margin:20px 0;}')
    html.append('</style>')
    html.append('</head><body>')
    html.append('<div class="container">')
    html.append('<h1>📝 Revisão de Classificação - Valor Econômico</h1>')
    html.append('<div class="meta">')
    html.append(f'Total: {data.get("total_coletado", 0)} notícias | ')
    html.append(f'Classificadas: {len(data.get("por_tema", {}))} temas | ')
    html.append(f'Não classificadas: {len(nao_classificadas)}')
    html.append('</div>')
    html.append('<div class="stats">')
    html.append('<strong>Instruções:</strong> Para cada notícia, marque se a classificação está <strong>Correta</strong> ou <strong>Errada</strong>. ')
    html.append('Se estiver errada, escolha o tema correto no dropdown. Opcionalmente, adicione comentários. ')
    html.append('Clique em <strong>"Salvar Feedback"</strong> ao final para gerar arquivo de correções.')
    html.append('</div>')

    # Contador para IDs únicos
    contador = 0

    # Notícias classificadas por tema
    for tema in sorted(noticias_por_tema.keys()):
        lista = noticias_por_tema[tema]
        html.append(f'<h2>{escape(tema)} ({len(lista)})</h2>')
        for n in lista:
            contador += 1
            titulo = escape(n.get("titulo", ""))
            link = escape(n.get("link", "#"))
            resumo = escape((n.get("resumo") or "")[:200])
            info = f"{n.get('categoria', '')} | {n.get('hora', '')} | score {n.get('score', 0)}"
            tema_atual = escape(tema)
            
            html.append(f'<div class="noticia" id="n{contador}" data-tema-atual="{tema_atual}">')
            html.append(f'<a href="{link}" target="_blank">{titulo}</a>')
            if resumo:
                html.append(f'<p class="resumo">{resumo}...</p>')
            html.append(f'<p class="info">{escape(info)}</p>')
            html.append('<div class="controles">')
            html.append(f'<label><input type="radio" name="status_{contador}" value="correta" checked> ✓ Correta</label>')
            html.append(f'<label><input type="radio" name="status_{contador}" value="errada"> ✗ Errada</label>')
            html.append(f'<select name="tema_correto_{contador}" id="tema_{contador}" style="display:none;">')
            html.append('<option value="">-- Escolha o tema correto --</option>')
            for t in temas_disponiveis:
                selected = 'selected' if t == tema_atual else ''
                html.append(f'<option value="{escape(t)}" {selected}>{escape(t)}</option>')
            html.append('</select>')
            html.append(f'<textarea name="comentario_{contador}" placeholder="Comentário (opcional): por que está errada? que palavra-chave falta?"></textarea>')
            html.append('</div>')
            html.append('</div>')

    # Não classificadas
    html.append(f'<h2>Não classificadas ({len(nao_classificadas)})</h2>')
    for n in nao_classificadas:
        contador += 1
        titulo = escape(n.get("titulo", ""))
        link = escape(n.get("link", "#"))
        resumo = escape((n.get("resumo") or "")[:200])
        info = f"{n.get('categoria', '')} | {n.get('hora', '')}"
        
        html.append(f'<div class="noticia nao" id="n{contador}" data-tema-atual="Não classificado">')
        html.append(f'<a href="{link}" target="_blank">{titulo}</a>')
        if resumo:
            html.append(f'<p class="resumo">{resumo}...</p>')
        html.append(f'<p class="info">{escape(info)}</p>')
        html.append('<div class="controles">')
        html.append(f'<label><input type="radio" name="status_{contador}" value="correta"> ✓ Correta (deve ficar sem tema)</label>')
        html.append(f'<label><input type="radio" name="status_{contador}" value="errada" checked> ✗ Errada (deveria ter tema)</label>')
        html.append(f'<select name="tema_correto_{contador}" id="tema_{contador}">')
        html.append('<option value="">-- Escolha o tema correto --</option>')
        for t in temas_disponiveis:
            if t != "Não classificado":
                html.append(f'<option value="{escape(t)}">{escape(t)}</option>')
        html.append('</select>')
        html.append(f'<textarea name="comentario_{contador}" placeholder="Comentário: que palavra-chave deveria ter para classificar corretamente?"></textarea>')
        html.append('</div>')
        html.append('</div>')

    # JavaScript para interatividade
    html.append('''
    <script>
        // Mostrar/ocultar dropdown quando marca como errada
        document.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.addEventListener('change', function() {
                const contador = this.name.split('_')[1];
                const select = document.getElementById('tema_' + contador);
                const noticia = document.getElementById('n' + contador);
                
                if (this.value === 'errada') {
                    select.style.display = 'inline-block';
                    select.required = true;
                    noticia.classList.add('errada');
                    noticia.classList.remove('correta');
                } else {
                    select.style.display = 'none';
                    select.required = false;
                    noticia.classList.add('correta');
                    noticia.classList.remove('errada');
                }
            });
        });

        // Salvar feedback
        document.getElementById('salvar').addEventListener('click', function() {
            const feedback = {
                data_revisao: new Date().toISOString(),
                total_noticias: ''' + str(contador) + ''',
                correcoes: []
            };

            for (let i = 1; i <= ''' + str(contador) + '''; i++) {
                const noticia = document.getElementById('n' + i);
                const status = document.querySelector('input[name="status_' + i + '"]:checked')?.value;
                const temaAtual = noticia.dataset.temaAtual;
                const temaCorreto = document.getElementById('tema_' + i)?.value || '';
                const comentario = document.querySelector('textarea[name="comentario_' + i + '"]')?.value || '';
                const titulo = noticia.querySelector('a').textContent;

                if (status === 'errada' || (temaAtual === 'Não classificado' && temaCorreto)) {
                    feedback.correcoes.push({
                        titulo: titulo,
                        tema_atual: temaAtual,
                        tema_correto: temaCorreto,
                        comentario: comentario
                    });
                }
            }

            // Criar e baixar JSON
            const blob = new Blob([JSON.stringify(feedback, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'feedback_classificacao.json';
            a.click();
            URL.revokeObjectURL(url);

            alert('Feedback salvo! Arquivo "feedback_classificacao.json" foi baixado.');
        });
    </script>
    ''')

    html.append('<button id="salvar">💾 Salvar Feedback</button>')
    html.append('</div></body></html>')

    with open(ARQUIVO_HTML, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"HTML de revisão gerado: {ARQUIVO_HTML}")
    print("Abra esse arquivo no navegador, revise as notícias e clique em 'Salvar Feedback' ao final.")


if __name__ == "__main__":
    if not ARQUIVO_JSON.exists():
        print(f"Arquivo {ARQUIVO_JSON} não encontrado.")
        print("Rode primeiro: python test_valor_classificar_todas.py")
        exit(1)
    gerar_html_revisao()
