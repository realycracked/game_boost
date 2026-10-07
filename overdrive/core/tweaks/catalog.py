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
       windows_only: bool = True) -> dict:
    """Construit l'entrée normalisée d'un tweak."""
    return {
        "id": id,
        "name": name,
        "description": description,
        "category": category,
        "impact": impact,
        "risk": risk,
        "windows_only": windows_only,
        "default_for": list(default_for or []),
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
       "Active le plan d'alimentation « Performances ultimes » caché de Windows. "
       "Supprime les économies d'énergie agressives qui limitent CPU et GPU en jeu.",
       "alimentation", "eleve", "sur",
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
       check=None, default_for=["fps", "latence", "equilibre", "stream"]),

    _t("hibernation_off", "Désactiver l'hibernation",
       "Désactive l'hibernation et libère le fichier hiberfil.sys (plusieurs Go). "
       "Évite aussi les réveils lents liés à l'état hybride.",
       "alimentation", "faible", "sur",
       apply=[_cmd("powercfg", "/h", "off")],
       revert=[_cmd("powercfg", "/h", "on")],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Power",
                      "HibernateEnabled", 0),
       default_for=["fps", "latence"]),

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
       "Désactive l'économie d'énergie des liens PCIe (ASPM). Le GPU garde "
       "toute sa bande passante sans latence de réveil.",
       "alimentation", "moyen", "modere",
       apply=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                   "501a4d13-42af-4429-9fd1-a8218c268e20",
                   "ee12f906-d277-404b-b6da-e5fa1a576df5", "0"),
              _cmd("powercfg", "/setactive", "scheme_current")],
       revert=[_cmd("powercfg", "/setacvalueindex", "scheme_current",
                    "501a4d13-42af-4429-9fd1-a8218c268e20",
                    "ee12f906-d277-404b-b6da-e5fa1a576df5", "1"),
               _cmd("powercfg", "/setactive", "scheme_current")],
       check=None, default_for=["fps", "latence"]),

    _t("power_throttling_off", "Power Throttling désactivé",
       "Désactive le bridage d'alimentation des processus en arrière-plan. "
       "Les applications de jeu et d'overlay gardent leur pleine fréquence CPU.",
       "alimentation", "moyen", "modere",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                   "PowerThrottlingOff", "dword", 1)],
       revert=[_reg_del("HKLM",
                        r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                        "PowerThrottlingOff")],
       check=_chk_reg("HKLM",
                      r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                      "PowerThrottlingOff", 1),
       default_for=["fps", "latence"]),

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
       "Force l'état processeur minimal à 100 % sur secteur : le CPU ne "
       "redescend plus en fréquence entre deux actions, ce qui lisse le frametime.",
       "alimentation", "moyen", "modere",
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
       default_for=["fps"]),

    _t("window_animations_off", "Animations de fenêtres désactivées",
       "Supprime l'animation d'agrandissement/réduction des fenêtres. "
       "L'interface répond instantanément, utile en alt-tab pendant une partie.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", _DESKTOP + r"\WindowMetrics", "MinAnimate",
                   "string", "0")],
       revert=[_reg("HKCU", _DESKTOP + r"\WindowMetrics", "MinAnimate",
                    "string", "1")],
       check=_chk_reg("HKCU", _DESKTOP + r"\WindowMetrics", "MinAnimate", "0"),
       default_for=["fps", "latence"]),

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
       default_for=["fps", "equilibre", "stream"]),

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
       default_for=["fps"]),

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
       default_for=["fps"]),

    _t("aero_peek_off", "Aero Peek désactivé",
       "Désactive l'aperçu du bureau Aero Peek. Moins de miniatures et de "
       "composition inutiles pendant que le jeu tourne.",
       "visuels", "faible", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek",
                   "dword", 0)],
       revert=[_reg("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek",
                    "dword", 1)],
       check=_chk_reg("HKCU", r"Software\Microsoft\Windows\DWM",
                      "EnableAeroPeek", 0),
       default_for=["fps"]),

    # ------------------------------------------------------------------ #
    # Jeux                                                                #
    # ------------------------------------------------------------------ #
    _t("game_mode_on", "Mode Jeu activé",
       "Active le Mode Jeu de Windows : priorité CPU/GPU au jeu au premier "
       "plan et mises à jour Windows reportées pendant la partie.",
       "jeux", "moyen", "sur",
       apply=[_reg("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode",
                   "dword", 1),
              _reg("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled",
                   "dword", 1)],
       revert=[_reg_del("HKCU", r"Software\Microsoft\GameBar", "AllowAutoGameMode"),
               _reg_del("HKCU", r"Software\Microsoft\GameBar",
                        "AutoGameModeEnabled")],
       check=_chk_reg("HKCU", r"Software\Microsoft\GameBar",
                      "AllowAutoGameMode", 1),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("gamedvr_off", "Enregistrement Game DVR désactivé",
       "Coupe la capture d'arrière-plan Xbox Game DVR (clips automatiques). "
       "Supprime une charge GPU/disque permanente ; OBS reste le bon outil pour capturer.",
       "jeux", "eleve", "sur",
       apply=[_reg("HKCU", _GCS, "GameDVR_Enabled", "dword", 0),
              _reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                   "AppCaptureEnabled", "dword", 0)],
       revert=[_reg("HKCU", _GCS, "GameDVR_Enabled", "dword", 1),
               _reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
                    "AppCaptureEnabled", "dword", 1)],
       check=_chk_reg("HKCU", _GCS, "GameDVR_Enabled", 0),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("gamedvr_policy_off", "Game DVR interdit (stratégie machine)",
       "Interdit Game DVR au niveau machine (HKLM). Complète le réglage "
       "utilisateur pour tous les comptes du PC.",
       "jeux", "moyen", "modere",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
                   "AllowGameDVR", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
                        "AllowGameDVR")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR",
                      "AllowGameDVR", 0),
       default_for=["fps", "latence"]),

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
       "Désactive globalement les « optimisations plein écran » (FSE) : les jeux "
       "en plein écran exclusif évitent la composition DWM, pour une latence moindre.",
       "jeux", "moyen", "modere",
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
       default_for=["latence", "fps"]),

    # ------------------------------------------------------------------ #
    # Système & CPU                                                       #
    # ------------------------------------------------------------------ #
    _t("win32_priority_separation", "Priorité CPU au premier plan (0x26)",
       "Règle Win32PrioritySeparation sur 38 (0x26) : quanta courts et nette "
       "priorité au programme au premier plan — le jeu. Valeur par défaut : 2.",
       "systeme", "eleve", "modere",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                   "Win32PrioritySeparation", "dword", 38)],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                    "Win32PrioritySeparation", "dword", 2)],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                      "Win32PrioritySeparation", 38),
       default_for=["fps", "latence"]),

    _t("sysmain_off", "Service SysMain (Superfetch) désactivé",
       "Arrête et désactive SysMain, qui précharge des applications en tâche de "
       "fond. Supprime des accès disque et de la RAM consommée pendant le jeu.",
       "systeme", "moyen", "modere",
       apply=[_svc("SysMain", "disabled", stop=True)],
       revert=[_svc("SysMain", "auto")],
       check=_chk_svc("SysMain", "disabled"),
       default_for=["fps", "equilibre"]),

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
       "Relève le seuil de séparation des svchost.exe : les services partagent "
       "moins de processus, ce qui réduit l'empreinte mémoire et les changements de contexte.",
       "systeme", "faible", "avance",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                   "SvcHostSplitThresholdInKB", "dword", 67108864)],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                    "SvcHostSplitThresholdInKB", "dword", 3670016)],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control",
                      "SvcHostSplitThresholdInKB", 67108864),
       default_for=[]),

    _t("timer_resolution_global", "Résolution du timer global (Win11)",
       "Force Windows 11 à honorer la haute résolution du timer demandée par les "
       "jeux même en arrière-plan (GlobalTimerResolutionRequests=1). Redémarrage requis.",
       "systeme", "moyen", "avance",
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
       "Ferme automatiquement les applications qui ne répondent plus à la "
       "déconnexion/extinction, sans fenêtre « Fermer quand même ? ».",
       "systeme", "faible", "sur",
       apply=[_reg("HKCU", _DESKTOP, "AutoEndTasks", "string", "1")],
       revert=[_reg_del("HKCU", _DESKTOP, "AutoEndTasks")],
       check=_chk_reg("HKCU", _DESKTOP, "AutoEndTasks", "1"),
       default_for=["equilibre"]),

    # ------------------------------------------------------------------ #
    # Mémoire                                                             #
    # ------------------------------------------------------------------ #
    _t("memory_compression_off", "Compression mémoire désactivée",
       "Désactive la compression mémoire : moins de cycles CPU volés au jeu "
       "quand la RAM est sollicitée. À réserver aux PC avec 16 Go ou plus.",
       "memoire", "moyen", "modere",
       apply=[_ps("Disable-MMAgent -MemoryCompression")],
       revert=[_ps("Enable-MMAgent -MemoryCompression")],
       check=None, default_for=["fps", "latence"]),

    _t("page_combining_off", "Combinaison de pages désactivée",
       "Désactive la déduplication des pages mémoire (PageCombining), une tâche "
       "de fond CPU. Pertinent sur les machines avec beaucoup de RAM.",
       "memoire", "faible", "avance",
       apply=[_ps("Disable-MMAgent -PageCombining")],
       revert=[_ps("Enable-MMAgent -PageCombining")],
       check=None, default_for=[]),

    _t("large_system_cache_0", "Cache système standard (poste de travail)",
       "Garantit LargeSystemCache=0 : la RAM sert d'abord aux applications (le "
       "jeu), pas au cache fichiers géant destiné aux serveurs.",
       "memoire", "faible", "sur",
       apply=[_reg("HKLM", _MEMMGMT, "LargeSystemCache", "dword", 0)],
       revert=[_reg("HKLM", _MEMMGMT, "LargeSystemCache", "dword", 0)],
       check=_chk_reg("HKLM", _MEMMGMT, "LargeSystemCache", 0),
       default_for=["equilibre"]),

    _t("clear_pagefile_off", "Pas d'effacement du fichier d'échange à l'arrêt",
       "Garantit ClearPageFileAtShutdown=0 : l'effacement du pagefile à chaque "
       "extinction ralentit fortement l'arrêt sans bénéfice pour un PC de jeu.",
       "memoire", "faible", "sur",
       apply=[_reg("HKLM", _MEMMGMT, "ClearPageFileAtShutdown", "dword", 0)],
       revert=[_reg("HKLM", _MEMMGMT, "ClearPageFileAtShutdown", "dword", 0)],
       check=_chk_reg("HKLM", _MEMMGMT, "ClearPageFileAtShutdown", 0),
       default_for=["equilibre"]),

    _t("paging_executive_off", "Noyau maintenu en RAM",
       "DisablePagingExecutive=1 : empêche Windows de paginer le noyau sur le "
       "disque. Accès système plus constants ; nécessite une marge de RAM.",
       "memoire", "faible", "modere",
       apply=[_reg("HKLM", _MEMMGMT, "DisablePagingExecutive", "dword", 1)],
       revert=[_reg("HKLM", _MEMMGMT, "DisablePagingExecutive", "dword", 0)],
       check=_chk_reg("HKLM", _MEMMGMT, "DisablePagingExecutive", 1),
       default_for=["fps"]),

    # ------------------------------------------------------------------ #
    # Réseau & latence                                                    #
    # ------------------------------------------------------------------ #
    _t("network_throttling_off", "Bridage réseau multimédia désactivé",
       "NetworkThrottlingIndex=0xFFFFFFFF : supprime la limite de 10 paquets/ms "
       "que Windows applique quand du multimédia joue. Essentiel en jeu en ligne.",
       "reseau", "eleve", "sur",
       apply=[_reg("HKLM", _SYSPROF, "NetworkThrottlingIndex", "dword",
                   4294967295)],
       revert=[_reg("HKLM", _SYSPROF, "NetworkThrottlingIndex", "dword", 10)],
       check=_chk_reg("HKLM", _SYSPROF, "NetworkThrottlingIndex", 4294967295),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("system_responsiveness_0", "Réactivité système dédiée au jeu",
       "SystemResponsiveness=0 : le planificateur multimédia ne réserve plus "
       "20 % du CPU aux tâches de fond. Le jeu au premier plan prend tout.",
       "reseau", "eleve", "sur",
       apply=[_reg("HKLM", _SYSPROF, "SystemResponsiveness", "dword", 0)],
       revert=[_reg("HKLM", _SYSPROF, "SystemResponsiveness", "dword", 20)],
       check=_chk_reg("HKLM", _SYSPROF, "SystemResponsiveness", 0),
       default_for=["fps", "latence", "equilibre"]),

    _t("nagle_off", "Algorithme de Nagle désactivé",
       "Écrit TcpAckFrequency=1 et TCPNoDelay=1 sur toutes les interfaces : les "
       "petits paquets partent sans attente de regroupement. Ping plus régulier.",
       "reseau", "moyen", "modere",
       apply=[_ps("Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { New-ItemProperty -Path $_.PSPath -Name 'TcpAckFrequency' -Value 1 -PropertyType DWord -Force | Out-Null; New-ItemProperty -Path $_.PSPath -Name 'TCPNoDelay' -Value 1 -PropertyType DWord -Force | Out-Null }")],
       revert=[_ps("Get-ChildItem 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces' | ForEach-Object { Remove-ItemProperty -Path $_.PSPath -Name 'TcpAckFrequency','TCPNoDelay' -ErrorAction SilentlyContinue }")],
       check=None, default_for=["latence"]),

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
       "Bascule les DNS des cartes actives vers Cloudflare (1.1.1.1 / 1.0.0.1), "
       "souvent plus rapides que ceux du FAI pour résoudre les serveurs de jeu.",
       "reseau", "faible", "modere",
       apply=[_ps("Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | Set-DnsClientServerAddress -ServerAddresses ('1.1.1.1','1.0.0.1')")],
       revert=[_ps("Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | Set-DnsClientServerAddress -ResetServerAddresses")],
       check=None, default_for=[]),

    _t("lso_off", "Large Send Offload désactivé",
       "Désactive le LSO des cartes réseau : le découpage des paquets revient au "
       "CPU, ce qui évite la latence ajoutée par certains pilotes. Débit brut un peu réduit.",
       "reseau", "moyen", "avance",
       apply=[_ps("Disable-NetAdapterLso -Name '*'")],
       revert=[_ps("Enable-NetAdapterLso -Name '*'")],
       check=None, default_for=[]),

    _t("nic_power_saving_off", "Économie d'énergie des cartes réseau désactivée",
       "Empêche Windows d'éteindre la carte réseau pour économiser l'énergie. "
       "Évite déconnexions et pics de ping au réveil de la carte.",
       "reseau", "moyen", "sur",
       apply=[_ps("Get-NetAdapter -Physical | ForEach-Object { Disable-NetAdapterPowerManagement -Name $_.Name -ErrorAction SilentlyContinue }")],
       revert=[_ps("Get-NetAdapter -Physical | ForEach-Object { Enable-NetAdapterPowerManagement -Name $_.Name -ErrorAction SilentlyContinue }")],
       check=None, default_for=["latence", "equilibre", "stream"]),

    _t("teredo_off", "Teredo désactivé",
       "Désactive le tunnel IPv6 Teredo, source de latence et de résolutions "
       "parasites. Attention : le chat de groupe Xbox/Game Pass peut en dépendre.",
       "reseau", "faible", "modere",
       apply=[_cmd("netsh", "interface", "teredo", "set", "state", "disabled")],
       revert=[_cmd("netsh", "interface", "teredo", "set", "state",
                    "type=default")],
       check=None, default_for=[]),

    # ------------------------------------------------------------------ #
    # GPU                                                                 #
    # ------------------------------------------------------------------ #
    _t("games_task_gpu_priority", "Priorité CPU/IO des jeux (profil MMCSS)",
       "Relève le profil « Games » du planificateur multimédia : Priority 2→6, "
       "catégories High (GPU Priority garde sa valeur d'usine 8). Les threads "
       "du jeu passent devant le reste.",
       "gpu", "moyen", "modere",
       apply=[_reg("HKLM", _GAMES_TASK, "Priority", "dword", 6),
              _reg("HKLM", _GAMES_TASK, "Scheduling Category", "string", "High"),
              _reg("HKLM", _GAMES_TASK, "SFIO Priority", "string", "High")],
       revert=[_reg("HKLM", _GAMES_TASK, "Priority", "dword", 2),
               _reg("HKLM", _GAMES_TASK, "Scheduling Category", "string",
                    "Medium"),
               _reg("HKLM", _GAMES_TASK, "SFIO Priority", "string", "Normal")],
       check=_chk_reg("HKLM", _GAMES_TASK, "Priority", 6),
       default_for=["fps", "latence"]),

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
       default_for=["fps", "equilibre"]),

    # ------------------------------------------------------------------ #
    # Stockage                                                            #
    # ------------------------------------------------------------------ #
    _t("trim_on", "TRIM SSD activé",
       "Garantit que le TRIM est actif (DisableDeleteNotify=0), indispensable "
       "pour conserver les performances d'écriture d'un SSD dans le temps.",
       "stockage", "moyen", "sur",
       apply=[_cmd("fsutil", "behavior", "set", "DisableDeleteNotify", "0")],
       revert=[_cmd("fsutil", "behavior", "set", "DisableDeleteNotify", "0")],
       check=None, default_for=["fps", "latence", "equilibre", "stream"]),

    _t("ntfs_last_access_off", "Horodatage « dernier accès » NTFS désactivé",
       "NTFS n'écrit plus la date de dernier accès à chaque lecture de fichier. "
       "Moins d'écritures parasites pendant les chargements de jeux.",
       "stockage", "faible", "sur",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem",
                   "NtfsDisableLastAccessUpdate", "dword", 1)],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem",
                    "NtfsDisableLastAccessUpdate", "dword", 2147483650)],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem",
                      "NtfsDisableLastAccessUpdate", 1),
       default_for=["fps", "equilibre"]),

    _t("prefetcher_off", "Prefetch/Superfetch (registre) désactivés",
       "Coupe le préchargement Prefetch/Superfetch au niveau registre. Sur SSD "
       "NVMe, ce préchargement n'apporte rien et génère des accès disque inutiles.",
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
       "Désactive la tâche planifiée de défragmentation/optimisation. Utile si "
       "vous préférez lancer l'optimisation SSD manuellement, hors sessions de jeu.",
       "stockage", "faible", "modere",
       apply=[_cmd("schtasks", "/Change", "/TN",
                   r"\Microsoft\Windows\Defrag\ScheduledDefrag", "/Disable")],
       revert=[_cmd("schtasks", "/Change", "/TN",
                    r"\Microsoft\Windows\Defrag\ScheduledDefrag", "/Enable")],
       check=None, default_for=[]),

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
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("diagtrack_off", "Service de télémétrie (DiagTrack) désactivé",
       "Arrête et désactive « Expériences des utilisateurs connectés et "
       "télémétrie », qui collecte et téléverse des diagnostics en continu.",
       "confidentialite", "moyen", "sur",
       apply=[_svc("DiagTrack", "disabled", stop=True)],
       revert=[_svc("DiagTrack", "auto")],
       check=_chk_svc("DiagTrack", "disabled"),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("dmwappush_off", "Service de messages push WAP désactivé",
       "Désactive dmwappushservice, le routeur de messages push lié à la "
       "collecte de données. Sans usage pour un PC de jeu.",
       "confidentialite", "faible", "sur",
       apply=[_svc("dmwappushservice", "disabled", stop=True)],
       revert=[_svc("dmwappushservice", "manual")],
       check=_chk_svc("dmwappushservice", "disabled"),
       default_for=["fps", "equilibre"]),

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
       default_for=["fps", "equilibre", "stream"]),

    _t("consumer_features_off", "Installation auto d'applications promues bloquée",
       "DisableWindowsConsumerFeatures=1 : Windows n'installe plus tout seul "
       "les applications sponsorisées (jeux mobiles, services tiers).",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                   "DisableWindowsConsumerFeatures", "dword", 1)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                        "DisableWindowsConsumerFeatures")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent",
                      "DisableWindowsConsumerFeatures", 1),
       default_for=["equilibre", "stream"]),

    _t("cortana_off", "Cortana désactivée",
       "Interdit Cortana via stratégie (AllowCortana=0). Supprime son processus "
       "résident et ses requêtes réseau sur Windows 10.",
       "confidentialite", "faible", "sur",
       apply=[_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                   "AllowCortana", "dword", 0)],
       revert=[_reg_del("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                        "AllowCortana")],
       check=_chk_reg("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                      "AllowCortana", 0),
       default_for=["fps", "equilibre"]),

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
       default_for=["fps", "latence", "equilibre"]),

    _t("activity_feed_off", "Historique d'activités désactivé",
       "Coupe le flux d'activités et son envoi au cloud (EnableActivityFeed, "
       "PublishUserActivities, UploadUserActivities à 0).",
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

    # ------------------------------------------------------------------ #
    # Services Windows                                                    #
    # ------------------------------------------------------------------ #
    _t("svc_fax_off", "Service Fax désactivé",
       "Désactive le service Fax, inutile sur un PC de jeu moderne. "
       "Un service résident de moins.",
       "services", "faible", "sur",
       apply=[_svc("Fax", "disabled", stop=True)],
       revert=[_svc("Fax", "manual")],
       check=_chk_svc("Fax", "disabled"),
       default_for=["fps", "equilibre"]),

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
       default_for=["fps"]),

    _t("svc_xbox_off", "Services Xbox désactivés",
       "Désactive XblAuthManager, XblGameSave et XboxNetApiSvc. ATTENTION : "
       "l'application Xbox, le Game Pass et ses sauvegardes cloud en dépendent.",
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
       "Désactive MapsBroker (cartes hors connexion), sans objet sur un PC de "
       "jeu. Libère un service à démarrage automatique.",
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
       "Désactive WMPNetworkSvc, le partage de bibliothèques multimédias en "
       "réseau local. Service hérité sans usage pour le jeu.",
       "services", "faible", "sur",
       apply=[_svc("WMPNetworkSvc", "disabled", stop=True)],
       revert=[_svc("WMPNetworkSvc", "manual")],
       check=_chk_svc("WMPNetworkSvc", "disabled"),
       default_for=["equilibre"]),

    # ------------------------------------------------------------------ #
    # Souris & périphériques                                              #
    # ------------------------------------------------------------------ #
    _t("mouse_accel_off", "Précision du pointeur améliorée désactivée",
       "Désactive l'accélération souris de Windows (MouseSpeed/Threshold à 0). "
       "Indispensable en FPS : le même geste produit toujours le même déplacement.",
       "peripheriques", "eleve", "sur",
       apply=[_reg("HKCU", _MOUSE, "MouseSpeed", "string", "0"),
              _reg("HKCU", _MOUSE, "MouseThreshold1", "string", "0"),
              _reg("HKCU", _MOUSE, "MouseThreshold2", "string", "0")],
       revert=[_reg("HKCU", _MOUSE, "MouseSpeed", "string", "1"),
               _reg("HKCU", _MOUSE, "MouseThreshold1", "string", "6"),
               _reg("HKCU", _MOUSE, "MouseThreshold2", "string", "10")],
       check=_chk_reg("HKCU", _MOUSE, "MouseSpeed", "0"),
       default_for=["fps", "latence", "equilibre", "stream"]),

    _t("mouse_hover_time_10", "Délai de survol souris réduit",
       "Réduit MouseHoverTime de 400 à 10 ms : les infobulles et aperçus "
       "réagissent immédiatement au survol.",
       "peripheriques", "faible", "sur",
       apply=[_reg("HKCU", _MOUSE, "MouseHoverTime", "string", "10")],
       revert=[_reg("HKCU", _MOUSE, "MouseHoverTime", "string", "400")],
       check=_chk_reg("HKCU", _MOUSE, "MouseHoverTime", "10"),
       default_for=["latence"]),

    _t("keyboard_delay_0", "Délai de répétition clavier minimal",
       "Règle le délai avant répétition d'une touche maintenue au minimum "
       "(KeyboardDelay=0). Utile pour le strafe et l'édition rapide.",
       "peripheriques", "faible", "sur",
       apply=[_reg("HKCU", r"Control Panel\Keyboard", "KeyboardDelay",
                   "string", "0")],
       revert=[_reg("HKCU", r"Control Panel\Keyboard", "KeyboardDelay",
                    "string", "1")],
       check=_chk_reg("HKCU", r"Control Panel\Keyboard", "KeyboardDelay", "0"),
       default_for=["latence", "fps"]),

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

    _t("input_queue_sizes", "Files d'attente souris/clavier réduites",
       "Réduit MouseDataQueueSize et KeyboardDataQueueSize de 100 à 20 : moins "
       "de mise en tampon des entrées, au prix d'une marge réduite sous forte charge.",
       "peripheriques", "faible", "avance",
       apply=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Services\mouclass\Parameters",
                   "MouseDataQueueSize", "dword", 20),
              _reg("HKLM", r"SYSTEM\CurrentControlSet\Services\kbdclass\Parameters",
                   "KeyboardDataQueueSize", "dword", 20)],
       revert=[_reg("HKLM", r"SYSTEM\CurrentControlSet\Services\mouclass\Parameters",
                    "MouseDataQueueSize", "dword", 100),
               _reg("HKLM", r"SYSTEM\CurrentControlSet\Services\kbdclass\Parameters",
                    "KeyboardDataQueueSize", "dword", 100)],
       check=_chk_reg("HKLM", r"SYSTEM\CurrentControlSet\Services\mouclass\Parameters",
                      "MouseDataQueueSize", 20),
       default_for=[]),
]
