# Próximos Passos - Mapeamento de Jornais

## ✅ Concluído

- [x] Valor Econômico - Coleta, classificação e painel funcionando
- [x] Sistema de classificação por léxico (palavras-chave)
- [x] Painel HTML interativo com busca, filtros e ordenação
- [x] Exclusão automática de tema Mundo e categoria Mundo do site

---

## 📋 Próximos Jornais (Ordem Sugerida)

### 1. Estadão (estadao.com.br)
**Prioridade:** Alta  
**Complexidade:** Média (JavaScript - precisa Selenium)

**O que já sabemos:**
- URL: `https://www.estadao.com.br/ultimas/`
- Usa "Carregar mais" (JavaScript)
- Ver `docs/MAPEAMENTO_SITES.md` para detalhes

**Tarefas:**
1. Criar `tests/test_estadao_classificar_todas.py` (copiar estrutura do Valor)
2. Ajustar seletores CSS para Estadão
3. Extrair resumo (verificar se existe no HTML)
4. Testar coleta das últimas 24h
5. Validar classificação
6. Integrar no painel (agregar com Valor)

---

### 2. Folha de S.Paulo (folha.uol.com.br)
**Prioridade:** Alta  
**Complexidade:** Média

**O que já sabemos:**
- URL: `https://www.folha.uol.com.br/ultimas-noticias/`
- Ver `docs/MAPEAMENTO_SITES.md` para detalhes

**Tarefas:**
1. Criar `tests/test_folha_classificar_todas.py`
2. Mapear seletores CSS
3. Extrair resumo
4. Testar e validar
5. Integrar no painel

---

### 3. O Globo (oglobo.globo.com)
**Prioridade:** Alta  
**Complexidade:** Média

**O que já sabemos:**
- URL: `https://oglobo.globo.com/ultimas-noticias/`
- Ver `docs/MAPEAMENTO_SITES.md` para detalhes

**Tarefas:**
1. Criar `tests/test_oglobo_classificar_todas.py`
2. Mapear seletores CSS
3. Extrair resumo
4. Testar e validar
5. Integrar no painel

---

### 4. Metrópoles (metropoles.com)
**Prioridade:** Média  
**Complexidade:** Baixa-Média

**Tarefas:**
1. Mapear estrutura do site
2. Criar script de coleta
3. Testar e validar
4. Integrar no painel

---

### 5. G1 (g1.globo.com)
**Prioridade:** Média  
**Complexidade:** Média-Alta (pode ter JavaScript)

**Tarefas:**
1. Mapear estrutura do site
2. Criar script de coleta
3. Testar e validar
4. Integrar no painel

---

### 6. CNN Brasil (cnnbrasil.com.br)
**Prioridade:** Baixa  
**Complexidade:** Média

**Tarefas:**
1. Mapear estrutura do site
2. Criar script de coleta
3. Testar e validar
4. Integrar no painel

---

## 🔄 Integração no Painel

Quando tiver múltiplos jornais coletados:

**Opção 1: JSON único agregado**
- Cada script salva em `output/{fonte}_classificado_24h.json`
- `gerar_painel_html.py` lê todos e agrega

**Opção 2: JSON consolidado**
- Criar script `consolidar_fontes.py` que:
  - Lê todos os `*_classificado_24h.json`
  - Agrega em um único JSON
  - Ordena por data/hora
  - Salva em `output/todas_fontes_24h.json`
- `gerar_painel_html.py` lê o consolidado

**Recomendação:** Opção 2 (mais organizado)

---

## 📝 Template para Novo Jornal

Ao criar `test_{fonte}_classificar_todas.py`:

1. **Copiar** `test_valor_classificar_todas.py`
2. **Ajustar:**
   - URL base
   - Seletores CSS (título, link, categoria, data/hora, resumo)
   - Lógica de paginação (se diferente)
   - Nome do arquivo de saída
3. **Manter:**
   - Estrutura de classificação
   - Filtro de 24h
   - Exclusão de Mundo
   - Formato JSON de saída

**Exemplo de estrutura mínima:**
```python
# test_estadao_classificar_todas.py
URL_BASE = "https://www.estadao.com.br/ultimas/"
# ... ajustar seletores ...
# Resto igual ao Valor
```

---

## 🎯 Checklist de Validação

Para cada novo jornal, validar:

- [ ] Coleta notícias das últimas 24h
- [ ] Extrai título corretamente
- [ ] Extrai link válido
- [ ] Extrai categoria do site
- [ ] Extrai data/hora no formato esperado
- [ ] **Extrai resumo** (importante para classificação)
- [ ] Paginação funciona (ou scroll infinito)
- [ ] Critério de parada funciona
- [ ] Classificação funciona (testar com algumas notícias)
- [ ] Exclui categoria "Mundo" do site
- [ ] JSON gerado tem formato correto
- [ ] Integra no painel HTML

---

## 📊 Estrutura de Saída (JSON)

Cada `{fonte}_classificado_24h.json` deve ter:

```json
{
  "data_coleta": "2026-02-12T14:14:45",
  "periodo_horas": 24,
  "total_coletado": 86,
  "por_tema": {
    "Fiscal": [...],
    "Mercado": [...]
  },
  "nao_classificadas": []
}
```

Cada notícia:
```json
{
  "titulo": "...",
  "resumo": "...",  // IMPORTANTE: sempre incluir
  "categoria": "...",
  "fonte": "Nome do Jornal",
  "data": "12/02/2026",
  "hora": "14:30",
  "link": "https://...",
  "tema_classificado": "Fiscal",
  "score": 2,
  "scores_todos": {...}
}
```

---

**Última atualização:** 12/02/2026
