/* ==========================================================================
   Overdrive — moteur d'effets visuels « Midnight » (motion.js)

   Fonctionne SANS modifier app.js :
   - cascade d'apparition : MutationObserver sur #page (et la modale) ;
   - spotlight, inclinaison 3D, boutons magnétiques : délégation d'un seul
     listener pointermove, throttlé par requestAnimationFrame ;
   - onde au clic : délégation pointerdown ;
   - pilule de navigation calée sur .nav-item.active ;
   - compteurs animés sur .stat-value / .mon-value / .ns-value /
     .sens-stat-value quand leur texte change ;
   - jauges anneaux (tuiles CPU/RAM du moniteur) et aires de sparklines ;
   - fondus de sortie des modales, du QCM et du bandeau (clones « fantômes ») ;
   - fond vivant (#od-backdrop) ;
   - transitions de page (View Transitions API) sur les clics de navigation.

   Niveau : html[data-motion] = max | reduced | off ; pause :
   html[data-motion-paused] (posé par l'app quand un jeu tourne).

   API : window.OverdriveMotion = { setLevel, setPaused, refresh, countUp,
   transition, navigate, getLevel, isPaused }.
   Aucune dépendance, aucune exception à l'exécution attendue : chaque
   effet est protégé et se désactive proprement si une API manque.
   ========================================================================== */
