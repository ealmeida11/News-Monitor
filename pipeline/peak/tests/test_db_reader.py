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
    _cutoff_iso_local,
    _pick_timestamp,
)


@pytest.fixture
def fake_db(tmp_path):
    """Cria DB temporário com schema do seen_articles (realtime)."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE seen_articles (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            url_normalized TEXT NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            seen_at TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0,
            body TEXT NOT NULL DEFAULT '',
            published_at TEXT NOT NULL DEFAULT ''
        );
    """)
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
    # Cutoff: 17/05 22:36 BRT (naive local)
    cutoff = "2026-05-17T22:36:00"
    # Notícia de 16/05 12:19 — FORA da janela
    assert _within_window({"published_at": "2026-05-16T12:19:00"}, cutoff) is False
    # Notícia 22:00 BRT do dia 17 — antes do cutoff (22:36)
    assert _within_window({"published_at": "2026-05-17T22:00:00"}, cutoff) is False
    # Notícia 23:00 BRT do dia 17 — depois do cutoff
    assert _within_window({"published_at": "2026-05-17T23:00:00"}, cutoff) is True
    # Sem timestamp — descartar
    assert _within_window({"published_at": None}, cutoff) is False
    assert _within_window({}, cutoff) is False


def test_cutoff_iso_format():
    iso = _cutoff_iso_local(24)
    # Bate o formato esperado: YYYY-MM-DDTHH:MM:SS (ISO local naive, sem Z)
    assert "T" in iso
    assert len(iso) == 19  # YYYY-MM-DDTHH:MM:SS
    assert not iso.endswith("Z")


def test_pick_timestamp_prefers_published_when_available():
    assert _pick_timestamp("2026-05-18T22:00:00", "2026-05-18T22:30:00") == "2026-05-18T22:00:00"
    # Sem published, usa seen
    assert _pick_timestamp("", "2026-05-18T22:30:00.123") == "2026-05-18T22:30:00.123"
    # Ambos vazios
    assert _pick_timestamp("", "") is None
    assert _pick_timestamp(None, None) is None


def test_load_headlines_filters_24h(fake_db):
    conn, _ = fake_db
    now = datetime.now()
    conn.execute(
        "INSERT INTO seen_articles(url, url_normalized, title, source, seen_at, published_at, body) "
        "VALUES (?, ?, 'Hoje', 'CNN Brasil', ?, ?, 'corpo do artigo')",
        ("https://x/today", "https://x/today", now.strftime("%Y-%m-%dT%H:%M:%S"),
         now.strftime("%Y-%m-%dT%H:%M:%S")),
    )
    conn.commit()
    rows = _load_headlines_from_db(conn, hours=24)
    titles = [r["title"] for r in rows]
    assert "Hoje" in titles
