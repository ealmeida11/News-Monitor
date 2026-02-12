# -*- coding: utf-8 -*-
"""
Script principal: coleta das 5 fontes, grava no banco (sem duplicatas por link),
gera painel HTML e index para GitHub Pages.

Uso (a partir da raiz do projeto News):
  set PYTHONPATH=r:\Economics\Ealmeida\Brasil\News
  python news_monitor_v2/run_coleta.py

Ou na pasta news_monitor_v2:
  python run_coleta.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Garantir que o projeto está no path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Reduzir ruído do Chrome/WebDriver
os.environ.setdefault("WDM_LOG_LEVEL", "0")

from database import db
from config import settings

# Scripts de coleta (cada um gera um JSON em tests/output/)
TESTES = [
    ("Valor Econômico", "tests/test_valor_classificar_todas.py"),
    ("Estadão", "tests/test_estadao_classificar_todas.py"),
    ("Folha", "tests/test_folha_classificar_todas.py"),
    ("O Globo", "tests/test_oglobo_classificar_todas.py"),
    ("CNN Brasil", "tests/test_cnn_classificar_todas.py"),
]
OUTPUT_DIR = BASE_DIR / "tests" / "output"
ARQUIVOS_JSON = [
    OUTPUT_DIR / "valor_classificado_24h.json",
    OUTPUT_DIR / "estadao_classificado_24h.json",
    OUTPUT_DIR / "folha_classificado_24h.json",
    OUTPUT_DIR / "oglobo_classificado_24h.json",
    OUTPUT_DIR / "cnn_classificado_24h.json",
]


def _rodar_coleta_fonte(nome, script_rel):
    """Executa o script de coleta de uma fonte. Retorna True se OK."""
    script_path = BASE_DIR / script_rel
    if not script_path.exists():
        print(f"  [AVISO] Script não encontrado: {script_path}")
        return False
    try:
        # Rodar a partir de news_monitor_v2 para imports corretos
        r = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "PYTHONPATH": os.pathsep.join([str(PROJECT_ROOT), str(BASE_DIR)])},
        )
        if r.returncode != 0 and r.stderr:
            print(f"  [AVISO] {nome}: {r.stderr[:200]}")
        return True
    except subprocess.TimeoutExpired:
        print(f"  [AVISO] {nome}: timeout")
        return False
    except Exception as e:
        print(f"  [AVISO] {nome}: {e}")
        return False


def _extrair_noticias_do_json(arq):
    """Lê o JSON gerado por um test_* e retorna lista de notícias (cada uma com tema = tema_classificado)."""
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
    print("=" * 70)
    print("  MONITOR MACRO BRASIL V2 - Coleta e painel")
    print("=" * 70)
    print(f"  Data/Hora: {datetime.now():%d/%m/%Y %H:%M}")
    print()

    db_path = db.get_db_path()
    db.init_db(db_path)
    print(f"  Banco: {db_path}")

    links_existentes = db.get_links_existentes(db_path, ultimos_dias=7)
    print(f"  Links já no banco (últimos 7 dias): {len(links_existentes)}")
    print()

    # 1) Rodar coleta de cada fonte
    print("  [1/3] Coletando fontes...")
    for nome, script in TESTES:
        print(f"    - {nome}...", end=" ", flush=True)
        _rodar_coleta_fonte(nome, script)
        print("OK")
    print()

    # 2) Ler JSONs e inserir no banco (apenas links novos)
    print("  [2/3] Inserindo notícias novas no banco...")
    inseridas = 0
    for arq in ARQUIVOS_JSON:
        noticias = _extrair_noticias_do_json(arq)
        for n in noticias:
            link = (n.get("link") or "").strip()
            if not link or link in links_existentes:
                continue
            if db.insert_noticia(n, db_path):
                inseridas += 1
                links_existentes.add(link)
    print(f"    Inseridas: {inseridas} novas notícias")
    print()

    # 3) Gerar painel a partir do banco (últimas 24h)
    print("  [3/3] Gerando painel (últimas 24h)...")
    noticias_24h = db.get_noticias_ultimas_24h(db_path)
    data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")

    if noticias_24h:
        from tests import gerar_painel_html
        painel_path = OUTPUT_DIR / "painel_dashboard.html"
        index_path = PROJECT_ROOT / "index.html"
        gerar_painel_html.gerar_painel_de_lista(
            noticias_24h,
            data_formatada=data_formatada,
            periodo_horas=24,
            arquivo_saida=painel_path,
        )
        # Copiar para index.html (GitHub Pages)
        import shutil
        shutil.copy2(painel_path, index_path)
        print(f"    Painel: {painel_path}")
        print(f"    index.html (GitHub): {index_path}")
        print(f"    Notícias no painel: {len(noticias_24h)}")
    else:
        print("    Nenhuma notícia nas últimas 24h no banco.")

    print()
    print("=" * 70)
    print("  Concluído.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
