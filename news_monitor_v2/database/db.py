# -*- coding: utf-8 -*-
"""
Banco de dados SQLite para o Monitor de Notícias V2.
Evita duplicatas por link; armazena tema classificado para o painel.
"""

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

# Caminho padrão do DB (news_monitor_v2/noticias_v2.db)
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "noticias_v2.db"


def get_db_path():
    import os
    return os.environ.get("DB_PATH", str(DEFAULT_DB_PATH))


def init_db(db_path=None):
    """Cria a tabela se não existir. Retorna o path usado."""
    db_path = db_path or get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS noticias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            resumo TEXT DEFAULT '',
            fonte TEXT NOT NULL,
            categoria TEXT DEFAULT '',
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            tema_classificado TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_noticias_link ON noticias(link)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_noticias_data_coleta ON noticias(data_coleta)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_noticias_fonte ON noticias(fonte)")
    conn.commit()
    conn.close()
    return db_path


def get_links_existentes(db_path=None, ultimos_dias=7):
    """Retorna set de links já presentes no banco (últimos N dias) para evitar duplicatas."""
    db_path = db_path or get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    desde = (datetime.now() - timedelta(days=ultimos_dias)).strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT link FROM noticias WHERE date(data_coleta) >= ?",
        (desde,)
    )
    links = {row[0] for row in cursor.fetchall()}
    conn.close()
    return links


def insert_noticia(noticia, db_path=None):
    """
    Insere uma notícia. Campos: link, titulo, resumo, fonte, categoria, data, hora, tema_classificado, score.
    Usa INSERT OR IGNORE para não falhar em link duplicado.
    Retorna True se inseriu, False se ignorou (duplicado).
    """
    db_path = db_path or get_db_path()
    for tentativa in range(3):
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO noticias
                (link, titulo, resumo, fonte, categoria, data, hora, tema_classificado, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                noticia.get("link", "").strip(),
                (noticia.get("titulo") or "").strip(),
                (noticia.get("resumo") or "").strip(),
                (noticia.get("fonte") or "").strip(),
                (noticia.get("categoria") or "").strip(),
                (noticia.get("data") or "").strip(),
                (noticia.get("hora") or "").strip(),
                (noticia.get("tema_classificado") or noticia.get("tema") or "").strip(),
                int(noticia.get("score") or 0),
            ))
            inserted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return inserted
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and tentativa < 2:
                time.sleep(0.5)
                continue
            raise
    return False


def get_noticias_ultimas_24h(db_path=None):
    """
    Retorna lista de dicts com notícias das últimas 24 horas (por data/hora da notícia).
    Cada dict tem: titulo, resumo, fonte, categoria, data, hora, link, tema (tema_classificado), score.
    Ordenado do mais recente para o mais antigo.
    """
    db_path = db_path or get_db_path()
    limite = datetime.now() - timedelta(hours=24)
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT titulo, resumo, fonte, categoria, data, hora, link, tema_classificado, score
        FROM noticias
        ORDER BY data_coleta DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    out = []
    for r in rows:
        titulo, resumo, fonte, categoria, data, hora, link, tema, score = r
        try:
            dt = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M")
            if dt < limite:
                continue
        except Exception:
            continue
        out.append({
            "titulo": titulo or "",
            "resumo": resumo or "",
            "fonte": fonte or "",
            "categoria": categoria or "",
            "data": data or "",
            "hora": hora or "",
            "link": link or "",
            "tema": (tema or "").strip(),
            "score": score or 0,
        })
    # Ordenar do mais recente para o mais antigo (por datetime, não string)
    def _sort_key(n):
        try:
            return datetime.strptime(f"{n['data']} {n['hora']}", "%d/%m/%Y %H:%M")
        except Exception:
            return datetime.min
    out.sort(key=_sort_key, reverse=True)
    return out
