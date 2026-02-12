# Guia Rápido - Newsflow Macro Brasil

## 🚀 Uso Diário

### 1. Coletar Notícias do Valor
```bash
cd news_monitor_v2/tests
python test_valor_classificar_todas.py
```
**Saída:** `output/valor_classificado_24h.json`

---

### 2. Gerar Painel HTML
```bash
python gerar_painel_html.py
```
**Saída:** `output/painel_dashboard.html`  
**Abrir:** Clique duas vezes no arquivo ou arraste para o navegador

---

### 3. Reclassificar (sem coletar de novo)
Se ajustou keywords e quer reclassificar o JSON existente:
```bash
python reclassificar_json.py
```

---

## 🔧 Ajustar Classificação

### Se encontrar notícias classificadas errado:

1. **Gerar HTML de revisão:**
   ```bash
   python gerar_html_revisao.py
   ```
   Abrir `output/revisao_classificacao.html` no navegador

2. **Revisar e salvar feedback:**
   - Marque correções no HTML
   - Clique em "Salvar Feedback"
   - Salve o JSON em `output/feedback_classificacao.json`

3. **Processar feedback:**
   ```bash
   python processar_feedback.py
   ```
   Veja sugestões em `output/sugestoes_keywords.txt`

4. **Editar keywords:**
   - Abra `../classificador/temas_keywords.json`
   - Adicione/remova palavras-chave conforme sugestões

5. **Reclassificar:**
   ```bash
   python reclassificar_json.py
   ```

---

## 📁 Arquivos Importantes

| Arquivo | Descrição |
|---------|-----------|
| `test_valor_classificar_todas.py` | ⭐ Script principal de coleta |
| `gerar_painel_html.py` | ⭐ Gera painel HTML final |
| `reclassificar_json.py` | Reclassifica JSON sem coletar |
| `gerar_html_revisao.py` | Gera HTML para revisar classificação |
| `processar_feedback.py` | Processa feedback e sugere keywords |
| `../classificador/temas_keywords.json` | ⭐ **EDITAR AQUI** para ajustar classificação |

---

## 🎯 Próximo Jornal

Para adicionar Estadão/Folha/O Globo:

1. Copiar `test_valor_classificar_todas.py` → `test_{fonte}_classificar_todas.py`
2. Ajustar URL e seletores CSS
3. Testar coleta
4. Ver `../docs/PROXIMOS_PASSOS.md` para detalhes

---

**Última atualização:** 12/02/2026
