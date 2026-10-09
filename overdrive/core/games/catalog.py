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
        "process_names": ["cs2.exe"],
        "install_hints": [
            "Steam/steamapps/common/Counter-Strike Global Offensive",
        ],
        # Valeur « midrange » conservée pour la rétrocompatibilité de
        # /api/games ; les variantes par tier sont dans launch_options_tiers.
        # Le cap FPS vit désormais dans l'autoexec (une seule source de
        # vérité), plus dans les options de lancement.
        "launch_options": "-fullscreen -console -high +exec autoexec.cfg",
        "launch_options_note": (
            "Steam > Bibliothèque > clic droit sur CS2 > Propriétés > Options de lancement. "
            "-high est réservé aux CPU d'au moins 6 cœurs physiques : sur 4 cœurs, la "
            "priorité haute peut affamer le thread audio et les services Windows "
            "(saccades, crachotements). Sans effet dans CS2 : -novid, -tickrate, -nojoy, "
            "-threads, -d3d9ex, +cl_forcepreload, -refresh/-freq (la fréquence d'écran "
            "se règle dans cs2_video.txt)."
        ),
        "launch_options_tiers": {
            "lowend": "-fullscreen -console +exec autoexec.cfg",
            "midrange": "-fullscreen -console -high +exec autoexec.cfg",
            "highend": "-fullscreen -console +exec autoexec.cfg",
        },
        "launch_options_tiers_note": {
            "lowend": (
                "Pas de -high : sur 4 cœurs physiques ou moins, la priorité haute peut "
                "affamer le thread audio et les services système (saccades, "
                "crachotements). Le cap FPS vit dans l'autoexec."
            ),
            "midrange": (
                "-high acceptable dès 6 cœurs : gain faible mais réel quand des tâches "
                "de fond tournent. Le cap FPS vit dans l'autoexec."
            ),
            "highend": (
                "-high superflu (l'ordonnanceur Windows et Reflex suffisent) ; à tester "
                "en option. Le cap FPS vit dans l'autoexec."
            ),
        },
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
                "title": "Anticrénelage : MSAA 2x (4x en haut de gamme)",
                "detail": (
                    "Mode d'anticrénelage : MSAA 2x, le compromis netteté/FPS ; MSAA 4x "
                    "seulement sur machine haut de gamme (lisibilité à longue distance), "
                    "jamais 8x. CMAA2 reste un choix valide sur petite config, mais c'est "
                    "un mode distinct : il ne correspond PAS à msaa_samples 2 dans "
                    "cs2_video.txt (la valeur observée est alors 1)."
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
                "title": "Cap de FPS adapté à la machine (fps_max)",
                "detail": (
                    "Console ou autoexec.cfg : fps_max 0 (FPS libres) uniquement avec un CPU "
                    "costaud (8 cœurs ou plus). Sur un CPU modeste, fps_max 0 produit des "
                    "frametimes en dents de scie : capez à environ 2× la fréquence de "
                    "l'écran (ex. 144 Hz → fps_max 288). L'onglet CS2 d'Overdrive calcule "
                    "la valeur pour votre machine."
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
        "process_names": ["VALORANT-Win64-Shipping.exe"],
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
        "process_names": ["FortniteClient-Win64-Shipping.exe"],
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
        "process_names": ["r5apex.exe", "r5apex_dx12.exe"],
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
        "process_names": ["League of Legends.exe"],
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
        "process_names": ["cod.exe"],
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
        "process_names": ["Overwatch.exe"],
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
        "process_names": ["RainbowSix.exe", "RainbowSix_DX11.exe", "RainbowSix_Vulkan.exe"],
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
        "process_names": ["RocketLeague.exe"],
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
        "process_names": ["TslGame.exe"],
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
        "process_names": ["dota2.exe"],
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
        "process_names": ["GTA5.exe", "GTA5_Enhanced.exe"],
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


# ---------------------------------------------------------------------------
# i18n — champs anglais additifs (« launch_options_note_en », « title_en »,
# « detail_en »), injectés dans GAMES au chargement du module sans modifier
# aucune valeur existante. Les optimisations sont appariées par position.
# ---------------------------------------------------------------------------

# {id du jeu: {"note": launch_options_note_en,
#              "optimizations": [(title_en, detail_en), ...]}}
_GAMES_EN: dict[str, dict] = {
    "cs2": {
        "note": (
            "Steam > Library > right-click CS2 > Properties > Launch Options. "
            "-high is for CPUs with at least 6 physical cores: on 4 cores, "
            "high priority can starve the audio thread and Windows services "
            "(stutters, audio crackling). No effect in CS2: -novid, -tickrate, "
            "-nojoy, -threads, -d3d9ex, +cl_forcepreload, -refresh/-freq (the "
            "refresh rate lives in cs2_video.txt)."
        ),
        "launch_options_tiers_note": {
            "lowend": (
                "No -high: on 4 physical cores or fewer, high priority can "
                "starve the audio thread and system services (stutters, "
                "crackling). The FPS cap lives in the autoexec."
            ),
            "midrange": (
                "-high is fine from 6 cores up: a small but real gain when "
                "background tasks are running. The FPS cap lives in the "
                "autoexec."
            ),
            "highend": (
                "-high is unnecessary (the Windows scheduler and Reflex are "
                "enough); worth testing as an option. The FPS cap lives in "
                "the autoexec."
            ),
        },
        "optimizations": [
            ("Shadow quality: Low",
             "Advanced video settings > Shadow quality: Low. Keeps shadows "
             "visible (they are game information) at minimal GPU cost; never "
             "turn them off entirely."),
            ("Shader and particle detail: Low, ambient occlusion: Disabled",
             "Shader detail: Low, particle detail: Low, ambient occlusion: "
             "Disabled. A big FPS gain in smokes and firefights."),
            ("Anti-aliasing: MSAA 2x (4x on high-end machines)",
             "Anti-aliasing mode: MSAA 2x, the clarity/FPS trade-off; MSAA 4x "
             "only on a high-end machine (long-range readability), never 8x. "
             "CMAA2 remains a valid choice on a low-end machine, but it is a "
             "separate mode: it does NOT correspond to msaa_samples 2 in "
             "cs2_video.txt (the observed value is then 1)."),
            ("NVIDIA Reflex: Enabled (+ Boost)",
             "Video settings > NVIDIA Reflex Low Latency: Enabled + Boost on "
             "NVIDIA GPUs. Cuts system latency when the GPU is saturated."),
            ("FPS cap matched to your machine (fps_max)",
             "Console or autoexec.cfg: fps_max 0 (uncapped) only with a "
             "strong CPU (8 cores or more). On a modest CPU, fps_max 0 "
             "produces sawtooth frametimes: cap at about 2x your monitor's "
             "refresh rate (e.g. 144 Hz -> fps_max 288). Overdrive's CS2 tab "
             "computes the value for your machine."),
            ("Autoexec.cfg in the profile's cfg folder",
             "Place an autoexec.cfg under Steam/userdata/<id>/730/local/cfg "
             "(generated by Overdrive, CS2 tab). CS:GO relics (rate, "
             "cl_interp, cl_updaterate) are obsolete in CS2 and must not be "
             "used."),
            ("FidelityFX Super Resolution: Disabled (native)",
             "FidelityFX Super Resolution: Disabled (highest resolution). "
             "Upscaling blurs silhouettes at long range; prefer native "
             "resolution."),
        ],
    },
    "valorant": {
        "note": (
            "The Riot client takes no launch options: every setting is done "
            "in-game (Settings > Video)."
        ),
        "optimizations": [
            ("Multithreaded Rendering: On",
             "Settings > Video > Graphics Quality > Multithreaded Rendering: "
             "On. A must on any CPU with 4 cores or more — a major FPS gain."),
            ("Material/Texture/Detail/UI quality: Low",
             "Material, texture, detail and UI quality: Low. Valorant is "
             "designed to stay readable at minimum settings; there is no "
             "visual disadvantage."),
            ("Vignette, blur and improved clarity: Off",
             "Vignette: Off, Improve Clarity: Off, Bloom: Off, Distortion: "
             "Off, First Person Shadows: Off."),
            ("In-game FPS limit off, VSync off",
             "Settings > Video > General: “Limit FPS Always” set to Off and "
             "VSync Off. Only cap in menus/background (e.g. 60) to relieve "
             "the GPU."),
            ("NVIDIA Reflex: On + Boost",
             "Settings > Video > General > NVIDIA Reflex Low Latency: On + "
             "Boost (GeForce 900+ GPUs). Clearly reduces click-to-photon "
             "latency."),
            ("Raw Input Buffer: On",
             "Settings > General > Raw Input Buffer: On. More direct mouse "
             "reads, useful with mice polling at 1000 Hz and above."),
        ],
    },
    "fortnite": {
        "note": (
            "Epic Games Launcher > Settings > Manage Games > Fortnite > "
            "Additional Command Line Arguments."
        ),
        "optimizations": [
            ("Rendering mode: Performance (Alpha)",
             "Video settings > Rendering Mode: Performance. The biggest "
             "possible FPS gain, used in competitive play; otherwise DirectX "
             "12 on a recent machine."),
            ("3D resolution: 100%, shadows and effects at minimum",
             "3D Resolution: 100% (never lower in competitive), Shadows: Off, "
             "Effects: Low, Post Processing: Low."),
            ("View distance: Epic",
             "View Distance: Epic. Costs almost no FPS and is essential to "
             "spot distant structures and players."),
            ("FPS limit matched to your monitor",
             "Frame Rate Limit: your monitor's refresh rate (144/240) or a "
             "stable multiple, VSync Off. A steady cap beats FPS swinging up "
             "and down."),
            ("Multithreaded rendering: On",
             "Advanced settings > Allow Multithreaded Rendering: On. A clear "
             "gain on CPUs with 6 cores or more."),
            ("GameUserSettings.ini file (fine-tuning)",
             "%LOCALAPPDATA%\\FortniteGame\\Saved\\Config\\WindowsClient\\"
             "GameUserSettings.ini: check bUseVSync=False and FrameRateLimit. "
             "Set the file read-only if the launcher overwrites your "
             "settings."),
        ],
    },
    "apex_legends": {
        "note": (
            "Steam > Properties > Launch Options, or EA App > Apex Legends > "
            "Manage > Advanced Launch Properties. Cap your FPS (~190): Apex's "
            "Source engine becomes unstable beyond ~250-300 FPS."
        ),
        "optimizations": [
            ("Texture streaming budget based on VRAM",
             "Video settings > Texture Streaming Budget: Medium for 4-6 GB of "
             "VRAM, High for 8 GB+. This is Apex's real “texture” setting."),
            ("Dynamic and spot shadows: Disabled",
             "Dynamic Spot Shadows: Disabled, Spot Shadow Detail: Disabled, "
             "Sun Shadow Coverage: Low. A big gain in fights."),
            ("Volumetric lighting: Disabled",
             "Volumetric sun rays: Disabled. A high GPU cost for a purely "
             "cosmetic effect that hurts visibility."),
            ("TSAA: Disabled for FPS",
             "Anti-aliasing: None for maximum FPS and a crisp image (more "
             "jagged edges), TSAA only if shimmering bothers you."),
            ("Ragdolls, impact marks and model detail: at minimum",
             "Ragdolls: Low, Impact Marks: Disabled, Model Detail: Medium. "
             "Reduces hitching during skirmishes."),
            ("videoconfig.txt file",
             "%USERPROFILE%\\Saved Games\\Respawn\\Apex\\local\\"
             "videoconfig.txt: fine-grained settings (e.g. setting.dvs_enable "
             "\"0\" to turn off adaptive resolution)."),
        ],
    },
    "league_of_legends": {
        "note": (
            "The Riot client takes no launch options: settings live in the "
            "client (Esc > Video while in game)."
        ),
        "optimizations": [
            ("FPS cap: 144/240 (never “Uncapped”)",
             "Video > Frame Rate Cap: your monitor's refresh rate or double "
             "it. “Uncapped” heats up the GPU in teamfights for no benefit."),
            ("Shadows: Off or Low",
             "Video > Shadow Quality: Off (or Low). The first setting to "
             "lower, with zero impact on game readability."),
            ("Effects and environment quality: Medium",
             "Effects Quality: Medium, Environment Quality: Medium, Character "
             "Quality: Medium. Keeps FPS stable in 10-player teamfights."),
            ("Anti-aliasing and VSync: Off",
             "Anti-Aliasing: Off and Wait for Vertical Sync (VSync): Off for "
             "responsiveness; fullscreen rather than borderless windowed."),
            ("Hide superfluous effects",
             "Interface > enable “Hide Eye Candy” (other players' visual "
             "effects) and disable click haptic feedback; less visual noise, "
             "steadier FPS."),
            ("game.cfg file read-only if needed",
             "Riot Games\\League of Legends\\Config\\game.cfg: FrameCapType "
             "and persistent settings; set it read-only if the client keeps "
             "resetting your options."),
        ],
    },
    "warzone": {
        "note": (
            "Battle.net > Game Settings > Additional command line arguments: "
            "no useful, up-to-date argument is recommended (the old "
            "-d3d11/-fullscreen are no longer supported). Everything is set "
            "in-game."
        ),
        "optimizations": [
            ("Custom FPS limit (gameplay / menus / background)",
             "Graphics > Display > Frame Rate Limit: Custom — gameplay at "
             "your monitor's refresh rate, menus 60, background 30. Avoids "
             "pointless heat."),
            ("Render resolution 100 + quality upscaling",
             "Render Resolution: 100. If you need FPS: DLSS “Quality” "
             "(NVIDIA) or FSR “Quality” rather than lowering the render "
             "resolution."),
            ("VRAM usage target: 80-85%",
             "Quality > VRAM Scale Target: 80-85%. Beyond that, you risk "
             "stutters when Windows and overlays consume the rest."),
            ("Motion blur and film grain: Off",
             "World and Weapon Motion Blur: Off, Film Grain: 0, Depth of "
             "Field: Off. More FPS and better target visibility."),
            ("NVIDIA Reflex: On + Boost",
             "Display > NVIDIA Reflex Low Latency: On + Boost. A measurable "
             "latency drop, especially with the GPU at 95-100% load."),
            ("Shadows and details at the right level",
             "Shadow Quality: Low, texture resolution: per your VRAM (Medium "
             "for 8 GB), detail quality and streaming textures: Low. Let "
             "shaders precompile after every update before judging "
             "performance."),
        ],
    },
    "overwatch2": {
        "note": (
            "Battle.net > Game Settings > Additional arguments (nothing "
            "useful to put there today); on Steam, Properties > Launch "
            "Options. Settings are done in-game."
        ),
        "optimizations": [
            ("FPS limit: Custom, high",
             "Video > Frame Rate: Custom, at your monitor's refresh rate or "
             "above (up to 600). “Display-Based” adds latency."),
            ("Reduce Buffering: On",
             "Video > Reduce Buffering: On (with VSync and Triple Buffering "
             "Off). Lower input latency — OW2's key setting."),
            ("Render scale: 100%",
             "Render Scale: fixed at 100% (disable dynamic render scale). A "
             "sharp image beats extra detail for tracking targets."),
            ("Overall graphics quality: Low, textures per VRAM",
             "Graphics Quality: Low, then raise only “Texture Quality” to "
             "High if you have 6 GB of VRAM or more (near-zero FPS cost)."),
            ("Dynamic reflections and local fog: Off/Low",
             "Dynamic Reflections: Off, Local Fog Detail: Low, Shadow Detail: "
             "Off. The engine's most expensive effects."),
            ("NVIDIA Reflex: Enabled",
             "Video > NVIDIA Reflex: Enabled (or Enabled + Boost). "
             "Complements “Reduce Buffering” on NVIDIA GPUs."),
        ],
    },
    "r6_siege": {
        "note": (
            "No useful, up-to-date launch option for Siege (Steam or Ubisoft "
            "Connect): settings go through the game and GameSettings.ini."
        ),
        "optimizations": [
            ("Render scaling: 100",
             "Display > Resolution Scaling: 100 (disable dynamic rendering). "
             "Pixel sharpness is decisive for long-range headshots."),
            ("Shadows: Low, ambient occlusion: Off",
             "Shadow Quality: Low, Ambient Occlusion: Off, Lens Effects: Off, "
             "Zoom-In Depth of Field: Off."),
            ("Anti-aliasing: T-AA (sharpness ~50)",
             "Anti-Aliasing: T-AA with the sharpness filter around 50; no AA "
             "if every frame counts (more jagged image)."),
            ("FPS cap via GameSettings.ini",
             "Documents\\My Games\\Rainbow Six - Siege\\<id>\\"
             "GameSettings.ini: FPSLimit=0 (uncapped) or a stable value "
             "(e.g. 240); VSync=0 in-game."),
            ("Textures per your VRAM",
             "Texture Detail: High from 6 GB of VRAM, Medium below. Low FPS "
             "cost, but stutters if VRAM overflows."),
            ("NVIDIA Reflex: On + Boost",
             "Display > NVIDIA Reflex Low Latency: On + Boost (available "
             "since the modern Vulkan/DX11 renderer). Lower latency in "
             "duels."),
        ],
    },
    "rocket_league": {
        "note": (
            "Steam > Properties > Launch Options, or Epic > Settings > Rocket "
            "League > Additional Command Line Arguments. -nomovie skips the "
            "intro videos. (The game is no longer sold on Steam but remains "
            "playable there if already owned.)"
        ),
        "optimizations": [
            ("Max FPS: above your monitor's refresh rate",
             "Video > Max FPS: 240 (or your stable maximum), VSync Off. The "
             "game interpolates better with surplus FPS."),
            ("Render detail: Performance",
             "Render Quality: High Performance, World Detail: Performance, "
             "Particle Detail: Performance."),
            ("Weather effects and effect intensity: off",
             "Weather Effects: Off, Effect Intensity: Low, Transparent "
             "Goalposts: On (visibility in goal corners)."),
            ("Anti-aliasing: Off or low FXAA",
             "Anti-Aliasing: Off for minimal latency, FXAA Low if jagged "
             "edges bother you. Avoid high MLAA/SMAA."),
            ("Exclusive fullscreen",
             "Display Mode: Fullscreen (not borderless windowed) for the "
             "lowest latency and stable frame pacing."),
            ("TASystemSettings.ini file (fine-tuning)",
             "Documents\\My Games\\Rocket League\\TAGame\\Config\\"
             "TASystemSettings.ini: set AllowPerFrameSleep=False only if "
             "micro-stutters persist (raises CPU usage)."),
        ],
    },
    "pubg": {
        "note": (
            "Steam > Properties > Launch Options: the historical options "
            "(-malloc=system, -USEALLAVAILABLECORES, -sm4) are ineffective or "
            "blocked today; leave it empty."
        ),
        "optimizations": [
            ("Post-processing, shadows and effects: Very Low",
             "Graphics > Post-Processing: Very Low, Shadows: Very Low, "
             "Effects: Very Low. The three most expensive settings, with no "
             "loss of readability."),
            ("Foliage and view distance: the useful minimum",
             "Foliage: Very Low (distant grass is not rendered for opponents "
             "anyway), View Distance: Medium — players are rendered "
             "regardless of this setting."),
            ("Anti-aliasing: Medium, sharpen enabled",
             "Anti-Aliasing: Medium + the Sharpen option enabled. Any lower "
             "and foliage shimmering strains your reading of the game."),
            ("Textures: Medium/High per VRAM",
             "Textures: High from 6 GB of VRAM, otherwise Medium. Improves "
             "silhouette readability at a low FPS cost."),
            ("Stable FPS cap, VSync off",
             "Frame Rate Limit: your monitor's refresh rate (or a stable "
             "value below it), VSync: Off, Display Mode: Fullscreen."),
            ("GameUserSettings.ini file",
             "%LOCALAPPDATA%\\TslGame\\Saved\\Config\\WindowsNoEditor\\"
             "GameUserSettings.ini: check bUseVSync=False and FrameRateLimit "
             "after every update."),
        ],
    },
    "dota2": {
        "note": (
            "Steam > Properties > Launch Options. -map dota and -novid are "
            "obsolete on Source 2; test -vulkan separately (possible gain "
            "depending on GPU/drivers)."
        ),
        "optimizations": [
            ("Advanced settings: expensive effects off",
             "Video > Advanced Options: World Lighting Quality: Low, Ambient "
             "Occlusion: Off, Additive Light Pass: Off, Animate Portraits: "
             "Off."),
            ("Grass and foliage: Disabled",
             "Decorations: Grass Off, High Quality Trees Off, Water Quality "
             "Low. A clear gain in fights around the river."),
            ("Shadows: Low",
             "Shadow Quality: Low (not Off: the shadows of some spells remain "
             "useful information)."),
            ("Max FPS: 240 or fps_max 0",
             "Video > Maximum Frames Per Second: 240, or fps_max 0 as a "
             "launch option to leave it uncapped. VSync Off, exclusive "
             "fullscreen."),
            ("Rendering at 100%",
             "Game Screen Render Quality: 100% (never go lower: text and "
             "health bars turn blurry). Lower the advanced options first."),
            ("Render API: try Vulkan",
             "The -vulkan launch option: on AMD GPUs and CPU-bound setups, "
             "Vulkan often delivers steadier FPS than DirectX 11; compare on "
             "your own machine."),
        ],
    },
    "gta_online": {
        "note": (
            "No options via the launchers: create a commandline.txt file in "
            "the game folder (e.g. -fullscreen); most settings go through the "
            "game and settings.xml."
        ),
        "optimizations": [
            ("MSAA: Off (FXAA only)",
             "Graphics > MSAA: Off, FXAA: On. MSAA is GTA V's most expensive "
             "setting, up to 40% of FPS lost at x4."),
            ("Grass quality: Normal",
             "Grass Quality: Normal. A disproportionately expensive setting "
             "online (missions in the hills); Very High halves FPS in rural "
             "areas."),
            ("Extended distance scaling: slider at 0",
             "Advanced Graphics > Extended Distance Scaling: 0. This "
             "“advanced” slider devours VRAM for a minimal visual gain."),
            ("Reflections: High at most, no reflection MSAA",
             "Reflection Quality: High (not Very High/Ultra), Reflection "
             "MSAA: Off. A big GPU saving in the city at night."),
            ("Population density and variety: ~70%",
             "Population Density/Variety/Focus sliders: around 70%. Online, "
             "reduces CPU load (the setting that limits FPS most in a full "
             "session)."),
            ("Soft shadows: Softest / avoid NVIDIA PCSS-AMD CHS",
             "Shadows: Soft (standard). The NVIDIA PCSS/AMD CHS variants cost "
             "10-15% of FPS for a barely visible difference in motion."),
        ],
    },
}

for _game in GAMES:
    _en = _GAMES_EN.get(_game["id"], {})
    _game["launch_options_note_en"] = _en.get(
        "note", _game.get("launch_options_note"))
    # Notes de tiers (cs2 uniquement à ce jour) : miroir EN additif.
    _tiers_note_en = _en.get("launch_options_tiers_note")
    if isinstance(_tiers_note_en, dict):
        _game["launch_options_tiers_note_en"] = _tiers_note_en
    _pairs = _en.get("optimizations", [])
    for _index, _opt in enumerate(_game["optimizations"]):
        if _index < len(_pairs):
            _opt["title_en"], _opt["detail_en"] = _pairs[_index]
        else:
            _opt["title_en"] = _opt["title"]
            _opt["detail_en"] = _opt["detail"]
