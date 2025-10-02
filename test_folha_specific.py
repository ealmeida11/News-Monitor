#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def noticia_dentro_24h(data, hora):
    """Verifica se uma notícia está dentro das últimas 24 horas"""
    try:
        # Converter data e hora para datetime
        data_hora_str = f"{data} {hora}"
        data_hora_noticia = datetime.strptime(data_hora_str, "%d/%m/%Y %H:%M")
        
        # Calcular 24 horas atrás
        limite_24h = datetime.now() - timedelta(hours=24)
        
        # Verificar se a notícia está dentro das últimas 24 horas
        return data_hora_noticia >= limite_24h
    except:
        # Se houver erro na conversão, considerar como válida
        return True

def processar_data_folha(data_hora_texto):
    """Processa data da Folha no formato "25.abr.2025 às 12h22" ou "25.abr.2025 Ã s 12h22" """
    # Normalizar texto para lidar com problemas de codificação
    texto_normalizado = data_hora_texto.replace('Ã s', 'às').replace('Ã¡', 'á').replace('Ã£', 'ã').replace('Ã³', 'ó')
    
    # Tentar diferentes padrões de regex
    patterns = [
        r'(\d{1,2})\.(\w{3})\.(\d{4})\s+às\s+(\d{1,2})h(\d{2})',  # Formato normal
        r'(\d{1,2})\.(\w{3})\.(\d{4})\s+(\d{1,2})h(\d{2})',      # Sem "às"
    ]
    
    for pattern in patterns:
        data_match = re.search(pattern, texto_normalizado)
        if data_match:
            dia = data_match.group(1).zfill(2)  # Garantir 2 dígitos
            mes_texto = data_match.group(2).lower()
            ano = data_match.group(3)
            hora = data_match.group(4).zfill(2)  # Garantir 2 dígitos
            minuto = data_match.group(5)
            
            meses = {
                'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
                'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
            }
            
            if mes_texto in meses:
                mes = meses[mes_texto]
                data_formatada = f"{dia}/{mes}/{ano}"
                hora_formatada = f"{hora}:{minuto}"
                return (data_formatada, hora_formatada)
    return None

print("Testando processamento específico da Folha...")

try:
    response = requests.get("https://www1.folha.uol.com.br/ultimas-noticias/", timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Encontrar elementos com título e data
    artigos = soup.find_all('a', href=re.compile(r"folha\.uol\.com\.br/.*\.shtml"))
    
    print(f"Total de links encontrados: {len(artigos)}")
    
    noticias_validas = 0
    noticias_rejeitadas_data = 0
    noticias_sem_titulo = 0
    noticias_sem_data = 0
    
    print("\n=== ANALISANDO PRIMEIROS 10 ELEMENTOS ===")
    
    for i, artigo in enumerate(artigos[:10]):
        print(f"\n--- Elemento {i+1} ---")
        
        # Verificar título
        titulo_element = artigo.find('h2', class_='c-headline__title')
        if not titulo_element:
            print("❌ Sem título")
            noticias_sem_titulo += 1
            continue
        
        titulo = titulo_element.text.strip()
        print(f"✓ Título: {titulo[:60]}...")
        
        # Verificar data
        data_element = artigo.find('time', class_='c-headline__dateline')
        if not data_element:
            print("❌ Sem data")
            noticias_sem_data += 1
            continue
        
        data_texto = data_element.text.strip()
        print(f"✓ Data original: {data_texto}")
        
        # Processar data
        data_hora = processar_data_folha(data_texto)
        if not data_hora:
            print("❌ Erro no processamento da data")
            noticias_sem_data += 1
            continue
        
        data_formatada, hora_formatada = data_hora
        print(f"✓ Data processada: {data_formatada} {hora_formatada}")
        
        # Verificar se está dentro de 24h
        dentro_24h = noticia_dentro_24h(data_formatada, hora_formatada)
        print(f"✓ Dentro de 24h: {dentro_24h}")
        
        if dentro_24h:
            noticias_validas += 1
            print("✅ NOTÍCIA VÁLIDA!")
        else:
            noticias_rejeitadas_data += 1
            print("❌ Rejeitada por data antiga")
    
    print(f"\n=== RESUMO ===")
    print(f"Total analisados: 10")
    print(f"Sem título: {noticias_sem_titulo}")
    print(f"Sem data: {noticias_sem_data}")
    print(f"Rejeitadas por data: {noticias_rejeitadas_data}")
    print(f"Notícias válidas: {noticias_validas}")
    
    # Verificar data atual
    agora = datetime.now()
    print(f"\nData/hora atual: {agora.strftime('%d/%m/%Y %H:%M')}")
    limite_24h = agora - timedelta(hours=24)
    print(f"Limite 24h: {limite_24h.strftime('%d/%m/%Y %H:%M')}")

except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()

print("Teste concluído.")
