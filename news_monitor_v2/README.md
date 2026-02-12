# Newsflow Macro Brasil - Monitor de Notícias V2

Sistema de monitoramento de notícias macroeconômicas brasileiras com classificação automática por temas.

## 📋 Status Atual

✅ **Valor Econômico** - Mapeado e funcionando  
⏳ **Estadão, Folha, O Globo** - Próximos  
⏳ **Metrópoles, G1, CNN** - Planejados

---

## 🗂️ Estrutura do Projeto

```
news_monitor_v2/
├── classificador/          # Sistema de classificação por temas
│   ├── lexico_classifier.py    # Classificador por palavras-chave
│   └── temas_keywords.json     # Palavras-chave por tema (EDITAR AQUI)
│
├── config/                  # Configurações
│   ├── settings.py             # Configurações gerais
│   └── categorias_excluidas.txt # Categorias a ignorar na coleta
│
├── dashboard/               # Painel de visualização
│   └── app.py                  # Streamlit (opcional)
│
├── tests/                   # Scripts principais de coleta e geração
│   ├── test_valor_classificar_todas.py  # ⭐ COLETA VALOR + CLASSIFICAÇÃO
│   ├── gerar_painel_html.py             # ⭐ GERA PAINEL HTML FINAL
│   ├── reclassificar_json.py            # Reclassifica JSON existente (sem coletar)
│   ├── gerar_html_revisao.py            # Gera HTML para revisar classificação
│   ├── processar_feedback.py            # Processa feedback e sugere keywords
│   └── output/                          # Saídas (JSON, HTML)
│       ├── valor_classificado_24h.json # Dados coletados e classificados
│       └── painel_dashboard.html        # Painel final (ABRIR NO NAVEGADOR)
│
├── docs/                    # Documentação
│   └── MAPEAMENTO_SITES.md      # Como cada site funciona hoje
│
└── requirements.txt         # Dependências Python
```

---

## 🚀 Como Usar (Valor Econômico)

### 1. Coletar e Classificar Notícias

```bash
cd news_monitor_v2/tests
python test_valor_classificar_todas.py
```

**O que faz:**
- Coleta notícias das últimas 24h do Valor
- Classifica cada uma por tema (Fiscal, BC, Mercado, etc.)
- Exclui automaticamente tema "Mundo" e notícias cuja categoria do site é "Mundo"
- Salva em `output/valor_classificado_24h.json`

**Saída:** Console mostra resumo + arquivos JSON e HTML simples

---

### 2. Gerar Painel HTML

```bash
python gerar_painel_html.py
```

**O que faz:**
- Lê `valor_classificado_24h.json`
- Gera `output/painel_dashboard.html` com tabela interativa

**Funcionalidades do painel:**
- 🔍 Busca por título/resumo
- 🏷️ Filtro por categoria/tema
- ↕️ Ordenação clicável nas colunas
- 📄 Paginação (25 por página)
- 📊 Categorias coloridas

**Abrir:** `tests/output/painel_dashboard.html` no navegador

---

### 3. Revisar e Ajustar Classificação

Se encontrar classificações erradas:

```bash
# 1. Gerar HTML de revisão
python gerar_html_revisao.py

# 2. Abrir output/revisao_classificacao.html no navegador
# 3. Marcar correções e salvar feedback
# 4. Processar feedback
python processar_feedback.py

# 5. Editar classificador/temas_keywords.json com as sugestões
# 6. Reclassificar sem coletar de novo
python reclassificar_json.py
```

---

## 🎯 Temas de Classificação

Atualmente classificamos em **7 temas** (Mundo desativado):

1. **Governo/Congresso** - Política, STF, Congresso, ministros
2. **Fiscal** - Orçamento, dívida, impostos, Plano Safra
3. **Eleições** - Campanhas, pesquisas, TSE, candidatos
4. **Inflação** - IPCA, índices de preços, metas
5. **Banco Central** - Copom, Selic, política monetária
6. **Mercado** - Bolsa, dólar, cripto, investimentos
7. **Atividade** - PIB, IBGE, produção industrial, serviços
8. **Editorial** - Artigos de opinião

**Arquivo de configuração:** `classificador/temas_keywords.json`

---

## 📝 Próximos Passos: Mapear Outros Jornais

### Checklist para cada novo jornal:

1. **Criar script de teste** (ex: `test_estadao_classificar_todas.py`)
   - Copiar estrutura de `test_valor_classificar_todas.py`
   - Ajustar URL e seletores CSS/HTML
   - Testar coleta de título, link, categoria, data/hora, **resumo**

2. **Validar coleta**
   - Verificar se pega notícias das últimas 24h
   - Confirmar que resumo está sendo extraído
   - Testar paginação/parada

3. **Integrar no painel**
   - Atualizar `gerar_painel_html.py` para ler múltiplos JSONs
   - Agregar notícias de todas as fontes
   - Manter ordenação por data/hora

4. **Documentar**
   - Adicionar seção em `docs/MAPEAMENTO_SITES.md`
   - Anotar URLs, seletores, particularidades

---

## 🔧 Configurações Importantes

### Exclusões Automáticas

- **Tema "Mundo"**: Não aparece no painel (desativado)
- **Categoria "Mundo" do site**: Notícias descartadas mesmo se classificadas em outro tema
- **Categorias excluídas**: Ver `config/categorias_excluidas.txt`
  - Valor: ESG, Carreira, Empresas, Eu &, Marketing

### Filtros de Tempo

- Coleta: últimas **24 horas** (configurável em `test_valor_classificar_todas.py`)
- Critério de parada: ≥5 notícias antigas na mesma página

---

## 📚 Documentação Adicional

- `docs/MAPEAMENTO_SITES.md` - Como cada site funciona hoje
- `classificador/README.md` - Como adicionar/modificar temas
- `tests/GUIA_TREINAMENTO.md` - Processo de revisão e ajuste de keywords

---

## 🛠️ Dependências

Ver `requirements.txt`. Principais:
- selenium, beautifulsoup4 (scraping)
- pandas (processamento)
- streamlit, streamlit-autorefresh (dashboard opcional)

---

**Última atualização:** 12/02/2026
