# FileDrop

Transfert de fichiers entre appareils Android sur le réseau local — sans cloud,
sans compte, sans code PIN.

Ce projet est conçu pour être développé **entièrement depuis un téléphone** :
tout le code est modifiable depuis GitHub, la compilation se fait sur GitHub
Actions, et l'APK se récupère dans les artifacts du workflow. Aucun PC, aucun
Android Studio, aucun émulateur ne sont nécessaires.

---

## Sommaire

1. [Compiler avec GitHub Actions](#1-compiler-avec-github-actions)
2. [Récupérer l'APK](#2-récupérer-lapk)
3. [Installer l'APK sur le téléphone](#3-installer-lapk-sur-le-téléphone)
4. [Lancer un build](#4-lancer-un-build)
5. [Modifier les paramètres principaux](#5-modifier-les-paramètres-principaux)
6. [Utiliser FileDrop](#6-utiliser-filedrop)
7. [Diagnostiquer un problème sans PC](#7-diagnostiquer-un-problème-sans-pc)
8. [Architecture](#8-architecture)
9. [Ce qui est fait, ce qui ne l'est pas](#9-ce-qui-est-fait-ce-qui-ne-lest-pas)
10. [Limites réelles d'Android, assumées](#10-limites-réelles-dandroid-assumées)
11. [APK release signé](#11-apk-release-signé)

---

## 1. Compiler avec GitHub Actions

Le workflow est dans `.github/workflows/build.yml`. Il fait exactement ceci :

| Étape | Ce qu'elle fait |
| --- | --- |
| `actions/checkout@v4` | récupère le dépôt |
| `actions/setup-java@v4` | installe le JDK **17** (Temurin) |
| `android-actions/setup-android@v3` | installe les composants Android SDK (`platforms;android-35`, `build-tools;35.0.0`) et accepte les licences |
| `gradle/actions/setup-gradle@v4` | configure Gradle et son cache |
| `chmod +x ./gradlew` | rend le wrapper Gradle exécutable |
| `./gradlew testDebugUnitTest` | lance les tests unitaires |
| `./gradlew assembleDebug` | compile l'APK debug |
| `actions/upload-artifact@v4` | publie l'APK dans les artifacts |

Versions figées, pour que deux builds successifs produisent la même chose :

- JDK 17
- Gradle 8.14.3 (via le wrapper commité dans le dépôt)
- Android Gradle Plugin 8.7.3
- Kotlin 2.0.21
- `compileSdk` / `targetSdk` 35, `minSdk` 26 (Android 8.0)

## 2. Récupérer l'APK

1. ouvrir le dépôt sur GitHub (navigateur ou application GitHub) ;
2. onglet **Actions** ;
3. ouvrir le dernier run **Build APK** avec une coche verte ;
4. descendre jusqu'à la section **Artifacts** ;
5. télécharger **`filedrop-apk-debug`**.

GitHub fournit toujours les artifacts sous forme de **fichier `.zip`** — c'est
une contrainte de la plateforme, pas un choix du projet. Il faut donc
décompresser le `.zip` sur le téléphone (l'application Fichiers d'Android sait
le faire, sinon n'importe quel gestionnaire d'archives) pour obtenir
`FileDrop-debug-<commit>.apk`.

## 3. Installer l'APK sur le téléphone

1. décompresser le `.zip` téléchargé ;
2. appuyer sur le fichier `.apk` ;
3. Android demande d'autoriser l'installation depuis cette source (navigateur ou
   gestionnaire de fichiers) : accepter, puis revenir en arrière ;
4. installer.

L'APK debug a l'identifiant `com.filedrop.app.debug` : il **cohabite** avec une
éventuelle version release, il ne l'écrase pas.

Pour tester un transfert, l'APK doit être installé sur **les deux** appareils.

## 4. Lancer un build

Trois moyens, tous utilisables depuis un téléphone :

- **automatiquement** : à chaque `push` sur n'importe quelle branche (les
  modifications faites directement dans l'éditeur web de GitHub déclenchent donc
  un build) ;
- **automatiquement** : à l'ouverture ou à la mise à jour d'une pull request ;
- **manuellement** : onglet **Actions** → **Build APK** → bouton
  **Run workflow** → choisir la branche → **Run workflow**.

Les modifications de fichiers `.md` seuls ne déclenchent pas de build (inutile).

## 5. Modifier les paramètres principaux

| Ce que vous voulez changer | Fichier | Ligne |
| --- | --- | --- |
| Version d'Android minimale | `app/build.gradle.kts` | `minSdk = 26` |
| Version d'Android ciblée | `app/build.gradle.kts` | `targetSdk = 35` |
| Numéro de version affiché | `app/build.gradle.kts` | `versionName = "0.1.0"` |
| Version des outils (AGP, Kotlin, Compose…) | `gradle/libs.versions.toml` | section `[versions]` |
| Version du JDK / du SDK utilisés par le build | `.github/workflows/build.yml` | bloc `env:` |
| Nom du service réseau annoncé | `discovery/NsdDiscovery.kt` | `SERVICE_TYPE` |
| Taille des blocs envoyés | `security/SecureChannel.kt` | `CHUNK_SIZE` (64 Kio) |
| Délai avant refus automatique d'une demande | `transfer/TransferEngine.kt` | `DECISION_TIMEOUT_MS` |
| Dossier de réception par défaut | `storage/ReceivedFileWriter.kt` | `ROOT_FOLDER` |

Les réglages destinés à l'utilisateur (nom de l'appareil, dossier de réception,
acceptation automatique) se changent directement dans l'écran **Paramètres** de
l'application, sans recompiler.

## 6. Utiliser FileDrop

**Sur l'appareil qui reçoit :** ouvrir FileDrop → **Recevoir**. L'appareil
devient visible sur le réseau et une notification discrète indique qu'il est
prêt.

**Sur l'appareil qui envoie :** deux chemins.

- depuis FileDrop : **Envoyer un fichier** → choisir les fichiers → choisir
  l'appareil → **Envoyer** ;
- depuis n'importe quelle application : **Partager → FileDrop** → choisir
  l'appareil → **Envoyer**.

**Sur l'appareil qui reçoit :** une notification apparaît avec le nom de
l'expéditeur, le nombre de fichiers et la taille totale, et deux boutons :
**Refuser** / **Accepter**. Aucun code, aucun compte, aucun formulaire.

Les fichiers arrivent dans `Téléchargements/FileDrop` (visible dans
l'application Fichiers, et dans la galerie pour les photos et vidéos), ou dans
le dossier choisi dans les paramètres.

## 7. Diagnostiquer un problème sans PC

`adb logcat` n'est pas disponible quand on développe depuis un téléphone. Pour
cette raison, FileDrop journalise tout **dans l'application** :

**Accueil → Journal.**

Chaque étape y laisse une trace horodatée : recherche mDNS, appareil trouvé et
résolu, transport retenu et transports écartés (avec la raison), poignée de main
et empreinte du pair, offre envoyée, décision, début et fin de chaque fichier,
erreurs complètes. Les mêmes lignes partent dans logcat sous l'étiquette `FD/*`
si un PC est disponible un jour.

Les cas les plus fréquents :

| Symptôme | Cause la plus probable |
| --- | --- |
| Aucun appareil détecté | les deux appareils ne sont pas sur le même Wi-Fi, ou le point d'accès isole ses clients (Wi-Fi public, mode « isolation des clients » d'une box) |
| « Connexion en données mobiles » dans les paramètres | le Wi-Fi est coupé ; le réseau local est alors inaccessible |
| L'appareil apparaît puis disparaît | la découverte s'arrête quand l'application passe en arrière-plan (choix délibéré : mDNS en continu vide la batterie). Activez **Recevoir** pour rester visible |
| Aucune notification à la réception | permission de notification refusée (Android 13+). La demande reste visible dans l'application |

## 8. Architecture

```
app/src/main/java/com/filedrop/app/
├── core/           journalisation (FdLog) et formatage
├── discovery/      découverte mDNS (NsdManager) + modèle PeerDevice
├── transport/      TransferTransport et ses implémentations
│                   ├── LanTcpTransport      (Wi-Fi local, actif)
│                   ├── WifiDirectTransport  (déclaré indisponible, V3)
│                   └── BluetoothTransport   (déclaré indisponible, V3)
├── security/       identité EC P-256, poignée de main, canal AES-GCM
├── transfer/       protocole, moteur de transfert, service de premier plan
├── sharing/        lecture des intents ACTION_SEND / ACTION_SEND_MULTIPLE
├── storage/        résolution des URI, écriture des fichiers reçus, réglages
├── notifications/  canaux, notification Accepter/Refuser
├── history/        historique et appareils connus
└── ui/             interface Compose
```

**Choix du transport.** `TransportManager` interroge chaque transport, garde
ceux qui sont réellement disponibles, et retient celui dont le débit estimé est
le plus élevé. C'est ce qui garantit qu'un envoi de plusieurs Go ne partira
jamais par Bluetooth si le Wi-Fi répond. Chaque décision — y compris chaque
rejet, avec sa raison — est écrite dans le journal.

**Sécurité.** Chaque appareil possède une paire de clés EC P-256 durable.
À chaque session : échange de clés éphémères, signature des deux clés éphémères
par les identités durables, dérivation HKDF-SHA256, puis chiffrement de tout le
reste en AES-256-GCM (une clé par sens, nonce à compteur). Le contenu des
fichiers passe dans le même canal chiffré. L'empreinte du pair est affichée dans
la demande de transfert et mémorisée après un transfert réussi.

Le modèle est celui de la **confiance à la première utilisation** : au tout
premier contact, rien ne prouve que l'empreinte est la bonne. Le seul moyen d'y
remédier serait un code à comparer entre les deux appareils, ce que le cahier
des charges exclut. L'empreinte est donc affichée pour permettre une
vérification manuelle si nécessaire.

**Mémoire.** Rien n'est jamais chargé en entier : lecture et écriture par blocs
de 64 Kio, du disque au socket. Un envoi de 18 Go consomme la même mémoire qu'un
envoi de 1 Mo.

## 9. Ce qui est fait, ce qui ne l'est pas

**V1 — dans cet APK**

- découverte Android ↔ Android par mDNS, sans aucune permission d'exécution
- transport Wi-Fi local (TCP), session chiffrée et authentifiée
- envoi d'un ou plusieurs fichiers, arborescence conservée
- menu Partager Android (`ACTION_SEND` et `ACTION_SEND_MULTIPLE`, tous types MIME)
- notification **Accepter / Refuser**, sans code PIN
- progression globale et par fichier, débit, temps restant, annulation
- transfert en arrière-plan (service de premier plan `dataSync`)
- historique, appareils connus, journal intégré
- écriture via `MediaStore` ou dossier choisi par l'utilisateur

**V2 — prévu**

- sélection de dossiers entiers via le sélecteur d'arborescence
- reprise après interruption (le protocole prévoit déjà `FileStart` / `FileEnd`
  par fichier, ce qui rend la reprise par fichier réalisable sans casser le format)
- pause et reprise d'un transfert en cours

**V3 — prévu**

- Wi-Fi Direct et Wi-Fi Aware selon la compatibilité de l'appareil
- Bluetooth pour la découverte et le secours
- confiance explicite accordée aux appareils connus

Les transports non implémentés existent déjà dans le code sous forme de classes
qui **déclarent honnêtement leur indisponibilité**. Ils ne simulent rien : un
transport qui ne marche pas ne doit jamais être annoncé comme disponible.

## 10. Limites réelles d'Android, assumées

Ces points ne sont pas contournés artificiellement ; ils sont documentés et
traités par la solution officielle la plus adaptée.

- **mDNS ne traverse pas les réseaux.** `NsdManager` ne voit que le réseau local
  et échoue si le point d'accès isole ses clients. Aucune solution côté
  application ; le cas est détecté et expliqué.
- **`NsdManager.resolveService` ne supporte qu'une résolution à la fois.** Les
  résolutions sont mises en file d'attente et relancées en cas de
  `FAILURE_ALREADY_ACTIVE`.
- **Une URI reçue par le menu Partager n'est lisible que temporairement.**
  L'autorisation est propagée au service de transfert via `ClipData` et
  `FLAG_GRANT_READ_URI_PERMISSION`, mécanisme officiel. Copier les fichiers dans
  le cache aurait doublé l'espace disque et le temps d'écriture sur un envoi de
  plusieurs Go.
- **Le stockage est cloisonné depuis Android 10.** Les fichiers reçus passent par
  `MediaStore` (aucune permission) ou par le dossier choisi via le sélecteur
  système. Aucune permission de stockage large n'est demandée.
- **L'accord de clés EC matériel n'existe qu'à partir d'Android 12.** La clé
  d'identité est donc stockée dans les préférences privées de l'application,
  protégées par le bac à sable Android. Le passage à `AndroidKeyStore` là où il
  est disponible est identifié comme travail futur.
- **Un service de premier plan est obligatoire** pour qu'un transfert survive au
  passage en arrière-plan, et son type `dataSync` doit être déclaré depuis
  Android 14. C'est fait.
- **GitHub Actions ne peut pas tester deux téléphones qui se parlent.** Les tests
  automatisés couvrent donc ce qui est testable sans appareil : protocole,
  cryptographie de session (poignée de main complète et flux de 8 Mio),
  assainissement des chemins, historique, calcul de débit. Le reste se teste avec
  deux téléphones et l'écran Journal.

## 11. APK release signé

La V1 se construit en **debug** et n'a besoin d'aucun secret. La configuration
release existe déjà mais reste hors du chemin critique.

Pour compiler la variante release sans la signer (vérification de compilation
uniquement) : **Actions → Build APK → Run workflow**, en cochant
`build_release`. L'APK produit est alors **non signé** et non installable.

Pour produire un APK release **signé**, ajouter quatre secrets au dépôt
(Settings → Secrets and variables → Actions) :

| Secret | Contenu |
| --- | --- |
| `FILEDROP_KEYSTORE_BASE64` | le keystore `.jks` encodé en base64 |
| `FILEDROP_KEYSTORE_PASSWORD` | mot de passe du keystore |
| `FILEDROP_KEY_ALIAS` | alias de la clé |
| `FILEDROP_KEY_PASSWORD` | mot de passe de la clé |

Le workflow les utilise automatiquement s'ils existent. Sans eux, rien ne casse :
l'APK release est simplement produit non signé.

Le fichier `keystore.properties` et les fichiers `.jks` / `.keystore` sont dans
`.gitignore` : un secret de signature ne doit jamais être commité.
