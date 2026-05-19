# -*- coding: utf-8 -*-
"""Unit tests para peak.ranker."""

from peak.ranker import score, build_keyword_regexes


def test_score_zero_when_no_match():
    regexes = build_keyword_regexes({"core": ["Lula"]})
    assert score("Eclipse solar visto em SP", regexes) == 0


def test_score_one_per_match():
    regexes = build_keyword_regexes({"core": ["Lula", "Haddad"]})
    assert score("Lula recebe Haddad no Planalto", regexes) == 2


def test_score_case_insensitive():
    regexes = build_keyword_regexes({"core": ["selic"]})
    assert score("SELIC mantida em 14,75%", regexes) == 1


def test_score_word_boundary():
    """\\bIPCA\\b não deve bater em 'XIPCAY' (palavra parcial)."""
    regexes = build_keyword_regexes({"core": ["IPCA"]})
    assert score("XIPCAYZ é só ruído", regexes) == 0
    assert score("IPCA sobe 0,5%", regexes) == 1


def test_score_highlight_doubles():
    """Termos na categoria 'highlight' valem 2× cada match."""
    regexes = build_keyword_regexes({
        "core": ["Lula"],
        "highlight": ["COPOM"],
    })
    # Lula = 1 (core), COPOM = 2 (highlight) → total 3
    assert score("Lula comenta decisão do COPOM", regexes) == 3


def test_score_dedup_within_title():
    """Mesma keyword aparecendo 2× no título conta 1 vez (não inflar score)."""
    regexes = build_keyword_regexes({"core": ["Lula"]})
    assert score("Lula encontra Lula em Brasília", regexes) == 1


def test_score_multiword_phrase():
    regexes = build_keyword_regexes({"core": ["Banco Central"]})
    assert score("Banco Central anuncia decisão", regexes) == 1
    assert score("banco central reage", regexes) == 1
