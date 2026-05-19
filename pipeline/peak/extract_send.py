# -*- coding: utf-8 -*-
"""
Fase 3 do peak Brasil: lê selecionados da selection.json, busca corpos no DB,
chama claude -p batch pra resumos PT-BR, envia WhatsApp digest + bodies starred limpos.

DB-only: o pipeline diário das 06:00 já popula articles.full_text. Se algum
item não tiver body no DB, o prompt do claude resume direto do título (fallback
já no prompt). Sem fetch via CDP.

Fluxo:
  1. Lê selection.json (items added=true, ordenados por position)
  2. SELECT full_text/summary do DB via headline_id
  3. 1 batch claude -p → resumos PT-BR
  4. TinyURL pra cada URL
  5. Monta digest + envia WhatsApp
  6. Pra starred: 1 batch claude -p limpando bodies → envia 1 msg por starred
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import sqlite3
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from peak.config import (
    DATA_DIR, DB_PATH, SELECTION_JSON, SOURCE_LABELS,
    WHATSAPP_HEADER_TEMPLATE, TINYURL_API, COLUNISTAS_TAB_ID,
    PEAK_WHATSAPP_RECIPIENTS, OBSIDIAN_INBOX_DIR, OBSIDIAN_COUNTRY_TAG,
)

log = logging.getLogger(__name__)

_WHATSAPP_SERVER_URL = "http://localhost:3001"
_SEND_TIMEOUT_SECONDS = 600
_RETRY_INTERVAL_SECONDS = 30
_INTER_MESSAGE_DELAY = 1.5

_BATCH_BODY_TRUNCATE_CHARS = 2500
_BATCH_TIMEOUT_SECONDS = 300
_CLEAN_BODY_MAX_CHARS = 8000
_CLEAN_BODY_TIMEOUT_SECONDS = 360
_CLAUDE_MAX_ATTEMPTS = 3
_CLAUDE_RETRY_BACKOFF = [5, 10]


# ---------------------------------------------------------------------------
# claude -p helpers (subprocess + retry)
# ---------------------------------------------------------------------------

def _find_claude_cli() -> str | None:
    for name in ("claude", "claude.cmd", "claude.exe"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _run_claude_with_retry(claude_path: str, prompt: str, timeout: int, label: str) -> str:
    """Roda claude -p com prompt via stdin, retry até _CLAUDE_MAX_ATTEMPTS."""
    last_error = None
    for attempt in range(1, _CLAUDE_MAX_ATTEMPTS + 1):
        try:
            result = subprocess.run(
                [claude_path, "-p"],
                input=prompt, capture_output=True, text=True, encoding="utf-8",
                timeout=timeout, check=False,
            )
        except subprocess.TimeoutExpired:
            last_error = f"timeout após {timeout}s"
            log.warning("[%s] tentativa %d/%d: %s", label, attempt, _CLAUDE_MAX_ATTEMPTS, last_error)
        except FileNotFoundError:
            log.error("[%s] claude CLI não encontrado — sem retry", label)
            return ""
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            log.warning("[%s] tentativa %d/%d: %s", label, attempt, _CLAUDE_MAX_ATTEMPTS, last_error)
        else:
            if result.returncode == 0 and (result.stdout or "").strip():
                if attempt > 1:
                    log.info("[%s] sucesso na tentativa %d", label, attempt)
                return result.stdout
            last_error = (
                f"exit={result.returncode} stderr={(result.stderr or '')[:200]!r}"
                if result.returncode != 0 else "stdout vazio"
            )
            log.warning("[%s] tentativa %d/%d: %s", label, attempt, _CLAUDE_MAX_ATTEMPTS, last_error)

        if attempt < _CLAUDE_MAX_ATTEMPTS:
            wait = _CLAUDE_RETRY_BACKOFF[min(attempt - 1, len(_CLAUDE_RETRY_BACKOFF) - 1)]
            log.info("[%s] aguardando %ds antes da próxima tentativa...", label, wait)
            time.sleep(wait)

    log.error("[%s] esgotadas %d tentativas (último erro: %s)", label, _CLAUDE_MAX_ATTEMPTS, last_error)
    return ""


# ---------------------------------------------------------------------------
# Summary batch — PT-BR
# ---------------------------------------------------------------------------

def _build_summary_prompt(articles: list[dict]) -> str:
    items = []
    for i, art in enumerate(articles, start=1):
        title = (art.get("title") or "").strip()
        body = (art.get("full_text") or "").strip()
        if len(body) > _BATCH_BODY_TRUNCATE_CHARS:
            body = body[:_BATCH_BODY_TRUNCATE_CHARS] + "…"
        if not body:
            body = "(sem corpo — resuma a partir do título)"
        items.append(f"[{i}] Título: {title}\n\nCorpo:\n{body}")
    block = "\n\n----\n\n".join(items)
    n = len(articles)
    return f"""Você é um analista macro de um fundo de investimento global, especializado em Brasil.

