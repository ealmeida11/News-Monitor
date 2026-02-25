# -*- coding: utf-8 -*-
"""Configurações gerais do Monitor de Notícias V2."""

import os
from pathlib import Path

# Caminho base do projeto (pasta news_monitor_v2)
BASE_DIR = Path(__file__).resolve().parent.parent

# Caminho do projeto principal (Brasil/News) para usar scrapers atuais
PROJECT_ROOT = BASE_DIR.parent

# Banco de dados (evita duplicatas por link; usado por run_coleta.py)
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "noticias_v2.db"))

# Scraper original (para testes)
SCRAPER_ORIGINAL_PATH = PROJECT_ROOT / "scraper_otimizado.py"
DB_ORIGINAL_PATH = PROJECT_ROOT / "noticias.db"

# Pastas
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Fontes atuais para validação e coleta
FONTES_ATUAIS = ["Valor Econômico", "Estadão", "Folha de S.Paulo", "O Globo", "CNN Brasil", "Metrópoles"]

# Temas para classificação (futuro)
TEMAS = [
    "Governo/Congresso",
    "Fiscal",
    "Eleições",
    "Inflação",
    "Banco Central",
    "Mercado",
    "Editorial",
    "Mundo",
    "Atividade",
]
