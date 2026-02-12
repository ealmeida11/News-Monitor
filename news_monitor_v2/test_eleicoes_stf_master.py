# -*- coding: utf-8 -*-
"""Testa classificação das manchetes de Eleições, STF e Caso Master."""
from classificador.lexico_classifier import classificar

# Manchetes que devem ser Eleições
titulos_eleicoes = [
    "Essa era pra ser eleição: Lula se reúne com Pacheco para discutir candidatura em Minas, em articulação que pode ajudar Messias no Senado",
    "'Não acho negativo, cada partido tem a liberdade de indicar seus candidatos', diz Flávio sobre falta de adesão do Centrão a seu nome",
]

# Manchetes que devem ser STF (não "corte de gastos")
titulos_stf = [
    "STF decide hoje sobre prisão de réu",
    "Barroso vota a favor no Plenário do Supremo",
]
titulo_corte_gastos = "Governo anuncia corte de gastos para cumprir teto"

# Caso Master
titulos_master = [
    "Daniel Vorcaro defende Banco Master em audiência",
    "Credcesta é alvo de investigação",
]

print("=== Eleições ===")
for t in titulos_eleicoes:
    r = classificar(titulo=t, resumo="")
    print(f"  {r['tema']} (score={r['score']}): {t[:60]}...")

print("\n=== STF ===")
for t in titulos_stf:
    r = classificar(titulo=t, resumo="")
    print(f"  {r['tema']} (score={r['score']}): {t[:60]}...")

print("\n=== Corte de gastos (não deve ser STF) ===")
r = classificar(titulo=titulo_corte_gastos, resumo="")
print(f"  {r['tema']} (score={r['score']})")

print("\n=== Caso Master ===")
for t in titulos_master:
    r = classificar(titulo=t, resumo="")
    print(f"  {r['tema']} (score={r['score']}): {t[:60]}...")
