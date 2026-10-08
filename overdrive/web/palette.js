/* ==========================================================================
   Overdrive — palette de commandes Ctrl+K (palette.js)

   Autonome : fonctionne sans modification d'app.js. Par défaut elle propose
   - les pages (lues dans les liens .nav-item[data-route] de la barre latérale),
   - les 5 thèmes (application locale : data-theme + localStorage),
   - les 3 niveaux d'animation (via window.OverdriveMotion.setLevel).

   app.js peut ajouter / remplacer des commandes :
     window.OverdrivePalette.register([{
       id: "action:boost",            // unique ; même id = remplace (y compris un défaut)
       title: "Boost",                // chaîne ou fonction () => chaîne (i18n dynamique)
       subtitle: "…",                 // facultatif (chaîne ou fonction)
       section: "actions",            // actions | pages | theme | motion | lang | autre
       sectionLabel: "…",             // facultatif, pour une section personnalisée
       keywords: "optimiser fps",     // facultatif (chaîne ou fonction)
       icon: "<svg …>",               // facultatif (HTML d'une icône)
       shortcut: ["Ctrl", "B"],       // facultatif (affiché en <kbd>)
       active: () => true,            // facultatif : coche « actuel »
       run: () => { … }               // obligatoire
     }]);
     window.OverdrivePalette.open("thème");   // ouverture (requête facultative)

   Clavier : Ctrl+K (ou ⌘K) ouvre/ferme, ↑ ↓ PageUp PageDown, Entrée, Échap.
   ========================================================================== */
