/* Overdrive — application frontend.
   Vanilla JS, aucune dépendance, aucun CDN. Consomme l'API REST locale. */

(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* État global                                                         */
  /* ------------------------------------------------------------------ */

  var state = {
    status: null,            // GET /api/status
    profile: null,           // profil QCM courant
    hardware: null,          // GET /api/hardware
    tweaks: null,            // GET /api/tweaks → {categories, tweaks}
    tweakSelection: new Set(),
    tweakSelectionInit: false,
    tweakFilter: "all",
    tweakResults: {},        // id → {ok, message}
    games: null,             // GET /api/games → liste
    selectedGame: null,
    cs2: null,               // GET /api/games/cs2
    programs: null,          // GET /api/programs
    cleanTargets: null,      // GET /api/clean/scan (null = pas encore analysé)
    cleanScanning: false,
    cleanSelection: new Set(),
    cleanResults: {},
    autoScan: false,
    pendingProfileSelect: false,
    aiKeys: null,            // GET /api/ai/keys
    chat: [],
    chatBusy: false,
    chatError: null,
    chatProvider: null,
    quiz: null
  };

  var renderSeq = 0;
  function alive(seq) { return seq === renderSeq; }

  /* ------------------------------------------------------------------ */
  /* Icônes SVG inline (style Lucide, trait 1.5px, currentColor)         */
  /* ------------------------------------------------------------------ */

  var ICONS = {
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    left: '<path d="m15 18-6-6 6-6"/>',
    right: '<path d="m9 18 6-6-6-6"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>'
  };

  function icon(name) {
    return '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || "") + "</svg>";
  }

  /* ------------------------------------------------------------------ */
  /* Utilitaires                                                         */
  /* ------------------------------------------------------------------ */

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function byId(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtMb(mb) {
    if (mb === null || mb === undefined) { return "—"; }
    if (mb >= 1024) { return (mb / 1024).toFixed(1).replace(".", ",") + " Go"; }
    return String(Math.round(mb * 10) / 10).replace(".", ",") + " Mo";
  }

  function fmtGb(gb) {
    if (gb === null || gb === undefined) { return "—"; }
    return String(Math.round(gb * 10) / 10).replace(".", ",") + " Go";
  }

  function setBusy(btn, label) {
    if (!btn) { return; }
    btn.dataset.prev = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = esc(label);
  }

  function clearBusy(btn) {
    if (!btn) { return; }
    if (btn.dataset.prev !== undefined) { btn.innerHTML = btn.dataset.prev; delete btn.dataset.prev; }
    btn.disabled = false;
  }

  function fallbackCopy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (e) { return false; }
  }

  function copyFeedback(btn, ok) {
    if (!btn) { return; }
    var prev = btn.innerHTML;
    btn.innerHTML = ok ? icon("check") + " Copié" : "Échec de la copie";
    btn.disabled = true;
    setTimeout(function () { btn.innerHTML = prev; btn.disabled = false; }, 1500);
  }

  function copyText(text, btn) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { copyFeedback(btn, true); },
        function () { copyFeedback(btn, fallbackCopy(text)); }
      );
    } else {
      copyFeedback(btn, fallbackCopy(text));
    }
  }

  /* Boutons "Copier" : lit le texte du <pre> voisin dans le bloc mono. */
  function bindCopyButtons(root) {
    $all(".copy-btn", root).forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        var block = btn.closest(".mono-block");
        var pre = block ? block.querySelector("pre") : null;
        copyText(pre ? pre.textContent : "", btn);
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Libellés                                                            */
  /* ------------------------------------------------------------------ */

  var IMPACT_META = {
    eleve: { label: "Impact élevé", cls: "badge-blue" },
    moyen: { label: "Impact moyen", cls: "badge-gray" },
    faible: { label: "Impact faible", cls: "badge-gray" }
  };

  var RISK_META = {
    sur: { label: "Sûr", cls: "badge-green" },
    modere: { label: "Modéré", cls: "badge-yellow" },
    avance: { label: "Avancé", cls: "badge-red" }
  };

  var STORE_LABELS = {
    steam: "Steam", riot: "Riot Client", epic: "Epic Games",
    battlenet: "Battle.net", ea: "EA App", multi: "Multi-plateformes"
  };

  var PROGRAM_CATEGORIES = {
    monitoring: "Monitoring", pilotes: "Pilotes", capture: "Capture",
    utilitaire: "Utilitaire", communication: "Communication"
  };

  var PROVIDERS_META = [
    { id: "groq", name: "Groq", note: 'Clé gratuite sur <a href="https://console.groq.com" target="_blank" rel="noopener">console.groq.com</a>' },
    { id: "openai", name: "OpenAI", note: null },
    { id: "anthropic", name: "Anthropic", note: null },
    { id: "gemini", name: "Google Gemini", note: null }
  ];

  function providerName(id) {
    for (var i = 0; i < PROVIDERS_META.length; i++) {
      if (PROVIDERS_META[i].id === id) { return PROVIDERS_META[i].name; }
    }
    return id;
  }

  /* ------------------------------------------------------------------ */
  /* Appels API                                                          */
  /* ------------------------------------------------------------------ */

  async function api(path, opts) {
    opts = opts || {};
    var init = { method: opts.method || (opts.body !== undefined ? "POST" : "GET"), headers: {} };
    if (opts.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    var res;
    try {
      res = await fetch(path, init);
    } catch (e) {
      showBanner("Connexion au serveur impossible. Vérifiez qu'Overdrive est en cours d'exécution.", "error");
      throw e;
    }
    var data = null;
    try { data = await res.json(); } catch (e2) { data = null; }
    if (!res.ok) {
      var msg = data && data.detail ? String(data.detail) : "Erreur serveur (" + res.status + ")";
      showBanner(msg, "error");
      var err = new Error(msg);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  /* ------------------------------------------------------------------ */
  /* Bandeau discret (erreurs réseau, confirmations)                     */
  /* ------------------------------------------------------------------ */

  var bannerTimer = null;

  function showBanner(message, kind) {
    var b = byId("banner");
    if (!b) { return; }
    b.className = kind === "error" ? "banner-error" : (kind === "ok" ? "banner-ok" : "");
    b.innerHTML = "<span>" + esc(message) + "</span>" +
      '<button class="btn btn-ghost btn-sm banner-close" type="button" aria-label="Fermer">' + icon("x") + "</button>";
    b.hidden = false;
    b.querySelector(".banner-close").addEventListener("click", hideBanner);
    if (bannerTimer) { clearTimeout(bannerTimer); }
    bannerTimer = setTimeout(hideBanner, kind === "error" ? 7000 : 4500);
  }

  function hideBanner() {
    var b = byId("banner");
    if (b) { b.hidden = true; b.innerHTML = ""; }
    if (bannerTimer) { clearTimeout(bannerTimer); bannerTimer = null; }
  }

  /* ------------------------------------------------------------------ */
  /* Modale de confirmation                                              */
  /* ------------------------------------------------------------------ */

  function openModal(opts) {
    var root = byId("modal-root");
    root.hidden = false;
    root.innerHTML =
      '<div class="modal-overlay">' +
      '<div class="modal" role="dialog" aria-modal="true" aria-label="' + esc(opts.title) + '">' +
      '<div class="modal-head"><h3 class="modal-title">' + esc(opts.title) + "</h3>" +
      '<button class="btn btn-ghost btn-sm" id="modal-x" type="button" aria-label="Fermer">' + icon("x") + "</button></div>" +
      '<div class="modal-body">' + (opts.bodyHtml || "") + "</div>" +
      '<div class="modal-foot">' +
      '<button class="btn" id="modal-cancel" type="button">' + esc(opts.cancelLabel || "Annuler") + "</button>" +
      '<button class="btn ' + (opts.danger ? "btn-danger-solid" : "btn-primary") + '" id="modal-confirm" type="button">' +
      esc(opts.confirmLabel || "Confirmer") + "</button>" +
      "</div></div></div>";

    function close() { root.hidden = true; root.innerHTML = ""; }
    byId("modal-x").addEventListener("click", close);
    byId("modal-cancel").addEventListener("click", close);
    byId("modal-confirm").addEventListener("click", function () {
      close();
      if (opts.onConfirm) { opts.onConfirm(); }
    });
    root.querySelector(".modal-overlay").addEventListener("click", function (e) {
      if (e.target === e.currentTarget) { close(); }
    });
    byId("modal-confirm").focus();
  }

  /* ------------------------------------------------------------------ */
  /* Thème clair / sombre                                                */
  /* ------------------------------------------------------------------ */

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("overdrive-theme", theme); } catch (e) { /* stockage indisponible */ }
    updateThemeLabel();
  }

  function updateThemeLabel() {
    var label = byId("theme-label");
    if (label) { label.textContent = currentTheme() === "dark" ? "Thème clair" : "Thème sombre"; }
    $all(".seg[data-seg='theme'] button").forEach(function (b) {
      b.classList.toggle("active", b.dataset.theme === currentTheme());
    });
  }

  async function setTheme(theme) {
    applyTheme(theme);
    try { await api("/api/settings", { body: { theme: theme } }); } catch (e) { /* déjà signalé */ }
  }

  /* ------------------------------------------------------------------ */
  /* Routeur (hash routing)                                              */
  /* ------------------------------------------------------------------ */

  var routes = {
    "/": renderHome,
    "/tweaks": renderTweaks,
    "/games": renderGames,
    "/clean": renderClean,
    "/assistant": renderAssistant,
    "/settings": renderSettings
  };

  function currentRoute() {
    var h = window.location.hash || "#/";
    var p = h.replace(/^#/, "");
    if (!routes[p]) { p = "/"; }
    return p;
  }

  function setActiveNav(route) {
    $all(".nav-item[data-route]").forEach(function (a) {
      a.classList.toggle("active", a.dataset.route === route);
    });
  }

  function render() {
    renderSeq++;
    var route = currentRoute();
    setActiveNav(route);
    routes[route](renderSeq);
  }

  /* ------------------------------------------------------------------ */
  /* Page Accueil                                                        */
  /* ------------------------------------------------------------------ */

  function renderHome(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">Accueil</h1>' +
      '<p class="page-sub">Vue d\'ensemble de la machine et de l\'état d\'optimisation.</p>' +
      '<div class="stats-row">' +
      statCard("stat-profile", "Profil", "…", "") +
      statCard("stat-tweaks", "Optimisations appliquées", "…", "") +
      statCard("stat-games", "Jeux détectés", "…", "") +
      "</div>" +
      '<div class="group-label">Matériel <span class="spacer"></span>' +
      '<button class="btn btn-ghost btn-sm" id="btn-hw-refresh" type="button">' + icon("refresh") + " Actualiser</button></div>" +
      '<div id="hw-area"><div class="loading-line">Détection du matériel…</div></div>' +
      '<div class="group-label">Actions rapides</div>' +
      '<div class="quick-actions">' +
      '<button class="btn btn-primary" id="btn-quick-profile" type="button">Optimiser selon mon profil</button>' +
      '<button class="btn" id="btn-quick-clean" type="button">' + icon("search") + " Analyser le nettoyage</button>" +
      "</div>" +
      '<div class="group-label">Programmes recommandés</div>' +
      '<div id="programs-area"><div class="loading-line">Chargement de la liste…</div></div>';

    byId("btn-quick-profile").addEventListener("click", function () {
      if (state.profile) {
        state.pendingProfileSelect = true;
        if (currentRoute() === "/tweaks") { render(); } else { window.location.hash = "#/tweaks"; }
      } else {
        openQuiz(false);
      }
    });
    byId("btn-quick-clean").addEventListener("click", function () {
      state.autoScan = true;
      if (currentRoute() === "/clean") { render(); } else { window.location.hash = "#/clean"; }
    });
    byId("btn-hw-refresh").addEventListener("click", function () {
      var btn = byId("btn-hw-refresh");
      setBusy(btn, "Analyse…");
      loadHardware(seq, true).then(function () { clearBusy(btn); });
    });

    updateProfileStat();
    loadHardware(seq, false);
    loadHomeStats(seq);
    loadPrograms(seq);
  }

  function statCard(id, label, value, note) {
    return '<div class="card stat-card" id="' + id + '">' +
      '<div class="stat-label">' + esc(label) + "</div>" +
      '<div class="stat-value">' + esc(value) + "</div>" +
      '<div class="stat-note">' + esc(note) + "</div></div>";
  }

  function updateProfileStat() {
    var card = byId("stat-profile");
    if (!card) { return; }
    if (state.profile) {
      card.querySelector(".stat-value").textContent = state.profile.label || state.profile.id;
      card.querySelector(".stat-note").textContent = "Profil issu du questionnaire";
    } else {
      card.querySelector(".stat-value").textContent = "Aucun";
      card.querySelector(".stat-note").innerHTML =
        '<button class="link-btn" id="link-open-quiz" type="button">Répondre au questionnaire</button>';
      var link = byId("link-open-quiz");
      if (link) { link.addEventListener("click", function () { openQuiz(false); }); }
    }
  }

  async function loadHardware(seq, refresh) {
    if (!state.hardware || refresh) {
      try {
        state.hardware = await api("/api/hardware" + (refresh ? "?refresh=1" : ""));
      } catch (e) {
        if (alive(seq) && byId("hw-area")) {
          byId("hw-area").innerHTML = '<p class="muted small">Matériel non disponible pour le moment.</p>';
        }
        return;
      }
    }
    if (!alive(seq) || !byId("hw-area")) { return; }
    byId("hw-area").innerHTML = hardwareHtml(state.hardware);
  }

  function hwCard(label, lines) {
    var body = lines.filter(Boolean).map(function (l) {
      return '<div class="hw-line mono">' + l + "</div>";
    }).join("");
    return '<div class="card hw-card"><div class="hw-label">' + esc(label) + "</div>" +
      (body || '<div class="hw-line muted small">Non détecté</div>') + "</div>";
  }

  function hardwareHtml(h) {
    if (!h) { return '<p class="muted small">Matériel non disponible.</p>'; }
    var os = h.os || {}, cpu = h.cpu || {}, ram = h.ram || {};
    var gpus = h.gpus || [], disks = h.disks || [], net = h.network || {};

    var html = "";
    if (h.summary) {
      html += '<div class="mono-block hw-summary"><pre>' + esc(h.summary) + "</pre></div>";
    }
    html += '<div class="hw-grid">';
    html += hwCard("Système", [
      esc([os.name, os.version].filter(Boolean).join(" ")) + (os.build ? ' <span class="muted">(build ' + esc(os.build) + ")</span>" : "")
    ]);
    html += hwCard("Processeur", [
      esc(cpu.name || ""),
      (cpu.cores_physical ? esc(cpu.cores_physical) + " cœurs / " + esc(cpu.cores_logical || "?") + " threads" : ""),
      (cpu.freq_mhz_max ? "jusqu'à " + esc(Math.round(cpu.freq_mhz_max)) + " MHz" : ""),
      (cpu.usage_percent !== undefined && cpu.usage_percent !== null ? "charge actuelle " + esc(Math.round(cpu.usage_percent)) + " %" : "")
    ]);
    html += hwCard("Mémoire", [
      ram.total_gb !== undefined ? esc(fmtGb(ram.total_gb)) + " au total" : "",
      ram.available_gb !== undefined ? esc(fmtGb(ram.available_gb)) + " disponibles" : "",
      ram.used_percent !== undefined ? "utilisée à " + esc(Math.round(ram.used_percent)) + " %" : ""
    ]);
    html += hwCard("Carte graphique", gpus.length ? gpus.map(function (g) {
      return esc(g.name || "GPU") +
        (g.vram_mb ? ' <span class="muted">· ' + esc(fmtMb(g.vram_mb)) + "</span>" : "") +
        (g.driver ? ' <span class="muted">· pilote ' + esc(g.driver) + "</span>" : "");
    }) : []);
    html += hwCard("Stockage", disks.map(function (d) {
      return esc(d.mountpoint || d.device || "") + ' <span class="muted">· ' +
        esc(fmtGb(d.free_gb)) + " libres / " + esc(fmtGb(d.total_gb)) + "</span>";
    }));
    var ifaces = (net.interfaces || []).slice(0, 4);
    html += hwCard("Réseau", [esc(net.hostname || "")].concat(ifaces.map(function (i) {
      return esc(i.name || "") + (i.speed_mbps ? ' <span class="muted">· ' + esc(i.speed_mbps) + " Mb/s</span>" : "");
    })));
    html += "</div>";
    return html;
  }

  async function loadHomeStats(seq) {
    var tweaksP = state.tweaks ? Promise.resolve(state.tweaks) : api("/api/tweaks").then(function (d) { state.tweaks = d; return d; });
    var gamesP = state.games ? Promise.resolve(state.games) : api("/api/games").then(function (d) { state.games = d.games || []; return state.games; });

    try {
      var tw = await tweaksP;
      if (alive(seq) && byId("stat-tweaks")) {
        var list = tw.tweaks || [];
        var applied = list.filter(function (t) { return t.applied === true; }).length;
        byId("stat-tweaks").querySelector(".stat-value").textContent = applied + " / " + list.length;
        byId("stat-tweaks").querySelector(".stat-note").textContent = "sur l'ensemble du catalogue";
      }
    } catch (e) { /* bandeau déjà affiché */ }

    try {
      var games = await gamesP;
      if (alive(seq) && byId("stat-games")) {
        var n = games.filter(function (g) { return g.installed; }).length;
        byId("stat-games").querySelector(".stat-value").textContent = n + " / " + games.length;
        byId("stat-games").querySelector(".stat-note").textContent = n ? "présents sur cette machine" : "aucun jeu détecté";
      }
    } catch (e2) { /* idem */ }
  }

  async function loadPrograms(seq) {
    if (!state.programs) {
      try {
        state.programs = await api("/api/programs");
      } catch (e) {
        if (alive(seq) && byId("programs-area")) {
          byId("programs-area").innerHTML = '<p class="muted small">Liste indisponible pour le moment.</p>';
        }
        return;
      }
    }
    if (!alive(seq) || !byId("programs-area")) { return; }
    byId("programs-area").innerHTML = programsHtml(state.programs);
    $all("#programs-area [data-install]").forEach(function (btn) {
      btn.addEventListener("click", onInstallProgram);
    });
  }

  function programsHtml(data) {
    var progs = (data && data.programs) || [];
    var hasWinget = !!(data && data.winget);
    if (!progs.length) { return '<p class="muted small">Aucun programme recommandé.</p>'; }
    var cards = progs.map(function (p) {
      var actions = "";
      if (hasWinget && p.winget_id) {
        actions += '<button class="btn btn-sm" data-install="' + esc(p.id) + '" type="button">' +
          icon("download") + " Installer</button>";
      }
      if (p.url) {
        actions += '<a class="btn btn-sm ' + (hasWinget && p.winget_id ? "btn-ghost" : "") +
          '" href="' + esc(p.url) + '" target="_blank" rel="noopener">' + icon("external") + " Site officiel</a>";
      }
      return '<div class="card program-card">' +
        '<div class="prog-head"><span class="card-title">' + esc(p.name) + "</span>" +
        '<span class="badge badge-gray">' + esc(PROGRAM_CATEGORIES[p.category] || p.category || "") + "</span></div>" +
        '<div class="prog-desc">' + esc(p.description || "") + "</div>" +
        '<div class="prog-foot">' + actions + "</div>" +
        '<div class="prog-result" id="prog-res-' + esc(p.id) + '"></div>' +
        "</div>";
    }).join("");
    var note = hasWinget ? "" :
      '<p class="muted small">winget n\'est pas disponible sur ce système : l\'installation directe est désactivée, les liens restent accessibles.</p>';
    return note + '<div class="grid grid-3">' + cards + "</div>";
  }

  async function onInstallProgram(e) {
    var btn = e.currentTarget;
    var id = btn.dataset.install;
    setBusy(btn, "Installation…");
    var box = byId("prog-res-" + id);
    try {
      var res = await api("/api/programs/install", { body: { id: id } });
      if (box) {
        box.innerHTML = '<span class="' + (res.ok ? "ok-text" : "err-text") + '">' + esc(res.message || "") + "</span>";
      }
    } catch (err) {
      if (box) { box.innerHTML = '<span class="err-text">Installation impossible.</span>'; }
    }
    clearBusy(btn);
  }

  /* ------------------------------------------------------------------ */
  /* Page Optimisations                                                  */
  /* ------------------------------------------------------------------ */

  function findTweak(id) {
    var list = (state.tweaks && state.tweaks.tweaks) || [];
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) { return list[i]; } }
    return null;
  }

  async function renderTweaks(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">Optimisations</h1>' +
      '<p class="page-sub">Sélectionnez les réglages à appliquer. Chaque optimisation est réversible.</p>' +
      '<div id="tweaks-area"><div class="loading-line">Chargement du catalogue…</div></div>';

    try {
      state.tweaks = await api("/api/tweaks");
    } catch (e) {
      if (alive(seq) && byId("tweaks-area")) {
        byId("tweaks-area").innerHTML =
          '<div class="card empty-state">' + icon("alert") +
          '<p class="empty-title">Catalogue indisponible</p>' +
          '<p>Le serveur n\'a pas répondu. Réessayez dans un instant.</p>' +
          '<button class="btn" id="btn-tweaks-retry" type="button">Réessayer</button></div>';
        byId("btn-tweaks-retry").addEventListener("click", render);
      }
      return;
    }
    if (!alive(seq)) { return; }

    var tweaks = state.tweaks.tweaks || [];
    var supportedIds = {};
    tweaks.forEach(function (t) { if (t.supported !== false) { supportedIds[t.id] = true; } });

    /* Pré-cocher la sélection du profil (premier passage ou demande explicite). */
    if (state.profile && (state.pendingProfileSelect || !state.tweakSelectionInit)) {
      state.tweakSelection = new Set((state.profile.recommended_tweaks || []).filter(function (id) {
        return supportedIds[id];
      }));
      state.pendingProfileSelect = false;
      state.tweakSelectionInit = true;
    }
    /* Retire de la sélection les ids disparus ou non supportés. */
    Array.from(state.tweakSelection).forEach(function (id) {
      if (!supportedIds[id]) { state.tweakSelection.delete(id); }
    });

    buildTweaksArea();
  }

  function buildTweaksArea() {
    var area = byId("tweaks-area");
    if (!area) { return; }
    var data = state.tweaks || {};
    var categories = data.categories || [];
    var tweaks = data.tweaks || [];
    var st = state.status;

    var note = "";
    if (st && !st.is_windows) {
      note = '<div class="notice">' + icon("alert") +
        "<span>Système non Windows détecté : les optimisations sont affichées à titre informatif (mode développement), leur application est désactivée.</span></div>";
    } else if (st && st.is_windows && !st.is_admin) {
      note = '<div class="notice">' + icon("alert") +
        "<span>Overdrive n'est pas lancé en administrateur : certains réglages (registre machine, services) pourraient échouer. Relancez l'application en tant qu'administrateur pour un résultat complet.</span></div>";
    }

    var toolbar =
      '<div class="tweaks-toolbar">' +
      '<button class="btn btn-sm" id="btn-sel-profile" type="button"' +
      (state.profile ? "" : ' disabled title="Répondez d\'abord au questionnaire"') + ">Sélection profil</button>" +
      '<button class="btn btn-sm" id="btn-sel-safe" type="button">Tout sûr</button>' +
      '<button class="btn btn-sm btn-ghost" id="btn-sel-none" type="button">Tout désélectionner</button>' +
      '<span class="tweaks-count" id="tweak-count"></span>' +
      '<span class="spacer"></span>' +
      '<button class="btn btn-sm" id="btn-restore" type="button">' + icon("shield") + " Point de restauration</button>" +
      '<button class="btn btn-sm btn-danger" id="btn-revert" type="button">Annuler les tweaks appliqués</button>' +
      '<button class="btn btn-sm btn-primary" id="btn-apply" type="button"></button>' +
      "</div>";

    var chips = '<div class="chips">' +
      '<button class="chip' + (state.tweakFilter === "all" ? " active" : "") + '" data-filter="all" type="button">Toutes</button>' +
      categories.map(function (c) {
        return '<button class="chip' + (state.tweakFilter === c.id ? " active" : "") + '" data-filter="' +
          esc(c.id) + '" type="button">' + esc(c.label) + "</button>";
      }).join("") + "</div>";

    var groups = categories.map(function (c) {
      if (state.tweakFilter !== "all" && state.tweakFilter !== c.id) { return ""; }
      var items = tweaks.filter(function (t) { return t.category === c.id; });
      if (!items.length) { return ""; }
      var rows = items.map(tweakRowHtml).join("");
      return '<div class="tweak-group"><h2 class="tweak-group-head">' + esc(c.label) +
        ' <span class="muted">· ' + items.length + "</span></h2>" + rows + "</div>";
    }).join("");

    area.innerHTML = note + toolbar + chips + '<div id="tweaks-list">' + (groups ||
      '<p class="muted small">Aucune optimisation dans cette catégorie.</p>') + "</div>";

    /* Liaisons. */
    byId("btn-sel-profile").addEventListener("click", function () {
      if (!state.profile) { return; }
      var rec = state.profile.recommended_tweaks || [];
      state.tweakSelection = new Set(rec.filter(function (id) {
        var t = findTweak(id);
        return t && t.supported !== false;
      }));
      buildTweaksArea();
    });
    byId("btn-sel-safe").addEventListener("click", function () {
      state.tweakSelection = new Set(tweaks.filter(function (t) {
        return t.supported !== false && t.risk === "sur";
      }).map(function (t) { return t.id; }));
      buildTweaksArea();
    });
    byId("btn-sel-none").addEventListener("click", function () {
      state.tweakSelection = new Set();
      buildTweaksArea();
    });
    byId("btn-apply").addEventListener("click", onApplyTweaks);
    byId("btn-revert").addEventListener("click", onRevertTweaks);
    byId("btn-restore").addEventListener("click", onRestorePoint);

    $all(".chip", area).forEach(function (chip) {
      chip.addEventListener("click", function () {
        state.tweakFilter = chip.dataset.filter;
        buildTweaksArea();
      });
    });

    byId("tweaks-list").addEventListener("change", function (e) {
      var input = e.target;
      if (!input.classList.contains("tweak-check")) { return; }
      var id = input.dataset.id;
      if (input.checked) { state.tweakSelection.add(id); } else { state.tweakSelection.delete(id); }
      updateTweakCounts();
    });

    updateTweakCounts();
  }

  function tweakRowHtml(t) {
    var unsupported = t.supported === false;
    var im = IMPACT_META[t.impact] || IMPACT_META.moyen;
    var rk = RISK_META[t.risk] || RISK_META.sur;
    var status = "";
    if (unsupported) {
      status = '<span class="tweak-status">Non supporté ici</span>';
    } else if (t.applied === true) {
      status = '<span class="tweak-status"><span class="dot dot-green"></span>Appliqué</span>';
    }
    var checked = state.tweakSelection.has(t.id) && !unsupported;
    var res = state.tweakResults[t.id];
    var resHtml = res ?
      '<div class="tweak-result ' + (res.ok ? "ok-text" : "err-text") + '">' + esc(res.message || "") + "</div>" : "";

    return '<label class="tweak-row' + (unsupported ? " unsupported" : "") + '">' +
      '<input type="checkbox" class="tweak-check" data-id="' + esc(t.id) + '"' +
      (checked ? " checked" : "") + (unsupported ? " disabled" : "") + ">" +
      '<span class="tweak-name">' + esc(t.name) + "</span>" +
      '<span class="badge ' + im.cls + '">' + esc(im.label) + "</span>" +
      '<span class="badge ' + rk.cls + '">' + esc(rk.label) + "</span>" +
      '<span class="tweak-desc" title="' + esc(t.description || "") + '">' + esc(t.description || "") + "</span>" +
      status + "</label>" + resHtml;
  }

  function updateTweakCounts() {
    var n = state.tweakSelection.size;
    var count = byId("tweak-count");
    if (count) { count.textContent = n + " sélectionné" + (n > 1 ? "s" : ""); }
    var apply = byId("btn-apply");
    if (apply) {
      apply.textContent = "Appliquer (" + n + ")";
      apply.disabled = n === 0;
    }
  }

  function onApplyTweaks() {
    var ids = Array.from(state.tweakSelection);
    if (!ids.length) { return; }
    var advanced = ids.map(findTweak).filter(function (t) { return t && t.risk === "avance"; });
    if (advanced.length) {
      openModal({
        title: "Tweaks avancés sélectionnés",
        bodyHtml: "<p>Les réglages suivants sont marqués avancés : ils modifient des paramètres système sensibles. " +
          "Un point de restauration est recommandé avant application.</p><ul>" +
          advanced.map(function (t) { return "<li>" + esc(t.name) + "</li>"; }).join("") + "</ul>",
        confirmLabel: "Appliquer quand même",
        danger: true,
        onConfirm: function () { doApplyTweaks(ids); }
      });
    } else {
      doApplyTweaks(ids);
    }
  }

  async function doApplyTweaks(ids) {
    var btn = byId("btn-apply");
    setBusy(btn, "Application…");
    var results;
    try {
      var res = await api("/api/tweaks/apply", { body: { ids: ids } });
      results = res.results || [];
    } catch (e) {
      clearBusy(btn);
      return;
    }
    var okCount = 0;
    results.forEach(function (r) {
      state.tweakResults[r.id] = r;
      if (r.ok) { okCount++; state.tweakSelection.delete(r.id); }
    });
    showBanner("Application terminée : " + okCount + " réussie" + (okCount > 1 ? "s" : "") +
      (results.length - okCount ? " · " + (results.length - okCount) + " en échec" : "") + ".",
      results.length - okCount ? "error" : "ok");
    try { state.tweaks = await api("/api/tweaks"); } catch (e2) { /* état précédent conservé */ }
    if (currentRoute() === "/tweaks") { buildTweaksArea(); }
  }

  function onRevertTweaks() {
    var tweaks = (state.tweaks && state.tweaks.tweaks) || [];
    var ids = tweaks.filter(function (t) { return t.tracked; }).map(function (t) { return t.id; });
    if (!ids.length) {
      showBanner("Aucun tweak appliqué par Overdrive à annuler.", "");
      return;
    }
    openModal({
      title: "Annuler les tweaks appliqués",
      bodyHtml: "<p>" + ids.length + " réglage" + (ids.length > 1 ? "s" : "") +
        " appliqué" + (ids.length > 1 ? "s" : "") + " par Overdrive ser" + (ids.length > 1 ? "ont" : "a") +
        " remis à leur valeur d'origine.</p>",
      confirmLabel: "Tout annuler",
      danger: true,
      onConfirm: async function () {
        var btn = byId("btn-revert");
        setBusy(btn, "Annulation…");
        try {
          var res = await api("/api/tweaks/revert", { body: { ids: ids } });
          var results = res.results || [];
          var okCount = results.filter(function (r) { return r.ok; }).length;
          results.forEach(function (r) { state.tweakResults[r.id] = r; });
          showBanner("Annulation terminée : " + okCount + " / " + results.length + ".", "ok");
          state.tweaks = await api("/api/tweaks");
        } catch (e) { /* bandeau déjà affiché */ }
        if (currentRoute() === "/tweaks") { buildTweaksArea(); }
      }
    });
  }

  async function onRestorePoint() {
    var btn = byId("btn-restore");
    setBusy(btn, "Création…");
    try {
      var res = await api("/api/restore-point", { method: "POST" });
      showBanner(res.message || (res.ok ? "Point de restauration créé." : "Création impossible."), res.ok ? "ok" : "error");
    } catch (e) { /* bandeau déjà affiché */ }
    clearBusy(btn);
  }

  /* ------------------------------------------------------------------ */
  /* Page Jeux                                                           */
  /* ------------------------------------------------------------------ */

  async function renderGames(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">Jeux</h1>' +
      '<p class="page-sub">Options de lancement et réglages recommandés pour les jeux compétitifs courants.</p>' +
      '<div id="games-area"><div class="loading-line">Détection des jeux installés…</div></div>';

    try {
      var res = await api("/api/games");
      state.games = res.games || [];
    } catch (e) {
      if (alive(seq) && byId("games-area")) {
        byId("games-area").innerHTML = '<p class="muted small">Détection indisponible pour le moment.</p>';
      }
      return;
    }
    if (!alive(seq)) { return; }
    buildGamesArea(seq);
  }

  function buildGamesArea(seq) {
    var area = byId("games-area");
    if (!area) { return; }
    var games = state.games || [];
    var detected = games.filter(function (g) { return g.installed; }).length;

    var note = detected === 0 ?
      '<p class="muted small">Aucun jeu détecté automatiquement sur cette machine. Les fiches et recommandations restent consultables.</p>' : "";

    var cards = games.map(function (g) {
      var badge = g.installed ?
        '<span class="badge badge-green">Détecté</span>' :
        '<span class="badge badge-gray">Non détecté</span>';
      var path = g.installed && g.install_path ?
        '<div class="game-path mono" title="' + esc(g.install_path) + '">' + esc(g.install_path) + "</div>" : "";
      return '<div class="card game-card' + (state.selectedGame === g.id ? " selected" : "") +
        '" data-game="' + esc(g.id) + '" tabindex="0" role="button">' +
        '<span class="card-title">' + esc(g.name) + "</span>" +
        '<span class="game-store">' + esc(STORE_LABELS[g.store] || g.store || "") + "</span>" +
        "<div>" + badge + "</div>" + path + "</div>";
    }).join("");

    area.innerHTML = note + '<div class="grid grid-4" id="games-grid">' + cards + "</div>" +
      '<div id="game-detail-area"></div>';

    $all("#games-grid .game-card").forEach(function (card) {
      function select() {
        state.selectedGame = card.dataset.game;
        buildGamesArea(seq);
        var det = byId("game-detail-area");
        if (det) { det.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
      }
      card.addEventListener("click", select);
      card.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(); }
      });
    });

    if (state.selectedGame) { buildGameDetail(seq); }
  }

  function buildGameDetail(seq) {
    var area = byId("game-detail-area");
    if (!area) { return; }
    var game = null;
    (state.games || []).forEach(function (g) { if (g.id === state.selectedGame) { game = g; } });
    if (!game) { area.innerHTML = ""; return; }

    var html = '<div class="card game-detail">' +
      '<div class="game-detail-head"><div><h2>' + esc(game.name) + "</h2>" +
      '<span class="muted small">' + esc(STORE_LABELS[game.store] || game.store || "") +
      (game.installed && game.install_path ? ' · <span class="mono mono-inline">' + esc(game.install_path) + "</span>" : "") +
      "</span></div>" +
      '<button class="btn btn-ghost btn-sm" id="btn-game-close" type="button" aria-label="Fermer">' + icon("x") + "</button></div>";

    if (game.launch_options) {
      html += '<div class="group-label">Options de lancement</div>' +
        '<div class="mono-block"><pre>' + esc(game.launch_options) + "</pre>" +
        '<button class="btn btn-sm copy-btn" type="button">' + icon("copy") + " Copier</button></div>";
      if (game.launch_options_note) {
        html += '<p class="muted small">' + esc(game.launch_options_note) + "</p>";
      }
    }

    var opts = game.optimizations || [];
    if (opts.length) {
      html += '<div class="group-label">Réglages recommandés</div><ul class="opt-list">' +
        opts.map(function (o) {
          return '<li><div class="opt-title">' + esc(o.title) + "</div>" +
            '<div class="opt-detail">' + esc(o.detail) + "</div></li>";
        }).join("") + "</ul>";
    }

    if (game.id === "cs2") {
      html += '<div id="cs2-panel"><div class="loading-line">Lecture de la configuration CS2…</div></div>';
    }

    html += "</div>";
    area.innerHTML = html;

    byId("btn-game-close").addEventListener("click", function () {
      state.selectedGame = null;
      buildGamesArea(seq);
    });
    bindCopyButtons(area);

    if (game.id === "cs2") { loadCs2Panel(seq); }
  }

  async function loadCs2Panel(seq) {
    if (!state.cs2) {
      try {
        state.cs2 = await api("/api/games/cs2");
      } catch (e) {
        var boxErr = byId("cs2-panel");
        if (boxErr) { boxErr.innerHTML = '<p class="muted small">Informations CS2 indisponibles.</p>'; }
        return;
      }
    }
    if (!alive(seq)) { return; }
    var box = byId("cs2-panel");
    if (!box) { return; }
    box.innerHTML = cs2PanelHtml(state.cs2);
    bindCs2Panel(seq);
  }

  function cs2PanelHtml(info) {
    var profiles = (info && info.userdata_profiles) || [];
    var html = '<div class="group-label">Configuration CS2</div>';

    if (!profiles.length) {
      html += '<p class="muted small">Aucun profil Steam (userdata) détecté : l\'écriture de l\'autoexec n\'est pas possible pour le moment.</p>';
    } else {
      html += profiles.map(function (p) {
        return '<div class="cs2-profile-row">' +
          "<span>Profil <span class=\"mono mono-inline\">" + esc(p.user_id) + "</span></span>" +
          (p.has_autoexec ?
            '<span class="badge badge-green">autoexec présent</span>' :
            '<span class="badge badge-gray">aucun autoexec</span>') +
          '<span class="muted small mono clean-path" title="' + esc(p.cfg_dir) + '">' + esc(p.cfg_dir) + "</span>" +
          "</div>";
      }).join("");

      var select = "";
      if (profiles.length > 1) {
        select = '<select class="input" id="cs2-user">' + profiles.map(function (p) {
          return '<option value="' + esc(p.user_id) + '">Profil ' + esc(p.user_id) + "</option>";
        }).join("") + "</select> ";
      }
      html += '<div class="quick-actions" style="margin-top:12px">' + select +
        '<button class="btn btn-primary btn-sm" id="btn-cs2-write" type="button">Écrire l\'autoexec recommandé</button></div>' +
        '<div class="small" id="cs2-write-result" style="margin-top:8px"></div>';
    }

    if (info && info.autoexec_recommended) {
      html += '<details class="fold"><summary>Aperçu de l\'autoexec recommandé</summary>' +
        '<div class="fold-body"><div class="mono-block"><pre>' + esc(info.autoexec_recommended) + "</pre>" +
        '<button class="btn btn-sm copy-btn" type="button">' + icon("copy") + " Copier</button></div></div></details>";
    }

    var recs = (info && info.video_recommendations) || [];
    if (recs.length) {
      html += '<div class="group-label">Réglages vidéo (cs2_video.txt)</div>';
      if (!info.video_settings) {
        html += '<p class="muted small">Fichier cs2_video.txt non lu : recommandations générales.</p>';
      }
      html += '<table class="table"><thead><tr><th>Paramètre</th><th>Actuel</th><th>Recommandé</th><th>Note</th></tr></thead><tbody>' +
        recs.map(function (r) {
          return "<tr><td class=\"mono\">" + esc(r.key) + "</td><td class=\"mono\">" + esc(r.current === null || r.current === undefined ? "—" : r.current) +
            "</td><td class=\"mono\">" + esc(r.recommended) + "</td><td class=\"muted small\">" + esc(r.note || "") + "</td></tr>";
        }).join("") + "</tbody></table>";
    }
    return html;
  }

  function bindCs2Panel(seq) {
    var panel = byId("cs2-panel");
    if (!panel) { return; }
    bindCopyButtons(panel);
    var writeBtn = byId("btn-cs2-write");
    if (writeBtn) {
      writeBtn.addEventListener("click", async function () {
        var sel = byId("cs2-user");
        var userId = sel ? sel.value : null;
        setBusy(writeBtn, "Écriture…");
        try {
          var res = await api("/api/games/cs2/autoexec", { body: { user_id: userId } });
          var out = byId("cs2-write-result");
          if (out) {
            out.innerHTML = '<span class="' + (res.ok ? "ok-text" : "err-text") + '">' + esc(res.message || "") + "</span>" +
              (res.ok && res.path ? ' <span class="mono mono-inline">' + esc(res.path) + "</span>" : "");
          }
          if (res.ok) { state.cs2 = null; loadCs2Panel(seq); return; }
        } catch (e) { /* bandeau déjà affiché */ }
        clearBusy(writeBtn);
      });
    }
  }

  /* ------------------------------------------------------------------ */
  /* Page Nettoyage                                                      */
  /* ------------------------------------------------------------------ */

  function renderClean(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">Nettoyage</h1>' +
      '<p class="page-sub">Fichiers temporaires, caches de shaders et autres fichiers récupérables.</p>' +
      '<div id="clean-area"></div>';
    buildCleanArea(seq);
    if (state.autoScan) {
      state.autoScan = false;
      doCleanScan(seq);
    }
  }

  function buildCleanArea(seq) {
    var area = byId("clean-area");
    if (!area) { return; }

    if (state.cleanScanning) {
      area.innerHTML = '<div class="loading-line">Analyse en cours…</div>';
      return;
    }

    if (state.cleanTargets === null) {
      area.innerHTML = '<div class="card empty-state">' + icon("search") +
        '<p class="empty-title">Aucune analyse pour l\'instant</p>' +
        "<p>Lancez une analyse pour mesurer l'espace récupérable.</p>" +
        '<button class="btn btn-primary" id="btn-scan" type="button">Analyser</button></div>';
      byId("btn-scan").addEventListener("click", function () { doCleanScan(seq); });
      return;
    }

    var targets = state.cleanTargets;
    if (!targets.length) {
      area.innerHTML = '<div class="card empty-state">' + icon("check") +
        '<p class="empty-title">Rien à nettoyer</p>' +
        "<p>Aucune cible de nettoyage trouvée sur ce système.</p>" +
        '<button class="btn" id="btn-rescan" type="button">' + icon("refresh") + " Réanalyser</button></div>";
      byId("btn-rescan").addEventListener("click", function () { doCleanScan(seq); });
      return;
    }

    var allChecked = targets.every(function (t) { return state.cleanSelection.has(t.id); });
    var rows = targets.map(function (t) {
      var res = state.cleanResults[t.id];
      var resHtml = res ?
        '<span class="' + (res.ok ? "ok-text" : "err-text") + ' small">' +
        esc(res.ok ? fmtMb(res.freed_mb) + " libérés" : (res.message || "Échec")) + "</span>" : "";
      return "<tr>" +
        '<td><input type="checkbox" class="clean-check" data-id="' + esc(t.id) + '"' +
        (state.cleanSelection.has(t.id) ? " checked" : "") + "></td>" +
        "<td>" + esc(t.name) + "</td>" +
        '<td><span class="mono mono-inline clean-path" title="' + esc(t.path) + '">' + esc(t.path) + "</span></td>" +
        '<td class="mono">' + esc(t.files) + "</td>" +
        '<td class="mono">' + esc(fmtMb(t.size_mb)) + "</td>" +
        "<td>" + resHtml + "</td></tr>";
    }).join("");

    area.innerHTML =
      '<table class="table"><thead><tr>' +
      '<th><input type="checkbox" id="clean-all"' + (allChecked ? " checked" : "") + "></th>" +
      "<th>Cible</th><th>Chemin</th><th>Fichiers</th><th>Taille</th><th>Résultat</th>" +
      "</tr></thead><tbody>" + rows + "</tbody></table>" +
      '<div class="clean-foot">' +
      '<span class="muted" id="clean-total"></span>' +
      '<span class="spacer"></span>' +
      '<button class="btn" id="btn-rescan" type="button">' + icon("refresh") + " Réanalyser</button>" +
      '<button class="btn btn-primary" id="btn-clean" type="button"></button>' +
      "</div>";

    byId("btn-rescan").addEventListener("click", function () { doCleanScan(seq); });
    byId("btn-clean").addEventListener("click", onClean);
    byId("clean-all").addEventListener("change", function (e) {
      if (e.target.checked) {
        state.cleanSelection = new Set(targets.map(function (t) { return t.id; }));
      } else {
        state.cleanSelection = new Set();
      }
      buildCleanArea(seq);
    });
    $all(".clean-check", area).forEach(function (cb) {
      cb.addEventListener("change", function () {
        if (cb.checked) { state.cleanSelection.add(cb.dataset.id); } else { state.cleanSelection.delete(cb.dataset.id); }
        updateCleanTotals();
      });
    });
    updateCleanTotals();
  }

  function updateCleanTotals() {
    var targets = state.cleanTargets || [];
    var total = 0;
    var n = 0;
    targets.forEach(function (t) {
      if (state.cleanSelection.has(t.id)) { total += t.size_mb || 0; n++; }
    });
    var label = byId("clean-total");
    if (label) { label.textContent = "Total sélectionné : " + fmtMb(total); }
    var btn = byId("btn-clean");
    if (btn) {
      btn.textContent = "Nettoyer (" + n + ")";
      btn.disabled = n === 0;
    }
  }

  async function doCleanScan(seq) {
    state.cleanScanning = true;
    state.cleanResults = {};
    buildCleanArea(seq);
    try {
      var res = await api("/api/clean/scan");
      state.cleanTargets = res.targets || [];
      state.cleanSelection = new Set(state.cleanTargets.map(function (t) { return t.id; }));
    } catch (e) {
      state.cleanTargets = state.cleanTargets || null;
    }
    state.cleanScanning = false;
    if (alive(seq) && currentRoute() === "/clean") { buildCleanArea(seq); }
  }

  function onClean() {
    var ids = Array.from(state.cleanSelection);
    if (!ids.length) { return; }
    openModal({
      title: "Confirmer le nettoyage",
      bodyHtml: "<p>Les fichiers des " + ids.length + " cible" + (ids.length > 1 ? "s" : "") +
        " sélectionnée" + (ids.length > 1 ? "s" : "") + " seront définitivement supprimés.</p>",
      confirmLabel: "Nettoyer",
      danger: true,
      onConfirm: async function () {
        var btn = byId("btn-clean");
        setBusy(btn, "Nettoyage…");
        try {
          var res = await api("/api/clean", { body: { ids: ids } });
          var results = res.results || [];
          var freed = 0;
          results.forEach(function (r) {
            state.cleanResults[r.id] = r;
            freed += r.freed_mb || 0;
          });
          showBanner("Nettoyage terminé : " + fmtMb(freed) + " libérés.", "ok");
        } catch (e) { /* bandeau déjà affiché */ }
        if (currentRoute() === "/clean") { buildCleanArea(renderSeq); }
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Page Assistant                                                      */
  /* ------------------------------------------------------------------ */

  function defaultProviderOf(data) {
    var dp = data && data.default_provider;
    if (typeof dp === "string") { return dp; }
    if (dp && typeof dp === "object" && typeof dp.ai_provider === "string") { return dp.ai_provider; }
    return null;
  }

  async function renderAssistant(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">Assistant</h1>' +
      '<p class="page-sub">Un assistant qui connaît votre matériel, votre profil et vos optimisations.</p>' +
      '<div id="assistant-area"><div class="loading-line">Vérification des clés API…</div></div>';

    try {
      state.aiKeys = await api("/api/ai/keys");
    } catch (e) {
      if (alive(seq) && byId("assistant-area")) {
        byId("assistant-area").innerHTML = '<p class="muted small">Assistant indisponible pour le moment.</p>';
      }
      return;
    }
    if (!alive(seq)) { return; }

    var configured = ((state.aiKeys && state.aiKeys.keys) || []).filter(function (k) { return k.configured; });
    var area = byId("assistant-area");

    if (!configured.length) {
      area.innerHTML = '<div class="card empty-state">' + icon("alert") +
        '<p class="empty-title">Aucune clé API configurée</p>' +
        "<p>Ajoutez une clé (Groq propose une clé gratuite) pour activer l'assistant.</p>" +
        '<button class="btn btn-primary" id="btn-goto-settings" type="button">Ouvrir les réglages</button></div>';
      byId("btn-goto-settings").addEventListener("click", function () { window.location.hash = "#/settings"; });
      return;
    }

    var def = defaultProviderOf(state.aiKeys);
    var configuredIds = configured.map(function (k) { return k.provider; });
    if (!state.chatProvider || configuredIds.indexOf(state.chatProvider) === -1) {
      state.chatProvider = configuredIds.indexOf(def) !== -1 ? def : configuredIds[0];
    }

    area.innerHTML =
      '<div class="chat-wrap">' +
      '<div class="chat-top">' +
      "<label>Fournisseur " +
      '<select class="input" id="chat-provider">' + configured.map(function (k) {
        return '<option value="' + esc(k.provider) + '"' + (k.provider === state.chatProvider ? " selected" : "") + ">" +
          esc(providerName(k.provider)) + "</option>";
      }).join("") + "</select></label>" +
      '<button class="btn btn-ghost btn-sm" id="chat-clear" type="button">Effacer la conversation</button>' +
      "</div>" +
      '<div class="chat-messages" id="chat-messages"></div>' +
      '<div class="chat-input-row">' +
      '<textarea class="input" id="chat-input" rows="1" placeholder="Votre question sur l\'optimisation…"></textarea>' +
      '<button class="btn btn-primary" id="chat-send" type="button">' + icon("send") + " Envoyer</button>" +
      "</div></div>";

    byId("chat-provider").addEventListener("change", function (e) { state.chatProvider = e.target.value; });
    byId("chat-clear").addEventListener("click", function () {
      state.chat = [];
      state.chatError = null;
      renderChatMessages();
    });
    byId("chat-send").addEventListener("click", sendChat);
    byId("chat-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChat();
      }
    });
    renderChatMessages();
  }

  function formatChatText(text) {
    var safe = esc(text);
    safe = safe.replace(/`([^`]+)`/g, '<code class="inline">$1</code>');
    var paras = safe.split(/\n{2,}/).map(function (p) {
      return "<p>" + p.replace(/\n/g, "<br>") + "</p>";
    });
    return paras.join("");
  }

  function renderChatMessages() {
    var box = byId("chat-messages");
    if (!box) { return; }
    var html = "";
    if (!state.chat.length && !state.chatBusy && !state.chatError) {
      html = '<div class="chat-empty">Aucun message pour l\'instant.<br>' +
        '<span class="small">Exemple : « Quels réglages pour gagner des FPS sur ma machine ? »</span></div>';
    } else {
      html = state.chat.map(function (m) {
        return '<div class="msg ' + (m.role === "user" ? "msg-user" : "msg-assistant") + '">' +
          formatChatText(m.content) + "</div>";
      }).join("");
      if (state.chatBusy) { html += '<div class="msg-pending">L\'assistant rédige une réponse…</div>'; }
      if (state.chatError) { html += '<div class="msg-error">' + esc(state.chatError) + "</div>"; }
    }
    box.innerHTML = html;
    box.scrollTop = box.scrollHeight;
    var send = byId("chat-send");
    if (send) { send.disabled = state.chatBusy; }
  }

  async function sendChat() {
    if (state.chatBusy) { return; }
    var input = byId("chat-input");
    var text = input ? input.value.trim() : "";
    if (!text) { return; }
    input.value = "";
    state.chat.push({ role: "user", content: text });
    state.chatError = null;
    state.chatBusy = true;
    renderChatMessages();
    try {
      var res = await api("/api/ai/chat", { body: { messages: state.chat, provider: state.chatProvider } });
      if (res.ok && res.reply) {
        state.chat.push({ role: "assistant", content: res.reply });
      } else {
        state.chatError = res.message || "Réponse indisponible.";
      }
    } catch (e) {
      state.chatError = "Erreur réseau : la question n'a pas pu être envoyée.";
    }
    state.chatBusy = false;
    renderChatMessages();
    if (input) { input.focus(); }
  }

  /* ------------------------------------------------------------------ */
  /* Page Réglages                                                       */
  /* ------------------------------------------------------------------ */

  async function renderSettings(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">Réglages</h1>' +
      '<p class="page-sub">Clés API, fournisseur par défaut, apparence et questionnaire.</p>' +
      '<div id="settings-area"><div class="loading-line">Chargement…</div></div>';

    try {
      state.aiKeys = await api("/api/ai/keys");
    } catch (e) {
      state.aiKeys = state.aiKeys || { keys: [] };
    }
    if (!alive(seq)) { return; }
    buildSettingsArea(seq);
  }

  function buildSettingsArea(seq) {
    var area = byId("settings-area");
    if (!area) { return; }
    var keys = {};
    ((state.aiKeys && state.aiKeys.keys) || []).forEach(function (k) { keys[k.provider] = k; });
    var configured = PROVIDERS_META.filter(function (p) { return keys[p.id] && keys[p.id].configured; });
    var def = defaultProviderOf(state.aiKeys);
    var st = state.status || {};

    var keyRows = PROVIDERS_META.map(function (p) {
      var k = keys[p.id] || { configured: false, masked: null };
      var status = k.configured ?
        'Configurée' + (k.masked ? ' · <span class="mono mono-inline">' + esc(k.masked) + "</span>" : "") :
        "Non configurée";
      return '<div class="settings-row">' +
        '<div class="set-info"><div class="set-name">' + esc(p.name) + "</div>" +
        '<div class="set-status">' + status + "</div>" +
        (p.note ? '<div class="set-note">' + p.note + "</div>" : "") +
        "</div>" +
        '<div class="set-controls">' +
        '<input class="input" type="password" id="key-in-' + esc(p.id) + '" placeholder="Clé API" autocomplete="off">' +
        '<button class="btn btn-sm" data-save-key="' + esc(p.id) + '" type="button">Enregistrer</button>' +
        (k.configured ? '<button class="btn btn-sm btn-danger" data-del-key="' + esc(p.id) + '" type="button">Supprimer</button>' : "") +
        "</div></div>";
    }).join("");

    var defSelect = configured.length ?
      '<select class="input" id="default-provider">' + configured.map(function (p) {
        return '<option value="' + esc(p.id) + '"' + (p.id === def ? " selected" : "") + ">" + esc(p.name) + "</option>";
      }).join("") + "</select>" :
      '<span class="muted small">Aucune clé configurée pour l\'instant.</span>';

    area.innerHTML =
      '<div class="group-label">Clés API</div>' +
      '<div class="card">' +
      '<p class="muted small" style="margin-top:0">Les clés sont chiffrées localement et ne quittent jamais cette machine, sauf vers le fournisseur que vous choisissez.</p>' +
      keyRows + "</div>" +

      '<div class="group-label">Assistant</div>' +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">Fournisseur par défaut</div>' +
      '<div class="set-status">Utilisé quand aucun fournisseur n\'est précisé.</div></div>' +
      '<div class="set-controls">' + defSelect + "</div></div></div>" +

      '<div class="group-label">Apparence</div>' +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">Thème</div>' +
      '<div class="set-status">Clair par défaut, sombre doux disponible.</div></div>' +
      '<div class="set-controls"><div class="seg" data-seg="theme">' +
      '<button type="button" data-theme="light">Clair</button>' +
      '<button type="button" data-theme="dark">Sombre</button>' +
      "</div></div></div></div>" +

      '<div class="group-label">Questionnaire</div>' +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">Profil d\'optimisation</div>' +
      '<div class="set-status">' + (state.profile ? "Profil actuel : " + esc(state.profile.label || state.profile.id) : "Aucun profil pour l'instant.") + "</div></div>" +
      '<div class="set-controls"><button class="btn btn-sm" id="btn-redo-quiz" type="button">Refaire le questionnaire</button></div>' +
      "</div></div>" +

      '<div class="group-label">À propos</div>' +
      '<div class="card">' +
      "<p style=\"margin-top:0\"><strong>Overdrive</strong>" + (st.version ? " v" + esc(st.version) : "") +
      (st.platform ? ' · <span class="mono mono-inline">' + esc(st.platform) + "</span>" : "") +
      (st.is_windows ? (st.is_admin ? ' · <span class="badge badge-green">administrateur</span>' : ' · <span class="badge badge-yellow">non administrateur</span>') : "") +
      "</p>" +
      '<p class="muted small" style="margin-bottom:0">Les clés API sont chiffrées localement et ne quittent jamais cette machine, sauf vers l\'API du fournisseur d\'IA sélectionné. Les optimisations appliquées sont journalisées et réversibles depuis la page Optimisations.</p>' +
      "</div>";

    /* Liaisons. */
    $all("[data-save-key]", area).forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var provider = btn.dataset.saveKey;
        var input = byId("key-in-" + provider);
        var key = input ? input.value.trim() : "";
        if (!key) {
          showBanner("Saisissez une clé API avant d'enregistrer.", "error");
          return;
        }
        setBusy(btn, "Enregistrement…");
        try {
          var saveRes = await api("/api/ai/keys", { body: { provider: provider, key: key } });
          if (!saveRes || saveRes.ok === false) {
            showBanner((saveRes && saveRes.message) || "Échec de l'enregistrement de la clé.", "error");
            clearBusy(btn);
            return;
          }
          showBanner("Clé " + providerName(provider) + " enregistrée.", "ok");
          state.aiKeys = await api("/api/ai/keys");
          if (currentRoute() === "/settings") { buildSettingsArea(seq); return; }
        } catch (e) { /* bandeau déjà affiché */ }
        clearBusy(btn);
      });
    });

    $all("[data-del-key]", area).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var provider = btn.dataset.delKey;
        openModal({
          title: "Supprimer la clé " + providerName(provider),
          bodyHtml: "<p>La clé sera supprimée du stockage chiffré local.</p>",
          confirmLabel: "Supprimer",
          danger: true,
          onConfirm: async function () {
            try {
              var delRes = await api("/api/ai/keys/" + encodeURIComponent(provider), { method: "DELETE" });
              if (!delRes || delRes.ok === false) {
                showBanner((delRes && delRes.message) || "Échec de la suppression de la clé.", "error");
              } else {
                showBanner("Clé " + providerName(provider) + " supprimée.", "ok");
              }
              state.aiKeys = await api("/api/ai/keys");
            } catch (e) { /* bandeau déjà affiché */ }
            if (currentRoute() === "/settings") { buildSettingsArea(seq); }
          }
        });
      });
    });

    var defSel = byId("default-provider");
    if (defSel) {
      defSel.addEventListener("change", async function () {
        try {
          await api("/api/ai/default", { body: { provider: defSel.value } });
          showBanner("Fournisseur par défaut : " + providerName(defSel.value) + ".", "ok");
        } catch (e) { /* bandeau déjà affiché */ }
      });
    }

    $all(".seg[data-seg='theme'] button", area).forEach(function (b) {
      b.addEventListener("click", function () { setTheme(b.dataset.theme); });
    });
    updateThemeLabel();

    byId("btn-redo-quiz").addEventListener("click", function () { openQuiz(false); });
  }

  /* ------------------------------------------------------------------ */
  /* QCM premier lancement (overlay plein écran)                         */
  /* ------------------------------------------------------------------ */

  async function openQuiz(firstRun) {
    var data;
    try {
      data = await api("/api/quiz");
    } catch (e) {
      return;
    }
    state.quiz = {
      questions: (data && data.questions) || [],
      index: 0,
      answers: {},
      firstRun: !!firstRun,
      result: null,
      submitting: false
    };
    if (!state.quiz.questions.length) { return; }
    var root = byId("overlay-root");
    root.hidden = false;
    document.body.style.overflow = "hidden";
    renderQuiz();
  }

  function closeQuiz() {
    var root = byId("overlay-root");
    root.hidden = true;
    root.innerHTML = "";
    document.body.style.overflow = "";
    state.quiz = null;
  }

  function quizAnswered(q) {
    var a = state.quiz.answers[q.id];
    if (q.multi) { return Array.isArray(a) && a.length > 0; }
    return typeof a === "string" && a.length > 0;
  }

  function renderQuiz() {
    var root = byId("overlay-root");
    var quiz = state.quiz;
    if (!root || !quiz) { return; }

    if (quiz.result) {
      renderQuizResult();
      return;
    }

    var total = quiz.questions.length;
    var q = quiz.questions[quiz.index];
    var answer = quiz.answers[q.id];
    var pct = Math.round(((quiz.index + 1) / total) * 100);

    var optionsHtml = (q.options || []).map(function (o) {
      var selected = q.multi ?
        (Array.isArray(answer) && answer.indexOf(o.id) !== -1) :
        answer === o.id;
      var mark = q.multi ?
        '<span class="opt-mark square">' + icon("check") + "</span>" :
        '<span class="opt-mark round"><span class="opt-dot-inner"></span></span>';
      return '<button class="quiz-opt' + (selected ? " selected" : "") + '" data-opt="' + esc(o.id) +
        '" type="button">' + mark + "<span>" + esc(o.label) + "</span></button>";
    }).join("");

    root.innerHTML =
      '<div class="quiz-overlay"><div class="quiz-inner">' +
      '<div class="quiz-head">' +
      '<span class="quiz-brand">' +
      '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/></svg>' +
      "Overdrive</span>" +
      '<span class="quiz-progress">Question ' + (quiz.index + 1) + "/" + total + "</span>" +
      '<button class="btn btn-ghost btn-sm" id="quiz-later" type="button">' +
      (quiz.firstRun ? "Plus tard" : "Annuler") + "</button>" +
      "</div>" +
      '<div class="quiz-bar"><div style="width:' + pct + '%"></div></div>' +
      '<h2 class="quiz-question">' + esc(q.question) + "</h2>" +
      '<p class="quiz-hint">' + (q.multi ? "Plusieurs réponses possibles" : "Une seule réponse") + "</p>" +
      '<div class="quiz-options">' + optionsHtml + "</div>" +
      '<div class="quiz-nav">' +
      '<button class="btn" id="quiz-prev" type="button"' + (quiz.index === 0 ? " disabled" : "") + ">" +
      icon("left") + " Précédent</button>" +
      '<button class="btn btn-primary" id="quiz-next" type="button"' +
      (quizAnswered(q) && !quiz.submitting ? "" : " disabled") + ">" +
      (quiz.submitting ? "Analyse…" : (quiz.index === total - 1 ? "Terminer" : "Suivant " + icon("right"))) +
      "</button></div>" +
      "</div></div>";

    byId("quiz-later").addEventListener("click", closeQuiz);

    $all(".quiz-opt", root).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var optId = btn.dataset.opt;
        if (q.multi) {
          var arr = Array.isArray(quiz.answers[q.id]) ? quiz.answers[q.id].slice() : [];
          var at = arr.indexOf(optId);
          if (at === -1) { arr.push(optId); } else { arr.splice(at, 1); }
          quiz.answers[q.id] = arr;
        } else {
          quiz.answers[q.id] = optId;
        }
        renderQuiz();
      });
    });

    byId("quiz-prev").addEventListener("click", function () {
      if (quiz.index > 0) { quiz.index--; renderQuiz(); }
    });
    byId("quiz-next").addEventListener("click", function () {
      if (!quizAnswered(q) || quiz.submitting) { return; }
      if (quiz.index < total - 1) {
        quiz.index++;
        renderQuiz();
      } else {
        submitQuiz();
      }
    });
  }

  async function submitQuiz() {
    var quiz = state.quiz;
    if (!quiz) { return; }
    quiz.submitting = true;
    renderQuiz();
    try {
      var res = await api("/api/quiz", { body: { answers: quiz.answers } });
      quiz.result = res.profile || null;
      state.profile = quiz.result;
      if (state.status) {
        state.status.first_run = false;
        state.status.profile = quiz.result;
      }
      state.tweakSelectionInit = false;
    } catch (e) {
      quiz.submitting = false;
      if (state.quiz) { renderQuiz(); }
      return;
    }
    quiz.submitting = false;
    renderQuiz();
  }

  function renderQuizResult() {
    var root = byId("overlay-root");
    var quiz = state.quiz;
    if (!root || !quiz || !quiz.result) { return; }
    var p = quiz.result;
    var notes = p.notes || [];

    root.innerHTML =
      '<div class="quiz-overlay"><div class="quiz-inner"><div class="quiz-result">' +
      '<div class="result-check">' + icon("check") + "</div>" +
      "<h2>Profil : " + esc(p.label || p.id) + "</h2>" +
      '<p class="result-desc">' + esc(p.description || "") + "</p>" +
      (notes.length ?
        '<div class="quiz-notes"><div class="quiz-notes-title">Conseils personnalisés</div><ul>' +
        notes.map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("") + "</ul></div>" : "") +
      '<div class="quiz-result-actions">' +
      '<button class="btn btn-primary" id="quiz-goto-tweaks" type="button">Voir mes optimisations</button>' +
      '<button class="btn" id="quiz-close" type="button">Fermer</button>' +
      "</div></div></div></div>";

    byId("quiz-goto-tweaks").addEventListener("click", function () {
      closeQuiz();
      state.pendingProfileSelect = true;
      if (currentRoute() === "/tweaks") { render(); } else { window.location.hash = "#/tweaks"; }
    });
    byId("quiz-close").addEventListener("click", function () {
      closeQuiz();
      render();
    });
  }

  /* ------------------------------------------------------------------ */
  /* Initialisation                                                      */
  /* ------------------------------------------------------------------ */

  async function init() {
    byId("theme-toggle").addEventListener("click", function () {
      setTheme(currentTheme() === "dark" ? "light" : "dark");
    });
    updateThemeLabel();

    window.addEventListener("hashchange", render);
    render();

    try {
      var st = await api("/api/status");
      state.status = st;
      state.profile = st.profile || null;
      var ver = byId("app-version");
      if (ver && st.version) { ver.textContent = "v" + st.version; }
      var stored = null;
      try { stored = localStorage.getItem("overdrive-theme"); } catch (e) { /* stockage indisponible */ }
      if (!stored && (st.theme === "dark" || st.theme === "light")) { applyTheme(st.theme); }
      render();
      if (st.first_run) { openQuiz(true); }
    } catch (e) { /* bandeau déjà affiché, l'interface reste utilisable */ }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
