# -*- coding: utf-8 -*-
r"""
Script principal: lê notícias do NewsAI Real Time (seen.db), classifica por tema,
grava no banco (sem duplicatas por link), gera painel HTML e index para GitHub Pages.

Uso (a partir da raiz do projeto News):
  set PYTHONPATH=<raiz_do_projeto>
  python news_monitor_v2/run_coleta.py

Ou na pasta news_monitor_v2:
  python run_coleta.py
"""

import io
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Evitar UnicodeEncodeError no console Windows (cp1252)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Garantir que o projeto está no path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
log = logging.getLogger(__name__)

from database import db
from config import settings
from filtros import is_excluded
from coletor_realtime import coletar_do_realtime
from classificador.lexico_classifier import classificar, NAO_CLASSIFICADO

OUTPUT_DIR = BASE_DIR / "output"


def main():
    t0 = time.time()
    agora = datetime.now()

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("MONITOR MACRO BRASIL v2")
    log.info("%s", agora.strftime("%d/%m/%Y %H:%M:%S"))
    log.info("Fonte: NewsAI Real Time (seen.db)")
    log.info("=" * 60)

    db_path = db.get_db_path()
    db.init_db(db_path)
    links_existentes = db.get_links_existentes(db_path, ultimos_dias=7)

    # ── Coleta (leitura do Real Time) ─────────────────────────────────────
    log.info("")
    log.info("Coleta (Real Time)")
    log.info("-" * 60)
    t_coleta = time.time()

    realtime_db = settings.REALTIME_DB
    if not Path(realtime_db).exists():
        log.error("  seen.db não encontrado: %s", realtime_db)
        return 1

    noticias_rt = coletar_do_realtime(realtime_db, ultimas_horas=24)
    elapsed_coleta = time.time() - t_coleta
    log.info("  (%.1fs)", elapsed_coleta)

    # ── Classificação + Filtro + Banco ────────────────────────────────────
    log.info("")
    log.info("Classificação e banco")
    log.info("-" * 60)
    t_banco = time.time()
    inseridas = 0
    filtradas = 0
    ja_existentes = 0

    for n in noticias_rt:
        link = (n.get("link") or "").strip()
        if not link:
            continue
        if link in links_existentes:
            ja_existentes += 1
            continue

        titulo = n.get("titulo", "")
        if is_excluded(link, titulo):
            filtradas += 1
            continue

        # Classificar por tema
        resultado = classificar(titulo, resumo="")
        tema = resultado["tema"]
        if tema == "Mundo":
            filtradas += 1
            continue
        n["tema_classificado"] = tema if tema != NAO_CLASSIFICADO else ""
        n["tema"] = n["tema_classificado"]
        n["score"] = resultado["score"]

        if db.insert_noticia(n, db_path):
            inseridas += 1
            links_existentes.add(link)

    elapsed_banco = time.time() - t_banco
    log.info("  do Real Time    %6d", len(noticias_rt))
    log.info("  já no banco     %6d", ja_existentes)
    log.info("  filtradas       %6d", filtradas)
    log.info("  inseridas       %6d", inseridas)
    log.info("  (%.1fs)", elapsed_banco)

    # ── Painel ────────────────────────────────────────────────────────────
    log.info("")
    log.info("Painel (24h)")
    log.info("-" * 60)
    t_painel = time.time()
    noticias_24h_bruto = db.get_noticias_ultimas_24h(db_path)
    CATEGORIAS_COMO_TEMA = {"Política", "Economia", "Mercado", "Macroeconomia"}
    MAPEAMENTO_CATEGORIA_TEMA = {"Macroeconomia": "Mercado"}
    TEMAS_EXCLUIDOS_PAINEL = {"Saúde", "Mundo", "Ambiente", "Ciência", "Cotidiano", "Tecnologia"}
    noticias_24h = []
    for n in noticias_24h_bruto:
        tema = (n.get("tema") or "").strip()
        cat = (n.get("categoria") or "").strip()
        if tema and tema not in TEMAS_EXCLUIDOS_PAINEL:
            noticias_24h.append(n)
        elif not tema and cat in CATEGORIAS_COMO_TEMA:
            n_copy = dict(n)
            n_copy["tema"] = MAPEAMENTO_CATEGORIA_TEMA.get(cat, cat)
            noticias_24h.append(n_copy)
    sem_tema = len(noticias_24h_bruto) - len(noticias_24h)
    data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")

    if noticias_24h:
        from gerar_painel import gerar_painel_de_lista
        import shutil
        painel_path = OUTPUT_DIR / "painel_dashboard.html"
        index_path = PROJECT_ROOT / "index.html"
        gerar_painel_de_lista(
            noticias_24h,
            data_formatada=data_formatada,
            periodo_horas=24,
            arquivo_saida=painel_path,
        )
        shutil.copy2(painel_path, index_path)
        log.info("  notícias        %6d", len(noticias_24h))
        if sem_tema:
            log.info("  sem tema        %6d (não exibidas)", sem_tema)
        log.info("  index.html      atualizado")
    else:
        log.info("  (nenhuma notícia com tema nas 24h)")
    elapsed_painel = time.time() - t_painel
    log.info("  (%.1fs)", elapsed_painel)

    # ── Rodapé ────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    log.info("")
    log.info("=" * 60)
    log.info("Concluído em %.0fs", elapsed)
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
