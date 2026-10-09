"""Bibliothèque de viseurs CS2 « inspirés des pros » + encodeur de share codes.

Les codes de partage des joueurs professionnels changent au fil des saisons et
ne peuvent pas être vérifiés en ligne de façon fiable : chaque entrée du
catalogue décrit donc un style RÉALISTE « inspiré de <joueur> » (et non « le
code exact du moment »), et son share code est GÉNÉRÉ par l'encodeur de ce
module, puis vérifié par aller-retour decode(encode(p)) == p dans les tests.

Format de partage CS2 (algorithme public, documenté par la communauté,
implémentation de référence : csgo-sharecode) :

- 18 octets de paramètres ; l'octet 0 est une somme de contrôle
  (somme des octets 1..17 modulo 256) ;
- le tout est lu comme un grand entier (gros-boutiste) puis écrit en base 57
  avec l'alphabet « ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789 »
  (chiffre de poids faible en premier), 25 caractères en 5 groupes de 5,
  préfixés par « CSGO- ».

Chaque entrée porte aussi un champ "console" (commandes cl_crosshair* exactes),
repli garanti si un code généré n'était pas accepté par une version du jeu.
"""

from __future__ import annotations

import re

# Alphabet officiel des share codes CS2 (57 caractères, sans I, l, g, 0, 1).
_DICTIONARY = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789"
_BASE = len(_DICTIONARY)  # 57
_CODE_CHARS = 25
_BYTES_LEN = 18

_CODE_RE = re.compile(
    r"^CSGO(?:-[" + re.escape(_DICTIONARY) + r"]{5}){5}$"
)

