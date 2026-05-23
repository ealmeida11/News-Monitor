# Warm-up em duas fases — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar o warm-up do monitor real-time em 3 fases sequenciais por site (coletar manchetes → filtrar → baixar corpos) para deixar o log mais legível, sem mudar a janela de 8h nem o loop contínuo.

**Architecture:** Adicionar 3 helpers em `realtime/monitor.py` (`_collect_warmup_candidates`, `_filter_warmup_candidates`, `_process_warmup_bodies`) e substituir o bloco warm-up dentro de `_monitor_site`. Lógica do loop normal (`_scan_pages` / `_check_page`) permanece intocada.

**Tech Stack:** Python 3.10+, BeautifulSoup, Edge CDP (já em uso), SQLite via `SeenStore` (já em uso). Sem dependências novas.

**Spec:** `docs/superpowers/specs/2026-05-23-warmup-duas-fases-design.md`

**Notas para o executor:**
- Não há suite pytest. Validação é feita por compilação (`python -m py_compile`), import smoke (`python -c "import monitor"`) e smoke run em `--dry-run` observando logs.
- Todas as alterações ficam num único arquivo: `realtime/monitor.py`. Não tocar em mais nada.
- Há um watcher externo ("Monitor V2") que faz auto-commits periódicos no repo. Os commits manuais abaixo podem ser absorvidos por commits do watcher — não tem problema, contanto que o conteúdo do arquivo entre no histórico.

---

## File Structure

**Modificado:**
- `realtime/monitor.py` — adicionar 3 funções novas após `_build_published_at` (linha 314), modificar warm-up dentro de `_monitor_site` (linhas 222-230).

**Não modificado:** nenhum outro arquivo. Sem novos arquivos.

---

## Task 1: Helper `_collect_warmup_candidates` (Fase A)

**Files:**
- Modify: `realtime/monitor.py` (adicionar função nova logo após `_build_published_at`, antes de `_check_page` — aproximadamente após linha 314)

- [ ] **Step 1: Reler `monitor.py` antes de editar**

Run: usar a ferramenta Read em `R:\Economics\Ealmeida\Brasil\News\realtime\monitor.py` (arquivo inteiro).

Necessário para localizar com precisão o ponto de inserção e ter o conteúdo atual em contexto. O arquivo tem ~554 linhas.

- [ ] **Step 2: Adicionar função `_collect_warmup_candidates` após `_build_published_at`**

Inserir o bloco abaixo IMEDIATAMENTE antes de `def _check_page(...)`. A função usa `BeautifulSoup`, `time`, `JANELA_WARMUP` e `get_editorial_extractor`, que já estão importados no topo do módulo.

