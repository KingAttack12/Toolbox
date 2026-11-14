# Toolbox

**Convertir, calculer et travailler sur ses fichiers depuis un seul espace privé.**

Toolbox rassemble des outils du quotidien dans une interface en français, adaptée aux ordinateurs, tablettes et smartphones. Les conversions s’exécutent sur le serveur qui héberge le site, sans transmettre les fichiers à un service de conversion tiers.

Le projet est conçu pour un petit groupe : les inscriptions sont ouvertes par le propriétaire, et chaque nouveau compte doit être approuvé.

[Les outils](#les-outils) · [Les conversions](#les-conversions) · [Installation](#installation) · [Administration](#administration) · [Tests](#tests)

## En quelques gestes

1. Connectez-vous à votre espace.
2. **Déposez un fichier** ou choisissez-le depuis votre appareil.
3. Sélectionnez l’un des formats de sortie proposés.
4. Lancez la conversion, puis téléchargez le résultat.

Vous pouvez aussi rechercher un outil précis, le placer dans vos favoris et retrouver les derniers outils utilisés. Le mode sombre et le menu compact rendent l’interface utilisable sur les petits écrans.

## Les outils

| Famille | Fonctionnalités |
| --- | --- |
| **Documents** | Word ↔ PDF, fusion de PDF, extraction et rotation de pages, PDF ↔ images, compression, lecture et nettoyage des métadonnées |
| **Images** | Conversion de format, redimensionnement, rotation, miroir, noir et blanc, suppression des métadonnées |
| **Audio et vidéo** | Conversion audio, conversion vidéo, extraction de la piste audio |
| **Texte et code** | Compteur de mots, nettoyage, casse, Base64, SHA-256/512, UUID, mots de passe, JSON, XML, différences de texte, aperçu CSV |
| **Calculatrices** | Calcul scientifique, pourcentages, TVA, unités, températures, écarts de dates, moyenne pondérée |
| **Bioinformatique** | Taux de GC, transcription ADN → ARN, traduction en protéines, motifs, statistiques FASTA |
| **QR codes** | Génération d’un QR code téléchargeable en PNG |
| **Manga et animé** | Recherche, tendances, fiches et liens vers les plateformes légales via AniList |

Le bandeau **À la une** affiche jusqu’à huit titres récents du Monde et de France 24, avec un lien vers chaque article. Les flux sont mis en cache côté serveur et actualisés environ toutes les quinze minutes lorsqu’ils sont consultés. Le bandeau peut être mis en pause, masqué ou réaffiché ; ce choix est mémorisé dans le navigateur.

Une **bêta YouTube → MP3** reste disponible séparément : elle demande un lien direct et la confirmation que le téléchargement est explicitement autorisé. Elle est limitée à vingt minutes et dépend du fonctionnement de YouTube et de yt-dlp.

## Les conversions

La zone de dépôt reconnaît les signatures des fichiers, puis propose les sorties compatibles. Le serveur vérifie à nouveau le contenu lors du traitement.

| Fichier déposé | Sorties proposées |
| --- | --- |
| **Image** — JPG, PNG, WebP, BMP, TIFF, GIF, ICO | JPG, PNG, WebP, BMP, TIFF, GIF fixe, ICO, PDF ou texte OCR |
| **PDF** | Word DOCX, images PNG/JPG regroupées en ZIP, texte intégré ou texte OCR |
| **Word DOCX** | PDF ou texte brut |
| **Audio** — MP3, WAV, FLAC, OGG, M4A, AAC | MP3, WAV, FLAC, OGG ou M4A |
| **Vidéo** — MP4, MOV, M4V, AVI, MKV, WebM | MP4, WebM ou extraction audio dans les cinq formats ci-dessus |

**Plusieurs fichiers ?** Déposez plusieurs images pour créer un PDF, ou plusieurs PDF pour les fusionner. L’ordre des noms affichés correspond à l’ordre utilisé.

### Limites à connaître

| Opération | Limite actuelle |
| --- | --- |
| Dépôt de fichiers | 20 fichiers et 50 Mo au total ; 20 Mo par image |
| PDF → Word ou extraction directe de texte | 100 pages |
| PDF → images | 50 pages |
| OCR d’un PDF | 20 pages, en français et/ou anglais |
| OCR d’une image | Français et anglais ; réduction des grandes images avant reconnaissance |
| Nouveau convertisseur audio/vidéo | Source de 10 minutes maximum, sortie de 50 Mo maximum |
| Sortie vidéo | Jusqu’à 1280 × 720 pixels et 30 images/s, sans agrandissement |

Les images animées deviennent des images fixes. Les icônes ICO sont placées dans un carré transparent de 256 pixels. Le passage d’un PDF à Word peut demander des retouches ; un scan nécessite l’OCR pour en extraire le texte. Convertir un son dans un format sans perte ne restaure pas la qualité déjà perdue.

Les WAV et FLAC peuvent devenir volumineux : si la sortie dépasse la limite, la conversion est refusée. Le nouveau convertisseur multimédia dispose d’un délai maximal de cinq minutes ; ses sources vidéo sont limitées à la 4K. Les anciens outils dédiés et la bêta YouTube conservent leurs propres limites.

## Installation

### Prérequis

- **Python 3.12+** et Git pour lancer l’application.
- **LibreOffice Writer** pour Word → PDF.
- **Tesseract**, avec les langues française et anglaise, pour l’OCR.
- **FFmpeg et ffprobe** pour les conversions audio et vidéo.
- **Deno** pour la bêta YouTube.

Les outils qui nécessitent un logiciel système ne fonctionneront qu’une fois ce logiciel installé et accessible dans le `PATH`. Les dépendances Python sont listées dans [requirements.txt](requirements.txt).

### Sur Windows — PowerShell

```powershell
git clone https://github.com/KingAttack12/Toolbox.git toolbox
cd toolbox
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe generate_password.py
```

Copiez la ligne `TOOLBOX_PASSWORD_HASH=...` produite par le script dans `.env`, puis démarrez l’application :

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Ouvrez [localhost:8000](http://127.0.0.1:8000). Connectez-vous avec l’identifiant défini par `TOOLBOX_USERNAME` — `admin` par défaut — et le mot de passe choisi.

### Sur Linux

```bash
git clone https://github.com/KingAttack12/Toolbox.git toolbox
cd toolbox
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python generate_password.py
# Reporter la ligne TOOLBOX_PASSWORD_HASH produite dans .env.
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Sur Ubuntu, les composants système des conversions peuvent être installés ainsi :

```bash
sudo apt-get update
sudo apt-get install -y python3-venv ffmpeg libreoffice-writer \
  tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng
```

Ces commandes supposent une nouvelle installation. Lors d’une mise à jour, conservez le `.env` existant et la base des comptes.

### Sur Oracle Cloud

Le [guide Oracle](GUIDE_VM_ORACLE.md) décrit la création de la VM et les premières étapes réseau. Le dossier [deploy/](deploy/) contient les modèles Nginx, le service systemd et les scripts d’installation et de sauvegarde.

Pour une instance accessible sur Internet, terminez la configuration avec **HTTPS**, adaptez les chemins et le domaine à votre serveur, puis vérifiez la présence de FFmpeg et ffprobe. Le script d’installation Oracle ne remplace pas ces vérifications.

Le service fourni utilise **un seul processus Uvicorn**, avec une limite de **1 500 Mo de mémoire** et **150 % de CPU**. La file d’attente étant en mémoire, le fonctionnement avec plusieurs processus n’est pas pris en charge.

## Administration

### Comptes et connexion

Le propriétaire se connecte avec son identifiant et son mot de passe serveur, **sans adresse e-mail obligatoire**. Les autres utilisateurs suivent ce parcours :

**Demande par e-mail → confirmation de l’adresse → approbation du propriétaire → connexion.**

Les mots de passe utilisateurs doivent contenir entre 15 et 128 caractères. Un compte approuvé est durable ; une demande non traitée expire après sept jours. La capacité actuelle est de vingt comptes et demandes au total.

Depuis **Administration**, le propriétaire peut rechercher et filtrer les comptes, approuver ou refuser une demande, suspendre ou réactiver un compte, révoquer ses sessions et supprimer un compte suspendu ou refusé. Les actions sensibles demandent son mot de passe actuel. Fermer les inscriptions ne suspend pas les comptes déjà actifs.

Les anciens comptes sans e-mail peuvent associer une adresse depuis **Mon compte**, avec leur mot de passe et une confirmation par e-mail.

<details>
<summary><strong>Configurer les e-mails de confirmation et de récupération</strong></summary>

L’adresse d’envoi est distincte du compte propriétaire. Utilisez une boîte dédiée et un [mot de passe d’application Google](https://support.google.com/accounts/answer/185833?hl=fr), puis renseignez ces variables dans le `.env` du serveur :

```ini
TOOLBOX_PUBLIC_URL=https://votre-domaine.example
TOOLBOX_SMTP_HOST=smtp.gmail.com
TOOLBOX_SMTP_PORT=587
TOOLBOX_SMTP_USER=votre-boite@gmail.com
TOOLBOX_SMTP_FROM=votre-boite@gmail.com
TOOLBOX_SMTP_PASSWORD=votre-mot-de-passe-application
```

Redémarrez le service après modification :

```bash
sudo systemctl restart toolbox
```

L’envoi utilise TLS. Sans configuration SMTP complète et URL publique HTTPS, les inscriptions par e-mail restent indisponibles. Un paramétrage présent ne garantit pas la réception dans la boîte principale : les échecs d’envoi apparaissent dans le journal administrateur et le renvoi est manuel.

Pour l’instance Oracle déjà configurée dans ce dépôt, [configure-mail.py](deploy/configure-mail.py) permet de saisir le secret de façon masquée et de vérifier l’authentification Gmail. Ce script utilise le domaine et le service de cette instance ; adaptez-le avant de le réutiliser ailleurs.

</details>

### Charge et quotas

Le panneau **Charge du site**, réservé au propriétaire, affiche le CPU, la mémoire, le disque disponible, les conversions en cours et la file d’attente. Les mesures sont actualisées toutes les cinq secondes ; les compteurs d’activité repartent à zéro au redémarrage.

Les conversions lourdes partagent une file commune :

- **Un traitement actif** et **trois places d’attente**.
- **Une seule conversion en cours ou en attente par personne**.
- **Trente secondes d’attente maximum** avant un refus temporaire.
- **Dix tentatives démarrées par utilisateur et par heure**, ou trente pour le propriétaire.

Les quotas sont conservés dans SQLite. Une tentative admise compte même si le fichier est ensuite refusé ou si le traitement échoue. Les outils texte et calcul ne passent pas par cette file. Ces limites organisent l’accès ; elles ne constituent pas une garantie de capacité ni de consommation mémoire pour chaque fichier.

## Données et sécurité

### Essai IA locale — propriétaire uniquement

Une expérimentation facultative utilise **Qwen3 1.7B Q4** avec Ollama sur la VM pour résumer, reformuler et corriger des textes courts. Le bouton **IA · essai** est réservé au propriétaire ; les autres comptes ne peuvent pas appeler ses routes. Aucune clé d’API externe n’est nécessaire.

L’essai accepte de 20 à 2 000 caractères, limite la réponse à 192 tokens et désactive le raisonnement prolongé. Le modèle dispose d’un contexte de 2 048 tokens et de deux threads. L’IA partage la file et les quotas des conversions ; elle ne démarre pas pendant une autre opération lourde. Les textes et réponses ne sont pas enregistrés dans un historique.

Le service séparé `toolbox-ai` est plafonné à **150 % de CPU** (1,5 cœur) et **4 Gio de RAM**, sans swap. Son API écoute uniquement sur `127.0.0.1:11435` et le mode cloud est désactivé. Le modèle est déchargé après deux minutes d’inactivité. L’interface affiche le temps de réponse, le débit de génération et les mesures CPU/RAM du service. La qualité des réponses doit être vérifiée par l’utilisateur.

Mesures initiales du 14 novembre 2026 sur Oracle ARM, pour deux textes synthétiques courts : correction en **8,7 s**, résumé en **16,7 s**, génération à **8,7–9,5 tokens/s**, RAM du service jusqu’à **2,89 Gio**. Les requêtes de santé du site ont toutes répondu pendant l’essai (maximum local observé : 56 ms). Ce petit échantillon ne garantit pas les performances avec d’autres textes ; une faute a été laissée dans la correction. Le benchmark reproductible se trouve dans `deploy/benchmark-local-ai.py`.

L’installation ARM64 est fournie dans `deploy/install-local-ai.sh`, avec l’unité `deploy/toolbox-ai.service`. L’interface reste désactivée par défaut (`TOOLBOX_LOCAL_AI=0`). Sur l’instance Oracle de ce dépôt, après installation et mesure des performances :

```bash
# Depuis la racine du projet ; chaque commande redémarre Toolbox.
.venv/bin/python deploy/local-ai-control.py enable
.venv/bin/python deploy/local-ai-control.py disable
```

Pour retirer entièrement le moteur et le modèle de cet essai :

```bash
sudo bash deploy/uninstall-local-ai.sh
```

Ce script désactive l’interface, supprime le service dédié, son stockage de modèle et `/opt/toolbox-ai` uniquement si le marqueur de cette installation est présent. Il conserve les comptes, les fichiers de conversion et le code facultatif de l’intégration. Ces scripts ciblent l’instance Oracle et le service `toolbox` ; adaptez-les avant utilisation ailleurs.

### Conservation des données

Les fichiers sont traités sur le serveur, en mémoire ou dans des dossiers temporaires. Certaines conversions nettoient leurs fichiers dès la fin du traitement ; les autres passent par un nettoyage automatique, avec une durée cible de **deux heures** par défaut. Il n’existe pas encore d’historique durable permettant de retélécharger ses résultats.

Les comptes, mots de passe hachés, états, dates de connexion et quotas sont enregistrés dans `data/accounts.sqlite3`. Le journal des décisions administratives est conservé trente jours. Le navigateur mémorise les favoris, les outils récents, le thème et le choix d’affichage des actualités.

Les fichiers de conversion ne sont pas transmis aux sources d’actualités, à AniList ou à Gmail. Ces services sont utilisés respectivement pour les titres RSS, les recherches de mangas/animés et les e-mails de compte. La bêta YouTube contacte YouTube. Les liens vers les articles et les plateformes ouvrent leurs sites externes.

<details>
<summary><strong>Protections et points à surveiller</strong></summary>

- Mots de passe hachés avec **PBKDF2-SHA256**, 600 000 itérations pour les nouveaux hachages.
- Sessions en mémoire : douze heures maximum, cinq sessions par compte, invalidées au redémarrage.
- Cookies `HttpOnly`, `SameSite=Strict` et `Secure` sous HTTPS.
- Liens à usage unique : vingt-quatre heures pour confirmer l’adresse, trente minutes pour récupérer un mot de passe ; seule leur empreinte est stockée.
- Limitation des tentatives de connexion et des demandes sensibles ; plafond de trois demandes d’e-mail par adresse et par heure, et soixante au total.
- Validation des fichiers, formats de sortie autorisés, délais de traitement et protection des actions administratives.
- Nouveau convertisseur multimédia : playlists refusées, formats d’entrée imposés et protocoles réseau FFmpeg désactivés.

La récupération du compte propriétaire passe par la configuration du serveur. La double authentification et les passkeys ne sont pas encore implémentées.

Gardez `.env`, clés privées et sauvegardes hors de Git et hors du répertoire web. Les sauvegardes de configuration peuvent contenir des secrets et des données de compte. Les fichiers déjà présents dans une sauvegarde suivent sa propre politique de conservation.

</details>

### Sauvegarder avant une mise à jour

Depuis la racine du projet sur le serveur :

```bash
.venv/bin/python deploy/backup-accounts.py
```

Ce script crée une copie cohérente de SQLite dans `data/backups/`, avec des permissions restrictives. Sauvegardez aussi le `.env` séparément dans un emplacement protégé. [backup-toolbox.sh](deploy/backup-toolbox.sh) fournit une archive de configuration et de données, à adapter à vos chemins et à votre politique de conservation.

## Tests

Installez les dépendances de développement, puis lancez la suite depuis la racine du dépôt :

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Utilisez le Python de votre environnement virtuel. Les tests des comptes emploient une base temporaire, des identifiants factices et un envoi SMTP simulé : aucun e-mail réel n’est envoyé.

Les tests couvrent les comptes et leurs permissions, les liens de confirmation/récupération, les quotas, la file d’attente, le cache d’actualités et les conversions réelles. Les tests de conversion nécessitent les composants système correspondants ; ceux des nouveaux médias demandent FFmpeg et ffprobe, et l’OCR demande Tesseract et ses langues.

Pour vérifier uniquement les nouveaux formats :

```bash
python -m unittest discover -s tests -p test_more_conversions.py -v
```

## Structure du projet

```text
app/
  main.py                 Application et routes
  routers/tools_*.py      Outils et convertisseurs
  auth.py                 Sessions et hachage des mots de passe
  accounts.py             Comptes, approbations et SQLite
  email_accounts.py       Confirmation et récupération par e-mail
  workload.py             File d’attente et quotas
  monitoring.py           Mesures de charge
  news.py                 Cache des flux d’actualités
frontend/
  index.html              Interface principale
  app.js                  Catalogue des outils et navigation
  convert.js              Dépôt et choix de conversion
  news.js                 Bandeau d’actualités
  style.css               Styles et adaptation aux écrans
deploy/                   Configuration et scripts serveur
tests/                    Tests automatisés
```

Le serveur utilise **FastAPI** ; l’interface est en **HTML, CSS et JavaScript**, sans framework frontend. SQLite conserve les comptes. Pillow, LibreOffice, PyMuPDF, pdf2docx, Tesseract et FFmpeg assurent les conversions selon leur famille.

## Évolutions envisagées

- Double authentification ou passkeys pour le propriétaire.
- File de tâches durable et meilleure isolation des conversions.
- Historique de téléchargements avec conservation choisie par l’utilisateur.
- Davantage d’outils exécutés entièrement dans le navigateur.

Ces pistes ne sont pas encore implémentées.

## Utilisation et contributions

Projet personnel destiné à un **usage personnel non commercial**. Les dépendances conservent leurs licences respectives.

Pour proposer une amélioration ou signaler un problème, utilisez les [issues GitHub](https://github.com/KingAttack12/Toolbox/issues). Décrivez le comportement attendu et les étapes de reproduction, sans joindre de mot de passe, de clé privée ni de fichier confidentiel.
