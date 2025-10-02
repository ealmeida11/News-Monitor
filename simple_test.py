#!/usr/bin/env python
# -*- coding: utf-8 -*-

print("Teste simples iniciado...")

try:
    import requests
    print("Requests importado com sucesso")
    
    print("Fazendo requisição para a Folha...")
    response = requests.get("https://www1.folha.uol.com.br/ultimas-noticias/", timeout=10)
    print(f"Status code: {response.status_code}")
    print(f"Tamanho da resposta: {len(response.text)} caracteres")
    
    if "c-main-headline__url" in response.text:
        print("✓ Elemento c-main-headline__url encontrado no HTML")
    else:
        print("✗ Elemento c-main-headline__url NÃO encontrado")
        
    if "folha.uol.com.br" in response.text:
        print("✓ Links da Folha encontrados no HTML")
    else:
        print("✗ Links da Folha NÃO encontrados")
        
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()

print("Teste concluído.")