```python
def _collect_warmup_candidates(tab, site, extractor, site_log) -> list:
    """Fase A do warm-up: percorre todas as listagens e devolve candidatos crus.

    Visita home (com load-more se for o caso) + paginação URL (páginas 2-5)
    + cada editorial. Não checa dedup nem filtros — só coleta. Dedup local
    por título para não devolver a mesma manchete duas vezes entre páginas.
    Cada artigo de editorial recebe a chave interna `_editorial_author` para
    que a Fase C aplique o prefixo de coluna corretamente.
    """
    candidates = []
    seen_titles = set()
    listagens_visitadas = 0

    def _ler_listagem(url, ed_author="", ed_extractor=None, allow_load_more=False):
        """Visita uma listagem. Retorna (n_total_na_janela, n_novos_adicionados)."""
        nonlocal listagens_visitadas
        try:
            tab.navigate(url, wait_secs=2.0)
            tab.dismiss_popups()

            if allow_load_more and site.pagination_type == "button" and site.load_more_selector:
                prev_count = 0
                for _ in range(8):
                    cur_html = tab.get_html()
                    if cur_html:
                        cur_soup = BeautifulSoup(cur_html, "html.parser")
                        cur_count = (
                            len(cur_soup.select(site.headline_selector))
                            if site.headline_selector else 0
                        )
                    else:
                        cur_count = 0
                    if cur_count > 0 and cur_count == prev_count:
                        break
                    prev_count = cur_count
                    if not tab.click_selector(site.load_more_selector):
                        break
                    time.sleep(2)

            html = tab.get_html()
            if not html:
                return 0, 0
            soup = BeautifulSoup(html, "html.parser")
            fn = ed_extractor or extractor
            artigos = fn(soup, site, JANELA_WARMUP)
        except Exception as e:
            site_log.warning("  -> falha ao ler %s: %s", url[:60], e)
            return 0, 0

        listagens_visitadas += 1
        adicionados = 0
        for art in artigos:
            titulo = (art.get("titulo") or "").strip()
            link = (art.get("link") or "").strip()
            if not titulo or not link:
                continue
            if titulo in seen_titles:
                continue
            seen_titles.add(titulo)
            if ed_author:
                art["_editorial_author"] = ed_author
            candidates.append(art)
            adicionados += 1
        return len(artigos), adicionados

    # 1. Home
    total_home, _ = _ler_listagem(site.url, allow_load_more=True)
    site_log.info("  -> home (%d manchetes na janela %dmin)", total_home, JANELA_WARMUP)

    # 2. Paginação por URL (páginas 2..5)
    if site.pagination_type == "url" and site.pagination_url:
        for page in range(2, 6):
            page_url = site.pagination_url.format(page=page)
            total_p, _ = _ler_listagem(page_url)
            site_log.info("  -> pagina %d (%d na janela)", page, total_p)
            if total_p == 0:
                site_log.info("  -> paginacao encerrada (0 na janela)")
                break

    # 3. Editoriais
    for ed in site.editorial_pages:
        ed_extractor_fn = get_editorial_extractor(ed.extractor, site.name)
        total_e, _ = _ler_listagem(
            ed.url, ed_author=ed.author, ed_extractor=ed_extractor_fn,
        )
        site_log.info(
            "  -> editorial %s (%d na janela)",
            ed.author or "sem-autor", total_e,
        )

    site_log.info(
        "Coletados: %d manchetes em %d listagens",
        len(candidates), listagens_visitadas,
    )
    return candidates


```

Use a ferramenta Edit com `old_string = "def _check_page(tab, url, site, extractor, seen, send_lock, site_log,"` e `new_string` começando com o bloco acima seguido de `\n\ndef _check_page(...)`. Confira no Edit que o `old_string` é único no arquivo (deve ser — só uma definição).

Forma exata da edição:
- `old_string`: a linha `def _check_page(tab, url, site, extractor, seen, send_lock, site_log,` (apenas essa linha — confirmar unicidade)
- `new_string`: o bloco completo da função `_collect_warmup_candidates` acima + duas quebras de linha + `def _check_page(tab, url, site, extractor, seen, send_lock, site_log,`

- [ ] **Step 3: Verificar sintaxe e import**

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -m py_compile monitor.py
```

Expected: nenhum output (sucesso). Se aparecer SyntaxError, reabrir o arquivo e corrigir indentação.

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -c "from monitor import _collect_warmup_candidates; print(_collect_warmup_candidates.__doc__[:80])"
```

Expected: imprime a primeira linha do docstring (`Fase A do warm-up: percorre todas as listagens...`).

- [ ] **Step 4: Commit**

```bash
cd "R:/Economics/Ealmeida/Brasil/News" && git add realtime/monitor.py && git commit -m "feat(monitor): add _collect_warmup_candidates (warm-up Fase A)"
```

Se o watcher Monitor V2 já tiver commitado o arquivo automaticamente entre a edição e este passo, `git commit` vai dizer "nothing to commit" — nesse caso, conferir com `git log --oneline -3 realtime/monitor.py` que o conteúdo já está em algum commit recente. Tudo certo.

---

## Task 2: Helper `_filter_warmup_candidates` (Fase B)

**Files:**
- Modify: `realtime/monitor.py` (adicionar função nova imediatamente após `_collect_warmup_candidates`)

- [ ] **Step 1: Reler `monitor.py`**

Use Read em `realtime/monitor.py` para reconfirmar o estado atual após Task 1.

