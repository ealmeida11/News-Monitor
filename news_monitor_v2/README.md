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
├── coletores/               # Coleta por fonte (Valor, Estadão, Folha, O Globo, CNN)
│   ├── valor.py
│   ├── estadao.py
│   ├── folha.py
│   ├── oglobo.py
│   └── cnn.py
│
├── output/                  # Saídas (JSON por fonte + painel)
│   ├── *_classificado_24h.json
│   └── painel_dashboard.html   # Painel final (ABRIR NO NAVEGADOR)
│
├── gerar_painel.py          # Gera painel HTML a partir de lista de notícias
├── run_coleta.py            # ⭐ Script principal: coleta 5 fontes + DB + painel
│
├── docs/                    # Documentação
│   └── MAPEAMENTO_SITES.md      # Como cada site funciona hoje
│
└── requirements.txt         # Dependências Python
```

---

## 🚀 Como Usar (Valor Econômico)

### 1. Coletar, classificar e gerar painel (recomendado)

Na raiz do projeto ou em `news_monitor_v2`:

```bash
python news_monitor_v2/run_coleta.py
```

**O que faz:**
- Roda os 5 coletores (Valor, Estadão, Folha, O Globo, CNN)
- Grava notícias novas no banco (sem duplicatas por link)
- Gera `output/painel_dashboard.html` e copia para `index.html` (GitHub Pages)

**Abrir:** `news_monitor_v2/output/painel_dashboard.html` ou `index.html` na raiz

---

### 2. Rodar um coletor só (ex.: Valor)

```bash
cd news_monitor_v2
python coletores/valor.py
```

Salva em `output/valor_classificado_24h.json` (e HTML simples).

---

### 3. Ajustar classificação

Edite **classificador/temas_keywords.json** e rode de novo `run_coleta.py` ou o coletor desejado.

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

1. **Adicionar novo coletor** em `coletores/`
   - Copiar estrutura de `coletores/valor.py`
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

- Coleta: últimas **24 horas** (configurável em cada script em `coletores/`)
- Critério de parada: ≥5 notícias antigas na mesma página

---

## 📚 Documentação Adicional

- `docs/MAPEAMENTO_SITES.md` - Como cada site funciona hoje
- `classificador/README.md` - Como adicionar/modificar temas
- `classificador/temas_keywords.json` - Palavras-chave por tema (editar para ajustar)

---

## 🛠️ Dependências

Ver `requirements.txt`. Principais:
- selenium, beautifulsoup4 (scraping)
- pandas (processamento)
- streamlit, streamlit-autorefresh (dashboard opcional)

---

**Última atualização:** 12/02/2026
