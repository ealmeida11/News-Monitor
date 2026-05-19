# -*- coding: utf-8 -*-
"""
Canonicalização de URLs pra dedup cross-runs e cross-fontes.

Regras:
- Host lowercased.
- Strip de query params de tracking (utm_*, mod*, fbclid, gclid, ref, mc_*, ito, mbid, xpid).
- Strip de fragment (#...).
- Trailing slash preservada (paths reais costumam ter ou não, não normalizo agressivamente).
"""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

_TRACKING_PREFIXES = ("utm_", "mod", "mc_")
_TRACKING_EXACT = {"fbclid", "gclid", "ref", "ito", "mbid", "xpid"}


def _is_tracking(key: str) -> bool:
    key = key.lower()
    if key in _TRACKING_EXACT:
        return True
    return any(key.startswith(p) for p in _TRACKING_PREFIXES)


def canonicalize(url: str) -> str:
    if not url:
        return ""
    try:
        p = urlparse(url)
    except Exception:
        return url

    host = (p.hostname or "").lower()
    if p.port:
        host = f"{host}:{p.port}"

    query_pairs = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not _is_tracking(k)]
    query = urlencode(query_pairs, doseq=True)

    return urlunparse((p.scheme.lower(), host, p.path, p.params, query, ""))
