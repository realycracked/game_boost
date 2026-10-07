"""Questionnaire de premier lancement (7 questions) et calcul du profil d'optimisation."""

from __future__ import annotations

QUESTIONS: list[dict] = [
    {
        "id": "jeux",
        "question": "À quels types de jeux jouez-vous le plus souvent ?",
        "multi": True,
        "options": [
            {"id": "fps_competitif", "label": "FPS compétitifs (CS2, Valorant, Overwatch 2...)"},
            {"id": "battle_royale", "label": "Battle royale (Fortnite, Warzone, Apex Legends...)"},
            {"id": "moba", "label": "MOBA (League of Legends, Dota 2...)"},
            {"id": "solo_aaa", "label": "Grands jeux solo (AAA)"},
            {"id": "un_peu_de_tout", "label": "Un peu de tout"},
        ],
    },
    {
        "id": "objectif",
        "question": "Qu'est-ce qui compte le plus pour vous en jeu ?",
        "multi": False,
        "options": [
            {"id": "max_fps", "label": "Un maximum de FPS, quitte à sacrifier les graphismes"},
            {"id": "latence", "label": "Une réactivité parfaite (latence et input lag minimaux)"},
            {"id": "equilibre", "label": "Un bon équilibre entre performances et qualité visuelle"},
            {"id": "stream", "label": "Une machine stable pour jouer et streamer en même temps"},
        ],
    },
    {
        "id": "config",
        "question": "Comment décririez-vous votre PC ?",
        "multi": False,
        "options": [
            {"id": "haut_de_gamme", "label": "Haut de gamme et récent"},
            {"id": "milieu_de_gamme", "label": "Milieu de gamme"},
            {"id": "modeste", "label": "Modeste ou un peu ancien"},
            {"id": "je_ne_sais_pas", "label": "Je ne sais pas trop"},
        ],
    },
    {
        "id": "connexion",
        "question": "Comment votre PC est-il connecté à Internet ?",
        "multi": False,
        "options": [
            {"id": "fibre", "label": "Fibre, en câble Ethernet"},
            {"id": "adsl_4g", "label": "ADSL ou 4G/5G"},
            {"id": "wifi", "label": "En Wi-Fi"},
            {"id": "je_ne_sais_pas", "label": "Je ne sais pas"},
        ],
    },
    {
        "id": "risque",
        "question": "Jusqu'où acceptez-vous d'aller dans les optimisations ?",
        "multi": False,
        "options": [
            {"id": "sur", "label": "Uniquement les réglages sûrs"},
            {"id": "modere", "label": "Les réglages sûrs et modérés"},
            {"id": "avance", "label": "Tout, y compris les réglages avancés"},
        ],
    },
    {
        "id": "usage",
        "question": "À quoi sert votre PC en dehors du jeu ?",
        "multi": False,
        "options": [
            {"id": "jeu_uniquement", "label": "À rien d'autre, il ne sert qu'à jouer"},
            {"id": "bureautique", "label": "Bureautique, études, navigation"},
            {"id": "creation", "label": "Création de contenu ou stream"},
            {"id": "dev", "label": "Développement et informatique"},
        ],
    },
    {
        "id": "peripheriques",
        "question": "Quelle souris utilisez-vous ?",
        "multi": False,
        "options": [
            {"id": "gamer", "label": "Une souris gamer avec son logiciel (G HUB, Synapse...)"},
            {"id": "standard", "label": "Une souris standard"},
            {"id": "je_ne_sais_pas", "label": "Je ne sais pas"},
        ],
    },
]

_PROFILES: dict[str, dict] = {
    "fps": {
        "label": "Priorité aux FPS",
        "description": (
            "Votre machine sera réglée pour produire un maximum d'images par seconde, "
            "au détriment du confort visuel de Windows. Idéal pour le jeu compétitif "
            "sur écran à haute fréquence de rafraîchissement."
        ),
    },
    "latence": {
        "label": "Priorité à la latence",
        "description": (
            "L'objectif est une réactivité maximale : réduction de l'input lag, du ping "
            "et des micro-saccades. Parfait pour les FPS compétitifs où chaque "
            "milliseconde compte."
        ),
    },
    "equilibre": {
        "label": "Équilibre performances et confort",
        "description": (
            "Un compromis raisonnable : de meilleures performances en jeu sans sacrifier "
            "le confort d'utilisation au quotidien. Le choix le plus polyvalent pour un "
            "PC qui sert aussi à autre chose."
        ),
    },
    "stream": {
        "label": "Stabilité pour le stream",
        "description": (
            "La priorité est une machine stable capable d'encaisser le jeu et l'encodage "
            "en même temps. Les réglages privilégient la constance des performances "
            "plutôt que le pic de FPS."
        ),
    },
}

_OBJECTIF_TO_PROFILE = {
    "max_fps": "fps",
    "latence": "latence",
    "equilibre": "equilibre",
    "stream": "stream",
}

_RISK_ORDER = {"sur": 0, "modere": 1, "avance": 2}


def _single(answers: dict, question_id: str) -> str | None:
    """Réponse unique d'une question (prend la première si une liste est fournie)."""
    value = answers.get(question_id)
    if isinstance(value, list):
        return value[0] if value else None
    return value if isinstance(value, str) else None


