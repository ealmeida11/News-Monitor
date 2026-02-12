# Classificador por tema (léxico)

Classifica notícias por tema usando palavras-chave. Os temas e as palavras vêm de **`temas_keywords.json`**.

## Como adicionar um novo tema

1. Abra **`temas_keywords.json`**.
2. Copie um bloco existente (por exemplo o de "Editorial").
3. Cole no mesmo nível dos outros e edite:

```json
  "Nome do Novo Tema": {
    "keywords": [
      "palavra1", "palavra2", "frase de três palavras"
    ],
    "ativo": true
  }
```

4. Salve o arquivo. Na próxima execução o classificador já usa o novo tema.

**Dicas:**
- Use minúsculas nas palavras (o código normaliza).
- Coloque frases inteiras quando fizer sentido (ex.: "teto de gastos").
- Se não quiser usar um tema por um tempo, use `"ativo": false`.

## Dependência opcional: spaCy (lematização)

Para melhor resultado (ex.: "gastos" e "gastou" virarem "gasto"), instale o spaCy e o modelo em português:

```bash
pip install spacy
python -m spacy download pt_core_news_sm
```

Sem o spaCy, o classificador usa só comparação de palavras (sem lematização), mas continua funcionando.

## Uso no código

```python
from classificador.lexico_classifier import classificar, listar_temas_ativos

# Classificar uma notícia (título + resumo)
resultado = classificar(
    titulo="Copom mantém Selic em 14,25% ao ano",
    resumo="Decisão foi unanimidade. Mercado esperava manutenção."
)
# resultado["tema"]   -> "Banco Central"
# resultado["score"]  -> 2
# resultado["scores"] -> {"Banco Central": 2, "Mercado": 1, ...}

# Listar temas ativos
temas = listar_temas_ativos()
```
