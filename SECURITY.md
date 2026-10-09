# Sécurité

## Signaler une vulnérabilité

Merci de **ne pas** ouvrir d'issue publique pour une faille de sécurité.
Utilise le signalement privé de GitHub :
[Security → Report a vulnerability](https://github.com/realycracked/game_boost/security/advisories/new).

Décris le problème, la version concernée (Réglages → Mise à jour) et, si possible,
les étapes pour le reproduire. Tu recevras une réponse dès que possible.
Si le formulaire n'est pas disponible, ouvre une issue **sans détail technique**
en demandant un moyen de contact privé.

## Ce qu'Overdrive protège

- Le serveur local n'écoute que sur `127.0.0.1` par défaut et refuse les requêtes
  dont l'en-tête `Host` n'est pas local (protection contre le DNS rebinding).
- L'exposition au réseau (`--host`) exige un jeton d'accès aléatoire.
- Les clés API sont chiffrées (Fernet, clé dérivée par PBKDF2) dans un fichier
  lisible par le seul utilisateur, et ne quittent la machine que vers le
  fournisseur IA choisi.
- Aucune URL fournie par l'utilisateur n'est téléchargée par le serveur.

## Versions maintenues

Seule la dernière [Release](https://github.com/realycracked/game_boost/releases/latest) reçoit des correctifs.
