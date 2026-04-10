# News

Plataforma unificada de monitoramento, análise e distribuição de notícias macroeconômicas do Brasil.

## Componentes

| Módulo | Descrição | Execução |
|--------|-----------|----------|
| `realtime/` | Monitor real-time — envia notícias novas via WhatsApp | `scripts\run_monitor.bat` |
| `pipeline/` | Pipeline AI — gera briefings macro diários | `scripts\run_pipeline.bat` |
| `dashboard/` | Painel web — classificação temática (GitHub Pages) | `scripts\run_dashboard.bat` |
| `whatsapp/` | Servidor WhatsApp (Node.js) — compartilhado | `scripts\run_whatsapp.bat` |

## Quick Start

```bash
pip install -r requirements.txt
cd whatsapp && npm install && cd ..

# Terminal 1: WhatsApp
scripts\run_whatsapp.bat

# Terminal 2: Monitor real-time
scripts\run_monitor.bat
```

## Fontes

Valor Econômico · Folha de S.Paulo · Estadão · O Globo · CNN Brasil · Metrópoles

## Tecnologias

- Python 3.10+ (httpx, beautifulsoup4, websocket-client)
- Node.js 18+ (whatsapp-web.js)
- Microsoft Edge CDP (headless, paywall bypass)
- SQLite (armazenamento local)
