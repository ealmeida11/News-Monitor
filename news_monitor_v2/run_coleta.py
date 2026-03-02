# -*- coding: utf-8 -*-
r"""
Script principal: coleta das 6 fontes, grava no banco (sem duplicatas por link),
gera painel HTML e index para GitHub Pages.

Uso (a partir da raiz do projeto News):
  set PYTHONPATH=<raiz_do_projeto>
  python news_monitor_v2/run_coleta.py

Ou na pasta news_monitor_v2:
  python run_coleta.py
"""

import io
import json
import logging
import os
import subprocess
import sys
import threading
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

# Reduzir ruído do Chrome/WebDriver
os.environ.setdefault("WDM_LOG_LEVEL", "0")

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

# Scripts de coleta (cada um gera um JSON em output/)
COLETORES = [
    ("Valor Econômico", "coletores/valor.py"),
    ("Estadão", "coletores/estadao.py"),
    ("Folha", "coletores/folha.py"),
    ("O Globo", "coletores/oglobo.py"),
    ("CNN Brasil", "coletores/cnn.py"),
    ("Metrópoles", "coletores/metropoles.py"),
]
OUTPUT_DIR = BASE_DIR / "output"
ARQUIVOS_JSON = [
    OUTPUT_DIR / "valor_classificado_24h.json",
    OUTPUT_DIR / "estadao_classificado_24h.json",
    OUTPUT_DIR / "folha_classificado_24h.json",
    OUTPUT_DIR / "oglobo_classificado_24h.json",
    OUTPUT_DIR / "cnn_classificado_24h.json",
    OUTPUT_DIR / "metropoles_classificado_24h.json",
]


def _extrair_noticias_do_json(arq):
    """Lê o JSON gerado por um coletor e retorna lista de notícias (cada uma com tema = tema_classificado)."""
    if not arq.exists():
        return []
    try:
        with open(arq, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    out = []
    por_tema = data.get("por_tema", {})
    for tema, lista in por_tema.items():
        if tema == "Mundo":
            continue
        for n in lista:
            n_copy = dict(n)
            n_copy["tema_classificado"] = tema
            n_copy["tema"] = tema
            out.append(n_copy)
    for n in data.get("nao_classificadas", []):
        n_copy = dict(n)
        n_copy["tema_classificado"] = ""
        n_copy["tema"] = ""
        out.append(n_copy)
    return out


def main():
    t0 = time.time()
    agora = datetime.now()

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("MONITOR MACRO BRASIL v2")
    log.info("%s", agora.strftime("%d/%m/%Y %H:%M:%S"))
    log.info("Fontes: %s", ", ".join(nome for nome, _ in COLETORES))
    log.info("=" * 60)

    db_path = db.get_db_path()
    db.init_db(db_path)
    links_existentes = db.get_links_existentes(db_path, ultimos_dias=7)
    _links_file = OUTPUT_DIR / "links_existentes.txt"
    try:
        with open(_links_file, "w", encoding="utf-8") as f:
            for link in links_existentes:
                f.write(link + "\n")
    except Exception:
        pass

    # ── Coleta (paralela) ─────────────────────────────────────────────────
    log.info("")
    log.info("Coleta (6 fontes em paralelo)")
    log.info("-" * 60)
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(PROJECT_ROOT), str(BASE_DIR)]),
        "PYTHONIOENCODING": "utf-8",
    }

    # Linhas de ruído do Chrome/Selenium que queremos esconder
    _NOISE = ("DevTools listening", "ERROR:device_event_log", "ERROR:ssl_client_socket",
              "[WARNING:", "USB:", "Bluetooth", "HidManager")

    import re as _re
    _TS_PREFIX = _re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} \w+\s+")

    def _stream_output(stream, prefix):
        """Lê stream linha a linha e loga com prefixo (roda em thread)."""
        try:
            for line in stream:
                line = line.rstrip()
                if not line or any(n in line for n in _NOISE):
                    continue
                # Remover timestamp/level duplicado dos coletores
                line = _TS_PREFIX.sub("", line)
                log.info("[%s] %s", prefix, line)
        except Exception:
            pass

    t_coleta = time.time()
    processos = {}
    tempos_inicio = {}
    threads = []

    for nome, script_rel in COLETORES:
        script_path = BASE_DIR / script_rel
        if script_path.exists():
            p = subprocess.Popen(
                [sys.executable, "-u", str(script_path)],
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            processos[nome] = p
            tempos_inicio[nome] = time.time()
            # Abreviar nome para prefixo compacto no log
            tag = nome.split()[0][:8].upper()
            t_out = threading.Thread(target=_stream_output, args=(p.stdout, tag), daemon=True)
            t_err = threading.Thread(target=_stream_output, args=(p.stderr, tag), daemon=True)
            t_out.start()
            t_err.start()
            threads.extend([t_out, t_err])
            log.info("  %-22s [iniciado]", nome)
            time.sleep(3)  # stagger: evitar sobrecarga
        else:
            log.warning("  %-22s [arquivo não encontrado]", nome)

    log.info("")
    log.info("Aguardando conclusão...")
    ok = 0
    for nome, p in processos.items():
        p.wait()
        elapsed_fonte = time.time() - tempos_inicio[nome]
        status = p.returncode == 0
        ok += status
        sym = "ok" if status else "ERRO"
        log.info("  %-22s [%s]  (%.0fs)", nome, sym, elapsed_fonte)
    # Esperar threads de leitura terminarem
    for t in threads:
        t.join(timeout=5)
    elapsed_coleta = time.time() - t_coleta
    log.info("Fontes: %d/%d (%.0fs)", ok, len(COLETORES), elapsed_coleta)

    # ── Banco ─────────────────────────────────────────────────────────────
    log.info("")
    log.info("Banco")
    log.info("-" * 60)
    t_banco = time.time()
    inseridas = 0
    filtradas = 0
    for arq in ARQUIVOS_JSON:
        noticias = _extrair_noticias_do_json(arq)
        for n in noticias:
            link = (n.get("link") or "").strip()
            if not link or link in links_existentes:
                continue
            titulo = n.get("titulo", "")
            autor = n.get("autor", "")
            if is_excluded(link, titulo, autor):
                filtradas += 1
                continue
            if db.insert_noticia(n, db_path):
                inseridas += 1
                links_existentes.add(link)
    elapsed_banco = time.time() - t_banco
    log.info("  links (7 dias)  %6d", len(links_existentes))
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
