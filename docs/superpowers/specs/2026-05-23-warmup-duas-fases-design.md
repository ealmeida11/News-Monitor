# Warm-up em duas fases — design

**Data:** 2026-05-23
**Autor:** ealmeida11 (via Claude)
**Status:** aprovado, pendente de plano de implementação
**Arquivo principal afetado:** `realtime/monitor.py`

## Contexto

O monitor real-time (`realtime/monitor.py`) inicia 6 threads (uma por site) que rodam um warm-up de 8h antes de cair no loop contínuo. Hoje o warm-up está **intercalado**:

1. Visita uma página de listagem.
2. Para cada manchete encontrada na janela: checa dedup (`seen.is_new`) e filtros básicos (`is_excluded` por URL/título).
3. Se passou, navega imediatamente para a página do artigo, baixa o corpo, aplica filtro de autor, envia WhatsApp e marca seen+sent.
4. Volta para a listagem, vai para a próxima manchete.
5. Após esgotar a listagem, vai para a próxima página de paginação, e depois para cada editorial.

O log fica difícil de ler: cada manchete tem entradas misturadas de "→ Buscando corpo" + "ENVIADO" + "Excluído" + erros de retry, sem visão consolidada de "quantas manchetes esse site tem na janela 8h, quantas são novas, quantas vão ser enviadas".

## Objetivo

Reorganizar **apenas o warm-up** em três fases sequenciais por site, para que o log mostre claramente:

```
[monitor.valor] Warm-up: coletando manchetes em listagens...
[monitor.valor]   → home (48 manchetes na janela 8h)
[monitor.valor]   → página 2 (32 na janela)
[monitor.valor]   → página 3 (5 na janela)
[monitor.valor]   → página 4 (0 na janela) — paginação encerrada
[monitor.valor] Coletados: 85 manchetes em 3 listagens
[monitor.valor]   Após dedup banco: 12 candidatas (73 já vistas)
[monitor.valor]   Após filtros (URL/título): 9 a baixar (3 excluídas)
[monitor.valor] Baixando corpos: 9 artigos...
[monitor.valor]   1/9: Tesouro emite NTN-B... → ENVIADO
[monitor.valor]   2/9: Lula assina decreto... → ENVIADO
[monitor.valor]   ...
[monitor.valor] Warm-up concluído: 8 enviados, 1 filtrado pós-corpo (autor) em 73s
```

**Não-objetivos:**

- Não muda o loop contínuo (`JANELA_NORMAL=20`). Segue intercalado, igual hoje.
- Não muda a janela (`JANELA_WARMUP=480` permanece 8h).
- Não muda nenhum dos parsers de manchete (`extract_valor`, `extract_folha`, etc.).
- Não muda lógica de dedup, filtros, retry de WhatsApp, retry de corpo curto, marca seen+sent, normalização de URL, threading.

## Design

### Visão geral

Substituir o trecho de warm-up dentro de `_monitor_site` (hoje uma única chamada a `_scan_pages(minutos=480)`) por três funções novas chamadas em sequência:

```
_collect_warmup_candidates(tab, site, extractor, site_log)
        ↓ retorna list[dict]
_filter_warmup_candidates(candidates, seen, site_log)
        ↓ retorna list[dict] filtrada (e loga resumo)
_process_warmup_bodies(tab, site, seen, send_lock, site_log, articles, dry_run)
        ↓ executa downloads sequenciais + envios
```

Cada site executa esse fluxo na sua própria thread, em paralelo aos outros 5 sites (igual hoje). O `send_lock` continua serializando os envios WhatsApp entre threads.

### Fase A — `_collect_warmup_candidates`

**Responsabilidade:** percorrer todas as listagens (home + paginação + editoriais) de um site, extrair manchetes na janela 8h, retornar uma lista única de candidatos sem corpo.

**Assinatura:**

```python
def _collect_warmup_candidates(tab, site, extractor, site_log) -> list[dict]:
    """Fase A do warm-up: visita listagens e devolve candidatos crus.

    Não checa dedup nem filtros — só coleta. Dedup local por título
    (mesma regra do _check_page atual) para não retornar a mesma
    manchete duas vezes entre páginas de paginação.

    Cada item do retorno é o dict que vem de extractor(soup, site, minutos),
    enriquecido com a chave 'editorial_author' (vazia se não vier de editorial)
    para que a Fase C aplique o prefixo de coluna corretamente.
    """
```

**Comportamento:**

1. **Home (`site.url`):**
   - Mesma lógica de `_check_page` atual: `tab.navigate(url, wait_secs=2.0)` + `dismiss_popups()`.
   - Se `site.pagination_type == "button"` e `site.load_more_selector`: clicar load-more até 8 vezes (mantém o `max_load_more_clicks=8` que o warm-up usa hoje).
   - `extractor(soup, site, minutos=480)` → lista.
   - Logar: `→ home (N manchetes na janela 8h)`.

