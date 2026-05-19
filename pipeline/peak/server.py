# -*- coding: utf-8 -*-
"""
HTTP server stdlib pra UI de seleção.

Rotas:
  GET  /               → ui/index.html
  GET  /style.css      → ui/style.css
  GET  /app.js         → ui/app.js
  GET  /vendor/Sortable.min.js
  GET  /headlines.json → data/headlines.json (current scrape)
  GET  /selection.json → data/selection.json (estado atual; {} se 1º run)
  POST /save           → escreve data/selection.json (atomic)
  POST /quit           → sinaliza shutdown e responde 204
"""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


class PeakHandler(BaseHTTPRequestHandler):
    ui_dir: Path = None
    data_dir: Path = None
    quit_event: threading.Event = None

    def log_message(self, format, *args):
        # silencia o log padrão (já temos prints próprios)
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path == "/index.html":
            self._serve_static(self.ui_dir / "index.html", "text/html; charset=utf-8")
        elif self.path == "/style.css":
            self._serve_static(self.ui_dir / "style.css", "text/css; charset=utf-8")
        elif self.path == "/app.js":
            self._serve_static(self.ui_dir / "app.js", "application/javascript; charset=utf-8")
        elif self.path == "/vendor/Sortable.min.js":
            self._serve_static(self.ui_dir / "vendor" / "Sortable.min.js",
                               "application/javascript; charset=utf-8")
        elif self.path == "/headlines.json":
            self._serve_static(self.data_dir / "headlines.json",
                               "application/json; charset=utf-8")
        elif self.path == "/selection.json":
            sel = self.data_dir / "selection.json"
            if sel.exists():
                self._serve_static(sel, "application/json; charset=utf-8")
            else:
                self._respond(200, b"{}", "application/json; charset=utf-8")
        else:
            self._respond(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/save":
            self._handle_save()
        elif self.path == "/quit":
            self._handle_quit()
        else:
            self._respond(404, b"not found", "text/plain")

    def _handle_save(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("payload must be JSON object")
        except Exception as exc:
            self._respond(400, str(exc).encode("utf-8"), "text/plain")
            return
        _atomic_write(
            self.data_dir / "selection.json",
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        self._respond(204, b"", "text/plain")

    def _handle_quit(self) -> None:
        self._respond(204, b"", "text/plain")
        if self.quit_event is not None:
            self.quit_event.set()
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _serve_static(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._respond(404, b"not found", "text/plain")
            return
        data = path.read_bytes()
        self._respond(200, data, content_type)

    def _respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)


def _recover_corrupt_selection(data_dir: Path) -> None:
    sel = data_dir / "selection.json"
    if not sel.exists():
        return
    try:
        json.loads(sel.read_text(encoding="utf-8"))
    except Exception:
        corrupt = sel.with_suffix(f".json.corrupt-{int(time.time())}")
        sel.rename(corrupt)


def build_server(host: str, port: int, ui_dir: Path, data_dir: Path,
                 quit_event: threading.Event | None = None) -> ThreadingHTTPServer:
    data_dir.mkdir(parents=True, exist_ok=True)
    _recover_corrupt_selection(data_dir)

    handler_cls = type("BoundPeakHandler", (PeakHandler,), {
        "ui_dir": ui_dir,
        "data_dir": data_dir,
        "quit_event": quit_event,
    })
    return ThreadingHTTPServer((host, port), handler_cls)
