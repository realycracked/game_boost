/* ==========================================================================
   Overdrive — écran d'accueil « héros » (home.js, vague 7)

   Module autonome appelé par app.js : window.OverdriveHome.render(pageEl, ctx).
   ctx fournit les aides de l'application (traduction, API, état, actions
   existantes : Boost, Boost CS2, benchmark, nettoyage, widget, fiche d'un
   jeu…) ; ce module ne duplique aucune de ces logiques.

   Sections (dans l'ordre d'affichage) :
     1. Héros cinématique : art « hero » du jeu mis en avant, Ken Burns,
        parallaxe souris (fond, personnage et contenu sur des plans
        différents), voiles, grain, reflet périodique, rotation auto (10 s)
        parmi CS2 + jeux détectés ;
     2. Carrousel de jaquettes 3D (molette, glisser, flèches, dérive) ;
     3. Indice de performance (anneau 0-100 + détail transparent) et tuiles
        LIVE (CPU, RAM, réseau) à remplissage en vague, mini-courbes 2 s ;
     4. Actions rapides animées ; 5. Conseils ; 6. Ta config ;
     7. Programmes recommandés (rendu existant d'app.js).
   Fond : champ de particules très discret (canvas, ≤ 60 points).

   Performances : on n'anime que transform / opacity / filter ; aucune boucle
   quand la fenêtre est cachée, hors data-motion="max" ou pendant le jeu
   (html[data-motion-paused]) ; tout est nettoyé quand on quitte la page.

   API : window.OverdriveHome = { render(pageEl, ctx), stop(), isActive() }.
   ========================================================================== */