- [ ] **Step 2: Adicionar função `_filter_warmup_candidates`**

Inserir o bloco abaixo IMEDIATAMENTE antes de `def _check_page(...)` (depois de `_collect_warmup_candidates`, que ficou logo antes nessa mesma região).

```python
def _filter_warmup_candidates(candidates, seen, site_log) -> list:
    """Fase B do warm-up: dedup contra banco + is_excluded por URL/titulo.

    Não aplica filtro de autor — esse só roda na Fase C, depois do corpo,
    porque a maioria dos sites só revela o autor dentro do artigo.
    """
    total = len(candidates)
    apos_dedup = [c for c in candidates if seen.is_new(c["link"])]
    descartados_dedup = total - len(apos_dedup)
    site_log.info(
        "  Apos dedup banco: %d candidatas (%d ja vistas)",
        len(apos_dedup), descartados_dedup,
    )

    sobreviventes = [
        c for c in apos_dedup
        if not is_excluded(c["link"], c["titulo"])
    ]
    descartados_filtro = len(apos_dedup) - len(sobreviventes)
    site_log.info(
        "  Apos filtros (URL/titulo): %d a baixar (%d excluidas)",
        len(sobreviventes), descartados_filtro,
    )
    return sobreviventes


```

Edit:
- `old_string`: `def _check_page(tab, url, site, extractor, seen, send_lock, site_log,`
- `new_string`: bloco acima + `\n\ndef _check_page(tab, url, site, extractor, seen, send_lock, site_log,`

- [ ] **Step 3: Verificar sintaxe e teste isolado da função**

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -m py_compile monitor.py
```

Expected: nenhum output.

Teste isolado com mock simples — copiar este código exato para um arquivo temporário ou rodar em REPL:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -c "
import logging
logging.basicConfig(level='INFO', format='%(message)s')
from monitor import _filter_warmup_candidates

class _FakeSeen:
    def __init__(self, vistos): self.vistos = set(vistos)
    def is_new(self, url): return url not in self.vistos

candidates = [
    {'link': 'https://valor.globo.com/economia/noticia/1', 'titulo': 'Tesouro emite NTN-B', 'fonte': 'valor'},
    {'link': 'https://valor.globo.com/esporte/noticia/2', 'titulo': 'Flamengo vence', 'fonte': 'valor'},
    {'link': 'https://valor.globo.com/economia/noticia/3', 'titulo': 'Lula assina decreto', 'fonte': 'valor'},
]
seen = _FakeSeen(['https://valor.globo.com/economia/noticia/3'])
log = logging.getLogger('test')
result = _filter_warmup_candidates(candidates, seen, log)
print('SOBREVIVENTES:', [c['titulo'] for c in result])
assert len(result) == 1, f'esperado 1, got {len(result)}'
assert result[0]['titulo'] == 'Tesouro emite NTN-B'
print('OK')
"
```

Expected output:
```
  Apos dedup banco: 2 candidatas (1 ja vistas)
  Apos filtros (URL/titulo): 1 a baixar (1 excluidas)
SOBREVIVENTES: ['Tesouro emite NTN-B']
OK
```

(Os contadores: 3 total → 1 já visto, sobram 2 → noticia/2 cai por `/esporte/`, sobra noticia/1.)

- [ ] **Step 4: Commit**

```bash
cd "R:/Economics/Ealmeida/Brasil/News" && git add realtime/monitor.py && git commit -m "feat(monitor): add _filter_warmup_candidates (warm-up Fase B)"
```

(Mesmo comentário sobre watcher do Task 1.)

---

## Task 3: Helper `_process_warmup_bodies` (Fase C)

**Files:**
- Modify: `realtime/monitor.py` (adicionar função imediatamente após `_filter_warmup_candidates`)

- [ ] **Step 1: Reler `monitor.py`**

Use Read. Confirme que `_filter_warmup_candidates` já está no arquivo e que `def _check_page(...)` continua sendo único como ponto de ancoragem.

- [ ] **Step 2: Adicionar função `_process_warmup_bodies`**

