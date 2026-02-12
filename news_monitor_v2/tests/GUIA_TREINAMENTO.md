# Guia de Treinamento do Classificador

Processo simples para você revisar e melhorar a classificação de notícias.

## Fluxo Completo

### 1. Coletar e classificar notícias
```bash
python test_valor_classificar_todas.py
```
Isso gera:
- `output/valor_classificado_24h.json` (dados completos)
- `output/valor_classificado_24h.html` (relatório visual)

### 2. Gerar HTML interativo para revisão
```bash
python gerar_html_revisao.py
```
Isso cria:
- `output/revisao_classificacao.html` ← **Abra este arquivo no navegador**

### 3. Revisar no navegador

No HTML você verá:
- **Notícias classificadas por tema** (com botões para marcar como Correta/Errada)
- **Notícias não classificadas** (para indicar qual tema deveriam ter)

**Para cada notícia:**
- Se está **correta**: deixe marcado "✓ Correta"
- Se está **errada**: marque "✗ Errada" e escolha o tema correto no dropdown
- **Opcional**: adicione um comentário explicando (ex.: "falta palavra X", "deveria pegar por Y")

### 4. Salvar feedback

Ao terminar a revisão, clique no botão **"💾 Salvar Feedback"** (canto inferior direito).

Isso baixa um arquivo `feedback_classificacao.json` para sua pasta de Downloads.

**Mova esse arquivo para:** `news_monitor_v2/tests/output/`

### 5. Processar feedback e ver sugestões

```bash
python processar_feedback.py
```

Isso gera:
- **Sugestões no console** (o que precisa ajustar)
- `output/sugestoes_keywords.txt` (relatório detalhado)

### 6. Ajustar palavras-chave

Edite `classificador/temas_keywords.json` e adicione as palavras-chave sugeridas.

### 7. Testar novamente

```bash
python test_valor_classificar_todas.py
```

Compare os resultados. Repita o processo até ficar satisfeito.

---

## Exemplo Prático

**Situação:** "Bolsa Família 2026" foi classificada como Eleições (errado)

**No HTML de revisão:**
1. Marque como "✗ Errada"
2. Escolha tema correto: "Não classificado" (ou outro tema se fizer sentido)
3. Comentário: "Bolsa Família não é sobre eleições, é programa social"

**Após processar feedback:**
- O script vai sugerir adicionar "bolsa família" como palavra-chave negativa em Eleições
- Ou criar um novo tema "Social" se houver muitas notícias assim

**Ajuste:**
- Edite `temas_keywords.json` conforme sugestões
- Rode novamente e veja se melhorou

---

## Dicas

- **Não precisa revisar todas de uma vez**: pode fazer por partes, salvar feedback múltiplas vezes
- **Comentários são importantes**: ajudam a entender o que falta nas keywords
- **Foque nas erradas primeiro**: as corretas já estão funcionando bem
- **Não classificadas são oportunidades**: podem indicar necessidade de novo tema ou palavras-chave
