# -*- coding: utf-8 -*-
"""
Recebe feedback de classificação de duas formas:
1. Lê arquivo feedback_classificacao.json de qualquer lugar
2. Permite colar JSON diretamente

Uso:
    python receber_feedback.py
    # Ou colar JSON quando solicitado
"""

import json
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
FEEDBACK_FILE = OUTPUT_DIR / "feedback_classificacao.json"


def procurar_arquivo():
    """Procura feedback_classificacao.json em locais comuns."""
    locais = [
        OUTPUT_DIR / "feedback_classificacao.json",
        Path.home() / "Downloads" / "feedback_classificacao.json",
        Path.home() / "Desktop" / "feedback_classificacao.json",
    ]
    for local in locais:
        if local.exists():
            return local
    return None


def main():
    print("=" * 70)
    print("  RECEBER FEEDBACK DE CLASSIFICAÇÃO")
    print("=" * 70)
    print()

    # Tentar encontrar arquivo automaticamente
    arq_encontrado = procurar_arquivo()
    if arq_encontrado:
        print(f"✅ Arquivo encontrado: {arq_encontrado}")
        print(f"   Deseja usar este arquivo? (s/n): ", end="")
        resposta = input().strip().lower()
        if resposta == 's':
            with open(arq_encontrado, "r", encoding="utf-8") as f:
                feedback = json.load(f)
            # Copiar para pasta output
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(feedback, f, ensure_ascii=False, indent=2)
            print(f"✅ Arquivo copiado para: {FEEDBACK_FILE}")
            return feedback
    else:
        print("❌ Arquivo não encontrado automaticamente.")
        print()

    # Opção 1: Caminho manual
    print("Opção 1: Informe o caminho completo do arquivo JSON")
    print("Opção 2: Cole o JSON diretamente (pressione Enter para pular)")
    print()
    escolha = input("Escolha (1 ou 2): ").strip()

    if escolha == "1":
        caminho = input("Caminho do arquivo: ").strip().strip('"')
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                feedback = json.load(f)
            # Copiar para pasta output
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(feedback, f, ensure_ascii=False, indent=2)
            print(f"✅ Arquivo lido e copiado para: {FEEDBACK_FILE}")
            return feedback
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            return None

    elif escolha == "2":
        print()
        print("Cole o JSON abaixo (termine com linha em branco + Ctrl+Z + Enter):")
        print("-" * 70)
        linhas = []
        try:
            while True:
                linha = input()
                linhas.append(linha)
        except EOFError:
            pass
        json_str = "\n".join(linhas)
        try:
            feedback = json.loads(json_str)
            # Salvar em output
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(feedback, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON recebido e salvo em: {FEEDBACK_FILE}")
            return feedback
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao processar JSON: {e}")
            return None

    else:
        print("Opção inválida.")
        return None


if __name__ == "__main__":
    feedback = main()
    if feedback:
        print()
        print("=" * 70)
        print("  FEEDBACK RECEBIDO COM SUCESSO!")
        print("=" * 70)
        correcoes = feedback.get("correcoes", [])
        print(f"Total de correções: {len(correcoes)}")
        print()
        print("Agora rode: python processar_feedback.py")
        print("=" * 70)