# Couleurs prédéfinies de CS2 (cl_crosshaircolor 0..4) ; 5 = personnalisée (RVB).
_PRESET_COLORS: dict[int, tuple[int, int, int]] = {
    0: (250, 50, 50),    # rouge
    1: (50, 250, 50),    # vert
    2: (250, 250, 50),   # jaune
    3: (50, 50, 250),    # bleu
    4: (50, 250, 250),   # cyan
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _int8(byte: int) -> int:
    """Octet non signé → entier signé (complément à deux)."""
    return byte - 256 if byte > 127 else byte


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    """"#rrggbb" → (r, v, b) ; blanc en cas de valeur illisible."""
    try:
        text = str(color).lstrip("#")
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    except (ValueError, IndexError):
        return 255, 255, 255


def encode_code(params: dict) -> str:
    """Encode des paramètres de viseur en share code « CSGO-… » valide.

    Clés reconnues (valeurs hors bornes ramenées dans les bornes du jeu) :
    size (0..819,1), thickness (0..6,3), gap (-12,8..12,7), dot (bool),
    outline (bool), color ("#rrggbb"), style_num (0..5), et en option
    alpha (0..255), outline_thickness (0..3), split_distance (0..127),
    follow_recoil, fixed_gap, inner_split_alpha, outer_split_alpha,
    split_size_ratio, t_style, deployed_weapon_gap, alpha_enabled.
    """
    size = _clamp(round(float(params.get("size", 2.5)) * 10), 0, 0x1FFF)
    thickness = _clamp(round(float(params.get("thickness", 0.5)) * 10), 0, 63)
    gap = int(_clamp(round(float(params.get("gap", 0.0)) * 10), -128, 127))
    dot = bool(params.get("dot", False))
    outline_on = bool(params.get("outline", False))
    outline_thickness = _clamp(
        round(float(params.get("outline_thickness", 1.0)) * 2), 0, 6)
    red, green, blue = _hex_to_rgb(params.get("color", "#00ff00"))
    alpha = int(_clamp(int(params.get("alpha", 255)), 0, 255))
    style = int(_clamp(int(params.get("style_num", 4)), 0, 7))
    split_distance = int(_clamp(int(params.get("split_distance", 7)), 0, 127))
    follow_recoil = bool(params.get("follow_recoil", False))
    fixed_gap = int(_clamp(round(float(params.get("fixed_gap", 3.0)) * 10), -128, 127))
    inner_split_alpha = int(_clamp(round(float(params.get("inner_split_alpha", 1.0)) * 10), 0, 10))
    outer_split_alpha = int(_clamp(round(float(params.get("outer_split_alpha", 0.5)) * 10), 0, 10))
    split_size_ratio = int(_clamp(round(float(params.get("split_size_ratio", 0.3)) * 10), 0, 10))
    t_style = bool(params.get("t_style", False))
    deployed_weapon_gap = bool(params.get("deployed_weapon_gap", False))
    alpha_enabled = bool(params.get("alpha_enabled", True))
    color_index = 5  # toujours « personnalisée » : le RVB fait foi

    data = bytearray(_BYTES_LEN)
    data[1] = 1  # constante du format
    data[2] = gap & 0xFF
    data[3] = int(outline_thickness)
    data[4], data[5], data[6], data[7] = red, green, blue, alpha
    data[8] = split_distance | (0x80 if follow_recoil else 0)
    data[9] = fixed_gap & 0xFF
    data[10] = (color_index & 7) | (8 if outline_on else 0) | (inner_split_alpha << 4)
    data[11] = (outer_split_alpha & 0xF) | (split_size_ratio << 4)
    data[12] = int(thickness) & 0x3F
    flags = (1 if dot else 0) | (2 if deployed_weapon_gap else 0) \
        | (4 if alpha_enabled else 0) | (8 if t_style else 0)
    data[13] = ((style & 7) << 1) | (flags << 4)
    data[14] = int(size) & 0xFF
    data[15] = (int(size) >> 8) & 0x1F
    data[0] = sum(data[1:]) % 256

    value = int.from_bytes(bytes(data), "big")
    digits: list[str] = []
    for _ in range(_CODE_CHARS):
        value, remainder = divmod(value, _BASE)
        digits.append(_DICTIONARY[remainder])
    # Chiffre de poids faible en premier (convention du format).
    text = "".join(digits)
    groups = [text[i:i + 5] for i in range(0, _CODE_CHARS, 5)]
    return "CSGO-" + "-".join(groups)


def decode_code(code: str) -> dict | None:
    """Décode un share code « CSGO-… » ; None si format ou checksum invalide."""
    try:
        if not isinstance(code, str) or not _CODE_RE.match(code):
            return None
        clean = code.replace("CSGO", "").replace("-", "")
        value = 0
        for char in reversed(clean):  # poids fort en dernier dans la chaîne
            value = value * _BASE + _DICTIONARY.index(char)
        if value >= 1 << (8 * _BYTES_LEN):
            return None
        data = value.to_bytes(_BYTES_LEN, "big")
        if data[0] != sum(data[1:]) % 256:
            return None

        color_index = data[10] & 7
        if color_index == 5:
            red, green, blue = data[4], data[5], data[6]
        else:
            red, green, blue = _PRESET_COLORS.get(color_index, (data[4], data[5], data[6]))
        flags = (data[13] >> 4) & 0xF
        return {
            "size": (((data[15] & 0x1F) << 8) | data[14]) / 10.0,
            "thickness": (data[12] & 0x3F) / 10.0,
            "gap": _int8(data[2]) / 10.0,
            "dot": bool(flags & 1),
            "outline": bool(data[10] & 8),
            "color": f"#{red:02x}{green:02x}{blue:02x}",
            "style_num": (data[13] >> 1) & 7,
            "alpha": data[7],
            "alpha_enabled": bool(flags & 4),
            "deployed_weapon_gap": bool(flags & 2),
            "t_style": bool(flags & 8),
            "outline_thickness": data[3] / 2.0,
            "color_index": color_index,
            "split_distance": data[8] & 0x7F,
            "follow_recoil": bool(data[8] & 0x80),
            "fixed_gap": _int8(data[9]) / 10.0,
            "inner_split_alpha": ((data[10] >> 4) & 0xF) / 10.0,
            "outer_split_alpha": (data[11] & 0xF) / 10.0,
            "split_size_ratio": ((data[11] >> 4) & 0xF) / 10.0,
        }
    except Exception:  # jamais d'exception vers l'appelant
        return None


def console_commands(params: dict) -> str:
    """Commandes console cl_crosshair* exactes correspondant aux paramètres."""
    red, green, blue = _hex_to_rgb(params.get("color", "#00ff00"))
    parts = [
        f"cl_crosshairstyle {int(params.get('style_num', 4))}",
        f"cl_crosshairsize {float(params.get('size', 2.5)):g}",
        f"cl_crosshairthickness {float(params.get('thickness', 0.5)):g}",
        f"cl_crosshairgap {float(params.get('gap', 0.0)):g}",
        f"cl_crosshairdot {1 if params.get('dot') else 0}",
        f"cl_crosshair_drawoutline {1 if params.get('outline') else 0}",
        "cl_crosshair_outlinethickness 1",
        "cl_crosshaircolor 5",
        f"cl_crosshaircolor_r {red}",
        f"cl_crosshaircolor_g {green}",
        f"cl_crosshaircolor_b {blue}",
        "cl_crosshairusealpha 1",
        "cl_crosshairalpha 255",
    ]
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Catalogue : styles réalistes « inspirés de » joueurs pros CS2 connus.
# Valeurs sur la grille du format (pas de 0,1) pour un aller-retour exact.
# Le champ "code" est généré par encode_code() à l'import ; "console" donne
# les commandes exactes en repli garanti.
# ---------------------------------------------------------------------------

CROSSHAIRS: list[dict] = [
    {
        "id": "s1mple",
        "player": "s1mple",
        "style": "Petite croix verte classique, sans point, gap serré",
        "style_en": "Small classic green cross, no dot, tight gap",
        "params": {"size": 1.5, "thickness": 0.5, "gap": -3.0, "dot": False,
                   "outline": False, "color": "#00ff00", "style_num": 4},
    },
    {
        "id": "zywoo",
        "player": "ZywOo",
        "style": "Croix cyan minimaliste, très fine",
        "style_en": "Minimalist cyan cross, very thin",
        "params": {"size": 1.0, "thickness": 0.5, "gap": -2.0, "dot": False,
                   "outline": False, "color": "#00ffff", "style_num": 4},
    },
    {
        "id": "niko",
        "player": "NiKo",
        "style": "Micro-croix verte avec point central, gap très négatif",
        "style_en": "Tiny green cross with center dot, very negative gap",
        "params": {"size": 1.0, "thickness": 1.0, "gap": -5.0, "dot": True,
                   "outline": False, "color": "#00ff00", "style_num": 4},
    },
    {
        "id": "m0nesy",
        "player": "m0NESY",
        "style": "Petite croix bleue nette, sans contour",
        "style_en": "Small crisp blue cross, no outline",
        "params": {"size": 1.0, "thickness": 0.5, "gap": -3.0, "dot": False,
                   "outline": False, "color": "#0080ff", "style_num": 4},
    },
    {
        "id": "donk",
        "player": "donk",
        "style": "Croix jaune compacte et agressive",
        "style_en": "Compact, aggressive yellow cross",
        "params": {"size": 1.0, "thickness": 0.5, "gap": -1.0, "dot": False,
                   "outline": False, "color": "#ffff00", "style_num": 4},
    },
    {
        "id": "ropz",
        "player": "ropz",
        "style": "Croix verte équilibrée, lisible sur toutes les cartes",
        "style_en": "Balanced green cross, readable on every map",
        "params": {"size": 1.5, "thickness": 0.5, "gap": -4.0, "dot": False,
                   "outline": False, "color": "#00ff00", "style_num": 4},
    },
    {
        "id": "device",
        "player": "device",
        "style": "Croix verte un peu plus longue, style AWP polyvalent",
        "style_en": "Slightly longer green cross, versatile AWP style",
        "params": {"size": 2.5, "thickness": 0.5, "gap": -1.0, "dot": False,
                   "outline": False, "color": "#00ff00", "style_num": 4},
    },
    {
        "id": "sh1ro",
        "player": "sh1ro",
        "style": "Croix blanche sobre avec contour, très lisible",
        "style_en": "Clean white cross with outline, highly readable",
        "params": {"size": 2.0, "thickness": 0.5, "gap": -1.0, "dot": False,
                   "outline": True, "color": "#ffffff", "style_num": 4},
    },
    {
        "id": "b1t",
        "player": "b1t",
        "style": "Petite croix verte dense, gap fermé",
        "style_en": "Small dense green cross, closed gap",
        "params": {"size": 1.0, "thickness": 1.0, "gap": -4.0, "dot": False,
                   "outline": False, "color": "#00ff00", "style_num": 4},
    },
    {
        "id": "twistzz",
        "player": "Twistzz",
        "style": "Croix cyan fine et allongée, sans point",
        "style_en": "Thin, elongated cyan cross, no dot",
        "params": {"size": 2.0, "thickness": 0.5, "gap": -3.0, "dot": False,
                   "outline": False, "color": "#00ffff", "style_num": 4},
    },
    {
        "id": "broky",
        "player": "broky",
        "style": "Croix jaune avec contour, bien visible dans les fumées",
        "style_en": "Yellow cross with outline, highly visible in smokes",
        "params": {"size": 2.0, "thickness": 0.5, "gap": -2.0, "dot": False,
                   "outline": True, "color": "#ffff00", "style_num": 4},
    },
    {
        "id": "electronic",
        "player": "electroNic",
        "style": "Croix rose medium avec point, style rifler original",
        "style_en": "Medium pink cross with dot, distinctive rifler style",
        "params": {"size": 2.0, "thickness": 1.0, "gap": -3.0, "dot": True,
                   "outline": False, "color": "#ff00ff", "style_num": 4},
    },
]

# Injection des champs générés ("code", "console") sans jamais lever à l'import.
for _entry in CROSSHAIRS:
    try:
        _entry["code"] = encode_code(_entry["params"])
    except Exception:
        _entry["code"] = None
    try:
        _entry["console"] = console_commands(_entry["params"])
    except Exception:
        _entry["console"] = None


def get_crosshair(crosshair_id: str) -> dict | None:
    """Entrée du catalogue pour cet id, ou None."""
    for entry in CROSSHAIRS:
        if entry["id"] == crosshair_id:
            return entry
    return None
