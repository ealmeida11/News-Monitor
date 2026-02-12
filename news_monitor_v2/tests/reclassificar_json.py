# -*- coding: utf-8 -*-
"""
Reclassifica notícias a partir de um JSON existente (sem fazer nova coleta).
Útil para testar mudanças no classificador quando a rede falha na coleta.

Uso:
  python reclassificar_json.py

Usa test_valor_econômico_*.json mais recente em output/ ou valor_classificado_24h.json
se tiver notícias. Cada item deve ter: titulo, categoria, link, data, hora; resumo opcional.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classificador.lexico_classifier import classificar, NAO_CLASSIFICADO

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _carregar_noticias():
    """Carrega lista de notícias de um JSON disponível."""
    # Se valor_classificado_24h tem itens, extrair lista única (por_tema + nao_classificadas)
    arq_principal = OUTPUT_DIR / "valor_classificado_24h.json"
    if arq_principal.exists():
        with open(arq_principal, "r", encoding="utf-8") as f:
            data = json.load(f)
        total = data.get("total_coletado", 0)
        if total > 0:
            lista = []
            for tema, itens in data.get("por_tema", {}).items():
                lista.extend(itens)
            lista.extend(data.get("nao_classificadas", []))
            if lista:
                return lista, "valor_classificado_24h.json"

    # Senão, usar o backup de coleta (sem resumo)
    backups = sorted(OUTPUT_DIR.glob("test_valor_econômico_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for arq in backups:
        with open(arq, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list) and len(raw) > 0:
            # Garantir campos mínimos
            for n in raw:
                n.setdefault("resumo", "")
                n.setdefault("tema_classificado", "")
                n.setdefault("score", 0)
                n.setdefault("scores_todos", {})
            return raw, arq.name

    return None, None


def main():
    noticias, origem = _carregar_noticias()
    if not noticias:
        print("Nenhum JSON com notícias encontrado em output/.")
        print("Rode test_valor_classificar_todas.py quando a rede estiver ok.")
        return

    print("=" * 70)
    print("  RECLASSIFICAÇÃO (sem nova coleta)")
    print("=" * 70)
    print(f"  Fonte: {origem}")
    print(f"  Total: {len(noticias)} notícias")
    print("  Classificando com o léxico atual...")
    print()

    noticias_por_tema = defaultdict(list)
    nao_classificadas = []

    for noticia in noticias:
        categoria_site = noticia.get("categoria", "")
        if categoria_site == "Mundo":
            tema = "Mundo"
            noticia["tema_classificado"] = tema
            noticia["score"] = 1
            noticia["scores_todos"] = {"Mundo": 1}
            noticias_por_tema[tema].append(noticia)
        else:
            resultado = classificar(noticia["titulo"], resumo=noticia.get("resumo") or "")
            tema = resultado["tema"]
            noticia["tema_classificado"] = tema
            noticia["score"] = resultado["score"]
            noticia["scores_todos"] = resultado["scores"]
            if tema == NAO_CLASSIFICADO:
                nao_classificadas.append(noticia)
            else:
                noticias_por_tema[tema].append(noticia)

    # Resumo
    print("  RESULTADO")
    print("-" * 70)
    for tema in sorted(noticias_por_tema.keys()):
        print(f"  {tema}: {len(noticias_por_tema[tema])}")
    print(f"  Não classificadas: {len(nao_classificadas)}")
    print()

    # Salvar (formato igual ao test_valor_classificar_todas)
    from datetime import datetime
    from test_valor_classificar_todas import _gerar_html

    arq_json = OUTPUT_DIR / "valor_classificado_24h.json"
    arq_html = OUTPUT_DIR / "valor_classificado_24h.html"
    resultado_completo = {
        "data_coleta": datetime.now().isoformat(),
        "periodo_horas": 24,
        "total_coletado": len(noticias),
        "por_tema": dict(noticias_por_tema),
        "nao_classificadas": nao_classificadas,
    }
    with open(arq_json, "w", encoding="utf-8") as f:
        json.dump(resultado_completo, f, ensure_ascii=False, indent=2)
    _gerar_html(noticias_por_tema, nao_classificadas, len(noticias), arq_html)

    print(f"  JSON: {arq_json}")
    print(f"  HTML: {arq_html}")
    print("=" * 70)


if __name__ == "__main__":
    main()
