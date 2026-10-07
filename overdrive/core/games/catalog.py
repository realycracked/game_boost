"""Catalogue des 12 jeux pris en charge : options de lancement et optimisations concrètes."""

from __future__ import annotations

# Chaque entrée suit le contrat Module B :
#   id, name, store, steam_appid, install_hints, launch_options,
#   launch_options_note, optimizations (>= 5 réglages concrets et actuels).
# Les install_hints sont des chemins RELATIFS testés sous les racines typiques
# (C:\, C:\Program Files, C:\Program Files (x86), D:\, etc.) par detect.py.

GAMES: list[dict] = [
    {
        "id": "cs2",
        "name": "Counter-Strike 2",
        "store": "steam",
        "steam_appid": 730,
        "install_hints": [
            "Steam/steamapps/common/Counter-Strike Global Offensive",
        ],
        "launch_options": "-high -fullscreen +fps_max 0",
        "launch_options_note": (
            "Steam > Bibliothèque > clic droit sur CS2 > Propriétés > Options de lancement. "
            "Note : -novid, -tickrate et -nojoy n'ont plus d'effet dans CS2."
        ),
        "optimizations": [
            {
                "title": "Qualité des ombres : Faible",
                "detail": (
                    "Paramètres vidéo avancés > Qualité des ombres : Faible. Garde les ombres "
                    "visibles (information de jeu) pour un coût GPU minimal ; ne jamais les couper."
                ),
            },
            {
                "title": "Détail des shaders et des particules : Faible, occlusion ambiante : Désactivée",
                "detail": (
                    "Détail des shaders : Faible, détail des particules : Faible, occlusion ambiante : "
                    "Désactivée. Gros gain de FPS dans les fumées et les échanges de tirs."
                ),
            },
            {
                "title": "Anticrénelage : CMAA2 (ou MSAA 2x)",
                "detail": (
                    "Mode d'anticrénelage : CMAA2 pour un maximum de FPS, MSAA 2x si la lisibilité "
                    "des contours à longue distance prime. Éviter MSAA 4x/8x, trop coûteux."
                ),
            },
            {
                "title": "NVIDIA Reflex : Activé (+ Boost)",
                "detail": (
                    "Paramètres vidéo > NVIDIA Reflex Low Latency : Activé + Boost sur GPU NVIDIA. "
                    "Réduit la latence système quand le GPU est saturé."
                ),
            },
            {
                "title": "FPS non plafonnés : fps_max 0",
                "detail": (
                    "Console ou autoexec.cfg : fps_max 0. CS2 gère le frame pacing en subtick ; "
                    "laisser les FPS libres (ou caper juste sous la limite thermique, ex. fps_max 400)."
                ),
            },
            {
                "title": "Autoexec.cfg dans le dossier cfg du profil",
                "detail": (
                    "Placer un autoexec.cfg sous Steam/userdata/<id>/730/local/cfg (généré par "
                    "Overdrive, onglet CS2). Les reliques CS:GO (rate, cl_interp, cl_updaterate) "
                    "sont obsolètes dans CS2 et à ne pas utiliser."
                ),
            },
            {
                "title": "Super-résolution FidelityFX : Désactivée (natif)",
                "detail": (
                    "FidelityFX Super Resolution : Désactivé (résolution la plus élevée). L'upscaling "
                    "floute les silhouettes à longue distance ; préférer la résolution native."
                ),
            },
        ],
    },
    {
        "id": "valorant",
        "name": "Valorant",
        "store": "riot",
        "steam_appid": None,
        "install_hints": [
            "Riot Games/VALORANT/live",
            "Riot Games/VALORANT",
        ],
        "launch_options": None,
        "launch_options_note": (
            "Le client Riot ne prend pas d'options de lancement : tous les réglages se font "
            "dans le jeu (Paramètres > Vidéo)."
        ),
        "optimizations": [
            {
                "title": "Multithreaded Rendering : Activé",
                "detail": (
                    "Paramètres > Vidéo > Qualité graphique > Rendu multithread : Activé. "
                    "Indispensable sur tout CPU à 4 cœurs ou plus, gain de FPS majeur."
                ),
            },
            {
                "title": "Qualités Matériaux/Textures/Détails/Interface : Faible",
                "detail": (
                    "Qualité des matériaux, des textures, des détails et de l'interface : Faible. "
                    "Valorant est pensé pour rester lisible au minimum ; aucun désavantage visuel."
                ),
            },
            {
                "title": "Vignette, flou et netteté améliorée : Désactivés",
                "detail": (
                    "Vignette : Désactivé, Améliorer la netteté : Désactivé, Bloom : Désactivé, "
                    "Distorsion : Désactivé, Ombres portées (First Person Shadows) : Désactivé."
                ),
            },
            {
                "title": "Limite de FPS : désactivée en jeu, VSync off",
                "detail": (
                    "Paramètres > Vidéo > Général : « Limiter les FPS - Toujours » sur Non et VSync "
                    "Désactivé. Caper uniquement en menu/arrière-plan (ex. 60) pour soulager le GPU."
                ),
            },
            {
                "title": "NVIDIA Reflex : Activé + Boost",
                "detail": (
                    "Paramètres > Vidéo > Général > NVIDIA Reflex Low Latency : Activé + Boost "
                    "(GPU GeForce 900+). Réduit nettement la latence entrée-écran."
                ),
            },
            {
                "title": "Raw Input Buffer : Activé",
                "detail": (
                    "Paramètres > Général > Raw Input Buffer : Activé. Lecture souris plus directe, "
                    "utile avec les souris à 1000 Hz et plus."
                ),
            },
        ],
    },
    {
        "id": "fortnite",
        "name": "Fortnite",
        "store": "epic",
        "steam_appid": None,
        "install_hints": [
            "Epic Games/Fortnite",
            "Fortnite",
        ],
        "launch_options": "-USEALLAVAILABLECORES -NOSPLASH",
        "launch_options_note": (
            "Epic Games Launcher > Paramètres > Gérer les jeux > Fortnite > Arguments de ligne "
            "de commande supplémentaires."
        ),
        "optimizations": [
            {
                "title": "Mode de rendu : Performances (Alpha)",
                "detail": (
                    "Paramètres vidéo > Mode de rendu : Performances. Le plus gros gain de FPS "
                    "possible, utilisé en compétitif ; sinon DirectX 12 sur machine récente."
                ),
            },
            {
                "title": "Résolution 3D : 100 %, ombres et effets au minimum",
                "detail": (
                    "Résolution 3D : 100 % (jamais moins en compétitif), Ombres : Désactivé, "
                    "Effets : Faible, Post-traitement : Faible."
                ),
            },
            {
                "title": "Distance d'affichage : Épique",
                "detail": (
                    "Distance d'affichage : Épique. Quasi aucun coût en FPS et indispensable pour "
                    "voir les structures et joueurs lointains."
                ),
            },
            {
                "title": "Limite de FPS alignée sur l'écran",
                "detail": (
                    "Limite d'images par seconde : la fréquence de l'écran (144/240) ou un multiple "
                    "stable, VSync Désactivé. Un cap stable vaut mieux que des FPS en dents de scie."
                ),
            },
            {
                "title": "Rendu multithread : Activé",
                "detail": (
                    "Paramètres avancés > Autoriser le rendu multithread : Activé. "
                    "Gain net sur les CPU à 6 cœurs et plus."
                ),
            },
            {
                "title": "Fichier GameUserSettings.ini (réglages fins)",
                "detail": (
                    "%LOCALAPPDATA%\\FortniteGame\\Saved\\Config\\WindowsClient\\GameUserSettings.ini : "
                    "vérifier bUseVSync=False et FrameRateLimit. Fichier à passer en lecture seule si "
                    "le launcher écrase les réglages."
                ),
            },
        ],
    },
    {
        "id": "apex_legends",
        "name": "Apex Legends",
        "store": "multi",
        "steam_appid": 1172470,
        "install_hints": [
            "Steam/steamapps/common/Apex Legends",
            "EA Games/Apex",
            "Origin Games/Apex",
        ],
        "launch_options": "-novid -fullscreen +fps_max 190",
        "launch_options_note": (
            "Steam > Propriétés > Options de lancement, ou EA App > Apex Legends > Gérer > "
            "Propriétés de lancement avancées. Caper les FPS (~190) : le moteur Source d'Apex "
            "devient instable au-delà de ~250-300 FPS."
        ),
        "optimizations": [
            {
                "title": "Budget de streaming des textures selon la VRAM",
                "detail": (
                    "Paramètres vidéo > Budget de streaming des textures : Moyen pour 4-6 Go de VRAM, "
                    "Élevé pour 8 Go+. C'est le réglage « textures » réel d'Apex."
                ),
            },
            {
                "title": "Ombres dynamiques et de spot : Désactivées",
                "detail": (
                    "Ombres de spot dynamiques : Désactivé, Détail des ombres de spot : Désactivé, "
                    "Couverture des ombres du soleil : Faible. Gros gain en combat."
                ),
            },
            {
                "title": "Éclairage volumétrique : Désactivé",
                "detail": (
                    "Rayon solaire volumétrique : Désactivé. Coût GPU élevé pour un effet purement "
                    "cosmétique qui gêne la visibilité."
                ),
            },
            {
                "title": "TSAA : Désactivé pour les FPS",
                "detail": (
                    "Anticrénelage : Aucun pour un maximum de FPS et une image nette (image plus "
                    "crénelée), TSAA seulement si le scintillement gêne."
                ),
            },
            {
                "title": "Ragdolls, impacts et détails des modèles : au minimum",
                "detail": (
                    "Ragdolls : Faible, Marques d'impact : Désactivé, Détail des modèles : Moyen. "
                    "Réduit les à-coups pendant les escarmouches."
                ),
            },
            {
                "title": "Fichier videoconfig.txt",
                "detail": (
                    "%USERPROFILE%\\Saved Games\\Respawn\\Apex\\local\\videoconfig.txt : réglages fins "
                    "(ex. setting.dvs_enable \"0\" pour couper la résolution adaptative)."
                ),
            },
        ],
    },
    {
        "id": "league_of_legends",
        "name": "League of Legends",
        "store": "riot",
        "steam_appid": None,
        "install_hints": [
            "Riot Games/League of Legends",
        ],
        "launch_options": None,
        "launch_options_note": (
            "Le client Riot ne prend pas d'options de lancement : réglages dans le client "
            "(Échap > Vidéo en partie)."
        ),
        "optimizations": [
            {
                "title": "Limite de FPS : 144/240 (jamais « Illimité »)",
                "detail": (
                    "Vidéo > Limite d'images par seconde : la fréquence de l'écran ou son double. "
                    "« Illimité » fait chauffer le GPU en combat d'équipe sans bénéfice."
                ),
            },
            {
                "title": "Ombres : Désactivées ou Faibles",
                "detail": (
                    "Vidéo > Qualité des ombres : Désactivé (ou Faible). Premier réglage à baisser, "
                    "aucun impact sur la lisibilité du jeu."
                ),
            },
            {
                "title": "Qualité des effets et de l'environnement : Moyen",
                "detail": (
                    "Qualité des effets : Moyen, qualité de l'environnement : Moyen, qualité des "
                    "personnages : Moyen. Stabilise les FPS pendant les combats à 10."
                ),
            },
            {
                "title": "Anticrénelage et attente verticale : Désactivés",
                "detail": (
                    "Anticrénelage : Désactivé et Attente verticale (VSync) : Désactivé pour la "
                    "réactivité ; plein écran plutôt que fenêtré sans bordure."
                ),
            },
            {
                "title": "Masquer les effets superflus",
                "detail": (
                    "Interface > activer « Masquer les effets visuels des autres joueurs » (Eye candy) "
                    "et désactiver le retour haptique des clics ; moins de bruit visuel, FPS plus stables."
                ),
            },
            {
                "title": "Fichier game.cfg en lecture seule si besoin",
                "detail": (
                    "Riot Games\\League of Legends\\Config\\game.cfg : FrameCapType et réglages "
                    "persistants ; le passer en lecture seule si le client réinitialise les options."
                ),
            },
        ],
    },
    {
        "id": "warzone",
        "name": "Call of Duty: Warzone",
        "store": "multi",
        "steam_appid": 1962663,
        "install_hints": [
            "Call of Duty",
            "Battle.net/Call of Duty",
            "Steam/steamapps/common/Call of Duty HQ",
        ],
        "launch_options": None,
        "launch_options_note": (
            "Battle.net > Options du jeu > Arguments de ligne de commande supplémentaires : "
            "aucun argument utile et à jour n'est recommandé (les anciens -d3d11/-fullscreen "
            "ne sont plus pris en charge). Tout se règle dans le jeu."
        ),
        "optimizations": [
            {
                "title": "Limite de FPS personnalisée (jeu / menus / arrière-plan)",
                "detail": (
                    "Graphismes > Affichage > Limite d'images par seconde : Personnalisée — jeu à la "
                    "fréquence de l'écran, menus 60, arrière-plan 30. Évite la chauffe inutile."
                ),
            },
            {
                "title": "Résolution de rendu 100 + upscaling qualité",
                "detail": (
                    "Résolution de rendu : 100. Si besoin de FPS : DLSS « Qualité » (NVIDIA) ou "
                    "FSR « Qualité » plutôt que de baisser la résolution de rendu."
                ),
            },
            {
                "title": "Objectif de mémoire VRAM : 80-85 %",
                "detail": (
                    "Qualité > Objectif d'utilisation de la VRAM : 80-85 %. Au-delà, risques de "
                    "saccades quand Windows et l'overlay consomment le reste."
                ),
            },
            {
                "title": "Flou de mouvement et grain : Désactivés",
                "detail": (
                    "Flou de mouvement du monde et de l'arme : Désactivé, grain du film : 0, "
                    "profondeur de champ : Désactivé. FPS et visibilité des cibles en hausse."
                ),
            },
            {
                "title": "NVIDIA Reflex : Activé + Boost",
                "detail": (
                    "Affichage > NVIDIA Reflex Low Latency : Activé + Boost. Baisse mesurable de la "
                    "latence, surtout GPU à 95-100 % de charge."
                ),
            },
            {
                "title": "Ombres et détails au juste niveau",
                "detail": (
                    "Qualité des ombres : Faible, résolution des textures : selon VRAM (Moyen pour "
                    "8 Go), qualité des détails et textures en streaming : Faible. Laisser les "
                    "shaders se précompiler après chaque mise à jour avant de juger les performances."
                ),
            },
        ],
    },
    {
        "id": "overwatch2",
        "name": "Overwatch 2",
        "store": "multi",
        "steam_appid": 2357570,
        "install_hints": [
            "Overwatch",
            "Battle.net/Overwatch",
            "Steam/steamapps/common/Overwatch",
        ],
        "launch_options": None,
        "launch_options_note": (
            "Battle.net > Options du jeu > Arguments supplémentaires (rien d'utile à y mettre "
            "aujourd'hui) ; sur Steam, Propriétés > Options de lancement. Les réglages se font en jeu."
        ),
        "optimizations": [
            {
                "title": "Limite de FPS : Personnalisée, haute",
                "detail": (
                    "Vidéo > Limite d'images par seconde : Personnalisée, à la fréquence de l'écran "
                    "ou au-dessus (jusqu'à 600). « Basé sur l'affichage » ajoute de la latence."
                ),
            },
            {
                "title": "Réduction de la mise en mémoire tampon : Activée",
                "detail": (
                    "Vidéo > Réduire la mise en mémoire tampon : Activé (avec VSync et triple "
                    "buffering Désactivés). Latence d'entrée réduite, le réglage clé d'OW2."
                ),
            },
            {
                "title": "Échelle de rendu : 100 %",
                "detail": (
                    "Échelle de résolution de rendu : 100 % fixe (désactiver l'échelle dynamique). "
                    "Une image nette prime sur les détails pour suivre les cibles."
                ),
            },
            {
                "title": "Qualité graphique globale : Faible, textures selon VRAM",
                "detail": (
                    "Qualité des graphismes : Faible, puis remonter uniquement « Qualité des "
                    "textures » à Élevé si 6 Go de VRAM ou plus (coût FPS quasi nul)."
                ),
            },
            {
                "title": "Reflets dynamiques et brouillard local : Désactivés/Faible",
                "detail": (
                    "Reflets dynamiques : Désactivé, détail du brouillard local : Faible, ombres : "
                    "Désactivé. Les effets les plus coûteux du moteur."
                ),
            },
            {
                "title": "NVIDIA Reflex : Activé",
                "detail": (
                    "Vidéo > NVIDIA Reflex : Activé (ou Activé + Boost). Complète « Réduire la mise "
                    "en mémoire tampon » sur GPU NVIDIA."
                ),
            },
        ],
    },
    {
        "id": "r6_siege",
        "name": "Tom Clancy's Rainbow Six Siege",
        "store": "multi",
        "steam_appid": 359550,
        "install_hints": [
            "Steam/steamapps/common/Tom Clancy's Rainbow Six Siege",
            "Ubisoft/Ubisoft Game Launcher/games/Tom Clancy's Rainbow Six Siege",
        ],
        "launch_options": None,
        "launch_options_note": (
            "Aucune option de lancement utile et à jour pour Siege (Steam ou Ubisoft Connect) : "
            "les réglages passent par le jeu et GameSettings.ini."
        ),
        "optimizations": [
            {
                "title": "Mise à l'échelle du rendu : 100",
                "detail": (
                    "Affichage > Mise à l'échelle de la résolution : 100 (désactiver le rendu "
                    "dynamique). La netteté des pixels est décisive pour les head-shots à distance."
                ),
            },
            {
                "title": "Ombres : Faible, occlusion ambiante : Désactivée",
                "detail": (
                    "Qualité des ombres : Faible, occlusion ambiante : Désactivé, effets de "
                    "lentille : Désactivé, zoom avec profondeur de champ : Désactivé."
                ),
            },
            {
                "title": "Anticrénelage : T-AA (netteté ~50)",
                "detail": (
                    "Anticrénelage : T-AA avec filtre de netteté autour de 50 ; aucun AA si chaque "
                    "FPS compte (image plus crénelée)."
                ),
            },
            {
                "title": "Cap de FPS via GameSettings.ini",
                "detail": (
                    "Documents\\My Games\\Rainbow Six - Siege\\<id>\\GameSettings.ini : FPSLimit=0 "
                    "(illimité) ou une valeur stable (ex. 240) ; VSync=0 dans le jeu."
                ),
            },
            {
                "title": "Textures selon la VRAM",
                "detail": (
                    "Détail des textures : Élevé à partir de 6 Go de VRAM, Moyen en dessous. "
                    "Peu de coût FPS mais des saccades si la VRAM déborde."
                ),
            },
            {
                "title": "NVIDIA Reflex : Activé + Boost",
                "detail": (
                    "Affichage > NVIDIA Reflex Low Latency : Activé + Boost (disponible depuis "
                    "l'ajout du rendu Vulkan/DX11 moderne). Latence réduite en duel."
                ),
            },
        ],
    },
    {
        "id": "rocket_league",
        "name": "Rocket League",
        "store": "multi",
        "steam_appid": 252950,
        "install_hints": [
            "Epic Games/rocketleague",
            "Steam/steamapps/common/rocketleague",
        ],
        "launch_options": "-nomovie",
        "launch_options_note": (
            "Steam > Propriétés > Options de lancement, ou Epic > Paramètres > Rocket League > "
            "Arguments de ligne de commande supplémentaires. -nomovie saute les vidéos d'intro. "
            "(Le jeu n'est plus vendu sur Steam mais y reste jouable si déjà possédé.)"
        ),
        "optimizations": [
            {
                "title": "FPS max : au-dessus de la fréquence de l'écran",
                "detail": (
                    "Vidéo > Images par seconde max : 240 (ou le maximum stable), VSync Désactivé. "
                    "Le jeu interpole mieux avec un surplus de FPS."
                ),
            },
            {
                "title": "Détails du rendu : Performance",
                "detail": (
                    "Qualité du rendu : Haute performance, détails du monde : Performance, "
                    "détails des particules : Performance."
                ),
            },
            {
                "title": "Effets météo et intensité des effets : coupés",
                "detail": (
                    "Effets météorologiques : Désactivé, intensité des effets : Faible, "
                    "poteaux transparents : Activé (visibilité dans les coins de but)."
                ),
            },
            {
                "title": "Anticrénelage : Désactivé ou FXAA faible",
                "detail": (
                    "Anticrénelage : Désactivé pour la latence minimale, FXAA Faible si le "
                    "crénelage gêne. Éviter MLAA/SMAA élevés."
                ),
            },
            {
                "title": "Plein écran exclusif",
                "detail": (
                    "Mode d'affichage : Plein écran (pas fenêtré sans bordure) pour la latence la "
                    "plus basse et un frame pacing stable."
                ),
            },
            {
                "title": "Fichier TASystemSettings.ini (réglages fins)",
                "detail": (
                    "Documents\\My Games\\Rocket League\\TAGame\\Config\\TASystemSettings.ini : "
                    "vérifier AllowPerFrameSleep=False uniquement si des micro-saccades persistent "
                    "(augmente l'usage CPU)."
                ),
            },
        ],
    },
    {
        "id": "pubg",
        "name": "PUBG: Battlegrounds",
        "store": "steam",
        "steam_appid": 578080,
        "install_hints": [
            "Steam/steamapps/common/PUBG",
        ],
        "launch_options": None,
        "launch_options_note": (
            "Steam > Propriétés > Options de lancement : les options historiques (-malloc=system, "
            "-USEALLAVAILABLECORES, -sm4) sont sans effet ou bloquées aujourd'hui ; ne rien mettre."
        ),
        "optimizations": [
            {
                "title": "Post-traitement, ombres et effets : Très faible",
                "detail": (
                    "Graphismes > Post-traitement : Très faible, Ombres : Très faible, Effets : "
                    "Très faible. Les trois réglages les plus coûteux, sans perte de lisibilité."
                ),
            },
            {
                "title": "Végétation et distance de vue : au minimum utile",
                "detail": (
                    "Végétation : Très faible (l'herbe lointaine n'est de toute façon pas rendue "
                    "pour les adversaires), distance de vue : Moyen — les joueurs sont rendus "
                    "indépendamment de ce réglage."
                ),
            },
            {
                "title": "Anticrénelage : Moyen, netteté activée",
                "detail": (
                    "Anticrénelage : Moyen + option Netteté (Sharpen) activée. En dessous, le "
                    "scintillement de la végétation fatigue la lecture du jeu."
                ),
            },
            {
                "title": "Textures : Moyen/Élevé selon la VRAM",
                "detail": (
                    "Textures : Élevé à partir de 6 Go de VRAM, sinon Moyen. Améliore la lisibilité "
                    "des silhouettes pour un coût FPS faible."
                ),
            },
            {
                "title": "Cap de FPS stable, VSync off",
                "detail": (
                    "Limite d'images par seconde : la fréquence de l'écran (ou une valeur stable "
                    "en dessous), VSync : Désactivé, mode d'affichage : Plein écran."
                ),
            },
            {
                "title": "Fichier GameUserSettings.ini",
                "detail": (
                    "%LOCALAPPDATA%\\TslGame\\Saved\\Config\\WindowsNoEditor\\GameUserSettings.ini : "
                    "vérifier bUseVSync=False et FrameRateLimit après chaque mise à jour."
                ),
            },
        ],
    },
    {
        "id": "dota2",
        "name": "Dota 2",
        "store": "steam",
        "steam_appid": 570,
        "install_hints": [
            "Steam/steamapps/common/dota 2 beta",
        ],
        "launch_options": "-high +fps_max 0",
        "launch_options_note": (
            "Steam > Propriétés > Options de lancement. -map dota et -novid sont obsolètes sur "
            "Source 2 ; tester -vulkan séparément (gain possible selon GPU/pilotes)."
        ),
        "optimizations": [
            {
                "title": "Paramètres avancés : effets coûteux coupés",
                "detail": (
                    "Vidéo > Options avancées : Éclairage mondial de qualité : Faible, occlusion "
                    "ambiante : Désactivé, passe de lumière additive : Désactivé, animation des "
                    "portraits : Désactivé."
                ),
            },
            {
                "title": "Herbe et végétation : Désactivées",
                "detail": (
                    "Décorations : herbe Désactivé, arbres haute qualité Désactivé, qualité de "
                    "l'eau Faible. Gain net en combat autour de la rivière."
                ),
            },
            {
                "title": "Ombres : Faible",
                "detail": (
                    "Qualité des ombres : Faible (pas Désactivé : les ombres de certains sorts "
                    "restent une information utile)."
                ),
            },
            {
                "title": "FPS max : 240 ou fps_max 0",
                "detail": (
                    "Vidéo > Images maximum par seconde : 240, ou fps_max 0 en option de lancement "
                    "pour laisser libre. VSync Désactivé, plein écran exclusif."
                ),
            },
            {
                "title": "Rendu à 100 %",
                "detail": (
                    "Qualité de rendu de l'écran : 100 % (ne jamais descendre : le texte et les "
                    "barres de vie deviennent flous). Baisser d'abord les options avancées."
                ),
            },
            {
                "title": "API de rendu : tester Vulkan",
                "detail": (
                    "Option de lancement -vulkan : sur les GPU AMD et les configurations CPU-bound, "
                    "Vulkan donne souvent des FPS plus stables que DirectX 11 ; comparer sur sa machine."
                ),
            },
        ],
    },
    {
        "id": "gta_online",
        "name": "GTA Online (GTA V)",
        "store": "multi",
        "steam_appid": 271590,
        "install_hints": [
            "Steam/steamapps/common/Grand Theft Auto V",
            "Rockstar Games/Grand Theft Auto V",
            "Epic Games/GTAV",
        ],
        "launch_options": None,
        "launch_options_note": (
            "Pas d'options via les launchers : créer un fichier commandline.txt dans le dossier "
            "du jeu (ex. -fullscreen) ; la plupart des réglages passent par le jeu et settings.xml."
        ),
        "optimizations": [
            {
                "title": "MSAA : Désactivé (FXAA seul)",
                "detail": (
                    "Graphismes > MSAA : Désactivé, FXAA : Activé. Le MSAA est le réglage le plus "
                    "coûteux de GTA V, jusqu'à 40 % de FPS perdus en x4."
                ),
            },
            {
                "title": "Qualité de l'herbe : Normal",
                "detail": (
                    "Qualité de l'herbe : Normal. Réglage disproportionnellement coûteux en ligne "
                    "(missions dans les collines) ; Très élevé divise les FPS en zone rurale."
                ),
            },
            {
                "title": "Échelle de distance étendue : curseur à 0",
                "detail": (
                    "Graphismes avancés > Échelle de distance de détail étendue : 0. Ce curseur "
                    "« avancé » consomme énormément de VRAM pour un gain visuel minime."
                ),
            },
            {
                "title": "Reflets : Élevé max, sans MSAA de reflets",
                "detail": (
                    "Qualité des reflets : Élevé (pas Très élevé/Ultra), MSAA des reflets : "
                    "Désactivé. Grosse économie GPU en ville de nuit."
                ),
            },
            {
                "title": "Densité de population et variété : ~70 %",
                "detail": (
                    "Curseurs Population/Variété/Focalisation : autour de 70 %. En Online, réduit "
                    "la charge CPU (le réglage qui limite le plus les FPS en session pleine)."
                ),
            },
            {
                "title": "Ombres douces : Douces / AMD CHS-NVIDIA PCSS évités",
                "detail": (
                    "Ombres : Douces (standard). Les variantes NVIDIA PCSS/AMD CHS coûtent 10-15 % "
                    "de FPS pour une différence à peine visible en mouvement."
                ),
            },
        ],
    },
]


def get_game(game_id: str) -> dict | None:
    """Renvoie l'entrée du catalogue pour cet id, ou None."""
    for game in GAMES:
        if game["id"] == game_id:
            return game
    return None
