# -*- coding: utf-8 -*-
"""Test smart_merge preserva escolhas entre runs."""

from peak.selection_merge import smart_merge


def test_smart_merge_preserves_added_and_position():
    prev = {
        "items": [
            {"url": "https://x/1", "added": True, "important": False, "position": 1},
            {"url": "https://x/2", "added": True, "important": True, "position": 2},
            {"url": "https://x/3", "added": False, "important": False, "position": None},
        ]
    }
    new = {
        "sources": [
            {"id": "cnn", "headlines": [
                {"url": "https://x/1", "title": "A", "rank": 0},
                {"url": "https://x/2", "title": "B", "rank": 1},
                {"url": "https://x/4", "title": "D (new)", "rank": 2},
            ]},
        ],
        "scraped_at": "2026-05-18T10:00:00",
    }
    merged = smart_merge(prev, new)
    by_url = {it["url"]: it for it in merged["items"]}

    assert by_url["https://x/1"]["added"] is True
    assert by_url["https://x/1"]["position"] == 1
    assert by_url["https://x/2"]["added"] is True
    assert by_url["https://x/2"]["important"] is True
    assert by_url["https://x/2"]["position"] == 2
    # x/3 sumiu do scrape novo — não está em merged
    assert "https://x/3" not in by_url
    # x/4 é novo — added=False
    assert by_url["https://x/4"]["added"] is False