(function () {
  "use strict";

  if (window.OverdrivePalette) { return; }

  var doc = document;
  var root = doc.documentElement;

  var I18N = {
    fr: {
      search_btn: "Rechercher…",
      search_aria: "Rechercher une page ou une action (Ctrl+K)",
      dialog: "Palette de commandes",
      placeholder: "Rechercher une page, une action, un thème…",
      empty: "Aucun résultat pour « {q} »",
      hint_nav: "naviguer",
      hint_open: "ouvrir",
      hint_close: "fermer",
      esc: "Échap",
      sec_actions: "Actions",
      sec_pages: "Pages",
      sec_theme: "Thème",
      sec_motion: "Animations",
      sec_lang: "Langue",
      sec_other: "Autres",
      go_to: "Aller à la page",
      theme_midnight: "Midnight",
      theme_ocean: "Océan",
      theme_emerald: "Émeraude",
      theme_rose: "Rose",
      theme_daylight: "Clair",
      theme_sub: "Thème",
      motion_max: "Animations maximales",
      motion_reduced: "Animations réduites",
      motion_off: "Animations désactivées",
      motion_max_sub: "3D, halos, compteurs",
      motion_reduced_sub: "Fondus courts uniquement",
      motion_off_sub: "Aucun mouvement",
      current: "actuel"
    },
    en: {
      search_btn: "Search…",
      search_aria: "Search a page or an action (Ctrl+K)",
      dialog: "Command palette",
      placeholder: "Search a page, an action, a theme…",
      empty: "No results for “{q}”",
      hint_nav: "navigate",
      hint_open: "open",
      hint_close: "close",
      esc: "Esc",
      sec_actions: "Actions",
      sec_pages: "Pages",
      sec_theme: "Theme",
      sec_motion: "Animations",
      sec_lang: "Language",
      sec_other: "Other",
      go_to: "Go to page",
      theme_midnight: "Midnight",
      theme_ocean: "Ocean",
      theme_emerald: "Emerald",
      theme_rose: "Rose",
      theme_daylight: "Light",
      theme_sub: "Theme",
      motion_max: "Maximum animations",
      motion_reduced: "Reduced animations",
      motion_off: "Animations off",
      motion_max_sub: "3D, glows, counters",
      motion_reduced_sub: "Short fades only",
      motion_off_sub: "No motion at all",
      current: "current"
    }
  };

  var SECTION_ORDER = ["actions", "pages", "theme", "motion", "lang"];

  var THEMES = [
    { id: "midnight", key: "theme_midnight", bg: "#0a0a0f", grad: "linear-gradient(135deg,#8b5cf6,#3b82f6)" },
    { id: "midnight-ocean", key: "theme_ocean", bg: "#090c12", grad: "linear-gradient(135deg,#3b82f6,#22b8cf)" },
    { id: "midnight-emerald", key: "theme_emerald", bg: "#090d0c", grad: "linear-gradient(135deg,#22b58a,#36c2b0)" },
    { id: "midnight-rose", key: "theme_rose", bg: "#0d0a0d", grad: "linear-gradient(135deg,#e85a77,#a66be8)" },
    { id: "daylight", key: "theme_daylight", bg: "#f7f7f9", grad: "linear-gradient(135deg,#6d4aff,#2563eb)" }
  ];

  var ICONS = {
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7.5"/><path d="m20.5 20.5-4.2-4.2"/></svg>',
    sparkles: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/></svg>',
    feather: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12h4l3-7 4 14 3-7h4"/></svg>',
    pause: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M10 9v6"/><path d="M14 9v6"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    dot: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="12" cy="12" r="3"/></svg>'
  };

  var registered = [];           /* commandes fournies par l'app */
  var el = null, input = null, list = null, pill = null, empty = null;
  var isOpenFlag = false, active = 0, results = [], lastFocus = null, hideTimer = null;
  var pillPlaced = false;

  /* ------------------------------------------------------------------ */
  /* Utilitaires                                                         */
  /* ------------------------------------------------------------------ */

  function lang() {
    return String(root.lang || "fr").slice(0, 2).toLowerCase() === "en" ? "en" : "fr";
  }

  function t(key) {
    var d = I18N[lang()] || I18N.fr;
    return Object.prototype.hasOwnProperty.call(d, key) ? d[key] : (I18N.fr[key] || key);
  }

  function esc(s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function val(v) {
    try { return typeof v === "function" ? String(v() || "") : String(v || ""); } catch (e) { return ""; }
  }

  function motionLevel() { return root.getAttribute("data-motion") || "max"; }

  /** Normalise (minuscules, sans accents) en gardant la correspondance des positions. */
  function normMap(str) {
    var s = "", map = [];
    for (var i = 0; i < str.length; i++) {
      var n = str.charAt(i).normalize ? str.charAt(i).normalize("NFD").replace(/[̀-ͯ]/g, "") : str.charAt(i);
      n = n.toLowerCase();
      for (var j = 0; j < n.length; j++) { s += n.charAt(j); map.push(i); }
    }
    return { s: s, map: map };
  }

  function norm(str) { return normMap(String(str || "")).s; }

  /** Correspondance approximative : sous-chaîne d'abord, sinon sous-séquence. */
  function fuzzy(q, text) {
    var tm = normMap(text);
    var s = tm.s;
    if (!q) { return { score: 0, pos: [] }; }
    var idx = s.indexOf(q);
    if (idx >= 0) {
      var pos = [];
      for (var k = idx; k < idx + q.length; k++) { pos.push(tm.map[k]); }
      var boundary = idx === 0 || /[\s\-:/·(]/.test(s.charAt(idx - 1));
      return { score: 120 - Math.min(idx, 40) + (boundary ? 60 : 0) + (q.length === s.length ? 40 : 0), pos: pos };
    }
    var qq = q.replace(/\s+/g, "");
    var ti = 0, score = 0, streak = 0, prev = -2, out = [];
    for (var i = 0; i < qq.length; i++) {
      var f = s.indexOf(qq.charAt(i), ti);
      if (f < 0) { return null; }
      if (f === prev + 1) { streak++; score += 3 + streak; } else { streak = 0; score += 1; }
      if (f === 0 || /[\s\-:/·(]/.test(s.charAt(f - 1))) { score += 5; }
      out.push(tm.map[f]);
      prev = f;
      ti = f + 1;
    }
    return { score: score - (out[out.length - 1] - out[0]) * 0.25, pos: out };
  }

  function highlight(text, pos) {
    if (!pos || !pos.length) { return esc(text); }
    var set = {};
    pos.forEach(function (p) { set[p] = 1; });
    var html = "", open = false;
    for (var i = 0; i < text.length; i++) {
      var m = !!set[i];
      if (m && !open) { html += "<mark>"; open = true; }
      if (!m && open) { html += "</mark>"; open = false; }
      html += esc(text.charAt(i));
    }
    if (open) { html += "</mark>"; }
    return html;
  }

  function sectionLabel(cmd) {
    var s = cmd.section || "other";
    if (SECTION_ORDER.indexOf(s) >= 0) { return t("sec_" + s); }
    return val(cmd.sectionLabel) || (s === "other" ? t("sec_other") : s);
  }

  function sectionRank(s) {
    var i = SECTION_ORDER.indexOf(s || "other");
    return i >= 0 ? i : SECTION_ORDER.length;
  }

  /* ------------------------------------------------------------------ */
  /* Commandes par défaut                                                */
  /* ------------------------------------------------------------------ */

  function go(href) {
    if (window.OverdriveMotion && typeof window.OverdriveMotion.navigate === "function") {
      window.OverdriveMotion.navigate(href);
    } else {
      window.location.hash = href;
    }
  }

  function applyTheme(id) {
    function apply() {
      root.setAttribute("data-theme", id);
      try { localStorage.setItem("overdrive-theme", id); } catch (e) { /* stockage indisponible */ }
    }
    if (window.OverdriveMotion && typeof window.OverdriveMotion.transition === "function") {
      window.OverdriveMotion.transition(apply, "theme");
    } else {
      apply();
    }
    try { window.dispatchEvent(new CustomEvent("overdrive:theme", { detail: { theme: id } })); } catch (e) { /* ancien moteur */ }
  }

  function setMotion(level) {
    if (window.OverdriveMotion && typeof window.OverdriveMotion.setLevel === "function") {
      window.OverdriveMotion.setLevel(level);
    } else {
      root.setAttribute("data-motion", level);
      try { localStorage.setItem("overdrive-motion", level); } catch (e) { /* stockage indisponible */ }
    }
    try { window.dispatchEvent(new CustomEvent("overdrive:motion", { detail: { motion: level } })); } catch (e) { /* ancien moteur */ }
  }

  function currentTheme() {
    var th = root.getAttribute("data-theme") || "midnight";
    if (th === "dark") { return "midnight"; }
    if (th === "light") { return "daylight"; }
    return th;
  }

  function defaultCommands() {
    var cmds = [];
    Array.prototype.forEach.call(doc.querySelectorAll("#sidebar .nav-item[data-route]"), function (a) {
      var label = a.querySelector("span");
      var svg = a.querySelector("svg");
      var href = a.getAttribute("href") || ("#" + a.getAttribute("data-route"));
      cmds.push({
        id: "nav:" + a.getAttribute("data-route"),
        title: (label ? label.textContent : a.textContent).trim(),
        subtitle: t("go_to"),
        section: "pages",
        keywords: a.getAttribute("data-route") + " page",
        icon: svg ? svg.outerHTML : ICONS.dot,
        active: function () { return a.classList.contains("active"); },
        run: function () { go(href); }
      });
    });
    THEMES.forEach(function (th) {
      cmds.push({
        id: "theme:" + th.id,
        title: t(th.key),
        section: "theme",
        keywords: "theme thème couleur color apparence appearance " + th.id +
          (th.id === "daylight" ? " clair light jour" : " sombre dark nuit"),
        swatch: th,
        active: function () { return currentTheme() === th.id; },
        run: function () { applyTheme(th.id); }
      });
    });
    [["max", "sparkles"], ["reduced", "feather"], ["off", "pause"]].forEach(function (m) {
      cmds.push({
        id: "motion:" + m[0],
        title: t("motion_" + m[0]),
        subtitle: t("motion_" + m[0] + "_sub"),
        section: "motion",
        keywords: "animation animations motion mouvement effets effects " + m[0],
        icon: ICONS[m[1]],
        active: function () { return motionLevel() === m[0]; },
        run: function () { setMotion(m[0]); }
      });
    });
    return cmds;
  }

  function allCommands() {
    var map = {}, order = [];
    defaultCommands().concat(registered).forEach(function (c) {
      if (!c || !c.id) { return; }
      if (!map[c.id]) { order.push(c.id); }
      map[c.id] = c;
    });
    return order.map(function (id) { return map[id]; });
  }

  /* ------------------------------------------------------------------ */
  /* Construction et rendu                                               */
  /* ------------------------------------------------------------------ */

  function build() {
    if (el) { return; }
    el = doc.createElement("div");
    el.className = "od-pal-overlay";
    el.hidden = true;
    el.innerHTML =
      '<div class="od-pal" role="dialog" aria-modal="true">' +
      '<div class="od-pal-search">' + ICONS.search +
      '<input class="od-pal-input" type="text" role="combobox" aria-expanded="true" aria-controls="od-pal-list" ' +
      'aria-autocomplete="list" autocomplete="off" spellcheck="false">' +
      "<kbd class=\"od-pal-esc\"></kbd></div>" +
      '<div class="od-pal-list" id="od-pal-list" role="listbox"></div>' +
      '<div class="od-pal-empty" hidden></div>' +
      '<div class="od-pal-foot">' +
      '<span><kbd>↑</kbd><kbd>↓</kbd><span class="od-pal-h-nav"></span></span>' +
      '<span><kbd>↵</kbd><span class="od-pal-h-open"></span></span>' +
      '<span><kbd class="od-pal-esc"></kbd><span class="od-pal-h-close"></span></span>' +
      '<span class="od-pal-brand">Overdrive</span></div>' +
      "</div>";
    doc.body.appendChild(el);
    input = el.querySelector(".od-pal-input");
    list = el.querySelector(".od-pal-list");
    empty = el.querySelector(".od-pal-empty");

    el.addEventListener("mousedown", function (e) {
      if (e.target === el) { e.preventDefault(); close(); }
    });
    input.addEventListener("input", function () { active = 0; renderList(false); });
    input.addEventListener("keydown", onInputKey);
    list.addEventListener("pointermove", function (e) {
      var item = e.target && e.target.closest ? e.target.closest(".od-pal-item") : null;
      if (item) {
        var idx = Number(item.getAttribute("data-idx"));
        if (idx !== active) { setActive(idx, false); }
      }
    });
    list.addEventListener("click", function (e) {
      var item = e.target && e.target.closest ? e.target.closest(".od-pal-item") : null;
      if (item) { runAt(Number(item.getAttribute("data-idx"))); }
    });
    list.addEventListener("mousedown", function (e) { e.preventDefault(); });   /* garde le focus dans le champ */
    translateStatic();
  }

  function translateStatic() {
    if (el) {
      el.querySelector(".od-pal").setAttribute("aria-label", t("dialog"));
      input.setAttribute("placeholder", t("placeholder"));
      input.setAttribute("aria-label", t("placeholder"));
      Array.prototype.forEach.call(el.querySelectorAll(".od-pal-esc"), function (k) { k.textContent = t("esc"); });
      el.querySelector(".od-pal-h-nav").textContent = t("hint_nav");
      el.querySelector(".od-pal-h-open").textContent = t("hint_open");
      el.querySelector(".od-pal-h-close").textContent = t("hint_close");
    }
    Array.prototype.forEach.call(doc.querySelectorAll("[data-od-i18n]"), function (n) {
      n.textContent = t(n.getAttribute("data-od-i18n"));
    });
    Array.prototype.forEach.call(doc.querySelectorAll("[data-od-i18n-aria]"), function (n) {
      var v = t(n.getAttribute("data-od-i18n-aria"));
      n.setAttribute("aria-label", v);
      n.setAttribute("title", v);
    });
  }

  function compute() {
    var q = norm(input ? input.value : "").trim();
    var cmds = allCommands();
    var out = [];
    cmds.forEach(function (c, i) {
      var title = val(c.title);
      if (!title) { return; }
      var r = { cmd: c, title: title, pos: [], score: 0, order: i };
      if (q) {
        var m = fuzzy(q, title);
        if (m) {
          r.score = m.score + 10;
          r.pos = m.pos;
        } else {
          var hay = [val(c.subtitle), val(c.keywords), sectionLabel(c)].join(" ");
          var words = q.split(/\s+/), total = 0, ok = true;
          for (var w = 0; w < words.length && ok; w++) {
            var mt = fuzzy(words[w], title), mh = fuzzy(words[w], hay);
            var best = Math.max(mt ? mt.score : -1, mh && norm(hay).indexOf(words[w]) >= 0 ? mh.score * 0.6 : -1);
            if (best < 0) { ok = false; } else { total += best; }
          }
          if (!ok) { return; }
          r.score = total * 0.7;
        }
      }
      out.push(r);
    });
    if (q) {
      out.sort(function (a, b) { return (b.score - a.score) || (a.order - b.order); });
    } else {
      out.sort(function (a, b) {
        return (sectionRank(a.cmd.section) - sectionRank(b.cmd.section)) || (a.order - b.order);
      });
    }
    return { q: q, items: out };
  }

  function iconHtml(c) {
    if (c.swatch) {
      return '<span class="od-pal-swatch" style="background:' + esc(c.swatch.grad) + ';box-shadow:inset 0 0 0 3px ' +
        esc(c.swatch.bg) + ',0 0 0 1px rgba(127,127,140,.35)"></span>';
    }
    return c.icon ? String(c.icon) : ICONS.dot;
  }

  function isActiveCmd(c) {
    try { return typeof c.active === "function" ? !!c.active() : false; } catch (e) { return false; }
  }

  function renderList(opening) {
    if (!list) { return; }
    var res = compute();
    results = res.items;
    if (active >= results.length) { active = Math.max(0, results.length - 1); }
    var html = '<div class="od-pal-pill" aria-hidden="true"></div>';
    var lastSection = null;
    results.forEach(function (r, i) {
      var c = r.cmd;
      if (!res.q && c.section !== lastSection) {
        html += '<div class="od-pal-section" role="presentation">' + esc(sectionLabel(c)) + "</div>";
        lastSection = c.section;
      }
      var keys = Array.isArray(c.shortcut) && c.shortcut.length ?
        '<span class="od-pal-keys">' + c.shortcut.map(function (k) { return "<kbd>" + esc(k) + "</kbd>"; }).join("") + "</span>" : "";
      var tag = res.q ? '<span class="od-pal-tag">' + esc(sectionLabel(c)) + "</span>" : "";
      var check = isActiveCmd(c) ? '<span class="od-pal-check" title="' + esc(t("current")) + '">' + ICONS.check + "</span>" : "";
      var sub = val(c.subtitle);
      html += '<div class="od-pal-item' + (opening && i < 10 ? " od-pal-in" : "") + '" role="option" id="od-pal-opt-' + i +
        '" data-idx="' + i + '" aria-selected="false"' + (opening && i < 10 ? ' style="--i:' + i + '"' : "") + ">" +
        '<span class="od-pal-ic">' + iconHtml(c) + "</span>" +
        '<span class="od-pal-text"><span class="od-pal-title">' + highlight(r.title, r.pos) + "</span>" +
        (sub ? '<span class="od-pal-sub">' + esc(sub) + "</span>" : "") + "</span>" +
        check + tag + keys + "</div>";
    });
    list.innerHTML = html;
    pill = list.querySelector(".od-pal-pill");
    pillPlaced = false;
    var q = input.value.trim();
    empty.hidden = results.length > 0;
    list.hidden = results.length === 0;
    if (!results.length) { empty.textContent = t("empty").replace("{q}", q); }
    setActive(active, true);
  }

  function setActive(idx, scroll) {
    if (!results.length || !list) { if (pill) { pill.style.opacity = "0"; } input.removeAttribute("aria-activedescendant"); return; }
    active = (idx + results.length) % results.length;
    var prev = list.querySelector(".od-pal-item.is-active");
    if (prev) { prev.classList.remove("is-active"); prev.setAttribute("aria-selected", "false"); }
    var item = list.querySelector('.od-pal-item[data-idx="' + active + '"]');
    if (!item) { return; }
    item.classList.add("is-active");
    item.setAttribute("aria-selected", "true");
    input.setAttribute("aria-activedescendant", item.id);
    if (pill) {
      var instant = !pillPlaced;
      if (instant) { pill.classList.add("od-noanim"); }
      pill.style.height = item.offsetHeight + "px";
      pill.style.transform = "translateY(" + item.offsetTop + "px)";
      pill.style.opacity = "1";
      if (instant) { void pill.offsetWidth; pill.classList.remove("od-noanim"); }
      pillPlaced = true;
    }
    if (scroll) {
      var top = item.offsetTop, bottom = top + item.offsetHeight;
      var head = 34;
      if (top - head < list.scrollTop) { list.scrollTop = Math.max(0, top - head); }
      else if (bottom + 8 > list.scrollTop + list.clientHeight) { list.scrollTop = bottom + 8 - list.clientHeight; }
    }
  }

  function runAt(idx) {
    var r = results[idx];
    if (!r) { return; }
    close();
    try {
      r.cmd.run();
    } catch (e) {
      if (window.console) { console.error("[palette]", e); }
    }
  }

  function onInputKey(e) {
    var k = e.key;
    if (k === "ArrowDown") { e.preventDefault(); setActive(active + 1, true); }
    else if (k === "ArrowUp") { e.preventDefault(); setActive(active - 1, true); }
    else if (k === "PageDown") { e.preventDefault(); setActive(Math.min(results.length - 1, active + 5), true); }
    else if (k === "PageUp") { e.preventDefault(); setActive(Math.max(0, active - 5), true); }
    else if (k === "Home" && e.ctrlKey) { e.preventDefault(); setActive(0, true); }
    else if (k === "End" && e.ctrlKey) { e.preventDefault(); setActive(results.length - 1, true); }
    else if (k === "Enter") { e.preventDefault(); runAt(active); }
    else if (k === "Escape") { e.preventDefault(); e.stopPropagation(); close(); }
    else if (k === "Tab") { e.preventDefault(); setActive(active + (e.shiftKey ? -1 : 1), true); }
  }

  /* ------------------------------------------------------------------ */
  /* Ouverture / fermeture                                               */
  /* ------------------------------------------------------------------ */

  function open(query) {
    build();
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    if (!isOpenFlag) {
      lastFocus = doc.activeElement;
    }
    isOpenFlag = true;
    translateStatic();
    input.value = typeof query === "string" ? query : "";
    active = 0;
    el.hidden = false;
    renderList(true);
    void el.offsetWidth;   /* déclenche la transition d'entrée */
    el.classList.add("is-open");
    try { input.focus({ preventScroll: true }); } catch (e) { input.focus(); }
    if (input.value) { input.select(); }
  }

  function close() {
    if (!el || !isOpenFlag) { return; }
    isOpenFlag = false;
    el.classList.remove("is-open");
    var instant = motionLevel() === "off" || root.hasAttribute("data-motion-paused");
    hideTimer = setTimeout(function () {
      hideTimer = null;
      if (!isOpenFlag) { el.hidden = true; }
    }, instant ? 0 : 230);
    if (lastFocus && lastFocus.isConnected && typeof lastFocus.focus === "function" && lastFocus !== doc.body) {
      try { lastFocus.focus({ preventScroll: true }); } catch (e) { /* focus impossible */ }
    }
    lastFocus = null;
  }

  function toggle() { if (isOpenFlag) { close(); } else { open(); } }

  /* ------------------------------------------------------------------ */
  /* API                                                                 */
  /* ------------------------------------------------------------------ */

  function register(cmds) {
    var arr = Array.isArray(cmds) ? cmds : [cmds];
    var n = 0;
    arr.forEach(function (c) {
      if (!c || typeof c.id !== "string" || typeof c.run !== "function") { return; }
      registered = registered.filter(function (x) { return x.id !== c.id; });
      registered.push(c);
      n++;
    });
    if (isOpenFlag) { renderList(false); }
    return n;
  }

  function unregister(id) {
    var before = registered.length;
    registered = registered.filter(function (x) { return x.id !== id; });
    if (isOpenFlag) { renderList(false); }
    return registered.length !== before;
  }

  window.OverdrivePalette = {
    register: register,
    unregister: unregister,
    open: open,
    close: close,
    toggle: toggle,
    isOpen: function () { return isOpenFlag; }
  };

  /* ------------------------------------------------------------------ */
  /* Initialisation                                                      */
  /* ------------------------------------------------------------------ */

  function init() {
    window.addEventListener("keydown", function (e) {
      var k = String(e.key || "").toLowerCase();
      if ((e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && k === "k") {
        e.preventDefault();
        e.stopPropagation();
        toggle();
      } else if (k === "escape" && isOpenFlag) {
        e.preventDefault();
        close();
      }
    }, true);
    var btn = doc.getElementById("palette-open");
    if (btn) { btn.addEventListener("click", function () { open(); }); }
    translateStatic();
    if (typeof MutationObserver === "function") {
      new MutationObserver(function () { translateStatic(); if (isOpenFlag) { renderList(false); } })
        .observe(root, { attributes: true, attributeFilter: ["lang"] });
    }
  }

  if (doc.body) {
    init();
  } else {
    doc.addEventListener("DOMContentLoaded", init);
  }
})();
