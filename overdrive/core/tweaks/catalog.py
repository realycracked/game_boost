"""Catalogue des tweaks d'optimisation Windows 10/11 d'Overdrive.

Chaque tweak est déclaratif : des actions `apply` et `revert` (réellement
inverses, basées sur les valeurs par défaut de Windows) interprétées par
`engine.py`. Aucun tweak ne touche aux mitigations de sécurité ni à la
protection temps réel de Windows Defender.
"""

from __future__ import annotations

from typing import Any

CATEGORIES: list[dict] = [
    {"id": "alimentation", "label": "Alimentation"},
    {"id": "visuels", "label": "Visuels & animations"},
    {"id": "jeux", "label": "Jeux"},
    {"id": "systeme", "label": "Système & CPU"},
    {"id": "memoire", "label": "Mémoire"},
    {"id": "reseau", "label": "Réseau & latence"},
    {"id": "gpu", "label": "GPU"},
    {"id": "stockage", "label": "Stockage"},
    {"id": "confidentialite", "label": "Confidentialité & télémétrie"},
    {"id": "services", "label": "Services Windows"},
    {"id": "peripheriques", "label": "Souris & périphériques"},
]

# ---------------------------------------------------------------------------
# Petits constructeurs d'actions (le catalogue reste une liste de dicts purs).
# ---------------------------------------------------------------------------


def _reg(hive: str, path: str, name: str, kind: str, value: Any) -> dict:
    """Action d'écriture registre (via winreg dans l'engine)."""
    return {"type": "reg", "hive": hive, "path": path, "name": name,
            "kind": kind, "value": value}


def _reg_del(hive: str, path: str, name: str) -> dict:
    """Action de suppression d'une valeur registre."""
    return {"type": "reg_delete", "hive": hive, "path": path, "name": name}


def _ps(command: str) -> dict:
    """Action PowerShell à commande FIXE (l'engine préfixe powershell.exe)."""
    return {"type": "powershell", "args": ["-NoProfile", "-Command", command]}


def _cmd(*args: str) -> dict:
    """Action exécutable + arguments fixes (shell=False)."""
    return {"type": "cmd", "args": list(args)}


def _svc(service: str, startup: str, stop: bool = False) -> dict:
    """Action sur un service Windows (type de démarrage, arrêt optionnel)."""
    return {"type": "service", "service": service, "startup": startup, "stop": stop}


def _chk_reg(hive: str, path: str, name: str, expected: Any) -> dict:
    """Check lecture seule d'une valeur registre."""
    return {"type": "reg", "hive": hive, "path": path, "name": name,
            "expected": expected}


def _chk_svc(service: str, expected_startup: str) -> dict:
    """Check lecture seule du type de démarrage d'un service."""
    return {"type": "service", "service": service,
            "expected_startup": expected_startup}


def _t(id: str, name: str, description: str, category: str, impact: str,
       risk: str, apply: list[dict], revert: list[dict],
       check: dict | None = None, default_for: list[str] | None = None,
       lowend: bool = False, windows_only: bool = True) -> dict:
    """Construit l'entrée normalisée d'un tweak.

    ``lowend`` marque les tweaks réellement utiles sur une petite
    configuration (iGPU, 4-8 Go de RAM, CPU 2-4 cœurs) ; le champ circule
    tel quel jusqu'à /api/tweaks via ``engine.list_tweaks()``.
    """
    return {
        "id": id,
        "name": name,
        "description": description,
        "category": category,
        "impact": impact,
        "risk": risk,
        "windows_only": windows_only,
        "default_for": list(default_for or []),
        "lowend": bool(lowend),
        "apply": apply,
        "revert": revert,
        "check": check,
    }


# Chemins registre fréquents.
_DESKTOP = r"Control Panel\Desktop"
_MOUSE = r"Control Panel\Mouse"
_ADVANCED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
_GCS = r"System\GameConfigStore"
_SYSPROF = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
_GAMES_TASK = _SYSPROF + r"\Tasks\Games"
_MEMMGMT = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
_GFX = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
_CDM = r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"

