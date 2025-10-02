#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

print("Debugando regex para data da Folha...")

# Texto de exemplo
texto_original = "2.out.2025 Ã s 13h31"
print(f"Texto original: '{texto_original}'")

# Normalizar
texto_normalizado = texto_original.replace('Ã s', 'às').replace('Ã¡', 'á').replace('Ã£', 'ã').replace('Ã³', 'ó')
print(f"Texto normalizado: '{texto_normalizado}'")

# Testar diferentes padrões
patterns = [
    r'(\d{1,2})\.(\w{3})\.(\d{4})\s+às\s+(\d{1,2})h(\d{2})',  # Formato normal
    r'(\d{1,2})\.(\w{3})\.(\d{4})\s+(\d{1,2})h(\d{2})',      # Sem "às"
    r'(\d{1,2})\.(\w{3})\.(\d{4}).*?(\d{1,2})h(\d{2})',      # Mais flexível
]

for i, pattern in enumerate(patterns):
    print(f"\nTestando padrão {i+1}: {pattern}")
    match = re.search(pattern, texto_normalizado)
    if match:
        print(f"✓ MATCH encontrado!")
        print(f"  Dia: {match.group(1)}")
        print(f"  Mês: {match.group(2)}")
        print(f"  Ano: {match.group(3)}")
        print(f"  Hora: {match.group(4)}")
        print(f"  Minuto: {match.group(5)}")
        
        # Processar
        dia = match.group(1).zfill(2)
        mes_texto = match.group(2).lower()
        ano = match.group(3)
        hora = match.group(4).zfill(2)
        minuto = match.group(5)
        
        meses = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
            'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        }
        
        if mes_texto in meses:
            mes = meses[mes_texto]
            data_formatada = f"{dia}/{mes}/{ano}"
            hora_formatada = f"{hora}:{minuto}"
            print(f"  Resultado: {data_formatada} {hora_formatada}")
        else:
            print(f"  ❌ Mês '{mes_texto}' não encontrado no dicionário")
    else:
        print(f"❌ Sem match")

# Testar com diferentes variações
print(f"\n=== TESTANDO VARIAÇÕES ===")
variacoes = [
    "2.out.2025 às 13h31",
    "2.out.2025 Ã s 13h31", 
    "02.out.2025 às 13h31",
    "2.out.2025 às 1h31",
    "2.out.2025 às 13h01",
]

for texto in variacoes:
    print(f"\nTestando: '{texto}'")
    texto_norm = texto.replace('Ã s', 'às')
    match = re.search(r'(\d{1,2})\.(\w{3})\.(\d{4})\s+(\d{1,2})h(\d{2})', texto_norm)
    if match:
        print(f"✓ MATCH: {match.groups()}")
    else:
        print(f"❌ Sem match")

print("\nDebug concluído.")
