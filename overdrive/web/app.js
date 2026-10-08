/* Overdrive — application frontend.
   Vanilla JS, aucune dépendance, aucun CDN. Consomme l'API REST locale. */

(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Langue (lue avant le premier rendu pour éviter tout flash)          */
  /* ------------------------------------------------------------------ */

  var LANG = "fr";
  try {
    var _storedLang = localStorage.getItem("overdrive-lang");
    if (_storedLang === "en" || _storedLang === "fr") { LANG = _storedLang; }
  } catch (e) { /* stockage indisponible : français par défaut */ }

  /* Dictionnaire de TOUTES les chaînes d'interface. */
  var I18N = {
    fr: {
      /* Navigation et chrome */
      nav_home: "Accueil",
      nav_tweaks: "Optimisations",
      nav_games: "Jeux",
      nav_clean: "Nettoyage",
      nav_monitor: "Moniteur",
      nav_startup: "Démarrage",
      nav_assistant: "Assistant",
      nav_settings: "Réglages",
      theme_to_dark: "Thème sombre",
      theme_to_light: "Thème clair",
      loading_ui: "Chargement de l'interface…",

      /* Commun */
      close: "Fermer",
      cancel: "Annuler",
      confirm: "Confirmer",
      copy: "Copier",
      copied: "Copié",
      copy_failed: "Échec de la copie",
      refresh: "Actualiser",
      retry: "Réessayer",
      loading: "Chargement…",
      err_conn: "Connexion au serveur impossible. Vérifiez qu'Overdrive est en cours d'exécution.",
      err_server: "Erreur serveur",
      unit_gb: "Go",
      unit_mb: "Mo",
      unit_mbps: "Mo/s",

      /* Accueil */
      home_title: "Accueil",
      home_sub: "Vue d'ensemble de la machine et de l'état d'optimisation.",
      stat_profile: "Profil",
      stat_tweaks: "Optimisations appliquées",
      stat_games: "Jeux détectés",
      stat_profile_note: "Profil issu du questionnaire",
      stat_none: "Aucun",
      stat_quiz_link: "Répondre au questionnaire",
      stat_tweaks_note: "sur l'ensemble du catalogue",
      stat_games_some: "présents sur cette machine",
      stat_games_none: "aucun jeu détecté",
      hw_group: "Matériel",
      hw_detecting: "Détection du matériel…",
      hw_unavailable: "Matériel non disponible pour le moment.",
      hw_missing: "Matériel non disponible.",
      analyzing: "Analyse…",
      hw_system: "Système",
      hw_cpu: "Processeur",
      hw_ram: "Mémoire",
      hw_gpu: "Carte graphique",
      hw_disk: "Stockage",
      hw_net: "Réseau",
      hw_cores: "{p} cœurs / {l} threads",
      hw_up_to: "jusqu'à {m} MHz",
      hw_load: "charge actuelle {n} %",
      hw_total: "{g} au total",
      hw_avail: "{g} disponibles",
      hw_used: "utilisée à {n} %",
      hw_driver: "pilote {d}",
      hw_free: "{f} libres / {t}",
      hw_none: "Non détecté",
      quick_actions: "Actions rapides",
      quick_clean: "Analyser le nettoyage",
      programs_group: "Programmes recommandés",
      programs_loading: "Chargement de la liste…",
      programs_unavailable: "Liste indisponible pour le moment.",
      programs_none: "Aucun programme recommandé.",
      prog_install: "Installer",
      prog_site: "Site officiel",
      prog_installing: "Installation…",
      prog_install_failed: "Installation impossible.",
      winget_missing: "winget n'est pas disponible sur ce système : l'installation directe est désactivée, les liens restent accessibles.",
      prog_cat_monitoring: "Monitoring",
      prog_cat_pilotes: "Pilotes",
      prog_cat_capture: "Capture",
      prog_cat_utilitaire: "Utilitaire",
      prog_cat_communication: "Communication",
      store_multi: "Multi-plateformes",

      /* Boost */
      boost_btn: "Boost",
      boost_title: "Boost en un clic",
      boost_intro: "Overdrive enchaîne trois étapes sûres pour préparer la machine à jouer :",
      boost_step1: "Point de restauration Windows (optionnel, recommandé)",
      boost_step2: "Application des optimisations recommandées de votre profil",
      boost_step3: "Nettoyage des caches sûrs (fichiers temporaires, caches de shaders)",
      boost_restore_check: "Créer un point de restauration avant le boost",
      boost_run: "Lancer le boost",
      boost_running: "Boost en cours…",
      boost_done: "Boost terminé.",
      boost_done_issues: "Boost terminé avec des erreurs.",
      boost_failed: "Le boost n'a pas pu être lancé.",
      boost_lbl_restore: "Point de restauration",
      boost_lbl_tweaks: "Tweaks du profil",
      boost_lbl_clean: "Nettoyage des caches sûrs",

      /* Optimisations */
      tweaks_title: "Optimisations",
      tweaks_sub: "Sélectionnez les réglages à appliquer. Chaque optimisation est réversible.",
      tweaks_loading: "Chargement du catalogue…",
      tweaks_unavail_title: "Catalogue indisponible",
      tweaks_unavail_body: "Le serveur n'a pas répondu. Réessayez dans un instant.",
      notice_not_windows: "Système non Windows détecté : les optimisations sont affichées à titre informatif (mode développement), leur application est désactivée.",
      notice_not_admin: "Overdrive n'est pas lancé en administrateur : certains réglages (registre machine, services) pourraient échouer. Relancez l'application en tant qu'administrateur pour un résultat complet.",
      sel_profile: "Sélection profil",
      sel_profile_hint: "Répondez d'abord au questionnaire",
      sel_safe: "Tout sûr",
      sel_none: "Tout désélectionner",
      restore_point: "Point de restauration",
      revert_applied: "Annuler les tweaks appliqués",
      apply_n: "Appliquer ({n})",
      selected_one: "{n} sélectionné",
      selected_many: "{n} sélectionnés",
      chip_all: "Toutes",
      impact_high: "Impact élevé",
      impact_medium: "Impact moyen",
      impact_low: "Impact faible",
      risk_safe: "Sûr",
      risk_moderate: "Modéré",
      risk_advanced: "Avancé",
      tweak_unsupported: "Non supporté ici",
      tweak_applied: "Appliqué",
      tweaks_none_cat: "Aucune optimisation dans cette catégorie.",
      adv_modal_title: "Tweaks avancés sélectionnés",
      adv_modal_body: "Les réglages suivants sont marqués avancés : ils modifient des paramètres système sensibles. Un point de restauration est recommandé avant application.",
      adv_confirm: "Appliquer quand même",
      applying: "Application…",
      apply_done: "Application terminée : {ok}",
      apply_ok_one: "{n} réussie",
      apply_ok_many: "{n} réussies",
      apply_fail: " · {n} en échec",
      revert_none: "Aucun tweak appliqué par Overdrive à annuler.",
      revert_body_one: "1 réglage appliqué par Overdrive sera remis à sa valeur d'origine.",
      revert_body_many: "{n} réglages appliqués par Overdrive seront remis à leur valeur d'origine.",
      revert_all: "Tout annuler",
      reverting: "Annulation…",
      revert_done: "Annulation terminée : {ok} / {total}.",
      creating: "Création…",
      restore_created: "Point de restauration créé.",
      restore_failed: "Création impossible.",

      /* Optimisations — petites configs */
      tweak_lowend_badge: "Petite config",
      chip_lowend: "Petite config",
      lowend_banner: "Petite configuration détectée — sélection adaptée disponible.",
      lowend_banner_btn: "Cocher la sélection petite config",
      lowend_selected_one: "{n} optimisation petite config cochée (risque sûr ou modéré).",
      lowend_selected_many: "{n} optimisations petite config cochées (risque sûr ou modéré).",

      /* Jeux */
      games_title: "Jeux",
      games_sub: "Options de lancement et réglages recommandés pour les jeux compétitifs courants.",
      games_detecting: "Détection des jeux installés…",
      games_unavailable: "Détection indisponible pour le moment.",
      games_none: "Aucun jeu détecté automatiquement sur cette machine. Les fiches et recommandations restent consultables.",
      badge_detected: "Détecté",
      badge_not_detected: "Non détecté",
      launch_options: "Options de lancement",
      recommended_settings: "Réglages recommandés",
      cs2_loading: "Lecture de la configuration CS2…",
      cs2_unavailable: "Informations CS2 indisponibles.",
      cs2_config: "Configuration CS2",
      cs2_no_profiles: "Aucun profil Steam (userdata) détecté : l'écriture de l'autoexec n'est pas possible pour le moment.",
      cs2_profile: "Profil",
      cs2_autoexec_yes: "autoexec présent",
      cs2_autoexec_no: "aucun autoexec",
      cs2_write: "Écrire l'autoexec recommandé",
      writing: "Écriture…",
      cs2_preview: "Aperçu de l'autoexec recommandé",
      cs2_video_group: "Réglages vidéo (cs2_video.txt)",
      cs2_video_not_read: "Fichier cs2_video.txt non lu : recommandations générales.",
      th_param: "Paramètre",
      th_current: "Actuel",
      th_recommended: "Recommandé",
      th_note: "Note",

      /* Panneau CS2 — « Pour ta machine » (tiers) */
      cs2_machine_group: "Pour ta machine",
      cs2_tier_detected: "Tier détecté",
      cs2_tier_reasons: "Pourquoi ce classement",
      cs2_tier_select: "Tier des recommandations",
      tier_lowend: "Petite config",
      tier_midrange: "Milieu de gamme",
      tier_highend: "Haut de gamme",
      advice_kind_reco: "Recommandé",
      advice_kind_opinion: "Avis",
      advice_kind_info: "Info",
      cs2_video_read: "Fichier cs2_video.txt lu : comparaison avec vos valeurs actuelles.",
      cs2_apply_video: "Appliquer les réglages vidéo",
      cs2_apply_video_body: "Overdrive ne modifie que les réglages déjà présents dans votre cs2_video.txt — jamais votre résolution. Une sauvegarde automatique est créée dans le coffre de configurations avant toute écriture : vous pourrez revenir en arrière. Si CS2 est lancé, l'application sera refusée : fermez d'abord le jeu.",
      cs2_apply_count_one: "{n} réglage sera modifié (tier « {t} »).",
      cs2_apply_count_many: "{n} réglages seront modifiés (tier « {t} »).",
      cs2_apply_none: "Vos réglages correspondent déjà aux recommandations de ce tier : rien à appliquer.",
      cs2_val_same: "Conforme",
      cs2_res_changed: "Réglages modifiés",
      cs2_res_skipped: "Réglages ignorés",
      cs2_autoexec_group: "Autoexec par tier",
      cs2_launch_group: "Options de lancement par tier",

      /* Latence */
      latency_group: "Latence estimée",
      latency_desc: "Estimation de la latence TCP vers chaque zone (3 connexions par région, aucune donnée envoyée). Ce n'est pas un ping in-game.",
      latency_measure: "Mesurer",
      latency_measuring: "Mesure en cours…",
      latency_failed: "Mesure impossible.",
      th_region: "Région",
      th_min: "Min",
      th_avg: "Moy",
      th_max: "Max",

      /* Nettoyage */
      clean_title: "Nettoyage",
      clean_sub: "Fichiers temporaires, caches de shaders et autres fichiers récupérables.",
      clean_none_title: "Aucune analyse pour l'instant",
      clean_none_body: "Lancez une analyse pour mesurer l'espace récupérable.",
      scan: "Analyser",
      scanning: "Analyse en cours…",
      rescan: "Réanalyser",
      clean_empty_title: "Rien à nettoyer",
      clean_empty_body: "Aucune cible de nettoyage trouvée sur ce système.",
      th_target: "Cible",
      th_path: "Chemin",
      th_files: "Fichiers",
      th_size: "Taille",
      th_result: "Résultat",
      freed: "{x} libérés",
      failed: "Échec",
      clean_total: "Total sélectionné : {x}",
      clean_n: "Nettoyer ({n})",
      clean_modal_title: "Confirmer le nettoyage",
      clean_body_one: "Les fichiers de la cible sélectionnée seront définitivement supprimés.",
      clean_body_many: "Les fichiers des {n} cibles sélectionnées seront définitivement supprimés.",
      clean_confirm: "Nettoyer",
      cleaning: "Nettoyage…",
      clean_done: "Nettoyage terminé : {x} libérés.",

      /* Moniteur */
      monitor_title: "Moniteur",
      monitor_sub: "CPU, mémoire et débits en temps réel, rafraîchis toutes les 2 secondes.",
      mon_cpu: "Processeur",
      mon_ram: "Mémoire",
      mon_disk: "Débit disque",
      mon_net: "Débit réseau",
      mon_read: "Lecture",
      mon_write: "Écriture",
      mon_up: "Envoi",
      mon_down: "Réception",
      mon_top: "Processus les plus actifs",
      th_process: "Processus",
      th_cpu: "CPU",
      th_ram: "RAM",
      mon_waiting: "Collecte des premières mesures…",
      mon_unavail_title: "Moniteur indisponible",
      mon_unavail_body: "Le serveur n'a pas répondu. Réessayez dans un instant.",

      /* Démarrage */
      startup_title: "Démarrage",
      startup_sub: "Programmes lancés au démarrage de Windows. Désactiver conserve l'entrée, exactement comme le Gestionnaire des tâches.",
      startup_loading: "Lecture des programmes au démarrage…",
      startup_unavailable: "Liste indisponible pour le moment.",
      startup_empty_title: "Aucun programme au démarrage",
      startup_empty_windows: "Aucun programme configuré au démarrage de Windows.",
      startup_empty_other: "Cette fonction repose sur le registre Windows : aucune entrée détectée sur ce système.",
      th_name: "Nom",
      th_command: "Commande",
      th_source: "Source",
      th_state: "État",
      state_enabled: "Activé",
      state_disabled: "Désactivé",
      src_user_folder: "Dossier utilisateur",
      src_common_folder: "Dossier commun",
      hklm_modal_title: "Entrée machine (HKLM)",
      hklm_modal_body: "Cette entrée s'applique à tous les utilisateurs de la machine (registre HKLM). Confirmez la modification.",
      startup_toggle_failed: "Modification impossible.",

      /* Assistant */
      assistant_title: "Assistant",
      assistant_sub: "Un assistant qui connaît votre matériel, votre profil et vos optimisations.",
      checking_keys: "Vérification des clés API…",
      assistant_unavailable: "Assistant indisponible pour le moment.",
      no_key_title: "Aucune clé API configurée",
      no_key_body: "Ajoutez une clé (Groq propose une clé gratuite) pour activer l'assistant.",
      open_settings: "Ouvrir les réglages",
      provider: "Fournisseur",
      chat_clear: "Effacer la conversation",
      chat_placeholder: "Votre question sur l'optimisation…",
      send: "Envoyer",
      chat_empty: "Aucun message pour l'instant.",
      chat_example: "Exemple : « Quels réglages pour gagner des FPS sur ma machine ? »",
      chat_pending: "L'assistant rédige une réponse…",
      chat_error_net: "Erreur réseau : la question n'a pas pu être envoyée.",
      chat_no_reply: "Réponse indisponible.",

      /* Réglages */
      settings_title: "Réglages",
      settings_sub: "Clés API, fournisseur par défaut, apparence, langue et questionnaire.",
      keys_group: "Clés API",
      keys_note: "Les clés sont chiffrées localement et ne quittent jamais cette machine, sauf vers le fournisseur que vous choisissez.",
      key_configured: "Configurée",
      key_not_configured: "Non configurée",
      key_placeholder: "Clé API",
      save: "Enregistrer",
      del: "Supprimer",
      groq_note: 'Clé gratuite sur <a href="https://console.groq.com" target="_blank" rel="noopener">console.groq.com</a>',
      assistant_group: "Assistant",
      default_provider: "Fournisseur par défaut",
      default_provider_desc: "Utilisé quand aucun fournisseur n'est précisé.",
      no_keys_yet: "Aucune clé configurée pour l'instant.",
      appearance_group: "Apparence",
      theme: "Thème",
      theme_desc: "Sombre par défaut, clair disponible.",
      light: "Clair",
      dark: "Sombre",
      language: "Langue",
      language_desc: "Langue de l'interface. Les catalogues sont traduits automatiquement.",
      report_group: "Rapport",
      report_name: "Rapport système",
      report_desc: "Un fichier texte complet : matériel, profil, optimisations, jeux détectés.",
      report_download: "Télécharger le rapport système",
      quiz_group: "Questionnaire",
      quiz_profile: "Profil d'optimisation",
      quiz_profile_current: "Profil actuel : {p}",
      quiz_profile_none: "Aucun profil pour l'instant.",
      quiz_redo: "Refaire le questionnaire",
      about_group: "À propos",
      badge_admin: "administrateur",
      badge_not_admin: "non administrateur",
      about_note: "Les clés API sont chiffrées localement et ne quittent jamais cette machine, sauf vers l'API du fournisseur d'IA sélectionné. Les optimisations appliquées sont journalisées et réversibles depuis la page Optimisations.",
      key_enter_first: "Saisissez une clé API avant d'enregistrer.",
      saving: "Enregistrement…",
      key_save_err: "Échec de l'enregistrement de la clé.",
      key_saved: "Clé {p} enregistrée.",
      key_del_title: "Supprimer la clé {p}",
      key_del_body: "La clé sera supprimée du stockage chiffré local.",
      key_del_err: "Échec de la suppression de la clé.",
      key_deleted: "Clé {p} supprimée.",
      default_set: "Fournisseur par défaut : {p}.",

      /* QCM */
      quiz_progress: "Question {i}/{n}",
      later: "Plus tard",
      quiz_multi: "Plusieurs réponses possibles",
      quiz_single: "Une seule réponse",
      prev: "Précédent",
      next: "Suivant",
      finish: "Terminer",
      quiz_analyzing: "Analyse…",
      quiz_profile_prefix: "Profil : {p}",
      quiz_notes_title: "Conseils personnalisés",
      quiz_see_tweaks: "Voir mes optimisations",
      continue_lbl: "Continuer",
      widget_group: "Widget en jeu",
      widget_note: "Petite fenêtre déplaçable par-dessus le jeu : FPS et infos système. Chaque réglage s'applique immédiatement.",
      widget_elements: "Informations affichées",
      widget_el_fps: "FPS", widget_el_game: "Jeu", widget_el_cpu: "CPU",
      widget_el_ram: "RAM", widget_el_net: "Réseau", widget_el_clock: "Heure",
      widget_theme: "Thème du widget",
      widget_theme_desc: "Minimal = texte seul, sans fond : ne masque rien.",
      widget_theme_dark: "Sombre", widget_theme_light: "Clair", widget_theme_minimal: "Minimal",
      widget_layout: "Disposition",
      widget_layout_row: "Ligne", widget_layout_col: "Colonne",
      widget_opacity: "Opacité",
      widget_scale: "Taille",
      widget_click_through: "Cliquer à travers",
      widget_click_through_desc: "La souris passe au travers du widget. Désactivable ici à tout moment.",
      widget_autostart: "Démarrage automatique",
      widget_autostart_desc: "Quand le widget doit-il se lancer ?",
      widget_auto_never: "Jamais",
      widget_auto_always: "Au démarrage de Windows",
      widget_auto_game: "Quand un jeu se lance",
      widget_launch: "Lancer le widget",
      widget_launched: "Widget lancé.",
      widget_saved: "Réglages du widget enregistrés.",
      widget_save_err: "Impossible d'enregistrer les réglages du widget.",
      ob_title: "Démarrage automatique",
      ob_sub: "Choisissez quand le widget (FPS et infos par-dessus le jeu) doit se lancer. Modifiable à tout moment dans Réglages.",
      ob_never_desc: "Le widget ne se lance que manuellement.",
      ob_always_desc: "Le widget est présent dès l'allumage du PC.",
      ob_game_desc: "Invisible au quotidien, il apparaît quand un de vos jeux démarre et disparaît à sa fermeture.",
      ob_launch_now: "Lancer le widget maintenant",
      ob_finish: "Terminer",
      chat_apply: "Appliquer",
      chat_applied: "Appliqué",
      chat_apply_fail: "Échec de l'application.",
      insights_group: "Conseils pour votre machine",
      insights_none: "Rien à signaler : votre configuration ne présente aucun des problèmes courants détectables.",
      insights_badge_important: "Important",
      insights_badge_conseil: "Conseil",
      insights_action: "Ouvrir la page",
      bench_btn: "Benchmark",
      bench_title: "Benchmark rapide",
      bench_intro: "Mesure CPU (mono et multi-cœur), mémoire et disque en une dizaine de secondes. Fermez les applications lourdes pour un résultat fiable. Idéal avant/après l'application d'optimisations.",
      bench_run: "Lancer la mesure",
      bench_running: "Mesure en cours (~10 s)…",
      bench_score: "Score global",
      bench_cpu_single: "CPU (1 cœur)",
      bench_cpu_multi: "CPU (multi)",
      bench_ram: "Mémoire",
      bench_disk_w: "Disque (écriture)",
      bench_disk_r: "Disque (lecture)",
      bench_prev: "Mesure précédente : {s} ({d})",
      bench_err: "Échec du benchmark.",
      debloat_group: "Applications préinstallées",
      debloat_note: "Applications livrées avec Windows et rarement utiles sur un PC de jeu. La suppression ne concerne que votre session et chaque application reste réinstallable depuis le Microsoft Store.",
      debloat_installed: "Installée",
      debloat_absent: "Absente",
      debloat_unknown: "État inconnu",
      debloat_remove: "Supprimer la sélection ({n})",
      debloat_removing: "Suppression…",
      debloat_done: "{n} application(s) supprimée(s).",
      update_group: "Mise à jour",
      update_name: "Version de l'application",
      update_check: "Vérifier",
      update_checking: "Vérification…",
      update_available: "Nouvelle version disponible : {t}",
      update_download: "Télécharger",
      update_none: "Vous êtes à jour.",
      backup_group: "Sauvegarde du profil",
      backup_export: "Exporter",
      backup_export_desc: "Profil, réponses au questionnaire et réglages du widget dans un fichier JSON.",
      backup_import: "Importer",
      backup_imported: "Profil importé.",
      backup_import_err: "Fichier d'export invalide.",
      gamemode_name: "Mode jeu automatique",
      gamemode_desc: "Quand un jeu démarre : plan d'alimentation performance et priorité haute du jeu ; tout est restauré à sa fermeture. Nécessite que le widget tourne.",

      /* Convertisseur de sensibilité */
      sens_group: "Convertisseur de sensibilité",
      sens_desc: "Même rotation réelle (cm/360) d'un jeu à l'autre : choisissez le jeu source, votre sensibilité et le DPI de la souris.",
      sens_game: "Jeu source",
      sens_sens: "Sensibilité",
      sens_dpi: "DPI souris",
      sens_convert: "Convertir",
      sens_converting: "Conversion…",
      sens_cm360: "cm/360",
      sens_cm360_note: "distance de souris pour un tour complet",
      sens_edpi: "eDPI",
      sens_edpi_note: "sensibilité × DPI",
      sens_err_sens: "Sensibilité invalide : saisissez un nombre strictement positif.",
      sens_err_dpi: "DPI invalide : saisissez un entier entre 100 et 26000.",
      sens_failed: "Conversion impossible.",
      sens_unavailable: "Convertisseur indisponible pour le moment.",
      th_game: "Jeu",
      th_sens_conv: "Sensibilité convertie",

      /* Viseurs CS2 */
      xhair_group: "Viseurs CS2",
      xhair_desc: "Styles réalistes inspirés de joueurs professionnels, avec aperçu et code de partage prêt à importer.",
      xhair_inspired: "Inspiré de {p}",
      xhair_howto: "Pour importer : CS2 > Paramètres > Équipement > Partager ou importer le code du viseur. Les commandes console sont un repli garanti si un code était refusé.",
      xhair_copy_code: "Copier le code",
      xhair_copy_console: "Copier les commandes",
      xhair_unavailable: "Viseurs indisponibles pour le moment.",

      /* Coffre de configurations */
      vault_group: "Coffre de configurations",
      vault_desc: "Sauvegarde locale (zip) des fichiers de configuration de vos jeux, restaurable à tout moment.",
      vault_backup_now: "Sauvegarder maintenant",
      vault_backing_up: "Sauvegarde…",
      vault_backups_title: "Sauvegardes",
      vault_no_backups: "Aucune sauvegarde pour l'instant.",
      vault_none_found: "Aucune configuration de jeu détectée sur cette machine : rien à sauvegarder pour le moment.",
      vault_restore: "Restaurer",
      vault_restoring: "Restauration…",
      vault_deleting: "Suppression…",
      vault_restore_title: "Restaurer une sauvegarde",
      vault_restore_body: "Les fichiers de configuration actuels seront remplacés par ceux de « {id} ». Une sauvegarde de sécurité automatique est créée avant toute écriture : vous pourrez revenir en arrière.",
      vault_delete_title: "Supprimer la sauvegarde",
      vault_delete_body: "La sauvegarde « {id} » sera définitivement supprimée.",
      vault_unavailable: "Coffre indisponible pour le moment.",
      th_date: "Date",
      th_games: "Jeux",

      /* Test de stabilité réseau */
      netstab_btn: "Test de stabilité (20 s)",
      netstab_running: "Test de stabilité en cours (~20 s)…",
      netstab_loss: "Perte",
      netstab_jitter: "Gigue",
      netstab_region: "Région testée : {r}",

      /* Activité réseau (moniteur) */
      netusage_group: "Activité réseau",
      netusage_desc: "Applications avec des connexions actives (TCP/UDP) et téléchargements probables.",
      th_app: "Application",
      th_connections: "Connexions",
      netusage_empty: "Aucune application avec des connexions actives n'a pu être détectée sur ce système.",
      netusage_suspects: "Téléchargements probables",
      netusage_unavailable: "Activité réseau indisponible pour le moment.",

      /* Réglages : widget + maintenance */
      widget_el_temp: "Température",
      pause_updates_name: "Suspendre Windows Update pendant la partie",
      pause_updates_desc: "Le service de mise à jour est suspendu au lancement d'un jeu, puis rétabli à sa fermeture.",
      maintenance_group: "Maintenance",
      sched_name: "Nettoyage automatique hebdomadaire (dimanche 11 h)",
      sched_desc: "Nettoie les caches sûrs via le Planificateur de tâches Windows, sans ouvrir l'interface.",
      sched_unavailable: "Planification indisponible pour le moment."
    },
    en: {
      /* Navigation and chrome */
      nav_home: "Home",
      nav_tweaks: "Optimizations",
      nav_games: "Games",
      nav_clean: "Cleanup",
      nav_monitor: "Monitor",
      nav_startup: "Startup",
      nav_assistant: "Assistant",
      nav_settings: "Settings",
      theme_to_dark: "Dark theme",
      theme_to_light: "Light theme",
      loading_ui: "Loading interface…",

      /* Common */
      close: "Close",
      cancel: "Cancel",
      confirm: "Confirm",
      copy: "Copy",
      copied: "Copied",
      copy_failed: "Copy failed",
      refresh: "Refresh",
      retry: "Retry",
      loading: "Loading…",
      err_conn: "Cannot reach the server. Make sure Overdrive is running.",
      err_server: "Server error",
      unit_gb: "GB",
      unit_mb: "MB",
      unit_mbps: "MB/s",

      /* Home */
      home_title: "Home",
      home_sub: "Overview of your machine and its optimization status.",
      stat_profile: "Profile",
      stat_tweaks: "Applied optimizations",
      stat_games: "Detected games",
      stat_profile_note: "Profile from the questionnaire",
      stat_none: "None",
      stat_quiz_link: "Take the questionnaire",
      stat_tweaks_note: "across the whole catalog",
      stat_games_some: "found on this machine",
      stat_games_none: "no game detected",
      hw_group: "Hardware",
      hw_detecting: "Detecting hardware…",
      hw_unavailable: "Hardware unavailable right now.",
      hw_missing: "Hardware unavailable.",
      analyzing: "Analyzing…",
      hw_system: "System",
      hw_cpu: "Processor",
      hw_ram: "Memory",
      hw_gpu: "Graphics card",
      hw_disk: "Storage",
      hw_net: "Network",
      hw_cores: "{p} cores / {l} threads",
      hw_up_to: "up to {m} MHz",
      hw_load: "current load {n}%",
      hw_total: "{g} total",
      hw_avail: "{g} available",
      hw_used: "{n}% used",
      hw_driver: "driver {d}",
      hw_free: "{f} free / {t}",
      hw_none: "Not detected",
      quick_actions: "Quick actions",
      quick_clean: "Scan for cleanup",
      programs_group: "Recommended programs",
      programs_loading: "Loading list…",
      programs_unavailable: "List unavailable right now.",
      programs_none: "No recommended programs.",
      prog_install: "Install",
      prog_site: "Official website",
      prog_installing: "Installing…",
      prog_install_failed: "Installation failed.",
      winget_missing: "winget is not available on this system: direct installation is disabled, links remain available.",
      prog_cat_monitoring: "Monitoring",
      prog_cat_pilotes: "Drivers",
      prog_cat_capture: "Capture",
      prog_cat_utilitaire: "Utility",
      prog_cat_communication: "Communication",
      store_multi: "Multi-platform",

      /* Boost */
      boost_btn: "Boost",
      boost_title: "One-click Boost",
      boost_intro: "Overdrive runs three safe steps to get the machine ready for gaming:",
      boost_step1: "Windows restore point (optional, recommended)",
      boost_step2: "Apply your profile's recommended optimizations",
      boost_step3: "Clean safe caches (temporary files, shader caches)",
      boost_restore_check: "Create a restore point before boosting",
      boost_run: "Run boost",
      boost_running: "Boost running…",
      boost_done: "Boost finished.",
      boost_done_issues: "Boost finished with errors.",
      boost_failed: "The boost could not be started.",
      boost_lbl_restore: "Restore point",
      boost_lbl_tweaks: "Profile tweaks",
      boost_lbl_clean: "Safe cache cleanup",

      /* Optimizations */
      tweaks_title: "Optimizations",
      tweaks_sub: "Pick the tweaks to apply. Every optimization is reversible.",
      tweaks_loading: "Loading catalog…",
      tweaks_unavail_title: "Catalog unavailable",
      tweaks_unavail_body: "The server did not respond. Try again in a moment.",
      notice_not_windows: "Non-Windows system detected: optimizations are shown for reference (development mode) and cannot be applied.",
      notice_not_admin: "Overdrive is not running as administrator: some tweaks (machine registry, services) may fail. Restart the app as administrator for full results.",
      sel_profile: "Profile selection",
      sel_profile_hint: "Take the questionnaire first",
      sel_safe: "All safe",
      sel_none: "Deselect all",
      restore_point: "Restore point",
      revert_applied: "Revert applied tweaks",
      apply_n: "Apply ({n})",
      selected_one: "{n} selected",
      selected_many: "{n} selected",
      chip_all: "All",
      impact_high: "High impact",
      impact_medium: "Medium impact",
      impact_low: "Low impact",
      risk_safe: "Safe",
      risk_moderate: "Moderate",
      risk_advanced: "Advanced",
      tweak_unsupported: "Not supported here",
      tweak_applied: "Applied",
      tweaks_none_cat: "No optimization in this category.",
      adv_modal_title: "Advanced tweaks selected",
      adv_modal_body: "The following tweaks are marked advanced: they change sensitive system settings. A restore point is recommended before applying.",
      adv_confirm: "Apply anyway",
      applying: "Applying…",
      apply_done: "Apply finished: {ok}",
      apply_ok_one: "{n} succeeded",
      apply_ok_many: "{n} succeeded",
      apply_fail: " · {n} failed",
      revert_none: "No Overdrive-applied tweak to revert.",
      revert_body_one: "1 tweak applied by Overdrive will be restored to its original value.",
      revert_body_many: "{n} tweaks applied by Overdrive will be restored to their original values.",
      revert_all: "Revert all",
      reverting: "Reverting…",
      revert_done: "Revert finished: {ok} / {total}.",
      creating: "Creating…",
      restore_created: "Restore point created.",
      restore_failed: "Creation failed.",

      /* Optimizations — low-end machines */
      tweak_lowend_badge: "Low-end",
      chip_lowend: "Low-end",
      lowend_banner: "Low-end machine detected — a tailored selection is available.",
      lowend_banner_btn: "Select the low-end picks",
      lowend_selected_one: "{n} low-end optimization selected (safe or moderate risk).",
      lowend_selected_many: "{n} low-end optimizations selected (safe or moderate risk).",

      /* Games */
      games_title: "Games",
      games_sub: "Launch options and recommended settings for popular competitive games.",
      games_detecting: "Detecting installed games…",
      games_unavailable: "Detection unavailable right now.",
      games_none: "No game detected automatically on this machine. Game sheets and recommendations remain available.",
      badge_detected: "Detected",
      badge_not_detected: "Not detected",
      launch_options: "Launch options",
      recommended_settings: "Recommended settings",
      cs2_loading: "Reading CS2 configuration…",
      cs2_unavailable: "CS2 information unavailable.",
      cs2_config: "CS2 configuration",
      cs2_no_profiles: "No Steam profile (userdata) detected: writing the autoexec is not possible right now.",
      cs2_profile: "Profile",
      cs2_autoexec_yes: "autoexec present",
      cs2_autoexec_no: "no autoexec",
      cs2_write: "Write recommended autoexec",
      writing: "Writing…",
      cs2_preview: "Recommended autoexec preview",
      cs2_video_group: "Video settings (cs2_video.txt)",
      cs2_video_not_read: "cs2_video.txt not read: general recommendations.",
      th_param: "Setting",
      th_current: "Current",
      th_recommended: "Recommended",
      th_note: "Note",

      /* CS2 panel — "For your machine" (tiers) */
      cs2_machine_group: "For your machine",
      cs2_tier_detected: "Detected tier",
      cs2_tier_reasons: "Why this rating",
      cs2_tier_select: "Recommendations tier",
      tier_lowend: "Low-end",
      tier_midrange: "Mid-range",
      tier_highend: "High-end",
      advice_kind_reco: "Recommended",
      advice_kind_opinion: "Opinion",
      advice_kind_info: "Info",
      cs2_video_read: "cs2_video.txt read: compared against your current values.",
      cs2_apply_video: "Apply video settings",
      cs2_apply_video_body: "Overdrive only changes settings already present in your cs2_video.txt — never your resolution. An automatic backup is created in the config vault before anything is written, so you can roll back. If CS2 is running, the change will be refused: close the game first.",
      cs2_apply_count_one: "{n} setting will be changed ({t} tier).",
      cs2_apply_count_many: "{n} settings will be changed ({t} tier).",
      cs2_apply_none: "Your settings already match this tier's recommendations: nothing to apply.",
      cs2_val_same: "Matches",
      cs2_res_changed: "Changed settings",
      cs2_res_skipped: "Skipped settings",
      cs2_autoexec_group: "Autoexec per tier",
      cs2_launch_group: "Launch options per tier",

      /* Latency */
      latency_group: "Estimated latency",
      latency_desc: "TCP latency estimate toward each zone (3 connections per region, no data sent). Not an in-game ping.",
      latency_measure: "Measure",
      latency_measuring: "Measuring…",
      latency_failed: "Measurement failed.",
      th_region: "Region",
      th_min: "Min",
      th_avg: "Avg",
      th_max: "Max",

      /* Cleanup */
      clean_title: "Cleanup",
      clean_sub: "Temporary files, shader caches and other recoverable files.",
      clean_none_title: "No scan yet",
      clean_none_body: "Run a scan to measure recoverable space.",
      scan: "Scan",
      scanning: "Scanning…",
      rescan: "Rescan",
      clean_empty_title: "Nothing to clean",
      clean_empty_body: "No cleanup target found on this system.",
      th_target: "Target",
      th_path: "Path",
      th_files: "Files",
      th_size: "Size",
      th_result: "Result",
      freed: "{x} freed",
      failed: "Failed",
      clean_total: "Selected total: {x}",
      clean_n: "Clean ({n})",
      clean_modal_title: "Confirm cleanup",
      clean_body_one: "Files from the selected target will be permanently deleted.",
      clean_body_many: "Files from the {n} selected targets will be permanently deleted.",
      clean_confirm: "Clean",
      cleaning: "Cleaning…",
      clean_done: "Cleanup finished: {x} freed.",

      /* Monitor */
      monitor_title: "Monitor",
      monitor_sub: "Live CPU, memory and throughput, refreshed every 2 seconds.",
      mon_cpu: "Processor",
      mon_ram: "Memory",
      mon_disk: "Disk throughput",
      mon_net: "Network throughput",
      mon_read: "Read",
      mon_write: "Write",
      mon_up: "Upload",
      mon_down: "Download",
      mon_top: "Most active processes",
      th_process: "Process",
      th_cpu: "CPU",
      th_ram: "RAM",
      mon_waiting: "Collecting first samples…",
      mon_unavail_title: "Monitor unavailable",
      mon_unavail_body: "The server did not respond. Try again in a moment.",

      /* Startup */
      startup_title: "Startup",
      startup_sub: "Programs launched when Windows starts. Disabling keeps the entry, exactly like Task Manager.",
      startup_loading: "Reading startup programs…",
      startup_unavailable: "List unavailable right now.",
      startup_empty_title: "No startup programs",
      startup_empty_windows: "No program configured to start with Windows.",
      startup_empty_other: "This feature relies on the Windows registry: no entry detected on this system.",
      th_name: "Name",
      th_command: "Command",
      th_source: "Source",
      th_state: "State",
      state_enabled: "Enabled",
      state_disabled: "Disabled",
      src_user_folder: "User folder",
      src_common_folder: "Common folder",
      hklm_modal_title: "Machine entry (HKLM)",
      hklm_modal_body: "This entry applies to every user of this machine (HKLM registry). Confirm the change.",
      startup_toggle_failed: "Change failed.",

      /* Assistant */
      assistant_title: "Assistant",
      assistant_sub: "An assistant that knows your hardware, your profile and your optimizations.",
      checking_keys: "Checking API keys…",
      assistant_unavailable: "Assistant unavailable right now.",
      no_key_title: "No API key configured",
      no_key_body: "Add a key (Groq offers a free one) to enable the assistant.",
      open_settings: "Open settings",
      provider: "Provider",
      chat_clear: "Clear conversation",
      chat_placeholder: "Your optimization question…",
      send: "Send",
      chat_empty: "No messages yet.",
      chat_example: "Example: \"Which settings will give me more FPS on my machine?\"",
      chat_pending: "The assistant is writing a reply…",
      chat_error_net: "Network error: your question could not be sent.",
      chat_no_reply: "No reply available.",

      /* Settings */
      settings_title: "Settings",
      settings_sub: "API keys, default provider, appearance, language and questionnaire.",
      keys_group: "API keys",
      keys_note: "Keys are encrypted locally and never leave this machine, except toward the provider you choose.",
      key_configured: "Configured",
      key_not_configured: "Not configured",
      key_placeholder: "API key",
      save: "Save",
      del: "Delete",
      groq_note: 'Free key at <a href="https://console.groq.com" target="_blank" rel="noopener">console.groq.com</a>',
      assistant_group: "Assistant",
      default_provider: "Default provider",
      default_provider_desc: "Used when no provider is specified.",
      no_keys_yet: "No key configured yet.",
      appearance_group: "Appearance",
      theme: "Theme",
      theme_desc: "Dark by default, light available.",
      light: "Light",
      dark: "Dark",
      language: "Language",
      language_desc: "Interface language. Catalogs are translated automatically.",
      report_group: "Report",
      report_name: "System report",
      report_desc: "A complete text file: hardware, profile, optimizations, detected games.",
      report_download: "Download system report",
      quiz_group: "Questionnaire",
      quiz_profile: "Optimization profile",
      quiz_profile_current: "Current profile: {p}",
      quiz_profile_none: "No profile yet.",
      quiz_redo: "Retake the questionnaire",
      about_group: "About",
      badge_admin: "administrator",
      badge_not_admin: "not administrator",
      about_note: "API keys are encrypted locally and never leave this machine, except toward the selected AI provider's API. Applied optimizations are logged and reversible from the Optimizations page.",
      key_enter_first: "Enter an API key before saving.",
      saving: "Saving…",
      key_save_err: "Failed to save the key.",
      key_saved: "{p} key saved.",
      key_del_title: "Delete the {p} key",
      key_del_body: "The key will be removed from the local encrypted storage.",
      key_del_err: "Failed to delete the key.",
      key_deleted: "{p} key deleted.",
      default_set: "Default provider: {p}.",

      /* Quiz */
      quiz_progress: "Question {i}/{n}",
      later: "Later",
      quiz_multi: "Multiple answers possible",
      quiz_single: "One answer only",
      prev: "Previous",
      next: "Next",
      finish: "Finish",
      quiz_analyzing: "Analyzing…",
      quiz_profile_prefix: "Profile: {p}",
      quiz_notes_title: "Personalized tips",
      quiz_see_tweaks: "See my optimizations",
      continue_lbl: "Continue",
      widget_group: "In-game widget",
      widget_note: "Small movable window on top of the game: FPS and system info. Every setting applies instantly.",
      widget_elements: "Displayed information",
      widget_el_fps: "FPS", widget_el_game: "Game", widget_el_cpu: "CPU",
      widget_el_ram: "RAM", widget_el_net: "Network", widget_el_clock: "Clock",
      widget_theme: "Widget theme",
      widget_theme_desc: "Minimal = text only, no background: hides nothing.",
      widget_theme_dark: "Dark", widget_theme_light: "Light", widget_theme_minimal: "Minimal",
      widget_layout: "Layout",
      widget_layout_row: "Row", widget_layout_col: "Column",
      widget_opacity: "Opacity",
      widget_scale: "Size",
      widget_click_through: "Click-through",
      widget_click_through_desc: "The mouse passes through the widget. Can be turned off here anytime.",
      widget_autostart: "Autostart",
      widget_autostart_desc: "When should the widget launch?",
      widget_auto_never: "Never",
      widget_auto_always: "At Windows startup",
      widget_auto_game: "When a game starts",
      widget_launch: "Launch widget",
      widget_launched: "Widget launched.",
      widget_saved: "Widget settings saved.",
      widget_save_err: "Could not save widget settings.",
      ob_title: "Autostart",
      ob_sub: "Choose when the widget (FPS and info over the game) should launch. You can change this anytime in Settings.",
      ob_never_desc: "The widget only launches manually.",
      ob_always_desc: "The widget is there as soon as the PC boots.",
      ob_game_desc: "Invisible day to day; it appears when one of your games starts and goes away when it closes.",
      ob_launch_now: "Launch the widget now",
      ob_finish: "Finish",
      chat_apply: "Apply",
      chat_applied: "Applied",
      chat_apply_fail: "Could not apply.",
      insights_group: "Advice for your machine",
      insights_none: "Nothing to report: your setup shows none of the common detectable issues.",
      insights_badge_important: "Important",
      insights_badge_conseil: "Tip",
      insights_action: "Open page",
      bench_btn: "Benchmark",
      bench_title: "Quick benchmark",
      bench_intro: "Measures CPU (single and multi-core), memory and disk in about ten seconds. Close heavy apps for a reliable result. Ideal before/after applying optimizations.",
      bench_run: "Run benchmark",
      bench_running: "Measuring (~10 s)…",
      bench_score: "Overall score",
      bench_cpu_single: "CPU (1 core)",
      bench_cpu_multi: "CPU (multi)",
      bench_ram: "Memory",
      bench_disk_w: "Disk (write)",
      bench_disk_r: "Disk (read)",
      bench_prev: "Previous run: {s} ({d})",
      bench_err: "Benchmark failed.",
      debloat_group: "Preinstalled apps",
      debloat_note: "Apps bundled with Windows and rarely useful on a gaming PC. Removal only affects your account and every app can be reinstalled from the Microsoft Store.",
      debloat_installed: "Installed",
      debloat_absent: "Not present",
      debloat_unknown: "Unknown state",
      debloat_remove: "Remove selection ({n})",
      debloat_removing: "Removing…",
      debloat_done: "{n} app(s) removed.",
      update_group: "Update",
      update_name: "Application version",
      update_check: "Check",
      update_checking: "Checking…",
      update_available: "New version available: {t}",
      update_download: "Download",
      update_none: "You are up to date.",
      backup_group: "Profile backup",
      backup_export: "Export",
      backup_export_desc: "Profile, questionnaire answers and widget settings in a JSON file.",
      backup_import: "Import",
      backup_imported: "Profile imported.",
      backup_import_err: "Invalid export file.",
      gamemode_name: "Automatic game mode",
      gamemode_desc: "When a game starts: performance power plan and high priority for the game; everything is restored when it closes. Requires the widget to be running.",

      /* Sensitivity converter */
      sens_group: "Sensitivity converter",
      sens_desc: "Same real rotation (cm/360) across games: pick the source game, your sensitivity and your mouse DPI.",
      sens_game: "Source game",
      sens_sens: "Sensitivity",
      sens_dpi: "Mouse DPI",
      sens_convert: "Convert",
      sens_converting: "Converting…",
      sens_cm360: "cm/360",
      sens_cm360_note: "mouse distance for a full turn",
      sens_edpi: "eDPI",
      sens_edpi_note: "sensitivity × DPI",
      sens_err_sens: "Invalid sensitivity: enter a strictly positive number.",
      sens_err_dpi: "Invalid DPI: enter an integer between 100 and 26000.",
      sens_failed: "Conversion failed.",
      sens_unavailable: "Converter unavailable right now.",
      th_game: "Game",
      th_sens_conv: "Converted sensitivity",

      /* CS2 crosshairs */
      xhair_group: "CS2 crosshairs",
      xhair_desc: "Realistic styles inspired by professional players, with a preview and a ready-to-import share code.",
      xhair_inspired: "Inspired by {p}",
      xhair_howto: "To import: CS2 > Settings > Equipment > Share or import crosshair code. The console commands are a guaranteed fallback if a code were rejected.",
      xhair_copy_code: "Copy code",
      xhair_copy_console: "Copy commands",
      xhair_unavailable: "Crosshairs unavailable right now.",

      /* Config vault */
      vault_group: "Config vault",
      vault_desc: "Local zip backups of your games' configuration files, restorable at any time.",
      vault_backup_now: "Back up now",
      vault_backing_up: "Backing up…",
      vault_backups_title: "Backups",
      vault_no_backups: "No backup yet.",
      vault_none_found: "No game configuration detected on this machine: nothing to back up right now.",
      vault_restore: "Restore",
      vault_restoring: "Restoring…",
      vault_deleting: "Deleting…",
      vault_restore_title: "Restore a backup",
      vault_restore_body: "Current configuration files will be replaced by those from \"{id}\". An automatic safety backup is created before anything is written, so you can roll back.",
      vault_delete_title: "Delete backup",
      vault_delete_body: "The backup \"{id}\" will be permanently deleted.",
      vault_unavailable: "Vault unavailable right now.",
      th_date: "Date",
      th_games: "Games",

      /* Network stability test */
      netstab_btn: "Stability test (20 s)",
      netstab_running: "Stability test running (~20 s)…",
      netstab_loss: "Loss",
      netstab_jitter: "Jitter",
      netstab_region: "Tested region: {r}",

      /* Network activity (monitor) */
      netusage_group: "Network activity",
      netusage_desc: "Applications with active connections (TCP/UDP) and likely downloads.",
      th_app: "Application",
      th_connections: "Connections",
      netusage_empty: "No application with active connections could be detected on this system.",
      netusage_suspects: "Likely downloads",
      netusage_unavailable: "Network activity unavailable right now.",

      /* Settings: widget + maintenance */
      widget_el_temp: "Temperature",
      pause_updates_name: "Pause Windows Update during the game",
      pause_updates_desc: "The update service is paused when a game starts, then resumed when it closes.",
      maintenance_group: "Maintenance",
      sched_name: "Weekly automatic cleanup (Sunday 11 AM)",
      sched_desc: "Cleans safe caches via the Windows Task Scheduler, without opening the interface.",
      sched_unavailable: "Scheduling unavailable right now."
    }
  };

  /* Chaîne d'interface pour la langue courante (repli : français, puis clé). */
  function t(key) {
    var dict = I18N[LANG] || I18N.fr;
    if (Object.prototype.hasOwnProperty.call(dict, key)) { return dict[key]; }
    if (Object.prototype.hasOwnProperty.call(I18N.fr, key)) { return I18N.fr[key]; }
    return key;
  }

  /* t() + remplacement de gabarits {x}. */
  function tf(key, repl) {
    var s = t(key);
    Object.keys(repl || {}).forEach(function (k) {
      s = s.split("{" + k + "}").join(String(repl[k]));
    });
    return s;
  }

  /* Singulier / pluriel avec gabarit {n}. */
  function tp(n, oneKey, manyKey) {
    return tf(n > 1 ? manyKey : oneKey, { n: n });
  }

  /* Champ traduit d'un objet de l'API : obj[field + "_en"] si lang=en, sinon obj[field]. */
  function tr(obj, field) {
    if (!obj) { return ""; }
    if (LANG === "en") {
      var en = obj[field + "_en"];
      if (en !== undefined && en !== null && en !== "") { return en; }
    }
    var v = obj[field];
    return v === undefined || v === null ? "" : v;
  }

  /* Textes statiques de index.html (navigation, libellés fixes). */
  function applyStaticI18n() {
    document.documentElement.lang = LANG;
    $all("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.dataset.i18n);
    });
    updateThemeLabel();
  }

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
    tweakLowendOnly: false,  // filtre « Petite config » (cumulable aux catégories)
    tweakResults: {},        // id → {ok, message}
    games: null,             // GET /api/games → liste
    selectedGame: null,
    cs2: null,               // GET /api/games/cs2
    cs2Tier: null,           // tier choisi dans le panneau (null = détecté)
    cs2VideoResult: null,    // dernier résultat POST /api/games/cs2/video
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
    quiz: null,
    monitorHist: { cpu: [], ram: [], disk: [], net: [] },  // 60 derniers points
    startupItems: null,      // GET /api/startup → liste
    latency: null,           // POST /api/latency → résultats
    latencyBusy: false,
    netstab: null,           // POST /api/netstab → résultat du test de stabilité
    netstabBusy: false,
    sensGames: null,         // GET /api/sens/games → liste
    sensForm: { game: null, sens: "", dpi: "800" },
    sensResult: null,        // POST /api/sens/convert → résultat
    sensError: null,         // erreur de validation côté client
    crosshairs: null,        // GET /api/crosshairs → liste
    vault: null,             // GET /api/vault → {targets, backups}
    vaultSelection: new Set(),
    schedule: null           // GET /api/schedule → {enabled, supported, detail}
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
    trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    zap: '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    activity: '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>'
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

  /* Nombre décimal localisé (virgule en français, point en anglais). */
  function dec(x) {
    var s = String(x);
    return LANG === "en" ? s : s.replace(".", ",");
  }

  function fmtMb(mb) {
    if (mb === null || mb === undefined) { return "—"; }
    if (mb >= 1024) { return dec((mb / 1024).toFixed(1)) + " " + t("unit_gb"); }
    return dec(Math.round(mb * 10) / 10) + " " + t("unit_mb");
  }

  function fmtGb(gb) {
    if (gb === null || gb === undefined) { return "—"; }
    return dec(Math.round(gb * 10) / 10) + " " + t("unit_gb");
  }

  function fmtRate(mbps) {
    if (mbps === null || mbps === undefined) { return "—"; }
    return dec((Math.round(mbps * 10) / 10).toFixed(1)) + " " + t("unit_mbps");
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
    btn.innerHTML = ok ? icon("check") + " " + esc(t("copied")) : esc(t("copy_failed"));
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
    eleve: { key: "impact_high", cls: "badge-blue" },
    moyen: { key: "impact_medium", cls: "badge-gray" },
    faible: { key: "impact_low", cls: "badge-gray" }
  };

  var RISK_META = {
    sur: { key: "risk_safe", cls: "badge-green" },
    modere: { key: "risk_moderate", cls: "badge-yellow" },
    avance: { key: "risk_advanced", cls: "badge-red" }
  };

  var STORE_LABELS = {
    steam: "Steam", riot: "Riot Client", epic: "Epic Games",
    battlenet: "Battle.net", ea: "EA App"
  };

  function storeLabel(id) {
    if (id === "multi") { return t("store_multi"); }
    return STORE_LABELS[id] || id || "";
  }

  function programCategory(id) {
    var key = "prog_cat_" + id;
    var label = t(key);
    return label === key ? (id || "") : label;
  }

  var PROVIDERS_META = [
    { id: "groq", name: "Groq", noteKey: "groq_note" },
    { id: "openai", name: "OpenAI", noteKey: null },
    { id: "anthropic", name: "Anthropic", noteKey: null },
    { id: "gemini", name: "Google Gemini", noteKey: null }
  ];

  function providerName(id) {
    for (var i = 0; i < PROVIDERS_META.length; i++) {
      if (PROVIDERS_META[i].id === id) { return PROVIDERS_META[i].name; }
    }
    return id;
  }

  /* Source d'une entrée de démarrage, traduite (HKCU/HKLM restent tels quels). */
  function startupSourceLabel(source) {
    if (source === "dossier utilisateur") { return t("src_user_folder"); }
    if (source === "dossier commun") { return t("src_common_folder"); }
    return source || "";
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
      showBanner(t("err_conn"), "error");
      throw e;
    }
    var data = null;
    try { data = await res.json(); } catch (e2) { data = null; }
    if (!res.ok) {
      var msg = data && data.detail ? String(data.detail) : t("err_server") + " (" + res.status + ")";
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
      '<button class="btn btn-ghost btn-sm banner-close" type="button" aria-label="' + esc(t("close")) + '">' + icon("x") + "</button>";
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
      '<button class="btn btn-ghost btn-sm" id="modal-x" type="button" aria-label="' + esc(t("close")) + '">' + icon("x") + "</button></div>" +
      '<div class="modal-body">' + (opts.bodyHtml || "") + "</div>" +
      '<div class="modal-foot">' +
      '<button class="btn" id="modal-cancel" type="button">' + esc(opts.cancelLabel || t("cancel")) + "</button>" +
      '<button class="btn ' + (opts.danger ? "btn-danger-solid" : "btn-primary") + '" id="modal-confirm" type="button">' +
      esc(opts.confirmLabel || t("confirm")) + "</button>" +
      "</div></div></div>";

    function close() {
      root.hidden = true;
      root.innerHTML = "";
      if (opts.onCancel) { opts.onCancel(); }
    }
    byId("modal-x").addEventListener("click", close);
    byId("modal-cancel").addEventListener("click", close);
    byId("modal-confirm").addEventListener("click", function () {
      if (opts.keepOpen) {
        // La modale reste ouverte (ex. benchmark) : onConfirm gère l'affichage.
        if (opts.onConfirm) { opts.onConfirm(); }
        return;
      }
      root.hidden = true;
      root.innerHTML = "";
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
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("overdrive-theme", theme); } catch (e) { /* stockage indisponible */ }
    updateThemeLabel();
  }

  function updateThemeLabel() {
    var label = byId("theme-label");
    if (label) { label.textContent = currentTheme() === "dark" ? t("theme_to_light") : t("theme_to_dark"); }
    $all(".seg[data-seg='theme'] button").forEach(function (b) {
      b.classList.toggle("active", b.dataset.theme === currentTheme());
    });
  }

  async function setTheme(theme) {
    applyTheme(theme);
    try { await api("/api/settings", { body: { theme: theme } }); } catch (e) { /* déjà signalé */ }
  }

  /* ------------------------------------------------------------------ */
  /* Langue FR / EN                                                      */
  /* ------------------------------------------------------------------ */

  function applyLang(lang) {
    LANG = lang === "en" ? "en" : "fr";
    try { localStorage.setItem("overdrive-lang", LANG); } catch (e) { /* stockage indisponible */ }
    applyStaticI18n();
  }

  async function setLang(lang) {
    if (lang === LANG) { return; }
    applyLang(lang);
    render();
    try { await api("/api/settings", { body: { lang: lang } }); } catch (e) { /* déjà signalé */ }
  }

  /* ------------------------------------------------------------------ */
  /* Routeur (hash routing)                                              */
  /* ------------------------------------------------------------------ */

  var routes = {
    "/": renderHome,
    "/tweaks": renderTweaks,
    "/games": renderGames,
    "/clean": renderClean,
    "/monitor": renderMonitor,
    "/startup": renderStartup,
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
    stopMonitor();           /* l'intervalle du moniteur ne survit jamais à la page */
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
      '<h1 class="page-title">' + esc(t("home_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("home_sub")) + "</p>" +
      '<div class="stats-row">' +
      statCard("stat-profile", t("stat_profile"), "…", "") +
      statCard("stat-tweaks", t("stat_tweaks"), "…", "") +
      statCard("stat-games", t("stat_games"), "…", "") +
      "</div>" +
      '<div class="group-label">' + esc(t("hw_group")) + ' <span class="spacer"></span>' +
      '<button class="btn btn-ghost btn-sm" id="btn-hw-refresh" type="button">' + icon("refresh") + " " + esc(t("refresh")) + "</button></div>" +
      '<div id="hw-area"><div class="loading-line">' + esc(t("hw_detecting")) + "</div></div>" +
      '<div class="group-label">' + esc(t("quick_actions")) + "</div>" +
      '<div class="quick-actions">' +
      '<button class="btn btn-primary" id="btn-boost" type="button">' + icon("zap") + " " + esc(t("boost_btn")) + "</button>" +
      '<button class="btn" id="btn-quick-clean" type="button">' + icon("search") + " " + esc(t("quick_clean")) + "</button>" +
      '<button class="btn" id="btn-bench" type="button">' + icon("activity") + " " + esc(t("bench_btn")) + "</button>" +
      "</div>" +
      '<div class="group-label">' + esc(t("insights_group")) + "</div>" +
      '<div id="insights-area"><div class="loading-line">' + esc(t("loading")) + "</div></div>" +
      '<div class="group-label">' + esc(t("programs_group")) + "</div>" +
      '<div id="programs-area"><div class="loading-line">' + esc(t("programs_loading")) + "</div></div>";

    byId("btn-boost").addEventListener("click", openBoostModal);
    byId("btn-bench").addEventListener("click", openBenchModal);
    byId("btn-quick-clean").addEventListener("click", function () {
      state.autoScan = true;
      if (currentRoute() === "/clean") { render(); } else { window.location.hash = "#/clean"; }
    });
    byId("btn-hw-refresh").addEventListener("click", function () {
      var btn = byId("btn-hw-refresh");
      setBusy(btn, t("analyzing"));
      loadHardware(seq, true).then(function () { clearBusy(btn); });
    });

    updateProfileStat();
    loadHardware(seq, false);
    loadHomeStats(seq);
    loadPrograms(seq);
    loadInsights(seq);
  }

  /** Charge et affiche les conseils (détections intelligentes). */
  async function loadInsights(seq) {
    var area = byId("insights-area");
    if (!area) { return; }
    var items = [];
    try {
      var res = await api("/api/insights");
      items = (res && res.insights) || [];
    } catch (e) {
      items = [];
    }
    if (!alive(seq)) { return; }
    area = byId("insights-area");
    if (!area) { return; }
    if (!items.length) {
      area.innerHTML = '<div class="card"><p class="muted small" style="margin:0">' +
        esc(t("insights_none")) + "</p></div>";
      return;
    }
    area.innerHTML = '<div class="card">' + items.map(function (it) {
      var badge = it.severity === "important" ?
        '<span class="badge badge-red">' + esc(t("insights_badge_important")) + "</span>" :
        '<span class="badge badge-yellow">' + esc(t("insights_badge_conseil")) + "</span>";
      return '<div class="settings-row">' +
        '<div class="set-info"><div class="set-name">' + badge + " " + esc(tr(it, "title")) + "</div>" +
        '<div class="set-status">' + esc(tr(it, "detail")) + "</div></div>" +
        (it.action_url ?
          '<div class="set-controls"><a class="btn btn-sm" href="' + esc(it.action_url) +
          '" target="_blank" rel="noopener">' + icon("external") + " " + esc(t("insights_action")) + "</a></div>" : "") +
        "</div>";
    }).join("") + "</div>";
  }

  /** Modale du mini-benchmark avant/après. */
  function openBenchModal() {
    var prev = null;
    api("/api/bench/history").then(function (h) {
      prev = (h && h.history && h.history[0]) || null;
    }).catch(function () { /* silencieux */ });

    openModal({
      title: t("bench_title"),
      bodyHtml: '<p>' + esc(t("bench_intro")) + '</p><div id="bench-out"></div>',
      confirmLabel: t("bench_run"),
      keepOpen: true,
      onConfirm: async function () {
        var out = byId("bench-out");
        var btn = byId("modal-confirm");
        if (out) { out.innerHTML = '<div class="loading-line">' + esc(t("bench_running")) + "</div>"; }
        if (btn) { btn.disabled = true; }
        try {
          var r = await api("/api/bench", { method: "POST" });
          var s = r.scores || {};
          function row(lbl, val, unit) {
            return '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(lbl) +
              '</div></div><div class="set-controls"><span class="mono mono-inline">' + val + (unit || "") + "</span></div></div>";
          }
          var html =
            '<div class="card" style="margin-top:12px">' +
            row(t("bench_score"), '<strong>' + Math.round(r.total) + "</strong>") +
            row(t("bench_cpu_single"), Math.round(s.cpu_single)) +
            row(t("bench_cpu_multi"), Math.round(s.cpu_multi)) +
            row(t("bench_ram"), Math.round(s.ram_mbps), " Mo/s") +
            row(t("bench_disk_w"), Math.round(s.disk_write_mbps), " Mo/s") +
            row(t("bench_disk_r"), Math.round(s.disk_read_mbps), " Mo/s") +
            "</div>";
          if (prev && prev.total) {
            var delta = ((r.total - prev.total) / prev.total) * 100;
            var sign = delta >= 0 ? "+" : "";
            html += '<p class="muted small">' +
              esc(tf("bench_prev", { s: Math.round(prev.total), d: sign + delta.toFixed(1) + " %" })) + "</p>";
          }
          if (out) { out.innerHTML = html; }
          prev = r;
        } catch (e) {
          if (out) { out.innerHTML = '<p class="muted small">' + esc(t("bench_err")) + "</p>"; }
        }
        if (btn) { btn.disabled = false; }
      }
    });
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
      card.querySelector(".stat-value").textContent = tr(state.profile, "label") || state.profile.id;
      card.querySelector(".stat-note").textContent = t("stat_profile_note");
    } else {
      card.querySelector(".stat-value").textContent = t("stat_none");
      card.querySelector(".stat-note").innerHTML =
        '<button class="link-btn" id="link-open-quiz" type="button">' + esc(t("stat_quiz_link")) + "</button>";
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
          byId("hw-area").innerHTML = '<p class="muted small">' + esc(t("hw_unavailable")) + "</p>";
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
      (body || '<div class="hw-line muted small">' + esc(t("hw_none")) + "</div>") + "</div>";
  }

  function hardwareHtml(h) {
    if (!h) { return '<p class="muted small">' + esc(t("hw_missing")) + "</p>"; }
    var os = h.os || {}, cpu = h.cpu || {}, ram = h.ram || {};
    var gpus = h.gpus || [], disks = h.disks || [], net = h.network || {};

    var html = "";
    if (h.summary) {
      html += '<div class="mono-block hw-summary"><pre>' + esc(h.summary) + "</pre></div>";
    }
    html += '<div class="hw-grid">';
    html += hwCard(t("hw_system"), [
      esc([os.name, os.version].filter(Boolean).join(" ")) + (os.build ? ' <span class="muted">(build ' + esc(os.build) + ")</span>" : "")
    ]);
    html += hwCard(t("hw_cpu"), [
      esc(cpu.name || ""),
      (cpu.cores_physical ? esc(tf("hw_cores", { p: cpu.cores_physical, l: cpu.cores_logical || "?" })) : ""),
      (cpu.freq_mhz_max ? esc(tf("hw_up_to", { m: Math.round(cpu.freq_mhz_max) })) : ""),
      (cpu.usage_percent !== undefined && cpu.usage_percent !== null ? esc(tf("hw_load", { n: Math.round(cpu.usage_percent) })) : "")
    ]);
    html += hwCard(t("hw_ram"), [
      ram.total_gb !== undefined ? esc(tf("hw_total", { g: fmtGb(ram.total_gb) })) : "",
      ram.available_gb !== undefined ? esc(tf("hw_avail", { g: fmtGb(ram.available_gb) })) : "",
      ram.used_percent !== undefined ? esc(tf("hw_used", { n: Math.round(ram.used_percent) })) : ""
    ]);
    html += hwCard(t("hw_gpu"), gpus.length ? gpus.map(function (g) {
      return esc(g.name || "GPU") +
        (g.vram_mb ? ' <span class="muted">· ' + esc(fmtMb(g.vram_mb)) + "</span>" : "") +
        (g.driver ? ' <span class="muted">· ' + esc(tf("hw_driver", { d: g.driver })) + "</span>" : "");
    }) : []);
    html += hwCard(t("hw_disk"), disks.map(function (d) {
      return esc(d.mountpoint || d.device || "") + ' <span class="muted">· ' +
        esc(tf("hw_free", { f: fmtGb(d.free_gb), t: fmtGb(d.total_gb) })) + "</span>";
    }));
    var ifaces = (net.interfaces || []).slice(0, 4);
    html += hwCard(t("hw_net"), [esc(net.hostname || "")].concat(ifaces.map(function (i) {
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
        var applied = list.filter(function (x) { return x.applied === true; }).length;
        byId("stat-tweaks").querySelector(".stat-value").textContent = applied + " / " + list.length;
        byId("stat-tweaks").querySelector(".stat-note").textContent = t("stat_tweaks_note");
      }
    } catch (e) { /* bandeau déjà affiché */ }

    try {
      var games = await gamesP;
      if (alive(seq) && byId("stat-games")) {
        var n = games.filter(function (g) { return g.installed; }).length;
        byId("stat-games").querySelector(".stat-value").textContent = n + " / " + games.length;
        byId("stat-games").querySelector(".stat-note").textContent = n ? t("stat_games_some") : t("stat_games_none");
      }
    } catch (e2) { /* idem */ }
  }

  async function loadPrograms(seq) {
    if (!state.programs) {
      try {
        state.programs = await api("/api/programs");
      } catch (e) {
        if (alive(seq) && byId("programs-area")) {
          byId("programs-area").innerHTML = '<p class="muted small">' + esc(t("programs_unavailable")) + "</p>";
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
    if (!progs.length) { return '<p class="muted small">' + esc(t("programs_none")) + "</p>"; }
    var cards = progs.map(function (p) {
      var actions = "";
      if (hasWinget && p.winget_id) {
        actions += '<button class="btn btn-sm" data-install="' + esc(p.id) + '" type="button">' +
          icon("download") + " " + esc(t("prog_install")) + "</button>";
      }
      if (p.url) {
        actions += '<a class="btn btn-sm ' + (hasWinget && p.winget_id ? "btn-ghost" : "") +
          '" href="' + esc(p.url) + '" target="_blank" rel="noopener">' + icon("external") + " " + esc(t("prog_site")) + "</a>";
      }
      return '<div class="card program-card">' +
        '<div class="prog-head"><span class="card-title">' + esc(p.name) + "</span>" +
        '<span class="badge badge-gray">' + esc(programCategory(p.category)) + "</span></div>" +
        '<div class="prog-desc">' + esc(tr(p, "description")) + "</div>" +
        '<div class="prog-foot">' + actions + "</div>" +
        '<div class="prog-result" id="prog-res-' + esc(p.id) + '"></div>' +
        "</div>";
    }).join("");
    var note = hasWinget ? "" :
      '<p class="muted small">' + esc(t("winget_missing")) + "</p>";
    return note + '<div class="grid grid-3">' + cards + "</div>";
  }

  async function onInstallProgram(e) {
    var btn = e.currentTarget;
    var id = btn.dataset.install;
    setBusy(btn, t("prog_installing"));
    var box = byId("prog-res-" + id);
    try {
      var res = await api("/api/programs/install", { body: { id: id } });
      if (box) {
        box.innerHTML = '<span class="' + (res.ok ? "ok-text" : "err-text") + '">' + esc(res.message || "") + "</span>";
      }
    } catch (err) {
      if (box) { box.innerHTML = '<span class="err-text">' + esc(t("prog_install_failed")) + "</span>"; }
    }
    clearBusy(btn);
  }

  /* ------------------------------------------------------------------ */
  /* Boost en un clic (modale récap → POST /api/boost → résultats)       */
  /* ------------------------------------------------------------------ */

  function boostStepLabel(step, fallback) {
    var keys = { restore: "boost_lbl_restore", tweaks: "boost_lbl_tweaks", clean: "boost_lbl_clean" };
    if (keys[step]) { return t(keys[step]); }
    return fallback || step;
  }

  function openBoostModal() {
    var root = byId("modal-root");
    root.hidden = false;
    root.innerHTML =
      '<div class="modal-overlay">' +
      '<div class="modal" role="dialog" aria-modal="true" aria-label="' + esc(t("boost_title")) + '">' +
      '<div class="modal-head"><h3 class="modal-title">' + esc(t("boost_title")) + "</h3>" +
      '<button class="btn btn-ghost btn-sm" id="boost-x" type="button" aria-label="' + esc(t("close")) + '">' + icon("x") + "</button></div>" +
      '<div class="modal-body" id="boost-body">' +
      "<p>" + esc(t("boost_intro")) + "</p>" +
      '<ul class="boost-steps">' +
      [t("boost_step1"), t("boost_step2"), t("boost_step3")].map(function (step) {
        return '<li><span class="step-ic">' + icon("right") + "</span>" +
          '<span class="step-body">' + esc(step) + "</span></li>";
      }).join("") +
      "</ul>" +
      '<label class="boost-restore">' +
      '<input type="checkbox" id="boost-restore" checked>' +
      "<span>" + esc(t("boost_restore_check")) + "</span></label>" +
      "</div>" +
      '<div class="modal-foot" id="boost-foot">' +
      '<button class="btn" id="boost-cancel" type="button">' + esc(t("cancel")) + "</button>" +
      '<button class="btn btn-primary" id="boost-run" type="button">' + icon("zap") + " " + esc(t("boost_run")) + "</button>" +
      "</div></div></div>";

    var ran = false;

    function close() {
      root.hidden = true;
      root.innerHTML = "";
      if (ran) {
        /* Les tweaks et le nettoyage ont pu changer : invalide les caches. */
        state.tweaks = null;
        state.cleanTargets = null;
        state.cleanSelection = new Set();
        state.cleanResults = {};
        render();
      }
    }

    byId("boost-x").addEventListener("click", close);
    byId("boost-cancel").addEventListener("click", close);
    root.querySelector(".modal-overlay").addEventListener("click", function (e) {
      if (e.target === e.currentTarget) { close(); }
    });

    byId("boost-run").addEventListener("click", async function () {
      var runBtn = byId("boost-run");
      var restore = !!(byId("boost-restore") && byId("boost-restore").checked);
      setBusy(runBtn, t("boost_running"));
      var cancelBtn = byId("boost-cancel");
      if (cancelBtn) { cancelBtn.disabled = true; }
      var res;
      try {
        res = await api("/api/boost", { body: { restore_point: restore } });
      } catch (e) {
        clearBusy(runBtn);
        if (cancelBtn) { cancelBtn.disabled = false; }
        var body = byId("boost-body");
        if (body) {
          body.insertAdjacentHTML("beforeend",
            '<p class="err-text small">' + esc(t("boost_failed")) + "</p>");
        }
        return;
      }
      ran = true;
      var steps = (res && res.steps) || [];
      var stepsHtml = steps.map(function (s) {
        var details = (s.details || []).map(function (d) {
          var name = d.name || d.id || "";
          var msg = d.message || "";
          var extra = d.freed_mb !== undefined && d.freed_mb !== null ? " · " + fmtMb(d.freed_mb) : "";
          return '<li class="' + (d.ok === false ? "err-text" : "") + '">' +
            esc(name) + (name && msg ? " — " : "") + esc(msg) + esc(extra) + "</li>";
        }).join("");
        return '<li><span class="step-ic ' + (s.ok ? "ok" : "fail") + '">' +
          icon(s.ok ? "check" : "x") + "</span>" +
          '<span class="step-body">' +
          '<span class="step-name">' + esc(boostStepLabel(s.step, s.label)) + "</span>" +
          '<span class="step-msg">' + esc(s.message || "") + "</span>" +
          (details ? '<ul class="boost-details">' + details + "</ul>" : "") +
          "</span></li>";
      }).join("");
      var body2 = byId("boost-body");
      if (body2) {
        body2.innerHTML =
          '<p class="' + (res.ok ? "ok-text" : "err-text") + '" style="margin-top:0">' +
          esc(res.ok ? t("boost_done") : t("boost_done_issues")) + "</p>" +
          (stepsHtml ? '<ul class="boost-steps">' + stepsHtml + "</ul>" : "");
      }
      var foot = byId("boost-foot");
      if (foot) {
        foot.innerHTML = '<button class="btn btn-primary" id="boost-close" type="button">' + esc(t("close")) + "</button>";
        byId("boost-close").addEventListener("click", close);
        byId("boost-close").focus();
      }
    });
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
      '<h1 class="page-title">' + esc(t("tweaks_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("tweaks_sub")) + "</p>" +
      '<div id="tweaks-area"><div class="loading-line">' + esc(t("tweaks_loading")) + "</div></div>";

    try {
      state.tweaks = await api("/api/tweaks");
    } catch (e) {
      if (alive(seq) && byId("tweaks-area")) {
        byId("tweaks-area").innerHTML =
          '<div class="card empty-state">' + icon("alert") +
          '<p class="empty-title">' + esc(t("tweaks_unavail_title")) + "</p>" +
          "<p>" + esc(t("tweaks_unavail_body")) + "</p>" +
          '<button class="btn" id="btn-tweaks-retry" type="button">' + esc(t("retry")) + "</button></div>";
        byId("btn-tweaks-retry").addEventListener("click", render);
      }
      return;
    }
    if (!alive(seq)) { return; }

    /* Tier matériel encore inconnu (warm-up en cours) : retente une fois,
       la route /api/status est instantanée (lecture du cache uniquement). */
    if (state.status && !state.status.tier) {
      try {
        var st2 = await api("/api/status");
        if (st2) { state.status = st2; }
      } catch (eTier) { /* bandeau déjà affiché, tier simplement inconnu */ }
      if (!alive(seq)) { return; }
    }

    var tweaks = state.tweaks.tweaks || [];
    var supportedIds = {};
    tweaks.forEach(function (x) { if (x.supported !== false) { supportedIds[x.id] = true; } });

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
        "<span>" + esc(t("notice_not_windows")) + "</span></div>";
    } else if (st && st.is_windows && !st.is_admin) {
      note = '<div class="notice">' + icon("alert") +
        "<span>" + esc(t("notice_not_admin")) + "</span></div>";
    }

    /* Bannière sobre « petite config » : uniquement quand le tier détecté
       par /api/status vaut lowend. Le bouton coche les tweaks lowend sûrs
       ou modérés (jamais les avancés). */
    if (st && st.tier === "lowend") {
      note = '<div class="notice notice-lowend">' + icon("zap") +
        "<span>" + esc(t("lowend_banner")) + "</span>" +
        '<span class="spacer"></span>' +
        '<button class="btn btn-sm" id="btn-lowend-select" type="button">' +
        esc(t("lowend_banner_btn")) + "</button></div>" + note;
    }

    var toolbar =
      '<div class="tweaks-toolbar">' +
      '<button class="btn btn-sm" id="btn-sel-profile" type="button"' +
      (state.profile ? "" : ' disabled title="' + esc(t("sel_profile_hint")) + '"') + ">" + esc(t("sel_profile")) + "</button>" +
      '<button class="btn btn-sm" id="btn-sel-safe" type="button">' + esc(t("sel_safe")) + "</button>" +
      '<button class="btn btn-sm btn-ghost" id="btn-sel-none" type="button">' + esc(t("sel_none")) + "</button>" +
      '<span class="tweaks-count" id="tweak-count"></span>' +
      '<span class="spacer"></span>' +
      '<button class="btn btn-sm" id="btn-restore" type="button">' + icon("shield") + " " + esc(t("restore_point")) + "</button>" +
      '<button class="btn btn-sm btn-danger" id="btn-revert" type="button">' + esc(t("revert_applied")) + "</button>" +
      '<button class="btn btn-sm btn-primary" id="btn-apply" type="button"></button>' +
      "</div>";

    var chips = '<div class="chips">' +
      '<button class="chip' + (state.tweakFilter === "all" ? " active" : "") + '" data-filter="all" type="button">' + esc(t("chip_all")) + "</button>" +
      categories.map(function (c) {
        return '<button class="chip' + (state.tweakFilter === c.id ? " active" : "") + '" data-filter="' +
          esc(c.id) + '" type="button">' + esc(tr(c, "label")) + "</button>";
      }).join("") +
      '<span class="chip-sep" aria-hidden="true"></span>' +
      '<button class="chip' + (state.tweakLowendOnly ? " active" : "") +
      '" id="chip-lowend" type="button" aria-pressed="' + (state.tweakLowendOnly ? "true" : "false") + '">' +
      esc(t("chip_lowend")) + "</button></div>";

    var groups = categories.map(function (c) {
      if (state.tweakFilter !== "all" && state.tweakFilter !== c.id) { return ""; }
      var items = tweaks.filter(function (x) {
        if (x.category !== c.id) { return false; }
        if (state.tweakLowendOnly && !x.lowend) { return false; }
        return true;
      });
      if (!items.length) { return ""; }
      var rows = items.map(tweakRowHtml).join("");
      return '<div class="tweak-group"><h2 class="tweak-group-head">' + esc(tr(c, "label")) +
        ' <span class="muted">· ' + items.length + "</span></h2>" + rows + "</div>";
    }).join("");

    area.innerHTML = note + toolbar + chips + '<div id="tweaks-list">' + (groups ||
      '<p class="muted small">' + esc(t("tweaks_none_cat")) + "</p>") + "</div>";

    /* Liaisons. */
    byId("btn-sel-profile").addEventListener("click", function () {
      if (!state.profile) { return; }
      var rec = state.profile.recommended_tweaks || [];
      state.tweakSelection = new Set(rec.filter(function (id) {
        var x = findTweak(id);
        return x && x.supported !== false;
      }));
      buildTweaksArea();
    });
    byId("btn-sel-safe").addEventListener("click", function () {
      state.tweakSelection = new Set(tweaks.filter(function (x) {
        return x.supported !== false && x.risk === "sur";
      }).map(function (x) { return x.id; }));
      buildTweaksArea();
    });
    byId("btn-sel-none").addEventListener("click", function () {
      state.tweakSelection = new Set();
      buildTweaksArea();
    });
    byId("btn-apply").addEventListener("click", onApplyTweaks);
    byId("btn-revert").addEventListener("click", onRevertTweaks);
    byId("btn-restore").addEventListener("click", onRestorePoint);

    $all(".chip[data-filter]", area).forEach(function (chip) {
      chip.addEventListener("click", function () {
        state.tweakFilter = chip.dataset.filter;
        buildTweaksArea();
      });
    });

    var lowendChip = byId("chip-lowend");
    if (lowendChip) {
      lowendChip.addEventListener("click", function () {
        state.tweakLowendOnly = !state.tweakLowendOnly;
        buildTweaksArea();
      });
    }

    var lowendBtn = byId("btn-lowend-select");
    if (lowendBtn) {
      lowendBtn.addEventListener("click", function () {
        var picked = tweaks.filter(function (x) {
          return x.lowend && x.supported !== false &&
            (x.risk === "sur" || x.risk === "modere");
        }).map(function (x) { return x.id; });
        state.tweakSelection = new Set(picked);
        buildTweaksArea();
        showBanner(tp(picked.length, "lowend_selected_one", "lowend_selected_many"), "ok");
      });
    }

    byId("tweaks-list").addEventListener("change", function (e) {
      var input = e.target;
      if (!input.classList.contains("tweak-check")) { return; }
      var id = input.dataset.id;
      if (input.checked) { state.tweakSelection.add(id); } else { state.tweakSelection.delete(id); }
      updateTweakCounts();
    });

    updateTweakCounts();
  }

  function tweakRowHtml(x) {
    var unsupported = x.supported === false;
    var im = IMPACT_META[x.impact] || IMPACT_META.moyen;
    var rk = RISK_META[x.risk] || RISK_META.sur;
    var status = "";
    if (unsupported) {
      status = '<span class="tweak-status">' + esc(t("tweak_unsupported")) + "</span>";
    } else if (x.applied === true) {
      status = '<span class="tweak-status"><span class="dot dot-green"></span>' + esc(t("tweak_applied")) + "</span>";
    }
    var checked = state.tweakSelection.has(x.id) && !unsupported;
    var res = state.tweakResults[x.id];
    var resHtml = res ?
      '<div class="tweak-result ' + (res.ok ? "ok-text" : "err-text") + '">' + esc(res.message || "") + "</div>" : "";

    return '<label class="tweak-row' + (unsupported ? " unsupported" : "") + '">' +
      '<input type="checkbox" class="tweak-check" data-id="' + esc(x.id) + '"' +
      (checked ? " checked" : "") + (unsupported ? " disabled" : "") + ">" +
      '<span class="tweak-name">' + esc(tr(x, "name")) + "</span>" +
      '<span class="badge ' + im.cls + '">' + esc(t(im.key)) + "</span>" +
      '<span class="badge ' + rk.cls + '">' + esc(t(rk.key)) + "</span>" +
      (x.lowend ? '<span class="badge badge-outline">' + esc(t("tweak_lowend_badge")) + "</span>" : "") +
      '<span class="tweak-desc" title="' + esc(tr(x, "description")) + '">' + esc(tr(x, "description")) + "</span>" +
      status + "</label>" + resHtml;
  }

  function updateTweakCounts() {
    var n = state.tweakSelection.size;
    var count = byId("tweak-count");
    if (count) { count.textContent = tp(n, "selected_one", "selected_many"); }
    var apply = byId("btn-apply");
    if (apply) {
      apply.textContent = tf("apply_n", { n: n });
      apply.disabled = n === 0;
    }
  }

  function onApplyTweaks() {
    var ids = Array.from(state.tweakSelection);
    if (!ids.length) { return; }
    var advanced = ids.map(findTweak).filter(function (x) { return x && x.risk === "avance"; });
    if (advanced.length) {
      openModal({
        title: t("adv_modal_title"),
        bodyHtml: "<p>" + esc(t("adv_modal_body")) + "</p><ul>" +
          advanced.map(function (x) { return "<li>" + esc(tr(x, "name")) + "</li>"; }).join("") + "</ul>",
        confirmLabel: t("adv_confirm"),
        danger: true,
        onConfirm: function () { doApplyTweaks(ids); }
      });
    } else {
      doApplyTweaks(ids);
    }
  }

  async function doApplyTweaks(ids) {
    var btn = byId("btn-apply");
    setBusy(btn, t("applying"));
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
    var failCount = results.length - okCount;
    showBanner(
      tf("apply_done", { ok: tp(okCount, "apply_ok_one", "apply_ok_many") }) +
      (failCount ? tf("apply_fail", { n: failCount }) : "") + ".",
      failCount ? "error" : "ok");
    try { state.tweaks = await api("/api/tweaks"); } catch (e2) { /* état précédent conservé */ }
    if (currentRoute() === "/tweaks") { buildTweaksArea(); }
  }

  function onRevertTweaks() {
    var tweaks = (state.tweaks && state.tweaks.tweaks) || [];
    var ids = tweaks.filter(function (x) { return x.tracked; }).map(function (x) { return x.id; });
    if (!ids.length) {
      showBanner(t("revert_none"), "");
      return;
    }
    openModal({
      title: t("revert_applied"),
      bodyHtml: "<p>" + esc(tp(ids.length, "revert_body_one", "revert_body_many")) + "</p>",
      confirmLabel: t("revert_all"),
      danger: true,
      onConfirm: async function () {
        var btn = byId("btn-revert");
        setBusy(btn, t("reverting"));
        try {
          var res = await api("/api/tweaks/revert", { body: { ids: ids } });
          var results = res.results || [];
          var okCount = results.filter(function (r) { return r.ok; }).length;
          results.forEach(function (r) { state.tweakResults[r.id] = r; });
          showBanner(tf("revert_done", { ok: okCount, total: results.length }), "ok");
          state.tweaks = await api("/api/tweaks");
        } catch (e) { /* bandeau déjà affiché */ }
        if (currentRoute() === "/tweaks") { buildTweaksArea(); }
      }
    });
  }

  async function onRestorePoint() {
    var btn = byId("btn-restore");
    setBusy(btn, t("creating"));
    try {
      var res = await api("/api/restore-point", { method: "POST" });
      showBanner(res.message || (res.ok ? t("restore_created") : t("restore_failed")), res.ok ? "ok" : "error");
    } catch (e) { /* bandeau déjà affiché */ }
    clearBusy(btn);
  }

  /* ------------------------------------------------------------------ */
  /* Page Jeux                                                           */
  /* ------------------------------------------------------------------ */

  async function renderGames(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">' + esc(t("games_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("games_sub")) + "</p>" +
      '<div id="games-area"><div class="loading-line">' + esc(t("games_detecting")) + "</div></div>";

    try {
      var res = await api("/api/games");
      state.games = res.games || [];
    } catch (e) {
      if (alive(seq) && byId("games-area")) {
        byId("games-area").innerHTML = '<p class="muted small">' + esc(t("games_unavailable")) + "</p>";
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
      '<p class="muted small">' + esc(t("games_none")) + "</p>" : "";

    var cards = games.map(function (g) {
      var badge = g.installed ?
        '<span class="badge badge-green">' + esc(t("badge_detected")) + "</span>" :
        '<span class="badge badge-gray">' + esc(t("badge_not_detected")) + "</span>";
      var path = g.installed && g.install_path ?
        '<div class="game-path mono" title="' + esc(g.install_path) + '">' + esc(g.install_path) + "</div>" : "";
      return '<div class="card game-card' + (state.selectedGame === g.id ? " selected" : "") +
        '" data-game="' + esc(g.id) + '" tabindex="0" role="button">' +
        '<span class="card-title">' + esc(g.name) + "</span>" +
        '<span class="game-store">' + esc(storeLabel(g.store)) + "</span>" +
        "<div>" + badge + "</div>" + path + "</div>";
    }).join("");

    area.innerHTML = note + '<div class="grid grid-4" id="games-grid">' + cards + "</div>" +
      '<div id="game-detail-area"></div>' +
      '<div class="group-label">' + esc(t("latency_group")) + "</div>" +
      '<div class="card" id="latency-card"><div id="latency-inner"></div></div>' +
      '<div class="group-label">' + esc(t("sens_group")) + "</div>" +
      '<div class="card" id="sens-card"><div class="loading-line">' + esc(t("loading")) + "</div></div>" +
      '<div class="group-label">' + esc(t("xhair_group")) + "</div>" +
      '<div id="xhair-area"><div class="loading-line">' + esc(t("loading")) + "</div></div>" +
      '<div class="group-label">' + esc(t("vault_group")) + "</div>" +
      '<div class="card" id="vault-card"><div class="loading-line">' + esc(t("loading")) + "</div></div>";

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

    updateLatencyCard(seq);
    loadSensCard(seq);
    loadCrosshairs(seq);
    loadVault(seq);
    if (state.selectedGame) { buildGameDetail(seq); }
  }

  /* ---- Encart « Latence estimée » ---- */

  function msBadge(v) {
    if (v === null || v === undefined) { return '<span class="muted">—</span>'; }
    var cls = v < 30 ? "badge-green" : (v < 70 ? "badge-yellow" : "badge-red");
    return '<span class="badge ' + cls + '">' + esc(dec(v)) + " ms</span>";
  }

  /** Pastille colorée du verdict du test de stabilité. */
  function netstabVerdictBadge(res) {
    var cls = res.verdict === "stable" ? "badge-green" :
      (res.verdict === "instable" ? "badge-red" : "badge-gray");
    return '<span class="badge ' + cls + '">' + esc(tr(res, "verdict_label") || res.verdict || "") + "</span>";
  }

  /** Bloc résultat/état du test de stabilité (sous les résultats de latence). */
  function netstabBlockHtml() {
    if (state.netstabBusy) {
      return '<div class="loading-line">' + esc(t("netstab_running")) + "</div>";
    }
    var res = state.netstab;
    if (!res) { return ""; }
    var html = '<div class="ns-result">' +
      '<div class="ns-head">' + netstabVerdictBadge(res) +
      (res.region && res.region.label ?
        '<span class="muted small">' + esc(tf("netstab_region", { r: tr(res.region, "label") })) +
        (res.region.host ? ' <span class="mono mono-inline">' + esc(res.region.host) + "</span>" : "") + "</span>" : "") +
      "</div>";
    if (res.ok) {
      function nsStat(label, value) {
        return '<div class="ns-stat"><div class="ns-label">' + esc(label) +
          '</div><div class="ns-value mono">' + value + "</div></div>";
      }
      html += '<div class="ns-stats">' +
        nsStat(t("netstab_loss"), esc(dec(res.loss_percent)) + " %") +
        nsStat(t("netstab_jitter"), esc(dec(res.jitter_ms)) + " ms") +
        nsStat(t("th_min"), msBadge(res.ms_min)) +
        nsStat(t("th_avg"), msBadge(res.ms_avg)) +
        nsStat(t("th_max"), msBadge(res.ms_max)) +
        "</div>";
    } else {
      html += '<p class="muted small" style="margin:8px 0 0">' + esc(res.message || "") + "</p>";
    }
    return html + "</div>";
  }

  function latencyInnerHtml() {
    var btns = "";
    if (!state.latencyBusy && !state.netstabBusy) {
      btns = '<div class="lat-actions">' +
        '<button class="btn btn-sm' + (state.latency ? "" : " btn-primary") +
        '" id="btn-latency" type="button">' + icon("activity") + " " + esc(t("latency_measure")) + "</button>" +
        '<button class="btn btn-sm" id="btn-netstab" type="button">' + icon("activity") + " " +
        esc(t("netstab_btn")) + "</button></div>";
    }
    var html = '<div class="lat-head">' +
      '<p class="muted small lat-note">' + esc(t("latency_desc")) + "</p>" + btns + "</div>";
    if (state.latencyBusy) {
      return html + '<div class="loading-line">' + esc(t("latency_measuring")) + "</div>" + netstabBlockHtml();
    }
    if (state.latency && state.latency.length) {
      var rows = state.latency.map(function (r) {
        var label = "<td>" + esc(tr(r, "label")) +
          ' <span class="muted small mono">' + esc(r.host || "") + "</span></td>";
        if (!r.ok) {
          return "<tr>" + label +
            '<td colspan="3" class="muted small">' + esc(r.message || t("latency_failed")) + "</td></tr>";
        }
        return "<tr>" + label +
          '<td class="lat-ms">' + msBadge(r.ms_min) + "</td>" +
          '<td class="lat-ms">' + msBadge(r.ms_avg) + "</td>" +
          '<td class="lat-ms">' + msBadge(r.ms_max) + "</td></tr>";
      }).join("");
      html += '<div class="lat-results"><table class="table"><thead><tr>' +
        "<th>" + esc(t("th_region")) + "</th><th>" + esc(t("th_min")) + "</th><th>" +
        esc(t("th_avg")) + "</th><th>" + esc(t("th_max")) + "</th>" +
        "</tr></thead><tbody>" + rows + "</tbody></table></div>";
    }
    return html + netstabBlockHtml();
  }

  function updateLatencyCard(seq) {
    var inner = byId("latency-inner");
    if (!inner) { return; }
    inner.innerHTML = latencyInnerHtml();
    var btn = byId("btn-latency");
    if (btn) { btn.addEventListener("click", function () { doMeasureLatency(seq); }); }
    var nsBtn = byId("btn-netstab");
    if (nsBtn) { nsBtn.addEventListener("click", function () { doNetStab(seq); }); }
  }

  async function doMeasureLatency(seq) {
    if (state.latencyBusy) { return; }
    state.latencyBusy = true;
    updateLatencyCard(seq);
    try {
      var res = await api("/api/latency", { body: {} });
      state.latency = (res && res.results) || [];
    } catch (e) { /* bandeau déjà affiché */ }
    state.latencyBusy = false;
    updateLatencyCard(seq);
  }

  /** Test de stabilité (~20 s) : pas de select de région sur la page, région par défaut. */
  async function doNetStab(seq) {
    if (state.netstabBusy) { return; }
    state.netstabBusy = true;
    updateLatencyCard(seq);
    try {
      state.netstab = await api("/api/netstab", { body: {} });
    } catch (e) { /* bandeau déjà affiché */ }
    state.netstabBusy = false;
    updateLatencyCard(seq);
  }

  /* ---- Encart « Convertisseur de sensibilité » ---- */

  function sensGameById(id) {
    var list = state.sensGames || [];
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) { return list[i]; } }
    return null;
  }

  async function loadSensCard(seq) {
    if (!state.sensGames) {
      try {
        var res = await api("/api/sens/games");
        state.sensGames = (res && res.games) || [];
      } catch (e) {
        var boxErr = byId("sens-card");
        if (alive(seq) && boxErr) {
          boxErr.innerHTML = '<p class="muted small" style="margin:0">' + esc(t("sens_unavailable")) + "</p>";
        }
        return;
      }
    }
    if (!alive(seq)) { return; }
    buildSensCard(seq);
  }

  function sensResultHtml() {
    var r = state.sensResult;
    if (!r) { return ""; }
    if (!r.ok) {
      return '<p class="err-text small" style="margin:10px 0 0">' +
        esc(r.message || t("sens_failed")) + "</p>";
    }
    var cm = Math.round(r.cm360 * 100) / 100;
    var stats = '<div class="sens-stats">' +
      '<div class="sens-stat"><div class="sens-stat-label">' + esc(t("sens_cm360")) +
      '</div><div class="sens-stat-value mono">' + esc(dec(cm)) + ' <span class="sens-unit">cm</span></div>' +
      '<div class="sens-stat-note">' + esc(t("sens_cm360_note")) + "</div></div>";
    if (r.edpi !== null && r.edpi !== undefined) {
      stats += '<div class="sens-stat"><div class="sens-stat-label">' + esc(t("sens_edpi")) +
        '</div><div class="sens-stat-value mono">' + esc(dec(r.edpi)) + "</div>" +
        '<div class="sens-stat-note">' + esc(t("sens_edpi_note")) + "</div></div>";
    }
    stats += "</div>";
    var rows = (r.conversions || []).map(function (c) {
      var game = sensGameById(c.game_id);
      var note = game ? tr(game, "unit_note") : "";
      return "<tr><td><div>" + esc(c.name) + "</div>" +
        (note ? '<div class="muted small">' + esc(note) + "</div>" : "") + "</td>" +
        '<td class="mono sens-value">' + esc(dec(c.sens)) + "</td></tr>";
    }).join("");
    return stats + '<table class="table"><thead><tr><th>' + esc(t("th_game")) +
      "</th><th>" + esc(t("th_sens_conv")) + "</th></tr></thead><tbody>" + rows + "</tbody></table>";
  }

  function buildSensCard(seq) {
    var card = byId("sens-card");
    if (!card) { return; }
    var games = state.sensGames || [];
    if (!games.length) {
      card.innerHTML = '<p class="muted small" style="margin:0">' + esc(t("sens_unavailable")) + "</p>";
      return;
    }
    if (!state.sensForm.game || !sensGameById(state.sensForm.game)) {
      state.sensForm.game = games[0].id;
    }
    var selected = sensGameById(state.sensForm.game);
    var options = games.map(function (g) {
      return '<option value="' + esc(g.id) + '"' +
        (g.id === state.sensForm.game ? " selected" : "") + ">" + esc(g.name) + "</option>";
    }).join("");

    card.innerHTML =
      '<p class="muted small" style="margin-top:0">' + esc(t("sens_desc")) + "</p>" +
      '<div class="sens-form">' +
      '<label class="sens-field"><span>' + esc(t("sens_game")) + "</span>" +
      '<select class="input" id="sens-game">' + options + "</select></label>" +
      '<label class="sens-field"><span>' + esc(t("sens_sens")) + "</span>" +
      '<input class="input" id="sens-sens" type="text" inputmode="decimal" value="' +
      esc(state.sensForm.sens) + '" placeholder="2.0"></label>' +
      '<label class="sens-field"><span>' + esc(t("sens_dpi")) + "</span>" +
      '<input class="input" id="sens-dpi" type="text" inputmode="numeric" value="' +
      esc(state.sensForm.dpi) + '" placeholder="800"></label>' +
      '<button class="btn btn-primary btn-sm" id="btn-sens-convert" type="button">' +
      esc(t("sens_convert")) + "</button>" +
      "</div>" +
      '<p class="muted small sens-unit-note" id="sens-unit-note">' +
      esc(selected ? tr(selected, "unit_note") : "") + "</p>" +
      (state.sensError ? '<p class="err-text small" id="sens-error">' + esc(state.sensError) + "</p>" : "") +
      '<div id="sens-result">' + sensResultHtml() + "</div>";

    byId("sens-game").addEventListener("change", function (e) {
      state.sensForm.game = e.target.value;
      var g = sensGameById(state.sensForm.game);
      var noteEl = byId("sens-unit-note");
      if (noteEl) { noteEl.textContent = g ? tr(g, "unit_note") : ""; }
    });
    byId("sens-sens").addEventListener("input", function (e) { state.sensForm.sens = e.target.value; });
    byId("sens-dpi").addEventListener("input", function (e) { state.sensForm.dpi = e.target.value; });
    byId("btn-sens-convert").addEventListener("click", function () { doSensConvert(seq); });
    byId("sens-sens").addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); doSensConvert(seq); }
    });
    byId("sens-dpi").addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); doSensConvert(seq); }
    });
  }

  async function doSensConvert(seq) {
    /* Validation côté client : nombre > 0, DPI entier 100..26000. */
    var sensRaw = String(state.sensForm.sens || "").trim().replace(",", ".");
    var sens = Number(sensRaw);
    if (!sensRaw || !isFinite(sens) || sens <= 0) {
      state.sensError = t("sens_err_sens");
      state.sensResult = null;
      buildSensCard(seq);
      return;
    }
    var dpiRaw = String(state.sensForm.dpi || "").trim();
    var dpi = Number(dpiRaw);
    if (!dpiRaw || !isFinite(dpi) || Math.floor(dpi) !== dpi || dpi < 100 || dpi > 26000) {
      state.sensError = t("sens_err_dpi");
      state.sensResult = null;
      buildSensCard(seq);
      return;
    }
    state.sensError = null;
    var btn = byId("btn-sens-convert");
    setBusy(btn, t("sens_converting"));
    try {
      state.sensResult = await api("/api/sens/convert",
        { body: { game: state.sensForm.game, sens: sens, dpi: dpi } });
    } catch (e) {
      state.sensResult = { ok: false, message: t("sens_failed") };
    }
    clearBusy(btn);
    if (!alive(seq)) { return; }
    buildSensCard(seq);
  }

  /* ---- Encart « Viseurs CS2 » ---- */

  /** Aperçu SVG d'un viseur dessiné depuis ses paramètres, sur damier neutre. */
  function crosshairSvg(entryId, p) {
    p = p || {};
    var K_LEN = 5;      /* longueur : size × 5 px */
    var K_TH = 3;       /* épaisseur : thickness × 3 px */
    var cx = 32, cy = 32;
    var len = Math.max(1, (Number(p.size) || 0) * K_LEN);
    var th = Math.max(1.5, (Number(p.thickness) || 0.5) * K_TH);
    /* CS2 : l'écart visuel vaut environ (4 + gap) ; jamais négatif à l'écran. */
    var gap = Number(p.gap) || 0;
    var off = Math.max(0, (4 + gap)) * 1.5;
    var color = /^#[0-9a-fA-F]{6}$/.test(String(p.color || "")) ? p.color : "#00ff00";
    var stroke = p.outline ? ' stroke="#000000" stroke-width="1"' : "";

    function rect(x, y, w, h) {
      return '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) +
        '" height="' + h.toFixed(1) + '" fill="' + color + '"' + stroke + "/>";
    }
    var parts =
      rect(cx - off - len, cy - th / 2, len, th) +   /* gauche */
      rect(cx + off, cy - th / 2, len, th) +         /* droite */
      rect(cx - th / 2, cy - off - len, th, len) +   /* haut */
      rect(cx - th / 2, cy + off, th, len);          /* bas */
    if (p.dot) { parts += rect(cx - th / 2, cy - th / 2, th, th); }

    var pid = "chk-" + String(entryId).replace(/[^a-z0-9_-]/gi, "");
    return '<svg class="xhair-svg" viewBox="0 0 64 64" aria-hidden="true">' +
      '<defs><pattern id="' + pid + '" width="16" height="16" patternUnits="userSpaceOnUse">' +
      '<rect width="16" height="16" fill="#75787c"/>' +
      '<rect width="8" height="8" fill="#6a6d71"/><rect x="8" y="8" width="8" height="8" fill="#6a6d71"/>' +
      "</pattern></defs>" +
      '<rect width="64" height="64" rx="6" fill="url(#' + pid + ')"/>' + parts + "</svg>";
  }

  async function loadCrosshairs(seq) {
    if (!state.crosshairs) {
      try {
        var res = await api("/api/crosshairs");
        state.crosshairs = (res && res.crosshairs) || [];
      } catch (e) {
        var areaErr = byId("xhair-area");
        if (alive(seq) && areaErr) {
          areaErr.innerHTML = '<p class="muted small">' + esc(t("xhair_unavailable")) + "</p>";
        }
        return;
      }
    }
    if (!alive(seq)) { return; }
    buildCrosshairArea(seq);
  }

  function buildCrosshairArea(seq) {
    var area = byId("xhair-area");
    if (!area) { return; }
    var list = state.crosshairs || [];
    if (!list.length) {
      area.innerHTML = '<p class="muted small">' + esc(t("xhair_unavailable")) + "</p>";
      return;
    }
    var cards = list.map(function (c, i) {
      var codeBlock = c.code ?
        '<div class="mono-block xhair-code"><pre>' + esc(c.code) + "</pre></div>" : "";
      return '<div class="card xhair-card">' +
        '<div class="xhair-head">' +
        '<div class="xhair-preview">' + crosshairSvg(c.id || i, c.params) + "</div>" +
        '<div class="xhair-meta">' +
        '<div class="card-title">' + esc(tf("xhair_inspired", { p: c.player || c.id })) + "</div>" +
        '<div class="muted small">' + esc(tr(c, "style")) + "</div>" +
        "</div></div>" +
        codeBlock +
        '<div class="xhair-actions">' +
        (c.code ? '<button class="btn btn-sm" data-copy-code="' + i + '" type="button">' +
          icon("copy") + " " + esc(t("xhair_copy_code")) + "</button>" : "") +
        (c.console ? '<button class="btn btn-sm" data-copy-console="' + i + '" type="button">' +
          esc(t("xhair_copy_console")) + "</button>" : "") +
        "</div></div>";
    }).join("");
    area.innerHTML = '<div class="grid xhair-grid">' + cards + "</div>" +
      '<p class="muted small" style="margin:10px 0 0">' + esc(t("xhair_howto")) + "</p>";

    $all("[data-copy-code]", area).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var entry = list[Number(btn.dataset.copyCode)];
        copyText(entry && entry.code ? entry.code : "", btn);
      });
    });
    $all("[data-copy-console]", area).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var entry = list[Number(btn.dataset.copyConsole)];
        copyText(entry && entry.console ? entry.console : "", btn);
      });
    });
  }

  /* ---- Encart « Coffre de configurations » ---- */

  async function loadVault(seq, refresh) {
    if (!state.vault || refresh) {
      try {
        state.vault = await api("/api/vault");
      } catch (e) {
        var cardErr = byId("vault-card");
        if (alive(seq) && cardErr) {
          cardErr.innerHTML = '<p class="muted small" style="margin:0">' + esc(t("vault_unavailable")) + "</p>";
        }
        return;
      }
      /* Ne garde cochées que des cibles encore détectées. */
      var found = {};
      ((state.vault && state.vault.targets) || []).forEach(function (x) {
        if (x.found) { found[x.game_id] = true; }
      });
      Array.from(state.vaultSelection).forEach(function (id) {
        if (!found[id]) { state.vaultSelection.delete(id); }
      });
    }
    if (!alive(seq)) { return; }
    buildVaultCard(seq);
  }

  function buildVaultCard(seq) {
    var card = byId("vault-card");
    if (!card) { return; }
    var data = state.vault || {};
    var targets = data.targets || [];
    var backups = data.backups || [];
    var anyFound = targets.some(function (x) { return x.found; });

    var targetRows = targets.map(function (x) {
      var badge = x.found ?
        '<span class="badge badge-green">' + esc(t("badge_detected")) + "</span>" :
        '<span class="badge badge-gray">' + esc(t("badge_not_detected")) + "</span>";
      return "<tr>" +
        '<td><input type="checkbox" class="vault-check" data-id="' + esc(x.game_id) + '"' +
        (state.vaultSelection.has(x.game_id) ? " checked" : "") + (x.found ? "" : " disabled") + "></td>" +
        "<td>" + esc(x.name) + "</td>" +
        "<td>" + badge + "</td>" +
        '<td class="mono">' + (x.found ? esc(fmtMb(x.size_mb)) : "—") + "</td></tr>";
    }).join("");

    var html =
      '<p class="muted small" style="margin-top:0">' + esc(t("vault_desc")) + "</p>" +
      '<table class="table"><thead><tr><th></th><th>' + esc(t("th_game")) + "</th><th>" +
      esc(t("th_state")) + "</th><th>" + esc(t("th_size")) + "</th></tr></thead><tbody>" +
      targetRows + "</tbody></table>" +
      '<div class="vault-foot">' +
      (anyFound ? "" : '<span class="muted small">' + esc(t("vault_none_found")) + "</span>") +
      '<span class="spacer"></span>' +
      '<button class="btn btn-primary btn-sm" id="btn-vault-backup" type="button"' +
      (anyFound ? "" : " disabled") + ">" + esc(t("vault_backup_now")) + "</button></div>" +
      '<div class="group-label vault-sub">' + esc(t("vault_backups_title")) + "</div>";

    if (!backups.length) {
      html += '<p class="muted small" style="margin:0">' + esc(t("vault_no_backups")) + "</p>";
    } else {
      var backupRows = backups.map(function (b, i) {
        return "<tr>" +
          '<td class="mono">' + esc(String(b.ts || "").replace("T", " ")) + "</td>" +
          '<td class="mono">' + esc(fmtMb(b.size_mb)) + "</td>" +
          "<td>" + (b.games || []).map(function (g) {
            return '<span class="badge badge-gray">' + esc(g) + "</span>";
          }).join(" ") + "</td>" +
          '<td class="vault-actions">' +
          '<button class="btn btn-sm" data-vault-restore="' + i + '" type="button">' +
          esc(t("vault_restore")) + "</button>" +
          '<button class="btn btn-sm btn-danger" data-vault-delete="' + i + '" type="button">' +
          esc(t("del")) + "</button></td></tr>";
      }).join("");
      html += '<table class="table"><thead><tr><th>' + esc(t("th_date")) + "</th><th>" +
        esc(t("th_size")) + "</th><th>" + esc(t("th_games")) + "</th><th></th></tr></thead><tbody>" +
        backupRows + "</tbody></table>";
    }
    card.innerHTML = html;

    $all(".vault-check", card).forEach(function (cb) {
      cb.addEventListener("change", function () {
        if (cb.checked) { state.vaultSelection.add(cb.dataset.id); }
        else { state.vaultSelection.delete(cb.dataset.id); }
      });
    });

    var backupBtn = byId("btn-vault-backup");
    if (backupBtn) {
      backupBtn.addEventListener("click", async function () {
        var foundIds = targets.filter(function (x) { return x.found; })
          .map(function (x) { return x.game_id; });
        var checked = foundIds.filter(function (id) { return state.vaultSelection.has(id); });
        /* Rien de coché : tout sauvegarder (ids absents). */
        var body = checked.length ? { ids: checked } : {};
        setBusy(backupBtn, t("vault_backing_up"));
        try {
          var res = await api("/api/vault/backup", { body: body });
          showBanner(res.message || "", res.ok ? "ok" : "error");
          if (res.ok) { loadVault(seq, true); return; }
        } catch (e) { /* bandeau déjà affiché */ }
        clearBusy(backupBtn);
      });
    }

    $all("[data-vault-restore]", card).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var b = backups[Number(btn.dataset.vaultRestore)];
        if (!b) { return; }
        openModal({
          title: t("vault_restore_title"),
          bodyHtml: "<p>" + esc(tf("vault_restore_body", { id: b.id })) + "</p>",
          confirmLabel: t("vault_restore"),
          onConfirm: async function () {
            setBusy(btn, t("vault_restoring"));
            try {
              var res = await api("/api/vault/restore", { body: { id: b.id } });
              showBanner(res.message || "", res.ok ? "ok" : "error");
              if (res.ok) { loadVault(seq, true); return; }
            } catch (e) { /* bandeau déjà affiché */ }
            clearBusy(btn);
          }
        });
      });
    });

    $all("[data-vault-delete]", card).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var b = backups[Number(btn.dataset.vaultDelete)];
        if (!b) { return; }
        openModal({
          title: t("vault_delete_title"),
          bodyHtml: "<p>" + esc(tf("vault_delete_body", { id: b.id })) + "</p>",
          confirmLabel: t("del"),
          danger: true,
          onConfirm: async function () {
            setBusy(btn, t("vault_deleting"));
            try {
              var res = await api("/api/vault/delete", { body: { id: b.id } });
              showBanner(res.message || "", res.ok ? "ok" : "error");
              if (res.ok) { loadVault(seq, true); return; }
            } catch (e) { /* bandeau déjà affiché */ }
            clearBusy(btn);
          }
        });
      });
    });
  }

  function buildGameDetail(seq) {
    var area = byId("game-detail-area");
    if (!area) { return; }
    var game = null;
    (state.games || []).forEach(function (g) { if (g.id === state.selectedGame) { game = g; } });
    if (!game) { area.innerHTML = ""; return; }

    var html = '<div class="card game-detail">' +
      '<div class="game-detail-head"><div><h2>' + esc(game.name) + "</h2>" +
      '<span class="muted small">' + esc(storeLabel(game.store)) +
      (game.installed && game.install_path ? ' · <span class="mono mono-inline">' + esc(game.install_path) + "</span>" : "") +
      "</span></div>" +
      '<button class="btn btn-ghost btn-sm" id="btn-game-close" type="button" aria-label="' + esc(t("close")) + '">' + icon("x") + "</button></div>";

    if (game.launch_options) {
      html += '<div class="group-label">' + esc(t("launch_options")) + "</div>" +
        '<div class="mono-block"><pre>' + esc(game.launch_options) + "</pre>" +
        '<button class="btn btn-sm copy-btn" type="button">' + icon("copy") + " " + esc(t("copy")) + "</button></div>";
      if (game.launch_options_note) {
        html += '<p class="muted small">' + esc(tr(game, "launch_options_note")) + "</p>";
      }
    }

    var opts = game.optimizations || [];
    if (opts.length) {
      html += '<div class="group-label">' + esc(t("recommended_settings")) + '</div><ul class="opt-list">' +
        opts.map(function (o) {
          return '<li><div class="opt-title">' + esc(tr(o, "title")) + "</div>" +
            '<div class="opt-detail">' + esc(tr(o, "detail")) + "</div></li>";
        }).join("") + "</ul>";
    }

    if (game.id === "cs2") {
      html += '<div id="cs2-panel"><div class="loading-line">' + esc(t("cs2_loading")) + "</div></div>";
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

  /* ---- Panneau CS2 : tiers matériels (« Pour ta machine ») ---- */

  /** Tiers reconnus, alignés sur TIERS côté serveur (cs2.py). */
  var CS2_TIERS = ["lowend", "midrange", "highend"];

  function cs2TierLabel(tier) {
    return CS2_TIERS.indexOf(tier) >= 0 ? t("tier_" + tier) : (tier || "");
  }

  /** Réglages vidéo applicables ET différents de la valeur actuelle du joueur. */
  function cs2VideoDiffs(info) {
    var recs = (info && info.video_recommendations) || [];
    return recs.filter(function (r) {
      return r.applicable && r.current !== null && r.current !== undefined &&
        String(r.current) !== String(r.recommended);
    });
  }

  async function loadCs2Panel(seq, refresh) {
    if (!state.cs2 || refresh) {
      var box0 = byId("cs2-panel");
      if (box0) { box0.innerHTML = '<div class="loading-line">' + esc(t("cs2_loading")) + "</div>"; }
      try {
        var q = state.cs2Tier ? "?tier=" + encodeURIComponent(state.cs2Tier) : "";
        state.cs2 = await api("/api/games/cs2" + q);
      } catch (e) {
        var boxErr = byId("cs2-panel");
        if (boxErr) { boxErr.innerHTML = '<p class="muted small">' + esc(t("cs2_unavailable")) + "</p>"; }
        return;
      }
      if (!state.cs2Tier && state.cs2 && CS2_TIERS.indexOf(state.cs2.selected_tier) >= 0) {
        state.cs2Tier = state.cs2.selected_tier;
      }
    }
    if (!alive(seq)) { return; }
    var box = byId("cs2-panel");
    if (!box) { return; }
    box.innerHTML = cs2PanelHtml(state.cs2);
    bindCs2Panel(seq);
  }

  /** Résultat persistant du dernier POST /api/games/cs2/video. */
  function cs2VideoResultHtml() {
    var res = state.cs2VideoResult;
    if (!res) { return ""; }
    var html = '<span class="' + (res.ok ? "ok-text" : "err-text") + '">' + esc(res.message || "") + "</span>";
    var changed = res.changed || [];
    if (changed.length) {
      html += '<div class="muted small" style="margin-top:4px">' + esc(t("cs2_res_changed")) + " : " +
        changed.map(function (c) {
          return '<span class="mono mono-inline">' + esc(c.key) + " " +
            esc(c.old === null || c.old === undefined ? "—" : c.old) + " → " + esc(c.new) + "</span>";
        }).join(" ") + "</div>";
    }
    var skipped = res.skipped || [];
    if (res.ok && skipped.length) {
      html += '<div class="muted small" style="margin-top:2px">' + esc(t("cs2_res_skipped")) + " : " +
        skipped.length + "</div>";
    }
    return html;
  }

  function cs2PanelHtml(info) {
    var profiles = (info && info.userdata_profiles) || [];
    var tierInfo = (info && info.tier) || {};
    var selTier = (info && CS2_TIERS.indexOf(info.selected_tier) >= 0) ? info.selected_tier : "midrange";
    var html = '<div class="group-label">' + esc(t("cs2_config")) + "</div>";

    if (!profiles.length) {
      html += '<p class="muted small">' + esc(t("cs2_no_profiles")) + "</p>";
    } else {
      html += profiles.map(function (p) {
        return '<div class="cs2-profile-row">' +
          "<span>" + esc(t("cs2_profile")) + ' <span class="mono mono-inline">' + esc(p.user_id) + "</span></span>" +
          (p.has_autoexec ?
            '<span class="badge badge-green">' + esc(t("cs2_autoexec_yes")) + "</span>" :
            '<span class="badge badge-gray">' + esc(t("cs2_autoexec_no")) + "</span>") +
          '<span class="muted small mono clean-path" title="' + esc(p.cfg_dir) + '">' + esc(p.cfg_dir) + "</span>" +
          "</div>";
      }).join("");
    }

    /* ---- « Pour ta machine » : tier détecté, sélecteur, conseils ---- */
    var reasons = (LANG === "en" && Array.isArray(tierInfo.reasons_en) && tierInfo.reasons_en.length) ?
      tierInfo.reasons_en : (tierInfo.reasons || []);
    var tierSeg = '<div class="seg" id="cs2-tier-seg">' + CS2_TIERS.map(function (tierId) {
      return '<button type="button" data-tier="' + tierId + '"' +
        (tierId === selTier ? ' class="active"' : "") + ">" + esc(cs2TierLabel(tierId)) + "</button>";
    }).join("") + "</div>";

    html += '<div class="group-label">' + esc(t("cs2_machine_group")) + "</div>" +
      '<div class="cs2-machine">' +
      '<div class="cs2-tier-head">' +
      '<div><div class="muted small">' + esc(t("cs2_tier_detected")) + "</div>" +
      '<div class="cs2-tier-label">' + esc(tr(tierInfo, "label") || cs2TierLabel(tierInfo.tier)) + "</div></div>" +
      '<div class="cs2-tier-select"><div class="muted small">' + esc(t("cs2_tier_select")) + "</div>" +
      tierSeg + "</div></div>" +
      (reasons.length ?
        '<details class="fold cs2-reasons"><summary>' + esc(t("cs2_tier_reasons")) + "</summary>" +
        '<div class="fold-body"><ul class="muted small">' + reasons.map(function (r) {
          return "<li>" + esc(r) + "</li>";
        }).join("") + "</ul></div></details>" : "");

    var advice = (info && info.advice) || [];
    if (advice.length) {
      var kindMeta = {
        reco: { key: "advice_kind_reco", cls: "badge-blue" },
        opinion: { key: "advice_kind_opinion", cls: "badge-yellow" },
        info: { key: "advice_kind_info", cls: "badge-gray" }
      };
      html += '<ul class="cs2-advice">' + advice.map(function (a) {
        var meta = kindMeta[a.kind] || kindMeta.info;
        return '<li><div class="advice-title"><span class="badge ' + meta.cls + '">' +
          esc(t(meta.key)) + "</span> " + esc(tr(a, "title")) + "</div>" +
          '<div class="advice-detail">' + esc(tr(a, "detail")) + "</div></li>";
      }).join("") + "</ul>";
    }
    html += "</div>";

    /* ---- Réglages vidéo : comparaison actuel → recommandé + application ---- */
    var recs = (info && info.video_recommendations) || [];
    var diffs = cs2VideoDiffs(info);
    if (recs.length) {
      html += '<div class="group-label">' + esc(t("cs2_video_group")) +
        ' <span class="badge badge-blue">' + esc(cs2TierLabel(selTier)) + "</span></div>" +
        '<p class="muted small" style="margin-top:0">' +
        esc(info.video_settings ? t("cs2_video_read") : t("cs2_video_not_read")) + "</p>" +
        '<table class="table cs2-video-table"><thead><tr><th>' + esc(t("th_param")) + "</th><th>" +
        esc(t("th_current")) + "</th><th>" + esc(t("th_recommended")) + "</th><th>" +
        esc(t("th_note")) + "</th></tr></thead><tbody>" +
        recs.map(function (r) {
          var current = r.current === null || r.current === undefined ? "—" : String(r.current);
          var reco = r.recommended === null || r.recommended === undefined ? "—" : String(r.recommended);
          var differs = r.applicable && current !== "—" && reco !== "—" && current !== reco;
          var same = r.applicable && current !== "—" && current === reco;
          var recoCell;
          if (differs) {
            recoCell = '<span class="val-arrow">→</span><span class="mono val-diff">' + esc(reco) + "</span>";
          } else if (same) {
            recoCell = '<span class="mono">' + esc(reco) + '</span> <span class="badge badge-green">' +
              esc(t("cs2_val_same")) + "</span>";
          } else {
            recoCell = '<span class="mono">' + esc(reco) + "</span>";
          }
          var noteBits = [];
          var note = tr(r, "note");
          if (note) { noteBits.push(esc(note)); }
          /* skip_reason masqué sur les réglages protégés : la note le dit déjà. */
          if (!r.applicable && r.skip_reason && !r.protected) {
            noteBits.push('<span class="muted">' + esc(r.skip_reason) + "</span>");
          }
          var menu = tr(r, "menu_path");
          return "<tr><td><div>" + esc(tr(r, "label")) + "</div>" +
            (menu ? '<span class="cs2-menu-path">' + esc(menu) + "</span>" : "") + "</td>" +
            '<td class="mono">' + esc(current) + "</td>" +
            '<td class="cs2-reco-cell">' + recoCell + "</td>" +
            '<td class="muted small">' + noteBits.join("<br>") + "</td></tr>";
        }).join("") + "</tbody></table>";

      var applyDisabled = !info.video_settings || !profiles.length || !diffs.length;
      html += '<div class="quick-actions" style="margin-top:12px">' +
        '<button class="btn btn-primary btn-sm" id="btn-cs2-video-apply" type="button"' +
        (applyDisabled ? " disabled" : "") + ">" + esc(t("cs2_apply_video")) + "</button>" +
        (info.video_settings && profiles.length && !diffs.length ?
          '<span class="muted small">' + esc(t("cs2_apply_none")) + "</span>" : "") +
        "</div>" +
        '<div class="small" id="cs2-video-result" style="margin-top:8px">' + cs2VideoResultHtml() + "</div>";
    }

    /* ---- Autoexec par tier : sélecteur de profil, écriture, aperçu ---- */
    if (info && info.autoexec_recommended) {
      html += '<div class="group-label">' + esc(t("cs2_autoexec_group")) +
        ' <span class="badge badge-blue">' + esc(cs2TierLabel(selTier)) + "</span></div>";
      if (profiles.length) {
        var select = "";
        if (profiles.length > 1) {
          select = '<select class="input" id="cs2-user">' + profiles.map(function (p) {
            return '<option value="' + esc(p.user_id) + '">' + esc(t("cs2_profile")) + " " + esc(p.user_id) + "</option>";
          }).join("") + "</select> ";
        }
        html += '<div class="quick-actions">' + select +
          '<button class="btn btn-primary btn-sm" id="btn-cs2-write" type="button">' + esc(t("cs2_write")) + "</button></div>" +
          '<div class="small" id="cs2-write-result" style="margin-top:8px"></div>';
      }
      html += '<details class="fold"><summary>' + esc(t("cs2_preview")) + "</summary>" +
        '<div class="fold-body"><div class="mono-block"><pre>' + esc(info.autoexec_recommended) + "</pre>" +
        '<button class="btn btn-sm copy-btn" type="button">' + icon("copy") + " " + esc(t("copy")) + "</button></div></div></details>";
    }

    /* ---- Options de lancement du tier sélectionné ---- */
    var launch = (info && info.launch_options) || null;
    if (launch && launch.options) {
      html += '<div class="group-label">' + esc(t("cs2_launch_group")) +
        ' <span class="badge badge-blue">' + esc(cs2TierLabel(launch.tier || selTier)) + "</span></div>" +
        '<div class="mono-block"><pre>' + esc(launch.options) + "</pre>" +
        '<button class="btn btn-sm copy-btn" type="button">' + icon("copy") + " " + esc(t("copy")) + "</button></div>" +
        (tr(launch, "note") ? '<p class="muted small">' + esc(tr(launch, "note")) + "</p>" : "");
    }
    return html;
  }

  function bindCs2Panel(seq) {
    var panel = byId("cs2-panel");
    if (!panel) { return; }
    bindCopyButtons(panel);
    var info = state.cs2 || {};
    var selTier = CS2_TIERS.indexOf(info.selected_tier) >= 0 ? info.selected_tier : "midrange";

    /* Sélecteur de tier : recharge le panneau résolu pour ce tier. */
    $all("#cs2-tier-seg button", panel).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tier = btn.dataset.tier;
        if (!tier || tier === state.cs2Tier) { return; }
        state.cs2Tier = tier;
        state.cs2VideoResult = null;
        loadCs2Panel(seq, true);
      });
    });

    /* Application sécurisée du plan vidéo (modale de confirmation). */
    var applyBtn = byId("btn-cs2-video-apply");
    if (applyBtn) {
      applyBtn.addEventListener("click", function () {
        var diffs = cs2VideoDiffs(info);
        if (!diffs.length) { return; }
        var listHtml = "<ul>" + diffs.map(function (r) {
          return "<li>" + esc(tr(r, "label")) + ' : <span class="mono mono-inline">' +
            esc(r.current) + " → " + esc(r.recommended) + "</span></li>";
        }).join("") + "</ul>";
        openModal({
          title: t("cs2_apply_video"),
          bodyHtml: "<p>" +
            esc(tf(diffs.length > 1 ? "cs2_apply_count_many" : "cs2_apply_count_one",
              { n: diffs.length, t: cs2TierLabel(selTier) })) + "</p>" + listHtml +
            "<p>" + esc(t("cs2_apply_video_body")) + "</p>",
          confirmLabel: t("cs2_apply_video"),
          onConfirm: async function () {
            var sel = byId("cs2-user");
            var userId = sel ? sel.value : null;
            var btn2 = byId("btn-cs2-video-apply");
            setBusy(btn2, t("applying"));
            var res;
            try {
              res = await api("/api/games/cs2/video", { body: { user_id: userId, tier: selTier } });
            } catch (e) {
              clearBusy(btn2);
              return;
            }
            state.cs2VideoResult = res;
            /* Refus serveur (CS2 lancé, fichier absent…) : le message exact
               du serveur est affiché, en bandeau et sous le bouton. */
            showBanner(res.message || "", res.ok ? "ok" : "error");
            if (!alive(seq)) { return; }
            if (res.ok) {
              loadCs2Panel(seq, true);   /* relit le fichier : comparaison à jour */
              return;
            }
            clearBusy(btn2);
            var out = byId("cs2-video-result");
            if (out) { out.innerHTML = cs2VideoResultHtml(); }
          }
        });
      });
    }

    /* Écriture de l'autoexec du tier sélectionné. */
    var writeBtn = byId("btn-cs2-write");
    if (writeBtn) {
      writeBtn.addEventListener("click", async function () {
        var sel = byId("cs2-user");
        var userId = sel ? sel.value : null;
        setBusy(writeBtn, t("writing"));
        try {
          var res = await api("/api/games/cs2/autoexec", { body: { user_id: userId, tier: selTier } });
          if (res.ok) {
            showBanner(res.message || "", "ok");
            loadCs2Panel(seq, true);
            return;
          }
          var out = byId("cs2-write-result");
          if (out) {
            out.innerHTML = '<span class="err-text">' + esc(res.message || "") + "</span>";
          }
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
      '<h1 class="page-title">' + esc(t("clean_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("clean_sub")) + "</p>" +
      '<div id="clean-area"></div>' +
      '<div class="group-label">' + esc(t("debloat_group")) + "</div>" +
      '<div id="debloat-area"><div class="loading-line">' + esc(t("loading")) + "</div></div>";
    buildCleanArea(seq);
    loadDebloat(seq);
    if (state.autoScan) {
      state.autoScan = false;
      doCleanScan(seq);
    }
  }

  /** Charge puis affiche les applications préinstallées supprimables. */
  async function loadDebloat(seq) {
    try {
      var res = await api("/api/debloat");
      state.debloat = (res && res.apps) || [];
    } catch (e) {
      state.debloat = [];
    }
    if (!alive(seq)) { return; }
    buildDebloatArea(seq);
  }

  function buildDebloatArea(seq) {
    var area = byId("debloat-area");
    if (!area) { return; }
    var apps = state.debloat || [];
    if (!apps.length) {
      area.innerHTML = "";
      return;
    }
    var rows = apps.map(function (a) {
      var badge = a.installed === true ?
        '<span class="badge badge-green">' + esc(t("debloat_installed")) + "</span>" :
        a.installed === false ?
          '<span class="badge">' + esc(t("debloat_absent")) + "</span>" :
          '<span class="badge badge-yellow">' + esc(t("debloat_unknown")) + "</span>";
      var disabled = a.installed === false ? " disabled" : "";
      return '<div class="settings-row">' +
        '<div class="set-info"><div class="set-name">' +
        '<label class="check-item"><input type="checkbox" data-debloat="' + esc(a.id) + '"' + disabled + "> " +
        esc(a.name) + "</label> " + badge + "</div>" +
        '<div class="set-status">' + esc(tr(a, "description")) + "</div></div>" +
        "</div>";
    }).join("");
    area.innerHTML = '<div class="card">' +
      '<p class="muted small" style="margin-top:0">' + esc(t("debloat_note")) + "</p>" + rows +
      '<div style="margin-top:12px"><button class="btn btn-danger" id="btn-debloat" type="button" disabled>' +
      esc(tf("debloat_remove", { n: 0 })) + "</button></div></div>";

    function selected() {
      return $all("[data-debloat]:checked", area).map(function (c) { return c.dataset.debloat; });
    }
    function refreshBtn() {
      var btn = byId("btn-debloat");
      var n = selected().length;
      btn.disabled = n === 0;
      btn.textContent = tf("debloat_remove", { n: n });
    }
    $all("[data-debloat]", area).forEach(function (c) { c.addEventListener("change", refreshBtn); });
    byId("btn-debloat").addEventListener("click", async function () {
      var ids = selected();
      if (!ids.length) { return; }
      var btn = byId("btn-debloat");
      setBusy(btn, t("debloat_removing"));
      try {
        var res = await api("/api/debloat/remove", { body: { ids: ids } });
        var results = (res && res.results) || [];
        var okCount = results.filter(function (r) { return r.ok; }).length;
        var firstErr = results.find(function (r) { return !r.ok; });
        if (okCount) { showBanner(tf("debloat_done", { n: okCount }), "ok"); }
        if (firstErr) { showBanner(firstErr.message, "error"); }
        loadDebloat(seq);
        return;
      } catch (e) { /* bandeau déjà affiché */ }
      clearBusy(btn);
    });
  }

  function buildCleanArea(seq) {
    var area = byId("clean-area");
    if (!area) { return; }

    if (state.cleanScanning) {
      area.innerHTML = '<div class="loading-line">' + esc(t("scanning")) + "</div>";
      return;
    }

    if (state.cleanTargets === null) {
      area.innerHTML = '<div class="card empty-state">' + icon("search") +
        '<p class="empty-title">' + esc(t("clean_none_title")) + "</p>" +
        "<p>" + esc(t("clean_none_body")) + "</p>" +
        '<button class="btn btn-primary" id="btn-scan" type="button">' + esc(t("scan")) + "</button></div>";
      byId("btn-scan").addEventListener("click", function () { doCleanScan(seq); });
      return;
    }

    var targets = state.cleanTargets;
    if (!targets.length) {
      area.innerHTML = '<div class="card empty-state">' + icon("check") +
        '<p class="empty-title">' + esc(t("clean_empty_title")) + "</p>" +
        "<p>" + esc(t("clean_empty_body")) + "</p>" +
        '<button class="btn" id="btn-rescan" type="button">' + icon("refresh") + " " + esc(t("rescan")) + "</button></div>";
      byId("btn-rescan").addEventListener("click", function () { doCleanScan(seq); });
      return;
    }

    var allChecked = targets.every(function (x) { return state.cleanSelection.has(x.id); });
    var rows = targets.map(function (x) {
      var res = state.cleanResults[x.id];
      var resHtml = res ?
        '<span class="' + (res.ok ? "ok-text" : "err-text") + ' small">' +
        esc(res.ok ? tf("freed", { x: fmtMb(res.freed_mb) }) : (res.message || t("failed"))) + "</span>" : "";
      return "<tr>" +
        '<td><input type="checkbox" class="clean-check" data-id="' + esc(x.id) + '"' +
        (state.cleanSelection.has(x.id) ? " checked" : "") + "></td>" +
        "<td>" + esc(x.name) + "</td>" +
        '<td><span class="mono mono-inline clean-path" title="' + esc(x.path) + '">' + esc(x.path) + "</span></td>" +
        '<td class="mono">' + esc(x.files) + "</td>" +
        '<td class="mono">' + esc(fmtMb(x.size_mb)) + "</td>" +
        "<td>" + resHtml + "</td></tr>";
    }).join("");

    area.innerHTML =
      '<table class="table"><thead><tr>' +
      '<th><input type="checkbox" id="clean-all"' + (allChecked ? " checked" : "") + "></th>" +
      "<th>" + esc(t("th_target")) + "</th><th>" + esc(t("th_path")) + "</th><th>" + esc(t("th_files")) +
      "</th><th>" + esc(t("th_size")) + "</th><th>" + esc(t("th_result")) + "</th>" +
      "</tr></thead><tbody>" + rows + "</tbody></table>" +
      '<div class="clean-foot">' +
      '<span class="muted" id="clean-total"></span>' +
      '<span class="spacer"></span>' +
      '<button class="btn" id="btn-rescan" type="button">' + icon("refresh") + " " + esc(t("rescan")) + "</button>" +
      '<button class="btn btn-primary" id="btn-clean" type="button"></button>' +
      "</div>";

    byId("btn-rescan").addEventListener("click", function () { doCleanScan(seq); });
    byId("btn-clean").addEventListener("click", onClean);
    byId("clean-all").addEventListener("change", function (e) {
      if (e.target.checked) {
        state.cleanSelection = new Set(targets.map(function (x) { return x.id; }));
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
    targets.forEach(function (x) {
      if (state.cleanSelection.has(x.id)) { total += x.size_mb || 0; n++; }
    });
    var label = byId("clean-total");
    if (label) { label.textContent = tf("clean_total", { x: fmtMb(total) }); }
    var btn = byId("btn-clean");
    if (btn) {
      btn.textContent = tf("clean_n", { n: n });
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
      state.cleanSelection = new Set(state.cleanTargets.map(function (x) { return x.id; }));
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
      title: t("clean_modal_title"),
      bodyHtml: "<p>" + esc(tp(ids.length, "clean_body_one", "clean_body_many")) + "</p>",
      confirmLabel: t("clean_confirm"),
      danger: true,
      onConfirm: async function () {
        var btn = byId("btn-clean");
        setBusy(btn, t("cleaning"));
        try {
          var res = await api("/api/clean", { body: { ids: ids } });
          var results = res.results || [];
          var freed = 0;
          results.forEach(function (r) {
            state.cleanResults[r.id] = r;
            freed += r.freed_mb || 0;
          });
          showBanner(tf("clean_done", { x: fmtMb(freed) }), "ok");
        } catch (e) { /* bandeau déjà affiché */ }
        if (currentRoute() === "/clean") { buildCleanArea(renderSeq); }
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Page Moniteur (rafraîchissement 2 s, sparklines SVG maison)         */
  /* ------------------------------------------------------------------ */

  var monitorTimer = null;     /* intervalle actif, nettoyé en quittant la page */
  var monitorInFlight = false;

  function stopMonitor() {
    if (monitorTimer) { clearInterval(monitorTimer); monitorTimer = null; }
    monitorInFlight = false;
  }

  var MON_POINTS = 60;         /* 60 derniers points par sparkline */

  function pushHist(arr, v) {
    arr.push(v);
    if (arr.length > MON_POINTS) { arr.shift(); }
  }

  /* Sparkline SVG inline : trait 1.5px, currentColor, aucune lib. */
  function sparklineSvg(values, maxValue) {
    var W = 180, H = 40, PAD = 3;
    var open = '<svg class="spark" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none" aria-hidden="true">';
    if (!values || values.length < 2) { return open + "</svg>"; }
    var max = maxValue;
    if (max === undefined || max === null) {
      max = Math.max.apply(null, values);
    }
    if (!(max > 0)) { max = 1; }
    var step = W / (MON_POINTS - 1);
    var pts = values.map(function (v, i) {
      var clamped = Math.max(0, Math.min(v, max));
      var x = i * step;                        /* la courbe grandit depuis la gauche */
      var y = H - PAD - (clamped / max) * (H - PAD * 2);
      return (Math.round(x * 10) / 10) + "," + (Math.round(y * 10) / 10);
    }).join(" ");
    return open +
      '<polyline fill="none" stroke="currentColor" stroke-width="1.5" vector-effect="non-scaling-stroke" ' +
      'stroke-linecap="round" stroke-linejoin="round" points="' + pts + '"/></svg>';
  }

  function monTileHtml(id, label) {
    return '<div class="card mon-card">' +
      '<div class="mon-label">' + esc(label) + "</div>" +
      '<div class="mon-value" id="mon-' + id + '-val">—</div>' +
      '<div class="mon-sub" id="mon-' + id + '-sub">' + esc(t("mon_waiting")) + "</div>" +
      '<div class="spark-box" id="mon-' + id + '-spark">' + sparklineSvg([]) + "</div></div>";
  }

  function renderMonitor(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">' + esc(t("monitor_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("monitor_sub")) + "</p>" +
      '<div class="mon-grid">' +
      monTileHtml("cpu", t("mon_cpu")) +
      monTileHtml("ram", t("mon_ram")) +
      monTileHtml("disk", t("mon_disk")) +
      monTileHtml("net", t("mon_net")) +
      "</div>" +
      '<div class="group-label">' + esc(t("netusage_group")) + "</div>" +
      '<div class="card" id="netusage-card"><div class="loading-line">' + esc(t("mon_waiting")) + "</div></div>" +
      '<div class="group-label">' + esc(t("mon_top")) + "</div>" +
      '<div id="mon-procs"><div class="loading-line">' + esc(t("mon_waiting")) + "</div></div>";

    netUsageFailed = false;

    async function tick() {
      if (monitorInFlight) { return; }
      monitorInFlight = true;
      var sample;
      try {
        sample = await api("/api/monitor");
      } catch (e) {
        monitorInFlight = false;
        stopMonitor();
        if (alive(seq) && byId("page")) {
          byId("page").innerHTML =
            '<h1 class="page-title">' + esc(t("monitor_title")) + "</h1>" +
            '<p class="page-sub">' + esc(t("monitor_sub")) + "</p>" +
            '<div class="card empty-state">' + icon("alert") +
            '<p class="empty-title">' + esc(t("mon_unavail_title")) + "</p>" +
            "<p>" + esc(t("mon_unavail_body")) + "</p>" +
            '<button class="btn" id="btn-mon-retry" type="button">' + esc(t("retry")) + "</button></div>";
          var retry = byId("btn-mon-retry");
          if (retry) { retry.addEventListener("click", render); }
        }
        return;
      }
      monitorInFlight = false;
      if (!alive(seq) || !byId("mon-cpu-val")) { return; }
      updateMonitorDom(sample);
      updateNetUsage(seq);   /* même cadence que le moniteur, sans le bloquer */
    }

    tick();
    monitorTimer = setInterval(tick, 2000);
  }

  var netUsageInFlight = false;
  var netUsageFailed = false;   /* une erreur suffit : on cesse d'interroger la route */

  /** Rafraîchit l'encart « Activité réseau » (fetch silencieux, jamais de bandeau). */
  async function updateNetUsage(seq) {
    if (netUsageInFlight || netUsageFailed || !byId("netusage-card")) { return; }
    netUsageInFlight = true;
    var data = null;
    try {
      var res = await fetch("/api/netusage");
      if (!res.ok) { throw new Error("HTTP " + res.status); }
      data = await res.json();
    } catch (e) {
      netUsageFailed = true;
      var boxErr = byId("netusage-card");
      if (alive(seq) && boxErr) {
        boxErr.innerHTML = '<p class="muted small" style="margin:0">' + esc(t("netusage_unavailable")) + "</p>";
      }
      netUsageInFlight = false;
      return;
    }
    netUsageInFlight = false;
    if (!alive(seq)) { return; }
    var box = byId("netusage-card");
    if (!box || !data) { return; }
    box.innerHTML = netUsageHtml(data);
  }

  function netUsageHtml(data) {
    var apps = (data && data.apps) || [];
    var suspects = (data && data.suspects) || [];
    var html = '<p class="muted small" style="margin-top:0">' + esc(t("netusage_desc")) + "</p>";

    if (!apps.length) {
      html += '<p class="muted small" style="margin:0">' + esc(t("netusage_empty")) + "</p>";
    } else {
      html += '<table class="table"><thead><tr><th>' + esc(t("th_app")) + "</th><th>" +
        esc(t("th_connections")) + "</th></tr></thead><tbody>" +
        apps.map(function (a) {
          return '<tr><td class="mono proc-name" title="' + esc(a.name) + '">' + esc(a.name) + "</td>" +
            '<td class="mono">' + esc(a.connections) + "</td></tr>";
        }).join("") + "</tbody></table>";
    }

    if (suspects.length) {
      html += '<div class="netusage-suspects"><div class="netusage-suspects-title">' +
        esc(t("netusage_suspects")) + "</div>" +
        suspects.map(function (s) {
          return '<div class="settings-row">' +
            '<div class="set-info"><div class="set-name">' +
            '<span class="badge badge-yellow">' + esc(tr(s, "name")) + "</span></div>" +
            '<div class="set-status">' + esc(tr(s, "detail")) + "</div></div></div>";
        }).join("") + "</div>";
    }
    return html;
  }

  function updateMonitorDom(s) {
    var hist = state.monitorHist;
    var cpu = s.cpu_percent || 0;
    var ram = (s.ram && s.ram.percent) || 0;
    var diskTotal = ((s.disk_io && s.disk_io.read_mbps) || 0) + ((s.disk_io && s.disk_io.write_mbps) || 0);
    var netTotal = ((s.net_io && s.net_io.up_mbps) || 0) + ((s.net_io && s.net_io.down_mbps) || 0);
    pushHist(hist.cpu, cpu);
    pushHist(hist.ram, ram);
    pushHist(hist.disk, diskTotal);
    pushHist(hist.net, netTotal);

    byId("mon-cpu-val").textContent = dec(Math.round(cpu * 10) / 10) + " %";
    byId("mon-cpu-sub").textContent = (s.per_core || []).length ?
      (s.per_core || []).length + " threads" : "";
    byId("mon-cpu-spark").innerHTML = sparklineSvg(hist.cpu, 100);

    var ramObj = s.ram || {};
    byId("mon-ram-val").textContent = dec(Math.round(ram * 10) / 10) + " %";
    byId("mon-ram-sub").textContent = fmtGb(ramObj.used_gb) + " / " + fmtGb(ramObj.total_gb);
    byId("mon-ram-spark").innerHTML = sparklineSvg(hist.ram, 100);

    var dio = s.disk_io || {};
    byId("mon-disk-val").textContent = fmtRate(diskTotal);
    byId("mon-disk-sub").textContent =
      t("mon_read") + " " + fmtRate(dio.read_mbps || 0) + " · " + t("mon_write") + " " + fmtRate(dio.write_mbps || 0);
    byId("mon-disk-spark").innerHTML = sparklineSvg(hist.disk);

    var nio = s.net_io || {};
    byId("mon-net-val").textContent = fmtRate(netTotal);
    byId("mon-net-sub").textContent =
      t("mon_down") + " " + fmtRate(nio.down_mbps || 0) + " · " + t("mon_up") + " " + fmtRate(nio.up_mbps || 0);
    byId("mon-net-spark").innerHTML = sparklineSvg(hist.net);

    var procs = s.processes_top || [];
    var box = byId("mon-procs");
    if (!box) { return; }
    if (!procs.length) {
      box.innerHTML = '<p class="muted small">—</p>';
      return;
    }
    box.innerHTML =
      '<table class="table"><thead><tr><th>' + esc(t("th_process")) + "</th><th>" +
      esc(t("th_cpu")) + "</th><th>" + esc(t("th_ram")) + "</th></tr></thead><tbody>" +
      procs.map(function (p) {
        return '<tr><td class="mono proc-name" title="' + esc(p.name) + '">' + esc(p.name) + "</td>" +
          '<td class="mono">' + esc(dec(p.cpu_percent)) + ' %</td>' +
          '<td class="mono">' + esc(fmtMb(p.ram_mb)) + "</td></tr>";
      }).join("") + "</tbody></table>";
  }

  /* ------------------------------------------------------------------ */
  /* Page Démarrage (programmes au démarrage de Windows)                 */
  /* ------------------------------------------------------------------ */

  async function renderStartup(seq) {
    var page = byId("page");
    page.innerHTML =
      '<h1 class="page-title">' + esc(t("startup_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("startup_sub")) + "</p>" +
      '<div id="startup-area"><div class="loading-line">' + esc(t("startup_loading")) + "</div></div>";

    try {
      var res = await api("/api/startup");
      state.startupItems = res.items || [];
    } catch (e) {
      if (alive(seq) && byId("startup-area")) {
        byId("startup-area").innerHTML = '<p class="muted small">' + esc(t("startup_unavailable")) + "</p>";
      }
      return;
    }
    if (!alive(seq)) { return; }
    buildStartupArea(seq);
  }

  function buildStartupArea(seq) {
    var area = byId("startup-area");
    if (!area) { return; }
    var items = state.startupItems || [];
    var st = state.status;

    if (!items.length) {
      var body = st && st.is_windows ? t("startup_empty_windows") : t("startup_empty_other");
      area.innerHTML = '<div class="card empty-state">' + icon("check") +
        '<p class="empty-title">' + esc(t("startup_empty_title")) + "</p>" +
        "<p>" + esc(body) + "</p>" +
        '<button class="btn" id="btn-startup-reload" type="button">' + icon("refresh") + " " + esc(t("refresh")) + "</button></div>";
      byId("btn-startup-reload").addEventListener("click", render);
      return;
    }

    var rows = items.map(function (it) {
      var enabled = it.enabled !== false;   /* absent / null = activé */
      return "<tr>" +
        '<td class="startup-name">' + esc(it.name) + "</td>" +
        '<td><span class="mono mono-inline clean-path" title="' + esc(it.command) + '">' + esc(it.command) + "</span></td>" +
        '<td><span class="badge badge-gray">' + esc(startupSourceLabel(it.source)) + "</span></td>" +
        '<td><span class="startup-state"><label class="switch">' +
        '<input type="checkbox" class="startup-check" data-id="' + esc(it.id) + '"' + (enabled ? " checked" : "") + ">" +
        '<span class="track"></span></label>' +
        '<span class="state-label" id="su-state-' + esc(it.id) + '">' +
        esc(enabled ? t("state_enabled") : t("state_disabled")) + "</span></span></td>" +
        "</tr>";
    }).join("");

    area.innerHTML =
      '<table class="table"><thead><tr>' +
      "<th>" + esc(t("th_name")) + "</th><th>" + esc(t("th_command")) + "</th><th>" +
      esc(t("th_source")) + "</th><th>" + esc(t("th_state")) + "</th>" +
      "</tr></thead><tbody>" + rows + "</tbody></table>";

    $all(".startup-check", area).forEach(function (cb) {
      cb.addEventListener("change", function () {
        var id = cb.dataset.id;
        var item = null;
        (state.startupItems || []).forEach(function (it) { if (it.id === id) { item = it; } });
        if (!item) { return; }
        var desired = cb.checked;
        if (item.source === "HKLM") {
          /* Confirmation pour les entrées machine : on remet l'interrupteur en
             attendant la décision. */
          cb.checked = !desired;
          openModal({
            title: t("hklm_modal_title"),
            bodyHtml: "<p>" + esc(t("hklm_modal_body")) + "</p>" +
              '<p class="mono mono-inline">' + esc(item.name) + "</p>",
            confirmLabel: t("confirm"),
            danger: true,
            onConfirm: function () {
              cb.checked = desired;
              doToggleStartup(item, desired, cb);
            }
          });
        } else {
          doToggleStartup(item, desired, cb);
        }
      });
    });
  }

  async function doToggleStartup(item, enabled, cb) {
    cb.disabled = true;
    var ok = false;
    try {
      var res = await api("/api/startup/toggle", { body: { id: item.id, enabled: enabled } });
      ok = !!(res && res.ok);
      if (ok) {
        item.enabled = enabled;
        if (res.message) { showBanner(res.message, "ok"); }
      } else {
        showBanner((res && res.message) || t("startup_toggle_failed"), "error");
      }
    } catch (e) { /* bandeau déjà affiché */ }
    if (!ok) { cb.checked = item.enabled !== false; }
    cb.disabled = false;
    var stateLabel = byId("su-state-" + item.id);
    if (stateLabel) {
      stateLabel.textContent = item.enabled !== false ? t("state_enabled") : t("state_disabled");
    }
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
      '<h1 class="page-title">' + esc(t("assistant_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("assistant_sub")) + "</p>" +
      '<div id="assistant-area"><div class="loading-line">' + esc(t("checking_keys")) + "</div></div>";

    try {
      state.aiKeys = await api("/api/ai/keys");
    } catch (e) {
      if (alive(seq) && byId("assistant-area")) {
        byId("assistant-area").innerHTML = '<p class="muted small">' + esc(t("assistant_unavailable")) + "</p>";
      }
      return;
    }
    if (!alive(seq)) { return; }

    var configured = ((state.aiKeys && state.aiKeys.keys) || []).filter(function (k) { return k.configured; });
    var area = byId("assistant-area");

    if (!configured.length) {
      area.innerHTML = '<div class="card empty-state">' + icon("alert") +
        '<p class="empty-title">' + esc(t("no_key_title")) + "</p>" +
        "<p>" + esc(t("no_key_body")) + "</p>" +
        '<button class="btn btn-primary" id="btn-goto-settings" type="button">' + esc(t("open_settings")) + "</button></div>";
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
      "<label>" + esc(t("provider")) + " " +
      '<select class="input" id="chat-provider">' + configured.map(function (k) {
        return '<option value="' + esc(k.provider) + '"' + (k.provider === state.chatProvider ? " selected" : "") + ">" +
          esc(providerName(k.provider)) + "</option>";
      }).join("") + "</select></label>" +
      '<button class="btn btn-ghost btn-sm" id="chat-clear" type="button">' + esc(t("chat_clear")) + "</button>" +
      "</div>" +
      '<div class="chat-messages" id="chat-messages"></div>' +
      '<div class="chat-input-row">' +
      '<textarea class="input" id="chat-input" rows="1" placeholder="' + esc(t("chat_placeholder")) + '"></textarea>' +
      '<button class="btn btn-primary" id="chat-send" type="button">' + icon("send") + " " + esc(t("send")) + "</button>" +
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
      html = '<div class="chat-empty">' + esc(t("chat_empty")) + "<br>" +
        '<span class="small">' + esc(t("chat_example")) + "</span></div>";
    } else {
      html = state.chat.map(function (m) {
        var body = formatChatText(m.content);
        if (m.role !== "user") {
          // Marqueurs [[tweak:id]] émis par l'assistant → bouton Appliquer.
          body = body.replace(/\[\[tweak:([a-z0-9_]+)\]\]/g, function (_, id) {
            return ' <button class="btn btn-sm chat-apply" type="button" data-apply-tweak="' +
              id + '">' + esc(t("chat_apply")) + ' <span class="mono mono-inline">' + id + "</span></button>";
          });
        }
        return '<div class="msg ' + (m.role === "user" ? "msg-user" : "msg-assistant") + '">' +
          body + "</div>";
      }).join("");
      if (state.chatBusy) { html += '<div class="msg-pending">' + esc(t("chat_pending")) + "</div>"; }
      if (state.chatError) { html += '<div class="msg-error">' + esc(state.chatError) + "</div>"; }
    }
    box.innerHTML = html;
    box.scrollTop = box.scrollHeight;
    $all("[data-apply-tweak]", box).forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var id = btn.dataset.applyTweak;
        setBusy(btn, t("chat_apply"));
        try {
          var res = await api("/api/tweaks/apply", { body: { ids: [id] } });
          var r = res && res.results && res.results[0];
          if (r && r.ok) {
            btn.textContent = t("chat_applied");
            btn.disabled = true;
            showBanner(r.message || t("chat_applied"), "ok");
            return;
          }
          showBanner((r && r.message) || t("chat_apply_fail"), "error");
        } catch (e) { /* bandeau déjà affiché */ }
        clearBusy(btn);
      });
    });
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
        state.chatError = res.message || t("chat_no_reply");
      }
    } catch (e) {
      state.chatError = t("chat_error_net");
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
      '<h1 class="page-title">' + esc(t("settings_title")) + "</h1>" +
      '<p class="page-sub">' + esc(t("settings_sub")) + "</p>" +
      '<div id="settings-area"><div class="loading-line">' + esc(t("loading")) + "</div></div>";

    try {
      state.aiKeys = await api("/api/ai/keys");
    } catch (e) {
      state.aiKeys = state.aiKeys || { keys: [] };
    }
    try {
      state.widgetCfg = await api("/api/widget");
    } catch (e) {
      state.widgetCfg = state.widgetCfg || null;
    }
    try {
      state.schedule = await api("/api/schedule");
    } catch (e) {
      state.schedule = null;
    }
    if (!alive(seq)) { return; }
    buildSettingsArea(seq);
  }

  /** Enregistre un réglage partiel du widget et rafraîchit la section. */
  async function saveWidget(partial, seq, silent) {
    try {
      var res = await api("/api/widget", { body: partial });
      state.widgetCfg = res;
      if (res && res.autostart_result && res.autostart_result.ok === false) {
        showBanner(res.autostart_result.message || t("widget_save_err"), "error");
      } else if (!silent) {
        showBanner(t("widget_saved"), "ok");
      }
      return res;
    } catch (e) {
      return null;
    }
  }

  /** HTML de la section Widget des Réglages. */
  function widgetSectionHtml() {
    var cfg = state.widgetCfg && state.widgetCfg.widget;
    if (!cfg) { return ""; }
    var els = cfg.elements || {};
    var elNames = ["fps", "game", "cpu", "ram", "net", "clock", "temp"];
    var checks = elNames.map(function (n) {
      return '<label class="check-item"><input type="checkbox" data-wel="' + n + '"' +
        (els[n] ? " checked" : "") + "> " + esc(t("widget_el_" + n)) + "</label>";
    }).join("");
    function seg(name, values, labels, current) {
      return '<div class="seg" data-wseg="' + name + '">' + values.map(function (v, i) {
        return '<button type="button" data-val="' + v + '"' +
          (v === current ? ' class="active"' : "") + ">" + esc(labels[i]) + "</button>";
      }).join("") + "</div>";
    }
    return '<div class="group-label">' + esc(t("widget_group")) + "</div>" +
      '<div class="card">' +
      '<p class="muted small" style="margin-top:0">' + esc(t("widget_note")) + "</p>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("widget_elements")) + "</div></div>" +
      '<div class="set-controls check-grid">' + checks + "</div></div>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("widget_theme")) + "</div>" +
      '<div class="set-status">' + esc(t("widget_theme_desc")) + "</div></div>" +
      '<div class="set-controls">' + seg("theme", ["dark", "light", "minimal"],
        [t("widget_theme_dark"), t("widget_theme_light"), t("widget_theme_minimal")], cfg.theme) + "</div></div>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("widget_layout")) + "</div></div>" +
      '<div class="set-controls">' + seg("layout", ["row", "column"],
        [t("widget_layout_row"), t("widget_layout_col")], cfg.layout) + "</div></div>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("widget_scale")) + "</div></div>" +
      '<div class="set-controls">' + seg("scale", ["s", "m", "l"], ["S", "M", "L"], cfg.scale) + "</div></div>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("widget_opacity")) + "</div></div>" +
      '<div class="set-controls"><input type="range" id="widget-opacity" min="10" max="100" step="5" value="' +
      Math.round((cfg.opacity || 0.92) * 100) + '"> <span class="mono mono-inline" id="widget-opacity-val">' +
      Math.round((cfg.opacity || 0.92) * 100) + "%</span></div></div>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("widget_click_through")) + "</div>" +
      '<div class="set-status">' + esc(t("widget_click_through_desc")) + "</div></div>" +
      '<div class="set-controls"><label class="check-item"><input type="checkbox" id="widget-ct"' +
      (cfg.click_through ? " checked" : "") + "></label></div></div>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("gamemode_name")) + "</div>" +
      '<div class="set-status">' + esc(t("gamemode_desc")) + "</div></div>" +
      '<div class="set-controls"><label class="check-item"><input type="checkbox" id="widget-gamemode"' +
      (cfg.gamemode ? " checked" : "") + "></label></div></div>" +
      '<div class="settings-row sub-setting' + (cfg.gamemode ? "" : " sub-disabled") + '" id="row-pause-updates">' +
      '<div class="set-info"><div class="set-name">' + esc(t("pause_updates_name")) + "</div>" +
      '<div class="set-status">' + esc(t("pause_updates_desc")) + "</div></div>" +
      '<div class="set-controls"><label class="check-item"><input type="checkbox" id="widget-pause-updates"' +
      (cfg.pause_updates ? " checked" : "") + (cfg.gamemode ? "" : " disabled") + "></label></div></div>" +
      '<div class="settings-row"><div class="set-info"><div class="set-name">' + esc(t("widget_autostart")) + "</div>" +
      '<div class="set-status">' + esc(t("widget_autostart_desc")) + "</div></div>" +
      '<div class="set-controls"><select class="input" id="widget-autostart">' +
      [["never", t("widget_auto_never")], ["always", t("widget_auto_always")], ["game", t("widget_auto_game")]]
        .map(function (o) {
          return '<option value="' + o[0] + '"' + (cfg.autostart === o[0] ? " selected" : "") + ">" + esc(o[1]) + "</option>";
        }).join("") + "</select>" +
      '<button class="btn btn-sm" id="widget-launch" type="button">' + esc(t("widget_launch")) + "</button>" +
      "</div></div></div>";
  }

  /** Liaisons de la section Widget des Réglages. */
  function bindWidgetSection(area, seq) {
    if (!state.widgetCfg || !state.widgetCfg.widget) { return; }
    $all("[data-wel]", area).forEach(function (cb) {
      cb.addEventListener("change", function () {
        var el = {}; el[cb.dataset.wel] = cb.checked;
        saveWidget({ elements: el }, seq, true);
      });
    });
    $all("[data-wseg]", area).forEach(function (segEl) {
      $all("button", segEl).forEach(function (b) {
        b.addEventListener("click", async function () {
          var partial = {}; partial[segEl.dataset.wseg] = b.dataset.val;
          await saveWidget(partial, seq, true);
          $all("button", segEl).forEach(function (x) { x.classList.toggle("active", x === b); });
        });
      });
    });
    var op = byId("widget-opacity");
    if (op) {
      op.addEventListener("input", function () {
        var lbl = byId("widget-opacity-val");
        if (lbl) { lbl.textContent = op.value + "%"; }
      });
      op.addEventListener("change", function () {
        saveWidget({ opacity: Number(op.value) / 100 }, seq, true);
      });
    }
    var ct = byId("widget-ct");
    if (ct) {
      ct.addEventListener("change", function () {
        saveWidget({ click_through: ct.checked }, seq, true);
      });
    }
    var gm = byId("widget-gamemode");
    var pu = byId("widget-pause-updates");
    if (gm) {
      gm.addEventListener("change", function () {
        saveWidget({ gamemode: gm.checked }, seq, true);
        /* La sous-case dépend du mode jeu : grisée quand il est décoché. */
        if (pu) { pu.disabled = !gm.checked; }
        var row = byId("row-pause-updates");
        if (row) { row.classList.toggle("sub-disabled", !gm.checked); }
      });
    }
    if (pu) {
      pu.addEventListener("change", function () {
        saveWidget({ pause_updates: pu.checked }, seq, true);
      });
    }
    var autoSel = byId("widget-autostart");
    if (autoSel) {
      autoSel.addEventListener("change", function () {
        saveWidget({ autostart: autoSel.value }, seq);
      });
    }
    var launch = byId("widget-launch");
    if (launch) {
      launch.addEventListener("click", async function () {
        setBusy(launch, t("widget_launch"));
        try {
          var res = await api("/api/widget/launch", { method: "POST" });
          showBanner((res && res.ok) ? t("widget_launched") : ((res && res.message) || t("widget_save_err")),
            (res && res.ok) ? "ok" : "error");
        } catch (e) { /* bandeau déjà affiché */ }
        clearBusy(launch);
      });
    }
  }

  /** HTML du groupe « Maintenance » (nettoyage planifié hebdomadaire). */
  function maintenanceSectionHtml() {
    var sched = state.schedule;
    var row;
    if (!sched) {
      row = '<p class="muted small" style="margin:0">' + esc(t("sched_unavailable")) + "</p>";
    } else if (sched.supported === false) {
      /* Non supporté (hors Windows) : ligne grisée, detail en sous-titre. */
      row = '<div class="settings-row sub-disabled">' +
        '<div class="set-info"><div class="set-name">' + esc(t("sched_name")) + "</div>" +
        '<div class="set-status">' + esc(sched.detail || "") + "</div></div>" +
        '<div class="set-controls"><label class="switch">' +
        '<input type="checkbox" disabled><span class="track"></span></label></div></div>';
    } else {
      row = '<div class="settings-row">' +
        '<div class="set-info"><div class="set-name">' + esc(t("sched_name")) + "</div>" +
        '<div class="set-status" id="sched-status">' + esc(sched.detail || t("sched_desc")) + "</div></div>" +
        '<div class="set-controls"><label class="switch">' +
        '<input type="checkbox" id="sched-toggle"' + (sched.enabled ? " checked" : "") + ">" +
        '<span class="track"></span></label></div></div>';
    }
    return '<div class="group-label">' + esc(t("maintenance_group")) + "</div>" +
      '<div class="card">' + row + "</div>";
  }

  /** Liaison de l'interrupteur du nettoyage planifié. */
  function bindMaintenanceSection() {
    var toggle = byId("sched-toggle");
    if (!toggle) { return; }
    toggle.addEventListener("change", async function () {
      var desired = toggle.checked;
      toggle.disabled = true;
      var ok = false;
      try {
        var res = await api("/api/schedule", { body: { enabled: desired } });
        ok = !!(res && res.ok);
        showBanner((res && res.message) || "", ok ? "ok" : "error");
      } catch (e) { /* bandeau déjà affiché */ }
      if (ok) {
        if (state.schedule) { state.schedule.enabled = desired; }
      } else {
        toggle.checked = !desired;
      }
      toggle.disabled = false;
    });
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
        esc(t("key_configured")) + (k.masked ? ' · <span class="mono mono-inline">' + esc(k.masked) + "</span>" : "") :
        esc(t("key_not_configured"));
      return '<div class="settings-row">' +
        '<div class="set-info"><div class="set-name">' + esc(p.name) + "</div>" +
        '<div class="set-status">' + status + "</div>" +
        (p.noteKey ? '<div class="set-note">' + t(p.noteKey) + "</div>" : "") +
        "</div>" +
        '<div class="set-controls">' +
        '<input class="input" type="password" id="key-in-' + esc(p.id) + '" placeholder="' + esc(t("key_placeholder")) + '" autocomplete="off">' +
        '<button class="btn btn-sm" data-save-key="' + esc(p.id) + '" type="button">' + esc(t("save")) + "</button>" +
        (k.configured ? '<button class="btn btn-sm btn-danger" data-del-key="' + esc(p.id) + '" type="button">' + esc(t("del")) + "</button>" : "") +
        "</div></div>";
    }).join("");

    var defSelect = configured.length ?
      '<select class="input" id="default-provider">' + configured.map(function (p) {
        return '<option value="' + esc(p.id) + '"' + (p.id === def ? " selected" : "") + ">" + esc(p.name) + "</option>";
      }).join("") + "</select>" :
      '<span class="muted small">' + esc(t("no_keys_yet")) + "</span>";

    area.innerHTML =
      '<div class="group-label">' + esc(t("keys_group")) + "</div>" +
      '<div class="card">' +
      '<p class="muted small" style="margin-top:0">' + esc(t("keys_note")) + "</p>" +
      keyRows + "</div>" +

      '<div class="group-label">' + esc(t("assistant_group")) + "</div>" +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">' + esc(t("default_provider")) + "</div>" +
      '<div class="set-status">' + esc(t("default_provider_desc")) + "</div></div>" +
      '<div class="set-controls">' + defSelect + "</div></div></div>" +

      '<div class="group-label">' + esc(t("appearance_group")) + "</div>" +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">' + esc(t("theme")) + "</div>" +
      '<div class="set-status">' + esc(t("theme_desc")) + "</div></div>" +
      '<div class="set-controls"><div class="seg" data-seg="theme">' +
      '<button type="button" data-theme="light">' + esc(t("light")) + "</button>" +
      '<button type="button" data-theme="dark">' + esc(t("dark")) + "</button>" +
      "</div></div></div>" +
      '<div class="settings-row">' +
      '<div class="set-info"><div class="set-name">' + esc(t("language")) + "</div>" +
      '<div class="set-status">' + esc(t("language_desc")) + "</div></div>" +
      '<div class="set-controls"><div class="seg" data-seg="lang">' +
      '<button type="button" data-lang="fr"' + (LANG === "fr" ? ' class="active"' : "") + ">Français</button>" +
      '<button type="button" data-lang="en"' + (LANG === "en" ? ' class="active"' : "") + ">English</button>" +
      "</div></div></div></div>" +

      '<div class="group-label">' + esc(t("report_group")) + "</div>" +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">' + esc(t("report_name")) + "</div>" +
      '<div class="set-status">' + esc(t("report_desc")) + "</div></div>" +
      '<div class="set-controls"><a class="btn btn-sm" href="/api/report" download>' +
      icon("download") + " " + esc(t("report_download")) + "</a></div></div></div>" +

      '<div class="group-label">' + esc(t("update_group")) + "</div>" +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">' + esc(t("update_name")) + "</div>" +
      '<div class="set-status" id="update-status">Overdrive' + (st.version ? " v" + esc(st.version) : "") + "</div></div>" +
      '<div class="set-controls" id="update-controls">' +
      '<button class="btn btn-sm" id="btn-update-check" type="button">' + esc(t("update_check")) + "</button>" +
      "</div></div></div>" +

      '<div class="group-label">' + esc(t("backup_group")) + "</div>" +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">' + esc(t("backup_export")) + " / " + esc(t("backup_import")) + "</div>" +
      '<div class="set-status">' + esc(t("backup_export_desc")) + "</div></div>" +
      '<div class="set-controls">' +
      '<a class="btn btn-sm" href="/api/profile/export" download>' + icon("download") + " " + esc(t("backup_export")) + "</a>" +
      '<button class="btn btn-sm" id="btn-import-profile" type="button">' + esc(t("backup_import")) + "</button>" +
      '<input type="file" id="import-file" accept="application/json" hidden>' +
      "</div></div></div>" +

      widgetSectionHtml() +

      maintenanceSectionHtml() +

      '<div class="group-label">' + esc(t("quiz_group")) + "</div>" +
      '<div class="card"><div class="settings-row">' +
      '<div class="set-info"><div class="set-name">' + esc(t("quiz_profile")) + "</div>" +
      '<div class="set-status">' + esc(state.profile ?
        tf("quiz_profile_current", { p: tr(state.profile, "label") || state.profile.id }) :
        t("quiz_profile_none")) + "</div></div>" +
      '<div class="set-controls"><button class="btn btn-sm" id="btn-redo-quiz" type="button">' + esc(t("quiz_redo")) + "</button></div>" +
      "</div></div>" +

      '<div class="group-label">' + esc(t("about_group")) + "</div>" +
      '<div class="card">' +
      '<p style="margin-top:0"><strong>Overdrive</strong>' + (st.version ? " v" + esc(st.version) : "") +
      (st.platform ? ' · <span class="mono mono-inline">' + esc(st.platform) + "</span>" : "") +
      (st.is_windows ? (st.is_admin ? ' · <span class="badge badge-green">' + esc(t("badge_admin")) + "</span>" :
        ' · <span class="badge badge-yellow">' + esc(t("badge_not_admin")) + "</span>") : "") +
      "</p>" +
      '<p class="muted small" style="margin-bottom:0">' + esc(t("about_note")) + "</p>" +
      "</div>";

    /* Liaisons. */
    $all("[data-save-key]", area).forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var provider = btn.dataset.saveKey;
        var input = byId("key-in-" + provider);
        var key = input ? input.value.trim() : "";
        if (!key) {
          showBanner(t("key_enter_first"), "error");
          return;
        }
        setBusy(btn, t("saving"));
        try {
          var saveRes = await api("/api/ai/keys", { body: { provider: provider, key: key } });
          if (!saveRes || saveRes.ok === false) {
            showBanner((saveRes && saveRes.message) || t("key_save_err"), "error");
            clearBusy(btn);
            return;
          }
          showBanner(tf("key_saved", { p: providerName(provider) }), "ok");
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
          title: tf("key_del_title", { p: providerName(provider) }),
          bodyHtml: "<p>" + esc(t("key_del_body")) + "</p>",
          confirmLabel: t("del"),
          danger: true,
          onConfirm: async function () {
            try {
              var delRes = await api("/api/ai/keys/" + encodeURIComponent(provider), { method: "DELETE" });
              if (!delRes || delRes.ok === false) {
                showBanner((delRes && delRes.message) || t("key_del_err"), "error");
              } else {
                showBanner(tf("key_deleted", { p: providerName(provider) }), "ok");
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
          showBanner(tf("default_set", { p: providerName(defSel.value) }), "ok");
        } catch (e) { /* bandeau déjà affiché */ }
      });
    }

    $all(".seg[data-seg='theme'] button", area).forEach(function (b) {
      b.addEventListener("click", function () { setTheme(b.dataset.theme); });
    });
    $all(".seg[data-seg='lang'] button", area).forEach(function (b) {
      b.addEventListener("click", function () { setLang(b.dataset.lang); });
    });
    updateThemeLabel();

    bindWidgetSection(area, seq);
    bindMaintenanceSection();

    byId("btn-update-check").addEventListener("click", async function () {
      var btn = byId("btn-update-check");
      var status = byId("update-status");
      setBusy(btn, t("update_checking"));
      try {
        var u = await api("/api/update/check");
        if (status) { status.textContent = u.message || ""; }
        var controls = byId("update-controls");
        if (u.update_available && u.download_url && controls && !byId("btn-update-dl")) {
          var a = document.createElement("a");
          a.className = "btn btn-sm btn-primary";
          a.id = "btn-update-dl";
          a.href = u.download_url;
          a.target = "_blank";
          a.rel = "noopener";
          a.textContent = t("update_download");
          controls.appendChild(a);
        }
        if (u.update_available === false) { showBanner(t("update_none"), "ok"); }
      } catch (e) { /* bandeau déjà affiché */ }
      clearBusy(btn);
    });

    byId("btn-import-profile").addEventListener("click", function () {
      var input = byId("import-file");
      if (input) { input.click(); }
    });
    var importInput = byId("import-file");
    if (importInput) {
      importInput.addEventListener("change", function () {
        var file = importInput.files && importInput.files[0];
        if (!file) { return; }
        var reader = new FileReader();
        reader.onload = async function () {
          var data = null;
          try { data = JSON.parse(String(reader.result)); } catch (e) { data = null; }
          if (!data || typeof data !== "object") {
            showBanner(t("backup_import_err"), "error");
            return;
          }
          try {
            var res = await api("/api/profile/import", { body: data });
            if (res && res.ok) {
              showBanner(t("backup_imported"), "ok");
              state.status = await api("/api/status");
              state.profile = state.status.profile || null;
              if (state.status.lang) { applyLang(state.status.lang); }
              render();
              return;
            }
            showBanner((res && res.message) || t("backup_import_err"), "error");
          } catch (e) { /* bandeau déjà affiché */ }
        };
        reader.readAsText(file);
      });
    }

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
        '" type="button">' + mark + "<span>" + esc(tr(o, "label")) + "</span></button>";
    }).join("");

    root.innerHTML =
      '<div class="quiz-overlay"><div class="quiz-inner">' +
      '<div class="quiz-head">' +
      '<span class="quiz-brand">' +
      '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/></svg>' +
      "Overdrive</span>" +
      '<span class="quiz-progress">' + esc(tf("quiz_progress", { i: quiz.index + 1, n: total })) + "</span>" +
      '<button class="btn btn-ghost btn-sm" id="quiz-later" type="button">' +
      esc(quiz.firstRun ? t("later") : t("cancel")) + "</button>" +
      "</div>" +
      '<div class="quiz-bar"><div style="width:' + pct + '%"></div></div>' +
      '<h2 class="quiz-question">' + esc(tr(q, "question")) + "</h2>" +
      '<p class="quiz-hint">' + esc(q.multi ? t("quiz_multi") : t("quiz_single")) + "</p>" +
      '<div class="quiz-options">' + optionsHtml + "</div>" +
      '<div class="quiz-nav">' +
      '<button class="btn" id="quiz-prev" type="button"' + (quiz.index === 0 ? " disabled" : "") + ">" +
      icon("left") + " " + esc(t("prev")) + "</button>" +
      '<button class="btn btn-primary" id="quiz-next" type="button"' +
      (quizAnswered(q) && !quiz.submitting ? "" : " disabled") + ">" +
      (quiz.submitting ? esc(t("quiz_analyzing")) :
        (quiz.index === total - 1 ? esc(t("finish")) : esc(t("next")) + " " + icon("right"))) +
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
    var notes = (LANG === "en" && Array.isArray(p.notes_en)) ? p.notes_en : (p.notes || []);

    root.innerHTML =
      '<div class="quiz-overlay"><div class="quiz-inner"><div class="quiz-result">' +
      '<div class="result-check">' + icon("check") + "</div>" +
      "<h2>" + esc(tf("quiz_profile_prefix", { p: tr(p, "label") || p.id })) + "</h2>" +
      '<p class="result-desc">' + esc(tr(p, "description")) + "</p>" +
      (notes.length ?
        '<div class="quiz-notes"><div class="quiz-notes-title">' + esc(t("quiz_notes_title")) + "</div><ul>" +
        notes.map(function (n) { return "<li>" + esc(n) + "</li>"; }).join("") + "</ul></div>" : "") +
      '<div class="quiz-result-actions">' +
      (quiz.firstRun ?
        '<button class="btn btn-primary" id="quiz-continue" type="button">' + esc(t("continue_lbl")) + "</button>" :
        '<button class="btn btn-primary" id="quiz-goto-tweaks" type="button">' + esc(t("quiz_see_tweaks")) + "</button>" +
        '<button class="btn" id="quiz-close" type="button">' + esc(t("close")) + "</button>") +
      "</div></div></div></div>";

    if (quiz.firstRun) {
      byId("quiz-continue").addEventListener("click", renderAutostartStep);
      return;
    }
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

  /** Étape d'onboarding : démarrage automatique du widget (premier lancement). */
  function renderAutostartStep() {
    var root = byId("overlay-root");
    if (!root) { return; }
    var chosen = "never";
    var options = [
      { id: "never", label: t("widget_auto_never"), desc: t("ob_never_desc") },
      { id: "always", label: t("widget_auto_always"), desc: t("ob_always_desc") },
      { id: "game", label: t("widget_auto_game"), desc: t("ob_game_desc") }
    ];

    function optionsHtml() {
      return options.map(function (o) {
        var selected = o.id === chosen;
        return '<button class="quiz-opt' + (selected ? " selected" : "") + '" data-ob="' + o.id + '" type="button">' +
          '<span class="opt-mark round"><span class="opt-dot-inner"></span></span>' +
          '<span class="opt-text">' + esc(o.label) +
          '<span class="opt-desc">' + esc(o.desc) + "</span></span></button>";
      }).join("");
    }

    root.innerHTML =
      '<div class="quiz-overlay"><div class="quiz-inner">' +
      '<h2 class="quiz-question">' + esc(t("ob_title")) + "</h2>" +
      '<p class="quiz-hint">' + esc(t("ob_sub")) + "</p>" +
      '<div class="quiz-options" id="ob-options">' + optionsHtml() + "</div>" +
      '<div class="quiz-result-actions">' +
      '<button class="btn" id="ob-launch" type="button">' + esc(t("ob_launch_now")) + "</button>" +
      '<button class="btn btn-primary" id="ob-finish" type="button">' + esc(t("ob_finish")) + "</button>" +
      "</div></div></div>";

    function bindOptions() {
      $all("[data-ob]", root).forEach(function (b) {
        b.addEventListener("click", function () {
          chosen = b.dataset.ob;
          byId("ob-options").innerHTML = optionsHtml();
          bindOptions();
        });
      });
    }
    bindOptions();

    byId("ob-launch").addEventListener("click", async function () {
      var btn = byId("ob-launch");
      setBusy(btn, t("ob_launch_now"));
      try {
        var res = await api("/api/widget/launch", { method: "POST" });
        showBanner((res && res.ok) ? t("widget_launched") : ((res && res.message) || t("widget_save_err")),
          (res && res.ok) ? "ok" : "error");
      } catch (e) { /* bandeau déjà affiché */ }
      clearBusy(btn);
    });

    byId("ob-finish").addEventListener("click", async function () {
      var btn = byId("ob-finish");
      setBusy(btn, t("ob_finish"));
      await saveWidget({ autostart: chosen }, 0, true);
      closeQuiz();
      state.pendingProfileSelect = true;
      if (currentRoute() === "/tweaks") { render(); } else { window.location.hash = "#/tweaks"; }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Initialisation                                                      */
  /* ------------------------------------------------------------------ */

  async function init() {
    applyStaticI18n();

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

      /* Thème : la préférence locale prime, sinon le réglage serveur. */
      var storedTheme = null;
      try { storedTheme = localStorage.getItem("overdrive-theme"); } catch (e) { /* stockage indisponible */ }
      if (!storedTheme && (st.theme === "dark" || st.theme === "light")) { applyTheme(st.theme); }

      /* Langue : la préférence locale prime, sinon le réglage serveur. */
      var storedLang = null;
      try { storedLang = localStorage.getItem("overdrive-lang"); } catch (e2) { /* stockage indisponible */ }
      if (!storedLang && (st.lang === "fr" || st.lang === "en") && st.lang !== LANG) {
        applyLang(st.lang);
      }

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
