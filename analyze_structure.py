#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
from bs4 import BeautifulSoup

print("Analisando estrutura HTML da Folha...")

try:
    response = requests.get("https://www1.folha.uol.com.br/ultimas-noticias/", timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Encontrar elementos que contêm títulos
    artigos = soup.find_all('a', href=re.compile(r"folha\.uol\.com\.br/.*\.shtml"))
    
    print(f"Total de links encontrados: {len(artigos)}")
    
    # Analisar os primeiros 5 elementos
    print("\n=== ANÁLISE DOS PRIMEIROS 5 ELEMENTOS ===")
    
    for i, artigo in enumerate(artigos[:5]):
        print(f"\n--- Elemento {i+1} ---")
        href = artigo.get('href', 'N/A')
        print(f"Link: {href}")
        
        # Verificar se tem título diretamente
        if artigo.text.strip():
            print(f"Texto direto: {artigo.text.strip()[:100]}...")
        
        # Verificar elementos filhos
        h2_elements = artigo.find_all('h2')
        print(f"Elementos h2 filhos: {len(h2_elements)}")
        
        for j, h2 in enumerate(h2_elements):
            classes = h2.get('class', [])
            text = h2.text.strip()
            print(f"  h2[{j}]: classes={classes}, texto='{text[:50]}...'")
        
        # Verificar elementos time (data)
        time_elements = artigo.find_all('time')
        print(f"Elementos time filhos: {len(time_elements)}")
        
        for j, time_elem in enumerate(time_elements):
            classes = time_elem.get('class', [])
            text = time_elem.text.strip()
            print(f"  time[{j}]: classes={classes}, texto='{text}'")
        
        # Verificar estrutura do pai
        parent = artigo.parent
        if parent:
            print(f"Elemento pai: {parent.name} (classes: {parent.get('class', [])})")
            
            # Verificar títulos no pai
            parent_h2 = parent.find_all('h2')
            print(f"Títulos no pai: {len(parent_h2)}")
            
            for j, h2 in enumerate(parent_h2):
                classes = h2.get('class', [])
                text = h2.text.strip()
                print(f"  pai h2[{j}]: classes={classes}, texto='{text[:50]}...'")
        
        print("-" * 50)

except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()

print("Análise concluída.")
