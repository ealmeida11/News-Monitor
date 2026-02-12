# -*- coding: utf-8 -*-
"""
Gera painel HTML com tabela aprimorada de últimas notícias.
Funcionalidades: busca, filtro por categoria, ordenação, paginação.
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
ARQUIVOS_JSON = [
    OUTPUT_DIR / "valor_classificado_24h.json",
    OUTPUT_DIR / "estadao_classificado_24h.json",
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
}


def _chave_ordem(n):
    d = n.get("data", "")
    h = n.get("hora", "00:00")
    try:
        return datetime.strptime(f"{d} {h}", "%d/%m/%Y %H:%M")
    except Exception:
        return datetime.min


def gerar_painel():
    # Carregar e mesclar todos os JSONs disponíveis (Valor, Estadão)
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
        print("Nenhum dado encontrado em valor_classificado_24h.json nem estadao_classificado_24h.json")
        print("Rode: python test_valor_classificar_todas.py e/ou python test_estadao_classificar_todas.py")
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
    if data_coleta:
        try:
            dt = datetime.fromisoformat(data_coleta.replace("Z", "+00:00"))
            data_formatada = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_formatada = data_coleta[:16]
    else:
        data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Lista de temas únicos para o filtro
    temas_unicos = sorted(set(n.get("tema", "") for n in todas if n.get("tema")))

    # --- HTML ---
    html = []
    html.append("<!DOCTYPE html>")
    html.append('<html lang="pt-BR">')
    html.append("<head>")
    html.append('<meta charset="UTF-8">')
    html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html.append("<title>Newsflow Macro Brasil</title>")
    html.append("<style>")
    html.append("*{margin:0;padding:0;box-sizing:border-box;}")
    html.append("body{font-family:'Segoe UI',-apple-system,sans-serif;background:#f5f7fa;color:#2c3e50;line-height:1.6;}")
    html.append(".header{position:sticky;top:0;z-index:100;background:linear-gradient(135deg,#1a5276 0%,#2980b9 100%);color:#fff;padding:12px 24px;box-shadow:0 2px 8px rgba(0,0,0,.15);}")
    html.append(".header h1{font-size:20px;font-weight:600;margin-bottom:4px;}")
    html.append(".header .meta{font-size:12px;opacity:.9;}")
    html.append(".container{max-width:1600px;margin:0 auto;padding:28px 32px;}")
    html.append(".controls{background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.08);margin-bottom:20px;display:flex;gap:16px;flex-wrap:wrap;align-items:center;}")
    html.append(".controls input[type='text']{flex:1;min-width:250px;padding:10px 14px;border:1px solid #ddd;border-radius:6px;font-size:14px;}")
    html.append(".controls select{padding:10px 14px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;cursor:pointer;}")
    html.append(".controls .count{color:#666;font-size:14px;margin-left:auto;}")
    html.append(".table-wrapper{background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);overflow:hidden;}")
    html.append("table{width:100%;border-collapse:collapse;}")
    html.append("thead{background:#1a5276;color:#fff;}")
    html.append("th{padding:14px 16px;text-align:left;font-size:13px;font-weight:600;cursor:pointer;user-select:none;position:relative;}")
    html.append("th:hover{background:#164a6b;}")
    html.append("th.sortable::after{content:' ↕';opacity:.5;font-size:11px;margin-left:4px;}")
    html.append("th.sort-asc::after{content:' ↑';opacity:1;}")
    html.append("th.sort-desc::after{content:' ↓';opacity:1;}")
    html.append("tbody tr{border-bottom:1px solid #e9ecef;transition:background .15s;}")
    html.append("tbody tr:hover{background:#f8f9fa;}")
    html.append("tbody tr:last-child{border-bottom:none;}")
    html.append("td{padding:14px 16px;font-size:14px;vertical-align:top;}")
    html.append(".titulo-cell{font-weight:500;color:#2c3e50;max-width:400px;}")
    html.append(".resumo-cell{max-width:450px;color:#555;font-size:13px;line-height:1.5;}")
    html.append(".badge{display:inline-block;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:500;color:#fff;white-space:nowrap;}")
    html.append(".link-cell a{color:#2980b9;text-decoration:none;font-weight:500;padding:6px 12px;border:1px solid #2980b9;border-radius:4px;display:inline-block;transition:all .2s;}")
    html.append(".link-cell a:hover{background:#2980b9;color:#fff;}")
    html.append(".fonte-cell{font-size:13px;color:#555;white-space:nowrap;}")
    html.append(".dh-cell{white-space:nowrap;font-size:13px;color:#666;font-family:monospace;}")
    html.append(".pagination{display:flex;justify-content:center;gap:8px;padding:20px;background:#fff;border-top:1px solid #e9ecef;}")
    html.append(".pagination button{padding:8px 14px;border:1px solid #ddd;background:#fff;border-radius:4px;cursor:pointer;font-size:14px;transition:all .2s;}")
    html.append(".pagination button:hover:not(:disabled){background:#2980b9;color:#fff;border-color:#2980b9;}")
    html.append(".pagination button:disabled{opacity:.5;cursor:not-allowed;}")
    html.append(".pagination .active{background:#2980b9;color:#fff;border-color:#2980b9;}")
    html.append("@media (max-width:1200px){.resumo-cell{max-width:300px;}.titulo-cell{max-width:250px;}}")
    html.append("@media (max-width:768px){.container{padding:16px;}.controls{flex-direction:column;align-items:stretch;}.controls .count{margin-left:0;margin-top:8px;}table{font-size:12px;}th,td{padding:10px 8px;}}")
    html.append("</style>")
    html.append("</head><body>")

    periodo_horas = data.get("periodo_horas", 24)
    html.append('<div class="header">')
    html.append("<h1>📡 Newsflow Macro Brasil</h1>")
    html.append(f'<div class="meta">Última atualização: {data_formatada} | Notícias das últimas {periodo_horas} horas</div>')
    html.append("</div>")
    html.append('<div class="container">')

    # Controles: busca e filtro
    html.append('<div class="controls">')
    html.append('<input type="text" id="searchInput" placeholder="🔍 Buscar por título ou resumo..." />')
    html.append('<select id="filterCategoria">')
    html.append('<option value="">Todas as categorias</option>')
    for tema in temas_unicos:
        html.append(f'<option value="{escape(tema)}">{escape(tema)}</option>')
    html.append('</select>')
    html.append('<span class="count" id="resultCount">Mostrando todas as notícias</span>')
    html.append('</div>')

    # Tabela
    html.append('<div class="table-wrapper">')
    html.append('<table id="newsTable">')
    html.append('<thead><tr>')
    html.append('<th class="sortable" data-sort="titulo">Título</th>')
    html.append('<th class="sortable" data-sort="resumo">Resumo</th>')
    html.append('<th class="sortable" data-sort="categoria">Categoria</th>')
    html.append('<th class="sortable" data-sort="fonte">Fonte</th>')
    html.append('<th>Link</th>')
    html.append('<th class="sortable" data-sort="datahora">Data/Hora</th>')
    html.append('</tr></thead>')
    html.append('<tbody id="tableBody">')
    
    for n in todas:
        titulo = escape((n.get("titulo") or "").strip())
        resumo = escape((n.get("resumo") or "").strip())
        tema = (n.get("tema") or "").strip()
        cor = CORES_TEMAS.get(tema, "#95a5a6")
        fonte = (n.get("fonte") or "").strip()
        link = escape((n.get("link") or "#").strip())
        data = (n.get("data") or "").strip()
        hora = (n.get("hora") or "").strip()
        dh = f"{data} {hora}".strip()
        # Atributos para busca/filtro
        html.append(f'<tr data-titulo="{escape(titulo.lower())}" data-resumo="{escape(resumo.lower())}" data-categoria="{escape(tema)}" data-fonte="{escape(fonte.lower())}" data-datahora="{escape(dh)}">')
        html.append(f'<td class="titulo-cell">{titulo}</td>')
        html.append(f'<td class="resumo-cell">{resumo[:300] + ("..." if len(resumo) > 300 else "") if resumo else "—"}</td>')
        html.append(f'<td><span class="badge" style="background:{cor};">{escape(tema) or "—"}</span></td>')
        html.append(f'<td class="fonte-cell">{escape(fonte) or "—"}</td>')
        html.append(f'<td class="link-cell"><a href="{link}" target="_blank">Abrir</a></td>')
        html.append(f'<td class="dh-cell">{escape(dh)}</td>')
        html.append("</tr>")
    
    html.append("</tbody></table>")
    html.append("</div>")

    # JavaScript para busca, filtro, ordenação e paginação
    html.append("<script>")
    html.append("""
    let allRows = Array.from(document.querySelectorAll('#tableBody tr'));
    let currentSort = { col: 'datahora', dir: 'desc' };
    let currentPage = 1;
    const rowsPerPage = 25;

    function updateTable() {
        const search = document.getElementById('searchInput').value.toLowerCase();
        const categoria = document.getElementById('filterCategoria').value.toLowerCase();
        const tbody = document.getElementById('tableBody');
        const countSpan = document.getElementById('resultCount');
        
        let filtered = allRows.filter(row => {
            const titulo = row.dataset.titulo || '';
            const resumo = row.dataset.resumo || '';
            const cat = row.dataset.categoria || '';
            const matchSearch = !search || titulo.includes(search) || resumo.includes(search);
            const matchCat = !categoria || cat.toLowerCase() === categoria;
            return matchSearch && matchCat;
        });
        
        // Ordenação
        filtered.sort((a, b) => {
            const aVal = a.dataset[currentSort.col] || '';
            const bVal = b.dataset[currentSort.col] || '';
            if (currentSort.col === 'datahora') {
                // Parse data/hora para ordenação
                const aDate = parseDateTime(aVal);
                const bDate = parseDateTime(bVal);
                return currentSort.dir === 'asc' ? aDate - bDate : bDate - aDate;
            }
            const cmp = aVal.localeCompare(bVal);
            return currentSort.dir === 'asc' ? cmp : -cmp;
        });
        
        // Paginação
        const totalPages = Math.ceil(filtered.length / rowsPerPage);
        const start = (currentPage - 1) * rowsPerPage;
        const end = start + rowsPerPage;
        const pageRows = filtered.slice(start, end);
        
        tbody.innerHTML = '';
        pageRows.forEach(row => tbody.appendChild(row.cloneNode(true)));
        
        countSpan.textContent = `Mostrando ${start + 1}-${Math.min(end, filtered.length)} de ${filtered.length} notícias`;
        
        updatePagination(totalPages);
        updateSortIndicators();
    }
    
    function parseDateTime(str) {
        // "12/02/2026 13:48" -> timestamp
        const parts = str.trim().split(' ');
        if (parts.length !== 2) return 0;
        const [data, hora] = parts;
        const [d, m, y] = data.split('/');
        const [h, min] = hora.split(':');
        return new Date(y, m-1, d, h, min).getTime();
    }
    
    function updateSortIndicators() {
        document.querySelectorAll('th.sortable').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
            if (th.dataset.sort === currentSort.col) {
                th.classList.add(currentSort.dir === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        });
    }
    
    function updatePagination(totalPages) {
        const pagDiv = document.querySelector('.pagination');
        if (!pagDiv) {
            const wrapper = document.querySelector('.table-wrapper');
            const pag = document.createElement('div');
            pag.className = 'pagination';
            wrapper.appendChild(pag);
        }
        const pag = document.querySelector('.pagination');
        pag.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        const prev = document.createElement('button');
        prev.textContent = '« Anterior';
        prev.disabled = currentPage === 1;
        prev.onclick = () => { currentPage--; updateTable(); };
        pag.appendChild(prev);
        
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                const btn = document.createElement('button');
                btn.textContent = i;
                btn.className = i === currentPage ? 'active' : '';
                btn.onclick = () => { currentPage = i; updateTable(); };
                pag.appendChild(btn);
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                const span = document.createElement('span');
                span.textContent = '...';
                span.style.padding = '8px';
                pag.appendChild(span);
            }
        }
        
        const next = document.createElement('button');
        next.textContent = 'Próxima »';
        next.disabled = currentPage === totalPages;
        next.onclick = () => { currentPage++; updateTable(); };
        pag.appendChild(next);
    }
    
    // Event listeners
    document.getElementById('searchInput').addEventListener('input', () => {
        currentPage = 1;
        updateTable();
    });
    
    document.getElementById('filterCategoria').addEventListener('change', () => {
        currentPage = 1;
        updateTable();
    });
    
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (currentSort.col === col) {
                currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.col = col;
                currentSort.dir = 'asc';
            }
            currentPage = 1;
            updateTable();
        });
    });
    
    // Inicializar
    updateTable();
    """)
    html.append("</script>")
    html.append("</div></body></html>")

    with open(ARQUIVO_PAINEL, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"Painel gerado: {ARQUIVO_PAINEL}")
    print(f"  Notícias: {len(todas)} | Categorias: {len(temas_unicos)}")


if __name__ == "__main__":
    gerar_painel()
