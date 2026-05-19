# -*- coding: utf-8 -*-
"""
One-shot script: gera peak/keywords.json combinando:

  1. SEEDS curados manualmente nas categorias (core / highlight / colunistas)
  2. Top termos extraídos dos TXT em output/ (frequência por dias distintos
     >= MIN_DAYS), filtrados de FPs e duplicações com seeds.

Roda 1× quando criar o projeto e depois quando quiser refresh:
  cd pipeline && python -m peak.keywords_builder

Output: peak/keywords.json com chaves {core, highlight, colunistas, meta}.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PEAK_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = PEAK_DIR.parent
OUTPUT_DIR = PIPELINE_DIR / "output"
KEYWORDS_JSON = PEAK_DIR / "keywords.json"

MIN_DAYS_AUTO = 3   # termo precisa aparecer em >= N dias distintos pra entrar
TOP_N_AUTO = 60     # cap no nº de termos auto-extraídos

# ---------------------------------------------------------------------------
# SEEDS CURADOS — fonte primária; auto-extraídos só complementam
# ---------------------------------------------------------------------------

SEEDS_CORE = [
    # Candidatos 2026
    "Lula", "Flávio Bolsonaro", "Caiado", "Renan Santos", "Tarcísio", "Zema",
    "Ratinho Jr", "Eduardo Leite", "Pablo Marçal", "Ciro Gomes",
    # Bolsonaros e órbita
    "Bolsonaro", "Jair Bolsonaro", "Michelle Bolsonaro", "Eduardo Bolsonaro",
    "Carlos Bolsonaro",
    # Cabinet
    "Haddad", "Tebet", "Padilha", "Lupi", "Wellington Dias", "Alckmin",
    "Mauro Vieira", "Camilo Santana", "Marina Silva", "Rui Costa", "Anielle",
    "Sonia Guajajara", "Macaé Evaristo", "Esther Dweck", "Silvio Costa Filho",
    "Renan Filho", "Juscelino Filho", "Márcio Macedo", "Vinícius Carvalho",
    "Jorge Messias", "Ricardo Lewandowski", "Paulo Pimenta",
    # Fazenda
    "Durigan", "Dario Durigan", "Bernard Appy", "Rogério Ceron", "Marcos Pinto",
    # BCB
    "Galípolo", "Diogo Guillen", "Paulo Picchetti", "Nilton David",
    "Renato Dias de Brito Gomes", "Izabela Correa", "Gilneu Vivan",
    "Banco Central", "BC", "Copom", "BCB",
    # Câmara + Senado
    "Motta", "Hugo Motta", "Lira", "Arthur Lira", "Alcolumbre", "Davi Alcolumbre",
    "Pacheco", "Rodrigo Pacheco", "Renan Calheiros",
    # STF / Judiciário
    "STF", "Moraes", "Alexandre de Moraes", "Fachin", "Toffoli", "Dias Toffoli",
    "Gilmar Mendes", "Nunes Marques", "Cristiano Zanin", "Cármen Lúcia",
    "Edson Fachin", "Luís Roberto Barroso", "André Mendonça",
    "Flávio Dino", "TSE", "PGR", "Paulo Gonet",
    # Institutos pesquisa
    "Datafolha", "Quaest", "AtlasIntel", "Atlas Intel", "IPEC", "Genial/Quaest",
    "Paraná Pesquisas", "Real Time Big Data", "Vox Populi", "Ranking Brasil",
    "Numerus", "MDA", "Modalmais/Futura", "FSB",
    # Macro core
    "Selic", "IPCA", "PIB", "CDI", "juros", "inflação", "dólar", "real",
    "câmbio", "fiscal", "déficit", "superávit", "arcabouço", "Pix",
    # Fiscal terms
    "PEC", "LDO", "LOA", "MP", "medida provisória", "emendas Pix",
    "emendas parlamentares", "jabuti", "Desenrola", "renegociação",
    "imposto de renda", "isenção", "IR", "Receita Federal",
    # Casos hot
    "Master", "Banco Master", "BRB", "Vorcaro", "Daniel Vorcaro",
    "Crime Organizado", "PCC", "CV", "CPMI", "CPI", "Antifacção",
    "INSS", "fila INSS",
    # Petrobras / estatais
    "Petrobras", "Vale", "BNDES", "Eletrobras", "Caixa", "Banco do Brasil",
    "Itaú", "Bradesco",
    # Externos relevantes
    "Trump", "FED", "FOMC", "Powell", "EUA", "China", "Mercosul",
    # Misc político
    "Lula", "Planalto", "Esplanada", "Congresso", "Senado", "Câmara",
]

SEEDS_HIGHLIGHT = [
    # Highlight = 2× peso (termos high-signal que isoladamente já sinalizam matéria importante)
    "Copom", "COPOM", "IPCA", "IPCA-15", "Selic", "PEC", "CPMI", "CPI",
    "FED", "FOMC", "Powell", "Datafolha", "Quaest", "AtlasIntel", "IPEC",
    "Banco Central", "Galípolo", "Master", "Vorcaro",
]

# 22 colunistas (whitelist do código atual de pipeline/collectors/*.py)
COLUNISTAS = [
    # O Globo
    "Lauro Jardim", "Miriam Leitão", "Malu Gaspar", "Bela Megale",
    "Fábio Graner", "Fabio Graner", "Andréia Sadi",
    # Folha
    "Painel", "Adriana Fernandes", "Mônica Bergamo",
    # Valor
    "Alex Ribeiro", "Andrea Jubé", "Arthur Cagliari", "Sergio Lamucci",
    "Giordanna Neves",
    # Estadão
    "Carlos Pereira",
    # CNN
    "Caio Junqueira", "Matheus Teixeira", "Teo Cury", "Larissa Rodrigues",
    "Gustavo Uribe", "Isabel Mega", "Thaís Herédia", "Débora Bergamasco",
]

# Falsos positivos conhecidos da extração auto — descartar mesmo se frequentes
AUTO_BLOCKLIST = {
    "Painel",   # categoria de coluna Folha, vamos tratar via COLUNISTAS
    "Fim", "Aliados", "Oposição", "Governo", "Governo Lula",
    "São", "Porto", "Caso", "Banco", "Alto", "Sobre", "Hoje",
}

# ---------------------------------------------------------------------------
# Extração auto dos TXT
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(r"^\*([^:*]+): (.+?)\* \(http", re.MULTILINE)
_DATE_RE = re.compile(r"Newsflow BR - (\d{2}-\d{2}-\d{4})")
_STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das",
    "no", "na", "nos", "nas", "em", "para", "por", "pelo", "pela", "com",
    "e", "ou", "mas", "que", "se", "ao", "à", "aos", "às",
    "é", "foi", "será", "tem", "ter", "há", "sobre", "como", "após", "antes",
    "diz", "afirma", "vai", "fala",
    "ele", "ela", "eles", "elas", "seu", "sua", "seus", "suas",
    "país", "brasil", "brasileiro", "brasileira", "presidente", "ministro",
    "agora", "ainda", "também", "porque", "porém", "então", "já", "só",
    "esta", "este", "isso", "essa", "esse",
}
_SOURCES_LC = {"folha", "estadão", "estadao", "globo", "valor", "metrópoles",
               "metropoles", "cnn", "valor econômico", "folha de s.paulo",
               "o globo"}


def _extract_terms_from_title(title: str) -> list[str]:
    """Extrai sequências de palavras Capitalizadas (1-4) + siglas (CAPS 2-6)."""
    terms: list[str] = []
    for m in re.finditer(
        r"(?<![\.\?!]\s)\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+"
        r"(?:\s+(?:de|da|do|das|dos|e)\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+"
        r"|\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){0,3})\b",
        title,
    ):
        t = m.group(1).strip()
        if t.lower() in _STOPWORDS or t.lower() in _SOURCES_LC:
            continue
        if len(t) <= 2:
            continue
        terms.append(t)
    for m in re.finditer(r"\b([A-Z]{2,6})\b", title):
        t = m.group(1)
        if t in {"DE", "DO", "DA", "PT", "OS", "TV"}:
            continue
        terms.append(t)
    return terms


def _auto_extract() -> list[tuple[str, int, int]]:
    """Retorna lista (termo, dias_distintos, freq_total) ordenada por dias×freq."""
    files = sorted(
        f for f in OUTPUT_DIR.glob("Newsflow BR - *.txt")
        if "(WhatsApp).txt" in f.name and "Completo" not in f.name
    )
    if not files:
        return []

    freq: Counter[str] = Counter()
    days: dict[str, set[str]] = defaultdict(set)
    for f in files:
        m = _DATE_RE.search(f.name)
        date_str = m.group(1) if m else f.name
        text = f.read_text(encoding="utf-8", errors="replace")
        for _src, title in _TITLE_RE.findall(text):
            for term in _extract_terms_from_title(title):
                freq[term] += 1
                days[term].add(date_str)

    ranked = sorted(
        freq.items(),
        key=lambda kv: (len(days[kv[0]]), kv[1]),
        reverse=True,
    )
    return [(t, len(days[t]), f) for t, f in ranked]


# ---------------------------------------------------------------------------
# Composição final
# ---------------------------------------------------------------------------

def build_keywords() -> dict:
    seed_core_lc = {s.lower() for s in SEEDS_CORE}
    seed_highlight_lc = {s.lower() for s in SEEDS_HIGHLIGHT}
    colunistas_lc = {c.lower() for c in COLUNISTAS}
    blocklist_lc = {b.lower() for b in AUTO_BLOCKLIST}

    auto = _auto_extract()
    auto_filtered: list[str] = []
    for term, days_count, _freq in auto:
        if days_count < MIN_DAYS_AUTO:
            break
        if len(auto_filtered) >= TOP_N_AUTO:
            break
        tlc = term.lower()
        if tlc in seed_core_lc or tlc in seed_highlight_lc:
            continue
        if tlc in colunistas_lc:
            continue
        if tlc in blocklist_lc:
            continue
        auto_filtered.append(term)

    # core = seeds + auto (dedup case-insensitive, mantém forma original)
    seen_lc: set[str] = set()
    core: list[str] = []
    for term in SEEDS_CORE + auto_filtered:
        if term.lower() in seen_lc:
            continue
        seen_lc.add(term.lower())
        core.append(term)

    return {
        "meta": {
            "generated_from": "SEEDS_CORE + SEEDS_HIGHLIGHT + auto extração de output/*.txt",
            "auto_min_days": MIN_DAYS_AUTO,
            "auto_top_n": TOP_N_AUTO,
            "n_core": len(core),
            "n_highlight": len(SEEDS_HIGHLIGHT),
            "n_colunistas": len(COLUNISTAS),
        },
        "core": core,
        "highlight": list(SEEDS_HIGHLIGHT),
        "colunistas": list(COLUNISTAS),
    }


def main() -> int:
    kw = build_keywords()
    KEYWORDS_JSON.write_text(
        json.dumps(kw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OK — escrito {KEYWORDS_JSON}")
    print(f"  core:      {kw['meta']['n_core']} termos")
    print(f"  highlight: {kw['meta']['n_highlight']} termos")
    print(f"  colunistas:{kw['meta']['n_colunistas']} termos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
