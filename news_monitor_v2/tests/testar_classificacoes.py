# -*- coding: utf-8 -*-
"""Testa classificações específicas para verificar se estão corretas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classificador.lexico_classifier import classificar

testes = [
    {
        "titulo": "Fluxo cambial registra saída de US$ 294 milhões na semana de 6 de fevereiro, informa BC",
        "resumo": "",
        "esperado": "Mercado"
    },
    {
        "titulo": "Bolsa Família 2026: pagamentos começam antes do Carnaval; veja tabela e valores",
        "resumo": "",
        "esperado": "Não classificado"
    },
    {
        "titulo": "Maus resultados no Enamed impulsionam o debate sobre a qualificação dos médicos",
        "resumo": "",
        "esperado": "Não classificado"
    },
    {
        "titulo": "TRE-MG rejeita por unanimidade ações que pediam cassação de Nikolas Ferreira",
        "resumo": "",
        "esperado": "Governo/Congresso"
    },
]

print("=" * 70)
print("  TESTE DE CLASSIFICAÇÕES ESPECÍFICAS")
print("=" * 70)
print()

for i, teste in enumerate(testes, 1):
    resultado = classificar(teste["titulo"], resumo=teste.get("resumo", ""))
    tema = resultado["tema"]
    esperado = teste["esperado"]
    status = "OK" if tema == esperado else "ERRO"
    
    print(f"{i}. {status} Esperado: {esperado} | Obtido: {tema}")
    print(f"   Título: {teste['titulo'][:70]}...")
    if tema != esperado:
        print(f"   Scores: {resultado['scores']}")
    print()
