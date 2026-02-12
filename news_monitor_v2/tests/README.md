# Tests - Scripts Principais

## ⭐ Scripts Essenciais

### `test_valor_classificar_todas.py`
**Coleta e classifica notícias do Valor Econômico**

```bash
python test_valor_classificar_todas.py
```

**O que faz:**
- Coleta notícias das últimas 24h do Valor
- Classifica cada uma por tema (Fiscal, BC, Mercado, etc.)
- Exclui tema "Mundo" e categoria "Mundo" do site
- Salva em `output/valor_classificado_24h.json`

---

### `gerar_painel_html.py`
**Gera painel HTML interativo**

```bash
python gerar_painel_html.py
```

**O que faz:**
- Lê `output/valor_classificado_24h.json`
- Gera `output/painel_dashboard.html` com tabela interativa
- Funcionalidades: busca, filtro, ordenação, paginação

**Abrir:** `output/painel_dashboard.html` no navegador

---

## 🔧 Scripts de Apoio

### `reclassificar_json.py`
Reclassifica notícias de um JSON existente (sem coletar de novo).  
Útil quando você ajustou keywords e quer reclassificar os mesmos dados.

```bash
python reclassificar_json.py
```

---

### `gerar_html_revisao.py`
Gera HTML interativo para revisar classificação manualmente.

```bash
python gerar_html_revisao.py
# Abrir output/revisao_classificacao.html
# Marcar correções e salvar feedback
```

---

### `processar_feedback.py`
Processa feedback de revisão e sugere ajustes nas keywords.

```bash
python processar_feedback.py
# Veja sugestões em output/sugestoes_keywords.txt
```

---

## 📁 Estrutura de Saídas

```
tests/output/
├── valor_classificado_24h.json      # ⭐ Dados coletados e classificados
├── painel_dashboard.html             # ⭐ Painel final (abrir no navegador)
├── valor_classificado_24h.html      # Relatório simples (opcional)
├── revisao_classificacao.html       # HTML para revisar (gerado sob demanda)
├── feedback_classificacao.json      # Feedback de revisão (gerado manualmente)
└── sugestoes_keywords.txt           # Sugestões de keywords (gerado por processar_feedback.py)
```

---

## 📚 Documentação

- `GUIA_RAPIDO.md` - Guia rápido de uso diário
- `GUIA_TREINAMENTO.md` - Processo completo de revisão e ajuste
- `../docs/PROXIMOS_PASSOS.md` - Como adicionar novos jornais
- `../README.md` - Visão geral do projeto

---

**Última atualização:** 12/02/2026
