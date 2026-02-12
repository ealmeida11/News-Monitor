# -*- coding: utf-8 -*-
"""
Script para testar um scraper de notícias de forma isolada.

Uso:
    python run_test_scraper.py valor
    python run_test_scraper.py estadao
    python run_test_scraper.py folha
    python run_test_scraper.py oglobo

O script altera o diretório de trabalho para o projeto principal (Brasil/News)
para que o scraper encontre noticias.db e categorias_excluidas.txt.
"""

import os
import sys
import time
from pathlib import Path

# Diretório do projeto principal (Brasil/News)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FONTES = {
    "valor": ("Valor Econômico", "extrair_valor_economico"),
    "estadao": ("Estadão", "extrair_estadao"),
    "folha": ("Folha de S.Paulo", "extrair_folha"),
    "oglobo": ("O Globo", "extrair_oglobo"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1].lower() not in FONTES:
        print("Uso: python run_test_scraper.py <fonte>")
        print("Fontes: valor, estadao, folha, oglobo")
        sys.exit(1)

    fonte_key = sys.argv[1].lower()
    nome_fonte, metodo_nome = FONTES[fonte_key]

    # Garantir que rodamos a partir do projeto principal
    cwd_original = os.getcwd()
    try:
        os.chdir(PROJECT_ROOT)
        sys.path.insert(0, str(PROJECT_ROOT))

        import scraper_otimizado as scraper_mod

        print(f"\nIniciando teste do scraper: {nome_fonte}")
        print(f"Diretório de trabalho: {os.getcwd()}")
        print("-" * 50)

        start = time.time()
        scraper = scraper_mod.UnifiedNewsScraper()
        try:
            metodo = getattr(scraper, metodo_nome)
            noticias = metodo()
        finally:
            scraper.fechar_driver()
        tempo = time.time() - start

        # Voltar ao dir do teste para salvar resultados
        os.chdir(cwd_original)
        sys.path.insert(0, str(Path(__file__).resolve().parent))

        from test_utils import salvar_resultado, imprimir_relatorio

        relatorio, arq_not, arq_rel = salvar_resultado(
            noticias or [], nome_fonte, tempo
        )
        imprimir_relatorio(relatorio)
        print(f"Notícias salvas em: {arq_not}")
        print(f"Relatório salvo em: {arq_rel}")

    except Exception as e:
        os.chdir(cwd_original)
        print(f"ERRO: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