Bloco a inserir antes de `def _check_page(...)`:

```python
def _process_warmup_bodies(tab, site, seen, send_lock, site_log,
                           articles, dry_run=False) -> tuple:
    """Fase C do warm-up: baixa corpos, aplica filtros pos-corpo, envia.

    Espelha o trecho de body-fetch + send do _check_page (loop normal),
    mas em modo batch sobre uma lista pre-filtrada.
    Retorna (enviados, descartados_pos_corpo).
    """
    total = len(articles)
    enviados = 0
    descartados_pos_corpo = 0

    for i, article in enumerate(articles, start=1):
        link = (article.get("link") or "").strip()
        titulo = (article.get("titulo") or "").strip()

        # Prefixo de editorial (mesma regra do _check_page atual)
        ed_author = article.pop("_editorial_author", "")
        if ed_author and not titulo.startswith(ed_author):
            article["titulo"] = f"{ed_author}: {titulo}"
            article["autor"] = ed_author
            titulo = article["titulo"]

        site_log.info("  %d/%d: %s", i, total, titulo[:60])

        # Navega e extrai corpo (com retry progressivo)
        try:
            tab.navigate(link, wait_secs=3.5)
            tab.dismiss_popups()
            article_html = tab.get_html()
            if article_html:
                body_info = extract_body_from_html(article_html, link)
                article["corpo"] = body_info["corpo"]
                if body_info["autor"] and not article.get("autor"):
                    article["autor"] = body_info["autor"]
                if not article.get("hora") and body_info["hora"]:
                    article["hora"] = body_info["hora"]
                if not article.get("data") and body_info["data"]:
                    article["data"] = body_info["data"]

                for wait_secs in (2.5, 3.5, 5.0):
                    if len(article.get("corpo", "")) >= 150:
                        break
                    site_log.info(
                        "    corpo curto (%d chars), aguardando %.1fs...",
                        len(article.get("corpo", "")), wait_secs,
                    )
                    time.sleep(wait_secs)
                    article_html = tab.get_html()
                    if not article_html:
                        continue
                    body_info = extract_body_from_html(article_html, link)
                    if len(body_info["corpo"]) > len(article.get("corpo", "")):
                        article["corpo"] = body_info["corpo"]
                    if body_info["autor"] and not article.get("autor"):
                        article["autor"] = body_info["autor"]
        except Exception as e:
            site_log.warning("    erro ao buscar corpo: %s", e)
            article["corpo"] = ""

        pub_at = _build_published_at(article)

        # Filtro autor pos-corpo (mesma chamada do _check_page atual)
        if is_excluded(link, article["titulo"], article.get("autor", "")):
            seen.mark_seen(
                link, article["titulo"], article["fonte"],
                article.get("corpo", ""), pub_at,
            )
            site_log.info("    -> excluido (autor: %s)", article.get("autor", "—"))
            descartados_pos_corpo += 1
            continue

        # Janela temporal pos-corpo
        art_data = article.get("data") or ""
        art_hora = article.get("hora") or ""
        if art_data and art_hora:
            if not _dentro_janela(art_data, art_hora, JANELA_WARMUP):
                seen.mark_seen(
                    link, article["titulo"], article["fonte"],
                    article.get("corpo", ""), pub_at,
                )
                site_log.info("    -> fora da janela: %s %s", art_data, art_hora)
                descartados_pos_corpo += 1
                continue
        elif not art_data:
            # Sem data no warm-up: skip + mark seen (mesmo do _check_page atual)
            seen.mark_seen(
                link, article["titulo"], article["fonte"],
                article.get("corpo", ""), pub_at,
            )
            site_log.info("    -> sem data, pulando")
            descartados_pos_corpo += 1
            continue

        # Formata e envia
        msg = format_article(article)
        with send_lock:
            sent_ok = _send_whatsapp(msg, dry_run=dry_run)

        seen.mark_seen(
            link, article["titulo"], article["fonte"],
            article.get("corpo", ""), pub_at,
        )
        if sent_ok:
            seen.mark_sent(link)
            site_log.info("    -> ENVIADO")
            enviados += 1
        else:
            site_log.error("    -> FALHA NO ENVIO (marcado como visto)")

    return enviados, descartados_pos_corpo


```