2. **Paginação por URL:**
   - Só se `site.pagination_type == "url"` e `site.pagination_url`.
   - `max_pages = 5` (mesmo do warm-up atual).
   - Para cada página `2..max_pages`:
     - `tab.navigate(page_url, wait_secs=2.0)` + `dismiss_popups()`.
     - `extractor(soup, site, minutos=480)` → lista.
     - Logar: `→ página K (N na janela)`.
     - **Stop condition:** se a página devolver **0** manchetes na janela, parar e logar `paginação encerrada`. Equivalente ao critério atual.

3. **Editoriais:**
   - Para cada `ed in site.editorial_pages`:
     - `ed_extractor = get_editorial_extractor(ed.extractor, site.name)`
     - `tab.navigate(ed.url, wait_secs=2.0)` + `dismiss_popups()`.
     - `ed_extractor(soup, site, minutos=480)` → lista.
     - Marcar cada artigo com `article["_editorial_author"] = ed.author` (chave interna, prefixo de underline).
     - Logar: `→ editorial {ed.author or 'sem-autor'} (N na janela)`.

4. **Dedup local por título:** acumular num `seen_titles: set[str]` global ao warm-up; pular títulos repetidos entre páginas/editoriais. (Hoje o dedup local existe dentro de `_check_page`, então a mesma manchete pode aparecer de novo em outra página — comportamento idêntico ao atual nesse aspecto.)

5. **Resumo final:** logar `Coletados: X manchetes em N listagens` (N = home + páginas paginadas visitadas + nº de editoriais).

**Tratamento de erro:** se `tab.navigate` ou `tab.get_html` falhar em alguma listagem, logar warning e continuar com as outras (mesmo padrão de hoje).

### Fase B — `_filter_warmup_candidates`

**Responsabilidade:** aplicar dedup contra o banco e filtros baseados em URL+título; produzir a lista que vai pra Fase C.

**Assinatura:**

```python
def _filter_warmup_candidates(candidates, seen, site_log) -> list[dict]:
    """Fase B: dedup banco + is_excluded por URL/título. Loga resumo."""
```

**Comportamento:**

1. Recebe a lista de candidatos da Fase A.
2. Passo 1 — **dedup banco:** filtra `seen.is_new(link)`. Loga `Após dedup banco: X candidatas (Y já vistas)`.
3. Passo 2 — **filtros pré-corpo:** filtra `is_excluded(link, titulo)` (sem autor, igual ao primeiro check do `_check_page` atual). Loga `Após filtros (URL/título): X a baixar (Y excluídas)`.
4. Retorna a lista resultante (potencialmente vazia).

**Nota:** o filtro de autor (`_AUTORES_EXCLUIDOS`) **não** é aplicado aqui, porque a maioria dos sites só revela o autor no corpo do artigo. Continua sendo aplicado na Fase C.

### Fase C — `_process_warmup_bodies`

**Responsabilidade:** para cada artigo sobrevivente, navegar, baixar corpo, aplicar filtro de autor + janela temporal, formatar e enviar WhatsApp, marcar seen+sent.

**Assinatura:**

```python
def _process_warmup_bodies(tab, site, seen, send_lock, site_log,
                           articles, dry_run=False) -> tuple[int, int]:
    """Fase C: baixa corpos sequencialmente, envia, marca.

    Retorna (enviados, descartados_pos_corpo).
    """
```

**Comportamento:** copiar **byte por byte** o bloco interno do loop de `_check_page` atual (linhas ~383-455), com pequenas adaptações:

1. Para cada `(i, article)` em `enumerate(articles, start=1)`:
   - Aplicar prefixo de editorial usando a mesma regra do código atual (linhas 379-381 do monitor): se `editorial_author = article.pop("_editorial_author", "")` for não-vazio **e** o título atual ainda não começar com esse autor, sobrescrever `article["titulo"] = f"{editorial_author}: {titulo}"` e `article["autor"] = editorial_author`. (No código atual, `autor` é sempre sobrescrito quando a condição do `if` é satisfeita.)
   - Navegar para `link`, `wait_secs=3.5`, `dismiss_popups()`.
   - Extrair corpo via `extract_body_from_html`.
   - Retry progressivo para corpo curto (mesmos sleeps `(2.5, 3.5, 5.0)` e mesmo threshold 150 chars).
   - Calcular `pub_at` via `_build_published_at`.
   - **Filtro autor pós-corpo:** `is_excluded(link, titulo, autor)`. Se excluir, `seen.mark_seen(...)` + log `Excluído (autor: ...)` + `continue` (incrementa contador de descartados).
   - **Janela temporal pós-corpo:** mesmo `_dentro_janela(art_data, art_hora, 480)` e fallback "sem data no warm-up → mark_seen + skip" do código atual.
   - Formatar via `format_article` e enviar `_send_whatsapp(msg, dry_run=dry_run)` com `send_lock`.
   - `seen.mark_seen(...)` sempre; `seen.mark_sent(...)` só se enviou.
   - Logar `{i}/{N}: {titulo[:60]}... → ENVIADO` ou `→ FALHA WHATSAPP`.
