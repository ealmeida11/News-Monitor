# -*- coding: utf-8 -*-
"""Unit tests pro db_reader. Usa SQLite in-memory."""

import sqlite3
from datetime import datetime

import pytest

from peak.db_reader import (
    _normalize_title,
    _dedup_with_priority,
    _classify_columnist,
    _load_headlines_from_db,
    _within_window,
    _cutoff_iso_utc,
)


@pytest.fixture
def fake_db(tmp_path):
    """Cria DB temporário com schema simplificado."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE runs (id INTEGER PRIMARY KEY, run_date TEXT, status TEXT);
        CREATE TABLE headlines (
            id INTEGER PRIMARY KEY, run_id INTEGER, titulo TEXT, link TEXT,
            fonte TEXT, data TEXT, hora TEXT, resumo_site TEXT DEFAULT '',
            ai_category TEXT DEFAULT '',
            UNIQUE(run_id, link)
        );
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY, headline_id INTEGER UNIQUE,
            full_text TEXT DEFAULT '', fetch_status TEXT DEFAULT 'pending',
            summary_line1 TEXT DEFAULT '', summary_line2 TEXT DEFAULT '',
            partial INTEGER DEFAULT 0
        );
    """)
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO runs(id, run_date, status) VALUES (1, ?, 'done')", (today,))
    yield conn, str(db)
    conn.close()


def test_normalize_title_strips_punctuation_and_case():
    assert _normalize_title("Lula anuncia PEC: detalhes") == "lula anuncia pec detalhes"
    assert _normalize_title("  Foo  Bar  ") == "foo bar"


def test_dedup_with_priority_keeps_higher_ranked_source():
    items = [
        {"title": "Lula viaja para SP", "source_id": "cnn",    "rank": 0},
        {"title": "Lula viaja para SP", "source_id": "oglobo", "rank": 1},
        {"title": "Lula viaja para SP", "source_id": "valor",  "rank": 2},
    ]
    deduped = _dedup_with_priority(items)
    assert len(deduped) == 1
    assert deduped[0]["source_id"] == "oglobo"


def test_dedup_keeps_unique_titles():
    items = [
        {"title": "Lula viaja para SP",    "source_id": "cnn", "rank": 0},
        {"title": "Galípolo discute Selic", "source_id": "cnn", "rank": 1},
    ]
    deduped = _dedup_with_priority(items)
    assert len(deduped) == 2


def test_classify_columnist_matches_whitelist():
    whitelist = ["Lauro Jardim", "Painel", "Mônica Bergamo"]
    assert _classify_columnist("Lauro Jardim: Galípolo na mira", whitelist) == "Lauro Jardim"
    assert _classify_columnist("Painel: Lula irritado", whitelist) == "Painel"
    assert _classify_columnist("Lula tem reunião com Haddad", whitelist) is None


def test_classify_columnist_case_insensitive_at_start():
    whitelist = ["Lauro Jardim"]
    # Whitelist match deve exigir prefix "Nome: " (Lauro Jardim: ...)
    assert _classify_columnist("LAURO JARDIM: notícia", whitelist) is None  # all caps não é o pattern
    assert _classify_columnist("Lauro Jardim: notícia normal", whitelist) == "Lauro Jardim"


def test_within_window_drops_items_outside_24h():
    cutoff = "2026-05-17T22:36:00Z"
    # Notícia de 16/05 BRT 12:19 → UTC 15:19 — FORA da janela
    assert _within_window({"published_at": "2026-05-16T15:19:00Z"}, cutoff) is False
    # Notícia de 17/05 BRT 19:00 → UTC 22:00 — DENTRO (margem)
    assert _within_window({"published_at": "2026-05-17T22:00:00Z"}, cutoff) is False  # 22:00 < 22:36
    assert _within_window({"published_at": "2026-05-17T23:00:00Z"}, cutoff) is True
    # Sem timestamp — descartar
    assert _within_window({"published_at": None}, cutoff) is False
    assert _within_window({}, cutoff) is False


def test_cutoff_iso_format():
    iso = _cutoff_iso_utc(24)
    # Bate o formato esperado: YYYY-MM-DDTHH:MM:SSZ
    assert iso.endswith("Z")
    assert "T" in iso
    assert len(iso) == 20


def test_load_headlines_filters_24h(fake_db):
    conn, _ = fake_db
    today = datetime.now().strftime("%d/%m/%Y")
    conn.execute(
        "INSERT INTO headlines(run_id, titulo, link, fonte, data, hora) "
        "VALUES (1, 'Hoje', 'https://x/today', 'CNN Brasil', ?, '08:00')",
        (today,),
    )
    conn.commit()
    rows = _load_headlines_from_db(conn, hours=24)
    titles = [r["titulo"] for r in rows]
    assert "Hoje" in titles