def _multiple(answers: dict, question_id: str) -> list[str]:
    """Réponses multiples d'une question, toujours sous forme de liste."""
    value = answers.get(question_id)
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    if isinstance(value, str):
        return [value]
    return []


def _recommended_tweaks(profile_id: str, risk_max: str) -> list[str]:
    """Ids de tweaks du catalogue adaptés au profil et au niveau de risque accepté."""
    try:
        # Import tardif pour éviter les cycles d'import.
        from overdrive.core.tweaks import catalog  # noqa: PLC0415
    except ModuleNotFoundError:
        # Secours uniquement si le module catalogue n'existe pas (développement).
        return []
    max_level = _RISK_ORDER.get(risk_max, 0)
    recommended: list[str] = []
    for tweak in getattr(catalog, "TWEAKS", []):
        profiles = tweak.get("default_for", [])
        risk_level = _RISK_ORDER.get(tweak.get("risk", "avance"), 2)
        if profile_id in profiles and risk_level <= max_level:
            recommended.append(tweak["id"])
    return recommended


def _build_notes(answers: dict, profile_id: str, risk_max: str) -> list[str]:
    """Conseils personnalisés selon les réponses du questionnaire."""
    notes: list[str] = []

    connexion = _single(answers, "connexion")
    if connexion == "wifi":
        notes.append(
            "Vous jouez en Wi-Fi : passer sur un câble Ethernet est la meilleure "
            "optimisation réseau possible, bien plus efficace que n'importe quel tweak."
        )
    elif connexion == "adsl_4g":
        notes.append(
            "Avec une connexion ADSL ou 4G/5G, pensez à couper les téléchargements et "
            "mises à jour automatiques pendant vos sessions pour préserver votre ping."
        )

    config = _single(answers, "config")
    if config == "modeste":
        notes.append(
            "Sur une configuration modeste, le plus gros gain vient des réglages en jeu : "
            "baissez la résolution ou activez FSR/DLSS, et utilisez le nettoyage de "
            "caches d'Overdrive pour libérer de l'espace disque."
        )
    elif config == "je_ne_sais_pas":
        notes.append(
            "La page d'accueil d'Overdrive affiche le détail de votre matériel : "
            "jetez-y un œil pour savoir ce que votre PC a dans le ventre."
        )

    jeux = _multiple(answers, "jeux")
    if "fps_competitif" in jeux or "battle_royale" in jeux:
        notes.append(
            "Pour les jeux compétitifs, limitez vos FPS juste en dessous du maximum "
            "atteignable de façon stable : les frametimes réguliers comptent plus que "
            "le pic de FPS."
        )

    usage = _single(answers, "usage")
    if usage == "creation":
        notes.append(
            "Vous créez du contenu : évitez de désactiver trop de services Windows, "
            "certains logiciels de capture et de montage en dépendent."
        )
    elif usage == "dev":
        notes.append(
            "Vous développez sur cette machine : vérifiez chaque tweak de services "
            "avant de l'appliquer, certains outils (virtualisation, indexation) "
            "peuvent en dépendre."
        )

    peripheriques = _single(answers, "peripheriques")
    if peripheriques == "gamer":
        notes.append(
            "Avec une souris gamer, réglez la sensibilité uniquement dans son logiciel "
            "et en jeu : le tweak qui désactive la précision du pointeur Windows évite "
            "toute accélération parasite."
        )
    elif peripheriques == "standard":
        notes.append(
            "Même avec une souris standard, désactiver l'accélération du pointeur "
            "Windows rend la visée plus prévisible dans tous les jeux."
        )

    if risk_max == "avance":
        notes.append(
            "Vous avez choisi les optimisations avancées : créez systématiquement un "
            "point de restauration depuis Overdrive avant de les appliquer."
        )
    else:
        notes.append(
            "Tous les tweaks appliqués par Overdrive sont réversibles, mais un point de "
            "restauration avant la première application reste une bonne habitude."
        )

    if profile_id == "stream":
        notes.append(
            "Pour le stream, utilisez l'encodeur matériel de votre GPU (NVENC, AMF ou "
            "QuickSync) dans OBS : il coûte beaucoup moins de FPS que l'encodage x264."
        )

    return notes


def compute_profile(answers: dict) -> dict:
    """Calcule le profil d'optimisation à partir des réponses au questionnaire.

    ``answers`` : ``{question_id: option_id | [option_ids]}``.
    """
    if not isinstance(answers, dict):
        answers = {}

    objectif = _single(answers, "objectif")
    profile_id = _OBJECTIF_TO_PROFILE.get(objectif or "", "equilibre")

    # Un joueur "équilibre" qui crée du contenu/stream bascule sur le profil stream.
    if profile_id == "equilibre" and _single(answers, "usage") == "creation":
        profile_id = "stream"

    risque = _single(answers, "risque")
    risk_max = risque if risque in _RISK_ORDER else "sur"

    meta = _PROFILES[profile_id]
    return {
        "id": profile_id,
        "label": meta["label"],
        "description": meta["description"],
        "risk_max": risk_max,
        "recommended_tweaks": _recommended_tweaks(profile_id, risk_max),
        "notes": _build_notes(answers, profile_id, risk_max),
    }