(function () {
  "use strict";

  if (window.OverdriveMotion) { return; }

  var doc = document;
  var root = doc.documentElement;
  var SVGNS = "http://www.w3.org/2000/svg";

  var LEVELS = ["max", "reduced", "off"];
  var STORE_KEY = "overdrive-motion";

  /* Éléments qui apparaissent en cascade (seuls les plus hauts sont animés). */
  var REVEAL_SEL = [
    ".page-title", ".page-sub", ".group-label", ".card", ".notice", ".chips",
    ".tweaks-toolbar", ".quick-actions > .btn", ".tweak-group", ".tweak-row",
    ".settings-row", ".table tbody tr", ".opt-list > li", ".cs2-advice > li",
    ".boost-steps > li", ".mono-block", ".ns-stat", ".sens-stat", ".cs2-machine",
    ".cs2-profile-row", "details.fold", ".chat-wrap", ".msg", ".msg-pending",
    ".lat-head", ".xhair-card", ".hw-summary", ".quiz-notes"
  ].join(",");
  /* Repères pour reconnaître un même élément d'un rendu à l'autre. */
  var HEAD_SEL = "h1, h2, h3, .card-title, .set-name, .tweak-name, .opt-title, .advice-title, " +
    ".empty-title, .stat-label, .mon-label, .hw-label, .ns-label, .sens-stat-label, .tweak-group-head";
  var SPOT_SEL = ".card, .quiz-opt, .ns-stat, .sens-stat";
  var TILT_SEL = ".stat-card, .game-card, .xhair-card, .mon-card, .ns-stat, .sens-stat";
  var MAG_SEL = ".btn-primary";
  var RIPPLE_SEL = ".btn, .chip, .seg button, .nav-item, .quiz-opt, .sidebar-search";
  var COUNT_SEL = ".stat-value, .mon-value, .ns-value, .sens-stat-value, [data-od-count]";

  var MAX_STAGGER = 16;   /* au-delà : plus de décalage supplémentaire */
  var MAX_ANIM = 48;      /* au-delà : affichage direct (performances) */
  var LIVE_MS = 2600;     /* conteneur rafraîchi plus souvent : « vivant », pas de cascade */
  var USER_MS = 1200;     /* rendu juste après une action utilisateur : cascade autorisée */
  var COUNT_MS = 650;     /* durée des compteurs */

  var page = null, modalRoot = null, overlayRoot = null, banner = null;
  var observer = null;
  var lastInput = 0;

  /* ------------------------------------------------------------------ */
  /* Utilitaires                                                         */
  /* ------------------------------------------------------------------ */

  function now() {
    return (window.performance && performance.now) ? performance.now() : Date.now();
  }
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function noop() { /* rien */ }
  function isEl(n) { return !!n && n.nodeType === 1; }

  function getLevel() {
    var l = root.getAttribute("data-motion");
    return LEVELS.indexOf(l) >= 0 ? l : "max";
  }
  function isPaused() { return root.hasAttribute("data-motion-paused"); }
  /** Effets complets (3D, spotlight, magnétisme, compteurs). */
  function fxOn() { return getLevel() === "max" && !isPaused(); }
  /** Au moins des fondus. */
  function fadeOn() { return getLevel() !== "off" && !isPaused(); }

  function syncFxClass() { root.classList.toggle("od-fx", fxOn()); }

  function lang() {
    return String(root.lang || "fr").slice(0, 2).toLowerCase() === "en" ? "en" : "fr";
  }

  /* ------------------------------------------------------------------ */
  /* Cascade d'apparition                                                */
  /* ------------------------------------------------------------------ */

  function isCandidate(el) {
    try { return isEl(el) && el.matches(REVEAL_SEL); } catch (e) { return false; }
  }

  /** Candidats les plus hauts dans les racines données (racines incluses). */
  function collect(scopes) {
    var out = [];
    var seen = new Set();
    for (var s = 0; s < scopes.length; s++) {
      var scope = scopes[s];
      if (!isEl(scope)) { continue; }
      if (isCandidate(scope)) {
        if (!seen.has(scope)) { seen.add(scope); out.push(scope); }
        continue;
      }
      var list = scope.querySelectorAll(REVEAL_SEL);
      for (var i = 0; i < list.length; i++) {
        var el = list[i];
        var p = el.parentElement, nested = false;
        while (p && p !== scope) {
          if (isCandidate(p)) { nested = true; break; }
          p = p.parentElement;
        }
        if (!nested && !seen.has(el)) { seen.add(el); out.push(el); }
      }
    }
    return out;
  }

  function normClass(el) {
    var parts = [];
    for (var i = 0; i < el.classList.length; i++) {
      var c = el.classList[i];
      if (c.indexOf("od-") === 0 || c === "active" || c === "selected" || c === "sub-disabled") { continue; }
      parts.push(c);
    }
    return el.tagName + "." + parts.sort().join(".");
  }

  /** Clé stable d'un élément (id, data-*, titre, ou rang parmi ses pareils). */
  function keyOf(el, counts) {
    if (el.id) { return "#" + el.id; }
    var cls = normClass(el);
    var d = el.getAttribute("data-game") || el.getAttribute("data-id") || el.getAttribute("data-opt") ||
      el.getAttribute("data-filter") || el.getAttribute("data-ob");
    if (d) { return cls + "|" + d; }
    var h = null;
    try { h = el.matches(HEAD_SEL) ? el : el.querySelector(HEAD_SEL); } catch (e) { h = null; }
    if (h) { return cls + "|" + String(h.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60); }
    counts[cls] = (counts[cls] || 0) + 1;
    return cls + "@" + counts[cls];
  }

  function keySet(list) {
    var counts = {}, set = new Set();
    list.forEach(function (el) { set.add(keyOf(el, counts)); });
    return set;
  }

  /** Lance la cascade sur une liste (visibles seulement, décalage plafonné). */
  function reveal(list) {
    if (!fadeOn() || !list || !list.length) { return; }
    var vh = window.innerHeight || 900;
    var reduced = !fxOn();
    var n = 0, done = [];
    for (var i = 0; i < list.length && n < MAX_ANIM; i++) {
      var el = list[i];
      if (!isEl(el) || !el.isConnected || el.classList.contains("od-reveal")) { continue; }
      var r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) { continue; }
      if (r.top > vh + 40) { continue; }   /* hors écran : affiché tel quel */
      el.style.setProperty("--od-i", String(reduced ? 0 : Math.min(n, MAX_STAGGER)));
      el.classList.add("od-reveal");
      done.push(el);
      n++;
    }
    if (done.length) {
      /* Filet de sécurité si animationend ne vient jamais (élément masqué…). */
      setTimeout(function () { done.forEach(endReveal); }, 2200);
    }
  }

  function endReveal(el) {
    if (el.classList.contains("od-reveal")) {
      el.classList.remove("od-reveal");
      el.style.removeProperty("--od-i");
    }
  }

  function clearReveals() {
    Array.prototype.forEach.call(doc.querySelectorAll(".od-reveal"), endReveal);
    if (page) { page.classList.remove("od-page-enter"); }
  }

  function onAnimEnd(e) {
    var el = e.target;
    if (!isEl(el)) { return; }
    var name = e.animationName;
    if ((name === "od-rise" || name === "od-fade") && el.classList.contains("od-reveal")) {
      endReveal(el);
    } else if (el === page && (name === "od-page-in" || name === "od-fade")) {
      page.classList.remove("od-page-enter");
    } else if (name === "od-mark-pop") {
      var opt = el.closest(".od-pop");
      if (opt) { opt.classList.remove("od-pop"); }
    }
  }

  /** Rendu complet de la page (#page.innerHTML remplacé). */
  function onPageRender() {
    ensureRings();
    if (!fadeOn() || !page) { return; }
    page.classList.remove("od-page-enter");
    void page.offsetWidth;   /* redémarre l'animation */
    page.classList.add("od-page-enter");
    reveal(collect([page]));
  }

  /** Mise à jour d'un conteneur interne (zone chargée, re-rendu partiel…). */
  function onContainer(T, added, removed) {
    var addedEls = added.filter(isEl);
    if (!addedEls.length || !fadeOn()) { return; }
    var t = now();
    var last = T.__odLast || 0;
    T.__odLast = t;
    var removedEls = removed.filter(isEl);
    var fromLoading = !removedEls.length || removedEls.some(function (n) {
      return n.classList && n.classList.contains("loading-line");
    });
    if (fromLoading) { reveal(collect(addedEls)); return; }
    var userDriven = (t - lastInput) < USER_MS;
    if (!userDriven && (t - last) < LIVE_MS) { return; }   /* rafraîchissement en boucle */
    /* Re-rendu : seuls les éléments réellement nouveaux apparaissent. */
    var oldKeys = keySet(collect(removedEls));
    var counts = {};
    var fresh = collect(addedEls).filter(function (el) { return !oldKeys.has(keyOf(el, counts)); });
    reveal(fresh);
  }

  /* ------------------------------------------------------------------ */
  /* Compteurs animés                                                    */
  /* ------------------------------------------------------------------ */

  var NUM_RE = /\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?/g;
  var anims = new Set();
  var countRaf = 0;

  function parseNums(str) {
    var nums = [], skel = [], last = 0, m;
    str = String(str || "");
    NUM_RE.lastIndex = 0;
    while ((m = NUM_RE.exec(str)) !== null) {
      var raw = m[0];
      skel.push(str.slice(last, m.index));
      var gm = raw.match(/[   ]/);
      var dm = raw.match(/[.,](\d+)$/);
      var decimals = dm ? dm[1].length : 0;
      var ds = dm ? raw.charAt(raw.length - decimals - 1) : null;
      var clean = raw.replace(/[   ]/g, "").replace(",", ".");
      nums.push({ v: parseFloat(clean), dec: decimals, ds: ds, gs: gm ? gm[0] : null });
      last = m.index + raw.length;
    }
    skel.push(str.slice(last));
    return { nums: nums, skel: skel };
  }

  function fmtNum(n, meta) {
    var s = (Math.round(n * Math.pow(10, meta.dec)) / Math.pow(10, meta.dec)).toFixed(meta.dec);
    var parts = s.split(".");
    var intPart = parts[0];
    if (meta.gs) { intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, meta.gs); }
    return parts.length > 1 ? intPart + (meta.ds || ".") + parts[1] : intPart;
  }

  function buildStr(skel, values, metas) {
    var out = skel[0];
    for (var i = 0; i < values.length; i++) { out += fmtNum(values[i], metas[i]) + skel[i + 1]; }
    return out;
  }

  function firstDigitText(el) {
    var walker = doc.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = walker.nextNode())) { if (/\d/.test(n.data)) { return n; } }
    return null;
  }

  function cancelNode(node) {
    anims.forEach(function (a) { if (a.node === node || (a.el && a.el === node)) { anims.delete(a); } });
  }

  /** Anime un nœud texte de fromStr vers toStr en conservant le format. */
  function animateNode(node, fromStr, toStr) {
    var to = parseNums(toStr);
    if (!to.nums.length) { return; }
    var from = parseNums(fromStr);
    var same = from.nums.length === to.nums.length && from.skel.join("\u0000") === to.skel.join("\u0000");
    var starts = to.nums.map(function (n, i) { return same ? from.nums[i].v : 0; });
    var ends = to.nums.map(function (n) { return n.v; });
    var changed = starts.some(function (s, i) { return s !== ends[i]; });
    if (!changed) { return; }
    cancelNode(node);
    var a = { node: node, toStr: toStr, skel: to.skel, metas: to.nums, starts: starts, ends: ends, t0: now(), dur: COUNT_MS };
    node.data = buildStr(a.skel, starts, a.metas);
    anims.add(a);
    if (!countRaf) { countRaf = requestAnimationFrame(countTick); }
  }

  function countTick() {
    countRaf = 0;
    var t = now();
    anims.forEach(function (a) {
      var p = clamp((t - a.t0) / a.dur, 0, 1);
      var e = 1 - Math.pow(1 - p, 3);
      if (a.el) {
        /* countUp() public : formateur fourni. */
        if (!a.node.isConnected) { anims.delete(a); return; }
        a.node.data = p >= 1 ? a.fmt(a.to) : a.fmt(a.from + (a.to - a.from) * e);
      } else {
        if (!a.node.isConnected) { anims.delete(a); return; }
        a.node.data = p >= 1 ? a.toStr : buildStr(a.skel, a.starts.map(function (s, i) {
          return s + (a.ends[i] - s) * e;
        }), a.metas);
      }
      if (p >= 1) { anims.delete(a); }
    });
    if (anims.size) { countRaf = requestAnimationFrame(countTick); }
  }

  function finishCounters() {
    anims.forEach(function (a) {
      try { a.node.data = a.el ? a.fmt(a.to) : a.toStr; } catch (e) { /* nœud détaché */ }
    });
    anims.clear();
  }

  /** Texte d'un compteur modifié par l'app : anime depuis l'ancienne valeur. */
  function onCountChange(el, oldStr) {
    if (el.__odSkip !== undefined) {
      var skip = el.__odSkip === el.textContent;
      delete el.__odSkip;
      if (skip) { return; }
    }
    var node = firstDigitText(el);
    var finalStr = node ? node.data : el.textContent;
    syncRingFor(el, finalStr);
    if (!node || !fxOn()) { return; }
    animateNode(node, oldStr, finalStr);
  }

  /** Compteurs apparus dans un sous-arbre ajouté : comptent depuis 0. */
  function countNew(rootsAdded) {
    if (!fxOn()) { return; }
    rootsAdded.forEach(function (r) {
      if (!isEl(r)) { return; }
      var list = [];
      try {
        if (r.matches(COUNT_SEL)) { list.push(r); }
        Array.prototype.push.apply(list, r.querySelectorAll(COUNT_SEL));
      } catch (e) { return; }
      list.forEach(function (el) {
        var node = firstDigitText(el);
        if (node) { animateNode(node, "", node.data); }
      });
    });
  }

  /** API : anime el jusqu'à value (formateur optionnel). */
  function countUp(el, value, formatter) {
    if (!isEl(el)) { return; }
    var to = Number(value);
    if (!isFinite(to)) { return; }
    var cur = parseNums(el.textContent || "");
    var from = cur.nums.length ? cur.nums[0].v : 0;
    var fmt = typeof formatter === "function" ? formatter : defaultFormatter(el, value);
    if (!fxOn()) {
      el.__odSkip = String(fmt(to));
      el.textContent = el.__odSkip;
      return;
    }
    var start = String(fmt(from));
    el.__odSkip = start;
    el.textContent = start;
    var node = el.firstChild;
    if (!node || node.nodeType !== 3) { return; }
    anims.forEach(function (a) { if (a.el === el) { anims.delete(a); } });
    anims.add({ el: el, node: node, fmt: function (v) { return String(fmt(v)); }, from: from, to: to, t0: now(), dur: COUNT_MS });
    if (!countRaf) { countRaf = requestAnimationFrame(countTick); }
  }

  function defaultFormatter(el, value) {
    var s = String(value);
    var dec = s.indexOf(".") >= 0 ? Math.min(2, s.split(".")[1].length) : 0;
    var tpl = parseNums(el.textContent || "");
    var meta = { dec: dec, ds: lang() === "en" ? "." : ",", gs: null };
    if (tpl.nums.length) {
      meta.ds = tpl.nums[0].ds || meta.ds;
      meta.gs = tpl.nums[0].gs;
      var before = tpl.skel[0];
      var after = (el.textContent || "").slice((el.textContent || "").indexOf(before) + before.length)
        .replace(NUM_RE_FIRST, "");
      return function (v) { return before + fmtNum(v, meta) + after; };
    }
    return function (v) { return fmtNum(v, meta); };
  }
  var NUM_RE_FIRST = /\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?/;

  /* ------------------------------------------------------------------ */
  /* Jauges anneaux et sparklines                                        */
  /* ------------------------------------------------------------------ */

  var RING_HTML =
    '<svg class="od-ring" viewBox="0 0 44 44" aria-hidden="true" focusable="false">' +
    '<circle class="od-ring-track" cx="22" cy="22" r="18"/>' +
    '<circle class="od-ring-bar" cx="22" cy="22" r="18" pathLength="100"/></svg>';

  function ensureRings() {
    ["mon-cpu-val", "mon-ram-val"].forEach(function (id) {
      var v = doc.getElementById(id);
      if (!v) { return; }
      var card = v.closest(".mon-card");
      if (card && !card.querySelector(".od-ring")) { card.insertAdjacentHTML("beforeend", RING_HTML); }
    });
    Array.prototype.forEach.call(doc.querySelectorAll("[data-od-gauge]"), function (host) {
      if (!host.querySelector(".od-ring")) {
        host.insertAdjacentHTML("beforeend", RING_HTML);
        var val = parseFloat(host.getAttribute("data-od-gauge"));
        if (isFinite(val)) { setRing(host.querySelector(".od-ring"), val); }
      }
    });
  }

  function setRing(ring, pct) {
    if (!ring) { return; }
    var bar = ring.querySelector(".od-ring-bar");
    if (!bar) { return; }
    var p = clamp(Number(pct) || 0, 0, 100);
    bar.style.strokeDashoffset = String(100 - p);
    ring.classList.toggle("od-hot", p >= 90);
  }

  function syncRingFor(el, finalStr) {
    var host = el.closest("[data-od-gauge], .mon-card");
    if (!host) { return; }
    var ring = host.querySelector(".od-ring");
    if (!ring) { return; }
    var n = parseNums(finalStr).nums[0];
    if (n) { setRing(ring, n.v); }
  }

  /** Ajoute une aire en dégradé sous la sparkline (et un tracé animé la 1re fois). */
  function enhanceSpark(box) {
    var svg = box.querySelector("svg.spark");
    if (!svg || svg.querySelector(".od-spark-area")) { return; }
    var line = svg.querySelector("polyline");
    if (!line) { return; }
    var pts = String(line.getAttribute("points") || "").trim();
    if (!pts) { return; }
    var arr = pts.split(/\s+/);
    var vb = String(svg.getAttribute("viewBox") || "0 0 180 40").split(/[\s,]+/).map(Number);
    var H = vb[3] || 40;
    var first = arr[0].split(","), last = arr[arr.length - 1].split(",");
    var poly = doc.createElementNS(SVGNS, "polygon");
    poly.setAttribute("class", "od-spark-area");
    poly.setAttribute("points", pts + " " + last[0] + "," + H + " " + first[0] + "," + H);
    svg.insertBefore(poly, line);
    /* Tracé animé une seule fois par tuile, dès le premier segment (la courbe
       s'étire sur toute la largeur tant que l'historique n'est pas plein ; le
       drapeau n'est posé qu'au moment où l'animation joue vraiment). */
    if (!box.__odDrawn && fxOn() && arr.length >= 2 && svg.animate) {
      box.__odDrawn = true;
      /* Le dévoilement part du 1er point de la courbe. */
      var W = vb[2] || 180;
      var x0 = clamp(Number(first[0]) / W, 0, 1);
      var startInset = ((1 - x0) * 100).toFixed(2) + "%";
      svg.animate([{ clipPath: "inset(0 " + startInset + " 0 0)" }, { clipPath: "inset(0 0 0 0)" }],
        { duration: 900, easing: "cubic-bezier(.22,1,.36,1)" });
    }
  }

  /* ------------------------------------------------------------------ */
  /* Fantômes de sortie (modale, QCM, bandeau)                           */
  /* ------------------------------------------------------------------ */

  /** Clone inerte : sans ids (byId de l'app reste univoque) ni animations d'entrée. */
  function stripIds(n) {
    if (!isEl(n)) { return; }
    n.removeAttribute("id");
    Array.prototype.forEach.call(n.querySelectorAll("[id]"), function (x) { x.removeAttribute("id"); });
    Array.prototype.forEach.call(n.querySelectorAll(".od-reveal, .od-pop, .od-ripple, .od-tilting"), function (x) {
      x.classList.remove("od-reveal", "od-pop", "od-ripple", "od-tilting");
      x.style.removeProperty("--od-i");
    });
  }

  function removeLater(g, ms) {
    var done = false;
    function end() {
      if (done) { return; }
      done = true;
      if (g.parentNode) { g.parentNode.removeChild(g); }
    }
    g.addEventListener("animationend", function (e) { if (e.target === g) { end(); } });
    setTimeout(end, ms);
  }

  function ghostOut(node) {
    if (!fadeOn() || !isEl(node)) { return; }
    var g = node.cloneNode(true);
    stripIds(g);
    g.classList.add("od-ghost");
    g.classList.remove("od-enter");
    g.setAttribute("aria-hidden", "true");
    g.removeAttribute("role");
    try { g.inert = true; } catch (e) { /* inert indisponible */ }
    doc.body.appendChild(g);
    removeLater(g, 480);
  }

  function ghostBanner(nodes, className) {
    if (!fadeOn()) { return; }
    var g = doc.createElement("div");
    g.className = "od-banner-ghost od-ghost " + (className || "");
    g.setAttribute("aria-hidden", "true");
    nodes.forEach(function (n) { g.appendChild(n); });
    stripIds(g);
    doc.body.appendChild(g);
    removeLater(g, 480);
  }

  /** QCM re-rendu : nouvelle question → cascade ; même question → rebond. */
  function quizDiff(oldOv, newOv) {
    if (!fadeOn()) { return; }
    var oq = oldOv.querySelector(".quiz-question, h2");
    var nq = newOv.querySelector(".quiz-question, h2");
    var oT = oq ? oq.textContent : "", nT = nq ? nq.textContent : "";
    var ob = oldOv.querySelector(".quiz-bar > div"), nb = newOv.querySelector(".quiz-bar > div");
    if (ob && nb && fxOn() && nb.animate) {
      var ow = parseFloat(ob.style.width) || 0, nw = parseFloat(nb.style.width) || 0;
      if (nw > 0 && ow !== nw) {
        nb.animate([{ transform: "scaleX(" + (ow / nw) + ")" }, { transform: "scaleX(1)" }],
          { duration: 560, easing: "cubic-bezier(.22,1,.36,1)" });
      }
    }
    if (oT !== nT) {
      var inner = newOv.querySelector(".quiz-inner");
      if (!inner) { return; }
      var items = Array.prototype.slice.call(inner.querySelectorAll(
        ".quiz-question, .quiz-hint, .quiz-opt, .quiz-result > h2, .result-desc, .quiz-notes, .quiz-result-actions, .quiz-nav"));
      reveal(items);
    } else {
      selectionPop(oldOv, newOv);
    }
  }

  function optKey(o) { return o.getAttribute("data-opt") || o.getAttribute("data-ob") || o.textContent; }

  function selectionPop(oldScope, newScope) {
    if (!fxOn()) { return; }
    var was = {};
    Array.prototype.forEach.call(oldScope.querySelectorAll(".quiz-opt.selected"), function (o) { was[optKey(o)] = 1; });
    Array.prototype.forEach.call(newScope.querySelectorAll(".quiz-opt.selected"), function (o) {
      if (!was[optKey(o)]) { o.classList.add("od-pop"); }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Observation du DOM                                                  */
  /* ------------------------------------------------------------------ */

  function onMutations(records) {
    var pageRendered = false;
    var addedRoots = [];
    var containers = new Map();
    var counts = new Map();
    var modalAdded = null, modalRemoved = null;
    var ovAdded = null, ovRemoved = null;
    var ovInner = [];
    var bannerRemoved = [], bannerAdded = false;
    var sparks = new Set();

    var i, j, rec, t;
    for (i = 0; i < records.length; i++) {
      rec = records[i];
      if (rec.type !== "childList") { continue; }
      for (j = 0; j < rec.addedNodes.length; j++) {
        if (isEl(rec.addedNodes[j])) { addedRoots.push(rec.addedNodes[j]); }
      }
    }

    function insideAdded(node) {
      for (var k = 0; k < addedRoots.length; k++) {
        if (addedRoots[k] !== node && addedRoots[k].contains(node)) { return true; }
      }
      return false;
    }

    for (i = 0; i < records.length; i++) {
      rec = records[i];
      if (rec.type !== "childList") { continue; }
      t = rec.target;
      if (!isEl(t)) { continue; }
      var added = Array.prototype.slice.call(rec.addedNodes);
      var removed = Array.prototype.slice.call(rec.removedNodes);

      if (t === page) { pageRendered = true; continue; }

      if (t === modalRoot) {
        added.forEach(function (n) { if (isEl(n) && n.classList.contains("modal-overlay")) { modalAdded = n; } });
        removed.forEach(function (n) { if (isEl(n) && n.classList.contains("modal-overlay")) { modalRemoved = modalRemoved || n; } });
        continue;
      }
      if (t === overlayRoot) {
        added.forEach(function (n) { if (isEl(n) && n.classList.contains("quiz-overlay")) { ovAdded = n; } });
        removed.forEach(function (n) { if (isEl(n) && n.classList.contains("quiz-overlay")) { ovRemoved = ovRemoved || n; } });
        continue;
      }
      if (t === banner) {
        if (added.length) { bannerAdded = true; }
        Array.prototype.push.apply(bannerRemoved, removed);
        continue;
      }

      /* Compteur dont le texte a changé. */
      var cEl = null;
      try { cEl = t.matches(COUNT_SEL) ? t : t.closest(COUNT_SEL); } catch (e) { cEl = null; }
      if (cEl) {
        if (!counts.has(cEl)) {
          counts.set(cEl, removed.map(function (n) { return n.textContent || ""; }).join(""));
        }
        continue;
      }

      if (t.classList.contains("spark-box")) { sparks.add(t); continue; }

      if (overlayRoot && overlayRoot.contains(t)) {
        if (!insideAdded(t)) { ovInner.push({ removed: removed, added: added }); }
        continue;
      }

      var inPage = page && page.contains(t);
      var inModal = modalRoot && modalRoot.contains(t);
      if (!inPage && !inModal) { continue; }
      if (pageRendered && inPage) { continue; }
      if (insideAdded(t)) { continue; }
      var c = containers.get(t);
      if (!c) { c = { added: [], removed: [] }; containers.set(t, c); }
      Array.prototype.push.apply(c.added, added);
      Array.prototype.push.apply(c.removed, removed);
    }

    try {
      if (pageRendered) {
        onPageRender();
      }
      containers.forEach(function (c, T) {
        if (pageRendered && page && page.contains(T)) { return; }
        if (!T.isConnected) { return; }
        onContainer(T, c.added, c.removed);
      });
      counts.forEach(function (oldStr, el) { if (el.isConnected) { onCountChange(el, oldStr); } });
      countNew(addedRoots.filter(function (n) {
        return n.isConnected && !insideAdded(n) && ((page && page.contains(n)) || (modalRoot && modalRoot.contains(n)));
      }));
      if (pageRendered || containers.size) { ensureRings(); }
      sparks.forEach(enhanceSpark);

      /* Modale : remplacement direct = pas de nouvelle entrée ; fermeture = fantôme. */
      if (modalAdded && modalRemoved) {
        modalAdded.classList.add("od-no-enter");
      } else if (modalRemoved && !modalAdded && modalRoot && !modalRoot.querySelector(".modal-overlay")) {
        ghostOut(modalRemoved);
      }

      /* QCM. */
      if (ovAdded && !ovRemoved) {
        if (fadeOn()) { ovAdded.classList.add("od-enter"); }
      } else if (ovAdded && ovRemoved) {
        quizDiff(ovRemoved, ovAdded);
      } else if (ovRemoved && !ovAdded && overlayRoot && !overlayRoot.querySelector(".quiz-overlay")) {
        ghostOut(ovRemoved);
      }
      ovInner.forEach(function (m) {
        var oldWrap = doc.createElement("div"), newWrap = { querySelectorAll: function (s) {
          var out = [];
          m.added.forEach(function (n) {
            if (!isEl(n)) { return; }
            if (n.matches(s)) { out.push(n); }
            Array.prototype.push.apply(out, n.querySelectorAll(s));
          });
          return out;
        } };
        m.removed.forEach(function (n) { if (isEl(n)) { oldWrap.appendChild(n.cloneNode(true)); } });
        selectionPop(oldWrap, newWrap);
      });

      /* Bandeau masqué : il glisse vers le haut. */
      if (banner && bannerRemoved.length && !bannerAdded && banner.hidden) {
        ghostBanner(bannerRemoved, banner.className);
      }
    } catch (err) {
      /* Un effet visuel ne doit jamais casser l'application. */
    }
    /* Nos propres insertions (anneaux, aires, fantômes) ne sont pas à retraiter. */
    if (observer) { observer.takeRecords(); }
  }

  /* ------------------------------------------------------------------ */
  /* Pointeur : spotlight, inclinaison, magnétisme                       */
  /* ------------------------------------------------------------------ */

  var ptr = { e: null, raf: 0, tilt: null, mag: null };

  function onPointerMove(e) {
    if (e.pointerType === "touch") { return; }
    ptr.e = e;
    if (!ptr.raf) { ptr.raf = requestAnimationFrame(pointerFrame); }
  }

  function pointerFrame() {
    ptr.raf = 0;
    var e = ptr.e;
    if (!e) { return; }
    if (!fxOn()) { releaseAll(); return; }
    var t = isEl(e.target) ? e.target : null;
    if (!t || !t.closest) { return; }
    var x = e.clientX, y = e.clientY;

    var tilt = t.closest(TILT_SEL);
    if (tilt !== ptr.tilt) {
      if (ptr.tilt) { releaseTilt(ptr.tilt); }
      ptr.tilt = tilt;
      if (tilt) { tilt.__odRect = tilt.getBoundingClientRect(); }
    }
    if (tilt) { applyTilt(tilt, x, y); }

    var spot = t.closest(SPOT_SEL), guard = 0;
    while (spot && guard < 4) {
      var r = (spot === tilt && tilt.__odRect) ? tilt.__odRect : spot.getBoundingClientRect();
      spot.style.setProperty("--mx", (x - r.left).toFixed(1) + "px");
      spot.style.setProperty("--my", (y - r.top).toFixed(1) + "px");
      spot = spot.parentElement ? spot.parentElement.closest(SPOT_SEL) : null;
      guard++;
    }

    var mag = t.closest(MAG_SEL);
    if (mag && mag.disabled) { mag = null; }
    if (mag !== ptr.mag) {
      if (ptr.mag) { releaseMag(ptr.mag); }
      ptr.mag = mag;
      if (mag) { mag.__odRect = mag.getBoundingClientRect(); }
    }
    if (mag) { applyMag(mag, x, y); }
  }

  function applyTilt(el, x, y) {
    var r = el.__odRect;
    if (!r || !r.width || !r.height) { return; }
    var px = clamp((x - r.left) / r.width, 0, 1);
    var py = clamp((y - r.top) / r.height, 0, 1);
    var max = r.width > 420 ? 2.5 : 5;
    var ry = (px - 0.5) * 2 * max;
    var rx = (0.5 - py) * 2 * max;
    if (!el.classList.contains("od-tilting")) { el.classList.add("od-tilting"); }
    /* Léger soulèvement 2D plutôt qu'un scale3d (texte plus net). */
    el.style.transform = "translateY(-2px) perspective(900px) rotateX(" + rx.toFixed(2) + "deg) rotateY(" +
      ry.toFixed(2) + "deg)";
    /* Parallaxe 2D des éléments non textuels (anneau, pictogramme, viseur). */
    el.style.setProperty("--tx", ((px - 0.5) * 6).toFixed(2));
    el.style.setProperty("--ty", ((py - 0.5) * 6).toFixed(2));
  }

  function releaseTilt(el) {
    el.classList.remove("od-tilting");
    el.style.transform = "";
    el.style.removeProperty("--tx");
    el.style.removeProperty("--ty");
    el.__odRect = null;
  }

  function applyMag(el, x, y) {
    var r = el.__odRect;
    if (!r || !r.width || !r.height) { return; }
    var dx = clamp((x - (r.left + r.width / 2)) / (r.width / 2), -1, 1);
    var dy = clamp((y - (r.top + r.height / 2)) / (r.height / 2), -1, 1);
    el.style.setProperty("--magx", (dx * 4).toFixed(2) + "px");
    el.style.setProperty("--magy", (dy * 3).toFixed(2) + "px");
  }

  function releaseMag(el) {
    el.style.removeProperty("--magx");
    el.style.removeProperty("--magy");
    el.__odRect = null;
  }

  function releaseAll() {
    if (ptr.tilt) { releaseTilt(ptr.tilt); ptr.tilt = null; }
    if (ptr.mag) { releaseMag(ptr.mag); ptr.mag = null; }
  }

  /* Onde douce au clic. */
  function onPointerDown(e) {
    lastInput = now();
    if (!fxOn() || e.button !== 0 || !isEl(e.target)) { return; }
    var el = e.target.closest(RIPPLE_SEL);
    if (!el || el.disabled) { return; }
    var r = el.getBoundingClientRect();
    el.style.setProperty("--rx", (e.clientX - r.left).toFixed(1) + "px");
    el.style.setProperty("--ry", (e.clientY - r.top).toFixed(1) + "px");
    el.style.setProperty("--rs", Math.round(Math.max(r.width, r.height) * 2.4) + "px");
    el.classList.remove("od-ripple");
    void el.offsetWidth;
    el.classList.add("od-ripple");
    clearTimeout(el.__odRip);
    el.__odRip = setTimeout(function () { el.classList.remove("od-ripple"); }, 680);
  }

  /* ------------------------------------------------------------------ */
  /* Pilule de navigation                                                */
  /* ------------------------------------------------------------------ */

  var nav = null, pill = null, pillPlaced = false, pillPos = "";

  function setupPill() {
    nav = doc.querySelector("#sidebar .nav");
    if (!nav) { return; }
    pill = nav.querySelector(".od-nav-pill");
    if (!pill) {
      pill = doc.createElement("div");
      pill.className = "od-nav-pill";
      pill.setAttribute("aria-hidden", "true");
      nav.insertBefore(pill, nav.firstChild);
    }
    root.classList.add("od-pill-on");
    new MutationObserver(function () { movePill(true); })
      .observe(nav, { attributes: true, subtree: true, attributeFilter: ["class"] });
    window.addEventListener("resize", function () { movePill(false); });
    movePill(false);
  }

  function movePill(animate) {
    if (!nav || !pill) { return; }
    var active = nav.querySelector(".nav-item.active");
    if (!active) { pill.style.opacity = "0"; return; }
    var x = active.offsetLeft, y = active.offsetTop, w = active.offsetWidth, h = active.offsetHeight;
    if (!w || !h) { return; }
    var pos = x + "," + y + "," + w + "," + h;
    if (pos === pillPos && pill.style.opacity === "1") { return; }
    pillPos = pos;
    var instant = !animate || !pillPlaced || !fadeOn();
    if (instant) { pill.classList.add("od-noanim"); }
    pill.style.width = w + "px";
    pill.style.height = h + "px";
    pill.style.transform = "translate(" + x + "px, " + y + "px)";
    pill.style.opacity = "1";
    if (instant) {
      void pill.offsetWidth;
      pill.classList.remove("od-noanim");
    }
    pillPlaced = true;
  }

  /* ------------------------------------------------------------------ */
  /* Transitions de page (View Transitions API)                          */
  /* ------------------------------------------------------------------ */

  var vtActive = false;
  var currentVT = null;

  /** Clic pendant une View Transition : tant que la racine est capturée,
      Chromium dirige le clic vers <html> et il serait perdu (clics rapprochés
      sur les thèmes, navigation pendant une sortie de page). On termine la
      transition sans attendre, puis on rejoue le clic sur l'élément réel
      situé sous le pointeur. */
  function onVtClick(e) {
    if (!vtActive || !currentVT || e.target !== root || !e.isTrusted) { return; }
    var x = e.clientX, y = e.clientY;
    var vt = currentVT;
    e.preventDefault();
    e.stopPropagation();
    try { vt.skipTransition(); } catch (err) { /* transition déjà terminée */ }
    function replay() {
      requestAnimationFrame(function () {
        var el = doc.elementFromPoint(x, y);
        /* Une icône (<svg>, <path>) n'a pas de méthode click() : on remonte
           jusqu'au premier élément HTML cliquable (bouton, lien, libellé). */
        while (el && el !== root && typeof el.click !== "function") { el = el.parentElement; }
        if (el && el !== root && el !== doc.body) {
          try { el.click(); } catch (err2) { /* clic rejoué impossible */ }
        }
      });
    }
    vt.finished.then(replay, replay);
  }

  function canVT() {
    return typeof doc.startViewTransition === "function" && fadeOn() && !vtActive;
  }

  /** API : exécute fn() dans une transition animée (« page » ou « theme »). */
  function transition(fn, kind) {
    if (typeof fn !== "function") { return Promise.resolve(); }
    var k = kind === "theme" ? "theme" : "page";
    if (!canVT()) {
      try { return Promise.resolve(fn()); } catch (e) { return Promise.reject(e); }
    }
    vtActive = true;
    var cls = "od-vt-" + k;
    root.classList.add(cls);
    var vt;
    try {
      vt = doc.startViewTransition(function () { return fn(); });
    } catch (e) {
      root.classList.remove(cls);
      vtActive = false;
      try { return Promise.resolve(fn()); } catch (e2) { return Promise.reject(e2); }
    }
    currentVT = vt;
    function cleanup() {
      root.classList.remove(cls);
      vtActive = false;
      if (currentVT === vt) { currentVT = null; }
    }
    vt.ready.catch(noop);
    vt.finished.then(cleanup, cleanup);
    vt.updateCallbackDone.catch(noop);
    return vt.updateCallbackDone;
  }

  /** API : navigue vers un hash (#/route) avec transition de page. */
  function navigate(hash) {
    hash = String(hash || "#/");
    var cur = window.location.hash || "#/";
    if (cur === hash || (hash === "#/" && (cur === "" || cur === "#"))) { return; }
    if (!canVT()) { window.location.hash = hash; return; }
    transition(function () {
      return new Promise(function (resolve) {
        var done = false;
        function finish() {
          if (done) { return; }
          done = true;
          window.removeEventListener("hashchange", onHash);
          resolve();
        }
        /* Écouteur ajouté après celui de l'app : le rendu est déjà fait. */
        function onHash() { finish(); }
        window.addEventListener("hashchange", onHash);
        setTimeout(finish, 450);
        window.location.hash = hash;
      });
    }, "page");
  }

  function onNavClick(e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) { return; }
    if (!isEl(e.target)) { return; }
    var a = e.target.closest("a.nav-item[href^='#']");
    if (!a || !canVT()) { return; }
    var href = a.getAttribute("href");
    var cur = window.location.hash || "#/";
    if (href === cur || (href === "#/" && (cur === "" || cur === "#"))) { return; }
    e.preventDefault();
    navigate(href);
  }

  /* ------------------------------------------------------------------ */
  /* Fond vivant et définitions SVG partagées                            */
  /* ------------------------------------------------------------------ */

  function setupBackdrop() {
    var bd = doc.getElementById("od-backdrop");
    if (!bd) {
      bd = doc.createElement("div");
      bd.id = "od-backdrop";
      bd.setAttribute("aria-hidden", "true");
      doc.body.insertBefore(bd, doc.body.firstChild);
    }
    if (!bd.querySelector(".od-blob")) {
      bd.innerHTML = '<div class="od-blob od-blob-1"></div><div class="od-blob od-blob-2"></div>' +
        '<div class="od-blob od-blob-3"></div><div class="od-grid"></div><div class="od-noise"></div>';
    }
  }

  function setupDefs() {
    if (doc.getElementById("od-grad")) { return; }
    var wrap = doc.createElement("div");
    wrap.innerHTML =
      '<svg class="od-defs" width="0" height="0" aria-hidden="true" focusable="false" ' +
      'style="position:absolute;width:0;height:0;overflow:hidden;pointer-events:none">' +
      "<defs>" +
      '<linearGradient id="od-grad" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0" class="od-stop-1"/><stop offset="1" class="od-stop-2"/></linearGradient>' +
      '<linearGradient id="od-spark-stroke" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="180" y2="0">' +
      '<stop offset="0" class="od-stop-2"/><stop offset="1" class="od-stop-1"/></linearGradient>' +
      '<linearGradient id="od-spark-fill" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="40">' +
      '<stop offset="0" class="od-stop-f1"/><stop offset="1" class="od-stop-f2"/></linearGradient>' +
      "</defs></svg>";
    doc.body.appendChild(wrap.firstChild);
  }

  /* ------------------------------------------------------------------ */
  /* Niveau / pause                                                      */
  /* ------------------------------------------------------------------ */

  function afterModeChange() {
    syncFxClass();
    if (!fxOn()) { releaseAll(); finishCounters(); }
    if (!fadeOn()) { clearReveals(); }
    movePill(false);
  }

  /** API : max | reduced | off (persisté dans localStorage). */
  function setLevel(l) {
    if (LEVELS.indexOf(l) < 0) { return getLevel(); }
    root.setAttribute("data-motion", l);
    try { localStorage.setItem(STORE_KEY, l); } catch (e) { /* stockage indisponible */ }
    afterModeChange();
    return l;
  }

  /** API : pause complète des effets (jeu en cours). */
  function setPaused(b) {
    if (b) { root.setAttribute("data-motion-paused", ""); } else { root.removeAttribute("data-motion-paused"); }
    afterModeChange();
    return !!b;
  }

  /** API : rejoue la cascade sur un conteneur (défaut : #page) et resynchronise. */
  function refresh(scope) {
    ensureRings();
    movePill(false);
    var s = isEl(scope) ? scope : page;
    if (s) { reveal(collect([s])); }
  }

  /* ------------------------------------------------------------------ */
  /* Initialisation                                                      */
  /* ------------------------------------------------------------------ */

  function init() {
    page = doc.getElementById("page");
    modalRoot = doc.getElementById("modal-root");
    overlayRoot = doc.getElementById("overlay-root");
    banner = doc.getElementById("banner");

    if (!root.hasAttribute("data-motion")) {
      var l = "max";
      try {
        var s = localStorage.getItem(STORE_KEY);
        if (LEVELS.indexOf(s) >= 0) { l = s; } else if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) { l = "reduced"; }
      } catch (e) { /* défaut : max */ }
      root.setAttribute("data-motion", l);
    }

    try { setupBackdrop(); } catch (e) { /* fond facultatif */ }
    try { setupDefs(); root.classList.add("od-ready"); } catch (e) { /* jauges sans dégradé */ }
    try { setupPill(); } catch (e) { /* pilule facultative */ }
    syncFxClass();

    if (typeof MutationObserver === "function") {
      observer = new MutationObserver(onMutations);
      observer.observe(doc.body, { childList: true, subtree: true });
      new MutationObserver(function () { afterModeChange(); })
        .observe(root, { attributes: true, attributeFilter: ["data-motion", "data-motion-paused"] });
    }

    doc.addEventListener("pointermove", onPointerMove, { passive: true });
    doc.addEventListener("pointerdown", onPointerDown, { passive: true, capture: true });
    doc.addEventListener("keydown", function () { lastInput = now(); }, true);
    doc.addEventListener("click", onNavClick);
    window.addEventListener("click", onVtClick, true);
    doc.addEventListener("animationend", onAnimEnd, true);
    doc.addEventListener("animationcancel", onAnimEnd, true);
    root.addEventListener("mouseleave", releaseAll);
    window.addEventListener("blur", releaseAll);
    window.addEventListener("scroll", releaseAll, { passive: true, capture: true });
    doc.addEventListener("visibilitychange", function () {
      root.classList.toggle("od-hidden", !!doc.hidden);
      if (doc.hidden) { releaseAll(); }
    });

    /* Contenu déjà présent (script chargé après un premier rendu). */
    if (page && page.querySelector(".page-title")) { ensureRings(); }
  }

  window.OverdriveMotion = {
    setLevel: setLevel,
    setPaused: setPaused,
    refresh: refresh,
    countUp: countUp,
    transition: transition,
    navigate: navigate,
    getLevel: getLevel,
    isPaused: isPaused
  };

  if (doc.body) {
    init();
  } else {
    doc.addEventListener("DOMContentLoaded", init);
  }
})();
