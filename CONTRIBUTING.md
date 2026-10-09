# Contribuer à Overdrive

Merci de ton intérêt ! Les rapports de bug, idées et pull requests sont bienvenus.

## Signaler un bug ou proposer une idée

Ouvre une [issue](https://github.com/realycracked/game_boost/issues/new/choose) avec le modèle adapté. Pour un bug,
joins si possible le **rapport système** (Réglages → Télécharger le rapport
système) : il contient la configuration et la version, sans aucune clé API.

## Développer

```bash
git clone https://github.com/realycracked/game_boost.git
cd game_boost
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
python run.py --server        # interface sur http://127.0.0.1:8787
python -m pytest              # tests
```

L'interface et l'API tournent aussi sous Linux et macOS ; les optimisations
Windows y sont seulement affichées. `python build_exe.py` construit
l'exécutable (PyInstaller) sous Windows.

## Règles du projet

- **Réversible avant tout** : toute optimisation ajoutée au catalogue
  (`overdrive/core/tweaks/catalog.py`) a une action `revert` qui restaure l'état
  par défaut de Windows, une description honnête de son effet, un niveau de risque
  et sa traduction anglaise.
- **Jamais** de modification des mitigations de sécurité (Spectre/Meltdown) ni de
  la protection en temps réel de Windows Defender. Un test le vérifie.
- **Aucune dépendance front** : l'interface reste en HTML/CSS/JS sans framework ni
  CDN. Les animations n'utilisent que `transform`, `opacity` et `filter`, et se
  coupent pendant les parties.
- **Pas de télémétrie**, pas de nouvelle connexion sortante sans la documenter
  dans le README.
- Les visuels des jeux ne sont jamais ajoutés au dépôt (voir
  [THIRD_PARTY.md](THIRD_PARTY.md)).
- Toute chaîne visible existe en français et en anglais.

## Pull requests

1. Pars de `main` et garde une PR par sujet.
2. Vérifie que `python -m pytest` passe et que l'interface s'affiche sans erreur
   dans la console du navigateur.
3. La CI construit `Overdrive.exe` pour chaque PR (artefact téléchargeable) ; la
   Release publique est publiée automatiquement à la fusion dans `main`.