2. Retornar `(enviados, descartados_pos_corpo)`.

**Concorrência:** continua thread-safe — `seen` já tem lock interno, `send_lock` serializa WhatsApp, e cada thread tem sua própria `tab`.

### Mudança em `_monitor_site`

O bloco warm-up atual (linhas 222-230):

```python
site_log.info("Warm-up: verificando últimos %d min...", JANELA_WARMUP)
try:
    _scan_pages(tab, site, extractor, seen, send_lock, site_log,
                minutos=JANELA_WARMUP, dry_run=dry_run)
    site_log.info("Warm-up concluído")
except Exception:
    site_log.exception("Warm-up falhou — seguindo direto pro loop")
```

vira:

```python
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
            "Warm-up concluído: %d enviados, %d filtrados pós-corpo em %.0fs",
            enviados, descartados, elapsed,
        )
    else:
        elapsed = time.time() - t0
        site_log.info("Warm-up concluído: nada a enviar em %.0fs", elapsed)
except Exception:
    site_log.exception("Warm-up falhou — seguindo direto pro loop")
```

### Funções **não** modificadas

- `_scan_pages` — segue como está; usado pelo loop contínuo apenas.
- `_check_page` — segue como está; usado por `_scan_pages` apenas.
- `_build_published_at`, `_send_whatsapp`, `_save_obsidian`, `_setup_logging`, `_within_operating_hours` — intactos.
- Qualquer arquivo fora de `monitor.py`.

## Trade-offs

| Aspecto | Antes | Depois |
|---|---|---|
| Log | Intercalado, difícil ler quantas manchetes existem antes do filtro | Resumo claro por fase |
| Memória | ~1 dict por iteração | ~50-200 dicts segurados durante warm-up por site (≤6×200 = 1200 dicts no total na RAM) |
| Tempo total | Listagens e corpos misturados | Listagens primeiro (rápido), corpos depois. Tempo agregado equivalente — sem ganho de performance |
| Race com outras threads | Cada thread só checa seu próprio `seen.is_new` | Idem. Sem regressão |
| Stop de paginação | Para quando "novos sent == 0" (inclui duplicados que já estavam no banco) | Para quando "manchetes na janela == 0" (só conta o que o extractor devolveu). Em restart, isso pode visitar mais páginas do que hoje: ex.: se páginas 2-5 estão cheias de manchetes em janela mas todas duplicadas, hoje pára na 2, novo flow visita todas. Custo: ~2-4 navegações extras por site no warm-up (~5-10s a mais por site) |

## Riscos

1. **Janela de paginação:** se um site tiver paginação não-cronológica (ex: editoriais misturados), o stop "0 na janela" poderia parar cedo. Verificação: os 6 sites têm paginação cronológica nas listagens (Valor, Folha, Estadão, CNN, Globo, Metrópoles), então o risco é teórico.
2. **Erro no meio da coleta:** se `tab.navigate` numa página intermediária falhar, a função segue para a próxima — pode perder candidatos daquela página. Mesmo comportamento do código atual (que já loga warning e continua).
3. **Memória se warm-up engasgar:** se um site tiver 500+ manchetes na janela (improvável — 8h costuma render 50-100), a lista cresce, mas dicts de manchete são leves (~200 bytes cada). Mesmo no pior caso, ~100KB por site.

## Plano de testes

Como não há suite de testes formal para `monitor.py`, validação será:

1. **Smoke test em dry-run:** `python monitor.py --dry-run` por ~5 minutos. Verificar:
   - Cada site loga "Warm-up: coletando..." → "Coletados: X" → "Após dedup..." → "Após filtros..." → "Baixando corpos..." → "Warm-up concluído".
   - Ordem das fases é respeitada (sem entradas "Buscando corpo" antes de "Após filtros").
   - Nenhuma exceção não tratada.
2. **Smoke test em produção (sem dry-run) com banco vazio:** apagar `realtime/database/seen.db`, rodar `python monitor.py`, deixar warm-up completar. Verificar que mensagens chegam no WhatsApp e o resumo final bate (`X enviados` = mensagens recebidas).
3. **Smoke test com banco preenchido:** rodar imediatamente depois do (2). Esperar `Após dedup banco: 0 candidatas (X já vistas)` em todos os sites — warm-up termina sem baixar nenhum corpo.
4. **Loop contínuo intacto:** após o warm-up, observar 2-3 ciclos do loop. Logs do loop devem seguir o formato atual (`Ciclo #N: ... em X.Xs`).

## Arquivos tocados

- `realtime/monitor.py` — adicionar três funções novas, modificar warm-up em `_monitor_site`.

Nenhum outro arquivo. Nenhum schema de banco, nenhuma dependência nova, nenhum config a alterar.
