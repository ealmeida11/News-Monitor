# Estrutura do Projeto - Newsflow Macro Brasil

## 📂 Organização Atual

```
news_monitor_v2/
│
├── 📁 classificador/              # Sistema de classificação
│   ├── lexico_classifier.py          # Classificador por palavras-chave
│   ├── temas_keywords.json           # ⭐ EDITAR: palavras-chave por tema
│   └── README.md                     # Como adicionar temas
│
├── 📁 config/                     # Configurações
│   ├── settings.py                   # Configurações gerais
│   └── categorias_excluidas.txt      # Categorias a ignorar na coleta
│
├── 📁 dashboard/                  # Painel Streamlit (opcional)
│   └── app.py                        # App Streamlit (não usado atualmente)
│
├── 📁 tests/                       # ⭐ Scripts principais
│   ├── test_valor_classificar_todas.py  # ⭐ COLETA VALOR
│   ├── gerar_painel_html.py            # ⭐ GERA PAINEL HTML
│   ├── reclassificar_json.py           # Reclassifica sem coletar
│   ├── gerar_html_revisao.py           # HTML para revisar classificação
│   ├── processar_feedback.py           # Processa feedback e sugere keywords
│   ├── output/                          # Saídas
│   │   ├── valor_classificado_24h.json # ⭐ Dados coletados
│   │   └── painel_dashboard.html        # ⭐ Painel final
│   ├── GUIA_RAPIDO.md                  # Guia rápido de uso
│   ├── GUIA_TREINAMENTO.md             # Processo de revisão completo
│   └── README.md                       # Documentação dos scripts
│
├── 📁 docs/                        # Documentação
│   ├── MAPEAMENTO_SITES.md            # Como cada site funciona
│   └── PROXIMOS_PASSOS.md             # Como adicionar novos jornais
│
├── 📁 database/                    # (Futuro) Banco de dados
├── 📁 email_service/               # (Futuro) Email matinal
├── 📁 scheduler/                    # (Futuro) Agendamento
├── 📁 scrapers/                     # (Futuro) Scrapers modulares
│
├── README.md                        # ⭐ Visão geral do projeto
├── ESTRUTURA.md                     # Este arquivo
└── requirements.txt                  # Dependências Python
```

---

## 🎯 Arquivos Principais (O que usar no dia a dia)

### Para Coletar Notícias
- `tests/test_valor_classificar_todas.py` → Coleta e classifica Valor

### Para Ver Resultados
- `tests/output/painel_dashboard.html` → Abrir no navegador

### Para Ajustar Classificação
- `classificador/temas_keywords.json` → Editar palavras-chave

### Para Revisar Classificação
- `tests/gerar_html_revisao.py` → Gera HTML de revisão
- `tests/processar_feedback.py` → Processa feedback

---

## 📝 Fluxo de Trabalho Atual

```
1. Coletar
   python tests/test_valor_classificar_todas.py
   ↓
   output/valor_classificado_24h.json

2. Gerar Painel
   python tests/gerar_painel_html.py
   ↓
   output/painel_dashboard.html (abrir no navegador)

3. Se encontrar erros de classificação:
   python tests/gerar_html_revisao.py
   → Revisar em output/revisao_classificacao.html
   → Salvar feedback
   python tests/processar_feedback.py
   → Editar classificador/temas_keywords.json
   python tests/reclassificar_json.py
```

---

## 🚀 Próximos Passos

Ver `docs/PROXIMOS_PASSOS.md` para:
- Checklist de validação
- Template para novo jornal
- Ordem sugerida (Estadão → Folha → O Globo → ...)

---

**Última atualização:** 12/02/2026
