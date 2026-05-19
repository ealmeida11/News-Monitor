# -*- coding: utf-8 -*-
"""
Paths e constantes do subprojeto peak Brasil (UI manual de seleção).
"""

from pathlib import Path

PEAK_DIR = Path(__file__).resolve().parent
DATA_DIR = PEAK_DIR / "data"
UI_DIR = PEAK_DIR / "ui"

HEADLINES_JSON = DATA_DIR / "headlines.json"
SELECTION_JSON = DATA_DIR / "selection.json"
KEYWORDS_JSON = PEAK_DIR / "keywords.json"

SERVER_HOST = "127.0.0.1"

# DB path — newsai.db do pipeline diário Brasil
DB_PATH = PEAK_DIR.parent / "database" / "newsai.db"

# SOURCES da UI (ordem dos tabs).
# A tab "colunistas" é virtual (agregada via whitelist no db_reader).
SOURCES = [
    {"id": "oglobo",     "label": "O Globo"},
    {"id": "valor",      "label": "Valor"},
    {"id": "folha",      "label": "Folha"},
    {"id": "estadao",    "label": "Estadão"},
    {"id": "metropoles", "label": "Metrópoles"},
    {"id": "cnn",        "label": "CNN"},
]
SOURCE_LABELS = {s["id"]: s["label"] for s in SOURCES}

# Tab virtual de colunistas (não é uma fonte real)
COLUNISTAS_TAB_ID = "colunistas"
COLUNISTAS_TAB_LABEL = "Colunistas"

# Ordem de prioridade pra dedup quando o mesmo título aparece em várias fontes
# (1º vence). User-curated.
DEDUP_PRIORITY = ["oglobo", "valor", "folha", "estadao", "metropoles", "cnn"]
_DEDUP_RANK = {sid: i for i, sid in enumerate(DEDUP_PRIORITY)}


def dedup_rank(source_id: str) -> int:
    """Quanto menor o rank, maior a prioridade."""
    return _DEDUP_RANK.get(source_id, 99)


# Janela temporal default (horas)
WINDOW_HOURS = 24

# Mapeamento das fontes em `headlines.fonte` (string como vem do DB) → source_id
# Necessário porque o pipeline diário grava a label, não o id.
DB_SOURCE_TO_ID = {
    "O Globo": "oglobo",
    "oglobo": "oglobo",
    "Valor Econômico": "valor",
    "Valor": "valor",
    "valor": "valor",
    "Folha de S.Paulo": "folha",
    "Folha": "folha",
    "folha": "folha",
    "Estadão": "estadao",
    "estadao": "estadao",
    "Metrópoles": "metropoles",
    "metropoles": "metropoles",
    "CNN Brasil": "cnn",
    "CNN": "cnn",
    "cnn": "cnn",
}

WHATSAPP_HEADER_TEMPLATE = "📰 *JGP - Newsflow Macro BR - {date_br}*"
TINYURL_API = "http://tinyurl.com/api-create.php?url={url}"

# Destinatário do peak Brasil — isolado do .env global (que tem os grupos do
# pipeline diário). Peak envia só pra este número pessoal.
PEAK_WHATSAPP_RECIPIENTS = ["5521989020903@c.us"]
