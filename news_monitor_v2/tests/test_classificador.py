# -*- coding: utf-8 -*-
"""
Teste rápido do classificador por tema.
Roda com título (e opcionalmente resumo) e mostra tema + scores.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classificador.lexico_classifier import classificar, listar_temas_ativos, NAO_CLASSIFICADO


def testar(titulo, resumo=""):
    r = classificar(titulo, resumo=resumo)
    print(f"  Título: {titulo[:70]}...")
    if resumo:
        print(f"  Resumo: {resumo[:70]}...")
    print(f"  -> Tema: {r['tema']} (score={r['score']})")
    if r["scores"]:
        print(f"  -> Scores: {r['scores']}")
    print()
    return r


if __name__ == "__main__":
    print("=" * 60)
    print("  TESTE DO CLASSIFICADOR POR TEMA")
    print("=" * 60)
    print(f"  Temas ativos: {listar_temas_ativos()}")
    print()

    # Exemplos
    testar("Copom mantém Selic em 14,25% ao ano")
    testar("Governo anuncia novo arcabouço fiscal para 2027")
    testar("IPCA de janeiro fica em 0,42%, acima do esperado")
    testar("Dólar sobe e Ibovespa recua em dia de volatilidade")
    testar("Arthur Lira articula votação de PEC no plenário")
    testar("Kiev exporta armas em tempos de guerra")  # pode cair em Não classificado

    print("=" * 60)
