/* ==========================================================================
   Overdrive — intro animée au lancement (intro.js, vague 7)

   Chargé tout en haut de <body> (script bloquant, très léger) : l'overlay est
   posé AVANT le premier affichage de l'interface, puis l'app se construit
   dessous. Une fois par session de l'app (sessionStorage), ~2,4 s, passable
   (clic, touche, Échap). data-motion="off" → aucune intro ; "reduced" →
   composition fixe et simple fondu de 400 ms.

   Chorégraphie : halos aurore qui dérivent, logo (deux anneaux) qui se
   dessine puis cœur qui bat, lettres « OVERDRIVE » en cascade (flou → net),
   balayage lumineux diagonal, barre de progression alimentée par le vrai
   chargement (/api/status + /api/hardware) avec lignes qui défilent ; sortie :
   l'overlay s'agrandit et se fond pendant que le héros de l'accueil entre
   (événement « overdrive:intro-exit »).

   API : window.OverdriveIntro = { isActive(), isLeaving(), whenDone(), skip(),
   waitFor(promise) } — waitFor : l'intro attend aussi cette promesse (ex. le
   décodage de l'image du héros) avant de sortir, dans la limite de MAX_MS.
   Événements (window) : overdrive:intro-exit (début de la sortie),
   overdrive:intro-done (overlay retiré).
   ========================================================================== */
