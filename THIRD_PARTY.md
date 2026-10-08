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
