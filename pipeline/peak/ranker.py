# -*- coding: utf-8 -*-
"""
Score por título via keyword matching (regex \\b...\\b case-insensitive).

Keywords vêm de keywords.json com múltiplas categorias:
  - core: peso 1× por match
  - highlight: peso 2× por match (termos high-signal: COPOM, IPCA, FED, etc.)
  - colunistas: NÃO entram no score (usados separadamente pra routing pra tab Colunistas)
  - meta: também não entra no score (categoria, descrição, etc.)

Dedup: mesma keyword aparecendo várias vezes no título conta 1× (evita
título tipo 'Lula encontra Lula' inflar o score).
"""

from __future__ import annotations

import re
from typing import Iterable


_RANKING_CATEGORIES = {"core", "highlight"}
_HIGHLIGHT_WEIGHT = 2
_CORE_WEIGHT = 1


def build_keyword_regexes(keywords: dict[str, Iterable[str]]) -> dict[str, list[re.Pattern]]:
    """Compila regexes \\bTERMO\\b por categoria. Skip categorias não-ranking."""
    out: dict[str, list[re.Pattern]] = {}
    for cat, terms in keywords.items():
        if cat not in _RANKING_CATEGORIES:
            continue
        compiled = []
        for term in terms:
            term = term.strip()
            if not term:
                continue
            pattern = r"(?<![A-Za-zÀ-ÿ0-9])" + re.escape(term) + r"(?![A-Za-zÀ-ÿ0-9])"
            compiled.append(re.compile(pattern, re.IGNORECASE))
        out[cat] = compiled
    return out


def score(title: str, regexes: dict[str, list[re.Pattern]]) -> int:
    """Soma matches únicos por categoria, ponderada."""
    if not title:
        return 0
    total = 0
    for cat, patterns in regexes.items():
        weight = _HIGHLIGHT_WEIGHT if cat == "highlight" else _CORE_WEIGHT
        for p in patterns:
            if p.search(title):
                total += weight
    return total
