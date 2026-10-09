# Changelog

Toutes les évolutions notables d'Overdrive. Chaque build de `main` est publié en
[Release](https://github.com/realycracked/game_boost/releases/latest) ; seule la
plus récente est conservée.

## 1.0.0 — octobre 2026

Première version publique complète.

### Interface
- Design sombre « Midnight » façon Raycast : 5 thèmes (Midnight, Océan, Émeraude,
  Rose, Clair), 3 niveaux d'animation, survols en 3D, boutons magnétiques,
  transitions entre les pages.
- Intro animée au lancement et accueil cinématique : bannière du jeu mis en avant
  (zoom lent, parallaxe, rotation entre tes jeux), indice de performance, tuiles
  live, carrousel de jaquettes.
- Palette de commandes Ctrl+K, interface en français et en anglais.
- Toutes les animations se figent pendant une partie.

### Jeux
- 12 jeux avec leurs visuels officiels (CDN Steam, Data Dragon de Riot, API
  communautaires pour Valorant et Fortnite), mis en cache et remplaçables par une
  image personnelle.
- Détection d'installation (Steam et hors Steam), options de lancement et réglages
  par jeu.
- **Boost CS2 en un clic** : optimisations Windows ciblées, `cs2_video.txt` adapté à
  la machine (avec sauvegarde), autoexec avec `fps_max` calé sur l'écran.
- Réglages AMD Adrenalin par architecture (RDNA 4 → Polaris), détection EXPO/XMP,
  VRAM réelle des cartes de plus de 4 Go.
- Convertisseur de sensibilité (7 jeux), 12 viseurs CS2 de joueurs pros, coffre de
  sauvegarde des configurations.

### Optimisations
- 84 réglages Windows réversibles en 11 catégories, avec impact, risque et badge
  « petite config ».
- Annulation fidèle : restauration des valeurs d'origine relevées sur la machine.
- Profil « petite config » pour les PC modestes, réglages jugés contre-productifs
  retirés après audit.
- Point de restauration intégré. Aucune modification des mitigations de sécurité
  ni de la protection en temps réel de Defender.

### Outils
- Widget en jeu personnalisable (FPS via PresentMon, CPU, RAM, températures),
  Ctrl+F10, lancement au démarrage de Windows ou à l'ouverture d'un jeu.
- Moniteur temps réel, activité réseau par application, test de stabilité réseau,
  test de latence.
- Nettoyage des caches (dont shaders DirectX/NVIDIA/AMD), nettoyage planifié,
  débloat, programmes au démarrage, mode jeu automatique.
- Benchmark avant/après, conseils automatiques, rapport système, export/import de
  profil, mise à jour intégrée.
- Assistant IA (Groq, OpenAI, Anthropic, Gemini) avec clés chiffrées localement.
- Mode serveur local (`--server`), accès réseau protégé par jeton (`--host`).
