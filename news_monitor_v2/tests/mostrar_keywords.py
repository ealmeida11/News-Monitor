# -*- coding: utf-8 -*-
"""
Mostra as palavras-chave de cada tema para revisão.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classificador.lexico_classifier import _carregar_temas

temas = _carregar_temas()

print("=" * 70)
print("  PALAVRAS-CHAVE POR TEMA")
print("=" * 70)
print()

for tema, keywords in sorted(temas.items()):
    print(f"  [{tema}]")
    print("-" * 70)
    for kw in keywords:
        print(f"    - {kw}")
    print()

print("=" * 70)
print(f"  Total de temas: {len(temas)}")
print(f"  Total de keywords: {sum(len(kw) for kw in temas.values())}")
print("=" * 70)
