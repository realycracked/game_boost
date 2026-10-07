"""Outils Counter-Strike 2 : profils userdata, cs2_video.txt, autoexec recommandé."""

from __future__ import annotations

import shutil
from pathlib import Path

from .catalog import get_game
from .detect import find_steam_root, parse_vdf, steam_game_path

CS2_APPID = 730

# Recommandations vidéo : clés réelles de cs2_video.txt (format KV Valve).
# current est lu dans le fichier du joueur, None si absent.
_VIDEO_RECOMMENDATIONS: list[tuple[str, str, str]] = [
    ("setting.fullscreen", "1", "Plein écran exclusif : latence minimale."),
    ("setting.videocfg_shadow_quality", "1", "Ombres : Faible — les garder (information de jeu) au coût minimal."),
    ("setting.videocfg_texture_detail", "1", "Textures : Moyen (1) dès 6 Go de VRAM, Faible (0) en dessous."),
    ("setting.videocfg_shader_detail", "0", "Détail des shaders : Faible — gros gain dans les fumées."),
    ("setting.videocfg_particle_detail", "0", "Détail des particules : Faible — FPS stables en combat."),
    ("setting.videocfg_ao", "0", "Occlusion ambiante : Désactivée — coût GPU élevé, apport nul en compétitif."),
    ("setting.videocfg_hdr", "0", "Qualité HDR : Performance."),
    ("setting.videocfg_fsr", "0", "FidelityFX Super Resolution : Désactivé — netteté native des silhouettes."),
    ("setting.msaa_samples", "2", "MSAA 2x (ou CMAA2) : compromis netteté/FPS ; éviter 4x/8x."),
    ("setting.r_low_latency", "1", "NVIDIA Reflex : Activé (2 = + Boost) sur GPU NVIDIA."),
]

_FALLBACK_LAUNCH_OPTIONS = "-high -fullscreen +fps_max 0"


def _recommended_launch_options() -> str:
    """Options de lancement recommandées (depuis le catalogue, avec repli)."""
    game = get_game("cs2")
    if game and isinstance(game.get("launch_options"), str):
        return game["launch_options"]
    return _FALLBACK_LAUNCH_OPTIONS


def _flatten_kv(data: object, out: dict[str, str]) -> None:
    """Aplatit un arbre KeyValues en dict {clé: valeur str} (feuilles uniquement)."""
    if not isinstance(data, dict):
        return
    for key, value in data.items():
        if isinstance(value, dict):
            _flatten_kv(value, out)
        elif isinstance(key, str) and isinstance(value, str):
            out[key] = value


def _userdata_profiles(steam_root: Path) -> list[dict]:
    """Profils Steam ayant des données CS2 (userdata/<id>/730)."""
    profiles: list[dict] = []
    userdata = steam_root / "userdata"
    try:
        entries = sorted(p for p in userdata.iterdir() if p.is_dir())
    except OSError:
        return profiles
    for entry in entries:
        local_730 = entry / str(CS2_APPID) / "local"
        try:
            if not local_730.is_dir():
                continue
        except OSError:
            continue
        cfg_dir = local_730 / "cfg"
        autoexec = cfg_dir / "autoexec.cfg"
        config_files: list[str] = []
        try:
            if cfg_dir.is_dir():
                config_files = sorted(
                    p.name for p in cfg_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in (".cfg", ".txt")
                )
        except OSError:
            config_files = []
        has_autoexec = autoexec.name in config_files
        profiles.append(
            {
                "user_id": entry.name,
                "cfg_dir": str(cfg_dir),
                "has_autoexec": has_autoexec,
                "autoexec_path": str(autoexec) if has_autoexec else None,
                "config_files": config_files,
            }
        )
    return profiles


def _read_video_settings(cfg_dir: str) -> dict[str, str] | None:
    """Parse cs2_video.txt (KV Valve "setting.xxx" "val") dans ce dossier cfg."""
    video_file = Path(cfg_dir) / "cs2_video.txt"
    try:
        if not video_file.is_file():
            return None
        text = video_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    flat: dict[str, str] = {}
    _flatten_kv(parse_vdf(text), flat)
    return flat or None


def _video_recommendations(current: dict[str, str] | None) -> list[dict]:
    """Compare les réglages actuels aux valeurs recommandées."""
    settings = current or {}
    return [
        {"key": key, "current": settings.get(key), "recommended": recommended, "note": note}
        for key, recommended, note in _VIDEO_RECOMMENDATIONS
    ]