Vou te passar {n} artigos sobre Brasil (política, fiscal, BCB, atividade, mercado). Para CADA um, escreva um resumo em PORTUGUÊS BRASILEIRO com EXATAMENTE 2 linhas (máximo 25 palavras cada).

Regras por resumo:
- Linha 1: o fato-chave (o que aconteceu, quem decidiu, qual número)
- Linha 2: consequência ou contexto relevante
- Factual, objetivo, sem opinião
- Não comece com o nome do jornal/fonte
- Sem "segundo apurou" ou "fontes afirmam"
- Inclua números relevantes (%, BPS, R$, US$)
- Se o corpo estiver vazio, resuma a partir do título

Formato de saída — comece IMEDIATAMENTE com ###1### usando exatamente este formato:

###1###
<linha 1>
<linha 2>

###2###
<linha 1>
<linha 2>

(continue pra todos os {n} artigos; o último é ###{n}###)

Sem preâmbulo. Sem markdown. Sem comentários extras.

Artigos:

{block}
"""


def _parse_batch_summaries(output: str, n: int) -> list[str]:
    summaries: list[str] = [""] * n
    parts = re.split(r"###\s*(\d+)\s*###", output)
    for i in range(1, len(parts) - 1, 2):
        try:
            idx = int(parts[i].strip())
        except ValueError:
            continue
        content = parts[i + 1].strip()
        clean = [ln.rstrip() for ln in content.split("\n") if ln.strip()]
        if 1 <= idx <= n:
            if len(clean) >= 2:
                summaries[idx - 1] = clean[0] + "\n" + clean[1]
            elif clean:
                summaries[idx - 1] = clean[0]
    return summaries


def _summarize_batch(articles: list[dict], claude_path: str) -> list[str]:
    if not articles:
        return []
    prompt = _build_summary_prompt(articles)
    log.info("claude -p summary batch: %d artigos, prompt %d chars", len(articles), len(prompt))
    output = _run_claude_with_retry(claude_path, prompt, _BATCH_TIMEOUT_SECONDS, "summary-batch")
    if not output:
        return [""] * len(articles)
    summaries = _parse_batch_summaries(output, len(articles))
    log.info("claude -p summary batch: %d/%d resumos parseados",
             sum(1 for s in summaries if s), len(articles))
    return summaries


# ---------------------------------------------------------------------------
# Body cleanup batch — PT-BR
# ---------------------------------------------------------------------------

def _parse_batch_blocks(output: str, n: int) -> list[str]:
    blocks: list[str] = [""] * n
    parts = re.split(r"###\s*(\d+)\s*###", output)
    for i in range(1, len(parts) - 1, 2):
        try:
            idx = int(parts[i].strip())
        except ValueError:
            continue
        if 1 <= idx <= n:
            blocks[idx - 1] = parts[i + 1].strip()
    return blocks


def _build_clean_body_prompt(articles: list[dict]) -> str:
    items = []
    for i, art in enumerate(articles, start=1):
        body = (art.get("full_text") or "").strip()
        if len(body) > _CLEAN_BODY_MAX_CHARS:
            body = body[:_CLEAN_BODY_MAX_CHARS] + "…"
        if not body:
            body = "(empty)"
        items.append(f"[{i}]\n{body}")
    block = "\n\n----\n\n".join(items)
    n = len(articles)
    return f"""Você vai receber {n} corpos de artigos extraídos de sites de notícias brasileiros (Folha, O Globo, Valor, Estadão, CNN, Metrópoles). Cada um pode conter LIXO como:
- Controles de player de vídeo, atalhos de teclado
- Marcadores de publicidade ("Publicidade", "Anúncio", "AD", "Continue lendo após o anúncio")
- CTAs de newsletter ("Receba todas as semanas", "Inscreva-se", "Quer receber por email")
- Boilerplate ("Reportagem por X; Edição por Y", "Leia também", "Veja mais")
- Breadcrumbs, "Leia também", "Notícias relacionadas", "Veja também"
- Tags de seção, listas de notícias relacionadas, popular agora
- Linha de bullets "Apresentado por", "Patrocínio"

Para CADA artigo, devolva o corpo LIMPO — MANTENHA todos os parágrafos jornalísticos reais SEM ALTERAR. Apenas REMOVA o lixo. Preserve quebras de parágrafo.

Formato de saída — comece IMEDIATAMENTE com ###1###:

###1###
<corpo limpo do artigo 1>

###2###
<corpo limpo do artigo 2>

(continue pra todos os {n}; o último é ###{n}###)

Sem preâmbulo. Sem markdown. Sem comentários sobre o que removeu.

Artigos:

{block}
"""


def _clean_bodies_batch(articles: list[dict], claude_path: str) -> list[str]:
    if not articles:
        return []
    prompt = _build_clean_body_prompt(articles)
    log.info("claude -p clean batch: %d artigos, prompt %d chars", len(articles), len(prompt))
    output = _run_claude_with_retry(claude_path, prompt, _CLEAN_BODY_TIMEOUT_SECONDS, "clean-batch")
    if not output:
        log.warning("clean batch falhou — usando bodies raw")
        return [art.get("full_text", "") for art in articles]
    cleaned = _parse_batch_blocks(output, len(articles))
    for i, art in enumerate(articles):
        if not cleaned[i]:
            cleaned[i] = art.get("full_text", "")
    return cleaned


# ---------------------------------------------------------------------------
# WhatsApp + TinyURL
# ---------------------------------------------------------------------------

def _shorten_url(url: str) -> str:
    if not url:
        return ""
    try:
        api = TINYURL_API.format(url=urllib.parse.quote(url, safe=":/?=&"))
        with urllib.request.urlopen(api, timeout=5) as resp:
            short = resp.read().decode("utf-8").strip()
            if short.startswith("http"):
                return short
    except Exception as e:
        log.debug("TinyURL falhou para %s: %s", url[:60], e)
    return url


def _send_whatsapp_message(text: str) -> bool:
    if not PEAK_WHATSAPP_RECIPIENTS:
        log.warning("PEAK_WHATSAPP_RECIPIENTS vazio")
        return False
    all_ok = True
    for dest in PEAK_WHATSAPP_RECIPIENTS:
        body = json.dumps({"phone": dest, "message": text}).encode("utf-8")
        deadline = time.time() + _SEND_TIMEOUT_SECONDS
        sent = False
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            req = urllib.request.Request(
                f"{_WHATSAPP_SERVER_URL}/send", data=body,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30):
                    log.info("WhatsApp ✓ %s (%d chars, tentativa %d)", dest, len(text), attempt)
                    sent = True
                    break
            except Exception as e:
                remaining = int(deadline - time.time())
                log.warning("WhatsApp %s erro: %s (tentativa %d, %ds restantes)",
                            dest, e, attempt, remaining)
                if remaining > _RETRY_INTERVAL_SECONDS:
                    time.sleep(_RETRY_INTERVAL_SECONDS)
                else:
                    break
        if not sent:
            log.error("WhatsApp ✗ falha definitiva pra %s após %d tentativas", dest, attempt)
            all_ok = False
    return all_ok


def _label_for_item(item: dict) -> str:
    if item.get("columnist"):
        return item["columnist"]
    return SOURCE_LABELS.get(item.get("source_id") or item.get("home_tab"),
                             item.get("fonte_label") or "?")


def _build_digest(articles: list[dict], data_str: str) -> str:
    lines = [WHATSAPP_HEADER_TEMPLATE.format(date_br=data_str), ""]
    for art in articles:
        label = _label_for_item(art)
        titulo = art.get("title", "").strip()
        url = art.get("short_url") or art.get("raw_url") or art.get("url", "")
        resumo = (art.get("resumo_ai") or "").strip()
        resumo_inline = (
            " ".join(l.strip() for l in resumo.split("\n") if l.strip())
            if resumo else "(sem resumo disponível)"
        )
        lines.append(f"{label}: {titulo} ({url})")
        lines.append("")
        lines.append(f"> {resumo_inline}")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Obsidian Inbox — salva starred como .md depois de enviar no WhatsApp
# ---------------------------------------------------------------------------

# Caracteres bloqueados em filenames Windows + alguns mais agressivos
_FILENAME_BAD_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Em-dash usado como separador no filename (padrão CLAUDE.md do vault Macro)
_FN_SEP = " — "


def _sanitize_filename_part(s: str) -> str:
    """Remove caracteres inválidos pra filename, colapsa whitespace, trim."""
    if not s:
        return ""
    # Substitui o em-dash dentro do título por hifen pra não confundir com separador
    s = s.replace("—", "-")
    s = _FILENAME_BAD_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _format_body_paragraphs(body: str) -> str:
    """Separa parágrafos por linha em branco (mesma lógica do realtime/formatter)."""
    paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
    return "\n\n".join(paragraphs)


def _save_to_obsidian_inbox(art: dict) -> Path | None:
    """
    Salva o starred article como .md no Inbox/brasil/news/.
    Filename: YYYY-MM-DD — Fonte — Título.md (em-dash).
    Frontmatter: date, fonte, autor (se columnist), tags=[news, brasil], url.
    Body: # Título\\n\\n*DD/MM/YYYY HH:MM*\\n\\n<parágrafos espaçados>
    """
    fonte_label = (art.get("fonte_label") or "").strip() or "Desconhecido"
    title = (art.get("title") or "").strip()
    raw_url = (art.get("raw_url") or art.get("url") or "").strip()
    body = (art.get("cleaned_body") or art.get("full_text") or "").strip()
    columnist = (art.get("columnist") or "").strip()
    pub_iso = (art.get("published_at") or "").strip()

    if not title:
        log.warning("[obsidian] item sem título — pulando")
        return None

    # Parse timestamp do published_at (formato ISO local naive do seen.db).
    # Fallback: agora.
    dt = None
    if pub_iso:
        try:
            dt = datetime.fromisoformat(pub_iso.split(".")[0])
        except ValueError:
            dt = None
    if dt is None:
        dt = datetime.now()
    date_iso = dt.strftime("%Y-%m-%d")
    date_br = dt.strftime("%d/%m/%Y %H:%M")

    # Filename — limite total ~200 chars
    fonte_safe = _sanitize_filename_part(fonte_label)
    title_safe = _sanitize_filename_part(title)
    max_title_len = 200 - len(date_iso) - len(fonte_safe) - 2 * len(_FN_SEP) - len(".md")
    if len(title_safe) > max_title_len > 20:
        title_safe = title_safe[:max_title_len].rstrip()
    filename = f"{date_iso}{_FN_SEP}{fonte_safe}{_FN_SEP}{title_safe}.md"
    path = OBSIDIAN_INBOX_DIR / filename

    # Frontmatter
    fm_lines = [
        "---",
        f"date: {date_iso}",
        f"fonte: {fonte_label}",
    ]
    if columnist:
        fm_lines.append(f"autor: {columnist}")
    fm_lines.append(f"tags: [news, {OBSIDIAN_COUNTRY_TAG}]")
    if raw_url:
        fm_lines.append(f"url: {raw_url}")
    fm_lines.append("---")

    # Body markdown
    if body:
        body_md = _format_body_paragraphs(body)
    else:
        body_md = "(corpo do artigo não disponível)"

    content = (
        "\n".join(fm_lines)
        + "\n\n"
        + f"# {title}\n\n*{date_br}*\n\n{body_md}\n"
    )

    try:
        OBSIDIAN_INBOX_DIR.mkdir(parents=True, exist_ok=True)
        # Se já existe (re-run), sobrescreve
        path.write_text(content, encoding="utf-8")
        return path
    except Exception as e:
        log.error("[obsidian] falha ao salvar %s: %s", path.name, e)
        return None


def _build_starred_body_message(art: dict) -> str:
    label = _label_for_item(art)
    titulo = art.get("title", "").strip()
    # Starred = mensagem com corpo inteiro → manda link verdadeiro (não encurta).
    # O digest curto continua usando short_url pra economizar chars.
    url = art.get("raw_url") or art.get("url") or art.get("short_url", "")
    body = (art.get("cleaned_body") or art.get("full_text") or "").strip()
    if not body:
        body = "(corpo do artigo não disponível)"
    else:
        # Separar parágrafos por linha em branco (mesma lógica do
        # realtime/notify/formatter.py).
        paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
        body = "\n\n".join(paragraphs)
    return f"*{label}: {titulo}*\n\n{body}\n\n{url}"


# ---------------------------------------------------------------------------
# DB body loading
# ---------------------------------------------------------------------------

def _load_bodies_from_db(items: list[dict]) -> tuple[list[dict], int]:
    """
    Popula it['full_text'] consultando seen_articles no DB realtime.
    Tenta primeiro por headline_id; pra items sem id (legacy da selection.json
    de versões antigas), faz fallback por raw_url.
    Retorna (items_atualizados, n_sem_body).
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # 1) lookup por id
        ids = [it.get("headline_id") for it in items if it.get("headline_id")]
        by_id: dict[int, str] = {}
        if ids:
            placeholders = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT id, body FROM seen_articles WHERE id IN ({placeholders})",
                ids,
            ).fetchall()
            by_id = {r["id"]: (r["body"] or "") for r in rows}

        # 2) Fallback por URL pros items sem id
        urls_to_lookup = [
            it.get("raw_url") or it.get("url")
            for it in items
            if not it.get("headline_id") and (it.get("raw_url") or it.get("url"))
        ]
        by_url: dict[str, tuple[int, str]] = {}
        if urls_to_lookup:
            placeholders = ",".join("?" * len(urls_to_lookup))
            rows = conn.execute(
                f"SELECT id, url, body FROM seen_articles WHERE url IN ({placeholders})",
                urls_to_lookup,
            ).fetchall()
            for r in rows:
                by_url[r["url"]] = (r["id"], r["body"] or "")
    finally:
        conn.close()

    missing = 0
    for it in items:
        body = ""
        hid = it.get("headline_id")
        if hid and hid in by_id:
            body = by_id[hid]
        else:
            url = it.get("raw_url") or it.get("url")
            if url and url in by_url:
                hid_found, body = by_url[url]
                it["headline_id"] = hid_found  # patch in-memory pra próximos passos
        it["full_text"] = body
        if not body:
            missing += 1
    return items, missing


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> int:
    if not SELECTION_JSON.exists():
        log.error("selection.json não existe — nada a fazer")
        return 1

    selection = json.loads(SELECTION_JSON.read_text(encoding="utf-8"))
    added = [it for it in selection.get("items", []) if it.get("added")]
    added.sort(key=lambda it: it.get("position") or 0)
    starred = [it for it in added if it.get("important")]

    if not added:
        print("[extract] Nenhum artigo selecionado — nada a fazer.")
        return 0

    print(f"[extract] {len(added)} artigos selecionados ({len(starred)} starred)\n", flush=True)
    for it in added:
        marker = "★" if it.get("important") else " "
        label = _label_for_item(it)
        print(f"  {marker} #{it.get('position'):>2}  [{label:<18}] {it.get('title', '')[:75]}", flush=True)
    print()

    # 1. Body do DB (sem CDP fallback — se faltar, claude resume do título)
    print(f"[extract] Buscando corpos no DB...", flush=True)
    added, missing = _load_bodies_from_db(added)
    print(f"[extract] {len(added) - missing}/{len(added)} corpos no DB; "
          f"{missing} sem body (claude resume do título).\n", flush=True)

    # 2. AI summary batch
    claude_path = _find_claude_cli()
    if not claude_path:
        log.error("claude CLI não encontrado no PATH — resumos virão vazios")
        print("[extract] ⚠️  claude CLI não encontrado", flush=True)
        for it in added:
            it["resumo_ai"] = ""
    else:
        print(f"[extract] Gerando {len(added)} resumos via claude -p batch...", flush=True)
        t0 = time.time()
        summaries = _summarize_batch(added, claude_path)
        for it, s in zip(added, summaries):
            it["resumo_ai"] = s
        print(f"[extract] Resumos prontos em {time.time()-t0:.1f}s\n", flush=True)

    # 3. TinyURL
    print(f"[extract] Encurtando URLs...", flush=True)
    for it in added:
        it["short_url"] = _shorten_url(it.get("raw_url") or it.get("url") or "")

    # 4. Digest + send
    data_str = datetime.now().strftime("%d/%m/%Y")
    digest = _build_digest(added, data_str)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    debug_path = DATA_DIR / f"last_digest_{datetime.now():%Y%m%d-%H%M%S}.txt"
    debug_path.write_text(digest, encoding="utf-8")
    print(f"[extract] Digest salvo: {debug_path.name} ({len(digest)} chars)\n", flush=True)

    print(f"[extract] Enviando digest no WhatsApp...", flush=True)
    if not _send_whatsapp_message(digest):
        log.error("Digest WhatsApp falhou")
        return 2
    print(f"[extract] Digest enviado ✓\n", flush=True)

    # 5. Starred bodies
    if starred:
        if claude_path:
            print(f"[extract] Limpando bodies de {len(starred)} starred via claude -p...", flush=True)
            t0 = time.time()
            cleaned = _clean_bodies_batch(starred, claude_path)
            for it, c in zip(starred, cleaned):
                it["cleaned_body"] = c
            print(f"[extract] Bodies limpos em {time.time()-t0:.1f}s\n", flush=True)

        print(f"[extract] Enviando {len(starred)} bodies completos starred...\n", flush=True)
        for i, it in enumerate(starred, start=1):
            time.sleep(_INTER_MESSAGE_DELAY)
            msg = _build_starred_body_message(it)
            title = it.get("title", "")[:60]
            print(f"[starred] {i}/{len(starred)}: {title} ({len(msg)} chars)", flush=True)
            if not _send_whatsapp_message(msg):
                log.warning("Body starred falhou — continuando")

        # Salvar starred no Inbox do Obsidian Macro (staging — /sync-news-brasil
        # depois processa pra raw + wiki).
        print(f"\n[obsidian] Salvando {len(starred)} starred no Inbox/brasil/news/...", flush=True)
        saved = 0
        for it in starred:
            path = _save_to_obsidian_inbox(it)
            if path:
                saved += 1
                print(f"[obsidian] ✓ {path.name}", flush=True)
        print(f"[obsidian] {saved}/{len(starred)} salvos em {OBSIDIAN_INBOX_DIR}\n", flush=True)
    else:
        print("[extract] Nenhum starred — pulando bodies.\n", flush=True)

    print(f"\n[extract] ✓ {len(added)} enviados + {len(starred)} bodies starred.")
    return 0
