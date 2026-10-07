# Overdrive

Optimiseur PC gaming tout-en-un pour Windows 10/11 : optimisations système
réversibles, détection de jeux, nettoyage, programmes recommandés et assistant
IA — dans une interface locale claire, sans télémétrie.

L'application tourne entièrement sur votre machine : un petit serveur local
(FastAPI) sert une interface web affichée dans une fenêtre native.

## Fonctionnalités

- **Optimisations** : plus de 70 réglages Windows classés par catégorie
  (alimentation, visuels, jeux, système, mémoire, réseau, GPU, stockage,
  confidentialité, services, périphériques). Chaque optimisation affiche son
  impact et son niveau de risque, et dispose d'une annulation réelle.
  Création de point de restauration en un clic.
- **Profil personnalisé** : un questionnaire au premier lancement (7 questions)
  détermine votre profil (FPS maximum, latence minimale, équilibre ou stream)
  et présélectionne les optimisations adaptées.
- **Jeux** : détection de 12 jeux populaires (Steam et autres lanceurs),
  options de lancement recommandées et réglages précis par jeu. Panneau dédié
  Counter-Strike 2 : profils `userdata`, écriture d'un `autoexec.cfg`
  recommandé (avec sauvegarde de l'existant), analyse des réglages vidéo.
- **Nettoyage** : analyse puis suppression des fichiers temporaires, caches de
  shaders (DirectX, NVIDIA), vignettes, cache Windows Update et corbeille.
- **Programmes recommandés** : 12 outils utiles aux joueurs (monitoring,
  pilotes, capture...), installables en un clic via winget.
- **Assistant IA** (optionnel) : posez vos questions d'optimisation à un
  assistant qui connaît votre matériel et votre profil. Fournisseurs pris en
  charge : Groq (clé gratuite sur [console.groq.com](https://console.groq.com)),
  OpenAI, Anthropic, Gemini. Il faut fournir votre propre clé API.

## Téléchargement (Windows)

L'exécutable est construit automatiquement par GitHub Actions :

- **Releases** : la dernière release (`v1.0.0-build.N`) contient
  `Overdrive.exe`, prêt à lancer.
- **Artifacts** : chaque exécution du workflow « Build Overdrive.exe » publie
  aussi l'artefact `Overdrive-exe`.

Au lancement :

- Windows demande l'élévation administrateur (UAC) : nécessaire pour modifier
  les réglages système.
- SmartScreen peut afficher un avertissement (exécutable non signé) :
  « Informations complémentaires » puis « Exécuter quand même ».

## Utilisation

- `Overdrive.exe` : lance l'application dans une fenêtre native (navigateur en
  secours si la fenêtre n'est pas disponible).
- `Overdrive.exe --server` : mode serveur sans fenêtre, accessible depuis le
  réseau local (port 8787 par défaut).
- Options : `--port N`, `--host ADRESSE`, `--browser` (force le navigateur),
  `--no-open` (n'ouvre rien).

Le journal est écrit dans `%APPDATA%\Overdrive\overdrive.log`.

## Développement

Python 3.11+ requis (fonctionne aussi sous Linux : les optimisations Windows
sont alors marquées non disponibles, utile pour développer l'interface).

```bash
pip install -r requirements.txt
python run.py            # fenêtre native (ou navigateur)
python run.py --server   # mode serveur : http://127.0.0.1:8787
```

Construction de l'exécutable (Windows) :

```bash
pip install pyinstaller
python build_exe.py      # produit dist/Overdrive.exe
```

## Avertissements

- Les optimisations modifient des réglages Windows (registre, services). Elles
  sont choisies pour être sûres et documentées, et chacune dispose d'une
  annulation — créez néanmoins un point de restauration avant d'appliquer des
  optimisations marquées « avancé ».
- Overdrive ne touche jamais aux protections de sécurité du système
  (mitigations CPU, antivirus temps réel).

## Confidentialité

- Aucune donnée n'est collectée ni envoyée : tout reste sur votre machine.
- Les clés API de l'assistant sont chiffrées localement et ne quittent jamais
  votre machine, sauf vers l'API du fournisseur que vous avez choisi.