def cs2_info() -> dict:
    """État complet de l'installation CS2 ; jamais d'exception."""
    install_path: str | None = None
    try:
        path = steam_game_path(CS2_APPID)
        install_path = str(path) if path is not None else None
    except Exception:
        install_path = None

    profiles: list[dict] = []
    try:
        steam_root = find_steam_root()
        if steam_root is not None:
            profiles = _userdata_profiles(steam_root)
    except Exception:
        profiles = []

    video_settings: dict[str, str] | None = None
    for profile in profiles:
        try:
            video_settings = _read_video_settings(profile["cfg_dir"])
        except Exception:
            video_settings = None
        if video_settings is not None:
            break

    return {
        "installed": install_path is not None,
        "install_path": install_path,
        "userdata_profiles": profiles,
        "video_settings": video_settings,
        "video_recommendations": _video_recommendations(video_settings),
        "recommended_launch_options": _recommended_launch_options(),
        "autoexec_recommended": generate_autoexec(),
    }


def generate_autoexec(profile_id: str | None = None) -> str:
    """Contenu d'autoexec.cfg recommandé, commenté en français (cvars CS2 valides).

    Les cvars réseau hérités de CS:GO (rate, cl_interp, cl_interp_ratio,
    cl_updaterate, cl_cmdrate) sont obsolètes dans CS2 et volontairement absents.
    """
    header_profile = profile_id if profile_id else "par défaut"
    lines = [
        "// ============================================================",
        "// Overdrive — autoexec.cfg recommandé pour Counter-Strike 2",
        f"// Profil : {header_profile}",
        "// Emplacement : Steam/userdata/<id>/730/local/cfg/autoexec.cfg",
        "//",
        "// Note : les cvars réseau de CS:GO (rate, cl_interp,",
        "// cl_interp_ratio, cl_updaterate, cl_cmdrate) n'existent plus",
        "// dans CS2 (réseau subtick) et sont volontairement absentes.",
        "// ============================================================",
        "",
        "con_enable 1                        // console accessible (touche ²/~)",
        "",
        "// --- Performances ---",
        "fps_max 0                           // FPS libres ; mettre 400 pour caper",
        "fps_max_ui 120                      // limite les FPS dans les menus",
        "",
        "// --- Souris (décommentez et ajustez à vos valeurs) ---",
        "// sensitivity 1.00                 // votre sensibilité personnelle",
        "// zoom_sensitivity_ratio 1.00      // sensibilité sous lunette",
        "",
        "// --- Matchmaking ---",
        "mm_dedicated_search_maxping 60      // ping maximum accepté en recherche",
        "",
        "// --- Lisibilité ---",
        "r_drawtracers_firstperson 1         // tracers visibles (contrôle du spray)",
        "// viewmodel_fov 68                 // champ de vision de l'arme (54-68)",
        "",
        'echo "Overdrive : autoexec.cfg charge."',
        "",
    ]
    return "\n".join(lines)


def write_autoexec(user_id: str | None = None, content: str | None = None) -> dict:
    """Écrit l'autoexec recommandé dans le profil CS2 ; sauvegarde l'ancien en .bak.

    Retour : {"ok": bool, "message": str, "path": str | None}.
    """
    try:
        steam_root = find_steam_root()
        if steam_root is None:
            return {"ok": False, "message": "Steam introuvable sur cette machine.", "path": None}
        profiles = _userdata_profiles(steam_root)
        if not profiles:
            return {
                "ok": False,
                "message": "Aucun profil CS2 trouvé dans Steam/userdata (lancez CS2 une première fois).",
                "path": None,
            }
        if user_id is not None:
            profile = next((p for p in profiles if p["user_id"] == str(user_id)), None)
            if profile is None:
                return {
                    "ok": False,
                    "message": f"Profil utilisateur '{user_id}' introuvable dans Steam/userdata.",
                    "path": None,
                }
        else:
            profile = profiles[0]

        cfg_dir = Path(profile["cfg_dir"])
        cfg_dir.mkdir(parents=True, exist_ok=True)
        target = cfg_dir / "autoexec.cfg"

        backed_up = False
        if target.is_file():
            shutil.copy2(target, target.with_name("autoexec.cfg.bak"))
            backed_up = True

        text = content if content is not None else generate_autoexec(profile["user_id"])
        target.write_text(text, encoding="utf-8")

        message = f"autoexec.cfg écrit pour le profil {profile['user_id']}."
        if backed_up:
            message += " Ancien fichier sauvegardé en autoexec.cfg.bak."
        return {"ok": True, "message": message, "path": str(target)}
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False, "message": f"Échec de l'écriture de l'autoexec : {exc}", "path": None}