Edit:
- `old_string`: `def _check_page(tab, url, site, extractor, seen, send_lock, site_log,`
- `new_string`: bloco acima + `\n\ndef _check_page(tab, url, site, extractor, seen, send_lock, site_log,`

- [ ] **Step 3: Verificar sintaxe e import**

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -m py_compile monitor.py
```

Expected: sem output.

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -c "from monitor import _collect_warmup_candidates, _filter_warmup_candidates, _process_warmup_bodies; print('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
cd "R:/Economics/Ealmeida/Brasil/News" && git add realtime/monitor.py && git commit -m "feat(monitor): add _process_warmup_bodies (warm-up Fase C)"
```

---

## Task 4: Wire-up no `_monitor_site`

**Files:**
- Modify: `realtime/monitor.py` linhas ~222-230 (bloco warm-up dentro de `_monitor_site`)

- [ ] **Step 1: Reler `monitor.py`**

Use Read para confirmar as linhas exatas do bloco warm-up atual. No estado original (antes de qualquer edit), o bloco é:

```python
    # ── Warm-up: enviar artigos novos das últimas 8h ──
    site_log.info("Warm-up: verificando últimos %d min...", JANELA_WARMUP)
    try:
        _scan_pages(tab, site, extractor, seen, send_lock, site_log,
                    minutos=JANELA_WARMUP, dry_run=dry_run)
        site_log.info("Warm-up concluído")
    except Exception:
        site_log.exception("Warm-up falhou — seguindo direto pro loop")
```

- [ ] **Step 2: Substituir o bloco warm-up**

Edit:
- `old_string`:
```
    # ── Warm-up: enviar artigos novos das últimas 8h ──
    site_log.info("Warm-up: verificando últimos %d min...", JANELA_WARMUP)
    try:
        _scan_pages(tab, site, extractor, seen, send_lock, site_log,
                    minutos=JANELA_WARMUP, dry_run=dry_run)
        site_log.info("Warm-up concluído")
    except Exception:
        site_log.exception("Warm-up falhou — seguindo direto pro loop")
```

- `new_string`:
```
    # ── Warm-up: 3 fases (coletar → filtrar → baixar corpos) ──
    site_log.info("Warm-up: coletando manchetes em listagens (janela %d min)...", JANELA_WARMUP)
    t0 = time.time()
    try:
        candidates = _collect_warmup_candidates(tab, site, extractor, site_log)
        survivors = _filter_warmup_candidates(candidates, seen, site_log)
        if survivors:
            site_log.info("Baixando corpos: %d artigos...", len(survivors))
            enviados, descartados = _process_warmup_bodies(
                tab, site, seen, send_lock, site_log, survivors, dry_run=dry_run,
            )
            elapsed = time.time() - t0
            site_log.info(
                "Warm-up concluido: %d enviados, %d filtrados pos-corpo em %.0fs",
                enviados, descartados, elapsed,
            )
        else:
            elapsed = time.time() - t0
            site_log.info("Warm-up concluido: nada a enviar em %.0fs", elapsed)
    except Exception:
        site_log.exception("Warm-up falhou — seguindo direto pro loop")
```

(Atenção: preservar exatamente a indentação de 4 espaços do bloco original — ele está dentro da função `_monitor_site`.)

- [ ] **Step 3: Verificar sintaxe + import + assinatura de `_monitor_site` intacta**

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -m py_compile monitor.py
```

Expected: sem output.

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -c "
import inspect
from monitor import _monitor_site, _scan_pages, _check_page
sig = inspect.signature(_monitor_site)
print('_monitor_site signature:', sig)
assert list(sig.parameters) == ['tab', 'site', 'seen', 'send_lock', 'dry_run'], sig.parameters
print('OK')
"
```

Expected:
```
_monitor_site signature: (tab, site, seen, send_lock, dry_run=False)
OK
```

