# -*- coding: utf-8 -*-
"""
Entry point único peak Brasil: DB read → UI → extract+send.

DB-only: o pipeline diário das 06:00 já popula bodies. Sem Edge/CDP, sem cleanup.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from peak.config import DATA_DIR, UI_DIR, HEADLINES_JSON, SELECTION_JSON, SERVER_HOST
from peak.db_reader import write_headlines_json
from peak.selection_merge import smart_merge
from peak.server import build_server


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _load_prev_selection() -> dict:
    if not SELECTION_JSON.exists():
        return {}
    try:
        return json.loads(SELECTION_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        corrupt = SELECTION_JSON.with_suffix(f".corrupt-{int(time.time())}")
        SELECTION_JSON.rename(corrupt)
        print(f"[scraper] selection.json corrupto, renomeado pra {corrupt.name}: {e}")
        return {}


def _run_db_phase() -> None:
    print("\n=== Fase 1/3: lendo DB + ranqueando ===\n", flush=True)
    t0 = time.time()
    write_headlines_json()
    elapsed = time.time() - t0
    headlines = json.loads(HEADLINES_JSON.read_text(encoding="utf-8"))
    total = sum(s.get("count", 0) for s in headlines.get("sources", []))
    print(f"[db_reader] {total} headlines em {len(headlines.get('sources', []))} tabs ({elapsed:.1f}s)\n", flush=True)
    for s in headlines.get("sources", []):
        print(f"    {s['id']:<12} {s['count']:>4}  ({s['scrape_status']})", flush=True)
    print()

    prev = _load_prev_selection()
    merged = smart_merge(prev, headlines)
    _atomic_write_json(SELECTION_JSON, merged)
    print(f"[scraper] Selection.json atualizado ({len(merged['items'])} items)\n", flush=True)


def _find_free_port() -> int:
    sock = socket.socket()
    sock.bind((SERVER_HOST, 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _ui_phase() -> None:
    print("=== Fase 2/3: UI de seleção ===\n", flush=True)
    quit_event = threading.Event()
    port = _find_free_port()
    server = build_server(SERVER_HOST, port, UI_DIR, DATA_DIR, quit_event=quit_event)
    url = f"http://{SERVER_HOST}:{port}/"
    print(f"[server] UI rodando em {url}")
    print(f"[server] Browser abrindo... clique 'Done' quando terminar.\n", flush=True)
    threading.Thread(
        target=lambda: (time.sleep(0.5), webbrowser.open(url)),
        daemon=True,
    ).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    print("\n[server] UI fechada. Seleção salva.\n", flush=True)


def _run_extract_send_phase() -> int:
    print("=== Fase 3/3: extract + summarize + send ===\n", flush=True)
    from peak import extract_send
    return extract_send.run()


def main() -> int:
    try:
        _run_db_phase()
        _ui_phase()
        rc = _run_extract_send_phase()
        if rc != 0:
            print(f"\n[scraper] Fase 3 retornou exit code {rc}", flush=True)
        return rc
    except KeyboardInterrupt:
        print("\n[scraper] Interrompido (Ctrl+C)", flush=True)
        return 130
    except Exception as e:
        import traceback
        print(f"\n[scraper] ERRO FATAL: {type(e).__name__}: {e}\n", flush=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