TWEAKS: list[dict] = [
    # ------------------------------------------------------------------ #
    # Alimentation                                                        #
    # ------------------------------------------------------------------ #
    _t("power_plan_ultimate", "Plan Performances ultimes",
       "Active le plan « Performances ultimes » : supprime les économies "
       "d'énergie fines du plan équilibré. Gain modeste sur les CPU récents "
       "(frametimes un peu plus stables) ; augmente consommation et chauffe "
       "— prudence sur portable limité thermiquement.",
       "alimentation", "moyen", "sur",
       # Duplique le schéma caché vers un GUID fixe (Overdrive) puis l'active :
       # sans GUID de destination, powercfg crée une copie au GUID aléatoire et
       # le setactive sur le schéma source échoue sur la plupart des éditions.
       apply=[_ps("powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e | "
                  "Out-Null; powercfg /delete "
                  "0d0d0d0d-0d0d-0d0d-0d0d-0d0d0d0d0d0d 2>$null | Out-Null; "
                  "powercfg /duplicatescheme "
                  "e9a42b02-d5df-448d-aa00-03f14749eb61 "
                  "0d0d0d0d-0d0d-0d0d-0d0d-0d0d0d0d0d0d | Out-Null; "
                  "powercfg /setactive 0d0d0d0d-0d0d-0d0d-0d0d-0d0d0d0d0d0d")],
       revert=[_ps("powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e | "
                   "Out-Null; powercfg /delete "
                   "0d0d0d0d-0d0d-0d0d-0d0d-0d0d0d0d0d0d 2>$null | Out-Null")],
       check=None, default_for=["fps", "latence"], lowend=True),

    _t("hibernation_off", "Désactiver l'hibernation",
       "Désactive l'hibernation et supprime hiberfil.sys (plusieurs Go "
       "récupérés). Aucun effet sur les FPS : c'est un gain d'espace disque, "
       "précieux sur les petits SSD. Fait perdre la veille prolongée (et le "
       "démarrage rapide).",
       "alimentation", "faible", "sur",
       apply=[_cmd("powercfg", "/h", "off")],
       revert=[_cmd("powercfg", "/h", "on")],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Power",
                      "HibernateEnabled", 0),
       default_for=[], lowend=True),

    _t("usb_selective_suspend_off", "Suspension sélective USB désactivée",
       "Empêche Windows de mettre en veille les ports USB. Évite les micro-"
       "coupures de souris, clavier et casque en pleine partie.",
       "alimentation", "moyen", "sur",
       apply=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                   "2a737441-1930-4402-8d77-b2bebba308a3",
                   "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "0"),
              _cmd("powercfg", "/setdcvalueindex", "scheme_current",
                   "2a737441-1930-4402-8d77-b2bebba308a3",
                   "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "0"),
              _cmd("powercfg", "/setactive", "scheme_current")],
       revert=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                    "2a737441-1930-4402-8d77-b2bebba308a3",
                    "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "1"),
               _cmd("powercfg", "/setdcvalueindex", "scheme_current",
                    "2a737441-1930-4402-8d77-b2bebba308a3",
                    "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "1"),
               _cmd("powercfg", "/setactive", "scheme_current")],
       check=None, default_for=["fps", "latence", "equilibre"]),

    _t("pcie_aspm_off", "Gestion d'énergie PCI Express désactivée",
       "Désactive l'économie d'énergie des liens PCIe (ASPM). Gain quasi nul "
       "sur la plupart des machines récentes ; peut corriger de rares "
       "stutters liés aux transitions d'état du lien PCIe. Augmente la "
       "consommation au repos — sans objet sur iGPU.",
       "alimentation", "faible", "modere",
       apply=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                   "501a4d13-42af-4429-9fd1-a8218c268e20",
                   "ee12f906-d277-404b-b6da-e5fa1a576df5", "0"),
              _cmd("powercfg", "/setactive", "scheme_current")],
       revert=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                    "501a4d13-42af-4429-9fd1-a8218c268e20",
                    "ee12f906-d277-404b-b6da-e5fa1a576df5", "1"),
               _cmd("powercfg", "/setactive", "scheme_current")],
       check=None, default_for=[]),

    _t("power_throttling_off", "Power Throttling désactivé",
       "Désactive le bridage EcoQoS des processus en arrière-plan. Le jeu au "
       "premier plan n'est jamais bridé : utile surtout pour les applis de "
       "capture ou de stream en arrière-plan. Déconseillé sur petite config "
       "(2-4 cœurs) et sur portable : les tâches de fond consomment alors "
       "plus de CPU et de batterie.",
       "alimentation", "faible", "modere",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                   "PowerThrottlingOff", "dword", 1)],
       revert=[_reg_del("HKLM",
                        r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                        "PowerThrottlingOff")],
       check=_chk_reg("HKLM",
                      r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                      "PowerThrottlingOff", 1),
       default_for=["stream"]),

    _t("fast_startup_off", "Démarrage rapide désactivé",
       "Désactive le démarrage rapide (Hiberboot) qui garde un noyau « sale » "
       "entre les sessions. Un vrai redémarrage évite pilotes et états corrompus.",
       "alimentation", "faible", "sur",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                   "HiberbootEnabled", "dword", 0)],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                    "HiberbootEnabled", "dword", 1)],
       check=_chk_reg("HKLM",
                      r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
                      "HiberbootEnabled", 0),
       default_for=["equilibre", "stream"]),

    _t("cpu_min_state_100", "État processeur minimal à 100 %",
       "Force l'état processeur minimal à 100 % sur secteur. Sur les CPU "
       "récents (Speed Shift/HWP), la remontée en fréquence prend ~1 ms : "
       "gain quasi nul. Peut lisser le frametime sur de vieux CPU, mais "
       "augmente nettement chauffe et consommation — déconseillé sur "
       "portable et sur petite config limitée thermiquement.",
       "alimentation", "faible", "modere",
       apply=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                   "sub_processor", "procthrottlemin", "100"),
              _cmd("powercfg", "/setactive", "scheme_current")],
       revert=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                    "sub_processor", "procthrottlemin", "5"),
               _cmd("powercfg", "/setactive", "scheme_current")],
       check=None, default_for=["latence"]),

    # ------------------------------------------------------------------ #
    # Visuels & animations                                                #
    # ------------------------------------------------------------------ #
    _t("visualfx_performance", "Effets visuels : meilleures performances",
       "Règle les effets visuels de Windows sur « Ajuster afin d'obtenir les "
       "meilleures performances ». Libère CPU et GPU du superflu d'interface.",
       "visuels", "moyen", "sur",
       apply=[_reg("HKCU",
                   r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                   "VisualFXSetting", "dword", 2)],
       revert=[_reg("HKCU",
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                    "VisualFXSetting", "dword", 0)],
       check=_chk_reg("HKCU",
                      r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                      "VisualFXSetting", 2),
       default_for=["fps"], lowend=True),

    _t("window_animations_off", "Animations de fenêtres désactivées",
       "Supprime l'animation d'agrandissement/réduction des fenêtres. "
       "L'interface répond instantanément, utile en alt-tab pendant une partie.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", _DESKTOP + r"\WindowMetrics", "MinAnimate",
                   "string", "0")],
       revert=[_reg("HKCU", _DESKTOP + r"\WindowMetrics", "MinAnimate",
                    "string", "1")],
       check=_chk_reg("HKCU", _DESKTOP + r"\WindowMetrics", "MinAnimate", "0"),
       default_for=["fps", "latence"], lowend=True),

    _t("transparency_off", "Transparence désactivée",
       "Désactive les effets de transparence de Windows (barre des tâches, "
       "menus). Moins de travail de composition pour le GPU.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU",
                   r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                   "EnableTransparency", "dword", 0)],
       revert=[_reg("HKCU",
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                    "EnableTransparency", "dword", 1)],
       check=_chk_reg("HKCU",
                      r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                      "EnableTransparency", 0),
       default_for=["fps", "equilibre", "stream"], lowend=True),

    _t("menu_show_delay_0", "Délai d'ouverture des menus à 0",
       "Supprime le délai de 400 ms avant l'ouverture des menus Windows. "
       "L'interface paraît immédiatement plus réactive.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", _DESKTOP, "MenuShowDelay", "string", "0")],
       revert=[_reg("HKCU", _DESKTOP, "MenuShowDelay", "string", "400")],
       check=_chk_reg("HKCU", _DESKTOP, "MenuShowDelay", "0"),
       default_for=["fps", "latence", "equilibre"]),

    _t("taskbar_animations_off", "Animations de la barre des tâches désactivées",
       "Coupe les animations de la barre des tâches et du menu Démarrer. "
       "Un peu moins de composition DWM en arrière-plan.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", _ADVANCED, "TaskbarAnimations", "dword", 0)],
       revert=[_reg("HKCU", _ADVANCED, "TaskbarAnimations", "dword", 1)],
       check=_chk_reg("HKCU", _ADVANCED, "TaskbarAnimations", 0),
       default_for=["fps"], lowend=True),

    _t("listview_alpha_select_off", "Rectangle de sélection translucide désactivé",
       "Remplace le rectangle de sélection translucide de l'Explorateur par un "
       "simple contour. Micro-gain de rendu sur le bureau.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", _ADVANCED, "ListviewAlphaSelect", "dword", 0)],
       revert=[_reg("HKCU", _ADVANCED, "ListviewAlphaSelect", "dword", 1)],
       check=_chk_reg("HKCU", _ADVANCED, "ListviewAlphaSelect", 0),
       default_for=["fps"]),

    _t("listview_shadow_off", "Ombres des libellés d'icônes désactivées",
       "Supprime l'ombre portée sous les textes d'icônes du bureau. "
       "Allège légèrement le rendu de l'Explorateur.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", _ADVANCED, "ListviewShadow", "dword", 0)],
       revert=[_reg("HKCU", _ADVANCED, "ListviewShadow", "dword", 1)],
       check=_chk_reg("HKCU", _ADVANCED, "ListviewShadow", 0),
       default_for=["fps"]),

    _t("drag_full_windows_off", "Contenu des fenêtres masqué au déplacement",
       "N'affiche plus le contenu des fenêtres pendant leur déplacement. "
       "Réduit le travail de rendu lors des manipulations de fenêtres.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", _DESKTOP, "DragFullWindows", "string", "0")],
       revert=[_reg("HKCU", _DESKTOP, "DragFullWindows", "string", "1")],
       check=_chk_reg("HKCU", _DESKTOP, "DragFullWindows", "0"),
       default_for=["fps"]),

    _t("user_preferences_mask_perf", "Masque de préférences : performances",
       "Applique le masque UserPreferencesMask orienté performances : coupe "
       "fondus, ombres du pointeur et animations résiduelles d'un seul coup.",
       "visuels", "moyen", "modere",
       apply=[_reg("HKCU", _DESKTOP, "UserPreferencesMask", "binary",
                   "9012038010000000")],
       revert=[_reg("HKCU", _DESKTOP, "UserPreferencesMask", "binary",
                    "9e3e078012000000")],
       check=_chk_reg("HKCU", _DESKTOP, "UserPreferencesMask",
                      "9012038010000000"),
       default_for=["fps"], lowend=True),

    _t("aero_peek_off", "Aero Peek désactivé",
       "Désactive l'aperçu du bureau Aero Peek. Effet sur les performances "
       "quasi nul : Peek ne se déclenche qu'au survol du coin de la barre "
       "des tâches, jamais pendant une partie. À cocher par cohérence avec "
       "un profil « toutes animations désactivées ».",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek",
                   "dword", 0)],
       revert=[_reg("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek",
                    "dword", 1)],
       check=_chk_reg("HKCU", r"Software\Microsoft\Windows\DWM",
                      "EnableAeroPeek", 0),
       default_for=[]),

    # ------------------------------------------------------------------ #
    # Jeux                                                                #
    # ------------------------------------------------------------------ #
    _t("game_mode_on", "Mode Jeu activé",
       "S'assure que le Mode Jeu de Windows est actif (il l'est par défaut "
       "depuis 2017). Bloque l'activité de Windows Update et les "
       "notifications pendant la partie ; l'effet « priorité GPU » reste "
       "marginal. Utile uniquement s'il avait été désactivé.",
       "jeux", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode",
                   "dword", 1),
              _reg("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled",
                   "dword", 1)],
       revert=[_reg_del("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode"),
               _reg_del("HKCU", r"Software\Microsoft\GameBar",
                        "AutoGameModeEnabled")],
       check=_chk_reg("HKCU", r"Software\Microsoft\GameBar",
                      "AllowAutoGameMode", 1),
       default_for=["fps", "latence", "equilibre", "stream"], lowend=True),

    _t("gamedvr_off", "Enregistrement Game DVR désactivé",
       "Coupe la capture Xbox Game DVR (clips automatiques et hooks de "
       "capture). Gain important si l'enregistrement en arrière-plan était "
       "actif ; sinon, supprime surtout les hooks et l'activité résiduelle "
       "de la Game Bar. OBS reste le bon outil pour capturer.",
       "jeux", "moyen", "sur",
       apply=[_reg("HKCU", _GCS, "GameDVR_Enabled", "dword", 0),
              _reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                   "AppCaptureEnabled", "dword", 0)],
       revert=[_reg("HKCU", _GCS, "GameDVR_Enabled", "dword", 1),
               _reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                    "AppCaptureEnabled", "dword", 1)],
       check=_chk_reg("HKCU", _GCS, "GameDVR_Enabled", 0),
       default_for=["fps", "latence", "equilibre", "stream"], lowend=True),

    _t("gamedvr_policy_off", "Game DVR interdit (stratégie machine)",
       "Interdit Game DVR par stratégie machine (HKLM), pour tous les "
       "comptes du PC. N'apporte rien de plus que le réglage utilisateur sur "
       "un PC mono-compte et verrouille la capture Game Bar pour tout le "
       "monde : à réserver aux machines multi-comptes.",
       "jeux", "faible", "modere",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
                   "AllowGameDVR", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
                        "AllowGameDVR")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
                      "AllowGameDVR", 0),
       default_for=[]),

    _t("game_bar_off", "Xbox Game Bar en retrait",
       "Empêche la Game Bar de s'ouvrir via la touche/le bouton Xbox et coupe "
       "son panneau de démarrage. Évite un overlay inutile au-dessus du jeu.",
       "jeux", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\GameBar",
                   "UseNexusForGameBarEnabled", "dword", 0),
              _reg("HKCU", r"Software\Microsoft\GameBar", "ShowStartupPanel",
                   "dword", 0)],
       revert=[_reg("HKCU", r"Software\Microsoft\GameBar",
                    "UseNexusForGameBarEnabled", "dword", 1),
               _reg("HKCU", r"Software\Microsoft\GameBar", "ShowStartupPanel",
                    "dword", 1)],
       check=_chk_reg("HKCU", r"Software\Microsoft\GameBar",
                      "UseNexusForGameBarEnabled", 0),
       default_for=["fps", "latence", "equilibre"]),

    _t("hags_on", "Planification GPU accélérée (HAGS)",
       "Active la planification de GPU à accélération matérielle (HwSchMode=2). "
       "Réduit la latence de file GPU sur les cartes et pilotes récents. Redémarrage requis.",
       "jeux", "moyen", "modere",
       apply=[_reg("HKLM", _GFX, "HwSchMode", "dword", 2)],
       # La valeur est absente d'usine (choix OS/pilote) : la suppression rend
       # la main au défaut au lieu de forcer HAGS off sur Windows 11 récent.
       revert=[_reg_del("HKLM", _GFX, "HwSchMode")],
       check=_chk_reg("HKLM", _GFX, "HwSchMode", 2),
       default_for=["fps", "latence"]),

    _t("fse_optimizations_off", "Optimisations plein écran désactivées (global)",
       "Désactive globalement les « optimisations plein écran ». Tweak "
       "hérité de 2017 : sur les Windows 10/11 récents, le modèle de "
       "présentation a mûri et ces clés GameConfigStore ont un effet limité, "
       "voire nul. Peut encore aider quelques jeux anciens en plein écran "
       "exclusif ; sinon, préférez le réglage par jeu (onglet Compatibilité "
       "de l'exécutable).",
       "jeux", "faible", "modere",
       apply=[_reg("HKCU", _GCS, "GameDVR_FSEBehaviorMode", "dword", 2),
              _reg("HKCU", _GCS, "GameDVR_HonorUserFSEBehaviorMode", "dword", 1),
              _reg("HKCU", _GCS, "GameDVR_DXGIHonorFSEWindowsCompatible",
                   "dword", 1),
              _reg("HKCU", _GCS, "GameDVR_EFSEFeatureFlags", "dword", 0)],
       revert=[_reg("HKCU", _GCS, "GameDVR_FSEBehaviorMode", "dword", 0),
               _reg("HKCU", _GCS, "GameDVR_HonorUserFSEBehaviorMode", "dword", 0),
               _reg("HKCU", _GCS, "GameDVR_DXGIHonorFSEWindowsCompatible",
                    "dword", 0),
               _reg("HKCU", _GCS, "GameDVR_EFSEFeatureFlags", "dword", 0)],
       check=_chk_reg("HKCU", _GCS, "GameDVR_FSEBehaviorMode", 2),
       default_for=["latence"]),

    # ------------------------------------------------------------------ #
    # Système & CPU                                                       #
    # ------------------------------------------------------------------ #
    _t("sysmain_off", "Service SysMain (Superfetch) désactivé",
       "Arrête et désactive SysMain (Superfetch). Son cache occupe de la "
       "mémoire « en attente » rendue instantanément aux applications : le "
       "gain réel concerne surtout les HDD saturés par le préchargement. "
       "Déconseillé sur petite config : sa désactivation peut aussi couper "
       "la compression mémoire.",
       "systeme", "faible", "modere",
       apply=[_svc("SysMain", "disabled", stop=True)],
       revert=[_svc("SysMain", "auto")],
       check=_chk_svc("SysMain", "disabled"),
       default_for=[]),

    _t("startup_delay_off", "Délai de démarrage des applications supprimé",
       "Supprime le délai artificiel (StartupDelayInMSec) que Windows impose "
       "aux applications lancées au démarrage de la session.",
       "systeme", "faible", "sur",
       apply=[_reg("HKCU",
                   r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
                   "StartupDelayInMSec", "dword", 0)],
       revert=[_reg_del("HKCU",
                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
                        "StartupDelayInMSec")],
       check=_chk_reg("HKCU",
                      r"Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
                      "StartupDelayInMSec", 0),
       default_for=["fps", "equilibre"]),

    _t("svchost_split_threshold", "Regroupement des services (SvcHostSplit)",
       "Relève le seuil SvcHostSplit : les services Windows sont regroupés "
       "dans beaucoup moins de processus svchost.exe, comme avant Windows "
       "10 1703. Économise de l'ordre de 100 à 200 Mo de RAM — surtout "
       "utile sous 8 Go — au prix d'une isolation moindre (un service qui "
       "plante peut en entraîner d'autres). Redémarrage requis.",
       "systeme", "faible", "avance",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                   "SvcHostSplitThresholdInKB", "dword", 67108864)],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                    "SvcHostSplitThresholdInKB", "dword", 3670016)],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                      "SvcHostSplitThresholdInKB", 67108864),
       default_for=[], lowend=True),

    _t("timer_resolution_global", "Résolution du timer global (Win11)",
       "Windows 11 n'honore plus les demandes de timer haute résolution des "
       "processus en arrière-plan ; cette clé rétablit l'ancien comportement "
       "global (GlobalTimerResolutionRequests=1). Sans effet sur le jeu au "
       "premier plan, qui obtient déjà sa résolution — utile seulement à "
       "certains outils de fond (capture, limiteurs externes). Redémarrage "
       "requis.",
       "systeme", "faible", "avance",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel",
                   "GlobalTimerResolutionRequests", "dword", 1)],
       revert=[_reg_del("HKLM",
                        r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel",
                        "GlobalTimerResolutionRequests")],
       check=_chk_reg("HKLM",
                      r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel",
                      "GlobalTimerResolutionRequests", 1),
       default_for=[]),

    _t("wait_to_kill_services_2000", "Arrêt des services plus rapide",
       "Réduit le délai d'attente avant l'arrêt forcé des services (5000 → "
       "2000 ms). Extinctions et redémarrages du PC plus rapides.",
       "systeme", "faible", "sur",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                   "WaitToKillServiceTimeout", "string", "2000")],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                    "WaitToKillServiceTimeout", "string", "5000")],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                      "WaitToKillServiceTimeout", "2000"),
       default_for=["fps", "equilibre"]),

    _t("auto_end_tasks_on", "Fermeture automatique des tâches bloquées",
       "Ferme d'office les applications qui ne répondent plus à la "
       "déconnexion ou à l'extinction, sans fenêtre « Fermer quand même ? ». "
       "Attention : un document non enregistré dans une application bloquée "
       "peut être perdu à l'extinction.",
       "systeme", "faible", "modere",
       apply=[_reg("HKCU", _DESKTOP, "AutoEndTasks", "string", "1")],
       revert=[_reg_del("HKCU", _DESKTOP, "AutoEndTasks")],
       check=_chk_reg("HKCU", _DESKTOP, "AutoEndTasks", "1"),
       default_for=["equilibre"]),

    _t("onedrive_startup_off", "OneDrive coupé au démarrage",
       "Désactive le lancement automatique de OneDrive à l'ouverture de "
       "session (mécanisme StartupApproved, le même que le Gestionnaire des "
       "tâches). OneDrive reste installé et utilisable à la demande.",
       "systeme", "moyen", "sur",
       # Format StartupApproved : 12 octets, 1er octet pair = activé (02),
       # impair = désactivé (03). L'instantané original_values restaure
       # l'état réel de l'utilisateur au revert.
       apply=[_reg("HKCU",
                   r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                   "OneDrive", "binary", "030000000000000000000000")],
       revert=[_reg("HKCU",
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                    "OneDrive", "binary", "020000000000000000000000")],
       check=_chk_reg("HKCU",
                      r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
                      "OneDrive", "030000000000000000000000"),
       default_for=["petite_config"], lowend=True),

    _t("edge_preload_off", "Préchargement de Microsoft Edge désactivé",
       "Empêche Edge de se précharger à l'ouverture de session (Startup "
       "Boost) et de rester en tâche de fond une fois fermé. Libère RAM et "
       "CPU si Edge n'est pas votre navigateur principal.",
       "systeme", "moyen", "sur",
       # Défaut Windows : stratégie non configurée (valeurs absentes)
       # => revert = reg_delete.
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge",
                   "StartupBoostEnabled", "dword", 0),
              _reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge",
                   "BackgroundModeEnabled", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Edge",
                        "StartupBoostEnabled"),
               _reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Edge",
                        "BackgroundModeEnabled")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Edge",
                      "StartupBoostEnabled", 0),
       default_for=["petite_config"], lowend=True),

    _t("widgets_news_off", "Widgets et actualités désactivés",
       "Coupe les Widgets de Windows 11 (processus WebView2 permanents) et "
       "le flux « Actualités et champs d'intérêt » de Windows 10. Plusieurs "
       "centaines de Mo de RAM récupérés sur les petites configurations.",
       "systeme", "eleve", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Dsh",
                   "AllowNewsAndInterests", "dword", 0),
              _reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds",
                   "EnableFeeds", "dword", 0),
              _reg("HKCU", _ADVANCED, "TaskbarDa", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Dsh",
                        "AllowNewsAndInterests"),
               _reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds",
                        "EnableFeeds"),
               _reg("HKCU", _ADVANCED, "TaskbarDa", "dword", 1)],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Dsh",
                      "AllowNewsAndInterests", 0),
       default_for=["petite_config"], lowend=True),

    _t("defender_scan_lowprio", "Analyses Defender en arrière-plan allégées",
       "Limite le CPU que les analyses planifiées de Microsoft Defender "
       "peuvent consommer (50 % → 20 %) et les cantonne aux périodes "
       "d'inactivité. LA PROTECTION EN TEMPS RÉEL RESTE TOTALEMENT ACTIVE.",
       "systeme", "moyen", "sur",
       # Défauts usine : ScanAvgCPULoadFactor=50, ScanOnlyIfIdleEnabled=$true.
       # Conforme à la charte : on ne touche ni la protection temps réel ni
       # le cloud.
       apply=[_ps("Set-MpPreference -ScanAvgCPULoadFactor 20 "
                  "-ScanOnlyIfIdleEnabled $true")],
       revert=[_ps("Set-MpPreference -ScanAvgCPULoadFactor 50 "
                   "-ScanOnlyIfIdleEnabled $true")],
       check=None, default_for=["petite_config"], lowend=True),

    # ------------------------------------------------------------------ #
    # Mémoire                                                             #
    # ------------------------------------------------------------------ #
    _t("memory_compression_off", "Compression mémoire désactivée",
       "Désactive la compression mémoire : moins de cycles CPU dépensés "
       "quand la RAM est sollicitée. Réservé aux PC avec 16 Go ou plus — "
       "CONTRE-PRODUCTIF en dessous : la compression évite justement des "
       "accès disque (pagefile) quand la RAM manque.",
       "memoire", "faible", "modere",
       apply=[_ps("Disable-MMAgent -MemoryCompression")],
       revert=[_ps("Enable-MMAgent -MemoryCompression")],
       check=None, default_for=[]),

    _t("page_combining_off", "Combinaison de pages désactivée",
       "Désactive la déduplication des pages mémoire (PageCombining). Le "
       "coût CPU de cette tâche de fond est en pratique infime : gain quasi "
       "nul, à réserver aux machines avec beaucoup de RAM puisque la "
       "déduplication économise de la mémoire. Sans intérêt sur petite "
       "config.",
       "memoire", "faible", "avance",
       apply=[_ps("Disable-MMAgent -PageCombining")],
       revert=[_ps("Enable-MMAgent -PageCombining")],
       check=None, default_for=[]),

    _t("paging_executive_off", "Noyau maintenu en RAM",
       "DisablePagingExecutive=1 : garde le code noyau paginable en RAM. "
       "Gain imperceptible en jeu sur un SSD — c'est avant tout une aide au "
       "débogage de pilotes. À éviter sur les PC avec peu de RAM, où cette "
       "marge verrouillée manquera aux applications.",
       "memoire", "faible", "modere",
       apply=[_reg("HKLM", _MEMMGMT, "DisablePagingExecutive", "dword", 1)],
       revert=[_reg("HKLM", _MEMMGMT, "DisablePagingExecutive", "dword", 0)],
       check=_chk_reg("HKLM", _MEMMGMT, "DisablePagingExecutive", 1),
       default_for=[]),

    # ------------------------------------------------------------------ #
    # Réseau & latence                                                    #
    # ------------------------------------------------------------------ #
    _t("network_throttling_off", "Bridage réseau multimédia désactivé",
       "NetworkThrottlingIndex=0xFFFFFFFF : lève la limite de 10 paquets/ms "
       "que Windows applique pendant la lecture multimédia. Sans effet sur "
       "le ping en jeu — CS2 échange une centaine de paquets par seconde, "
       "cent fois sous la limite. Utile seulement pour des transferts "
       "dépassant ~100 Mbit/s pendant qu'un média joue.",
       "reseau", "faible", "sur",
       apply=[_reg("HKLM", _SYSPROF, "NetworkThrottlingIndex", "dword",
                   4294967295)],
       revert=[_reg("HKLM", _SYSPROF, "NetworkThrottlingIndex", "dword", 10)],
       check=_chk_reg("HKLM", _SYSPROF, "NetworkThrottlingIndex", 4294967295),
       default_for=[]),

    _t("system_responsiveness_0", "Réactivité système dédiée au jeu",
       "SystemResponsiveness=0 : le planificateur multimédia (MMCSS) ne "
       "réserve plus 20 % du CPU aux tâches ordinaires face aux threads "
       "multimédia enregistrés (audio du jeu notamment). Gain modeste, le "
       "plus sensible sur les CPU 2-4 cœurs saturés ; à éviter pendant un "
       "stream, l'encodeur en arrière-plan profite de cette réserve.",
       "reseau", "moyen", "sur",
       apply=[_reg("HKLM", _SYSPROF, "SystemResponsiveness", "dword", 0)],
       revert=[_reg("HKLM", _SYSPROF, "SystemResponsiveness", "dword", 20)],
       check=_chk_reg("HKLM", _SYSPROF, "SystemResponsiveness", 0),
       default_for=["fps", "latence", "equilibre"], lowend=True),

    _t("nagle_off", "Algorithme de Nagle désactivé",
       "Désactive l'algorithme de Nagle (TcpAckFrequency=1, TCPNoDelay=1) "
       "sur toutes les interfaces. Sans effet sur CS2, Valorant et la "
       "quasi-totalité des FPS en ligne, dont le trafic de jeu passe en "
       "UDP ; ne concerne que les rares jeux communiquant en TCP (certains "
       "MMO).",
       "reseau", "faible", "modere",
       apply=[_ps("Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { New-ItemProperty -Path $_.PSPath -Name 'TcpAckFrequency' -Value 1 -PropertyType DWord -Force | Out-Null; New-ItemProperty -Path $_.PSPath -Name 'TCPNoDelay' -Value 1 -PropertyType DWord -Force | Out-Null }")],
       revert=[_ps("Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { Remove-ItemProperty -Path $_.PSPath -Name 'TcpAckFrequency','TCPNoDelay' -ErrorAction SilentlyContinue }")],
       check=None, default_for=[]),

    _t("qos_reserve_0", "Réserve de bande passante QoS à 0 %",
       "Supprime la part de débit que le planificateur QoS peut réserver quand "
       "une application émet des flux QoS. Sans effet dans la plupart des cas "
       "(Windows ne réserve rien par défaut) ; inoffensif.",
       "reseau", "faible", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched",
                   "NonBestEffortLimit", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched",
                        "NonBestEffortLimit")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched",
                      "NonBestEffortLimit", 0),
       default_for=[]),

    _t("dns_cloudflare", "DNS Cloudflare (1.1.1.1)",
       "Bascule les DNS des cartes actives vers Cloudflare (1.1.1.1 / "
       "1.0.0.1). N'améliore pas le ping en jeu — la résolution de nom n'a "
       "lieu qu'au moment de la connexion au serveur — mais peut accélérer "
       "navigation et connexions initiales si les DNS du FAI sont lents. "
       "Remplace la configuration DNS existante.",
       "reseau", "faible", "modere",
       apply=[_ps("Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | Set-DnsClientServerAddress -ServerAddresses ('1.1.1.1','1.0.0.1')")],
       revert=[_ps("Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | Set-DnsClientServerAddress -ResetServerAddresses")],
       check=None, default_for=[]),

    _t("lso_off", "Large Send Offload désactivé",
       "Désactive le Large Send Offload : le découpage des paquets revient "
       "au CPU. Correctif hérité de l'époque des pilotes Realtek bogués ; "
       "sur un pilote sain, aucun gain mesurable et un surcroît de charge "
       "CPU — déconseillé sur petit CPU. À réserver au dépannage de latence "
       "réseau anormale.",
       "reseau", "faible", "avance",
       apply=[_ps("Disable-NetAdapterLso -Name '*'")],
       revert=[_ps("Enable-NetAdapterLso -Name '*'")],
       check=None, default_for=[]),

    _t("nic_power_saving_off", "Économie d'énergie des cartes réseau désactivée",
       "Empêche Windows d'éteindre la carte réseau pour économiser l'énergie. "
       "Évite déconnexions et pics de ping au réveil de la carte.",
       "reseau", "moyen", "sur",
       apply=[_ps("Get-NetAdapter -Physical | ForEach-Object { Disable-NetAdapterPowerManagement -Name $_.Name -ErrorAction SilentlyContinue }")],
       revert=[_ps("Get-NetAdapter -Physical | ForEach-Object { Enable-NetAdapterPowerManagement -Name $_.Name -ErrorAction SilentlyContinue }")],
       check=None, default_for=["latence", "equilibre", "stream"],
       lowend=True),

    _t("teredo_off", "Teredo désactivé",
       "Désactive le tunnel IPv6 Teredo, source de latence et de résolutions "
       "parasites. Attention : le chat de groupe Xbox/Game Pass peut en dépendre.",
       "reseau", "faible", "modere",
       apply=[_cmd("netsh", "interface", "teredo", "set", "state", "disabled")],
       revert=[_cmd("netsh", "interface", "teredo", "set", "state",
                    "type=default")],
       check=None, default_for=[]),

    _t("delivery_optimization_off", "Partage P2P des mises à jour désactivé",
       "DODownloadMode=0 : Windows Update télécharge en HTTP simple et "
       "n'envoie plus vos mises à jour à d'autres PC. Libère bande passante "
       "montante, disque et CPU — sensible sur petite connexion et petit "
       "CPU.",
       "reseau", "moyen", "sur",
       apply=[_reg("HKLM",
                   r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization",
                   "DODownloadMode", "dword", 0)],
       revert=[_reg_del("HKLM",
                        r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization",
                        "DODownloadMode")],
       check=_chk_reg("HKLM",
                      r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization",
                      "DODownloadMode", 0),
       default_for=["petite_config"], lowend=True),

    # ------------------------------------------------------------------ #
    # GPU                                                                 #
    # ------------------------------------------------------------------ #
    _t("games_task_gpu_priority", "Priorité CPU/IO des jeux (profil MMCSS)",
       "Relève le profil « Games » du planificateur multimédia (MMCSS). Ne "
       "concerne que les applications qui s'enregistrent explicitement sous "
       "ce profil — ce que très peu de jeux font réellement, et rien "
       "n'indique que CS2 en fasse partie : gain le plus souvent nul, "
       "réglage inoffensif.",
       "gpu", "faible", "sur",
       apply=[_reg("HKLM", _GAMES_TASK, "Priority", "dword", 6),
              _reg("HKLM", _GAMES_TASK, "Scheduling Category", "string", "High"),
              _reg("HKLM", _GAMES_TASK, "SFIO Priority", "string", "High")],
       revert=[_reg("HKLM", _GAMES_TASK, "Priority", "dword", 2),
               _reg("HKLM", _GAMES_TASK, "Scheduling Category", "string",
                    "Medium"),
               _reg("HKLM", _GAMES_TASK, "SFIO Priority", "string", "Normal")],
       check=_chk_reg("HKLM", _GAMES_TASK, "Priority", 6),
       default_for=[]),

    _t("tdr_delay_10", "Délai TDR porté à 10 s",
       "Laisse 10 s (au lieu de 2) au GPU pour répondre avant que Windows ne "
       "réinitialise le pilote. Évite des crashs « driver reset » sous forte charge.",
       "gpu", "faible", "avance",
       apply=[_reg("HKLM", _GFX, "TdrDelay", "dword", 10)],
       revert=[_reg_del("HKLM", _GFX, "TdrDelay")],
       check=_chk_reg("HKLM", _GFX, "TdrDelay", 10),
       default_for=[]),

    _t("mpo_off", "Multiplane Overlay désactivé",
       "Désactive le MPO du compositeur (OverlayTestMode=5), cause connue de "
       "scintillements et de stutter avec G-Sync/FreeSync sur certains pilotes.",
       "gpu", "moyen", "avance",
       apply=[_reg("HKLM", r"SOFTWARE\Microsoft\Windows\Dwm", "OverlayTestMode",
                   "dword", 5)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Microsoft\Windows\Dwm",
                        "OverlayTestMode")],
       check=_chk_reg("HKLM", r"SOFTWARE\Microsoft\Windows\Dwm",
                      "OverlayTestMode", 5),
       default_for=[]),

    _t("directx_swap_vrr_on", "Optimisations fenêtré + VRR DirectX",
       "Active les optimisations des jeux en mode fenêtré et du taux de "
       "rafraîchissement variable dans les préférences graphiques DirectX.",
       "gpu", "faible", "modere",
       # Lecture-modification-écriture : DirectXUserGlobalSettings est une
       # chaîne composite (Auto HDR y cohabite) — on ne touche que nos tokens.
       apply=[_ps("$p='HKCU:\\Software\\Microsoft\\DirectX\\UserGpuPreferences';"
                  " New-Item -Path $p -Force | Out-Null;"
                  " $v=(Get-ItemProperty -Path $p -Name DirectXUserGlobalSettings"
                  " -ErrorAction SilentlyContinue).DirectXUserGlobalSettings;"
                  " $parts=@(); if($v){$parts=@($v.Split(';') | Where-Object"
                  " {$_ -and $_ -notmatch"
                  " '^(SwapEffectUpgradeEnable|VRROptimizeEnable)='})};"
                  " $parts+='SwapEffectUpgradeEnable=1','VRROptimizeEnable=1';"
                  " Set-ItemProperty -Path $p -Name DirectXUserGlobalSettings"
                  " -Value (($parts -join ';')+';')")],
       revert=[_ps("$p='HKCU:\\Software\\Microsoft\\DirectX\\UserGpuPreferences';"
                   " $v=(Get-ItemProperty -Path $p -Name"
                   " DirectXUserGlobalSettings -ErrorAction SilentlyContinue"
                   ").DirectXUserGlobalSettings;"
                   " if($v){$parts=@($v.Split(';') | Where-Object"
                   " {$_ -and $_ -notmatch"
                   " '^(SwapEffectUpgradeEnable|VRROptimizeEnable)='});"
                   " if($parts.Count -gt 0){Set-ItemProperty -Path $p -Name"
                   " DirectXUserGlobalSettings -Value (($parts -join ';')+';')}"
                   " else {Remove-ItemProperty -Path $p -Name"
                   " DirectXUserGlobalSettings -ErrorAction SilentlyContinue}}")],
       check=None,
       default_for=["fps", "equilibre"], lowend=True),

    # ------------------------------------------------------------------ #
    # Stockage                                                            #
    # ------------------------------------------------------------------ #
    _t("trim_on", "TRIM SSD activé",
       "Garantit que le TRIM est actif (DisableDeleteNotify=0). Windows "
       "l'active déjà d'usine sur les SSD : ce réglage est une vérification "
       "de bon fonctionnement, pas un gain de performances.",
       "stockage", "faible", "sur",
       apply=[_cmd("fsutil", "behavior", "set", "DisableDeleteNotify", "0")],
       revert=[_cmd("fsutil", "behavior", "set", "DisableDeleteNotify", "0")],
       check=None, default_for=["fps", "latence", "equilibre", "stream"]),

    _t("ntfs_last_access_off", "Horodatage « dernier accès » NTFS désactivé",
       "NTFS n'écrit plus la date de dernier accès à chaque lecture. "
       "Windows le désactive déjà de lui-même sur la plupart des volumes "
       "(gestion système au-delà de 128 Go) : gain marginal, surtout utile "
       "sur un petit SSD système.",
       "stockage", "faible", "sur",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem",
                   "NtfsDisableLastAccessUpdate", "dword", 1)],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem",
                    "NtfsDisableLastAccessUpdate", "dword", 2147483650)],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem",
                      "NtfsDisableLastAccessUpdate", 1),
       default_for=["fps", "equilibre"]),

    _t("prefetcher_off", "Prefetch/Superfetch (registre) désactivés",
       "Coupe le Prefetch au niveau registre. Gain quasi nul sur SSD "
       "(Windows le neutralise déjà largement) et déconseillé sur HDD, où "
       "le préchargement accélère réellement démarrages et lancements "
       "d'applications.",
       "stockage", "faible", "avance",
       # EnableSuperfetch n'est plus lu par Windows 10/11 (SysMain pilote tout)
       # et n'existe pas d'usine : on ne touche que EnablePrefetcher.
       apply=[_reg("HKLM", _MEMMGMT + r"\PrefetchParameters", "EnablePrefetcher",
                   "dword", 0)],
       revert=[_reg("HKLM", _MEMMGMT + r"\PrefetchParameters", "EnablePrefetcher",
                    "dword", 3)],
       check=_chk_reg("HKLM", _MEMMGMT + r"\PrefetchParameters",
                      "EnablePrefetcher", 0),
       default_for=[]),

    _t("short_names_off", "Noms courts 8.3 désactivés",
       "Désactive la génération des noms de fichiers hérités 8.3 sur les "
       "nouveaux volumes : création de fichiers plus rapide dans les gros dossiers.",
       "stockage", "faible", "avance",
       apply=[_cmd("fsutil", "behavior", "set", "disable8dot3", "1")],
       revert=[_cmd("fsutil", "behavior", "set", "disable8dot3", "2")],
       check=None, default_for=[]),

    _t("scheduled_defrag_off", "Défragmentation planifiée désactivée",
       "Désactive la tâche planifiée d'optimisation des disques. Elle ne "
       "tourne qu'en période d'inactivité et assure le retrim des SSD : à "
       "couper seulement si vous optimisez manuellement, et déconseillé sur "
       "HDD où la fragmentation s'accumule.",
       "stockage", "faible", "modere",
       apply=[_cmd("schtasks", "/Change", "/TN",
                   r"\Microsoft\Windows\Defrag\ScheduledDefrag", "/Disable")],
       revert=[_cmd("schtasks", "/Change", "/TN",
                    r"\Microsoft\Windows\Defrag\ScheduledDefrag", "/Enable")],
       check=None, default_for=[]),

    _t("reserved_storage_off", "Stockage réservé de Windows désactivé",
       "Libère les ~7 Go que Windows réserve pour ses mises à jour (DISM). "
       "Précieux sur un petit SSD de 120/256 Go. Échoue proprement si une "
       "mise à jour est en cours ; les mises à jour futures redeviennent "
       "plus lentes si le disque est presque plein.",
       "stockage", "moyen", "modere",
       apply=[_cmd("dism", "/Online", "/Set-ReservedStorageState",
                   "/State:Disabled")],
       revert=[_cmd("dism", "/Online", "/Set-ReservedStorageState",
                    "/State:Enabled")],
       check=None, default_for=["petite_config"], lowend=True),

    # ------------------------------------------------------------------ #
    # Confidentialité & télémétrie                                        #
    # ------------------------------------------------------------------ #
    _t("telemetry_minimal", "Télémétrie réduite au minimum",
       "AllowTelemetry=0 (niveau Sécurité ; les éditions Famille/Pro retombent "
       "sur le niveau minimal « Requis »). Moins d'envois en tâche de fond.",
       "confidentialite", "moyen", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                   "AllowTelemetry", "dword", 0)],
       revert=[_reg_del("HKLM",
                        r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                        "AllowTelemetry")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                      "AllowTelemetry", 0),
       default_for=["fps", "latence", "equilibre", "stream"], lowend=True),

    _t("diagtrack_off", "Service de télémétrie (DiagTrack) désactivé",
       "Arrête et désactive « Expériences des utilisateurs connectés et "
       "télémétrie », qui collecte et téléverse des diagnostics en continu.",
       "confidentialite", "moyen", "sur",
       apply=[_svc("DiagTrack", "disabled", stop=True)],
       revert=[_svc("DiagTrack", "auto")],
       check=_chk_svc("DiagTrack", "disabled"),
       default_for=["fps", "latence", "equilibre", "stream"], lowend=True),

    _t("dmwappush_off", "Service de messages push WAP désactivé",
       "Désactive dmwappushservice, lié à la collecte de données. Le "
       "service est déjà en démarrage manuel et ne tourne presque jamais : "
       "gain nul, c'est un simple durcissement de confidentialité.",
       "confidentialite", "faible", "sur",
       apply=[_svc("dmwappushservice", "disabled", stop=True)],
       revert=[_svc("dmwappushservice", "manual")],
       check=_chk_svc("dmwappushservice", "disabled"),
       default_for=[]),

    _t("advertising_id_off", "Identifiant publicitaire désactivé",
       "Désactive l'identifiant publicitaire utilisé par les applications pour "
       "le ciblage. Aucune incidence sur le jeu, gain de confidentialité net.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                   "Enabled", "dword", 0)],
       revert=[_reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                    "Enabled", "dword", 1)],
       check=_chk_reg("HKCU",
                      r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                      "Enabled", 0),
       default_for=["equilibre", "stream"]),

    _t("content_suggestions_off", "Suggestions et publicités Windows désactivées",
       "Coupe les suggestions du menu Démarrer, les conseils et les mises en "
       "avant d'applications (ContentDeliveryManager). Moins de bruit et de fond.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKCU", _CDM, "SubscribedContent-338388Enabled", "dword", 0),
              _reg("HKCU", _CDM, "SubscribedContent-338389Enabled", "dword", 0),
              _reg("HKCU", _CDM, "SubscribedContent-310093Enabled", "dword", 0),
              _reg("HKCU", _CDM, "SystemPaneSuggestionsEnabled", "dword", 0),
              _reg("HKCU", _CDM, "SilentInstalledAppsEnabled", "dword", 0),
              _reg("HKCU", _CDM, "SoftLandingEnabled", "dword", 0)],
       revert=[_reg("HKCU", _CDM, "SubscribedContent-338388Enabled", "dword", 1),
               _reg("HKCU", _CDM, "SubscribedContent-338389Enabled", "dword", 1),
               _reg("HKCU", _CDM, "SubscribedContent-310093Enabled", "dword", 1),
               _reg("HKCU", _CDM, "SystemPaneSuggestionsEnabled", "dword", 1),
               _reg("HKCU", _CDM, "SilentInstalledAppsEnabled", "dword", 1),
               _reg("HKCU", _CDM, "SoftLandingEnabled", "dword", 1)],
       check=_chk_reg("HKCU", _CDM, "SystemPaneSuggestionsEnabled", 0),
       default_for=["fps", "equilibre", "stream"], lowend=True),

    _t("consumer_features_off", "Installation auto d'applications promues bloquée",
       "DisableWindowsConsumerFeatures=1 : bloque l'installation automatique "
       "d'applications sponsorisées. Stratégie pleinement honorée surtout "
       "sur les éditions Entreprise/Éducation ; sur Famille/Pro l'effet est "
       "partiel et les réglages ContentDeliveryManager font l'essentiel.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                   "DisableWindowsConsumerFeatures", "dword", 1)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                        "DisableWindowsConsumerFeatures")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                      "DisableWindowsConsumerFeatures", 1),
       default_for=["equilibre", "stream"]),

    _t("cortana_off", "Cortana désactivée",
       "Interdit Cortana via stratégie (AllowCortana=0) sur Windows 10 : "
       "moins d'activité résidente et de requêtes réseau. Sans effet sur "
       "Windows 11, où Cortana a été retirée du système.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                   "AllowCortana", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                        "AllowCortana")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                      "AllowCortana", 0),
       default_for=["fps", "equilibre"], lowend=True),

    _t("background_apps_off", "Applications en arrière-plan désactivées",
       "Empêche les applications du Microsoft Store de tourner en arrière-plan "
       "(GlobalUserDisabled=1). Libère CPU, RAM et réseau pendant le jeu.",
       "confidentialite", "moyen", "sur",
       apply=[_reg("HKCU",
                   r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
                   "GlobalUserDisabled", "dword", 1)],
       revert=[_reg("HKCU",
                    r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
                    "GlobalUserDisabled", "dword", 0)],
       check=_chk_reg("HKCU",
                      r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
                      "GlobalUserDisabled", 1),
       default_for=["fps", "latence", "equilibre"], lowend=True),

    _t("activity_feed_off", "Historique d'activités désactivé",
       "Coupe l'historique d'activités (EnableActivityFeed, "
       "PublishUserActivities, UploadUserActivities à 0). La "
       "synchronisation cloud de la Timeline a été abandonnée par "
       "Microsoft : c'est désormais un réglage de confidentialité, sans "
       "gain de performances.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System",
                   "EnableActivityFeed", "dword", 0),
              _reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System",
                   "PublishUserActivities", "dword", 0),
              _reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System",
                   "UploadUserActivities", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System",
                        "EnableActivityFeed"),
               _reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System",
                        "PublishUserActivities"),
               _reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System",
                        "UploadUserActivities")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\System",
                      "EnableActivityFeed", 0),
       default_for=["equilibre"]),

    _t("feedback_requests_off", "Demandes d'avis Windows désactivées",
       "NumberOfSIUFInPeriod=0 : Windows ne demande plus votre avis par "
       "notifications. Moins d'interruptions.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\Siuf\Rules",
                   "NumberOfSIUFInPeriod", "dword", 0)],
       revert=[_reg_del("HKCU", r"Software\Microsoft\Siuf\Rules",
                        "NumberOfSIUFInPeriod")],
       check=_chk_reg("HKCU", r"Software\Microsoft\Siuf\Rules",
                      "NumberOfSIUFInPeriod", 0),
       default_for=["equilibre"]),

    _t("tailored_experiences_off", "Expériences personnalisées désactivées",
       "Windows n'exploite plus les données de diagnostic pour personnaliser "
       "conseils et publicités (TailoredExperiences...=0).",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy",
                   "TailoredExperiencesWithDiagnosticDataEnabled", "dword", 0)],
       revert=[_reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy",
                    "TailoredExperiencesWithDiagnosticDataEnabled", "dword", 1)],
       check=_chk_reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy",
                      "TailoredExperiencesWithDiagnosticDataEnabled", 0),
       default_for=["equilibre"]),

    _t("copilot_off", "Copilot désactivé",
       "Désactive l'intégration Copilot de Windows 11 (stratégie "
       "utilisateur) et retire son bouton de la barre des tâches. Un "
       "processus WebView2 de moins en tâche de fond.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot",
                   "TurnOffWindowsCopilot", "dword", 1),
              _reg("HKCU", _ADVANCED, "ShowCopilotButton", "dword", 0)],
       revert=[_reg_del("HKCU",
                        r"Software\Policies\Microsoft\Windows\WindowsCopilot",
                        "TurnOffWindowsCopilot"),
               _reg("HKCU", _ADVANCED, "ShowCopilotButton", "dword", 1)],
       check=_chk_reg("HKCU", r"Software\Policies\Microsoft\Windows\WindowsCopilot",
                      "TurnOffWindowsCopilot", 1),
       default_for=["petite_config"], lowend=True),

    _t("search_web_suggestions_off", "Recherche Windows sans suggestions web",
       "La recherche du menu Démarrer n'interroge plus Bing : résultats "
       "locaux uniquement. Moins de RAM pour SearchHost et plus aucune "
       "requête réseau à chaque frappe.",
       "confidentialite", "moyen", "sur",
       # DisableSearchBoxSuggestions = clé supportée Win10 21H1+/Win11 ;
       # BingSearchEnabled = secours pour les anciens Windows 10.
       apply=[_reg("HKCU", r"Software\Policies\Microsoft\Windows\Explorer",
                   "DisableSearchBoxSuggestions", "dword", 1),
              _reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search",
                   "BingSearchEnabled", "dword", 0)],
       revert=[_reg_del("HKCU", r"Software\Policies\Microsoft\Windows\Explorer",
                        "DisableSearchBoxSuggestions"),
               _reg_del("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search",
                        "BingSearchEnabled")],
       check=_chk_reg("HKCU", r"Software\Policies\Microsoft\Windows\Explorer",
                      "DisableSearchBoxSuggestions", 1),
       default_for=["petite_config"], lowend=True),

    _t("clipboard_history_off", "Historique du presse-papiers désactivé",
       "Désactive l'historique du presse-papiers (Win+V) : Windows ne garde "
       "plus chaque copie en mémoire. Micro-gain de RAM et confidentialité "
       "accrue.",
       "confidentialite", "faible", "sur",
       # Défaut usine : valeur absente (fonction inactive tant que
       # l'utilisateur ne l'a pas activée).
       apply=[_reg("HKCU", r"Software\Microsoft\Clipboard",
                   "EnableClipboardHistory", "dword", 0)],
       revert=[_reg_del("HKCU", r"Software\Microsoft\Clipboard",
                        "EnableClipboardHistory")],
       check=_chk_reg("HKCU", r"Software\Microsoft\Clipboard",
                      "EnableClipboardHistory", 0),
       default_for=["petite_config"], lowend=True),

    _t("lockscreen_tips_off", "Conseils de l'écran de verrouillage désactivés",
       "Coupe les anecdotes, conseils et promotions de l'écran de "
       "verrouillage (Spotlight overlay) et leurs téléchargements en "
       "arrière-plan. Les fonds d'écran Windows à la une restent "
       "fonctionnels.",
       "confidentialite", "faible", "sur",
       # Complète content_suggestions_off (338388/338389/310093) sans doublon.
       apply=[_reg("HKCU", _CDM, "RotatingLockScreenOverlayEnabled", "dword", 0),
              _reg("HKCU", _CDM, "SubscribedContent-338387Enabled", "dword", 0)],
       revert=[_reg("HKCU", _CDM, "RotatingLockScreenOverlayEnabled", "dword", 1),
               _reg("HKCU", _CDM, "SubscribedContent-338387Enabled", "dword", 1)],
       check=_chk_reg("HKCU", _CDM, "RotatingLockScreenOverlayEnabled", 0),
       default_for=["petite_config"], lowend=True),

    # ------------------------------------------------------------------ #
    # Services Windows                                                    #
    # ------------------------------------------------------------------ #
    _t("svc_fax_off", "Service Fax désactivé",
       "Désactive le service Fax. Il est déjà en démarrage manuel et ne "
       "tourne jamais sur un PC moderne : gain nul, simple durcissement "
       "pour réduire la surface du système.",
       "services", "faible", "sur",
       apply=[_svc("Fax", "disabled", stop=True)],
       revert=[_svc("Fax", "manual")],
       check=_chk_svc("Fax", "disabled"),
       default_for=[]),

    _t("svc_spooler_off", "Spouleur d'impression désactivé",
       "Désactive le spouleur d'impression : IMPRESSION IMPOSSIBLE tant que ce "
       "tweak est actif. À réserver aux PC sans imprimante.",
       "services", "faible", "modere",
       apply=[_svc("Spooler", "disabled", stop=True)],
       revert=[_svc("Spooler", "auto")],
       check=_chk_svc("Spooler", "disabled"),
       default_for=[]),

    _t("svc_wsearch_off", "Indexation Windows Search désactivée",
       "Désactive le service d'indexation WSearch : la recherche de fichiers "
       "devient plus lente, mais le disque et le CPU respirent pendant le jeu.",
       "services", "moyen", "modere",
       apply=[_svc("WSearch", "disabled", stop=True)],
       revert=[_svc("WSearch", "delayed-auto")],
       check=_chk_svc("WSearch", "disabled"),
       default_for=["fps"], lowend=True),

    _t("svc_xbox_off", "Services Xbox désactivés",
       "Désactive XblAuthManager, XblGameSave et XboxNetApiSvc. Ces "
       "services sont en démarrage manuel et ne tournent que si l'app "
       "Xbox/Game Pass est utilisée : gain quasi nul si vous ne l'utilisez "
       "pas, et connexion Xbox/sauvegardes cloud cassées si vous "
       "l'utilisez.",
       "services", "faible", "modere",
       apply=[_svc("XblAuthManager", "disabled", stop=True),
              _svc("XblGameSave", "disabled", stop=True),
              _svc("XboxNetApiSvc", "disabled", stop=True)],
       revert=[_svc("XblAuthManager", "manual"),
               _svc("XblGameSave", "manual"),
               _svc("XboxNetApiSvc", "manual")],
       check=_chk_svc("XblAuthManager", "disabled"),
       default_for=[]),

    _t("svc_mapsbroker_off", "Gestionnaire de cartes désactivé",
       "Désactive MapsBroker (cartes hors connexion). En démarrage "
       "automatique différé sur Windows 10 (petit gain au démarrage de "
       "session), déjà en manuel sur Windows 11 : gain minime dans tous "
       "les cas.",
       "services", "faible", "sur",
       apply=[_svc("MapsBroker", "disabled", stop=True)],
       revert=[_svc("MapsBroker", "delayed-auto")],
       check=_chk_svc("MapsBroker", "disabled"),
       default_for=["fps", "equilibre"]),

    _t("svc_remote_registry_off", "Registre à distance désactivé",
       "Garantit que RemoteRegistry reste sur Désactivé (c'est déjà le réglage "
       "d'usine de Windows 10/11). Durcissement sans impact en jeu.",
       "services", "faible", "sur",
       apply=[_svc("RemoteRegistry", "disabled", stop=True)],
       revert=[_svc("RemoteRegistry", "disabled")],
       check=_chk_svc("RemoteRegistry", "disabled"),
       default_for=[]),

    _t("svc_wersvc_off", "Rapport d'erreurs Windows désactivé",
       "Désactive WerSvc : plus de collecte ni d'envoi de rapports de plantage. "
       "Complique le diagnostic d'un crash récurrent, d'où le niveau avancé.",
       "services", "faible", "avance",
       apply=[_svc("WerSvc", "disabled", stop=True)],
       revert=[_svc("WerSvc", "manual")],
       check=_chk_svc("WerSvc", "disabled"),
       default_for=[]),

    _t("svc_wmpnetwork_off", "Partage réseau Windows Media désactivé",
       "Désactive WMPNetworkSvc (partage de bibliothèques Windows Media en "
       "réseau). Le service est en manuel et souvent absent des "
       "installations récentes : gain nul, pur nettoyage d'héritage.",
       "services", "faible", "sur",
       apply=[_svc("WMPNetworkSvc", "disabled", stop=True)],
       revert=[_svc("WMPNetworkSvc", "manual")],
       check=_chk_svc("WMPNetworkSvc", "disabled"),
       default_for=[]),

    # ------------------------------------------------------------------ #
    # Souris & périphériques                                              #
    # ------------------------------------------------------------------ #
    _t("mouse_accel_off", "Précision du pointeur améliorée désactivée",
       "Désactive l'accélération souris de Windows (MouseSpeed/Threshold à "
       "0) : le même geste produit toujours le même déplacement sur le "
       "bureau et dans les jeux sans Raw Input. CS2 et la plupart des FPS "
       "récents lisent la souris en Raw Input et l'ignorent déjà en jeu — "
       "ce réglage sert d'assurance de cohérence.",
       "peripheriques", "moyen", "sur",
       apply=[_reg("HKCU", _MOUSE, "MouseSpeed", "string", "0"),
              _reg("HKCU", _MOUSE, "MouseThreshold1", "string", "0"),
              _reg("HKCU", _MOUSE, "MouseThreshold2", "string", "0")],
       revert=[_reg("HKCU", _MOUSE, "MouseSpeed", "string", "1"),
               _reg("HKCU", _MOUSE, "MouseThreshold1", "string", "6"),
               _reg("HKCU", _MOUSE, "MouseThreshold2", "string", "10")],
       check=_chk_reg("HKCU", _MOUSE, "MouseSpeed", "0"),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("mouse_hover_time_10", "Délai de survol souris réduit",
       "Réduit MouseHoverTime de 400 à 10 ms : infobulles et aperçus "
       "réagissent immédiatement au survol. Confort de bureau uniquement — "
       "aucun effet sur la latence en jeu.",
       "peripheriques", "faible", "sur",
       apply=[_reg("HKCU", _MOUSE, "MouseHoverTime", "string", "10")],
       revert=[_reg("HKCU", _MOUSE, "MouseHoverTime", "string", "400")],
       check=_chk_reg("HKCU", _MOUSE, "MouseHoverTime", "10"),
       default_for=[]),

    _t("keyboard_delay_0", "Délai de répétition clavier minimal",
       "Règle le délai avant répétition d'une touche maintenue au minimum "
       "(KeyboardDelay=0). Confort de frappe et d'édition uniquement : les "
       "jeux lisent l'état des touches directement et ignorent la "
       "répétition clavier.",
       "peripheriques", "faible", "sur",
       apply=[_reg("HKCU", r"Control Panel\Keyboard", "KeyboardDelay",
                   "string", "0")],
       revert=[_reg("HKCU", r"Control Panel\Keyboard", "KeyboardDelay",
                    "string", "1")],
       check=_chk_reg("HKCU", r"Control Panel\Keyboard", "KeyboardDelay", "0"),
       default_for=[]),

    _t("sticky_keys_off", "Touches rémanentes désactivées",
       "Désactive le raccourci des touches rémanentes (5 × Maj) qui interrompt "
       "le jeu en pleine action (Flags=506).",
       "peripheriques", "faible", "sur",
       apply=[_reg("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags",
                   "string", "506")],
       revert=[_reg("HKCU", r"Control Panel\Accessibility\StickyKeys", "Flags",
                    "string", "510")],
       check=_chk_reg("HKCU", r"Control Panel\Accessibility\StickyKeys",
                      "Flags", "506"),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("toggle_keys_off", "Touches bascules silencieuses",
       "Désactive le bip et le raccourci des touches bascules (Verr Num "
       "maintenue 5 s) — Flags=58.",
       "peripheriques", "faible", "sur",
       apply=[_reg("HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags",
                   "string", "58")],
       revert=[_reg("HKCU", r"Control Panel\Accessibility\ToggleKeys", "Flags",
                    "string", "62")],
       check=_chk_reg("HKCU", r"Control Panel\Accessibility\ToggleKeys",
                      "Flags", "58"),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("filter_keys_off", "Touches filtres désactivées",
       "Désactive le raccourci des touches filtres (Maj droite 8 s) qui peut "
       "geler le clavier en jeu (Flags=122).",
       "peripheriques", "faible", "sur",
       apply=[_reg("HKCU", r"Control Panel\Accessibility\Keyboard Response",
                   "Flags", "string", "122")],
       revert=[_reg("HKCU", r"Control Panel\Accessibility\Keyboard Response",
                    "Flags", "string", "126")],
       check=_chk_reg("HKCU", r"Control Panel\Accessibility\Keyboard Response",
                      "Flags", "122"),
       default_for=["fps", "latence", "equilibre", "stream"]),
]

# ---------------------------------------------------------------------------
# i18n — champs anglais additifs (« label_en », « name_en », « description_en »).
# Les tables ci-dessous sont injectées dans CATEGORIES et TWEAKS au chargement
# du module, sans modifier aucune valeur existante du catalogue.
# ---------------------------------------------------------------------------

_CATEGORY_LABELS_EN: dict[str, str] = {
    "alimentation": "Power",
    "visuels": "Visuals & animations",
    "jeux": "Gaming",
    "systeme": "System & CPU",
    "memoire": "Memory",
    "reseau": "Network & latency",
    "gpu": "GPU",
    "stockage": "Storage",
    "confidentialite": "Privacy & telemetry",
    "services": "Windows services",
    "peripheriques": "Mouse & peripherals",
}

# {id du tweak: (name_en, description_en)}
_TWEAKS_EN: dict[str, tuple[str, str]] = {
    "power_plan_ultimate": (
        "Ultimate Performance power plan",
        "Enables the hidden Ultimate Performance power plan, removing "
        "fine-grained power saving. Modest gain on modern CPUs (slightly "
        "steadier frametimes); raises power draw and heat — use with care "
        "on thermally limited laptops.",
    ),
    "hibernation_off": (
        "Disable hibernation",
        "Disables hibernation and removes hiberfil.sys, reclaiming several "
        "GB. No FPS effect: this is a disk-space tweak, valuable on small "
        "SSDs. You lose hibernate (and Fast Startup).",
    ),
    "usb_selective_suspend_off": (
        "USB selective suspend disabled",
        "Stops Windows from putting USB ports to sleep. Prevents micro-dropouts "
        "from your mouse, keyboard or headset in the middle of a match.",
    ),
    "pcie_aspm_off": (
        "PCI Express power management disabled",
        "Disables PCIe link power management (ASPM). Near-zero gain on most "
        "modern machines; can fix rare stutter tied to PCIe link state "
        "transitions. Raises idle power draw — irrelevant on iGPUs.",
    ),
    "power_throttling_off": (
        "Power Throttling disabled",
        "Disables EcoQoS power throttling of background processes. The "
        "foreground game is never throttled: mainly useful for background "
        "capture or streaming apps. Not recommended on small configs (2-4 "
        "cores) or laptops: background tasks then consume more CPU and "
        "battery.",
    ),
    "fast_startup_off": (
        "Fast startup disabled",
        "Disables fast startup (Hiberboot), which carries a “dirty” kernel over "
        "between sessions. A true reboot avoids corrupted drivers and states.",
    ),
    "cpu_min_state_100": (
        "Minimum processor state at 100%",
        "Forces the minimum processor state to 100% on AC power. On modern "
        "CPUs (Speed Shift/HWP) frequency ramp-up takes about 1 ms, so the "
        "gain is near zero. May smooth frametimes on old CPUs, but clearly "
        "increases heat and power draw — not recommended on laptops or "
        "thermally limited small configs.",
    ),
    "visualfx_performance": (
        "Visual effects: best performance",
        "Sets Windows visual effects to “Adjust for best performance”. Frees "
        "the CPU and GPU from interface eye candy.",
    ),
    "window_animations_off": (
        "Window animations disabled",
        "Removes the minimize/maximize window animation. The interface responds "
        "instantly — useful when alt-tabbing mid-game.",
    ),
    "transparency_off": (
        "Transparency disabled",
        "Turns off Windows transparency effects (taskbar, menus). Less "
        "compositing work for the GPU.",
    ),
    "menu_show_delay_0": (
        "Menu open delay set to 0",
        "Removes the 400 ms delay before Windows menus open. The interface "
        "immediately feels snappier.",
    ),
    "taskbar_animations_off": (
        "Taskbar animations disabled",
        "Cuts taskbar and Start menu animations. A little less DWM compositing "
        "in the background.",
    ),
    "listview_alpha_select_off": (
        "Translucent selection rectangle disabled",
        "Replaces Explorer's translucent selection rectangle with a simple "
        "outline. A micro rendering gain on the desktop.",
    ),
    "listview_shadow_off": (
        "Icon label shadows disabled",
        "Removes the drop shadow under desktop icon labels. Slightly lightens "
        "Explorer rendering.",
    ),
    "drag_full_windows_off": (
        "Window contents hidden while dragging",
        "No longer draws window contents while they are being moved. Reduces "
        "rendering work when handling windows.",
    ),
    "user_preferences_mask_perf": (
        "Preferences mask: performance",
        "Applies the performance-oriented UserPreferencesMask: cuts fades, "
        "pointer shadows and leftover animations in one go.",
    ),
    "aero_peek_off": (
        "Aero Peek disabled",
        "Disables the Aero Peek desktop preview. Performance effect is near "
        "zero: Peek only triggers when hovering the taskbar corner, never "
        "while a game is running. Tick it for consistency with an 'all "
        "animations off' profile.",
    ),
    "game_mode_on": (
        "Game Mode enabled",
        "Makes sure Windows Game Mode is on (it has been the default since "
        "2017). Blocks Windows Update activity and notifications during "
        "play; the 'GPU priority' effect is marginal. Only useful if it had "
        "been turned off.",
    ),
    "gamedvr_off": (
        "Game DVR recording disabled",
        "Turns off Xbox Game DVR capture (automatic clips and capture "
        "hooks). Big win if background recording was enabled; otherwise it "
        "mainly removes Game Bar capture hooks and residual activity. OBS "
        "remains the right tool for recording.",
    ),
    "gamedvr_policy_off": (
        "Game DVR blocked (machine policy)",
        "Blocks Game DVR via machine policy (HKLM) for every account on the "
        "PC. Adds nothing over the per-user setting on a single-user PC and "
        "locks Game Bar capture for everyone: reserve it for multi-account "
        "machines.",
    ),
    "game_bar_off": (
        "Xbox Game Bar out of the way",
        "Stops the Game Bar from opening via the Xbox key/button and disables "
        "its startup panel. Avoids a useless overlay on top of your game.",
    ),
    "hags_on": (
        "Hardware-accelerated GPU scheduling (HAGS)",
        "Enables hardware-accelerated GPU scheduling (HwSchMode=2). Reduces GPU "
        "queue latency on recent cards and drivers. Reboot required.",
    ),
    "fse_optimizations_off": (
        "Fullscreen optimizations disabled (global)",
        "Globally disables Fullscreen Optimizations. A 2017-era tweak: on "
        "recent Windows 10/11 builds the presentation model has matured and "
        "these GameConfigStore keys have limited or no effect. May still "
        "help a few older games in exclusive fullscreen; otherwise prefer "
        "the per-game setting (the executable's Compatibility tab).",
    ),
    "sysmain_off": (
        "SysMain (Superfetch) service disabled",
        "Stops and disables SysMain (Superfetch). Its cache lives in "
        "standby memory that is handed back to applications instantly: the "
        "real benefit is mostly on HDDs thrashed by preloading. Not "
        "recommended on low-end PCs: disabling it can also turn off memory "
        "compression.",
    ),
    "startup_delay_off": (
        "App startup delay removed",
        "Removes the artificial delay (StartupDelayInMSec) that Windows imposes "
        "on applications launched at sign-in.",
    ),
    "svchost_split_threshold": (
        "Service grouping (SvcHostSplit)",
        "Raises the SvcHostSplit threshold so Windows services are grouped "
        "into far fewer svchost.exe processes, as before Windows 10 1703. "
        "Saves roughly 100-200 MB of RAM — most useful below 8 GB — at the "
        "cost of weaker isolation (one crashing service can take others "
        "down). Reboot required.",
    ),
    "timer_resolution_global": (
        "Global timer resolution (Win11)",
        "Windows 11 no longer honors high-resolution timer requests from "
        "background processes; this key restores the old global behavior "
        "(GlobalTimerResolutionRequests=1). No effect on the foreground "
        "game, which already gets its requested resolution — only helps "
        "certain background tools (capture, external limiters). Reboot "
        "required.",
    ),
    "wait_to_kill_services_2000": (
        "Faster service shutdown",
        "Reduces the wait before services are force-stopped (5000 → 2000 ms). "
        "Faster PC shutdowns and restarts.",
    ),
    "auto_end_tasks_on": (
        "Hung tasks closed automatically",
        "Force-closes applications that stop responding at sign-out or "
        "shutdown, skipping the 'Close anyway?' prompt. Warning: unsaved "
        "work in a hung application can be lost at shutdown.",
    ),
    "memory_compression_off": (
        "Memory compression disabled",
        "Disables memory compression: fewer CPU cycles spent when RAM is "
        "under pressure. For PCs with 16 GB or more only — COUNTERPRODUCTIVE "
        "below that: compression is precisely what avoids disk paging when "
        "RAM runs short.",
    ),
    "page_combining_off": (
        "Page combining disabled",
        "Disables memory page deduplication (PageCombining). The CPU cost "
        "of this background task is tiny in practice: near-zero gain, only "
        "for machines with plenty of RAM since deduplication saves memory. "
        "Pointless on low-end PCs.",
    ),
    "paging_executive_off": (
        "Kernel kept in RAM",
        "DisablePagingExecutive=1: keeps pageable kernel code resident in "
        "RAM. Imperceptible in-game gain on an SSD — it is primarily a "
        "driver-debugging aid. Avoid on low-RAM PCs, where that locked "
        "headroom is taken away from applications.",
    ),
    "network_throttling_off": (
        "Multimedia network throttling disabled",
        "NetworkThrottlingIndex=0xFFFFFFFF: lifts the 10 packets/ms cap "
        "Windows applies while multimedia is playing. No effect on in-game "
        "ping — CS2 exchanges about a hundred packets per second, a hundred "
        "times below the cap. Only matters for transfers above ~100 Mbit/s "
        "while media is playing.",
    ),
    "system_responsiveness_0": (
        "System responsiveness dedicated to gaming",
        "SystemResponsiveness=0: the multimedia scheduler (MMCSS) stops "
        "reserving 20% of the CPU for regular tasks against registered "
        "multimedia threads (notably game audio). Modest gain, most "
        "noticeable on saturated 2-4 core CPUs; avoid while streaming, as "
        "the background encoder benefits from that reserve.",
    ),
    "nagle_off": (
        "Nagle's algorithm disabled",
        "Disables Nagle's algorithm (TcpAckFrequency=1, TCPNoDelay=1) on "
        "all interfaces. Has no effect on CS2, Valorant and virtually every "
        "online FPS, whose game traffic runs over UDP; only matters for the "
        "few TCP-based games (some MMOs).",
    ),
    "qos_reserve_0": (
        "QoS bandwidth reserve at 0%",
        "Removes the share of bandwidth the QoS scheduler may reserve when an "
        "application emits QoS flows. No effect in most cases (Windows "
        "reserves nothing by default); harmless.",
    ),
    "dns_cloudflare": (
        "Cloudflare DNS (1.1.1.1)",
        "Switches active adapters' DNS to Cloudflare (1.1.1.1 / 1.0.0.1). "
        "Does not improve in-game ping — name resolution only happens when "
        "connecting to the server — but can speed up browsing and initial "
        "connections when the ISP's DNS is slow. Replaces the existing DNS "
        "configuration.",
    ),
    "lso_off": (
        "Large Send Offload disabled",
        "Disables Large Send Offload, moving packet segmentation back to "
        "the CPU. A fix inherited from the buggy Realtek driver era; on a "
        "healthy driver it brings no measurable gain and adds CPU load — "
        "not recommended on weak CPUs. Reserve it for troubleshooting "
        "abnormal network latency.",
    ),
    "nic_power_saving_off": (
        "Network adapter power saving disabled",
        "Stops Windows from powering down the network adapter to save energy. "
        "Avoids disconnects and ping spikes when the adapter wakes up.",
    ),
    "teredo_off": (
        "Teredo disabled",
        "Disables the Teredo IPv6 tunnel, a source of latency and stray "
        "lookups. Beware: Xbox/Game Pass party chat may depend on it.",
    ),
    "games_task_gpu_priority": (
        "Game CPU/IO priority (MMCSS profile)",
        "Raises the multimedia scheduler's (MMCSS) 'Games' profile. Only "
        "affects applications that explicitly register under this profile — "
        "which very few games actually do, and there is no indication CS2 "
        "is one of them: the gain is usually nil, the setting itself "
        "harmless.",
    ),
    "tdr_delay_10": (
        "TDR delay raised to 10 s",
        "Gives the GPU 10 s (instead of 2) to respond before Windows resets the "
        "driver. Avoids “driver reset” crashes under heavy load.",
    ),
    "mpo_off": (
        "Multiplane Overlay disabled",
        "Disables the compositor's MPO (OverlayTestMode=5), a known cause of "
        "flicker and stutter with G-Sync/FreeSync on some drivers.",
    ),
    "directx_swap_vrr_on": (
        "DirectX windowed + VRR optimizations",
        "Enables optimizations for windowed games and variable refresh rate in "
        "the DirectX graphics preferences.",
    ),
    "trim_on": (
        "SSD TRIM enabled",
        "Ensures TRIM is active (DisableDeleteNotify=0). Windows already "
        "enables it out of the box on SSDs: this is a health check, not a "
        "performance gain.",
    ),
    "ntfs_last_access_off": (
        "NTFS “last access” timestamp disabled",
        "NTFS stops writing the last-access date on every read. Windows "
        "already disables it by itself on most volumes (system-managed "
        "above 128 GB): a marginal gain, mostly useful on a small system "
        "SSD.",
    ),
    "prefetcher_off": (
        "Prefetch/Superfetch (registry) disabled",
        "Shuts off Prefetch at the registry level. Near-zero gain on SSDs "
        "(Windows already largely neutralizes it) and not recommended on "
        "HDDs, where prefetching genuinely speeds up boots and app "
        "launches.",
    ),
    "short_names_off": (
        "Legacy 8.3 short names disabled",
        "Disables generation of legacy 8.3 file names on new volumes: faster "
        "file creation in large folders.",
    ),
    "scheduled_defrag_off": (
        "Scheduled defragmentation disabled",
        "Disables the scheduled drive-optimization task. It only runs while "
        "the PC is idle and handles SSD retrim: disable it only if you "
        "optimize manually, and avoid it on HDDs where fragmentation builds "
        "up.",
    ),
    "telemetry_minimal": (
        "Telemetry reduced to the minimum",
        "AllowTelemetry=0 (Security level; Home/Pro editions fall back to the "
        "minimal “Required” level). Fewer background uploads.",
    ),
    "diagtrack_off": (
        "Telemetry service (DiagTrack) disabled",
        "Stops and disables “Connected User Experiences and Telemetry”, which "
        "collects and uploads diagnostics continuously.",
    ),
    "dmwappush_off": (
        "WAP push message service disabled",
        "Disables dmwappushservice, tied to data collection. The service is "
        "already set to manual start and almost never runs: zero gain, this "
        "is plain privacy hardening.",
    ),
    "advertising_id_off": (
        "Advertising ID disabled",
        "Disables the advertising ID that applications use for targeting. No "
        "impact on gaming, a clear privacy win.",
    ),
    "content_suggestions_off": (
        "Windows suggestions and ads disabled",
        "Cuts Start menu suggestions, tips and app promotions "
        "(ContentDeliveryManager). Less noise and background activity.",
    ),
    "consumer_features_off": (
        "Auto-install of promoted apps blocked",
        "DisableWindowsConsumerFeatures=1: blocks automatic installation of "
        "sponsored apps. The policy is fully honored mostly on "
        "Enterprise/Education editions; on Home/Pro its effect is partial "
        "and the ContentDeliveryManager settings do most of the work.",
    ),
    "cortana_off": (
        "Cortana disabled",
        "Blocks Cortana via policy (AllowCortana=0) on Windows 10: less "
        "resident process activity and fewer network requests. No effect on "
        "Windows 11, where Cortana has been removed from the OS.",
    ),
    "background_apps_off": (
        "Background apps disabled",
        "Stops Microsoft Store apps from running in the background "
        "(GlobalUserDisabled=1). Frees CPU, RAM and network while you play.",
    ),
    "activity_feed_off": (
        "Activity history disabled",
        "Shuts off activity history (EnableActivityFeed, "
        "PublishUserActivities, UploadUserActivities set to 0). Microsoft "
        "has retired Timeline cloud sync: this is now a privacy setting, "
        "with no performance gain.",
    ),
    "feedback_requests_off": (
        "Windows feedback requests disabled",
        "NumberOfSIUFInPeriod=0: Windows no longer asks for your feedback "
        "through notifications. Fewer interruptions.",
    ),
    "tailored_experiences_off": (
        "Tailored experiences disabled",
        "Windows no longer uses diagnostic data to personalize tips and ads "
        "(TailoredExperiences...=0).",
    ),
    "svc_fax_off": (
        "Fax service disabled",
        "Disables the Fax service. It is already set to manual start and "
        "never runs on a modern PC: zero gain, just hardening to trim the "
        "system's surface.",
    ),
    "svc_spooler_off": (
        "Print spooler disabled",
        "Disables the print spooler: PRINTING IS IMPOSSIBLE while this tweak is "
        "active. Only for PCs without a printer.",
    ),
    "svc_wsearch_off": (
        "Windows Search indexing disabled",
        "Disables the WSearch indexing service: file search gets slower, but "
        "the disk and CPU can breathe while you play.",
    ),
    "svc_xbox_off": (
        "Xbox services disabled",
        "Disables XblAuthManager, XblGameSave and XboxNetApiSvc. These "
        "services are manual-start and only run when the Xbox app/Game Pass "
        "is in use: near-zero gain if you don't use it, and broken Xbox "
        "sign-in/cloud saves if you do.",
    ),
    "svc_mapsbroker_off": (
        "Maps manager disabled",
        "Disables MapsBroker (offline maps). Delayed auto-start on Windows "
        "10 (a small sign-in-time gain), already manual on Windows 11: a "
        "minimal gain either way.",
    ),
    "svc_remote_registry_off": (
        "Remote Registry disabled",
        "Ensures RemoteRegistry stays Disabled (already the factory setting on "
        "Windows 10/11). Hardening with no in-game impact.",
    ),
    "svc_wersvc_off": (
        "Windows Error Reporting disabled",
        "Disables WerSvc: no more crash report collection or upload. Makes "
        "diagnosing a recurring crash harder, hence the advanced level.",
    ),
    "svc_wmpnetwork_off": (
        "Windows Media network sharing disabled",
        "Disables WMPNetworkSvc (Windows Media library sharing over the "
        "network). The service is manual-start and often absent from recent "
        "installs: zero gain, pure legacy cleanup.",
    ),
    "mouse_accel_off": (
        "Enhance pointer precision disabled",
        "Disables Windows mouse acceleration (MouseSpeed/Threshold set to "
        "0): the same motion always produces the same movement on the "
        "desktop and in games without raw input. CS2 and most recent FPS "
        "games read the mouse through raw input and already bypass it "
        "in-game — this setting is a consistency safeguard.",
    ),
    "mouse_hover_time_10": (
        "Mouse hover delay reduced",
        "Reduces MouseHoverTime from 400 to 10 ms: tooltips and previews "
        "react to hovering instantly. Desktop comfort only — no effect on "
        "in-game latency.",
    ),
    "keyboard_delay_0": (
        "Minimal keyboard repeat delay",
        "Sets the delay before a held key repeats to the minimum "
        "(KeyboardDelay=0). Typing and editing comfort only: games read key "
        "state directly and ignore keyboard repeat.",
    ),
    "sticky_keys_off": (
        "Sticky Keys disabled",
        "Disables the Sticky Keys shortcut (5 × Shift) that interrupts the game "
        "mid-action (Flags=506).",
    ),
    "toggle_keys_off": (
        "Toggle Keys silenced",
        "Disables the Toggle Keys beep and shortcut (Num Lock held for 5 s) — "
        "Flags=58.",
    ),
    "filter_keys_off": (
        "Filter Keys disabled",
        "Disables the Filter Keys shortcut (right Shift held for 8 s), which "
        "can freeze the keyboard in-game (Flags=122).",
    ),
    # Tweaks « petite config » (lowend=True, profil petite_config).
    "onedrive_startup_off": (
        "OneDrive cut from startup",
        "Disables OneDrive's automatic launch at sign-in (the "
        "StartupApproved mechanism, the same one Task Manager uses). "
        "OneDrive stays installed and can still be used on demand.",
    ),
    "edge_preload_off": (
        "Microsoft Edge preloading disabled",
        "Stops Edge from preloading at sign-in (Startup Boost) and from "
        "staying in the background once closed. Frees RAM and CPU if Edge "
        "is not your main browser.",
    ),
    "widgets_news_off": (
        "Widgets and news feed disabled",
        "Shuts off Windows 11 Widgets (permanent WebView2 processes) and "
        "the Windows 10 “News and interests” feed. Several hundred MB of "
        "RAM reclaimed on small configurations.",
    ),
    "defender_scan_lowprio": (
        "Lighter Defender background scans",
        "Caps the CPU that Microsoft Defender's scheduled scans may consume "
        "(50% → 20%) and confines them to idle periods. REAL-TIME "
        "PROTECTION STAYS FULLY ON.",
    ),
    "copilot_off": (
        "Copilot disabled",
        "Disables the Windows 11 Copilot integration (user policy) and "
        "removes its taskbar button. One less WebView2 process in the "
        "background.",
    ),
    "search_web_suggestions_off": (
        "Windows Search without web suggestions",
        "The Start menu search no longer queries Bing: local results only. "
        "Less RAM for SearchHost and no more network requests on every "
        "keystroke.",
    ),
    "clipboard_history_off": (
        "Clipboard history disabled",
        "Disables clipboard history (Win+V): Windows no longer keeps every "
        "copy in memory. A micro RAM gain and better privacy.",
    ),
    "lockscreen_tips_off": (
        "Lock screen tips disabled",
        "Shuts off the lock screen's fun facts, tips and promotions "
        "(Spotlight overlay) and their background downloads. Windows "
        "Spotlight wallpapers keep working.",
    ),
    "delivery_optimization_off": (
        "Update P2P sharing disabled",
        "DODownloadMode=0: Windows Update downloads over plain HTTP and no "
        "longer uploads your updates to other PCs. Frees upload bandwidth, "
        "disk and CPU — noticeable on small connections and weak CPUs.",
    ),
    "reserved_storage_off": (
        "Windows reserved storage disabled",
        "Frees the ~7 GB Windows reserves for its updates (DISM). Precious "
        "on a small 120/256 GB SSD. Fails cleanly if an update is in "
        "progress; future updates get slower again if the disk is nearly "
        "full.",
    ),
}

for _category in CATEGORIES:
    _category["label_en"] = _CATEGORY_LABELS_EN.get(_category["id"],
                                                    _category["label"])

for _tweak in TWEAKS:
    _en = _TWEAKS_EN.get(_tweak["id"])
    _tweak["name_en"] = _en[0] if _en else _tweak["name"]
    _tweak["description_en"] = _en[1] if _en else _tweak["description"]