(Confere que não quebramos a chamada feita dentro de `run()` e do supervisor.)

- [ ] **Step 4: Confirmar que `_scan_pages` e `_check_page` ainda existem (loop continuo intacto)**

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -c "
from monitor import _scan_pages, _check_page
print('_scan_pages:', _scan_pages.__name__)
print('_check_page:', _check_page.__name__)
print('OK')
"
```

Expected:
```
_scan_pages: _scan_pages
_check_page: _check_page
OK
```

- [ ] **Step 5: Commit**

```bash
cd "R:/Economics/Ealmeida/Brasil/News" && git add realtime/monitor.py && git commit -m "feat(monitor): wire warm-up 3-phase flow in _monitor_site"
```

---

## Task 5: Smoke test em dry-run com banco preenchido

Objetivo: confirmar que o warm-up roda end-to-end sem exceções, com log ordenado (Fase A → B → C), e que o loop contínuo entra em seguida.

**Files:** nenhum. Só execução + observação.

- [ ] **Step 1: Garantir que o servidor WhatsApp está rodando (não é estritamente necessário em dry-run, mas evita ruído de retry)**

Em outro terminal, se ainda não estiver rodando:
```bash
scripts\run_whatsapp.bat
```

Esperar até ver "WhatsApp client ready" ou equivalente.

- [ ] **Step 2: Conferir que `seen.db` tem registros (não vamos apagar — queremos o caminho "banco preenchido")**

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python -c "
from storage.seen import SeenStore
from config.settings import DB_PATH
s = SeenStore(DB_PATH)
print('count:', s.count())
s.close()
"
```

Expected: número positivo (típico: alguns milhares). Se for 0, ainda dá pra rodar o smoke — só que a Fase B vai mostrar tudo como "novas".

- [ ] **Step 3: Rodar o monitor em dry-run por ~5 minutos**

Run em foreground (em outro terminal, ou aceitar bloqueio):
```bash
cd "R:/Economics/Ealmeida/Brasil/News/realtime" && python monitor.py --dry-run
```

Deixar correr até cada uma das 6 threads ter logado "Warm-up concluido" (varia de 30s a 2min por site dependendo da quantidade de candidatos). Depois esperar pelo menos 1 ciclo do loop normal (`Ciclo #1`).

Para parar: `Ctrl+C`. O `_signal_handler` deve cuidar do shutdown gracioso.

- [ ] **Step 4: Verificar o log**

Abrir `realtime/logs/monitor_YYYYMMDD.log` (data do dia da execução). Conferir, **por cada site**, que aparece nesta ordem:

1. `Warm-up: coletando manchetes em listagens (janela 480 min)...`
2. `-> home (N manchetes na janela 480min)`
3. (Opcional) `-> pagina K (N na janela)` para sites com `pagination_type=url`
4. (Opcional) `-> editorial NOME (N na janela)` para sites com editoriais
5. `Coletados: X manchetes em K listagens`
6. `Apos dedup banco: Y candidatas (Z ja vistas)`
7. `Apos filtros (URL/titulo): W a baixar (V excluidas)`
8. Se `W > 0`: `Baixando corpos: W artigos...` seguido de linhas `i/N: titulo... -> ENVIADO|excluido|FALHA NO ENVIO`
9. `Warm-up concluido: A enviados, B filtrados pos-corpo em Cs` (ou `nada a enviar em Cs`)

E depois disso (no loop), aparecem `Ciclo #1: ...` no estilo antigo (loop NÃO mudou).

Run para confirmar visualmente:
```bash
cd "R:/Economics/Ealmeida/Brasil/News" && python -c "
import re, pathlib, datetime
hoje = datetime.datetime.now().strftime('%Y%m%d')
log_file = pathlib.Path('realtime/logs') / f'monitor_{hoje}.log'
texto = log_file.read_text(encoding='utf-8', errors='replace')
sites = ['valor', 'folha', 'estadao', 'cnn', 'oglobo', 'metropoles']
for s in sites:
    linhas = [L for L in texto.splitlines() if f'monitor.{s}' in L]
    tags = [
        'Warm-up: coletando',
        'Coletados:',
        'Apos dedup banco',
        'Apos filtros',
        'Warm-up concluido',
    ]
    achadas = [t for t in tags if any(t in L for L in linhas)]
    print(f'{s}: {len(achadas)}/{len(tags)} marcos -> {achadas}')
"
```