(function () {
  "use strict";

  if (window.OverdriveIntro) { return; }

  var doc = document;
  var root = doc.documentElement;
  var KEY = "overdrive-intro";

  var MIN_MS = 1800;      /* durée minimale avant la sortie (effets complets) */
  var MAX_MS = 3200;      /* chargement lent : on sort quand même */
  var MIN_REDUCED = 450;  /* animations réduites : courte pause puis fondu */
  var LINE_MS = 420;      /* durée minimale d'affichage d'une ligne */

  var STR = {
    fr: {
      aria: "Chargement d'Overdrive",
      tag: "Optimiseur PC gaming",
      l_hw: "Détection du matériel…",
      l_hw_ok: "Matériel détecté : {g}",
      l_games: "Préparation de tes jeux…",
      l_ready: "Prêt.",
      skip: "Clic ou Échap pour passer"
    },
    en: {
      aria: "Loading Overdrive",
      tag: "Gaming PC optimizer",
      l_hw: "Detecting hardware…",
      l_hw_ok: "Hardware detected: {g}",
      l_games: "Getting your games ready…",
      l_ready: "Ready.",
      skip: "Click or press Esc to skip"
    }
  };

  var active = false;
  var doneResolve = null;
  var donePromise = new Promise(function (resolve) { doneResolve = resolve; });

  function lang() {
    return String(root.lang || "fr").slice(0, 2).toLowerCase() === "en" ? "en" : "fr";
  }
  function s(key, repl) {
    var d = STR[lang()] || STR.fr;
    var str = d[key] || STR.fr[key] || key;
    if (repl) {
      Object.keys(repl).forEach(function (k) { str = str.split("{" + k + "}").join(String(repl[k])); });
    }
    return str;
  }
  function esc(v) {
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  /** Nom de matériel lisible : même règle que l'accueil (home.js cleanName). */
  function cleanName(v) {
    return String(v || "").replace(/\((TM|R|C)\)/gi, "").replace(/\s*@\s*[\d.,]+\s*GHz\s*$/i, "")
      .replace(/\s+\d+-Core Processor\s*$/i, "")
      .replace(/\s+(CPU|Processor)\s*$/i, "").replace(/\s{2,}/g, " ").trim();
  }
  function nowMs() { return (window.performance && performance.now) ? performance.now() : Date.now(); }
  function motion() {
    var m = root.getAttribute("data-motion");
    return m === "reduced" || m === "off" ? m : "max";
  }
  function emit(name) {
    try { window.dispatchEvent(new CustomEvent(name)); } catch (e) { /* navigateur ancien : sans effet */ }
  }

  /** Doit-on jouer l'intro ? (une fois par session, jamais sans animations) */
  function shouldPlay() {
    if (!doc.body || motion() === "off" || doc.hidden) { return false; }
    try {
      if (window.sessionStorage.getItem(KEY)) { return false; }
      window.sessionStorage.setItem(KEY, "1");
    } catch (e) { /* stockage indisponible : on joue quand même */ }
    return true;
  }

  function finishNow() {
    if (doneResolve) { doneResolve(); doneResolve = null; }
  }

  function play() {
    var reduced = motion() === "reduced";
    var startedAt = nowMs();
    var timers = [];
    var leaving = false;
    var finished = false;
    var loaded = { status: false, hw: false };
    var gpuName = "";

    function later(fn, ms) { var id = setTimeout(fn, ms); timers.push(id); return id; }

    /* ---- construction ---- */

    var letters = "OVERDRIVE".split("").map(function (c, i) {
      return '<span style="--i:' + i + '">' + c + "</span>";
    }).join("");

    var el = doc.createElement("div");
    el.id = "od-intro";
    if (reduced) { el.className = "is-reduced"; }
    el.setAttribute("role", "status");
    el.setAttribute("aria-label", s("aria"));
    el.innerHTML =
      '<div class="oi-bg" aria-hidden="true">' +
      '<span class="oi-halo oi-halo-1"></span><span class="oi-halo oi-halo-2"></span>' +
      '<span class="oi-halo oi-halo-3"></span><span class="oi-grid"></span></div>' +
      '<div class="oi-stage" aria-hidden="true">' +
      '<div class="oi-logo-wrap"><span class="oi-glow"></span><span class="oi-pulse"></span>' +
      '<svg class="oi-logo" viewBox="0 0 120 120" focusable="false">' +
      '<defs><linearGradient id="oi-grad" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0" class="oi-stop-a"/><stop offset="1" class="oi-stop-b"/></linearGradient></defs>' +
      '<circle class="oi-ring oi-ring-1" cx="60" cy="60" r="46" pathLength="1"/>' +
      '<circle class="oi-ring oi-ring-2" cx="60" cy="60" r="19" pathLength="1"/>' +
      '<circle class="oi-core" cx="60" cy="60" r="7"/>' +
      "</svg></div>" +
      '<div class="oi-word">' + letters + "</div>" +
      '<div class="oi-tag">' + esc(s("tag")) + "</div>" +
      /* Balayage limité à la scène (logo + mot), pas à tout l'écran. */
      '<span class="oi-sweep-clip"><span class="oi-sweep"></span></span>' +
      "</div>" +
      '<div class="oi-foot">' +
      '<div class="oi-lines" aria-live="polite"><div class="oi-line">' + esc(s("l_hw")) + "</div></div>" +
      '<div class="oi-bar" aria-hidden="true"><i></i></div>' +
      '<div class="oi-skip">' + esc(s("skip")) + "</div>" +
      "</div>";
    doc.body.insertBefore(el, doc.body.firstChild);
    active = true;
    root.classList.add("od-intro-on");

    var linesEl = el.querySelector(".oi-lines");
    var barEl = el.querySelector(".oi-bar i");

    /* ---- lignes qui défilent (durée minimale de lecture) ---- */

    var lineQueue = [];
    var lineBusyUntil = nowMs() + LINE_MS;
    var lineTimer = 0;
    var lastLine = s("l_hw");

    function pushLine(text, ready) {
      if (text === lastLine) { return; }
      lastLine = text;
      lineQueue.push({ text: text, ready: !!ready });
      pumpLines();
    }
    function pumpLines() {
      if (lineTimer || !lineQueue.length || leaving) { return; }
      var wait = Math.max(0, lineBusyUntil - nowMs());
      lineTimer = later(function () {
        lineTimer = 0;
        if (leaving || !lineQueue.length) { return; }
        var item = lineQueue.shift();
        var olds = linesEl.querySelectorAll(".oi-line:not(.is-old)");
        Array.prototype.forEach.call(olds, function (old) {
          /* Animations réduites : aucun fondu croisé, l'ancienne ligne part
             tout de suite (jamais deux textes superposés). */
          if (reduced) { if (old.parentNode) { old.parentNode.removeChild(old); } return; }
          old.classList.remove("is-next");
          old.classList.add("is-old");
          later(function () { if (old.parentNode) { old.parentNode.removeChild(old); } }, 260);
        });
        var ln = doc.createElement("div");
        /* « is-next » : entrée retardée, l'ancienne ligne a d'abord quitté la boîte. */
        ln.className = "oi-line" + (item.ready ? " is-ready" : "") + (olds.length && !reduced ? " is-next" : "");
        ln.textContent = item.text;
        linesEl.appendChild(ln);
        lineBusyUntil = nowMs() + LINE_MS;
        pumpLines();
      }, wait);
    }

    /* ---- progression : vrai chargement + part liée au temps ---- */

    function progress() {
      if (leaving) { return; }
      var minDur = reduced ? MIN_REDUCED : MIN_MS;
      var tp = Math.min(1, (nowMs() - startedAt) / minDur);
      var p = 0.08 + (loaded.status ? 0.27 : 0) + (loaded.hw ? 0.4 : 0) + 0.25 * tp;
      barEl.style.transform = "scaleX(" + Math.min(1, p).toFixed(3) + ")";
    }
    var progTimer = setInterval(progress, 200);
    timers.push(progTimer);
    /* Style calculé avant la première valeur : la barre part de zéro. */
    try { void window.getComputedStyle(barEl).transform; } catch (e0) { /* sans effet */ }
    progress();

    /* Promesses supplémentaires (waitFor) : ex. image du héros décodée, pour
       que la sortie se fonde sur un visuel déjà peint (plafond MAX_MS). */
    var waits = [];
    api.waitFor = function (p) {
      if (leaving || !p || typeof p.then !== "function") { return; }
      var w = { done: false };
      waits.push(w);
      function fin() { w.done = true; readyCheck(); }
      p.then(fin, fin);
    };

    function readyCheck() {
      if (leaving) { return; }
      var elapsed = nowMs() - startedAt;
      var minDur = reduced ? MIN_REDUCED : MIN_MS;
      var allLoaded = loaded.status && loaded.hw && waits.every(function (w) { return w.done; });
      if (allLoaded) { pushLine(s("l_ready"), true); }
      if ((allLoaded && elapsed >= minDur) || elapsed >= MAX_MS) {
        exit(false);
      }
    }

    function fetchJson(path) {
      return fetch(path, { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; });
    }

    fetchJson("/api/status").then(function (st) {
      loaded.status = true;
      progress();
      /* Un jeu tourne : on s'efface tout de suite (zéro coût en jeu). */
      if (st && st.game_running) { exit(true); return; }
      readyCheck();
    }).catch(function () {
      loaded.status = true;
      readyCheck();
    });

    fetchJson("/api/hardware").then(function (hw) {
      loaded.hw = true;
      var gpus = (hw && hw.gpus) || [];
      var best = null;
      gpus.forEach(function (g) {
        var score = (Number(g.vram_mb) || 0) + (/\b(RX|RTX|GTX|Arc)\b/i.test(String(g.name || "")) ? 1e6 : 0);
        if (!best || score > best.score) { best = { score: score, name: g.name }; }
      });
      gpuName = best && best.name ? cleanName(best.name) : "";
      var cpu = hw && hw.cpu && hw.cpu.name ? cleanName(hw.cpu.name) : "";
      if (gpuName || cpu) { pushLine(s("l_hw_ok", { g: gpuName || cpu })); }
      pushLine(s("l_games"));
      progress();
      readyCheck();
    }).catch(function () {
      loaded.hw = true;
      pushLine(s("l_games"));
      readyCheck();
    });

    /* Vérifications régulières (durée minimale atteinte, plafond). */
    later(readyCheck, reduced ? MIN_REDUCED : MIN_MS);
    later(readyCheck, MAX_MS);
    /* Filet absolu : l'overlay ne reste jamais (animations figées, erreur…). */
    var safety = setTimeout(finish, MAX_MS + 2500);

    /* ---- passer l'intro ---- */

    function onSkip(e) {
      /* Touche de modification seule : on attend la suite. Un raccourci
         (Ctrl+K pour la palette, etc.) fait sortir l'intro tout de suite :
         la palette ne s'ouvre jamais invisible sous l'overlay. */
      if (e && e.type === "keydown" && /^(Control|Shift|Alt|Meta|AltGraph|OS)$/.test(String(e.key || ""))) { return; }
      exit(true);
    }
    el.addEventListener("click", onSkip);
    doc.addEventListener("keydown", onSkip, true);
    el.addEventListener("wheel", onSkip, { passive: true });

    function cleanupListeners() {
      el.removeEventListener("click", onSkip);
      doc.removeEventListener("keydown", onSkip, true);
      el.removeEventListener("wheel", onSkip);
    }

    function exit(fast) {
      if (leaving) { return; }
      leaving = true;
      cleanupListeners();
      timers.forEach(function (id) { clearTimeout(id); clearInterval(id); });
      timers = [];
      barEl.style.transform = "scaleX(1)";
      if (fast) { el.classList.add("is-fast"); }
      el.classList.add("is-leaving");
      emit("overdrive:intro-exit");
      var dur = reduced ? 400 : (fast ? 320 : 680);
      /* Fin par minuterie : fiable même si les animations sont figées
         (pause en jeu) ou désactivées en cours de route. */
      setTimeout(finish, dur + 40);
    }

    function finish() {
      if (finished) { return; }
      finished = true;
      leaving = true;
      clearTimeout(safety);
      cleanupListeners();
      timers.forEach(function (id) { clearTimeout(id); clearInterval(id); });
      timers = [];
      if (el.parentNode) { el.parentNode.removeChild(el); }
      active = false;
      root.classList.remove("od-intro-on");
      emit("overdrive:intro-done");
      finishNow();
    }

    api.skip = function () { exit(true); };
    api.isLeaving = function () { return leaving; };
  }

  var api = {
    isActive: function () { return active; },
    isLeaving: function () { return false; },
    whenDone: function () { return donePromise; },
    skip: function () { /* aucune intro en cours */ },
    waitFor: function () { /* aucune intro en cours */ }
  };
  window.OverdriveIntro = api;

  try {
    if (shouldPlay()) { play(); } else { finishNow(); }
  } catch (err) {
    /* Jamais bloquant : en cas d'erreur, l'overlay disparaît. */
    var ov = doc.getElementById("od-intro");
    if (ov && ov.parentNode) { ov.parentNode.removeChild(ov); }
    active = false;
    root.classList.remove("od-intro-on");
    finishNow();
  }
})();
