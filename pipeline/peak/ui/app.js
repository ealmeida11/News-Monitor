"use strict";

const state = {
  headlines: null,
  selection: null,
  activeTab: null,
  searchQueries: {},
};

let saveTimer = null;

async function init() {
  try {
    const [h, s] = await Promise.all([
      fetch("/headlines.json").then(r => r.json()),
      fetch("/selection.json").then(r => r.json()),
    ]);
    state.headlines = h;
    state.selection = s.items ? s : { items: [] };
    const sources = state.headlines.sources || [];
    state.activeTab = sources.length ? sources[0].id : null;
    buildTabs();
    bindDone();
    render();
  } catch (err) {
    document.getElementById("view").innerHTML =
      `<div class="empty-state">Falhou a carregar dados: ${err.message}</div>`;
  }
}

function buildTabs() {
  const tabs = document.getElementById("tabs");
  tabs.innerHTML = "";
  const sources = state.headlines.sources || [];
  for (const src of sources) {
    const btn = document.createElement("button");
    btn.className = "tab" + (src.id === state.activeTab ? " active" : "");
    btn.dataset.tab = src.id;
    const addedHere = state.selection.items.filter(i => i.added && i.home_tab === src.id).length;
    btn.textContent = addedHere > 0 ? `${src.label} (${addedHere})` : src.label;
    btn.addEventListener("click", () => setActiveTab(src.id));
    tabs.appendChild(btn);
  }
  const div = document.createElement("span");
  div.className = "divider";
  tabs.appendChild(div);
  const totalAdded = state.selection.items.filter(i => i.added).length;
  const ord = document.createElement("button");
  ord.className = "tab" + (state.activeTab === "ordering" ? " active" : "");
  ord.dataset.tab = "ordering";
  ord.textContent = totalAdded > 0 ? `Ordering (${totalAdded})` : "Ordering";
  ord.addEventListener("click", () => setActiveTab("ordering"));
  tabs.appendChild(ord);
}

function setActiveTab(tabId) {
  state.activeTab = tabId;
  buildTabs();
  render();
}

function render() {
  const view = document.getElementById("view");
  if (state.activeTab === "ordering") {
    renderOrdering(view);
  } else {
    renderSourceTab(view, state.activeTab);
  }
}

