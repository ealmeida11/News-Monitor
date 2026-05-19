# -*- coding: utf-8 -*-
"""
Lê últimas N horas de seen_articles do seen.db (realtime), dedupa por título
normalizado com prioridade editorial, classifica colunistas pela whitelist,
aplica keyword score, e serializa headlines.json no formato consumido pela UI.

Schema do seen_articles (origem):
  id, url, url_normalized, title, source, seen_at, sent, body, published_at

published_at e seen_at vêm em ISO local naive (BRT), ex: '2026-05-18T22:51:00'.
Quando published_at está vazio, usamos seen_at como fallback.

Schema dos rows que produzimos pra UI:
  {
    "rank": int,            # ordem natural do DB
    "title": str,
    "url": str,             # canonicalizado
    "raw_url": str,         # original do DB
    "fonte_label": str,     # ex: "CNN Brasil"
    "source_id": str,
    "home_tab": str,        # source_id ou "colunistas"
    "columnist": str|None,
    "published_at": str|None,  # ISO local BRT
    "category_db": str,     # vazio (não temos no realtime)
    "summary_line1": str,   # vazio (não temos no realtime)
    "summary_line2": str,   # vazio (não temos no realtime)
    "body_len": int,
    "keyword_score": int,
    "headline_id": int,     # seen_articles.id
  }
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from peak import config
from peak.url_canon import canonicalize
from peak.ranker import build_keyword_regexes, score


# ---------------------------------------------------------------------------
# Helpers de normalização e dedup
# ---------------------------------------------------------------------------

_NORM_PUNCT_RE = re.compile(r"[^\w\sÀ-ÿ]+", re.UNICODE)
_NORM_SPACE_RE = re.compile(r"\s+")


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.lower()
    t = _NORM_PUNCT_RE.sub(" ", t)
    t = _NORM_SPACE_RE.sub(" ", t).strip()
    return t


def _dedup_with_priority(items: list[dict]) -> list[dict]:
    """Dedup por título normalizado. Quando duplica, mantém o item com menor rank
    (config.dedup_rank — O Globo=0, Valor=1, etc.). Estável: mantém ordem original."""
    chosen: dict[str, dict] = {}
    for it in items:
        key = _normalize_title(it["title"])
        if not key:
            continue
        prev = chosen.get(key)
        if prev is None:
            chosen[key] = it
            continue
        if config.dedup_rank(it["source_id"]) < config.dedup_rank(prev["source_id"]):
            chosen[key] = it
    # Preservar ordem original (rank) entre os escolhidos
    return sorted(chosen.values(), key=lambda x: x.get("rank", 0))


# ---------------------------------------------------------------------------
# Classificação de colunista (whitelist)
# ---------------------------------------------------------------------------

def _classify_columnist(title: str, whitelist: list[str]) -> str | None:
    """Se o título começa com 'Nome: ...' onde Nome ∈ whitelist (exact match,
    case-sensitive no nome), retorna o nome. Caso contrário None."""
    if ":" not in title:
        return None
    prefix = title.split(":", 1)[0].strip()
    if prefix in whitelist:
        return prefix
    return None


# ---------------------------------------------------------------------------
# DB read
# ---------------------------------------------------------------------------

def _pick_timestamp(published_at: str, seen_at: str) -> str | None:
    """Retorna o melhor ISO disponível: published_at se não vazio, senão seen_at.
    Ambos vêm em ISO local naive (BRT). Retorna None se ambos vazios."""
    if published_at and published_at.strip():
        return published_at.strip()
    if seen_at and seen_at.strip():
        return seen_at.strip()
    return None


def _load_headlines_from_db(conn: sqlite3.Connection, hours: int) -> list[sqlite3.Row]:
    """SELECT amplo do seen_articles: rows com seen_at >= (now - N horas - buffer).
    Filtro fino é feito em Python via _within_window contra o cutoff exato.
    Usamos seen_at no SQL (sempre populado e indexável), published_at pode estar vazio."""
    buffer_hours = hours + 24
    cutoff_seen = (datetime.now() - timedelta(hours=buffer_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    rows = conn.execute("""
        SELECT id, url, url_normalized, title, source, seen_at, published_at, body
        FROM seen_articles
        WHERE seen_at >= ?
        ORDER BY id DESC
    """, (cutoff_seen,)).fetchall()
    return rows


def _cutoff_iso_local(hours: int) -> str:
    """ISO local BRT (naive) do cutoff (agora - N horas). published_at/seen_at
    do realtime são local naive, então comparação string funciona."""
    cutoff = datetime.now() - timedelta(hours=hours)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%S")


def _within_window(item: dict, cutoff_iso: str) -> bool:
    """True se o item tem published_at e cai dentro da janela [cutoff, agora].
    Items sem timestamp parseado são descartados."""
    pub = item.get("published_at")
    if not pub:
        return False
    return pub >= cutoff_iso


def _load_keywords() -> dict:
    return json.loads(config.KEYWORDS_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Serialização → headlines.json
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _row_to_item(row: sqlite3.Row, rank: int, regexes, columnist_whitelist: list[str]) -> dict:
    title = (row["title"] or "").strip()
    raw_url = (row["url"] or "").strip()
    fonte_label = (row["source"] or "").strip()
    source_id = config.DB_SOURCE_TO_ID.get(fonte_label, fonte_label.lower())

    columnist = _classify_columnist(title, columnist_whitelist)
    home_tab = config.COLUNISTAS_TAB_ID if columnist else source_id

    pub_iso = _pick_timestamp(row["published_at"] or "", row["seen_at"] or "")
    return {
        "rank": rank,
        "title": title,
        "url": canonicalize(raw_url),
        "raw_url": raw_url,
        "fonte_label": fonte_label,
        "source_id": source_id,
        "home_tab": home_tab,
        "columnist": columnist,
        "published_at": pub_iso,
        "category_db": "",
        "summary_line1": "",
        "summary_line2": "",
        "body_len": len(row["body"] or ""),
        "keyword_score": score(title, regexes),
        "headline_id": row["id"],
    }


def build_headlines_json(hours: int | None = None) -> dict:
    """
    Lê o DB e retorna o dict que serializaríamos como headlines.json.
    """
    hours = hours if hours is not None else config.WINDOW_HOURS
    keywords = _load_keywords()
    regexes = build_keyword_regexes(keywords)
    columnist_whitelist = keywords.get("colunistas", [])

    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = _load_headlines_from_db(conn, hours)
    finally:
        conn.close()

    # 1. Transforma em items
    items = [_row_to_item(r, i, regexes, columnist_whitelist) for i, r in enumerate(rows)]

    # 2. Filtro fino por janela temporal real (published_at do realtime)
    cutoff_iso = _cutoff_iso_local(hours)
    items = [it for it in items if _within_window(it, cutoff_iso)]

    # 3. Dedup global (todas as fontes) por título normalizado, com prioridade
    items = _dedup_with_priority(items)

    # 3. Agrupa em tabs
    by_tab: dict[str, list[dict]] = {s["id"]: [] for s in config.SOURCES}
    by_tab[config.COLUNISTAS_TAB_ID] = []
    for it in items:
        tab = it["home_tab"]
        if tab not in by_tab:
            # source desconhecida — joga na primeira tab pra não perder
            tab = config.SOURCES[0]["id"]
            it["home_tab"] = tab
        by_tab[tab].append(it)

    # 4. Sort dentro de cada tab por keyword_score DESC; tiebreak por published_at DESC
    for tab_items in by_tab.values():
        tab_items.sort(
            key=lambda it: (it.get("keyword_score", 0), it.get("published_at") or ""),
            reverse=True,
        )

    # 5. Monta o output
    source_blocks = []
    for s in config.SOURCES:
        hs = by_tab.get(s["id"], [])
        source_blocks.append({
            "id": s["id"],
            "label": s["label"],
            "count": len(hs),
            "scrape_status": "ok" if hs else "empty",
            "scrape_error": None,
            "elapsed_sec": 0,
            "headlines": hs,
        })
    cols = by_tab.get(config.COLUNISTAS_TAB_ID, [])
    source_blocks.append({
        "id": config.COLUNISTAS_TAB_ID,
        "label": config.COLUNISTAS_TAB_LABEL,
        "count": len(cols),
        "scrape_status": "ok" if cols else "empty",
        "scrape_error": None,
        "elapsed_sec": 0,
        "headlines": cols,
    })

    return {
        "scraped_at": _now_iso(),
        "window_hours": hours,
        "sources": source_blocks,
    }


# Entry point ergonômico
def write_headlines_json(path: Path | None = None, hours: int | None = None) -> Path:
    out = path or config.HEADLINES_JSON
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build_headlines_json(hours=hours)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out)
    return out


if __name__ == "__main__":
    # Smoke standalone: gera + relata
    out = write_headlines_json()
    data = json.loads(out.read_text(encoding="utf-8"))
    print(f"OK — escrito {out}")
    print(f"  window: {data['window_hours']}h, scraped_at: {data['scraped_at']}")
    for s in data["sources"]:
        print(f"    {s['id']:<12} {s['count']:>4} headlines  ({s['scrape_status']})")
