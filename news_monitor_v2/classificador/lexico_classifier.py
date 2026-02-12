# -*- coding: utf-8 -*-
"""
Classificador de notícias por tema usando palavras-chave (léxico).

- Carrega temas e keywords de temas_keywords.json (fácil editar e adicionar novo tema).
- Usa spaCy para lematização em português (ex.: "gastos" → "gasto"); fallback sem spaCy.
- Retorna o tema com maior score; se nenhum passar do limite, retorna "Não classificado".
"""

import json
import re
from pathlib import Path

# Caminho do arquivo de keywords (ao lado deste módulo)
_DIR = Path(__file__).resolve().parent
ARQUIVO_TEMAS = _DIR / "temas_keywords.json"

# Limite mínimo de pontos para considerar uma notícia como do tema (ajustável)
SCORE_MINIMO = 1

# Tema quando nenhum atinge o mínimo
NAO_CLASSIFICADO = "Não classificado"


def _normalizar_texto(texto):
    """Remove acentos opcional e deixa minúsculo para comparação."""
    if not texto or not isinstance(texto, str):
        return ""
    texto = texto.lower().strip()
    # Normalizar espaços
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _tokenizar_simples(texto):
    """Tokenização simples: palavras (letras + números). Sem spaCy."""
    texto = _normalizar_texto(texto)
    return re.findall(r"[a-záàâãéêíóôõúç0-9]+", texto)


def _carregar_temas():
    """Carrega temas e keywords do JSON. Só temas com ativo: true."""
    with open(ARQUIVO_TEMAS, "r", encoding="utf-8") as f:
        dados = json.load(f)
    temas = {}
    for nome, config in dados.items():
        if not isinstance(config, dict):
            continue
        if config.get("ativo", True) is False:
            continue
        kw = config.get("keywords", [])
        if isinstance(kw, list):
            temas[nome] = [k.strip().lower() for k in kw if k and isinstance(k, str)]
    return temas


# --- spaCy (opcional) para lematização ---
_nlp = None


def _inicializar_spacy():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load("pt_core_news_sm")
        return _nlp
    except Exception:
        _nlp = False  # marcamos que tentamos e não deu
        return None


def _lematizar_palavras(texto):
    """Retorna lista de lemas (raiz das palavras) em minúsculo. Sem spaCy: tokens simples."""
    nlp = _inicializar_spacy()
    if not nlp:  # None ou False (spaCy não disponível)
        return _tokenizar_simples(texto)
    texto = _normalizar_texto(texto)
    if not texto:
        return []
    doc = nlp(texto)
    return [t.lemma_.lower() for t in doc if not t.is_punct and not t.is_space]


def _normalizar_keyword(kw):
    """Uma keyword pode ser frase (ex.: 'teto de gastos'). Retorna lista de tokens/lemas."""
    nlp = _inicializar_spacy()
    kw = _normalizar_texto(kw)
    if not kw:
        return []
    if not nlp:  # spaCy não disponível
        return _tokenizar_simples(kw)
    doc = nlp(kw)
    return [t.lemma_.lower() for t in doc if not t.is_punct and not t.is_space]


def _texto_contem_keyword(texto_lemas, keyword_lemas):
    """Verifica se a keyword (como lista de lemas) aparece seguida no texto."""
    if not keyword_lemas or not texto_lemas:
        return False
    # Busca sequência: keyword_lemas dentro de texto_lemas
    for i in range(len(texto_lemas) - len(keyword_lemas) + 1):
        if texto_lemas[i:i + len(keyword_lemas)] == keyword_lemas:
            return True
    return False


def classificar(titulo, resumo="", usar_lematizacao=True):
    """
    Classifica uma notícia em um tema com base em título e resumo.

    Args:
        titulo: str – título da notícia
        resumo: str – resumo/lead (opcional)
        usar_lematizacao: bool – se True, usa spaCy quando disponível

    Returns:
        dict com:
          - "tema": str (nome do tema ou NAO_CLASSIFICADO)
          - "score": int (pontos do tema escolhido)
          - "scores": dict tema -> pontos (para debug/transparência)
    """
    temas = _carregar_temas()
    texto_completo = f"{titulo or ''} {resumo or ''}".strip()
    if not texto_completo:
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": {}}

    if usar_lematizacao:
        texto_lemas = _lematizar_palavras(texto_completo)
    else:
        texto_lemas = _tokenizar_simples(texto_completo)

    scores = {}
    for nome_tema, keywords in temas.items():
        pontos = 0
        for kw in keywords:
            if not kw:
                continue
            kw_tokens = _normalizar_keyword(kw) if usar_lematizacao else _tokenizar_simples(kw)
            if _texto_contem_keyword(texto_lemas, kw_tokens):
                pontos += 1
        if pontos > 0:
            scores[nome_tema] = pontos

    if not scores:
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": {}}

    # Se houver empate, priorizar Mercado quando houver "fluxo cambial"
    texto_lower = texto_completo.lower()
    tem_fluxo_cambial = "fluxo cambial" in texto_lower
    
    if tem_fluxo_cambial and "Mercado" in scores and "Banco Central" in scores:
        if scores["Mercado"] == scores["Banco Central"]:
            # Priorizar Mercado quando houver fluxo cambial
            melhor_tema = "Mercado"
            melhor_score = scores["Mercado"]
        else:
            melhor_tema = max(scores, key=scores.get)
            melhor_score = scores[melhor_tema]
    else:
        melhor_tema = max(scores, key=scores.get)
        melhor_score = scores[melhor_tema]

    if melhor_score < SCORE_MINIMO:
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    return {"tema": melhor_tema, "score": melhor_score, "scores": scores}


def listar_temas_ativos():
    """Retorna lista de nomes dos temas ativos (úteis para UI ou validação)."""
    return list(_carregar_temas().keys())
