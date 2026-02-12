# Como rodar o Monitor V2 (produção)

## Script principal: `run_coleta.py`

- Coleta as **5 fontes** (Valor, Estadão, Folha, O Globo, CNN Brasil) com os scripts em `tests/test_*_classificar_todas.py`.
- Grava apenas **notícias novas** no banco `noticias_v2.db` (deduplicação por **link** nos últimos 7 dias).
- Gera **painel_dashboard.html** em `tests/output/` e **index.html** na raiz do projeto (para GitHub Pages).

### Uma execução (manual)

Na **raiz do projeto** (pasta `News`):

```bat
set PYTHONPATH=%CD%;%CD%\news_monitor_v2
python news_monitor_v2/run_coleta.py
```

Ou, dentro de `news_monitor_v2`:

```bat
set PYTHONPATH=..;%CD%
python run_coleta.py
```

### Loop automático + GitHub

Na raiz do projeto, execute:

```bat
app_auto_loop_v2.bat
```

- Roda a coleta a cada **30 minutos**.
- Após cada execução: `git add index.html`, `git commit`, `git push origin main`.
- Acesso ao painel: **https://ealmeida11.github.io/Brasil-News/** (index.html).

O banco `noticias_v2.db` fica apenas local (não é enviado ao GitHub).

## Estrutura

- **database/db.py** – SQLite: `init_db`, `get_links_existentes`, `insert_noticia`, `get_noticias_ultimas_24h`.
- **run_coleta.py** – Orquestra: chama os 5 testes, lê os JSONs, insere no DB, gera painel e index.
- **tests/gerar_painel_html.py** – `gerar_painel_de_lista()` gera o HTML a partir de uma lista (ex.: do DB).
