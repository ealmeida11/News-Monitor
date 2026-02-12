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
├── 📁 coletores/                  # ⭐ Coleta por fonte
│   ├── valor.py
│   ├── estadao.py
│   ├── folha.py
│   ├── oglobo.py
│   └── cnn.py
│
├── 📁 output/                     # Saídas (JSON + painel)
│   ├── *_classificado_24h.json
│   └── painel_dashboard.html
│
├── gerar_painel.py                # Gera painel HTML
├── run_coleta.py                  # ⭐ Orquestra: coletores + DB + painel
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

### Para Coletar e Ver Resultados
- `run_coleta.py` → Roda os 5 coletores, grava no DB e gera o painel
- `output/painel_dashboard.html` → Abrir no navegador

### Para Rodar um Coletor Só
- `coletores/valor.py`, `coletores/estadao.py`, etc.

### Para Ajustar Classificação
- `classificador/temas_keywords.json` → Editar palavras-chave

---

## 📝 Fluxo de Trabalho Atual

```
python run_coleta.py
   → Coletores (valor, estadao, folha, oglobo, cnn)
   → Inserção no banco (sem duplicatas)
   → output/painel_dashboard.html + index.html (GitHub Pages)
```

---

## 🚀 Próximos Passos

Ver `docs/PROXIMOS_PASSOS.md` para:
- Checklist de validação
- Template para novo jornal
- Ordem sugerida (Estadão → Folha → O Globo → ...)

---

**Última atualização:** 12/02/2026
