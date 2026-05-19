# -*- coding: utf-8 -*-
"""
smart_merge: combina o selection.json anterior com o headlines.json novo.

Regras:
  - URLs do scrape novo que estavam no selection anterior preservam estado
    (added, important, position).
  - URLs que sumiram do scrape novo são dropped da seleção (notícia saiu
    do hub editorial — não faz sentido mantê-la).
  - URLs novas começam zeradas (added=false, important=false, position=null).
  - Posições são repacked contiguamente (1, 2, 3, ...) entre items added=true.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def smart_merge(prev_selection: dict, new_headlines: dict) -> dict:
    """
    prev_selection: dict carregado do selection.json antigo (ou {} no 1º run)
    new_headlines:  dict produzido por headlines_scraper.scrape_all()

    Retorna novo selection dict pronto pra serializar.
    """
    prev_items = (prev_selection or {}).get("items", [])
    prev_by_url = {it["url"]: it for it in prev_items if it.get("url")}

    new_items: list[dict] = []
    for src in new_headlines.get("sources", []):
        for h in src.get("headlines", []):
            url = h.get("url", "")
            if not url:
                continue
            prev = prev_by_url.get(url)
            new_items.append({
                "url": url,
                "raw_url": h.get("raw_url", url),
                "title": h.get("title", ""),
                "home_tab": h.get("home_tab", src["id"]),
                "added": bool(prev["added"]) if prev else False,
                "important": bool(prev["important"]) if prev else False,
                "position": prev.get("position") if prev else None,
                "published_at": h.get("published_at"),
                "category": h.get("category", ""),
                "rank": h.get("rank", 0),
            })

    # Repack positions: items added=True ganham positions contíguas 1..N,
    # mantendo a ordem prévia (sorted by old position) com fallback pra rank.
    added_items = [it for it in new_items if it["added"]]
    added_items.sort(key=lambda it: (
        it["position"] if it.get("position") is not None else 10**9,
        it.get("rank", 0),
    ))
    for new_pos, it in enumerate(added_items, start=1):
        it["position"] = new_pos

    for it in new_items:
        if not it["added"]:
            it["position"] = None
            it["important"] = False

    return {
        "updated_at": _now_iso(),
        "headlines_snapshot_at": new_headlines.get("scraped_at"),
        "items": new_items,
    }
