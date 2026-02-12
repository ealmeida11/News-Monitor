# -*- coding: utf-8 -*-
"""
Análise de cobertura dos scrapers.

Lê os relatórios gerados em tests/output/ e gera um resumo comparativo.
Útil para validar se alguma fonte está sub-representada ou com problemas.

Uso:
    python analise_cobertura.py
    python analise_cobertura.py --ultimos 3   # últimos 3 relatórios por fonte
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def carregar_relatorios(ultimos_n=5):
    """Carrega os últimos N relatórios de cada fonte."""
    if not OUTPUT_DIR.exists():
        print(f"Pasta {OUTPUT_DIR} não encontrada. Rode primeiro run_test_scraper.py para cada fonte.")
        return {}

    relatorios_por_fonte = defaultdict(list)
    for arq in OUTPUT_DIR.glob("relatorio_*.json"):
        try:
            with open(arq, "r", encoding="utf-8") as f:
                data = json.load(f)
            fonte = data.get("fonte", "?")
            data["_arquivo"] = arq.name
            data["_data"] = data.get("data_teste", "")[:19]
            relatorios_por_fonte[fonte].append(data)
        except Exception as e:
            print(f"Aviso: erro ao ler {arq}: {e}")

    # Ordenar por data (mais recente primeiro) e pegar últimos N
    for fonte in list(relatorios_por_fonte.keys()):
        relatorios_por_fonte[fonte].sort(
            key=lambda x: x.get("data_teste", ""), reverse=True
        )
        relatorios_por_fonte[fonte] = relatorios_por_fonte[fonte][:ultimos_n]

    return dict(relatorios_por_fonte)


def imprimir_analise(relatorios_por_fonte):
    """Imprime análise comparativa no console."""
    print("\n" + "=" * 70)
    print("  ANÁLISE DE COBERTURA - SCRAPERS")
    print("=" * 70)

    if not relatorios_por_fonte:
        print("  Nenhum relatório encontrado em tests/output/")
        print("  Execute: python run_test_scraper.py valor (e estadao, folha, oglobo)")
        print("=" * 70 + "\n")
        return

    totais_por_fonte = []
    for fonte, relatorios in sorted(relatorios_por_fonte.items()):
        if not relatorios:
            continue
        r = relatorios[0]  # mais recente
        total = r.get("total", 0)
        tempo = r.get("tempo_segundos", 0)
        data = r.get("_data", "?")
        totais_por_fonte.append((fonte, total, tempo, data))

    print("\n  Último teste por fonte (total de notícias | tempo em segundos):")
    print("-" * 70)
    for fonte, total, tempo, data in sorted(totais_por_fonte, key=lambda x: -x[1]):
        print(f"  {fonte:25}  total={total:4}  tempo={tempo:6.1f}s  data={data}")
    print("-" * 70)

    print("\n  Categorias encontradas no último teste de cada fonte:")
    print("-" * 70)
    for fonte, relatorios in sorted(relatorios_por_fonte.items()):
        if not relatorios:
            continue
        r = relatorios[0]
        cats = r.get("por_categoria", {})
        if cats:
            top = list(cats.items())[:5]
            cats_str = ", ".join(f"{c}:{n}" for c, n in top)
            print(f"  {fonte:25}  {cats_str}")
        else:
            print(f"  {fonte:25}  (nenhuma)")
    print("=" * 70 + "\n")


def main():
    ultimos = 5
    if len(sys.argv) > 2 and sys.argv[1] == "--ultimos":
        try:
            ultimos = int(sys.argv[2])
        except ValueError:
            pass

    relatorios = carregar_relatorios(ultimos_n=ultimos)
    imprimir_analise(relatorios)


if __name__ == "__main__":
    main()
