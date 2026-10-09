# Composants tiers

## PresentMon

Overdrive embarque, lorsqu'il est disponible, le binaire console **PresentMon**
d'Intel pour mesurer les FPS en temps réel dans le widget overlay.

- Projet : <https://github.com/GameTechDev/PresentMon>
- Auteur : Intel Corporation
- Licence : MIT (reproduite ci-dessous)

```text
MIT License

Copyright (C) 2017-2024 Intel Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Le binaire `PresentMon.exe` est téléchargé par la CI depuis les Releases
officielles du dépôt GameTechDev/PresentMon (version épinglée) et embarqué
tel quel, sans modification, dans `Overdrive.exe`. Si le téléchargement
échoue, l'application est construite sans PresentMon : le widget affiche
alors « — » pour les FPS.

## Visuels des jeux (jaquettes, bannières, logos)

Les images des jeux affichées par Overdrive (jaquettes, bannières, visuels
« héros », logos, portraits de personnages) **appartiennent à leurs éditeurs
respectifs** (Valve, Riot Games, Epic Games, Electronic Arts, Activision
Blizzard, Ubisoft, Psyonix, KRAFTON, Rockstar Games, etc.) et restent
protégées par leurs droits. Elles ne sont **jamais redistribuées** : ni dans ce
dépôt, ni dans `Overdrive.exe`.

Elles sont téléchargées à l'exécution, sur la machine de l'utilisateur, puis
mises en cache localement (`%APPDATA%\Overdrive\art\`) depuis :

- le CDN officiel de Steam (`shared.akamai.steamstatic.com`, repli
  `cdn.cloudflare.steamstatic.com`) pour les jeux distribués sur Steam ;
- Data Dragon, le CDN officiel de Riot Games
  (`ddragon.leagueoflegends.com`), pour League of Legends ;
- des API communautaires non officielles : <https://valorant-api.com>
  (Valorant) et <https://fortnite-api.com> (Fortnite, images d'actualité
  hébergées par Epic Games). Ces services ne sont ni affiliés à Riot Games ni
  à Epic Games.

Overdrive n'est affilié à aucun de ces éditeurs ; les visuels servent
uniquement à identifier les jeux dans l'interface. L'utilisateur peut
remplacer chaque visuel par sa propre image (Réglages > Images des jeux).

_Game artwork (covers, banners, logos) belongs to its respective publishers.
It is never shipped in this repository or in the executable: it is
downloaded at runtime from the publishers' CDNs (Steam, Riot Data Dragon) or
from unofficial community APIs (valorant-api.com, fortnite-api.com) and
cached locally._
