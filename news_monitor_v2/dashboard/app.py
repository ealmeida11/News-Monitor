# -*- coding: utf-8 -*-
"""
Monitor Macro Brasil - Streamlit
Layout: 1) Destaques por Tema (topo)  2) Tabela Últimas Notícias (abaixo)
Exclui tema Mundo e categoria Mundo do site.
"""

import json
from pathlib import Path
from datetime import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

BASE = Path(__file__).resolve().parent.parent
ARQUIVO_JSON = BASE / "tests" / "output" / "valor_classificado_24h.json"

ORDEM_TEMAS = [
    "Fiscal", "Banco Central", "Inflação", "Governo/Congresso",
    "Eleições", "Mercado", "Atividade", "Editorial",
]
ICONES = {
    "Fiscal": "🏛️", "Banco Central": "💰", "Inflação": "📈",
    "Governo/Congresso": "🏛️", "Eleições": "🗳️", "Mercado": "📊",
    "Atividade": "📉", "Editorial": "📰",
}
MAX_POR_TEMA = 3


def _chave_ordem(n):
    d = n.get("data", "")
    h = n.get("hora", "00:00")
    try:
        return datetime.strptime(f"{d} {h}", "%d/%m/%Y %H:%M")
    except Exception:
        return datetime.min


def _carregar_dados():
    """Carrega JSON. Exclui tema Mundo e notícias cuja categoria do site é Mundo."""
    if not ARQUIVO_JSON.exists():
        return [], {}, None
    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    por_tema_raw = data.get("por_tema", {})
    # Excluir tema Mundo
    por_tema = {k: v for k, v in por_tema_raw.items() if k != "Mundo"}
    
    # Dentro de cada tema, excluir notícias cuja categoria do site é "Mundo"
    por_tema_filtrado = {}
    for tema, lista in por_tema.items():
        filtrada = [n for n in lista if (n.get("categoria") or "").strip() != "Mundo"]
        if filtrada:
            por_tema_filtrado[tema] = filtrada
    
    todas = []
    for tema, lista in por_tema_filtrado.items():
        for n in lista:
            n_copy = dict(n)
            n_copy["tema"] = tema
            todas.append(n_copy)
    
    todas.sort(key=_chave_ordem, reverse=True)
    return todas, por_tema_filtrado, data.get("data_coleta")


st.set_page_config(layout="wide", page_title="Monitor Macro Brasil", page_icon="📡")
st_autorefresh(interval=120_000, key="refresh")

st.title("📡 Monitor Macro Brasil")
st.caption("Últimas 24h | Fonte: Valor Econômico")

todas, por_tema, data_coleta = _carregar_dados()
if data_coleta:
    try:
        dt = datetime.fromisoformat(data_coleta.replace("Z", "+00:00"))
        st.caption(f"Última atualização: {dt.strftime('%d/%m/%Y %H:%M')}")
    except Exception:
        pass

if not todas:
    st.warning("Nenhum dado encontrado. Rode: `python tests/test_valor_classificar_todas.py` (e reclassificar_json.py se precisar).")
    st.stop()

# ---------- SEÇÃO 1: DESTAQUES POR TEMA (TOPO) ----------
st.subheader("📂 Destaques por Tema")
st.markdown("---")

def _chave(n):
    return _chave_ordem(n)

# Linha 1: Fiscal, BC, Inflação
t1, t2, t3 = st.columns(3)
for col, tema in [(t1, "Fiscal"), (t2, "Banco Central"), (t3, "Inflação")]:
    with col:
        if tema not in por_tema:
            st.info(f"{ICONES.get(tema,'')} **{tema}**")
            st.caption("Sem notícias nas últimas 24h")
            continue
        lista = sorted(por_tema[tema], key=_chave, reverse=True)[:MAX_POR_TEMA]
        st.info(f"{ICONES.get(tema,'')} **{tema}** ({len(por_tema[tema])})")
        for n in lista:
            h = n.get("hora", "")
            t = (n.get("titulo") or "")[:65] + ("..." if len(n.get("titulo") or "") > 65 else "")
            st.markdown(f"- [{h}] [{t}]({n.get('link','#')})")
        if len(por_tema[tema]) > MAX_POR_TEMA:
            with st.expander("Ver mais"):
                for n in sorted(por_tema[tema], key=_chave, reverse=True)[MAX_POR_TEMA:]:
                    st.markdown(f"- [{n.get('hora','')}] [{n.get('titulo','')[:60]}...]({n.get('link','#')})")