(function () {
  "use strict";

  if (window.OverdriveHome) { return; }

  var doc = document;
  var root = doc.documentElement;

  /* ------------------------------------------------------------------ */
  /* Textes FR / EN (langue lue via ctx.lang(), repli : <html lang>)     */
  /* ------------------------------------------------------------------ */

  var STR = {
    fr: {
      greet_morning: "Bonjour",
      greet_afternoon: "Bon après-midi",
      greet_evening: "Bonsoir",
      greet_tail: "prêt à jouer ?",
      hero_aria: "Jeu mis en avant",
      hero_switch_aria: "Choisir le jeu mis en avant",
      hero_show: "Mettre en avant : {g}",
      hero_machine_v: "Ta machine : {v}",
      hero_machine_wait: "analyse en cours…",
      hero_installed: "Installé",
      hero_not_detected: "Non détecté",
      hero_discover: "À découvrir",
      hero_boost_general: "Boost général",
      hero_optimize: "Optimiser {g}",
      perf_title: "Indice de performance",
      perf_how: "Comment est-il calculé ?",
      perf_loading: "Calcul en cours…",
      perf_band_low: "À améliorer",
      perf_band_mid: "Correct",
      perf_band_good: "Très bien",
      perf_band_top: "Au top",
      perf_desc_low: "Il reste de la marge : quelques réglages peuvent vraiment aider.",
      perf_desc_mid: "Bonne base. Encore quelques optimisations et tu y es.",
      perf_desc_good: "Ta machine est bien réglée pour jouer.",
      perf_desc_top: "Réglages au top, rien à redire.",
      perf_part_tweaks: "Optimisations recommandées appliquées",
      perf_part_tier: "Niveau de la machine",
      perf_part_insights: "Aucun conseil « important »",
      perf_part_bench: "Benchmark réalisé",
      perf_val_none: "aucune disponible",
      perf_val_ins_ok: "0 trouvé",
      perf_val_ins_n: "{n} à traiter",
      perf_val_unknown: "inconnu",
      perf_val_bench_yes: "fait",
      perf_val_bench_no: "pas encore",
      perf_tip_foot: "Calculé sur cette machine, à partir de l'état réel des réglages.",
      perf_next_tweaks: "Appliquer les optimisations",
      perf_next_bench: "Lancer un benchmark",
      perf_next_insights: "Voir les conseils",
      perf_next_done: "Tout est en ordre",
      perf_next_tweaks_short: "Optimiser",
      perf_next_bench_short: "Benchmark",
      perf_next_insights_short: "Conseils",
      perf_pts: "{p} / {m}",
      live_title: "En direct",
      live_cpu: "CPU",
      live_ram: "RAM",
      live_net: "Réseau",
      live_gpu: "GPU",
      live_waiting: "En attente…",
      live_unavailable: "Indisponible",
      live_paused: "En pause pendant le jeu",
      live_threads: "{n} threads",
      live_ram_note: "{u} sur {t}",
      live_net_note: "↓ réception · ↑ {u}",
      live_net_note_short: "↓ {d} · ↑ {u}",
      live_gpu_note: "Température",
      games_title: "Tes jeux",
      games_count_one: "1 installé",
      games_count_many: "{n} installés",
      games_count_none: "Catalogue",
      games_all: "Tout voir",
      games_prev: "Jeux précédents",
      games_next: "Jeux suivants",
      games_rail: "Tes jeux (faire défiler)",
      games_optimize: "Optimiser",
      games_installed: "Installé",
      games_unavailable: "Liste des jeux indisponible.",
      actions_title: "Actions rapides",
      act_boost: "Boost en un clic",
      act_boost_sub: "Tweaks sûrs + nettoyage, réversible",
      act_clean: "Nettoyage",
      act_clean_sub: "Analyse les fichiers inutiles",
      act_bench: "Benchmark",
      act_bench_sub: "Score CPU, RAM et disque",
      act_widget: "Widget en jeu",
      act_widget_sub: "FPS et températures en overlay",
      insights_title: "Conseils",
      insights_none_title: "Rien à signaler",
      insights_none: "Aucun réglage problématique détecté sur ta machine.",
      insights_unavailable: "Conseils indisponibles pour le moment.",
      insights_open: "Ouvrir",
      config_title: "Ta config",
      config_cores: "{p} cœurs · {l} threads",
      config_ram: "{g} de RAM",
      config_free: "{f} libres",
      config_no_gpu: "GPU non détecté",
      config_unavailable: "Détection matérielle indisponible.",
      config_detecting: "Détection du matériel…",
      programs_title: "Programmes recommandés",
      programs_more: "Tout voir",
      programs_less: "Réduire"
    },
    en: {
      greet_morning: "Good morning",
      greet_afternoon: "Good afternoon",
      greet_evening: "Good evening",
      greet_tail: "ready to play?",
      hero_aria: "Featured game",
      hero_switch_aria: "Choose the featured game",
      hero_show: "Feature: {g}",
      hero_machine_v: "Your machine: {v}",
      hero_machine_wait: "analyzing…",
      hero_installed: "Installed",
      hero_not_detected: "Not detected",
      hero_discover: "Discover",
      hero_boost_general: "General Boost",
      hero_optimize: "Optimize {g}",
      perf_title: "Performance index",
      perf_how: "How is it calculated?",
      perf_loading: "Calculating…",
      perf_band_low: "Needs work",
      perf_band_mid: "Fair",
      perf_band_good: "Great",
      perf_band_top: "Top notch",
      perf_desc_low: "There is room to improve: a few settings can really help.",
      perf_desc_mid: "Solid base. A few more optimizations and you're there.",
      perf_desc_good: "Your machine is well tuned for gaming.",
      perf_desc_top: "Settings are spot on, nothing to add.",
      perf_part_tweaks: "Recommended optimizations applied",
      perf_part_tier: "Machine tier",
      perf_part_insights: "No \"important\" advice",
      perf_part_bench: "Benchmark done",
      perf_val_none: "none available",
      perf_val_ins_ok: "none found",
      perf_val_ins_n: "{n} to fix",
      perf_val_unknown: "unknown",
      perf_val_bench_yes: "done",
      perf_val_bench_no: "not yet",
      perf_tip_foot: "Computed on this machine from the actual state of your settings.",
      perf_next_tweaks: "Apply optimizations",
      perf_next_bench: "Run a benchmark",
      perf_next_insights: "See advice",
      perf_next_done: "All good",
      perf_next_tweaks_short: "Optimize",
      perf_next_bench_short: "Benchmark",
      perf_next_insights_short: "Advice",
      perf_pts: "{p} / {m}",
      live_title: "Live",
      live_cpu: "CPU",
      live_ram: "RAM",
      live_net: "Network",
      live_gpu: "GPU",
      live_waiting: "Waiting…",
      live_unavailable: "Unavailable",
      live_paused: "Paused while gaming",
      live_threads: "{n} threads",
      live_ram_note: "{u} of {t}",
      live_net_note: "↓ download · ↑ {u}",
      live_net_note_short: "↓ {d} · ↑ {u}",
      live_gpu_note: "Temperature",
      games_title: "Your games",
      games_count_one: "1 installed",
      games_count_many: "{n} installed",
      games_count_none: "Catalog",
      games_all: "See all",
      games_prev: "Previous games",
      games_next: "Next games",
      games_rail: "Your games (scrollable)",
      games_optimize: "Optimize",
      games_installed: "Installed",
      games_unavailable: "Game list unavailable.",
      actions_title: "Quick actions",
      act_boost: "One-click Boost",
      act_boost_sub: "Safe tweaks + cleanup, reversible",
      act_clean: "Cleanup",
      act_clean_sub: "Scan for useless files",
      act_bench: "Benchmark",
      act_bench_sub: "CPU, RAM and disk score",
      act_widget: "In-game widget",
      act_widget_sub: "FPS and temperatures overlay",
      insights_title: "Advice",
      insights_none_title: "Nothing to report",
      insights_none: "No problematic setting detected on your machine.",
      insights_unavailable: "Advice unavailable right now.",
      insights_open: "Open",
      config_title: "Your setup",
      config_cores: "{p} cores · {l} threads",
      config_ram: "{g} RAM",
      config_free: "{f} free",
      config_no_gpu: "GPU not detected",
      config_unavailable: "Hardware detection unavailable.",
      config_detecting: "Detecting hardware…",
      programs_title: "Recommended programs",
      programs_more: "See all",
      programs_less: "Show less"
    }
  };

  /* Jeux proposés en complément quand peu de jeux sont détectés (héros). */
  var SUGGEST = ["valorant", "apex_legends", "league_of_legends", "fortnite", "overwatch2", "rocket_league"];
  /* Repli si /api/games n'a pas encore répondu (premier affichage). */
  var FALLBACK_GAMES = [{ id: "cs2", name: "Counter-Strike 2", store: "steam", installed: false }];

  /* Point focal du visuel « hero » par jeu (sujet souvent hors du centre
     des bannières très larges) : cadrage object-position ET origine du zoom
     Ken Burns. CS2 : les deux soldats (CT 58-82 %, T 80-93 % de la largeur) ;
     Apex : visage de Valkyrie ; Fortnite : le bas de l'image, le panneau
     « FORTNITE » (déjà un titre) passe sous le voile du haut. */
  var HERO_FOCUS = {
    cs2: "84% 30%",
    apex_legends: "90% 25%",
    fortnite: "50% 100%",
    league_of_legends: "50% 22%"
  };

  /* Visuels « hero » qui portent déjà le nom du jeu en grand (panneau
     « FORTNITE ») : pas de mini-libellé sur leur vignette, titre texte plus
     discret sur la diapo (bannière d'origine seulement). */
  var ART_PRINTED = { fortnite: 1 };

  var ROTATE_MS = 10000;   /* rotation du héros (via l'animation de la barre) */
  var LIVE_MS = 2000;      /* relevé /api/monitor tant que l'accueil est affiché */
  var HIST = 30;           /* points des mini-courbes */

  /* ------------------------------------------------------------------ */
  /* Icônes locales (style Lucide, trait 1.5 px, currentColor)           */
  /* ------------------------------------------------------------------ */

  var ICONS = {
    gpu: '<path d="M2 21V3"/><path d="M2 5h18a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2"/><path d="M7 17v3"/><path d="M11 17v3"/><circle cx="16" cy="11" r="2.5"/><path d="M6 9h3"/><path d="M6 13h3"/>',
    monitor: '<rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>',
    disk: '<path d="M22 12H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><path d="M6 16h.01"/><path d="M10 16h.01"/>',
    net: '<path d="M12 20h.01"/><path d="M2 8.82a15 15 0 0 1 20 0"/><path d="M5 12.86a10 10 0 0 1 14 0"/><path d="M8.5 16.43a5 5 0 0 1 7 0"/>',
    thermo: '<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>',
    left: '<path d="m15 18-6-6 6-6"/>',
    right: '<path d="m9 18 6-6-6-6"/>',
    arrow: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    pad: '<line x1="6" x2="10" y1="12" y2="12"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="15" x2="15.01" y1="13" y2="13"/><line x1="18" x2="18.01" y1="11" y2="11"/><rect width="20" height="12" x="2" y="6" rx="2"/>'
  };

  function svgIcon(name, cls) {
    return '<svg class="icon' + (cls ? " " + cls : "") + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      (ICONS[name] || "") + "</svg>";
  }

  /* ------------------------------------------------------------------ */
  /* État du module (conservé d'un rendu à l'autre)                      */
  /* ------------------------------------------------------------------ */

  var view = null;              /* vue affichée (une seule à la fois) */
  var lastRenderAt = 0;         /* re-rendu rapproché : pas de nouvelle entrée */
  var featuredId = null;        /* jeu mis en avant (gardé entre deux rendus) */
  var loadedUrls = Object.create(null);  /* images déjà affichées : pas de fondu */
  var failedUrls = Object.create(null);  /* 404 déjà constatés pendant la session */
  var artInfo = null;           /* GET /api/art (capacités + révisions) */
  var artInfoP = null;
  var artInfoAt = 0;            /* instant de la dernière lecture de /api/art */
  var sharedReq = Object.create(null);   /* requêtes partagées : {chemin: {p, at}} */
  var hist = { cpu: [], ram: [], net: [], at: 0 };   /* mini-courbes */
  var railLeft = 0;             /* position du carrousel (re-rendu rapproché) */
  var shownScore = null;        /* indice déjà affiché : pas de recomptage */
  var netPeak = 10;             /* échelle adaptative du débit réseau (Mb/s) */

  /* ------------------------------------------------------------------ */
  /* Utilitaires                                                         */
  /* ------------------------------------------------------------------ */

  function esc(v) {
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function nowMs() { return (window.performance && performance.now) ? performance.now() : Date.now(); }

  function motionLevel() {
    var m = root.getAttribute("data-motion");
    return m === "reduced" || m === "off" ? m : "max";
  }
  function isPaused() { return root.hasAttribute("data-motion-paused"); }
  /** Fenêtre affichée par-dessus l'accueil : QCM (ou écran du 1er
      lancement), modale (Boost, Boost CS2, benchmark en cours…) ou palette
      de commandes. L'accueil, caché ou flouté dessous, ne fait alors tourner
      aucune boucle (rAF, relevés, animations CSS). Appelé à chaque image par
      les boucles : lectures d'attributs seulement. */
  function overlayOpen() {
    var o = doc.getElementById("overlay-root");
    if (o && !o.hidden && o.firstElementChild) { return true; }
    var m = doc.getElementById("modal-root");
    if (m && !m.hidden && m.firstElementChild) { return true; }
    var pal = window.OverdrivePalette;
    try { return !!(pal && typeof pal.isOpen === "function" && pal.isOpen()); } catch (e) { return false; }
  }
  /** Effets complets (parallaxe, 3D, particules, dérive, compteurs). */
  function fxOn() { return motionLevel() === "max" && !isPaused(); }
  /** Au moins des fondus. */
  function fadeOn() { return motionLevel() !== "off" && !isPaused(); }

  /** Lecture JSON silencieuse (aucun bandeau : sections secondaires). */
  function getJSON(path) {
    return fetch(path, { cache: "no-store" }).then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    });
  }

  /** Même requête JSON lancée plusieurs fois en moins de ``ms`` (accueil
      reconstruit au démarrage, langue…) : une seule requête réseau. */
  function sharedJSON(path, ms) {
    var e = sharedReq[path], t = Date.now();
    if (e && t - e.at < ms) { return e.p; }
    var p = getJSON(path);
    sharedReq[path] = { p: p, at: t };
    return p;
  }

  /** Capacités et révisions des visuels. Relues à chaque rendu (route
      locale, sans réseau, quelques ms) : une image personnalisée ou arrivée
      plus tard est prise en compte sans recharger l'application. En échec,
      les dernières infos connues restent (sinon : tout tenter). */
  function loadArtInfo(force) {
    if (artInfoP && !force) { return artInfoP; }
    artInfoAt = Date.now();
    var p = getJSON("/api/art").then(function (d) {
      if (d && typeof d === "object") { artInfo = d; } else if (!artInfo) { artInfo = {}; }
      return artInfo;
    }).catch(function () {
      if (!artInfo) { artInfo = {}; }
      return artInfo;
    });
    artInfoP = p;
    return p;
  }
  /* Lancée dès le chargement du script : prête au premier rendu. */
  try { loadArtInfo(); } catch (e0) { /* réseau indisponible : replis visuels */ }

  /* Visuel personnalisé ou réinitialisé dans les Réglages (app.js) : tout
     est relu au prochain affichage, échecs mémorisés compris. */
  /* Benchmark terminé : l'historique en cache partagé est périmé. */
  window.addEventListener("overdrive:bench-done", function () {
    delete sharedReq["/api/bench/history"];
  });

  window.addEventListener("overdrive:art-changed", function () {
    artInfoP = null;
    artInfo = null;
    failedUrls = Object.create(null);
  });

  function artSource(id) {
    var info = artInfo && artInfo[id];
    return info && info.source ? String(info.source) : "";
  }

  /** Types d'image à essayer, filtrés par /api/art quand il est connu. */
  function kindsFor(id, wanted) {
    var info = artInfo && artInfo[id];
    if (!info || !info.kinds) { return wanted.slice(); }
    return wanted.filter(function (k) { return info.kinds[k] !== false; });
  }

  function artUrl(id, kind) {
    var info = artInfo && artInfo[id];
    var rev = info && info.rev ? info.rev[kind] : 0;
    return "/api/art/" + encodeURIComponent(id) + "/" + encodeURIComponent(kind) + (rev ? "?v=" + encodeURIComponent(rev) : "");
  }

  /** Balise <img> d'art (src posée par bindArt, avec chaîne de replis). */
  function artImg(id, kinds, cls, alt, defer) {
    return '<img class="' + cls + '" data-art="' + esc(id) + '" data-kinds="' + esc(kinds.join(",")) +
      '" alt="' + esc(alt || "") + '" decoding="async" draggable="false"' + (defer ? " data-defer" : "") + ">";
  }

  /** Lance le chargement des images différées d'un élément (diapo activée). */
  function startArt(el) {
    if (!el) { return; }
    Array.prototype.forEach.call(el.querySelectorAll("img[data-defer]"), function (img) {
      if (img.__artStart) { img.__artStart(); }
    });
  }

  /** Branche les images d'art d'un conteneur : 1er type disponible, repli au
      suivant sur erreur, classe is-loaded / is-missing sur l'hôte [data-art-host].
      Images [data-defer] : chargées seulement à l'appel de startArt (diapos
      inactives du héros). img.__artRetry() retente un type mieux placé dont
      l'URL a changé (visuel arrivé plus tard côté serveur) ; img.__onSettle
      (facultatif) est appelé une fois avec le résultat. */
  function bindArt(scope) {
    var list = scope.querySelectorAll("img[data-art]:not([data-bound])");
    Array.prototype.forEach.call(list, function (img) {
      img.setAttribute("data-bound", "1");
      var id = img.getAttribute("data-art");
      var wanted = (img.getAttribute("data-kinds") || "").split(",").filter(Boolean);
      var kinds = kindsFor(id, wanted);
      var host = img.closest("[data-art-host]") || img.parentNode;
      var i = -1;
      var url = "";
      if (img.closest(".hm-cover, .hm-thumb")) { img.loading = "lazy"; }
      function settle(ok) {
        /* À retenter plus tard : aucune image, ou repli sur un type moins bon. */
        img.__artPending = !ok || i > 0;
        if (host) {
          host.classList.toggle("is-loaded", ok);
          host.classList.toggle("is-missing", !ok);
          /* Jaquette composée : fond flou (art « hero » derrière un portrait,
             sinon la même image) pour remplir le format 2:3. */
          var blur = ok ? host.querySelector(".hm-cover-blur") : null;
          var kind = host.getAttribute("data-kind");
          if (blur) {
            var bg = "";
            if (kind === "portrait") {
              if (kindsFor(id, ["hero"]).length && !failedUrls[artUrl(id, "hero")]) { bg = artUrl(id, "hero"); }
            } else if (kind !== "cover") {
              bg = url;
            }
            if (bg) { blur.style.setProperty("--bg", 'url("' + bg + '")'); } else { blur.style.removeProperty("--bg"); }
          }
          /* Visuel paysage haute définition dans une jaquette 2:3 (ex.
             Fortnite) : recadré plein cadre comme sur la page Jeux, au lieu
             d'un bandeau en letterbox. header.jpg 460×215 garde le fond flou. */
          if (host.classList.contains("hm-cover-art")) {
            var h = host.clientHeight || 258;
            host.classList.toggle("is-crop", !!ok && (kind === "hero" || kind === "header") && img.naturalHeight >= 2 * h);
          }
        }
        var hook = img.__onSettle;
        if (hook) {
          img.__onSettle = null;
          try { hook(ok); } catch (e) { /* sans effet */ }
        }
      }
      function next() {
        i++;
        while (i < kinds.length && failedUrls[artUrl(id, kinds[i])]) { i++; }
        if (i >= kinds.length) {
          img.removeAttribute("src");
          settle(false);
          return;
        }
        url = artUrl(id, kinds[i]);
        if (host) {
          host.setAttribute("data-kind", kinds[i]);
          host.classList.toggle("is-instant", !!loadedUrls[url]);
        }
        img.src = url;
      }
      img.addEventListener("load", function () {
        if (!img.naturalWidth) { failedUrls[url] = 1; next(); return; }
        loadedUrls[url] = 1;
        if (img.classList.contains("hm-logo") && host) { host.classList.toggle("is-dark", logoIsDark(img, url)); }
        settle(true);
      });
      img.addEventListener("error", function () {
        failedUrls[url] = 1;
        next();
      });
      img.__artRetry = function () {
        if (img.hasAttribute("data-defer") || !img.__artPending) { return; }
        var fresh = kindsFor(id, wanted);
        var cur = i < kinds.length ? fresh.indexOf(kinds[i]) : -1;
        var limit = cur >= 0 ? cur : fresh.length;
        for (var j = 0; j < limit; j++) {
          if (!failedUrls[artUrl(id, fresh[j])]) {
            kinds = fresh;
            i = -1;
            next();
            return;
          }
        }
      };
      img.__artStart = function () {
        img.removeAttribute("data-defer");
        if (i < 0) { next(); }
      };
      if (!img.hasAttribute("data-defer")) { next(); }
    });
  }

  /** Logo surtout sombre (lettres noires/grises) ? Il serait illisible sur le
      héros : on l'affiche alors en blanc (filtre CSS). Résultat mémorisé. */
  var darkLogos = Object.create(null);
  function logoIsDark(img, url) {
    if (Object.prototype.hasOwnProperty.call(darkLogos, url)) { return darkLogos[url]; }
    var dark = false;
    try {
      var c = doc.createElement("canvas");
      c.width = 64;
      c.height = 36;
      var g = c.getContext("2d");
      g.drawImage(img, 0, 0, 64, 36);
      var px = g.getImageData(0, 0, 64, 36).data;
      var n = 0, darkN = 0;
      for (var i = 0; i < px.length; i += 4) {
        if (px[i + 3] < 128) { continue; }
        n++;
        var lum = (0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255;
        if (lum < 0.32) { darkN++; }
      }
      dark = n > 20 && darkN / n > 0.4;
    } catch (e) { dark = false; }
    darkLogos[url] = dark;
    return dark;
  }

  /** Nom de GPU lisible (« (TM) », « (R) » retirés). */
  function cleanName(s) {
    return String(s || "").replace(/\((TM|R|C)\)/gi, "").replace(/\s*@\s*[\d.,]+\s*GHz\s*$/i, "")
      .replace(/\s+\d+-Core Processor\s*$/i, "")
      .replace(/\s+(CPU|Processor)\s*$/i, "").replace(/\s{2,}/g, " ").trim();
  }

  /** GPU principal : le plus de VRAM, une carte dédiée de préférence. */
  function mainGpu(hw) {
    var gpus = (hw && hw.gpus) || [];
    if (!gpus.length) { return null; }
    var best = null, bestScore = -1;
    gpus.forEach(function (g) {
      var name = String(g.name || "");
      var score = (Number(g.vram_mb) || 0) + (/\b(RX|RTX|GTX|Arc|Radeon Pro|Quadro)\b/i.test(name) ? 1e6 : 0);
      if (score > bestScore) { bestScore = score; best = g; }
    });
    return best;
  }

  /* ------------------------------------------------------------------ */
  /* Rendu                                                               */
  /* ------------------------------------------------------------------ */

  function render(pageEl, ctx) {
    stop();
    if (!pageEl || !ctx) { return; }
    /* Visuels relus à chaque affichage (sauf lecture toute récente). */
    if (!artInfoP || Date.now() - artInfoAt > 1500) { loadArtInfo(true); }
    var t = Date.now();
    /* Re-rendu rapproché (langue, retour de modale…) : pas de seconde entrée.
       Sous 400 ms (démarrage : 2e rendu après /api/status), l'entrée à peine
       commencée est simplement rejouée. */
    var dt = t - lastRenderAt;
    /* Même page re-rendue (ctx.sameRoute : langue changée plus tard, retour
       de modale…) : jamais de seconde entrée, quel que soit le délai. */
    var quick = dt >= 400 && (dt < 2500 || !!ctx.sameRoute);
    lastRenderAt = t;
    view = createView(pageEl, ctx, quick);
  }

  function stop() {
    if (view) {
      var v = view;
      view = null;
      v.destroy();
    }
  }

  function isActive() { return !!view; }

  /* ------------------------------------------------------------------ */
  /* Vue                                                                 */
  /* ------------------------------------------------------------------ */

  function createView(page, ctx, quick) {
    var dead = false;
    var timers = [];
    var unlisten = [];
    var observers = [];
    var rafs = [];

    /* ---- aides de durée de vie ---- */

    function on(target, type, fn, opts) {
      target.addEventListener(type, fn, opts);
      unlisten.push(function () { target.removeEventListener(type, fn, opts); });
    }
    function later(fn, ms) {
      var id = setTimeout(function () {
        var k = timers.indexOf(id);
        if (k >= 0) { timers.splice(k, 1); }
        if (!dead) { fn(); }
      }, ms);
      timers.push(id);
      return id;
    }
    function cancel(id) {
      if (!id) { return; }
      clearTimeout(id);
      var k = timers.indexOf(id);
      if (k >= 0) { timers.splice(k, 1); }
    }
    /** Vue toujours affichée ? Sinon elle se détruit (filet de sécurité). */
    function ok() {
      if (dead) { return false; }
      var alive = true;
      try { alive = typeof ctx.alive === "function" ? !!ctx.alive() : true; } catch (e) { alive = false; }
      if (!alive || !rootEl || !rootEl.isConnected) {
        if (view === api) { view = null; }
        destroy();
        return false;
      }
      return true;
    }

    /* ---- traduction ---- */

    function lang() {
      var l = "fr";
      try { l = typeof ctx.lang === "function" ? ctx.lang() : root.lang; } catch (e) { l = root.lang; }
      return String(l || "fr").slice(0, 2).toLowerCase() === "en" ? "en" : "fr";
    }
    function s(key, repl) {
      var d = STR[lang()] || STR.fr;
      var str = Object.prototype.hasOwnProperty.call(d, key) ? d[key] : (STR.fr[key] || key);
      if (repl) {
        Object.keys(repl).forEach(function (k) { str = str.split("{" + k + "}").join(String(repl[k])); });
      }
      return str;
    }
    function T(key) {
      try { return ctx.t(key); } catch (e) { return key; }
    }
    function trf(obj, field) {
      try { return ctx.tr(obj, field); } catch (e) { return obj ? (obj[field] || "") : ""; }
    }
    function appIcon(name) {
      try { return ctx.icon(name); } catch (e) { return ""; }
    }
    function dec(x) {
      var str = String(x);
      return lang() === "en" ? str : str.replace(".", ",");
    }
    function gb(v) {
      try { return ctx.fmtGb(v); } catch (e) { return dec(Math.round(v * 10) / 10) + " Go"; }
    }
    function tierLabel(tier) {
      if (!tier) { return ""; }
      var k = "tier_" + tier;
      var l = T(k);
      return l === k ? tier : l;
    }
    /** Monogramme et teinte des visuels de secours : mêmes règles que la page
        Jeux (app.js artMonogram / artTurn, « LoL », « CS2 »…). */
    function monogram(name) {
      try { if (typeof ctx.artMonogram === "function") { return ctx.artMonogram(name); } } catch (e) { /* repli */ }
      return String(name || "").replace(/[^A-Za-z0-9 ]/g, " ").trim().split(/\s+/).map(function (w) { return w.charAt(0); }).join("").slice(0, 3).toUpperCase();
    }
    function artHue(id) {
      try { if (typeof ctx.artTurn === "function") { return ctx.artTurn(id); } } catch (e) { /* repli */ }
      var h = 0;
      for (var k = 0; k < id.length; k++) { h = (h * 31 + id.charCodeAt(k)) % 360; }
      return h;
    }
    /** Décalage de teinte du visuel de secours (±35°, même règle que la
        page Jeux, app.js artFbHue). */
    function artFbHue(id) {
      try { if (typeof ctx.artFbHue === "function") { return Number(ctx.artFbHue(id)) || 0; } } catch (e) { /* repli */ }
      return (artHue(id) % 71) - 35;
    }
    function artFocus(id) {
      try { return typeof ctx.artFocus === "function" ? String(ctx.artFocus(id) || "") : ""; } catch (e) { return ""; }
    }
    function storeName(id) {
      try { return typeof ctx.storeLabel === "function" ? ctx.storeLabel(id) : (id || ""); } catch (e) { return id || ""; }
    }
    function greeting() {
      var h = new Date().getHours();
      var g = h >= 5 && h < 12 ? s("greet_morning") : (h >= 12 && h < 18 ? s("greet_afternoon") : s("greet_evening"));
      return g + " — " + s("greet_tail");
    }

    /* ---- squelette ---- */

    var awaitIntro = false;
    try {
      awaitIntro = !!(window.OverdriveIntro && typeof window.OverdriveIntro.isActive === "function" &&
        window.OverdriveIntro.isActive());
    } catch (e1) { awaitIntro = false; }
    /* Entrée : premier rendu, ou rendu caché sous l'intro (rien n'a été vu). */
    var entrance = fadeOn() && (awaitIntro || !quick);
    /* Rendu sous un QCM déjà ouvert : l'entrée attend sa fermeture. */
    var coveredAtStart = !awaitIntro && entrance && overlayOpen();

    page.innerHTML =
      '<div class="hm-root' + (entrance && !coveredAtStart ? " hm-entering" : "") +
      (awaitIntro || coveredAtStart ? " hm-await-intro" : "") + '">' +
      '<div class="hm-pfield" aria-hidden="true"><canvas class="hm-particles"></canvas>' +
      '<span class="hm-pcolor"></span></div>' +
      heroShellHtml() +
      /* Jaquettes juste sous le héros : les vraies images sont visibles
         sans défiler, même à la taille de fenêtre par défaut. */
      gamesShellHtml() +
      perfHtml() +
      actionsHtml() +
      '<section class="hm-sec hm-insights-sec" aria-labelledby="hm-ins-title">' +
      '<div class="hm-sec-head"><h2 class="hm-sec-title" id="hm-ins-title">' + esc(s("insights_title")) + "</h2></div>" +
      '<div class="hm-insights" id="hm-insights"><div class="hm-skel hm-skel-ins"></div><div class="hm-skel hm-skel-ins"></div></div>' +
      "</section>" +
      '<section class="hm-sec hm-config-sec" aria-labelledby="hm-cfg-title">' +
      '<div class="hm-sec-head"><h2 class="hm-sec-title" id="hm-cfg-title">' + esc(s("config_title")) + "</h2>" +
      '<span class="hm-spacer"></span>' +
      '<button class="hm-ghost-btn" type="button" id="hm-hw-refresh">' + appIcon("refresh") + "<span>" + esc(T("refresh")) + "</span></button></div>" +
      '<div class="hm-panel hm-config" id="hm-config"><div class="hm-config-wait">' + esc(s("config_detecting")) + "</div></div>" +
      "</section>" +
      '<section class="hm-sec hm-programs-sec" aria-labelledby="hm-prog-title">' +
      '<div class="hm-sec-head"><h2 class="hm-sec-title" id="hm-prog-title">' + esc(s("programs_title")) + "</h2>" +
      '<span class="hm-spacer"></span>' +
      '<button class="hm-ghost-btn hm-prog-more" type="button" id="hm-prog-more" aria-expanded="false" aria-controls="programs-area">' +
      esc(s("programs_more")) + "</button></div>" +
      '<div id="programs-area"><div class="loading-line">' + esc(T("programs_loading")) + "</div></div>" +
      "</section>" +
      "</div>";

    var rootEl = page.querySelector(".hm-root");
    var heroEl = rootEl.querySelector(".hm-hero");
    var slidesEl = rootEl.querySelector(".hm-slides");
    var statesEl = rootEl.querySelector(".hm-states");
    var mainEl = rootEl.querySelector(".hm-main");
    var mainFg = mainEl.querySelector(".hm-par-fg");
    var logosEl = mainEl.querySelector(".hm-logos");
    var primsEl = mainEl.querySelector(".hm-prims");
    var boostEl = mainEl.querySelector(".hm-boost-wrap");
    var glareEl = rootEl.querySelector(".hm-glare");
    var switchEl = rootEl.querySelector(".hm-switch");
    var railEl = rootEl.querySelector(".hm-rail");

    var api = { destroy: destroy };

    /* ================================================================ */
    /* 1. Héros                                                         */
    /* ================================================================ */

    /* Contenu du héros : la colonne (puce « Ta machine », « Boost général »)
       est STATIQUE, rendue une seule fois ; seuls l'état, le logo et le
       bouton principal changent d'un jeu à l'autre (emplacements empilés
       .hm-states / .hm-logos / .hm-prims) : rien ne « saute » à la rotation. */
    function heroShellHtml() {
      return '<section class="hm-hero" aria-roledescription="carousel" aria-label="' + esc(s("hero_aria")) + '">' +
        '<div class="hm-hero-stage">' +
        '<div class="hm-slides" aria-hidden="true"></div>' +
        '<div class="hm-veil" aria-hidden="true"></div>' +
        '<div class="hm-tint" aria-hidden="true"></div>' +
        '<div class="hm-grain" aria-hidden="true"></div>' +
        '<div class="hm-sheen" aria-hidden="true"></div>' +
        '<div class="hm-glare" aria-hidden="true"></div>' +
        '<div class="hm-states" aria-hidden="true"></div>' +
        '<div class="hm-hero-top">' +
        '<h1 class="page-title hm-greet"><span class="hm-greet-dot" aria-hidden="true"></span>' + esc(greeting()) + "</h1>" +
        "</div>" +
        '<div class="hm-main" role="group" aria-roledescription="slide">' +
        '<div class="hm-par hm-par-fg">' +
        '<div class="hm-logos"></div>' +
        '<div class="hm-chips hm-rise" style="--d:1"><span class="hm-chip hm-chip-machine">' + svgIcon("gpu") +
        '<span class="hm-machine-txt">' + esc(machineChipText()) + "</span></span></div>" +
        '<div class="hm-cta"><div class="hm-prims"></div>' +
        '<span class="hm-boost-wrap hm-rise" style="--d:2">' +
        '<button class="hm-btn hm-btn-glass" type="button" data-act="boost">' + appIcon("sparkles") +
        "<span>" + esc(s("hero_boost_general")) + "</span></button></span></div>" +
        "</div></div>" +
        '<div class="hm-switch" role="tablist" aria-label="' + esc(s("hero_switch_aria")) + '"></div>' +
        "</div></section>";
    }

    var slides = [];        /* [{id, name, installed, suggest, game}] */
    var activeIdx = 0;
    var heroTier = null;
    var heroGpu = null;

    function machineChipText() {
      var tier = tierLabel(heroTier);
      var parts = [];
      if (tier) { parts.push(tier); }
      if (heroGpu) { parts.push(heroGpu); }
      return s("hero_machine_v", { v: parts.length ? parts.join(" · ") : s("hero_machine_wait") });
    }

    /** Jeu sans logo mais avec un personnage détouré (Valorant) : le
        portrait est posé en plan avant sur la diapo, comme sur la page Jeux. */
    function slidePortrait(id) {
      var info = artInfo && artInfo[id];
      return !!(info && info.kinds && info.kinds.portrait && !info.kinds.logo);
    }

    /** Point focal du héros : aucun pour une bannière personnalisée (son
        cadrage n'a rien à voir avec le visuel d'origine). */
    function heroFocus(id) {
      var info = artInfo && artInfo[id];
      if (info && (info.custom || []).indexOf("hero") >= 0) { return ""; }
      return HERO_FOCUS[id] || "";
    }

    /* Plan image d'une diapositive (sous les voiles). */
    function slideHtml(sl, idx, defer) {
      var src = artSource(sl.id);
      var focus = heroFocus(sl.id);
      return '<div class="hm-slide hm-kb-' + (idx % 3) + '" data-game="' + esc(sl.id) + '">' +
        '<div class="hm-slide-media" data-art-host' + (src ? ' data-source="' + esc(src) + '"' : "") +
        (focus ? ' style="--hfocus:' + esc(focus) + '"' : "") + ">" +
        '<div class="hm-par hm-par-bg">' +
        '<div class="hm-kb">' +
        '<div class="hm-fallback"><span class="hm-fb-blob hm-fb-1"></span>' +
        '<span class="hm-fb-blob hm-fb-2"></span><span class="hm-fb-blob hm-fb-3"></span></div>' +
        artImg(sl.id, ["hero", "header"], "hm-slide-img", "", defer) +
        "</div></div></div>" +
        (slidePortrait(sl.id) ?
          '<div class="hm-slide-pt" data-art-host>' + artImg(sl.id, ["portrait"], "hm-slide-portrait", "", defer) + "</div>" : "") +
        "</div>";
    }

    function stateText(sl) {
      return sl.installed ? s("hero_installed") : (sl.suggest ? s("hero_discover") : s("hero_not_detected"));
    }

    /* Éléments propres à chaque jeu, empilés dans leurs emplacements ; seul
       celui du jeu affiché est visible (.is-active). */
    function stateHtml(sl) {
      var stateCls = sl.installed ? "is-installed" : (sl.suggest ? "is-suggest" : "is-missing");
      return '<span class="hm-state hm-sw ' + stateCls + '" style="--d:0"><span class="hm-state-dot" aria-hidden="true"></span>' +
        esc(stateText(sl)) + "</span>";
    }
    function logoBoxHtml(sl, defer) {
      var src = artSource(sl.id);
      return '<div class="hm-logo-box hm-sw" style="--d:0" data-art-host' + (src ? ' data-source="' + esc(src) + '"' : "") +
        (ART_PRINTED[sl.id] && heroFocus(sl.id) ? " data-printed" : "") + ">" +
        artImg(sl.id, ["logo"], "hm-logo", sl.name, defer) +
        '<span class="hm-logo-text">' + esc(sl.name) + "</span></div>";
    }
    /* Bouton principal : libellé court « Optimiser » quand la colonne est
       étroite (requête de conteneur) ; le nom du jeu reste dans aria-label
       et title. */
    function primaryHtml(sl) {
      var full = sl.id === "cs2" ? T("cs2b_btn") : s("hero_optimize", { g: sl.name });
      var short = sl.id === "cs2" ? full : s("games_optimize");
      var attrs = sl.id === "cs2" ? 'data-act="cs2boost"' : 'data-act="game" data-game="' + esc(sl.id) + '"';
      return '<span class="hm-prim hm-sw" style="--d:1">' +
        '<button class="hm-btn hm-btn-primary" type="button" ' + attrs + ' aria-label="' + esc(full) + '" title="' + esc(full) + '">' +
        appIcon("zap") + '<span class="hm-lbl-long">' + esc(full) + '</span><span class="hm-lbl-short" aria-hidden="true">' + esc(short) + "</span>" +
        "</button></span>";
    }

    function thumbHtml(sl, idx) {
      var mono = monogram(sl.name || sl.id);
      /* Bannière personnalisée, ou header simple alias du héros (jeux non
         Steam) : même URL que la diapo, donc même image en cache (pas de
         second téléchargement / décodage d'un PNG de 2 Mo pour 106×50). */
      var info = artInfo && artInfo[sl.id];
      var useHero = !!(info && (info.source !== "steam" || (info.custom || []).indexOf("hero") >= 0 ||
        (info.rev && info.rev.header && info.rev.header === info.rev.hero)));
      /* Visuel sans nom imprimé (pas de logo : Valorant, LoL, Fortnite…) :
         mini-libellé (nom court, sinon monogramme « LoL »). */
      var noLogo = !!(info && info.kinds && info.kinds.logo === false && info.source !== "steam" &&
        !ART_PRINTED[sl.id] && (info.custom || []).indexOf("hero") < 0);
      var label = String(sl.name || sl.id);
      if (label.length > 12) { label = mono; }
      return '<button class="hm-thumb" type="button" role="tab" data-idx="' + idx + '" aria-selected="false" ' +
        'aria-label="' + esc(s("hero_show", { g: sl.name })) + '" title="' + esc(sl.name) + '">' +
        '<span class="hm-thumb-art" data-art-host><span class="hm-thumb-fb" aria-hidden="true">' + esc(mono) + "</span>" +
        artImg(sl.id, useHero ? ["hero", "cover"] : ["header", "hero", "cover"], "hm-thumb-img", "") + "</span>" +
        (noLogo ? '<span class="hm-thumb-name" aria-hidden="true">' + esc(label) + "</span>" : "") +
        '<span class="hm-thumb-bar" aria-hidden="true"><i></i></span></button>';
    }

    /** Liste du héros : CS2 + jeux détectés (CS2 d'abord, sinon le 1er
        détecté). Quelques jeux populaires la complètent jusqu'à 4 SEULEMENT
        s'il y a moins de 2 jeux disponibles (CS2 compris). */
    function heroList(games) {
      var byId = {};
      games.forEach(function (g) { byId[g.id] = g; });
      var installed = games.filter(function (g) { return g.installed; });
      var out = [];
      function push(g, suggest) {
        if (!g || out.some(function (x) { return x.id === g.id; })) { return; }
        out.push({ id: g.id, name: g.name || g.id, installed: !!g.installed, suggest: !!suggest && !g.installed, game: g });
      }
      var cs2 = byId.cs2 || FALLBACK_GAMES[0];
      if (cs2.installed || !installed.length) { push(cs2); }
      installed.forEach(function (g) { push(g); });
      push(cs2);
      if (out.length < 2) {
        for (var i = 0; i < SUGGEST.length && out.length < 4; i++) { push(byId[SUGGEST[i]], true); }
      }
      return out.slice(0, 6);
    }

    /** (Re)construit les diapositives ; réutilise celles déjà présentes. */
    function buildSlides(games) {
      var list = heroList(games);
      var same = list.length === slides.length && list.every(function (x, i) {
        return x.id === slides[i].id && x.installed === slides[i].installed && x.name === slides[i].name;
      });
      if (same) { return; }
      slides = list;
      /* Jeu gardé d'un rendu à l'autre seulement s'il a été CHOISI (vignette,
         clavier, rotation) : le rendu provisoire (CS2 seul) n'impose rien,
         le héros s'ouvre sur CS2 s'il est installé, sinon le 1er détecté. */
      var idx = 0;
      if (featuredId) {
        list.forEach(function (x, i) { if (x.id === featuredId) { idx = i; } });
      }
      activeIdx = -1;
      /* Seule la diapo affichée charge ses images ; les autres attendent
         leur tour (setActive) : moins de requêtes simultanées au démarrage. */
      slidesEl.innerHTML = list.map(function (sl, i) { return slideHtml(sl, i, i !== idx); }).join("");
      statesEl.innerHTML = list.map(stateHtml).join("");
      logosEl.innerHTML = list.map(function (sl, i) { return logoBoxHtml(sl, i !== idx); }).join("");
      primsEl.innerHTML = list.map(primaryHtml).join("");
      switchEl.innerHTML = list.length > 1 ? list.map(thumbHtml).join("") : "";
      switchEl.hidden = list.length <= 1;
      /* Nombre de vignettes : la colonne de gauche leur réserve la place
         (home.css, .hm-main), le texte ne passe jamais dessous. */
      heroEl.style.setProperty("--hm-n", String(list.length > 1 ? list.length : 0));
      bindArt(slidesEl);
      bindArt(logosEl);
      bindArt(switchEl);
      setActive(idx, true);
      holdIntro();
    }

    /** Intro encore affichée : elle attend que l'image du héros soit
        décodée (plafond géré par intro.js) pour se fondre sur un visuel
        déjà peint, pas sur un cadre vide. */
    function holdIntro() {
      var I = window.OverdriveIntro;
      try {
        if (!I || typeof I.waitFor !== "function" || !I.isActive()) { return; }
      } catch (e) { return; }
      var slide = slidesEl.children[activeIdx];
      var img = slide ? slide.querySelector("img.hm-slide-img") : null;
      var host = img ? img.closest("[data-art-host]") : null;
      if (!img || !host) { return; }
      I.waitFor(new Promise(function (resolve) {
        function done(okImg) {
          if (okImg && typeof img.decode === "function") { img.decode().then(resolve, resolve); } else { resolve(); }
        }
        if (host.classList.contains("is-loaded") || host.classList.contains("is-missing")) {
          done(host.classList.contains("is-loaded"));
        } else {
          img.__onSettle = done;
        }
      }));
    }

    var preTimer = 0;

    var parResetTimer = 0;

    function setActive(idx, initial) {
      if (!slides.length) { return; }
      idx = (idx + slides.length) % slides.length;
      if (idx === activeIdx && !initial) { return; }
      var prevIdx = activeIdx;
      activeIdx = idx;
      /* Mémorisé seulement pour un vrai choix (vignette, clavier, rotation). */
      if (!initial) { featuredId = slides[idx].id; }
      /* Position du bouton « Boost général » avant le changement de libellé
         du bouton principal (glissement doux plutôt qu'un saut). */
      var boostX = !initial && fadeOn() && boostEl ? boostEl.getBoundingClientRect().left : null;
      var slideEls = slidesEl.children;
      var groups = [statesEl.children, logosEl.children, primsEl.children];
      /* Éléments sortants : fondu de 300 ms (classe is-leaving) PENDANT
         que ceux du nouveau jeu montent (fondu croisé, aucun trou). */
      var leaving = [];
      if (!initial && prevIdx >= 0 && fadeOn()) {
        groups.forEach(function (g) { if (g[prevIdx]) { leaving.push(g[prevIdx]); } });
      }
      for (var i = 0; i < slideEls.length; i++) {
        var on = i === idx;
        var inst = !!initial && on && !entrance;
        var sEl = slideEls[i];
        if (on && sEl.classList.contains("is-prev")) {
          /* Re-sélectionnée pendant son fondu de sortie : le Ken Burns
             repart de zéro (nouvelle passe complète). */
          cancel(sEl.__prevTimer);
          sEl.classList.remove("is-prev");
          var kbEl = sEl.querySelector(".hm-kb");
          if (kbEl) { kbEl.style.animation = "none"; void kbEl.offsetWidth; kbEl.style.animation = ""; }
        }
        if (!on && i === prevIdx && prevIdx !== idx) {
          /* Diapo sortante : elle garde son Ken Burns (dernière image) le
             temps d'être recouverte par l'entrante (fondu de 1 s). */
          sEl.classList.add("is-prev");
          cancel(sEl.__prevTimer);
          sEl.__prevTimer = later((function (el) {
            return function () { if (!el.classList.contains("is-active")) { el.classList.remove("is-prev"); } };
          })(sEl), 1150);
        }
        sEl.classList.toggle("is-active", on);
        sEl.classList.toggle("is-instant", inst);
        groups.forEach(function (g) {
          var el = g[i];
          if (!el) { return; }
          el.classList.toggle("is-active", on);
          el.classList.toggle("is-instant", inst);
        });
        var prim = primsEl.children[i];
        if (prim) {
          if (on) { prim.removeAttribute("inert"); prim.removeAttribute("aria-hidden"); }
          else { prim.setAttribute("inert", ""); prim.setAttribute("aria-hidden", "true"); }
        }
        var logo = logosEl.children[i];
        if (logo) { logo.setAttribute("aria-hidden", on ? "false" : "true"); }
      }
      leaving.forEach(function (el) {
        el.classList.remove("is-leaving");
        void el.offsetWidth;
        el.classList.add("is-leaving");
        later(function () { el.classList.remove("is-leaving"); }, 340);
      });
      mainEl.setAttribute("aria-label", slides[idx].name + " — " + stateText(slides[idx]));
      var thumbs = switchEl.children;
      for (var j = 0; j < thumbs.length; j++) {
        var act = j === idx;
        thumbs[j].classList.toggle("is-active", act);
        thumbs[j].setAttribute("aria-selected", act ? "true" : "false");
        thumbs[j].tabIndex = act ? 0 : -1;
      }
      if (boostX !== null) {
        var dx = boostX - boostEl.getBoundingClientRect().left;
        if (Math.abs(dx) > 1 && typeof boostEl.animate === "function") {
          try {
            boostEl.animate([{ transform: "translate3d(" + dx.toFixed(1) + "px, 0, 0)" }, { transform: "none" }],
              { duration: 520, easing: "cubic-bezier(.2, .8, .2, 1)" });
          } catch (e) { /* sans animation */ }
        }
      }
      startArt(slideEls[idx]);
      startArt(logosEl.children[idx]);
      /* Parallaxe : la nouvelle diapo part de la position courante du
         pointeur ; l'ancienne est remise à zéro une fois son fondu fini. */
      applyParallax();
      cancel(parResetTimer);
      if (prevIdx >= 0 && prevIdx !== idx) {
        parResetTimer = later(function () {
          Array.prototype.forEach.call(slidesEl.children, function (sl, k) {
            if (k === activeIdx) { return; }
            Array.prototype.forEach.call(sl.querySelectorAll(".hm-par-bg, .hm-slide-pt"), function (p) { p.style.transform = ""; });
          });
        }, 1100);
      }
      /* Diapo suivante préchargée bien avant la rotation (10 s). */
      cancel(preTimer);
      if (slides.length > 1) {
        preTimer = later(function () {
          var n = (activeIdx + 1) % slides.length;
          startArt(slidesEl.children[n]);
          startArt(logosEl.children[n]);
        }, 3500);
      }
    }

    function updateMachineChips() {
      var txt = machineChipText();
      Array.prototype.forEach.call(rootEl.querySelectorAll(".hm-machine-txt"), function (el) {
        el.textContent = txt;
      });
    }

    /* Rotation : la fin de l'animation de la barre (10 s, figée au survol,
       en jeu ou sans animations) fait passer au jeu suivant. */
    on(switchEl, "animationend", function (e) {
      if (e.animationName !== "hm-progress" || !ok()) { return; }
      if (!fxOn() || doc.hidden) { return; }
      setActive(activeIdx + 1, false);
    });
    on(switchEl, "click", function (e) {
      var b = e.target.closest(".hm-thumb");
      if (!b || !switchEl.contains(b)) { return; }
      setActive(Number(b.getAttribute("data-idx")) || 0, false);
    });
    on(switchEl, "keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") { return; }
      e.preventDefault();
      setActive(activeIdx + (e.key === "ArrowRight" ? 1 : -1), false);
      var b = switchEl.children[activeIdx];
      if (b) { b.focus(); }
    });

    /* Boutons d'action (héros, tuiles, carrousel) : délégation unique. */
    on(rootEl, "click", function (e) {
      var b = e.target.closest("[data-act]");
      if (!b || !rootEl.contains(b) || b.disabled) { return; }
      var act = b.getAttribute("data-act");
      try {
        if (act === "cs2boost") { ctx.openCs2Boost(); }
        else if (act === "boost") { ctx.openBoost(); }
        else if (act === "bench") { ctx.openBench(); }
        else if (act === "clean") { ctx.quickClean(); }
        else if (act === "widget") { ctx.launchWidget(b); }
        else if (act === "tweaks") { ctx.go("#/tweaks"); }
        else if (act === "insights") {
          var sec = rootEl.querySelector(".hm-insights-sec");
          if (sec) { sec.scrollIntoView({ behavior: fxOn() ? "smooth" : "auto", block: "start" }); }
        }
        else if (act === "game") { ctx.openGame(b.getAttribute("data-game")); }
      } catch (err) {
        if (window.console) { console.error(err); }
      }
    });

    /* Parallaxe (souris) : une écriture par image au plus, DIRECTEMENT sur
       le transform des seuls plans visibles (fond et portrait de la diapo
       active, colonne de contenu) ; le reflet lit --gx / --gy posés sur
       lui-même. Pas de variable héritée sur le héros : modifier une
       propriété personnalisée à la racine recalculait le style de tout le
       sous-arbre (≈ 200 éléments) à chaque image. Les plans suivent par
       transition CSS (diapo active uniquement). */
    var parRaf = 0, parX = 0, parY = 0, parGx = 50, parGy = 30;
    function px(v) { return v.toFixed(2) + "px"; }
    function applyParallax() {
      var sl = activeIdx >= 0 ? slidesEl.children[activeIdx] : null;
      var bg = sl ? sl.querySelector(".hm-par-bg") : null;
      var pt = sl ? sl.querySelector(".hm-slide-pt") : null;
      if (bg) { bg.style.transform = parX || parY ? "translate3d(" + px(parX * -18) + ", " + px(parY * -11) + ", 0)" : ""; }
      if (pt) { pt.style.transform = parX || parY ? "translate3d(" + px(parX * 14) + ", " + px(parY * 6) + ", 0)" : ""; }
      if (mainFg) { mainFg.style.transform = parX || parY ? "translate3d(" + px(parX * 7) + ", " + px(parY * 5) + ", 0)" : ""; }
    }
    function parFrame() {
      parRaf = 0;
      if (dead) { return; }
      applyParallax();
      glareEl.style.setProperty("--gx", parGx.toFixed(1) + "%");
      glareEl.style.setProperty("--gy", parGy.toFixed(1) + "%");
    }
    on(heroEl, "pointermove", function (e) {
      if (!fxOn() || e.pointerType === "touch") { return; }
      var r = heroEl.getBoundingClientRect();
      if (!r.width || !r.height) { return; }
      var nx = (e.clientX - r.left) / r.width, ny = (e.clientY - r.top) / r.height;
      parX = clamp(nx * 2 - 1, -1, 1);
      parY = clamp(ny * 2 - 1, -1, 1);
      parGx = nx * 100;
      parGy = ny * 100;
      heroEl.classList.add("is-pointer");
      if (!parRaf) { parRaf = requestAnimationFrame(parFrame); }
    });
    /* Annulation à la destruction : enregistrée UNE fois (pas à chaque image). */
    rafs.push(function () { if (parRaf) { cancelAnimationFrame(parRaf); parRaf = 0; } });
    on(heroEl, "pointerleave", resetParallax);
    function resetParallax() {
      parX = 0; parY = 0;
      heroEl.classList.remove("is-pointer");
      if (parRaf) { cancelAnimationFrame(parRaf); parRaf = 0; }
      applyParallax();
    }

    /* ================================================================ */
    /* 2. Indice de performance + tuiles LIVE                           */
    /* ================================================================ */

    function perfHtml() {
      var ticks = "";
      for (var i = 0; i < 60; i++) {
        var a = (i / 60) * Math.PI * 2;   /* le SVG est tourné de -90° : départ à midi */
        var r1 = 93, r2 = i % 5 === 0 ? 86 : 89;
        ticks += '<line class="hm-tick" style="--t:' + i + '" x1="' + (100 + r1 * Math.cos(a)).toFixed(2) + '" y1="' +
          (100 + r1 * Math.sin(a)).toFixed(2) + '" x2="' + (100 + r2 * Math.cos(a)).toFixed(2) + '" y2="' +
          (100 + r2 * Math.sin(a)).toFixed(2) + '"/>';
      }
      return '<section class="hm-sec hm-perf" aria-label="' + esc(s("perf_title")) + '">' +
        '<div class="hm-panel hm-index hm-wave-in" style="--w:0">' +
        '<div class="hm-ring-wrap" tabindex="0" aria-describedby="hm-perf-tip">' +
        '<svg class="hm-ring" viewBox="0 0 200 200" aria-hidden="true" focusable="false">' +
        '<defs><linearGradient id="hm-ring-grad" x1="0" y1="0" x2="1" y2="1">' +
        '<stop offset="0" class="hm-stop-a"/><stop offset="1" class="hm-stop-b"/></linearGradient></defs>' +
        '<g class="hm-ticks">' + ticks + "</g>" +
        '<circle class="hm-ring-track" cx="100" cy="100" r="74"/>' +
        '<circle class="hm-ring-arc" cx="100" cy="100" r="74" pathLength="100"/>' +
        "</svg>" +
        '<div class="hm-ring-center"><span class="hm-score">—</span><span class="hm-score-max">/100</span></div>' +
        "</div>" +
        '<div class="hm-index-info">' +
        '<div class="hm-eyebrow-row"><span class="hm-eyebrow">' + esc(s("perf_title")) + "</span>" +
        '<button class="hm-info-btn" type="button" aria-label="' + esc(s("perf_how")) + '" aria-describedby="hm-perf-tip">' +
        svgIcon("info") + "</button></div>" +
        '<div class="hm-band" data-band=""><span class="hm-band-dot" aria-hidden="true"></span>' +
        '<span class="hm-band-text">' + esc(s("perf_loading")) + "</span></div>" +
        '<p class="hm-index-desc"></p>' +
        '<div class="hm-index-actions">' +
        '<button class="hm-soft-btn" type="button" id="hm-next" hidden></button>' +
        "</div></div>" +
        '<div class="hm-breakdown" aria-hidden="true"></div>' +
        '<div class="hm-tip" id="hm-perf-tip" role="tooltip"></div>' +
        "</div>" +
        '<div class="hm-live">' +
        tileHtml("cpu", s("live_cpu"), appIcon("cpu"), 1) +
        tileHtml("ram", s("live_ram"), appIcon("memory"), 2) +
        tileHtml("net", s("live_net"), svgIcon("net"), 3) +
        "</div></section>";
    }

    function tileHtml(k, label, ic, w) {
      /* Crête : 2 périodes sur 240 unités, translation de 50 % = sans couture. */
      var crest = '<path d="M0 8 Q30 0 60 8 T120 8 T180 8 T240 8 V16 H0 Z"/>';
      var crestLine = '<path class="hm-crest-line" d="M0 8 Q30 0 60 8 T120 8 T180 8 T240 8"/>';
      /* Moitié basse de la tuile : jauge liquide (niveau = pourcentage sur
         toute la hauteur de la zone) avec la mini-courbe posée PAR-DESSUS ;
         moitié haute : libellé, valeur, note (jamais touchés par la crête). */
      return '<div class="hm-panel hm-tile hm-wave-in" data-k="' + k + '" style="--w:' + w + ';--lvl:0">' +
        '<div class="hm-tile-head"><span class="hm-tile-ic">' + ic + '</span><span class="hm-tile-label">' + esc(label) + "</span>" +
        '<span class="hm-live-dot" title="' + esc(s("live_title")) + '"></span></div>' +
        '<div class="hm-tile-val"><span class="hm-num">—</span><span class="hm-unit"></span></div>' +
        '<div class="hm-tile-note">' + esc(s("live_waiting")) + "</div>" +
        '<div class="hm-tile-low">' +
        '<div class="hm-wave" aria-hidden="true"><div class="hm-wave-fill">' +
        '<svg class="hm-crest hm-crest-a" viewBox="0 0 240 16" preserveAspectRatio="none" focusable="false">' + crest + crestLine + "</svg>" +
        '<svg class="hm-crest hm-crest-b" viewBox="0 0 240 16" preserveAspectRatio="none" focusable="false">' + crest + "</svg>" +
        "</div></div>" +
        '<svg class="hm-spark" viewBox="0 0 120 34" preserveAspectRatio="none" aria-hidden="true" focusable="false">' +
        '<path class="hm-spark-area" d=""/><path class="hm-spark-line" d=""/></svg>' +
        "</div></div>";
    }

    /** Calcul transparent de l'indice (0-100). */
    function computeIndex(d) {
      var parts = [];
      /* 1) Optimisations recommandées appliquées : 40 pts. */
      var list = ((d.tweaks && d.tweaks.tweaks) || []).filter(function (x) { return x && x.supported !== false; });
      var recIds = d.profile && Array.isArray(d.profile.recommended_tweaks) ? d.profile.recommended_tweaks : null;
      var rec = recIds && recIds.length ?
        list.filter(function (x) { return recIds.indexOf(x.id) >= 0; }) :
        list.filter(function (x) { return x.risk === "sur" && Array.isArray(x.default_for) && x.default_for.length; });
      var applied = rec.filter(function (x) { return x.applied === true; }).length;
      parts.push({
        key: "tweaks", max: 40, act: "tweaks",
        pts: rec.length ? Math.round(40 * applied / rec.length) : 0,
        val: rec.length ? applied + " / " + rec.length : s("perf_val_none")
      });
      /* 2) Niveau de la machine : 20 pts. */
      var tierPts = { lowend: 8, midrange: 14, highend: 20 };
      parts.push({
        key: "tier", max: 20, act: null,
        pts: Object.prototype.hasOwnProperty.call(tierPts, d.tier) ? tierPts[d.tier] : 10,
        val: tierLabel(d.tier) || s("perf_val_unknown")
      });
      /* 3) Aucun conseil « important » : 20 pts (−10 par conseil important). */
      var imp = d.insights ? d.insights.filter(function (x) { return x && x.severity === "important"; }).length : null;
      parts.push({
        key: "insights", max: 20, act: "insights",
        pts: imp === null ? 10 : Math.max(0, 20 - 10 * imp),
        val: imp === null ? s("perf_val_unknown") : (imp ? s("perf_val_ins_n", { n: imp }) : s("perf_val_ins_ok"))
      });
      /* 4) Benchmark réalisé : 20 pts. */
      var benched = !!(d.bench && d.bench.length);
      parts.push({
        key: "bench", max: 20, act: "bench",
        pts: benched ? 20 : 0,
        val: benched ? s("perf_val_bench_yes") : s("perf_val_bench_no")
      });
      var total = parts.reduce(function (a, p) { return a + p.pts; }, 0);
      return { total: clamp(Math.round(total), 0, 100), parts: parts };
    }

    function bandOf(score) {
      if (score >= 90) { return "top"; }
      if (score >= 70) { return "good"; }
      if (score >= 40) { return "mid"; }
      return "low";
    }

    /** Infobulle de l'indice, recalculée à chaque ouverture (survol ou focus
        de l'anneau / du bouton ⓘ) : à droite du panneau s'il y a la place
        (décalage vertical borné à la fenêtre : jamais rognée en haut ni en
        bas), sinon sous le panneau (ou au-dessus s'il est en bas d'écran). */
    function placeTip(panel) {
      var tip = panel.querySelector(".hm-tip");
      if (!tip || panel.__tipBound) { return; }
      panel.__tipBound = true;
      function place() {
        var r = panel.getBoundingClientRect();
        var h = tip.offsetHeight || 0;
        var w = tip.offsetWidth || 380;
        var vh = window.innerHeight || doc.documentElement.clientHeight || 0;
        var vw = doc.documentElement.clientWidth || window.innerWidth || 0;
        var top, left;
        if (r.right + 12 + w <= vw - 8) {
          left = r.width + 12;
          top = Math.max(8 - r.top, Math.min(0, vh - 8 - h - r.top));
          top = Math.min(top, Math.max(0, r.height - 40));
          tip.style.transformOrigin = "0 " + Math.round(clamp(24 - top, 12, h - 12)) + "px";
        } else {
          left = 18;
          if (r.bottom + 10 + h <= vh - 8) { top = r.height + 10; tip.style.transformOrigin = "30% 0"; }
          else if (r.top - 10 - h >= 8) { top = -(h + 10); tip.style.transformOrigin = "30% 100%"; }
          else {
            /* Ni dessous ni dessus en entier : on la cale dans la fenêtre. */
            top = Math.max(8 - r.top, Math.min(r.height + 10, vh - 8 - h - r.top));
            tip.style.transformOrigin = "30% 0";
          }
        }
        tip.style.left = Math.round(left) + "px";
        tip.style.top = Math.round(top) + "px";
      }
      on(panel, "pointerover", function (e) {
        if (e.target && e.target.closest && e.target.closest(".hm-ring-wrap, .hm-info-btn")) { place(); }
      });
      on(panel, "focusin", place);
      /* Position calculée pour l'ancienne largeur : retour aux valeurs CSS
         (sinon l'infobulle cachée pourrait déborder de la page). */
      on(window, "resize", function () { tip.style.left = ""; tip.style.top = ""; });
    }

    function showIndex(res) {
      var panel = rootEl.querySelector(".hm-index");
      if (!panel) { return; }
      var score = res.total;
      var band = bandOf(score);
      var arc = panel.querySelector(".hm-ring-arc");
      var num = panel.querySelector(".hm-score");
      /* Re-rendu rapproché (langue…) d'un indice déjà affiché : valeur
         posée directement, ni recomptage ni remplissage de l'anneau. */
      var instant = quick && shownScore !== null && !panel.classList.contains("is-ready");
      panel.classList.toggle("is-instant", instant);
      /* Anneau : style calculé avant le remplissage, l'arc part de zéro. */
      try { void window.getComputedStyle(arc).strokeDashoffset; } catch (e) { /* sans effet */ }
      panel.style.setProperty("--score", String(score));
      arc.style.strokeDashoffset = String(100 - score);
      var lit = Math.round(score * 60 / 100);
      Array.prototype.forEach.call(panel.querySelectorAll(".hm-tick"), function (tk, i) {
        tk.classList.toggle("is-on", i < lit);
      });
      if (instant) { num.textContent = String(score); } else { countTo(num, score, 1500); }
      shownScore = score;
      var bandEl = panel.querySelector(".hm-band");
      bandEl.setAttribute("data-band", band);
      bandEl.querySelector(".hm-band-text").textContent = s("perf_band_" + band);
      panel.querySelector(".hm-index-desc").textContent = s("perf_desc_" + band);
      panel.classList.add("is-ready");

      /* Infobulle (et détail en ligne sur largeur moyenne) : 4 composantes. */
      var rows = res.parts.map(function (p) {
        var pct = p.max ? Math.round(p.pts * 100 / p.max) : 0;
        return '<div class="hm-tip-row"><div class="hm-tip-line"><span class="hm-tip-name">' + esc(s("perf_part_" + p.key)) +
          '</span><span class="hm-tip-pts">' + esc(s("perf_pts", { p: p.pts, m: p.max })) + "</span></div>" +
          '<div class="hm-tip-sub">' + esc(p.val) + "</div>" +
          '<div class="hm-tip-bar"><i style="--p:' + pct + '"></i></div></div>';
      }).join("");
      panel.querySelector(".hm-tip").innerHTML = '<div class="hm-tip-title">' + esc(s("perf_how")) + "</div>" + rows +
        '<div class="hm-tip-foot">' + esc(s("perf_tip_foot")) + "</div>";
      panel.querySelector(".hm-breakdown").innerHTML = rows;
      placeTip(panel);

      /* Prochaine étape : composante actionnable qui rapporte le plus. */
      var best = null;
      res.parts.forEach(function (p) {
        if (!p.act || p.pts >= p.max) { return; }
        if (p.key === "tweaks" && p.val === s("perf_val_none")) { return; }
        if (!best || (p.max - p.pts) > (best.max - best.pts)) { best = p; }
      });
      var next = panel.querySelector("#hm-next");
      if (best) {
        var nk = best.key === "tweaks" ? "perf_next_tweaks" : (best.key === "bench" ? "perf_next_bench" : "perf_next_insights");
        var label = s(nk);
        /* Libellé court (« Benchmark ») quand le panneau est étroit (CSS). */
        next.innerHTML = '<span class="hm-next-long">' + esc(label) + '</span><span class="hm-next-short" aria-hidden="true">' +
          esc(s(nk + "_short")) + '</span><span class="hm-gain">+' + (best.max - best.pts) + "</span>" + svgIcon("arrow");
        next.setAttribute("aria-label", label + " (+" + (best.max - best.pts) + ")");
        next.setAttribute("data-act", best.act);
        next.hidden = false;
      } else {
        next.hidden = true;
      }
    }

    /** Compteur 0 → valeur (rAF, s'arrête seul ; direct sans animations). */
    function countTo(el, value, dur) {
      if (!el) { return; }
      if (!fxOn() || doc.hidden) { el.textContent = String(value); return; }
      var t0 = 0;
      var raf = 0;
      function frame(t) {
        raf = 0;
        if (dead) { return; }
        if (!t0) { t0 = t; }
        var p = clamp((t - t0) / dur, 0, 1);
        var e = 1 - Math.pow(1 - p, 3);
        el.textContent = String(Math.round(value * e));
        if (p < 1) { raf = requestAnimationFrame(frame); }
      }
      raf = requestAnimationFrame(frame);
      rafs.push(function () { if (raf) { cancelAnimationFrame(raf); raf = 0; } });
    }

    /* ---- tuiles LIVE (/api/monitor toutes les 2 s, accueil affiché) ---- */

    var liveTimer = 0;
    var liveBusy = false;
    var liveHasData = false;
    /* Navigation vers une autre page annoncée (motion.js) : plus aucun
       relevé ni boucle pendant la transition, avant même le changement de
       hash qui détruit la vue. */
    var leavingPage = false;
    on(window, "overdrive:navigate", function (e) {
      var h = String((e && e.detail && e.detail.hash) || "#/");
      var r = h.replace(/^#/, "").split("?")[0] || "/";
      if (r === "/" || dead) { return; }
      leavingPage = true;
      cancel(liveTimer);
      liveTimer = 0;
      syncLoops();
    });

    function liveSchedule(ms) {
      cancel(liveTimer);
      liveTimer = later(liveTick, ms);
    }

    function setLivePaused(p) {
      rootEl.classList.toggle("hm-live-paused", p);
      if (p) {
        Array.prototype.forEach.call(rootEl.querySelectorAll(".hm-tile .hm-tile-note"), function (n) {
          n.textContent = s("live_paused");
        });
      }
    }

    function liveTick() {
      liveTimer = 0;
      if (!ok()) { return; }
      var gameOn = false;
      try { gameOn = typeof ctx.gameRunning === "function" && !!ctx.gameRunning(); } catch (e) { gameOn = false; }
      if (gameOn || isPaused()) {
        setLivePaused(true);
        liveSchedule(LIVE_MS);
        return;
      }
      if (leavingPage) { return; }
      if (doc.hidden || liveBusy || overlayOpen()) { liveSchedule(LIVE_MS); return; }
      liveBusy = true;
      sharedJSON("/api/monitor", 1000).then(function (m) {
        liveBusy = false;
        if (!ok()) { return; }
        setLivePaused(false);
        applyLive(m);
        liveSchedule(liveHasData ? LIVE_MS : 900);
      }).catch(function () {
        liveBusy = false;
        if (!ok()) { return; }
        if (!liveHasData) {
          Array.prototype.forEach.call(rootEl.querySelectorAll(".hm-tile .hm-tile-note"), function (n) {
            n.textContent = s("live_unavailable");
          });
        }
        liveSchedule(LIVE_MS * 2);
      });
    }

    function pushHist(arr, v) {
      arr.push(v);
      while (arr.length > HIST) { arr.shift(); }
    }

    function applyLive(m) {
      if (!m || typeof m !== "object") { return; }
      var first = !liveHasData;
      liveHasData = true;
      var t = Date.now();
      if (hist.at && t - hist.at > 30000) { hist.cpu = []; hist.ram = []; hist.net = []; }
      hist.at = t;
      var cpu = clamp(Number(m.cpu_percent) || 0, 0, 100);
      var ramObj = m.ram || {};
      var ram = clamp(Number(ramObj.percent) || 0, 0, 100);
      var netIo = m.net_io || {};
      var down = Math.max(0, Number(netIo.down_mbps) || 0);
      var up = Math.max(0, Number(netIo.up_mbps) || 0);
      pushHist(hist.cpu, cpu);
      pushHist(hist.ram, ram);
      pushHist(hist.net, down);
      var peak = Math.max.apply(null, hist.net.concat([down + up]));
      netPeak = Math.max(10, peak * 1.25, netPeak * 0.97);

      var cores = (m.per_core || []).length;
      setTile("cpu", cpu, String(Math.round(cpu)), "%", cores ? s("live_threads", { n: cores }) : "", hist.cpu, 100, first);
      measureTiles();
      var ramNote = "";
      if (ramObj.used_gb !== undefined && ramObj.total_gb !== undefined) {
        /* Tuile étroite : « 12,6 / 31,9 Go » (jamais tronqué). */
        ramNote = netCompact ? dec((Math.round(Number(ramObj.used_gb) * 10) / 10).toFixed(1)) + " / " + gb(ramObj.total_gb) :
          s("live_ram_note", { u: gb(ramObj.used_gb), t: gb(ramObj.total_gb) });
      }
      setTile("ram", ram, String(Math.round(ram)), "%", ramNote, hist.ram, 100, first);
      var gpuT = m.gpu_temp_c !== undefined ? Number(m.gpu_temp_c) : (m.temps && m.temps.gpu_c !== undefined ? Number(m.temps.gpu_c) : NaN);
      if (isFinite(gpuT) && gpuT > 0) {
        relabelNet(true);
        setTile("net", clamp(gpuT, 0, 100), String(Math.round(gpuT)), "°C", s("live_gpu_note"), null, 100, first);
      } else {
        relabelNet(false);
        /* Échelle logarithmique (référence 100 Mb/s ou pic observé). */
        var netPct = Math.log(1 + down) / Math.log(1 + Math.max(100, netPeak)) * 100;
        var downTxt = dec((Math.round(down * 10) / 10).toFixed(1));
        var upTxt = dec((Math.round(up * 10) / 10).toFixed(1));
        /* Tuile étroite (< 260 px) : note compacte « ↓ 4,9 · ↑ 0,0 »,
           la valeur montante n'est jamais tronquée. */
        /* Note compacte sans unité : « Mb/s » est déjà affiché à côté de la valeur. */
        setTile("net", clamp(netPct, 0, 100), downTxt, "Mb/s",
          netCompact ? s("live_net_note_short", { d: downTxt, u: upTxt }) :
            s("live_net_note", { u: upTxt + "\u00a0Mb/s" }), hist.net, netPeak, first);
      }
    }

    var netIsGpu = false;
    var netCompact = null;   /* notes compactes (tuiles étroites) ; null = à mesurer */
    on(window, "resize", function () { netCompact = null; });
    /** Largeur des tuiles lue une fois (puis après chaque redimensionnement),
        pas à chaque relevé : notes compactes sous 260 px. */
    function measureTiles() {
      if (netCompact !== null) { return; }
      var tile = rootEl.querySelector('.hm-tile[data-k="net"]');
      var tw = tile ? tile.clientWidth : 0;
      netCompact = tw ? tw < 260 : null;
    }
    function relabelNet(gpu) {
      if (gpu === netIsGpu) { return; }
      netIsGpu = gpu;
      var tile = rootEl.querySelector('.hm-tile[data-k="net"]');
      if (!tile) { return; }
      tile.querySelector(".hm-tile-label").textContent = gpu ? s("live_gpu") : s("live_net");
      tile.querySelector(".hm-tile-ic").innerHTML = gpu ? svgIcon("thermo") : svgIcon("net");
    }

    function setTile(k, pct, valTxt, unit, note, series, scale, first) {
      var tile = rootEl.querySelector('.hm-tile[data-k="' + k + '"]');
      if (!tile) { return; }
      tile.style.setProperty("--lvl", (clamp(pct, 0, 100) / 100).toFixed(3));
      tile.classList.toggle("is-hot", k !== "net" && pct >= 90);
      var num = tile.querySelector(".hm-num");
      if (first && fxOn() && /^\d+$/.test(valTxt)) { countTo(num, Number(valTxt), 900); } else { num.textContent = valTxt; }
      tile.querySelector(".hm-unit").textContent = unit;
      tile.querySelector(".hm-tile-note").textContent = note;
      tile.classList.add("is-live");
      if (series) { drawSpark(tile, series, scale); }
    }

    function drawSpark(tile, series, scale) {
      var line = tile.querySelector(".hm-spark-line");
      var area = tile.querySelector(".hm-spark-area");
      if (!line || !area || !series.length) { return; }
      var pts = series.slice(-HIST);
      while (pts.length < HIST) { pts.unshift(pts[0]); }
      var W = 120, H = 34, pad = 3;
      /* Échelle ajustée aux valeurs récentes : la courbe reste lisible. */
      var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts);
      var top = Math.max(1, scale || 100);
      lo = Math.max(0, lo - 6);
      hi = Math.min(top, hi + 6);
      if (hi - lo < top * 0.16) { var mid = (hi + lo) / 2; lo = Math.max(0, mid - top * 0.08); hi = lo + top * 0.16; }
      var d = "";
      for (var i = 0; i < pts.length; i++) {
        var x = (i / (pts.length - 1)) * W;
        var y = H - pad - clamp((pts[i] - lo) / (hi - lo), 0, 1) * (H - pad * 2);
        d += (i ? " L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
      }
      line.setAttribute("d", d);
      area.setAttribute("d", d + " L" + W + " " + H + " L0 " + H + " Z");
    }

    /* ================================================================ */
    /* 3. Carrousel de jaquettes                                        */
    /* ================================================================ */

    function gamesShellHtml() {
      var skel = "";
      for (var i = 0; i < 7; i++) { skel += '<div class="hm-cover-item hm-skel-item"><div class="hm-skel hm-skel-cover"></div></div>'; }
      return '<section class="hm-sec hm-games" aria-labelledby="hm-games-title">' +
        '<div class="hm-sec-head"><h2 class="hm-sec-title" id="hm-games-title">' + esc(s("games_title")) + "</h2>" +
        '<span class="hm-sec-count" id="hm-games-count"></span><span class="hm-spacer"></span>' +
        '<a class="hm-link" href="#/games">' + esc(s("games_all")) + "</a>" +
        '<button class="hm-arrow" type="button" data-dir="-1" aria-label="' + esc(s("games_prev")) + '">' + svgIcon("left") + "</button>" +
        '<button class="hm-arrow" type="button" data-dir="1" aria-label="' + esc(s("games_next")) + '">' + svgIcon("right") + "</button>" +
        "</div>" +
        '<div class="hm-rail-wrap"><div class="hm-rail" tabindex="0" role="list" aria-label="' + esc(s("games_rail")) + '">' + skel + "</div></div>" +
        "</section>";
    }

    function coverHtml(g, i) {
      var mono = monogram(g.name || g.id);
      var hue = artHue(g.id);
      var focus = artFocus(g.id);
      /* Sans jaquette : header Steam (460×215, léger) avant le héros 2x ;
         ailleurs le header n'est qu'un alias du héros (même fichier). */
      var kinds = artSource(g.id) === "steam" ? ["cover", "portrait", "header", "hero"] : ["cover", "portrait", "hero", "header"];
      return '<div class="hm-cover-item" role="listitem" style="--i:' + i + '">' +
        '<article class="hm-cover' + (g.installed ? " is-installed" : "") + '" data-game="' + esc(g.id) + '">' +
        '<div class="hm-cover-art" data-art-host style="--hue:' + hue + ";--fbh:" + artFbHue(g.id) + "deg" +
        (focus ? ";--focus:" + esc(focus) : "") + '">' +
        '<div class="hm-cover-fb" aria-hidden="true"><span class="hm-cover-mono' + (mono.length >= 4 ? " is-long" : "") + '">' + esc(mono) + "</span>" +
        '<span class="hm-cover-fbname">' + esc(g.name) + "</span></div>" +
        '<div class="hm-cover-blur" aria-hidden="true"></div>' +
        artImg(g.id, kinds, "hm-cover-img", g.name) +
        '<span class="hm-cover-title" aria-hidden="true">' + esc(g.name) + "</span>" +
        '<span class="hm-cover-shine" aria-hidden="true"></span>' +
        '<div class="hm-cover-over"><button class="hm-cover-btn" type="button" data-act="game" data-game="' + esc(g.id) + '" ' +
        'aria-label="' + esc(s("games_optimize") + " — " + g.name) + '">' + appIcon("zap") +
        "<span>" + esc(s("games_optimize")) + "</span></button></div>" +
        "</div></article>" +
        '<div class="hm-cover-name" title="' + esc(g.name) + '">' + esc(g.name) + "</div>" +
        /* « Installé » sous la jaquette : le logo imprimé reste visible. */
        '<div class="hm-cover-sub"><span class="hm-cover-store">' + esc(storeName(g.store)) + "</span>" +
        (g.installed ? '<span class="hm-badge-inst">' + svgIcon("check") + esc(s("games_installed")) + "</span>" : "") + "</div>" +
        "</div>";
    }

    var railBuilt = false;
    var railSig = "";
    function buildRail(games) {
      var sig = games.map(function (g) { return g.id + (g.installed ? "+" : "-") + g.name; }).join("|");
      if (railBuilt && sig === railSig) { return; }
      railSig = sig;
      stopDrift();
      stopAnim();
      var list = games.slice().sort(function (a, b) {
        if (!!a.installed !== !!b.installed) { return a.installed ? -1 : 1; }
        if (a.id === "cs2" || b.id === "cs2") { return a.id === "cs2" ? -1 : 1; }
        return 0;
      });
      railEl.innerHTML = list.map(coverHtml).join("");
      /* Re-rendu rapproché (langue…) : le carrousel reste où il était. */
      railEl.scrollLeft = quick && !railBuilt ? railLeft : 0;
      railBuilt = true;
      /* Pas de dérive avant 7 s : la 1re jaquette (CS2) reste entière. */
      idleUntil = Math.max(idleUntil, Date.now() + DRIFT_IDLE);
      later(syncLoops, DRIFT_IDLE + 100);
      bindArt(railEl);
      watchNear();
      var n = list.filter(function (g) { return g.installed; }).length;
      var count = rootEl.querySelector("#hm-games-count");
      if (count) { count.textContent = n === 0 ? s("games_count_none") : (n === 1 ? s("games_count_one") : s("games_count_many", { n: n })); }
      railEl.classList.toggle("hm-snap", !fxOn());
      syncArrows();
      syncLoops();
    }

    /* Jaquettes dans la zone visible du carrousel (même en partie) :
       classe is-near (seules celles-ci animent leur balayage de chargement). */
    var nearIo = null;
    function watchNear() {
      if (nearIo) { nearIo.disconnect(); }
      var items = railEl.querySelectorAll(".hm-cover-item");
      if (!window.IntersectionObserver) {
        Array.prototype.forEach.call(items, function (it) { it.classList.add("is-near"); });
        return;
      }
      nearIo = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { en.target.classList.toggle("is-near", en.isIntersecting); });
      }, { root: railEl, rootMargin: "0px" });
      Array.prototype.forEach.call(items, function (it) { nearIo.observe(it); });
      observers.push(nearIo);
    }

    /* ---- défilement : animation douce + accroche sur une jaquette ---- */

    var anim = null;          /* {target, raf, last, snap} */
    var snapTimer = 0;
    var railHover = false, railFocus = false, railVisible = true;
    var idleUntil = 0;        /* dérive suspendue jusqu'à… (interaction récente) */
    var drag = null, suppressClick = false;

    function railMax() { return Math.max(0, railEl.scrollWidth - railEl.clientWidth); }

    function itemOffsets() {
      var padL = parseFloat(window.getComputedStyle(railEl).paddingLeft) || 0;
      var out = [];
      Array.prototype.forEach.call(railEl.children, function (it) { out.push(Math.max(0, it.offsetLeft - padL)); });
      return out;
    }

    function nearestOffset(x, dir) {
      var offs = itemOffsets();
      if (!offs.length) { return x; }
      var best = offs[0], bd = Infinity;
      offs.forEach(function (o) {
        if (dir > 0 && o <= x + 2) { return; }
        if (dir < 0 && o >= x - 2) { return; }
        var dd = Math.abs(o - x);
        if (dd < bd) { bd = dd; best = o; }
      });
      if (bd === Infinity) { best = dir > 0 ? railMax() : 0; }
      return clamp(best, 0, railMax());
    }

    function stopAnim() {
      if (anim && anim.raf) { cancelAnimationFrame(anim.raf); }
      anim = null;
    }

    function smoothTo(target, snapAfter) {
      target = clamp(target, 0, railMax());
      railEl.classList.remove("hm-snap");
      if (!fadeOn()) {
        railEl.scrollLeft = target;
        if (snapAfter) { railEl.classList.add("hm-snap"); }
        syncArrows();
        return;
      }
      if (!anim) {
        anim = { target: target, raf: 0, last: 0, pos: railEl.scrollLeft, snap: snapAfter };
      } else {
        anim.target = target;
        anim.snap = snapAfter;
      }
      if (!anim.raf) { anim.raf = requestAnimationFrame(animFrame); }
    }

    function animFrame(t) {
      if (!anim) { return; }
      anim.raf = 0;
      if (dead) { anim = null; return; }
      var dt = anim.last ? Math.min(48, t - anim.last) : 16;
      anim.last = t;
      if (Math.abs(railEl.scrollLeft - anim.pos) > 3) { anim.pos = railEl.scrollLeft; }
      var k = 1 - Math.exp(-dt / 85);
      anim.pos += (anim.target - anim.pos) * k;
      if (Math.abs(anim.target - anim.pos) < 0.6) {
        railEl.scrollLeft = anim.target;
        var snap = anim.snap;
        anim = null;
        syncArrows();
        if (snap) {
          cancel(snapTimer);
          snapTimer = later(function () {
            var x = nearestOffset(railEl.scrollLeft, 0);
            if (Math.abs(x - railEl.scrollLeft) > 1) { smoothTo(x, false); }
            railEl.classList.add("hm-snap");
          }, 120);
        } else {
          railEl.classList.add("hm-snap");
        }
        return;
      }
      railEl.scrollLeft = anim.pos;
      anim.raf = requestAnimationFrame(animFrame);
    }

    function userTouched() {
      idleUntil = Date.now() + 4000;
      stopDrift();
      later(syncLoops, 4100);
    }

    function syncArrows() {
      var max = railMax();
      Array.prototype.forEach.call(rootEl.querySelectorAll(".hm-arrow"), function (b) {
        var dir = Number(b.getAttribute("data-dir"));
        b.disabled = dir < 0 ? railEl.scrollLeft <= 1 : railEl.scrollLeft >= max - 1;
      });
      var wrap = railEl.parentNode;
      wrap.classList.toggle("at-start", railEl.scrollLeft <= 1);
      wrap.classList.toggle("at-end", railEl.scrollLeft >= max - 1);
    }

    function step(dir) {
      var page2 = Math.max(1, Math.floor(railEl.clientWidth / 200) - 1);
      var offs = itemOffsets();
      var cur = nearestOffset(railEl.scrollLeft, 0);
      var idx = offs.indexOf(cur);
      if (idx < 0) { idx = 0; }
      var nextIdx = clamp(idx + dir * page2, 0, offs.length - 1);
      smoothTo(dir > 0 && nextIdx === offs.length - 1 ? railMax() : offs[nextIdx], false);
    }

    Array.prototype.forEach.call(rootEl.querySelectorAll(".hm-arrow"), function (b) {
      on(b, "click", function () {
        userTouched();
        step(Number(b.getAttribute("data-dir")) || 1);
      });
    });

    on(railEl, "scroll", function () { syncArrows(); }, { passive: true });

    on(railEl, "wheel", function (e) {
      if (e.ctrlKey || !railBuilt) { return; }
      var dx = e.deltaX, dy = e.deltaY;
      var d = Math.abs(dx) > Math.abs(dy) ? dx : dy;
      if (e.deltaMode === 1) { d *= 32; } else if (e.deltaMode === 2) { d *= railEl.clientWidth; }
      var max = railMax();
      var base = anim ? anim.target : railEl.scrollLeft;
      /* Bord atteint : la page défile normalement. */
      if ((d < 0 && base <= 0) || (d > 0 && base >= max - 1)) { return; }
      e.preventDefault();
      userTouched();
      smoothTo(base + d * 1.1, true);
    }, { passive: false });

    on(railEl, "keydown", function (e) {
      if (e.target !== railEl) { return; }
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        userTouched();
        var dir = e.key === "ArrowRight" ? 1 : -1;
        smoothTo(nearestOffset(railEl.scrollLeft, dir), false);
      }
    });

    /* Glisser à la souris (inertie puis accroche). */
    on(railEl, "pointerdown", function (e) {
      if (e.pointerType !== "mouse" || e.button !== 0) { return; }
      stopAnim();
      drag = { x: e.clientX, left: railEl.scrollLeft, moved: false, id: e.pointerId, lx: e.clientX, lt: e.timeStamp, v: 0 };
    });
    on(railEl, "pointermove", function (e) {
      if (drag && e.pointerId === drag.id) {
        var dx = e.clientX - drag.x;
        if (!drag.moved && Math.abs(dx) > 5) {
          drag.moved = true;
          userTouched();
          railEl.classList.remove("hm-snap");
          railEl.classList.add("is-dragging");
          try { railEl.setPointerCapture(e.pointerId); } catch (err) { /* capture impossible */ }
          releaseTilt();
        }
        if (drag.moved) {
          railEl.scrollLeft = drag.left - dx;
          var dt = e.timeStamp - drag.lt;
          if (dt > 0) { drag.v = (e.clientX - drag.lx) / dt; }
          drag.lx = e.clientX;
          drag.lt = e.timeStamp;
          return;
        }
      }
      onTiltMove(e);
    });
    function endDrag(e) {
      if (!drag || (e && e.pointerId !== drag.id)) { return; }
      var d = drag;
      drag = null;
      railEl.classList.remove("is-dragging");
      if (d.moved) {
        suppressClick = true;
        later(function () { suppressClick = false; }, 60);
        smoothTo(railEl.scrollLeft - d.v * 260, true);
      }
    }
    on(railEl, "pointerup", endDrag);
    on(railEl, "pointercancel", endDrag);
    on(railEl, "click", function (e) {
      if (suppressClick) { e.preventDefault(); e.stopPropagation(); suppressClick = false; return; }
      if (e.target.closest("[data-act]")) { return; }
      var card = e.target.closest(".hm-cover");
      if (card && railEl.contains(card)) {
        try { ctx.openGame(card.getAttribute("data-game")); } catch (err) { /* action indisponible */ }
      }
    }, true);
    on(railEl, "dragstart", function (e) { e.preventDefault(); });

    on(railEl, "pointerenter", function () { railHover = true; stopDrift(); });
    on(railEl, "pointerleave", function () {
      railHover = false;
      releaseTilt();
      idleUntil = Math.max(idleUntil, Date.now() + 1500);
      later(syncLoops, 1600);
    });
    on(railEl, "focusin", function () { railFocus = true; stopDrift(); });
    on(railEl, "focusout", function (e) {
      if (e.relatedTarget && railEl.contains(e.relatedTarget)) { return; }
      railFocus = false;
      later(syncLoops, 1600);
    });
    /* Jaquette focalisée au clavier : elle reste visible. */
    on(railEl, "focusin", function (e) {
      var item = e.target.closest(".hm-cover-item");
      if (!item) { return; }
      var l = item.offsetLeft - railEl.scrollLeft, r = l + item.offsetWidth;
      if (l < 0 || r > railEl.clientWidth) { smoothTo(nearestOffset(item.offsetLeft - 24, 0), false); }
    });

    /* ---- inclinaison 3D + reflet au survol ---- */

    var tiltEl = null, tiltRaf = 0, tiltX = 0, tiltY = 0;
    function onTiltMove(e) {
      if (!fxOn() || drag || e.pointerType === "touch") { return; }
      var card = e.target.closest ? e.target.closest(".hm-cover") : null;
      if (card !== tiltEl) { releaseTilt(); tiltEl = card; }
      if (!card) { return; }
      var r = card.getBoundingClientRect();
      if (!r.width) { return; }
      tiltX = clamp((e.clientX - r.left) / r.width, 0, 1);
      tiltY = clamp((e.clientY - r.top) / r.height, 0, 1);
      if (!tiltRaf) {
        tiltRaf = requestAnimationFrame(function () {
          tiltRaf = 0;
          if (!tiltEl || dead) { return; }
          /* Transform 3D (calque composité) seulement pendant l'inclinaison. */
          tiltEl.classList.add("is-tilt");
          /* ±12° / ±9° : inclinaison réellement perceptible sur 172 px. */
          tiltEl.style.setProperty("--ry", ((tiltX - 0.5) * 24).toFixed(2) + "deg");
          tiltEl.style.setProperty("--rx", ((0.5 - tiltY) * 18).toFixed(2) + "deg");
          tiltEl.style.setProperty("--gx", (tiltX * 100).toFixed(1) + "%");
          tiltEl.style.setProperty("--gy", (tiltY * 100).toFixed(1) + "%");
        });
      }
    }
    function releaseTilt() {
      if (tiltRaf) { cancelAnimationFrame(tiltRaf); tiltRaf = 0; }
      if (tiltEl) {
        tiltEl.style.removeProperty("--rx");
        tiltEl.style.removeProperty("--ry");
        tiltEl.classList.remove("is-tilt");
      }
      tiltEl = null;
    }
    rafs.push(function () { if (tiltRaf) { cancelAnimationFrame(tiltRaf); tiltRaf = 0; } });

    /* ---- dérive automatique (souris ailleurs, effets max, visible) ---- */

    /* Dérive : seulement après 7 s sans interaction, si le carrousel déborde
       d'au moins deux jaquettes ; aller lent, retour plus rapide, pause de
       7 s au début de chaque cycle (le jeu principal reste bien visible). */
    var driftRaf = 0, driftLast = 0, driftDir = 1, driftPos = 0, driftHold = 0;
    var DRIFT_IDLE = 7000;

    function driftWanted() {
      return railBuilt && fxOn() && !doc.hidden && !leavingPage && !overlayOpen() && railVisible && !railHover && !railFocus && !drag && !anim &&
        Date.now() >= idleUntil && railMax() > 380;
    }
    function startDrift() {
      if (driftRaf || !driftWanted()) { return; }
      driftLast = 0;
      driftPos = railEl.scrollLeft;
      railEl.classList.remove("hm-snap");
      driftRaf = requestAnimationFrame(driftFrame);
    }
    function stopDrift() {
      if (driftRaf) { cancelAnimationFrame(driftRaf); driftRaf = 0; }
    }
    function driftFrame(t) {
      driftRaf = 0;
      if (dead || !driftWanted()) { return; }
      /* ~30 i/s suffisent à 16 px/s (moitié moins de défilements et de
         scroll events qu'à 60 i/s). */
      if (driftLast && t - driftLast < 30) { driftRaf = requestAnimationFrame(driftFrame); return; }
      var dt = driftLast ? Math.min(64, t - driftLast) : 16;
      driftLast = t;
      var max = railMax();
      if (Math.abs(railEl.scrollLeft - driftPos) > 2) { driftPos = railEl.scrollLeft; }
      if (driftHold > 0) {
        driftHold -= dt;
      } else {
        driftPos += driftDir * dt * (driftDir > 0 ? 0.016 : 0.04);   /* 16 px/s, retour 40 px/s */
        if (driftPos >= max) { driftPos = max; driftDir = -1; driftHold = 2200; }
        else if (driftPos <= 0) { driftPos = 0; driftDir = 1; driftHold = DRIFT_IDLE; }
        railEl.scrollLeft = driftPos;
      }
      driftRaf = requestAnimationFrame(driftFrame);
    }
    rafs.push(stopDrift);

    /* ================================================================ */
    /* 4. Actions rapides                                               */
    /* ================================================================ */

    function actionsHtml() {
      var items = [
        { act: "boost", ic: appIcon("zap"), anim: "zap", t: s("act_boost"), sub: s("act_boost_sub") },
        { act: "clean", ic: appIcon("trash"), anim: "trash", t: s("act_clean"), sub: s("act_clean_sub") },
        { act: "bench", ic: appIcon("activity"), anim: "pulse", t: s("act_bench"), sub: s("act_bench_sub") },
        { act: "widget", ic: appIcon("widget"), anim: "pop", t: s("act_widget"), sub: s("act_widget_sub") }
      ];
      return '<section class="hm-sec hm-actions-sec" aria-labelledby="hm-act-title">' +
        '<div class="hm-sec-head"><h2 class="hm-sec-title" id="hm-act-title">' + esc(s("actions_title")) + "</h2></div>" +
        '<div class="hm-actions">' + items.map(function (it, i) {
          return '<button class="hm-action hm-wave-in" type="button" data-act="' + it.act + '" data-anim="' + it.anim + '" style="--w:' + i + '">' +
            '<span class="hm-action-ic">' + it.ic + "</span>" +
            '<span class="hm-action-txt"><span class="hm-action-title">' + esc(it.t) + "</span>" +
            '<span class="hm-action-sub">' + esc(it.sub) + "</span></span>" +
            '<span class="hm-action-go" aria-hidden="true">' + svgIcon("arrow") + "</span></button>";
        }).join("") + "</div></section>";
    }
    /* Tracé de l'icône « activité » : longueur normalisée pour l'animer. */
    Array.prototype.forEach.call(rootEl.querySelectorAll('.hm-action[data-anim="pulse"] svg path'), function (p) {
      p.setAttribute("pathLength", "100");
    });

    /* ================================================================ */
    /* 5. Conseils                                                      */
    /* ================================================================ */

    function showInsights(items) {
      var box = rootEl.querySelector("#hm-insights");
      if (!box) { return; }
      if (items === null) {
        box.innerHTML = '<div class="hm-panel hm-insight hm-insight-empty"><p>' + esc(s("insights_unavailable")) + "</p></div>";
        return;
      }
      if (!items.length) {
        box.innerHTML = '<div class="hm-panel hm-insight hm-insight-ok hm-cascade" style="--i:0">' +
          '<span class="hm-ok-ic">' + svgIcon("check") + "</span>" +
          '<div class="hm-insight-body"><div class="hm-insight-title">' + esc(s("insights_none_title")) + "</div>" +
          '<div class="hm-insight-detail">' + esc(s("insights_none")) + "</div></div></div>";
        return;
      }
      box.innerHTML = items.map(function (it, i) {
        var imp = it.severity === "important";
        return '<div class="hm-panel hm-insight hm-cascade" data-sev="' + (imp ? "important" : "conseil") + '" style="--i:' + i + '">' +
          '<span class="hm-sev-bar" aria-hidden="true"></span>' +
          '<span class="hm-sev-ic">' + appIcon(imp ? "alert" : "sparkles") + "</span>" +
          '<div class="hm-insight-body">' +
          '<div class="hm-insight-top"><span class="hm-sev-badge">' + esc(T(imp ? "insights_badge_important" : "insights_badge_conseil")) + "</span>" +
          '<span class="hm-insight-title">' + esc(trf(it, "title")) + "</span></div>" +
          '<div class="hm-insight-detail">' + esc(trf(it, "detail")) + "</div></div>" +
          (it.action_url ? '<a class="hm-ghost-btn" href="' + esc(it.action_url) + '" target="_blank" rel="noopener">' +
            appIcon("external") + "<span>" + esc(s("insights_open")) + "</span></a>" : "") +
          "</div>";
      }).join("");
    }

    /* ================================================================ */
    /* 6. Ta config                                                     */
    /* ================================================================ */

    function showConfig(hw) {
      var box = rootEl.querySelector("#hm-config");
      if (!box) { return; }
      if (!hw) {
        box.innerHTML = '<div class="hm-config-wait">' + esc(s("config_unavailable")) + "</div>";
        return;
      }
      var cpu = hw.cpu || {}, ram = hw.ram || {}, os = hw.os || {};
      var g = mainGpu(hw);
      var disks = (hw.disks || []).filter(function (d) { return Number(d.total_gb) > 1; });
      var sys = disks.filter(function (d) { return /^c:/i.test(String(d.mountpoint || "")) || d.mountpoint === "/"; })[0] || disks[0];
      function chip(ic, main, sub, k) {
        return '<div class="hm-spec" data-k="' + k + '">' + '<span class="hm-spec-ic">' + ic + "</span>" +
          '<span class="hm-spec-txt"><span class="hm-spec-main" title="' + esc(main) + '">' + esc(main) + "</span>" +
          (sub ? '<span class="hm-spec-sub">' + esc(sub) + "</span>" : "") + "</span></div>";
      }
      var html = "";
      html += chip(appIcon("cpu"), cleanName(cpu.name) || "—",
        cpu.cores_physical ? s("config_cores", { p: cpu.cores_physical, l: cpu.cores_logical || "?" }) : "", "cpu");
      html += chip(svgIcon("gpu"), g ? cleanName(g.name) : s("config_no_gpu"),
        g && g.vram_mb ? (function () { try { return ctx.fmtMb(g.vram_mb); } catch (e) { return ""; } })() : "", "gpu");
      html += chip(appIcon("memory"), ram.total_gb !== undefined ? s("config_ram", { g: gb(ram.total_gb) }) : "—", "", "ram");
      html += chip(svgIcon("monitor"), [os.name, os.version].filter(Boolean).join(" ") || "—", os.build ? "build " + os.build : "", "os");
      if (sys) {
        html += chip(svgIcon("disk"), String(sys.mountpoint || sys.device || ""), s("config_free", { f: gb(sys.free_gb) }) + " / " + gb(sys.total_gb), "disk");
      }
      box.innerHTML = '<div class="hm-specs">' + html + "</div>";
    }

    /* ================================================================ */
    /* Particules (canvas, ≤ 60 points, très discret)                   */
    /* ================================================================ */

    var pCanvas = rootEl.querySelector(".hm-particles");
    var pCtx = null;
    try { pCtx = pCanvas.getContext("2d"); } catch (e2) { pCtx = null; }
    var pts = [], pRaf = 0, pLast = 0, pW = 0, pH = 0, pRgb = "139,92,246", pVisible = true;

    function readParticleColor() {
      var probe = rootEl.querySelector(".hm-pcolor");
      if (!probe) { return; }
      var c = window.getComputedStyle(probe).color || "";
      var m = c.match(/rgba?\(([^)]+)\)/);
      if (m) {
        var p = m[1].split(",").slice(0, 3).map(function (x) { return Math.round(parseFloat(x)) || 0; });
        pRgb = p.join(",");
      }
    }

    function sizeCanvas() {
      if (!pCtx) { return false; }
      var r = pCanvas.getBoundingClientRect();
      var w = Math.round(r.width), h = Math.round(r.height);
      if (!w || !h) { return false; }
      if (w === pW && h === pH) { return true; }
      pW = w; pH = h;
      var dpr = Math.min(2, window.devicePixelRatio || 1);
      pCanvas.width = Math.round(w * dpr);
      pCanvas.height = Math.round(h * dpr);
      pCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = clamp(Math.round(w * h / 22000), 18, 60);
      pts = [];
      for (var i = 0; i < n; i++) {
        pts.push({
          x: Math.random() * w, y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.012, vy: -0.004 - Math.random() * 0.01,
          r: 0.6 + Math.random() * 1.4, a: 0.18 + Math.random() * 0.32,
          tw: 0.0006 + Math.random() * 0.0012, ph: Math.random() * 6.28
        });
      }
      return true;
    }

    function pWanted() { return !!pCtx && fxOn() && !doc.hidden && pVisible && !leavingPage && !overlayOpen(); }

    function startParticles() {
      if (pRaf || !pWanted()) { return; }
      if (!sizeCanvas()) { return; }
      pLast = 0;
      pRaf = requestAnimationFrame(pFrame);
    }
    function stopParticles(clear) {
      if (pRaf) { cancelAnimationFrame(pRaf); pRaf = 0; }
      if (clear && pCtx && pW) { pCtx.clearRect(0, 0, pW, pH); }
    }
    function pFrame(t) {
      pRaf = 0;
      if (dead || !pWanted()) { return; }
      var dt = pLast ? t - pLast : 33;
      if (dt < 30) { pRaf = requestAnimationFrame(pFrame); return; }   /* ~30 i/s suffisent */
      pLast = t;
      dt = Math.min(dt, 80);
      pCtx.clearRect(0, 0, pW, pH);
      for (var i = 0; i < pts.length; i++) {
        var p = pts[i];
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        if (p.y < -4) { p.y = pH + 4; p.x = Math.random() * pW; }
        if (p.x < -4) { p.x = pW + 4; } else if (p.x > pW + 4) { p.x = -4; }
        var al = p.a * (0.55 + 0.45 * Math.sin(t * p.tw + p.ph));
        pCtx.beginPath();
        pCtx.arc(p.x, p.y, p.r, 0, 6.2832);
        pCtx.fillStyle = "rgba(" + pRgb + "," + al.toFixed(3) + ")";
        pCtx.fill();
      }
      pRaf = requestAnimationFrame(pFrame);
    }
    rafs.push(function () { stopParticles(false); });

    /* ================================================================ */
    /* Boucles : démarrage / arrêt selon le contexte                    */
    /* ================================================================ */

    function syncLoops() {
      if (dead) { return; }
      if (pWanted()) { startParticles(); } else { stopParticles(!fxOn()); }
      if (driftWanted()) { startDrift(); } else { stopDrift(); }
      if (!fxOn()) { resetParallax(); releaseTilt(); }
      rootEl.classList.toggle("hm-fx", fxOn());
      /* Sous le QCM : Ken Burns, vagues et reflets figés (invisibles). */
      rootEl.classList.toggle("hm-covered", overlayOpen());
      if (!railHover && !drag && !anim && !driftRaf && railBuilt) { railEl.classList.add("hm-snap"); }
    }

    on(doc, "visibilitychange", function () {
      if (!ok()) { return; }
      syncLoops();
      if (!doc.hidden && !liveTimer) { liveSchedule(200); }
    });
    on(window, "resize", function () {
      if (dead) { return; }
      pW = 0;   /* recalcul au prochain démarrage */
      stopParticles(false);
      syncLoops();
      syncArrows();
    });

    var mo = null;
    if (window.MutationObserver) {
      mo = new MutationObserver(function (recs) {
        if (!ok()) { return; }
        var themeChanged = recs.some(function (r) { return r.attributeName === "data-theme"; });
        if (themeChanged) { readParticleColor(); }
        syncLoops();
        if (!isPaused() && rootEl.classList.contains("hm-live-paused")) { liveSchedule(100); }
      });
      mo.observe(root, { attributes: true, attributeFilter: ["data-motion", "data-motion-paused", "data-theme"] });
      observers.push(mo);
      /* QCM ou modale ouverts / fermés : boucles suspendues dessous, entrée
         rejouée à la fermeture si elle avait été retenue. */
      var onCover = function () {
        if (!ok()) { return; }
        syncLoops();
        if (!overlayOpen()) {
          if (pendingEntrance) { pendingEntrance = false; playEntrance(); }
          liveSchedule(200);
        }
      };
      var mo2 = new MutationObserver(onCover);
      ["overlay-root", "modal-root"].forEach(function (id) {
        var box = doc.getElementById(id);
        if (box) { mo2.observe(box, { attributes: true, attributeFilter: ["hidden"], childList: true }); }
      });
      observers.push(mo2);
      /* Palette de commandes (palette.js) : même traitement. */
      on(window, "overdrive:palette", onCover);
    }

    if (window.IntersectionObserver) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.target === railEl) { railVisible = en.isIntersecting; }
          else if (en.target === pCanvas) { pVisible = en.isIntersecting; }
          else if (en.target === heroEl) { heroEl.classList.toggle("is-offscreen", !en.isIntersecting); }
        });
        syncLoops();
      }, { threshold: 0 });
      io.observe(railEl);
      io.observe(pCanvas);
      io.observe(heroEl);
      observers.push(io);
    }

    /* ================================================================ */
    /* Entrée (après l'intro si elle joue encore)                       */
    /* ================================================================ */

    var entranceDone = null;
    var entranceP = new Promise(function (resolve) { entranceDone = resolve; });
    var pendingEntrance = false;

    function playEntrance() {
      if (dead) { return; }
      /* QCM du premier lancement monté sous l'intro : l'entrée attend sa
         fermeture (sinon elle se jouerait invisible, sous le questionnaire). */
      if (overlayOpen()) { pendingEntrance = true; return; }
      entranceDone();
      rootEl.classList.remove("hm-await-intro");
      /* Accueil enfin visible (après l'intro ou le QCM) : la dérive du
         carrousel attend de nouveau 7 s, la 1re jaquette reste entière. */
      idleUntil = Math.max(idleUntil, Date.now() + (DRIFT_IDLE || 7000));
      later(syncLoops, (DRIFT_IDLE || 7000) + 100);
      if (!entrance) { return; }
      void rootEl.offsetWidth;
      rootEl.classList.add("hm-entering");
      later(function () { rootEl.classList.remove("hm-entering"); }, 2600);
    }
    if (awaitIntro) {
      rootEl.classList.remove("hm-entering");
      var released = false;
      var release = function () {
        if (released || dead) { return; }
        released = true;
        /* Court délai : le QCM éventuel (ouvert sur le même événement) est
           monté avant de décider. */
        later(playEntrance, 60);
      };
      on(window, "overdrive:intro-exit", release);
      on(window, "overdrive:intro-done", release);
      later(release, 5000);   /* filet : l'intro dure ~2,5 s */
    } else if (coveredAtStart) {
      pendingEntrance = true;
    } else {
      entranceDone();
      if (entrance) { later(function () { rootEl.classList.remove("hm-entering"); }, 2600); }
    }

    /* ================================================================ */
    /* Chargements                                                      */
    /* ================================================================ */

    readParticleColor();

    function cachedGames() {
      try { return typeof ctx.cachedGames === "function" ? ctx.cachedGames() : null; } catch (e) { return null; }
    }
    function cachedHw() {
      try { return typeof ctx.cachedHardware === "function" ? ctx.cachedHardware() : null; } catch (e) { return null; }
    }
    function statusTier() {
      try {
        var st = ctx.status();
        return st && (st.tier || st.hardware_tier) || null;
      } catch (e) { return null; }
    }

    heroTier = statusTier();
    var hw0 = cachedHw();
    if (hw0) {
      heroTier = heroTier || hw0.tier || null;
      var g0 = mainGpu(hw0);
      heroGpu = g0 ? cleanName(g0.name) : null;
    }
    /* Puce « Ta machine » (statique) : niveau / GPU déjà connus. */
    updateMachineChips();

    if (hw0) { showConfig(hw0); }

    /* Les URLs d'images portent la révision de /api/art (cache navigateur) :
       on l'attend un court instant (400 ms max) avant de construire. */
    var artReady = Promise.race([loadArtInfo(), new Promise(function (resolve) { later(resolve, 400); })]);
    var gamesP = Promise.resolve().then(function () { return ctx.games(); });
    artReady.then(function () {
      if (!ok() || slides.length) { return; }
      var g0list = cachedGames();
      buildSlides(g0list && g0list.length ? g0list : FALLBACK_GAMES);
      if (g0list && g0list.length) { buildRail(g0list); }
    });
    Promise.all([artReady, gamesP.catch(function () { return null; })]).then(function (r) {
      if (!ok()) { return; }
      var games = r[1];
      if (!games || !games.length) {
        if (!railBuilt) { railEl.innerHTML = '<p class="hm-empty">' + esc(s("games_unavailable")) + "</p>"; }
        return;
      }
      buildSlides(games);
      buildRail(games);
    });

    var hwP = Promise.resolve().then(function () { return ctx.hardware(false); });
    hwP.then(function (hw) {
      if (!ok()) { return; }
      heroTier = statusTier() || (hw && hw.tier) || heroTier;
      var g = mainGpu(hw);
      heroGpu = g ? cleanName(g.name) : null;
      updateMachineChips();
      showConfig(hw);
    }).catch(function () {
      if (!ok()) { return; }
      showConfig(null);
    });

    var insP = sharedJSON("/api/insights", 2500).then(function (d) { return (d && d.insights) || []; }).catch(function () { return null; });
    insP.then(function (items) { if (ok()) { showInsights(items); } });

    var tweaksP = Promise.resolve().then(function () { return ctx.tweaks(); }).catch(function () { return null; });
    var benchP = sharedJSON("/api/bench/history", 2500).then(function (d) { return (d && d.history) || []; }).catch(function () { return null; });
    var idxData = null;   /* données de l'indice : {tweaks, insights, bench, tier} */
    function indexResult() {
      var prof = null;
      try { prof = ctx.profile(); } catch (e) { prof = null; }
      return computeIndex({
        tweaks: idxData.tweaks, insights: idxData.insights, bench: idxData.bench, profile: prof,
        tier: statusTier() || idxData.tier || null
      });
    }
    Promise.all([tweaksP, insP, benchP, hwP.catch(function () { return null; })]).then(function (r) {
      if (!ok()) { return; }
      idxData = { tweaks: r[0], insights: r[1], bench: r[2], tier: (r[3] && r[3].tier) || null };
      /* L'anneau se dessine une fois l'accueil visible (après l'intro) ET
         le panneau à l'écran (il est sous les jaquettes) : l'animation
         n'est pas jouée pour rien hors de la vue. */
      entranceP.then(function () {
        if (!ok()) { return; }
        var t0 = Date.now();
        onceVisible(rootEl.querySelector(".hm-index"), function () {
          later(function () { showIndex(indexResult()); }, entrance && Date.now() - t0 < 300 ? 420 : 80);
        });
      });
    });

    /* Benchmark terminé (modale ouverte depuis l'accueil, une tuile ou la
       palette) : l'indice est recalculé sur place, sans re-rendre la page ;
       le bouton « Lancer un benchmark +20 » disparaît aussitôt. */
    on(window, "overdrive:bench-done", function () {
      delete sharedReq["/api/bench/history"];
      sharedJSON("/api/bench/history", 2500).then(function (d) {
        if (!ok() || !idxData) { return; }
        idxData.bench = (d && d.history) || [];
        var panel = rootEl.querySelector(".hm-index");
        if (panel && panel.classList.contains("is-ready")) { showIndex(indexResult()); }
      }).catch(function () { /* indice inchangé */ });
    });

    /** Appelle fn une fois que el est (au moins en partie) à l'écran. */
    function onceVisible(el, fn) {
      if (!el || !window.IntersectionObserver || !fadeOn()) { fn(); return; }
      var done = false;
      var io2 = new IntersectionObserver(function (entries) {
        if (done || !entries.some(function (en) { return en.isIntersecting; })) { return; }
        done = true;
        io2.disconnect();
        if (!dead) { fn(); }
      }, { threshold: 0.2 });
      io2.observe(el);
      observers.push(io2);
    }

    try { ctx.loadPrograms(); } catch (e3) { /* rendu existant indisponible */ }

    /* Programmes : une rangée au repos, « Tout voir » déplie le reste. */
    var progMore = rootEl.querySelector("#hm-prog-more");
    on(progMore, "click", function () {
      var sec = rootEl.querySelector(".hm-programs-sec");
      var open = !sec.classList.contains("is-open");
      sec.classList.toggle("is-open", open);
      progMore.setAttribute("aria-expanded", open ? "true" : "false");
      progMore.textContent = s(open ? "programs_less" : "programs_more");
    });

    /* Visuels arrivés plus tard (réseau lent au démarrage, préchargement
       serveur en cours) : /api/art relu à 8, 20 puis 45 s ; les images en
       repli retentent un type mieux placé dont l'URL a changé. */
    var RETRY_AT = [8000, 20000, 45000];
    function scheduleArtRetry(n) {
      if (n >= RETRY_AT.length) { return; }
      later(function () {
        if (!ok()) { return; }
        var imgs = Array.prototype.filter.call(rootEl.querySelectorAll("img[data-art][data-bound]"), function (img) {
          return img.__artPending && !img.hasAttribute("data-defer");
        });
        if (!imgs.length) { scheduleArtRetry(n + 1); return; }
        loadArtInfo(true).then(function () {
          if (!ok()) { return; }
          imgs.forEach(function (img) { if (img.__artRetry) { img.__artRetry(); } });
          scheduleArtRetry(n + 1);
        });
      }, RETRY_AT[n] - (n ? RETRY_AT[n - 1] : 0));
    }
    scheduleArtRetry(0);

    var refreshBtn = rootEl.querySelector("#hm-hw-refresh");
    on(refreshBtn, "click", function () {
      refreshBtn.disabled = true;
      refreshBtn.classList.add("is-busy");
      Promise.resolve().then(function () { return ctx.hardware(true); }).then(function (hw) {
        if (!ok()) { return; }
        var g = mainGpu(hw);
        heroGpu = g ? cleanName(g.name) : null;
        heroTier = statusTier() || (hw && hw.tier) || heroTier;
        updateMachineChips();
        showConfig(hw);
      }).catch(function () { /* bandeau déjà affiché par l'app */ }).then(function () {
        if (dead) { return; }
        refreshBtn.disabled = false;
        refreshBtn.classList.remove("is-busy");
      });
    });

    liveTick();
    syncLoops();

    /* ================================================================ */
    /* Destruction                                                      */
    /* ================================================================ */

    function destroy() {
      if (dead) { return; }
      dead = true;
      if (railBuilt && railEl) { railLeft = railEl.scrollLeft; }
      timers.forEach(function (id) { clearTimeout(id); });
      timers = [];
      rafs.forEach(function (fn) { try { fn(); } catch (e) { /* déjà arrêté */ } });
      rafs = [];
      stopAnim();
      unlisten.forEach(function (fn) { try { fn(); } catch (e) { /* déjà retiré */ } });
      unlisten = [];
      observers.forEach(function (o) { try { o.disconnect(); } catch (e) { /* déjà déconnecté */ } });
      observers = [];
    }

    return api;
  }

  window.OverdriveHome = { render: render, stop: stop, isActive: isActive };
})();
