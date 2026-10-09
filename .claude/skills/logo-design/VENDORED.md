# Origine de ce skill

Copie du skill Claude **logo-design** v1.4.4 de
[kaankiziltug/logo-design-skill](https://github.com/kaankiziltug/logo-design-skill)
(commit `0ecf52e`), sous licence MIT (voir `LICENSE`). Il est chargé automatiquement par
Claude Code dans les sessions ouvertes sur ce dépôt, y compris sur le web et sur mobile :
`/logo-design`.

Différences avec l'original :

- Les 1 432 logos de référence (`assets/library/svg/`) ne sont **pas** commités : ce sont des
  marques déposées de leurs propriétaires (voir `TRADEMARKS.md`). `scripts/fetch_library.py`
  les télécharge à la demande depuis le dépôt d'origine, au commit épinglé, et vérifie leur
  empreinte SHA-256 avant de les installer. Le dossier est ignoré par git.
- `SKILL.md` : un paragraphe ajouté (« Reference library in this copy ») qui l'explique.
- `VENDORED.md` et `scripts/fetch_library.py` sont propres à ce dépôt.

Mettre à jour : recopier `skills/logo-design/` depuis un nouveau commit amont (sans
`assets/library/svg/`), puis mettre à jour `COMMIT` et `MANIFEST_SHA256` dans
`scripts/fetch_library.py`.

## Revue de sécurité (octobre 2026, commit `0ecf52e`)

Scripts, instructions et 1 432 SVG relus avant l'import : aucun appel réseau dans les
scripts, aucun `eval`/`exec`, aucune lecture de secrets, aucune installation de paquet,
aucune injection de prompt dans `SKILL.md`, `references/` ou les données, aucun script ni
lien externe dans les SVG. Points mineurs, qui ne concernent que des fichiers non fiables :
ne pas faire rendre par `render_png.py` un SVG ou un HTML d'origine inconnue (cairosvg
antérieur à 2.7 suit les liens externes d'un SVG ; Chrome exécute le JavaScript d'un HTML),
et garder les chemins d'un `spec.json` relatifs à son dossier.