function renderSourceTab(view, tabId) {
  const src = state.headlines.sources.find(s => s.id === tabId);
  if (!src) {
    view.innerHTML = `<div class="empty-state">Tab desconhecida.</div>`;
    return;
  }
  if (src.scrape_status === "failed" || src.count === 0) {
    view.innerHTML = `
      <div class="section-label">${escapeHtml(src.label)} <span class="meta">${src.scrape_status}</span></div>
      <div class="empty-state">Sem headlines disponíveis nesta tab.</div>
    `;
    return;
  }
  const addedHere = state.selection.items.filter(i => i.added && i.home_tab === tabId).length;
  // Sort: keyword_score DESC, depois published_at DESC (já vem ordenado do servidor,
  // mas re-aplicamos pra robustez se o JSON mudar)
  const sorted = [...src.headlines].sort((a, b) => {
    const ds = (b.keyword_score || 0) - (a.keyword_score || 0);
    if (ds !== 0) return ds;
    return (b.published_at || "").localeCompare(a.published_at || "");
  });
  const lines = [
    `<div class="section-label">${escapeHtml(src.label)} <span class="meta">${src.count} headlines · ${addedHere} added</span></div>`,
    `<div class="search-wrap"><input class="search-bar" id="search-${tabId}" type="text" placeholder="Filtrar por título…" autocomplete="off" value="${escapeAttr(state.searchQueries[tabId] || '')}"></div>`,
    `<div id="row-list">`,
  ];
  for (const h of sorted) {
    const item = state.selection.items.find(i => i.url === h.url);
    const isAdded = !!(item && item.added);
    const pubTime = formatBRT(h.published_at);
    const fonteBadge = h.columnist
      ? `<span class="source-label">${escapeHtml(h.columnist)}</span>`
      : (h.fonte_label ? `<span class="source-label">${escapeHtml(h.fonte_label)}</span>` : "");
    const summary = (h.summary_line1 || h.summary_line2)
      ? `<div class="row-summary">${escapeHtml(h.summary_line1)} ${escapeHtml(h.summary_line2)}</div>`
      : "";
    lines.push(`
      <div class="row${isAdded ? " added" : ""}" data-url="${escapeAttr(h.url)}">
        <div style="flex:1; min-width:0;">
          <div class="title">${fonteBadge} ${escapeHtml(h.title)}</div>
          <div class="meta">${pubTime}${h.category_db ? ' · ' + escapeHtml(h.category_db) : ''}</div>
          ${summary}
        </div>
        <a class="open-link" href="${escapeAttr(h.raw_url || h.url)}" target="_blank" rel="noopener noreferrer">Open</a>
        <button class="add-btn${isAdded ? " is-added" : ""}" data-action="toggle-add">
          ${isAdded ? "✓ Added" : "+ Add"}
        </button>
      </div>
    `);
  }
  lines.push(`</div>`);
  view.innerHTML = lines.join("");

  const searchEl = view.querySelector(`#search-${tabId}`);
  if (searchEl) {
    const initialQuery = state.searchQueries[tabId] || "";
    const applyFilter = (query) => {
      const lower = query.toLowerCase();
      view.querySelectorAll("#row-list .row").forEach(row => {
        const titleEl = row.querySelector(".title");
        const title = titleEl ? titleEl.textContent : "";
        row.style.display = lower && !title.toLowerCase().includes(lower) ? "none" : "";
      });
    };
    if (initialQuery) applyFilter(initialQuery);
    searchEl.addEventListener("input", () => {
      const v = searchEl.value.trim();
      state.searchQueries[tabId] = v;
      applyFilter(v);
    });
  }

  view.querySelectorAll("[data-action='toggle-add']").forEach(btn => {
    btn.addEventListener("click", () => {
      const row = btn.closest(".row");
      toggleAdd(row.dataset.url);
    });
  });
}

function renderOrdering(view) {
  const added = state.selection.items
    .filter(i => i.added)
    .sort((a, b) => (a.position || 0) - (b.position || 0));
  const importantCount = added.filter(i => i.important).length;

  if (added.length === 0) {
    view.innerHTML = `
      <div class="section-label">Ordering <span class="meta">0 selected · 0 important</span></div>
      <div class="empty-state">Nada selecionado. Vai nas tabs das fontes e clica "+ Add".</div>
    `;
    return;
  }

  const lines = [
    `<div class="section-label">Ordering <span class="meta">${added.length} selected · ${importantCount} important</span></div>`,
    `<div id="callout-list">`,
  ];
  for (const item of added) {
    const label = item.columnist
      ? item.columnist
      : (labelForId(item.home_tab) || item.fonte_label || "?");
    const pubTime = formatBRT(item.published_at);
    lines.push(`
      <div class="callout${item.important ? " important" : ""}" data-url="${escapeAttr(item.url)}">
        <span class="handle" title="Arrastar pra reordenar">≡</span>
        <span class="ordinal">${String(item.position).padStart(2, "0")}</span>
        <span class="source-label">${escapeHtml(label)}</span>
        <div class="content">
          <div class="title">${escapeHtml(item.title)}</div>
          <div class="url-display">${pubTime} · ${escapeHtml(truncate(item.url, 80))}</div>
        </div>
        <a class="open-link" href="${escapeAttr(item.raw_url || item.url)}" target="_blank" rel="noopener noreferrer">Open</a>
        <button class="star-btn" data-action="toggle-important" title="Marcar como importante (body completo no WhatsApp)">
          ${item.important ? "★" : "☆"}
        </button>
        <button class="delete-btn" data-action="delete" title="Remover">×</button>
      </div>
    `);
  }
  lines.push(`</div>`);
  view.innerHTML = lines.join("");

  const list = document.getElementById("callout-list");
  Sortable.create(list, {
    handle: ".handle",
    animation: 150,
    onEnd: () => repackPositionsFromDom(),
  });

  view.querySelectorAll("[data-action='toggle-important']").forEach(btn => {
    btn.addEventListener("click", () => {
      const url = btn.closest(".callout").dataset.url;
      toggleImportant(url);
    });
  });
  view.querySelectorAll("[data-action='delete']").forEach(btn => {
    btn.addEventListener("click", () => {
      const url = btn.closest(".callout").dataset.url;
      deleteFromOrdering(url);
    });
  });
}

