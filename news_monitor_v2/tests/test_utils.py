# -*- coding: utf-8 -*-
"""Utilitários para testes dos scrapers."""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Adicionar projeto principal ao path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Diretório de saída dos testes
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def gerar_relatorio(noticias, fonte, tempo_segundos):
    """Gera relatório de coleta: total, por categoria, por hora."""
    if not noticias:
        return {
            "fonte": fonte,
            "data_teste": datetime.now().isoformat(),
            "total": 0,
            "tempo_segundos": round(tempo_segundos, 1),
            "por_categoria": {},
            "por_hora": {},
            "amostra_titulos": [],
        }

    categorias = Counter(n.get("categoria", "N/D") for n in noticias)
    horas = Counter(n.get("hora", "N/D")[:2] for n in noticias)  # agrupa por hora

    return {
        "fonte": fonte,
        "data_teste": datetime.now().isoformat(),
        "total": len(noticias),
        "tempo_segundos": round(tempo_segundos, 1),
        "por_categoria": dict(categorias.most_common()),
        "por_hora": dict(horas.most_common()),
        "amostra_titulos": [n.get("titulo", "")[:80] for n in noticias[:10]],
    }


def salvar_resultado(noticias, fonte, tempo_segundos):
    """Salva JSON das notícias e relatório em tests/output/."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefixo = fonte.lower().replace(" ", "_").replace(".", "")

    # Salvar notícias
    arquivo_noticias = OUTPUT_DIR / f"test_{prefixo}_{timestamp}.json"
    with open(arquivo_noticias, "w", encoding="utf-8") as f:
        json.dump(noticias, f, ensure_ascii=False, indent=2)

    # Salvar relatório
    relatorio = gerar_relatorio(noticias, fonte, tempo_segundos)
    relatorio["arquivo_noticias"] = arquivo_noticias.name
    arquivo_relatorio = OUTPUT_DIR / f"relatorio_{prefixo}_{timestamp}.json"
    with open(arquivo_relatorio, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    return relatorio, arquivo_noticias, arquivo_relatorio


def imprimir_relatorio(relatorio):
    """Imprime relatório no console de forma legível."""
    print("\n" + "=" * 60)
    print(f"  RELATÓRIO DE TESTE - {relatorio['fonte']}")
    print("=" * 60)
    print(f"  Data do teste: {relatorio['data_teste']}")
    print(f"  Total de notícias: {relatorio['total']}")
    print(f"  Tempo de execução: {relatorio['tempo_segundos']} s")
    print("-" * 60)
    print("  Por categoria:")
    for cat, qtd in relatorio.get("por_categoria", {}).items():
        print(f"    - {cat}: {qtd}")
    print("-" * 60)
    print("  Amostra de títulos (até 10):")
    for i, tit in enumerate(relatorio.get("amostra_titulos", []), 1):
        print(f"    {i}. {tit}...")
    print("=" * 60 + "\n")
