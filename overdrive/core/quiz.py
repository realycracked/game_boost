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
    "petite_config": {
        "label": "Petite config optimisée",
        "description": (
            "Réglages pensés pour les PC modestes : alléger Windows au maximum "
            "(processus de fond, widgets, préchargements) sans toucher à ce qui "
            "aide une petite machine, comme la compression mémoire. Soyons "
            "honnêtes : les plus gros gains restent les réglages en jeu et, à "
            "terme, un peu plus de RAM ou un SSD."
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
    """Ids de tweaks du catalogue adaptés au profil et au niveau de risque accepté.

    Pour le profil ``petite_config``, les tweaks marqués ``lowend=True``
    dans le catalogue sont aussi retenus (toujours filtrés par le risque),
    en plus du mécanisme ``default_for`` existant. Le champ ``lowend`` est
    lu de façon tolérante : absent du catalogue, il vaut ``False`` et la
    sélection retombe proprement sur ``default_for`` seul.
    """
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
        if risk_level > max_level:
            continue
        selected = profile_id in profiles
        if not selected and profile_id == "petite_config":
            selected = tweak.get("lowend") is True
        if selected:
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

    if profile_id == "petite_config":
        notes.append(
            "Les tweaks Windows rapportent quelques FPS sur une petite config, pas "
            "des miracles : les plus gros gains viennent des réglages en jeu "
            "(résolution, FSR), de la fermeture du navigateur et des launchers "
            "pendant la partie, et à terme d'un ajout de RAM ou d'un SSD."
        )
        notes.append(
            "Fermez navigateur, Discord en vidéo et launchers pendant le jeu : avec "
            "8 Go de RAM, chaque application de fond se paie en saccades."
        )
        notes.append(
            "Sur un PC portable, le plan Performances ultimes augmente chauffe et "
            "consommation : gardez-le pour les sessions branchées sur secteur."
        )

    return notes


def compute_profile(answers: dict, tier: str | None = None) -> dict:
    """Calcule le profil d'optimisation à partir des réponses au questionnaire.

    ``answers`` : ``{question_id: option_id | [option_ids]}``.
    ``tier`` : tier matériel optionnel (valeur de
    :func:`overdrive.core.hardware.hardware_tier`), utilisé pour basculer
    sur le profil « petite_config » quand l'utilisateur ne sait pas décrire
    sa machine. L'appel à un seul argument reste valide (rétro-compatible).
    """
    if not isinstance(answers, dict):
        answers = {}

    objectif = _single(answers, "objectif")
    profile_id = _OBJECTIF_TO_PROFILE.get(objectif or "", "equilibre")

    # Un joueur "équilibre" qui crée du contenu/stream bascule sur le profil stream.
    if profile_id == "equilibre" and _single(answers, "usage") == "creation":
        profile_id = "stream"

    # En dernier (priorité maximale) : une machine déclarée modeste — ou
    # détectée « lowend » quand l'utilisateur ne sait pas — prend le profil
    # dédié aux petites configurations.
    config = _single(answers, "config")
    if config == "modeste":
        profile_id = "petite_config"
    elif config == "je_ne_sais_pas" and tier == "lowend":
        profile_id = "petite_config"

    risque = _single(answers, "risque")
    risk_max = risque if risque in _RISK_ORDER else "sur"

    meta = _PROFILES[profile_id]
    return {
        "id": profile_id,
        "label": meta["label"],
        "label_en": meta.get("label_en", meta["label"]),
        "description": meta["description"],
        "description_en": meta.get("description_en", meta["description"]),
        "risk_max": risk_max,
        "recommended_tweaks": _recommended_tweaks(profile_id, risk_max),
        "notes": _build_notes(answers, profile_id, risk_max),
        "notes_en": _build_notes_en(answers, profile_id, risk_max),
    }


# ---------------------------------------------------------------------------
# i18n — champs anglais additifs (« question_en », « label_en »,
# « description_en », « notes_en »), injectés dans QUESTIONS et _PROFILES au
# chargement du module sans modifier aucune valeur existante.
# ---------------------------------------------------------------------------

# {id de question: {"question": question_en, "options": {id: label_en}}}
_QUESTIONS_EN: dict[str, dict] = {
    "jeux": {
        "question": "Which types of games do you play most often?",
        "options": {
            "fps_competitif": "Competitive FPS (CS2, Valorant, Overwatch 2...)",
            "battle_royale": "Battle royale (Fortnite, Warzone, Apex Legends...)",
            "moba": "MOBA (League of Legends, Dota 2...)",
            "solo_aaa": "Big single-player games (AAA)",
            "un_peu_de_tout": "A bit of everything",
        },
    },
    "objectif": {
        "question": "What matters most to you in-game?",
        "options": {
            "max_fps": "Maximum FPS, even at the cost of graphics",
            "latence": "Perfect responsiveness (minimal latency and input lag)",
            "equilibre": "A good balance between performance and visual quality",
            "stream": "A stable machine for gaming and streaming at the same time",
        },
    },
    "config": {
        "question": "How would you describe your PC?",
        "options": {
            "haut_de_gamme": "High-end and recent",
            "milieu_de_gamme": "Mid-range",
            "modeste": "Modest or a bit old",
            "je_ne_sais_pas": "I'm not really sure",
        },
    },
    "connexion": {
        "question": "How is your PC connected to the Internet?",
        "options": {
            "fibre": "Fiber, over an Ethernet cable",
            "adsl_4g": "DSL or 4G/5G",
            "wifi": "Over Wi-Fi",
            "je_ne_sais_pas": "I don't know",
        },
    },
    "risque": {
        "question": "How far are you willing to go with optimizations?",
        "options": {
            "sur": "Safe tweaks only",
            "modere": "Safe and moderate tweaks",
            "avance": "Everything, including advanced tweaks",
        },
    },
    "usage": {
        "question": "What else is your PC used for besides gaming?",
        "options": {
            "jeu_uniquement": "Nothing else, it's only for gaming",
            "bureautique": "Office work, studies, browsing",
            "creation": "Content creation or streaming",
            "dev": "Software development and IT",
        },
    },
    "peripheriques": {
        "question": "Which mouse do you use?",
        "options": {
            "gamer": "A gaming mouse with its own software (G HUB, Synapse...)",
            "standard": "A standard mouse",
            "je_ne_sais_pas": "I don't know",
        },
    },
}

_PROFILES_EN: dict[str, dict] = {
    "fps": {
        "label": "FPS first",
        "description": (
            "Your machine will be tuned to push out as many frames per second "
            "as possible, at the expense of Windows' visual comfort. Ideal for "
            "competitive gaming on a high refresh rate monitor."
        ),
    },
    "latence": {
        "label": "Latency first",
        "description": (
            "The goal is maximum responsiveness: lower input lag, ping and "
            "micro-stutter. Perfect for competitive FPS where every "
            "millisecond counts."
        ),
    },
    "equilibre": {
        "label": "Balanced performance and comfort",
        "description": (
            "A sensible compromise: better in-game performance without "
            "sacrificing day-to-day comfort. The most versatile choice for a "
            "PC that is also used for other things."
        ),
    },
    "stream": {
        "label": "Stability for streaming",
        "description": (
            "The priority is a stable machine able to handle gaming and "
            "encoding at the same time. Settings favor consistent performance "
            "over peak FPS."
        ),
    },
    "petite_config": {
        "label": "Low-end tuned",
        "description": (
            "Settings designed for modest PCs: trim Windows down as much as "
            "possible (background processes, widgets, preloading) without "
            "touching what actually helps a small machine, such as memory "
            "compression. Let's be honest: the biggest gains still come from "
            "in-game settings and, down the road, a bit more RAM or an SSD."
        ),
    },
}

for _question in QUESTIONS:
    _q_en = _QUESTIONS_EN.get(_question["id"], {})
    _question["question_en"] = _q_en.get("question", _question["question"])
    _labels_en = _q_en.get("options", {})
    for _option in _question["options"]:
        _option["label_en"] = _labels_en.get(_option["id"], _option["label"])

for _profile_id, _meta_en in _PROFILES_EN.items():
    if _profile_id in _PROFILES:
        _PROFILES[_profile_id]["label_en"] = _meta_en["label"]
        _PROFILES[_profile_id]["description_en"] = _meta_en["description"]


def _build_notes_en(answers: dict, profile_id: str, risk_max: str) -> list[str]:
    """Mêmes conseils personnalisés que ``_build_notes``, en anglais.

    La logique de sélection est strictement identique à ``_build_notes`` afin
    que ``notes`` et ``notes_en`` restent alignés élément par élément.
    """
    notes: list[str] = []

    connexion = _single(answers, "connexion")
    if connexion == "wifi":
        notes.append(
            "You play over Wi-Fi: switching to an Ethernet cable is the best "
            "network optimization there is, far more effective than any tweak."
        )
    elif connexion == "adsl_4g":
        notes.append(
            "On a DSL or 4G/5G connection, remember to pause downloads and "
            "automatic updates during your sessions to protect your ping."
        )

    config = _single(answers, "config")
    if config == "modeste":
        notes.append(
            "On a modest setup, the biggest gain comes from in-game settings: "
            "lower the resolution or enable FSR/DLSS, and use Overdrive's "
            "cache cleanup to free up disk space."
        )
    elif config == "je_ne_sais_pas":
        notes.append(
            "Overdrive's home page shows the details of your hardware: take a "
            "look to find out what your PC is really made of."
        )

    jeux = _multiple(answers, "jeux")
    if "fps_competitif" in jeux or "battle_royale" in jeux:
        notes.append(
            "For competitive games, cap your FPS just below the maximum you "
            "can hold consistently: steady frametimes matter more than peak "
            "FPS."
        )

    usage = _single(answers, "usage")
    if usage == "creation":
        notes.append(
            "You create content: avoid disabling too many Windows services, "
            "as some capture and editing software depends on them."
        )
    elif usage == "dev":
        notes.append(
            "You develop on this machine: review every service tweak before "
            "applying it, since some tools (virtualization, indexing) may "
            "depend on them."
        )

    peripheriques = _single(answers, "peripheriques")
    if peripheriques == "gamer":
        notes.append(
            "With a gaming mouse, set sensitivity only in its software and "
            "in-game: the tweak that disables Windows' pointer precision "
            "prevents any stray acceleration."
        )
    elif peripheriques == "standard":
        notes.append(
            "Even with a standard mouse, disabling Windows pointer "
            "acceleration makes your aim more predictable in every game."
        )

    if risk_max == "avance":
        notes.append(
            "You chose advanced optimizations: always create a restore point "
            "from Overdrive before applying them."
        )
    else:
        notes.append(
            "Every tweak Overdrive applies is reversible, but creating a "
            "restore point before the first run remains a good habit."
        )

    if profile_id == "stream":
        notes.append(
            "For streaming, use your GPU's hardware encoder (NVENC, AMF or "
            "QuickSync) in OBS: it costs far fewer FPS than x264 encoding."
        )

    if profile_id == "petite_config":
        notes.append(
            "Windows tweaks buy a few FPS on a low-end PC, not miracles: the "
            "biggest gains come from in-game settings (resolution, FSR), from "
            "closing your browser and launchers while you play, and down the "
            "road from adding RAM or an SSD."
        )
        notes.append(
            "Close your browser, Discord video calls and launchers while "
            "gaming: with 8 GB of RAM, every background app costs you "
            "stutter."
        )
        notes.append(
            "On a laptop, the Ultimate Performance plan increases heat and "
            "power draw: save it for sessions plugged into the mains."
        )

    return notes
