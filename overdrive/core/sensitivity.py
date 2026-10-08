"""Convertisseur de sensibilité souris universel (cm/360 et équivalences entre jeux).

Principe : chaque jeu applique un « yaw » (degrés de rotation par compte souris
et par unité de sensibilité). La distance pour un tour complet vaut :

    cm/360 = (360 / (yaw_effectif × sens × dpi)) × 2,54

Les yaw utilisés ici sont les valeurs réelles des moteurs, documentées de longue
date par la communauté (mouse-sensitivity) :

- CS2 / Apex Legends (Source) : m_yaw = 0,022 ;
- Valorant : 0,07 (d'où le rapport CS→Valorant = 0,022/0,07 ≈ ×0,314286,
  soit CS 2,0 ↔ Valorant ≈ 0,6286) ;
- Overwatch 2 et Call of Duty: Warzone : 0,0066
  (rapport CS→OW ≈ ×3,3333, CS 2,0 ↔ OW2 ≈ 6,6667) ;
- Rainbow Six Siege : yaw de base 0,005729578 ((180/π)/10000) pour le
  MouseSensitivityMultiplierUnit PAR DÉFAUT (0,02) de GameSettings.ini ;
  le yaw effectif est proportionnel à ce multiplicateur
  (rapport CS→R6 ≈ ×3,8397 en hipfire, multiplicateur par défaut) ;
- Fortnite : la sensibilité X est un pourcentage ; yaw ≈ 0,5555 degré/compte à
  100 % (constante relevée dans les fichiers du jeu), soit 0,005555 par 1 %
  (rapport CS→Fortnite % ≈ ×3,96, Valorant→Fortnite % ≈ ×12,6).

Jeux volontairement absents (formule non garantie) : aucun autre n'est exposé
plutôt que de risquer une conversion fausse.
"""

from __future__ import annotations

import math

# Bornes d'entrée : sensibilité strictement positive, DPI des souris réelles.
_DPI_MIN = 100
_DPI_MAX = 26000

# Multiplicateur R6 Siege par défaut (GameSettings.ini > MouseSensitivityMultiplierUnit).
_R6_DEFAULT_MULTIPLIER_UNIT = 0.02

# Chaque entrée : id, nom, yaw effectif (degrés/compte par unité de sensibilité),
# note d'unité FR + EN, nombre de décimales d'affichage, pertinence de l'eDPI.
GAMES_SENS: list[dict] = [
    {
        "id": "cs2",
        "name": "Counter-Strike 2",
        "yaw": 0.022,
        "unit_note": "sens du jeu (m_yaw 0,022)",
        "unit_note_en": "in-game sens (m_yaw 0.022)",
        "decimals": 3,
        "edpi_relevant": True,
    },
    {
        "id": "valorant",
        "name": "Valorant",
        "yaw": 0.07,
        "unit_note": "sens du jeu (yaw 0,07)",
        "unit_note_en": "in-game sens (yaw 0.07)",
        "decimals": 4,
        "edpi_relevant": True,
    },
    {
        "id": "apex_legends",
        "name": "Apex Legends",
        "yaw": 0.022,
        "unit_note": "sens du jeu (identique à CS2, yaw 0,022)",
        "unit_note_en": "in-game sens (same as CS2, yaw 0.022)",
        "decimals": 3,
        "edpi_relevant": True,
    },
    {
        "id": "overwatch2",
        "name": "Overwatch 2",
        "yaw": 0.0066,
        "unit_note": "sens du jeu (yaw 0,0066)",
        "unit_note_en": "in-game sens (yaw 0.0066)",
        "decimals": 3,
        "edpi_relevant": True,
    },
    {
        "id": "r6_siege",
        "name": "Tom Clancy's Rainbow Six Siege",
        # Yaw effectif AVEC le multiplicateur par défaut 0,02 :
        # yaw = 0,005729578 × (MouseSensitivityMultiplierUnit / 0,02).
        "yaw": 0.005729578 * (_R6_DEFAULT_MULTIPLIER_UNIT / 0.02),
        "unit_note": (
            "sens hipfire du jeu — hypothèse : MouseSensitivityMultiplierUnit "
            "par défaut (0,02) dans GameSettings.ini"
        ),
        "unit_note_en": (
            "in-game hipfire sens — assumes the default "
            "MouseSensitivityMultiplierUnit (0.02) in GameSettings.ini"
        ),
        "decimals": 2,
        "edpi_relevant": False,
    },
    {
        "id": "fortnite",
        "name": "Fortnite",
        # Fortnite : sensibilité X en pourcent. Constante du moteur relevée
        # dans les fichiers du jeu : 0,5555 degré/compte à 100 %, donc
        # yaw_effectif = 0,5555/100 par point de pourcentage.
        "yaw": 0.5555 / 100.0,
        "unit_note": "sensibilité X (%)",
        "unit_note_en": "X sensitivity (%)",
        "decimals": 2,
        "edpi_relevant": False,
    },
    {
        "id": "warzone",
        "name": "Call of Duty: Warzone",
        "yaw": 0.0066,
        "unit_note": "sens du jeu (yaw 0,0066, identique à Overwatch 2)",
        "unit_note_en": "in-game sens (yaw 0.0066, same as Overwatch 2)",
        "decimals": 3,
        "edpi_relevant": True,
    },
]