st.markdown("---")
# Linha 2: Governo/Congresso, Eleições, Mercado
t4, t5, t6 = st.columns(3)
for col, tema in [(t4, "Governo/Congresso"), (t5, "Eleições"), (t6, "Mercado")]:
    with col:
        if tema not in por_tema:
            st.success(f"{ICONES.get(tema,'')} **{tema}**")
            st.caption("Sem notícias nas últimas 24h")
            continue
        lista = sorted(por_tema[tema], key=_chave, reverse=True)[:MAX_POR_TEMA]
        st.success(f"{ICONES.get(tema,'')} **{tema}** ({len(por_tema[tema])})")
        for n in lista:
            h = n.get("hora", "")
            t = (n.get("titulo") or "")[:65] + ("..." if len(n.get("titulo") or "") > 65 else "")
            st.markdown(f"- [{h}] [{t}]({n.get('link','#')})")
        if len(por_tema[tema]) > MAX_POR_TEMA:
            with st.expander("Ver mais"):
                for n in sorted(por_tema[tema], key=_chave, reverse=True)[MAX_POR_TEMA:]:
                    st.markdown(f"- [{n.get('hora','')}] [{n.get('titulo','')[:60]}...]({n.get('link','#')})")

st.markdown("---")
# Linha 3: Atividade, Editorial
t7, t8, _ = st.columns(3)
for col, tema in [(t7, "Atividade"), (t8, "Editorial")]:
    with col:
        if tema not in por_tema:
            st.markdown(f"{ICONES.get(tema,'')} **{tema}**")
            st.caption("Sem notícias nas últimas 24h")
            continue
        lista = sorted(por_tema[tema], key=_chave, reverse=True)[:MAX_POR_TEMA]
        st.markdown(f"{ICONES.get(tema,'')} **{tema}** ({len(por_tema[tema])})")
        for n in lista:
            h = n.get("hora", "")
            t = (n.get("titulo") or "")[:65] + ("..." if len(n.get("titulo") or "") > 65 else "")
            st.markdown(f"- [{h}] [{t}]({n.get('link','#')})")
        if len(por_tema[tema]) > MAX_POR_TEMA:
            with st.expander("Ver mais"):
                for n in sorted(por_tema[tema], key=_chave, reverse=True)[MAX_POR_TEMA:]:
                    st.markdown(f"- [{n.get('hora','')}] [{n.get('titulo','')[:60]}...]({n.get('link','#')})")

# ---------- SEÇÃO 2: TABELA ÚLTIMAS NOTÍCIAS (ABAIXO) ----------
st.markdown("---")
st.subheader("🔴 Últimas Notícias")
st.caption("Ordenado do mais novo para o mais antigo")

# Cores por tema (categoria de classificação)
CORES_TEMA = {
    "Fiscal": "#c0392b", "Banco Central": "#16a085", "Inflação": "#d35400",
    "Governo/Congresso": "#2980b9", "Eleições": "#8e44ad", "Mercado": "#27ae60",
    "Atividade": "#1abc9c", "Editorial": "#7f8c8d",
}

# Cabeçalho: Título | Resumo | Categoria | Link | Data/Hora
col_tit, col_res, col_cat, col_link, col_dh = st.columns([2, 2, 0.6, 0.45, 0.5])
with col_tit:
    st.markdown("**Título**")
with col_res:
    st.markdown("**Resumo**")
with col_cat:
    st.markdown("**Categoria**")
with col_link:
    st.markdown("**Link**")
with col_dh:
    st.markdown("**Data/Hora**")
st.markdown("---")

for n in todas:
    titulo = (n.get("titulo") or "").strip()
    resumo = (n.get("resumo") or "").strip()
    link = (n.get("link") or "#").strip()
    data = (n.get("data") or "").strip()
    hora = (n.get("hora") or "").strip()
    tema = (n.get("tema") or "").strip()
    cor = CORES_TEMA.get(tema, "#95a5a6")
    
    c_tit, c_res, c_cat, c_link, c_dh = st.columns([2, 2, 0.6, 0.45, 0.5])
    with c_tit:
        st.markdown(titulo[:120] + ("..." if len(titulo) > 120 else ""))
    with c_res:
        st.caption((resumo[:200] + "...") if len(resumo) > 200 else resumo if resumo else "—")
    with c_cat:
        st.markdown(
            f'<span style="background:{cor};color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;">{tema or "—"}</span>',
            unsafe_allow_html=True,
        )
    with c_link:
        st.markdown(f"[Abrir]({link})")
    with c_dh:
        st.caption(f"{data} {hora}".strip())
    st.markdown("")