// --- state mutations ---

function toggleAdd(url) {
  let item = state.selection.items.find(i => i.url === url);
  if (!item) {
    const h = findHeadline(url);
    if (!h) return;
    item = {
      url, raw_url: h.raw_url || h.url, title: h.title,
      home_tab: h.home_tab, columnist: h.columnist || null,
      fonte_label: h.fonte_label || "",
      published_at: h.published_at,
      headline_id: h.headline_id,
      added: false, important: false, position: null,
    };
    state.selection.items.push(item);
  }
  if (item.added) {
    item.added = false; item.important = false; item.position = null;
  } else {
    item.added = true; item.position = nextPosition();
  }
  buildTabs(); render(); persist();
}

function toggleImportant(url) {
  const it = state.selection.items.find(i => i.url === url);
  if (!it) return;
  it.important = !it.important;
  render(); persist();
}

function deleteFromOrdering(url) {
  const it = state.selection.items.find(i => i.url === url);
  if (!it) return;
  it.added = false; it.important = false; it.position = null;
  repackPositions();
  buildTabs(); render(); persist();
}

function repackPositions() {
  const added = state.selection.items.filter(i => i.added).sort((a, b) => (a.position || 0) - (b.position || 0));
  added.forEach((it, i) => { it.position = i + 1; });
}

function repackPositionsFromDom() {
  const dom = Array.from(document.querySelectorAll("#callout-list .callout"));
  dom.forEach((el, i) => {
    const url = el.dataset.url;
    const it = state.selection.items.find(x => x.url === url);
    if (it) it.position = i + 1;
  });
  render(); persist();
}

function nextPosition() {
  const positions = state.selection.items.filter(i => i.added && typeof i.position === "number").map(i => i.position);
  return positions.length ? Math.max(...positions) + 1 : 1;
}

function findHeadline(url) {
  for (const src of state.headlines.sources) {
    const h = src.headlines.find(h => h.url === url);
    if (h) return h;
  }
  return null;
}

function labelForId(srcId) {
  const src = state.headlines.sources.find(s => s.id === srcId);
  return src ? src.label : srcId;
}

function persist() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch("/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.selection),
    }).catch(() => showToast("Save falhou — verifica o terminal."));
  }, 200);
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 2500);
}

function bindDone() {
  document.getElementById("done-btn").addEventListener("click", async () => {
    showToast("Seleção salva · fechando server…");
    try { await fetch("/quit", { method: "POST" }); } catch (e) {}
    setTimeout(() => {
      document.body.innerHTML = `
        <div style="font-family: 'IBM Plex Sans', sans-serif; padding: 80px 24px; text-align: center; color: #16164D;">
          <h2 style="font-family: 'Fraunces', serif; font-size: 28px; margin-bottom: 12px;">Pronto.</h2>
          <p style="font-size: 15px; color: #6b6b6b;">Pode fechar esta aba. O extract+send está rodando no terminal.</p>
        </div>
      `;
    }, 400);
  });
}

function formatBRT(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);  // ISO com Z → JS parseia como UTC corretamente
    const brt = new Date(d.getTime() - 3 * 3600 * 1000);
    const pad = n => String(n).padStart(2, "0");
    return `${pad(brt.getUTCDate())}/${pad(brt.getUTCMonth()+1)} ${pad(brt.getUTCHours())}:${pad(brt.getUTCMinutes())}`;
  } catch { return "—"; }
}

function truncate(s, n) {
  if (!s) return "";
  return s.length <= n ? s : s.slice(0, n - 1) + "…";
}

function escapeHtml(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function escapeAttr(s) { return escapeHtml(s); }

init();
