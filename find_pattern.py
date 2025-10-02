#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
from bs4 import BeautifulSoup

print("Procurando padrão correto na Folha...")

try:
    response = requests.get("https://www1.folha.uol.com.br/ultimas-noticias/", timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Procurar por elementos que realmente contêm títulos
    artigos_com_titulo = []
    
    # Método 1: Procurar por links que têm h2 filhos com c-headline__title
    artigos = soup.find_all('a', href=re.compile(r"folha\.uol\.com\.br/.*\.shtml"))
    
    print(f"Total de links: {len(artigos)}")
    
    for artigo in artigos:
        # Verificar se tem h2 com c-headline__title
        h2_titulo = artigo.find('h2', class_='c-headline__title')
        if h2_titulo:
            titulo = h2_titulo.text.strip()
            link = artigo.get('href', '')
            
            # Verificar se tem data
            time_elem = artigo.find('time', class_='c-headline__dateline')
            data = time_elem.text.strip() if time_elem else 'Sem data'
            
            artigos_com_titulo.append({
                'titulo': titulo,
                'link': link,
                'data': data
            })
    
    print(f"\nElementos com título encontrados: {len(artigos_com_titulo)}")
    
    # Mostrar os primeiros 10
    print("\n=== PRIMEIROS 10 ELEMENTOS COM TÍTULO ===")
    for i, elem in enumerate(artigos_com_titulo[:10]):
        print(f"{i+1}. {elem['titulo'][:60]}...")
        print(f"   Data: {elem['data']}")
        print(f"   Link: {elem['link'][:80]}...")
        print()
    
    # Verificar se há outros padrões
    print("\n=== PROCURANDO OUTROS PADRÕES ===")
    
    # Procurar por divs que contêm notícias
    divs_noticias = soup.find_all('div', class_=re.compile(r'.*headline.*'))
    print(f"Divs com 'headline' na classe: {len(divs_noticias)}")
    
    # Procurar por elementos com c-headline__title
    titulos_diretos = soup.find_all('h2', class_='c-headline__title')
    print(f"Títulos diretos c-headline__title: {len(titulos_diretos)}")
    
    # Verificar estrutura dos títulos diretos
    print("\n=== PRIMEIROS 5 TÍTULOS DIRETOS ===")
    for i, titulo in enumerate(titulos_diretos[:5]):
        print(f"{i+1}. {titulo.text.strip()[:60]}...")
        # Verificar pai
        parent = titulo.parent
        if parent:
            print(f"   Pai: {parent.name} (classes: {parent.get('class', [])})")
            # Verificar se o pai é um link
            if parent.name == 'a':
                link = parent.get('href', '')
                print(f"   Link: {link[:80]}...")

except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()

print("Análise concluída.")
