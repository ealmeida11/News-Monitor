# -*- coding: utf-8 -*-
r"""
Script principal: coleta das 5 fontes, grava no banco (sem duplicatas por link),
gera painel HTML e index para GitHub Pages.

Uso (a partir da raiz do projeto News):
  set PYTHONPATH=<raiz_do_projeto>
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


def _rodar_coleta_fonte(nome, script_rel):
    """Executa o script de coleta de uma fonte. Retorna True se OK."""
    script_path = BASE_DIR / script_rel
    if not script_path.exists():
        return False
    try:
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(PROJECT_ROOT), str(BASE_DIR)]),
            "PYTHONIOENCODING": "utf-8",
        }
        r = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            env=env,
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


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
    t0 = datetime.now()
    W = 56  # largura do bloco

    # ---- Cabeçalho ----
    print()
    print("  " + "=" * (W - 2))
    print("  MONITOR MACRO BRASIL  v2")
    print("  " + "=" * (W - 2))
    print(f"  {t0:%d/%m/%Y  %H:%M:%S}")
    print()

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

    # ---- Coleta ----
    print("  Coleta")
    print("  " + "-" * (W - 2))
    ok = 0
    for nome, script in COLETORES:
        status = _rodar_coleta_fonte(nome, script)
        ok += status
        sym = "ok" if status else ".."
        print(f"    {nome:<22} [{sym}]")
    print(f"  fontes: {ok}/{len(COLETORES)}")
    print()

    # ---- Banco ----
    print("  Banco")
    print("  " + "-" * (W - 2))
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
    print(f"    links (7 dias)  {len(links_existentes):>6}")
    print(f"    filtradas       {filtradas:>6}")
    print(f"    inseridas       {inseridas:>6}")
    print()

    # ---- Painel ----
    print("  Painel (24h)")
    print("  " + "-" * (W - 2))
    noticias_24h_bruto = db.get_noticias_ultimas_24h(db_path)
    # Categorias da fonte usadas como tema quando o classificador não atribuiu (ex.: CNN "Política", "Macroeconomia")
    CATEGORIAS_COMO_TEMA = {"Política", "Economia", "Mercado", "Macroeconomia"}
    MAPEAMENTO_CATEGORIA_TEMA = {"Macroeconomia": "Mercado"}  # categoria do site -> tema no painel
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
        print(f"    noticias        {len(noticias_24h):>6}")
        if sem_tema:
            print(f"    sem tema        {sem_tema:>6} (nao exibidas)")
        print(f"    index.html      atualizado")
    else:
        print("    (nenhuma noticia com tema nas 24h)")
    print()

    # ---- Rodapé ----
    elapsed = (datetime.now() - t0).total_seconds()
    print("  " + "=" * (W - 2))
    print(f"  concluido  {elapsed:.0f}s")
    print("  " + "=" * (W - 2))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
