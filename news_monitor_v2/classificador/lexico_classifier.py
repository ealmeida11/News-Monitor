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

    texto_lower = texto_completo.lower()
    # Priorizar Mercado quando houver bitcoin/cripto (evitar classificar como Inflação por "preços" no resumo)
    tem_cripto = any(x in texto_lower for x in ["bitcoin", "criptomoeda", "criptomoedas", "crypto", "btc", "ethereum"])
    # Priorizar Mercado quando a notícia é sobre bolsas/fechamento/balanços (inflação no texto = dado que o mercado acompanha)
    contexto_bolsa = any(x in texto_lower for x in ["bolsas", "bolsa fech", "fecham em", "fechamento", "pregão", "balanços", "balanço ", "ibovespa", "ações em", "dólar em"])
    # Priorizar Mercado quando fala de ativo/commodity (ouro, petróleo) e movimento de preço — inflação no texto é dado, não tema
    contexto_ativo = any(x in texto_lower for x in ["ouro", "petróleo", "petroleo", "commodities"]) and any(x in texto_lower for x in ["avanço", "avanco", "alta", "queda", " sobe", " sobe ", " cai", " cai ", "valoriza", "desvaloriza"])
    if tem_cripto and "Mercado" in scores:
        melhor_tema = "Mercado"
        melhor_score = scores["Mercado"]
    elif contexto_ativo and "Mercado" in scores:
        melhor_tema = "Mercado"
        melhor_score = scores["Mercado"]
    elif contexto_bolsa and "Mercado" in scores and "Inflação" in scores:
        melhor_tema = "Mercado"
        melhor_score = scores["Mercado"]
    else:
        # Se houver empate, priorizar Mercado quando houver "fluxo cambial"
        tem_fluxo_cambial = "fluxo cambial" in texto_lower
        if tem_fluxo_cambial and "Mercado" in scores and "Banco Central" in scores:
            if scores["Mercado"] == scores["Banco Central"]:
                melhor_tema = "Mercado"
                melhor_score = scores["Mercado"]
            else:
                melhor_tema = max(scores, key=scores.get)
                melhor_score = scores[melhor_tema]
        else:
            melhor_tema = max(scores, key=scores.get)
            melhor_score = scores[melhor_tema]

    # Prioridade: Caso Master sobre Governo/Congresso quando a notícia é sobre Vorcaro/Master (ex.: depoimento ao Senado)
    if melhor_tema == "Governo/Congresso" and "Caso Master" in scores and scores["Caso Master"] >= 1:
        if "vorcaro" in texto_lower or "banco master" in texto_lower or "credcesta" in texto_lower or "daniel vorcaro" in texto_lower:
            melhor_tema = "Caso Master"
            melhor_score = scores["Caso Master"]

    if melhor_score < SCORE_MINIMO:
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    # Exclusão: leilão de serviços de remoção/guarda de veículos (governo) não é "Atividade" econômica
    if melhor_tema == "Atividade":
        if "leilão" in texto_lower and ("remoção" in texto_lower or "guarda" in texto_lower):
            return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    # Eleições: só classificar se score >= 2 (evitar matches fracos)
    if melhor_tema == "Eleições" and melhor_score < 2:
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    # STF: não classificar quando "corte" e "gastos" (ex.: "corte de gastos"); usar segundo tema
    if melhor_tema == "STF" and "corte" in texto_lower and "gastos" in texto_lower:
        scores_sem_stf = {k: v for k, v in scores.items() if k != "STF"}
        if scores_sem_stf:
            melhor_tema = max(scores_sem_stf, key=scores_sem_stf.get)
            melhor_score = scores_sem_stf[melhor_tema]
        if not scores_sem_stf or melhor_score < SCORE_MINIMO:
            return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}
    # STF: não classificar quando "corte" é de cabelo/visual (ex.: "corte bob", "corte de cabelo", Beyoncé)
    if melhor_tema == "STF" and "corte" in texto_lower:
        contexto_cabelo = any(x in texto_lower for x in (
            "corte bob", "corte de cabelo", "corte no cabelo", "corte cabelo",
            "cabelo", "visual", "posa", "beyoncé", "celebridade", "cabelereiro",
            "corte masculino", "corte feminino", "novo look", "mudança de visual"
        ))
        if contexto_cabelo:
            scores_sem_stf = {k: v for k, v in scores.items() if k != "STF"}
            if scores_sem_stf:
                melhor_tema = max(scores_sem_stf, key=scores_sem_stf.get)
                melhor_score = scores_sem_stf[melhor_tema]
            else:
                return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    # Editorial: aceito quando vindo de coleta dedicada (colunistas/editoriais por site) ou quando o léxico aponta para Editorial
    # (não forçar NAO_CLASSIFICADO)

    # Governo/Congresso: não classificar quando "presidente" é de empresa (Ambev, Banrisul, etc.), não do governo
    if melhor_tema == "Governo/Congresso" and "presidente" in texto_lower:
        contexto_empresa = ("ambev" in texto_lower or "banrisul" in texto_lower or "expandindo margem" in texto_lower
                           or "carteira pj" in texto_lower)
        if contexto_empresa:
            scores_sem_gov = {k: v for k, v in scores.items() if k != "Governo/Congresso"}
            if scores_sem_gov:
                melhor_tema = max(scores_sem_gov, key=scores_sem_gov.get)
                melhor_score = scores_sem_gov[melhor_tema]
            if not scores_sem_gov or melhor_score < SCORE_MINIMO:
                return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}
    # Governo/Congresso: não classificar quando é carnaval/sambódromo (ex.: Marquês de Sapucaí, escola de samba)
    if melhor_tema == "Governo/Congresso":
        contexto_carnaval = any(x in texto_lower for x in (
            "sapucaí", "sapucai", "marquês de sapucaí", "sambódromo", "sambodromo",
            "escola de samba", "desfile das escolas", "cobra coral", "cacique cobra",
            "avenida marquês", "carnaval", "alegoria", "enredo"
        ))
        if contexto_carnaval:
            scores_sem_gov = {k: v for k, v in scores.items() if k != "Governo/Congresso"}
            if scores_sem_gov:
                melhor_tema = max(scores_sem_gov, key=scores_sem_gov.get)
                melhor_score = scores_sem_gov[melhor_tema]
            else:
                return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    # Mercado: não classificar quando "ações" significa medidas/ato (ex.: "ações do MPF", "insuficientes ações"), não ações de bolsa
    if melhor_tema == "Mercado" and "ações" in texto_lower:
        acoes_como_medidas = ("ações do " in texto_lower or " ações contra " in texto_lower
                             or "insuficientes ações" in texto_lower or "ações insuficientes" in texto_lower)
        if acoes_como_medidas:
            scores_sem_merc = {k: v for k, v in scores.items() if k != "Mercado"}
            if scores_sem_merc:
                melhor_tema = max(scores_sem_merc, key=scores_sem_merc.get)
                melhor_score = scores_sem_merc[melhor_tema]
            if not scores_sem_merc or melhor_score < SCORE_MINIMO:
                return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}
    # Mercado: não classificar quando é carnaval/sambódromo (ex.: Unidos da Ponte, Sapucaí, desfilar, baile funk)
    if melhor_tema == "Mercado":
        contexto_carnaval_merc = any(x in texto_lower for x in (
            "sapucaí", "sapucai", "sambódromo", "sambodromo", "desfilar", "desfile das escolas",
            "escola de samba", "unidos da ", "baile funk", "carnaval", "enredo", "alegoria",
            "cobra coral", "cacique cobra", "marquês de sapucaí"
        ))
        if contexto_carnaval_merc:
            scores_sem_merc = {k: v for k, v in scores.items() if k != "Mercado"}
            if scores_sem_merc:
                melhor_tema = max(scores_sem_merc, key=scores_sem_merc.get)
                melhor_score = scores_sem_merc[melhor_tema]
            else:
                return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    # Não classificar notícias sobre política/economia de outros países (só queremos Brasil)
    titulo_lower = (titulo or "").strip().lower()
    prefixos_pais = ("argentina:", "chile:", "uruguai:", "paraguai:", "colômbia:", "colombia:", "peru:", "méxico:", "mexico:", "venezuela:", "bolívia:", "bolivia:", "equador:", "estados unidos:", "eua:", "reino unido:", "frança:", "franca:", "alemanha:", "espanha:", "itália:", "italia:")
    if titulo_lower.startswith(prefixos_pais):
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}
    # Milei + Senado/reforma no título = Argentina, não Brasil
    if "milei" in titulo_lower and ("senado" in titulo_lower or "reforma" in titulo_lower or "argentina" in titulo_lower):
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}
    # Economia/fiscal de outro país (ex.: "Economia do Reino Unido cresce...") = não classificar
    if "reino unido" in texto_lower and ("economia" in texto_lower or "cresce" in texto_lower or "orçamento" in texto_lower or "orcamento" in texto_lower or "pib" in texto_lower or "4 tri" in texto_lower or "trimestre" in texto_lower):
        return {"tema": NAO_CLASSIFICADO, "score": 0, "scores": scores}

    return {"tema": melhor_tema, "score": melhor_score, "scores": scores}


def listar_temas_ativos():
    """Retorna lista de nomes dos temas ativos (úteis para UI ou validação)."""
    return list(_carregar_temas().keys())
