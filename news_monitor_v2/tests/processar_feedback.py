# -*- coding: utf-8 -*-
"""
Processa o arquivo feedback_classificacao.json gerado pela revisão manual
e sugere ajustes nas palavras-chave dos temas.

Uso:
    1. Abra revisao_classificacao.html no navegador
    2. Revise as notícias e marque correções
    3. Clique em "Salvar Feedback" (baixa feedback_classificacao.json)
    4. Coloque o JSON em tests/output/
    5. Rode: python processar_feedback.py
"""

import json
from collections import defaultdict
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
FEEDBACK_FILE = OUTPUT_DIR / "feedback_classificacao.json"
SUGESTOES_FILE = OUTPUT_DIR / "sugestoes_keywords.txt"


def processar_feedback():
    """Lê feedback e gera sugestões de ajustes nas keywords."""
    if not FEEDBACK_FILE.exists():
        print(f"Arquivo {FEEDBACK_FILE} não encontrado.")
        print("1. Abra revisao_classificacao.html no navegador")
        print("2. Revise e marque correções")
        print("3. Clique em 'Salvar Feedback'")
        print("4. Coloque o JSON baixado em tests/output/")
        return

    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        feedback = json.load(f)

    correcoes = feedback.get("correcoes", [])
    if not correcoes:
        print("Nenhuma correção encontrada no feedback.")
        return

    # Agrupar por tema correto
    por_tema_correto = defaultdict(list)
    por_tema_atual = defaultdict(list)

    for corr in correcoes:
        tema_correto = corr.get("tema_correto", "")
        tema_atual = corr.get("tema_atual", "")
        if tema_correto:
            por_tema_correto[tema_correto].append(corr)
        if tema_atual != "Não classificado":
            por_tema_atual[tema_atual].append(corr)

    # Gerar relatório
    linhas = []
    linhas.append("=" * 70)
    linhas.append("  ANÁLISE DO FEEDBACK - SUGESTÕES DE AJUSTES")
    linhas.append("=" * 70)
    linhas.append(f"\nTotal de correções: {len(correcoes)}")
    linhas.append("")

    # Notícias que foram para tema errado
    linhas.append("=" * 70)
    linhas.append("  NOTÍCIAS CLASSIFICADAS NO TEMA ERRADO")
    linhas.append("=" * 70)
    linhas.append("")
    for tema_atual, lista in sorted(por_tema_atual.items()):
        if not lista:
            continue
        linhas.append(f"  [{len(lista)}] Estavam em '{tema_atual}' mas deveriam estar em:")
        linhas.append("-" * 70)
        por_tema_destino = defaultdict(list)
        for corr in lista:
            destino = corr.get("tema_correto", "?")
            por_tema_destino[destino].append(corr)
        for destino, corrs in sorted(por_tema_destino.items()):
            linhas.append(f"    -> {destino}:")
            for c in corrs[:5]:  # Mostrar até 5 exemplos
                linhas.append(f"      - {c['titulo'][:70]}...")
                if c.get('comentario'):
                    linhas.append(f"        Comentário: {c['comentario']}")
            if len(corrs) > 5:
                linhas.append(f"      ... e mais {len(corrs) - 5}")
        linhas.append("")

    # Notícias não classificadas que deveriam ter tema
    linhas.append("=" * 70)
    linhas.append("  NOTÍCIAS NÃO CLASSIFICADAS QUE DEVERIAM TER TEMA")
    linhas.append("=" * 70)
    linhas.append("")
    nao_class = [c for c in correcoes if c.get("tema_atual") == "Não classificado"]
    if nao_class:
        por_tema = defaultdict(list)
        for c in nao_class:
            tema = c.get("tema_correto", "?")
            por_tema[tema].append(c)
        for tema, lista in sorted(por_tema.items()):
            linhas.append(f"  [{len(lista)}] Deveriam estar em '{tema}':")
            linhas.append("-" * 70)
            for c in lista[:10]:
                linhas.append(f"    - {c['titulo'][:70]}...")
                if c.get('comentario'):
                    linhas.append(f"      Comentário: {c['comentario']}")
            if len(lista) > 10:
                linhas.append(f"    ... e mais {len(lista) - 10}")
            linhas.append("")
    else:
        linhas.append("  (nenhuma)")
        linhas.append("")

    # Sugestões de palavras-chave baseadas nos comentários
    linhas.append("=" * 70)
    linhas.append("  SUGESTÕES DE PALAVRAS-CHAVE (baseadas nos comentários)")
    linhas.append("=" * 70)
    linhas.append("")
    palavras_sugeridas = defaultdict(set)
    for corr in correcoes:
        comentario = corr.get("comentario", "").lower()
        tema_correto = corr.get("tema_correto", "")
        if comentario and tema_correto:
            # Extrair palavras do comentário (simples)
            palavras = [p.strip() for p in comentario.split() if len(p.strip()) > 3]
            for palavra in palavras:
                if palavra not in ["deveria", "ter", "para", "com", "que", "está", "estava"]:
                    palavras_sugeridas[tema_correto].add(palavra)
    if palavras_sugeridas:
        for tema, palavras in sorted(palavras_sugeridas.items()):
            linhas.append(f"  {tema}:")
            linhas.append(f"    {', '.join(sorted(palavras))}")
            linhas.append("")
    else:
        linhas.append("  (nenhuma sugestão extraída dos comentários)")
        linhas.append("")

    linhas.append("=" * 70)
    linhas.append("  PRÓXIMOS PASSOS")
    linhas.append("=" * 70)
    linhas.append("  1. Revise as sugestões acima")
    linhas.append("  2. Edite classificador/temas_keywords.json")
    linhas.append("  3. Adicione as palavras-chave sugeridas nos temas corretos")
    linhas.append("  4. Rode novamente: python test_valor_classificar_todas.py")
    linhas.append("=" * 70)

    # Salvar sugestões
    with open(SUGESTOES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print("\n".join(linhas))
    print(f"\nSugestões salvas em: {SUGESTOES_FILE}")


if __name__ == "__main__":
    processar_feedback()