Expected: cada site mostra 5/5 marcos (`Warm-up: coletando`, `Coletados:`, `Apos dedup banco`, `Apos filtros`, `Warm-up concluido`).

Se algum site mostrar < 5: olhar o log bruto para entender se foi exceção no warm-up (vai aparecer `Warm-up falhou` com traceback) — nesse caso voltar pro código.

- [ ] **Step 5: Validar visualmente o ordering**

Run:
```bash
cd "R:/Economics/Ealmeida/Brasil/News" && python -c "
import datetime, pathlib
hoje = datetime.datetime.now().strftime('%Y%m%d')
texto = (pathlib.Path('realtime/logs') / f'monitor_{hoje}.log').read_text(encoding='utf-8', errors='replace')
# pega só linhas de 1 site (valor) ate ciclo #1
recorte = []
for L in texto.splitlines():
    if 'monitor.valor' not in L: continue
    recorte.append(L)
    if 'Ciclo #1' in L: break
print('\n'.join(recorte))
"
```

Expected: ordem Warm-up: coletando → -> home → (paginas/editoriais) → Coletados: → Apos dedup → Apos filtros → (Baixando corpos + i/N: …) → Warm-up concluido → Ciclo #1. NUNCA "Buscando corpo" antes de "Apos filtros".

- [ ] **Step 6: Commit (caso o watcher não tenha)**

```bash
cd "R:/Economics/Ealmeida/Brasil/News" && git status
```

Se houver alteração não-committada em `realtime/monitor.py` (não deve, porque Task 4 já commitou), commitar com `git commit -m "chore: smoke test warm-up 3-phase flow"`. Caso contrário, nada a fazer.

---

## Task 6 (opcional): Cleanup pós-smoke

Só executar se o Step 4 da Task 5 acusou algo de fora do padrão (ex: log poluído, falta de espaçamento, contadores errados). Caso contrário, plano encerrado.

**Files:**
- Modify: `realtime/monitor.py` (ajustes pontuais)

- [ ] **Step 1: Listar discrepâncias observadas**

Anotar como bullets do que precisa ajustar (ex: "log da Fase B sem espaço no início", "contador de descartados em editoriais somando errado").

- [ ] **Step 2: Aplicar correções**

Edit pontual em `realtime/monitor.py`. Manter a abrangência mínima.

- [ ] **Step 3: Re-rodar smoke**

Repetir Steps 3-5 da Task 5.

- [ ] **Step 4: Commit**

```bash
cd "R:/Economics/Ealmeida/Brasil/News" && git add realtime/monitor.py && git commit -m "fix(monitor): polish warm-up 3-phase logs"
```

---

## Pontos de atenção / pitfalls

- **Encoding do log:** os helpers usam ASCII (`->`, `Apos`, `concluido`) de propósito, evitando acentos. Isso protege contra o `_SafeStreamHandler` que existe pra contornar OSError em consoles Windows com 6 threads concorrentes. Não trocar para `→` ou acentos sem testar primeiro.
- **Dedup local por título na Fase A** usa `seen_titles` (set local, vive só durante a coleta de UM site). Não confundir com `seen.is_new` que vai contra o banco SQLite.
- **`article.pop("_editorial_author", "")` na Fase C consome a chave** — chamar 2 vezes só dá string vazia na segunda. Está correto porque cada artigo só passa uma vez no loop.
- **Indentação:** as 3 funções novas ficam em top-level (sem indent). O bloco substituído na Task 4 fica dentro de `_monitor_site`, com indent de 4 espaços.
- **Watcher auto-commit:** se um commit manual falhar com "nothing to commit", checar `git log --oneline -3 realtime/monitor.py` — provavelmente o watcher já gravou. Sem problema.