def _get_entry(game_id: str) -> dict | None:
    """Entrée de GAMES_SENS pour cet id, ou None."""
    for entry in GAMES_SENS:
        if entry["id"] == game_id:
            return entry
    return None


def _validate(game_id: str, sens: float, dpi: int) -> tuple[dict | None, str | None]:
    """Valide les entrées ; retourne (entrée du jeu, message d'erreur FR)."""
    entry = _get_entry(game_id)
    if entry is None:
        known = ", ".join(e["id"] for e in GAMES_SENS)
        return None, f"Jeu inconnu : « {game_id} ». Jeux pris en charge : {known}."
    try:
        sens_f = float(sens)
    except (TypeError, ValueError):
        return None, "Sensibilité invalide : un nombre strictement positif est attendu."
    if not math.isfinite(sens_f) or sens_f <= 0:
        return None, "Sensibilité invalide : elle doit être strictement positive."
    try:
        dpi_i = int(dpi)
    except (TypeError, ValueError):
        return None, "DPI invalide : un entier est attendu."
    if not (_DPI_MIN <= dpi_i <= _DPI_MAX):
        return None, f"DPI hors plage : entre {_DPI_MIN} et {_DPI_MAX} attendu."
    return entry, None


def _cm360(yaw: float, sens: float, dpi: int) -> float:
    """cm/360 = (360 / (yaw × sens × dpi)) × 2,54."""
    return (360.0 / (yaw * float(sens) * float(dpi))) * 2.54


def _smart_round(value: float, decimals: int) -> float:
    """Arrondi « intelligent » : au moins `decimals` décimales, et jamais moins
    de 4 chiffres significatifs pour les très petites valeurs."""
    if value <= 0:
        return 0.0
    # Décimales nécessaires pour conserver ~4 chiffres significatifs.
    needed = 4 - 1 - math.floor(math.log10(value))
    return round(value, max(decimals, min(needed, 6)))


def compute(game_id: str, sens: float, dpi: int) -> dict:
    """Calcule les cm/360 pour un jeu, une sensibilité et un DPI donnés.

    Retour : {"ok": bool, "cm360": float, "message"?: str}. Jamais d'exception.
    """
    try:
        entry, error = _validate(game_id, sens, dpi)
        if entry is None:
            return {"ok": False, "cm360": 0.0, "message": error}
        return {"ok": True, "cm360": round(_cm360(entry["yaw"], float(sens), int(dpi)), 4)}
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False, "cm360": 0.0, "message": f"Échec du calcul : {exc}"}


def convert(game_id: str, sens: float, dpi: int) -> dict:
    """Convertit une sensibilité d'un jeu vers tous les autres (même cm/360).

    Retour : {"ok": bool, "cm360": float, "edpi": float | None,
              "conversions": [{"game_id","name","sens"}], "message"?: str}.
    L'eDPI (sens × dpi) n'est renvoyé que pour les jeux où la notion est
    d'usage (CS2, Valorant, Apex, OW2, Warzone), None sinon. Jamais d'exception.
    """
    try:
        entry, error = _validate(game_id, sens, dpi)
        if entry is None:
            return {"ok": False, "cm360": 0.0, "edpi": None,
                    "conversions": [], "message": error}
        sens_f, dpi_i = float(sens), int(dpi)
        cm360 = _cm360(entry["yaw"], sens_f, dpi_i)
        # Même rotation par compte pour tous les jeux : yaw_a × sens_a = yaw_b × sens_b.
        degrees_per_count = entry["yaw"] * sens_f
        conversions: list[dict] = []
        for other in GAMES_SENS:
            if other["id"] == entry["id"]:
                continue
            raw = degrees_per_count / other["yaw"]
            conversions.append(
                {
                    "game_id": other["id"],
                    "name": other["name"],
                    "sens": _smart_round(raw, other["decimals"]),
                }
            )
        edpi = round(sens_f * dpi_i, 2) if entry["edpi_relevant"] else None
        return {
            "ok": True,
            "cm360": round(cm360, 4),
            "edpi": edpi,
            "conversions": conversions,
        }
    except Exception as exc:  # jamais d'exception vers l'appelant
        return {"ok": False, "cm360": 0.0, "edpi": None,
                "conversions": [], "message": f"Échec de la conversion : {exc}"}
