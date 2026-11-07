# Toolbox — tous tes outils au même endroit

Une boîte à outils web personnelle, hébergée sur un serveur Oracle Cloud gratuit,
sans pub, sans compte à créer, sans données revendues. Tu l'installes, c'est à toi.

Le projet est né d'un besoin simple : arrêter de disperser ses fichiers sur dix
sites douteux pour convertir un PDF, compresser une image ou calculer une moyenne.
Ici tout tourne **sur ton propre serveur**, en local : aucun fichier n'est envoyé
à un service tiers.

## Ce qu'il y a dedans

**Texte & code** — compteur de mots, nettoyeur, majuscules/minuscules, Base64,
SHA-256/512, UUID, générateur de mots de passe, JSON format/validate, XML, diff, CSV.

**Calculatrices** — scientifique, pourcentages, TVA, unités, température, dates,
moyenne pondérée avec mention.

**Bioinfo** — GC%, transcription ADN→ARN, traduction →protéine, motifs, stats FASTA.

**Images** — conversion JPG/PNG/WebP, redimensionnement, rotation, miroir,
noir & blanc, suppression EXIF, QR codes.

**Documents PDF** — fusion, extraction de pages, rotation, PDF↔images,
métadonnées (lecture + nettoyage), compression, Word → PDF, PDF → Word et OCR
local (français/anglais). Word → PDF utilise LibreOffice ; PDF → Word utilise
pdf2docx. L'OCR extrait le texte des PDF scannés en fichier TXT. Limites :
50 Mo par fichier, 100 pages pour PDF → Word et 20 pages pour l'OCR.

**Média** — conversion MP4→MP3 et bêta YouTube→MP3 pour une vidéo
explicitement autorisée (20 min max, une à la fois).

Interface en français, utilisable sur téléphone, recherche intégrée, favoris,
mode sombre. Les outils lourds à venir (Word, OCR) sont affichés grisés.

## Technique, en bref

- Backend **Python / FastAPI**, frontend **HTML/CSS/JS** sans framework.
- Un fichier par famille d'outils (`app/routers/tools_*.py`) : ajouter un outil
  = ajouter une fonction + une entrée dans le catalogue JS.
- Auth par login (PBKDF2 + sessions HttpOnly), rate limit anti brute-force,
  fail2ban côté serveur, HTTPS Let's Encrypt via Nginx.
- Dépendances gratuites/open source uniquement : voir `requirements.txt`.
- Pas d'IA obligatoire : le code prévoit un crochet optionnel (`AI_API_KEY`
  vide = désactivée), aucun appel externe sans ça.
- LibreOffice Writer et Tesseract sont installés par le script Oracle ; leurs
  outils restent locaux au serveur.
- La bêta YouTube utilise yt-dlp, Deno et FFmpeg ; elle est limitée aux vidéos
  pour lesquelles le téléchargement est autorisé.

## L'essayer en 5 minutes (sur ton PC)

Prérequis : Python 3.12+.

```powershell
cd toolbox
pip install -r requirements.txt
Copy-Item .env.example .env
python generate_password.py
# colle la ligne TOOLBOX_PASSWORD_HASH=... affichée dans le fichier .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# ouvre http://127.0.0.1:8000, connecte-toi avec admin + ton mot de passe
```

Ne commite jamais ton `.env` (il est déjà dans le `.gitignore`).

## L'héberger gratis (Oracle Cloud Free Tier)

Le guide pas à pas est dans [`GUIDE_VM_ORACLE.md`](GUIDE_VM_ORACLE.md) :
création de la VM gratuite, réseau, `oracle-setup.sh` (Nginx + systemd + fail2ban),
nom de domaine + HTTPS. Compter une grosse demi-heure la première fois,
dont la moitié d'attente Oracle.

Dossier [`deploy/`](deploy/) : tout ce qu'il faut
(`nginx-toolbox*.conf`, `toolbox.service`, `oracle-setup.sh`, `backup-toolbox.sh`).

## Confidentialité

- Tes fichiers sont traités **en mémoire sur ton serveur** puis oubliés :
  les fichiers temporaires sont purgés automatiquement. Les comptes et journaux ont leur propre politique de conservation.
- Les logs serveur ne contiennent que des métadonnées (IP, date, endpoint),
  jamais le contenu de tes fichiers.
- Le navigateur garde seulement tes favoris et tes derniers outils utilisés.
- Détails dans la page « Confidentialité » du site.

## Feuille de route (idées, pas des promesses)

- Word ↔ PDF, OCR français, compression PDF forte.
- Historique de conversions avec re-téléchargement.
- Petits outils 100 % navigateur (zéro transit) pour les données sensibles.

## Licence et contributation

Projet personnel ouvert : utilisation et modification libres pour un usage
personnel non commercial. Les dépendances citées dans `requirements.txt`
restent sous leurs licences respectives (MIT, BSD, Apache-2.0, HPND...).


### Comptes utilisateurs et administration

Le propriétaire conserve son identifiant `TOOLBOX_USERNAME` et son mot de passe configuré sur le serveur, **sans adresse e-mail**. Les utilisateurs s’inscrivent par e-mail et mot de passe (15 à 128 caractères). Leur adresse est confirmée par lien à usage unique, avec confirmation du mot de passe choisi, puis le propriétaire approuve la demande. Un compte actif n’expire plus automatiquement. Les demandes non traitées expirent après 7 jours.

Le panneau **Administration** propose recherche, filtres par état, compteurs, dernière connexion, validation/refus, suspension/réactivation, révocation des sessions et suppression d’un compte préalablement suspendu/refusé. Les actions exigent le mot de passe actuel du propriétaire. Le panneau **Charge du site** conserve la supervision CPU, mémoire et file de conversion.

La migration SQLite ajoute les colonnes sans recréer les comptes. Les anciens comptes actifs non expirés deviennent durables. Ils peuvent associer une adresse depuis **Mon compte** avec leur mot de passe actuel et une confirmation par e-mail. Sauvegarder `data/accounts.sqlite3` via l’API SQLite backup avant toute mise à jour. La base reste hors du répertoire web ; sauvegardes et `.env` doivent être lisibles seulement par le compte serveur.

Les liens de confirmation expirent après 24 h, ceux de récupération après 30 min. Seule l’empreinte SHA-256 du jeton est stockée. Les liens utilisent un fragment URL pour éviter d’enregistrer le jeton dans les logs HTTP. Une récupération ne change jamais le statut du compte et révoque les sessions précédentes. La suspension, la réactivation et la déconnexion forcée changent aussi la version des sessions. Les réponses de récupération ne révèlent pas l’existence d’une adresse.

Limites : 20 comptes/demandes ; 5 tentatives par minute/IP pour inscription, récupération et confirmation ; au plus 3 demandes d’e-mail par adresse/heure et 60 au total/heure. Les sessions en mémoire expirent après 12 h et au redémarrage ; au plus 5 sessions par compte. Les mots de passe utilisent PBKDF2-SHA256 (600 000 itérations pour les nouveaux). Les cookies sont HttpOnly, SameSite=Strict, Secure sous HTTPS. Les actions utilisent un en-tête réservé au même site, sans CORS. Le journal administrateur est conservé 30 jours. La connexion du propriétaire reste récupérable uniquement via la configuration serveur. MFA/passkeys ne sont pas implémentés ; c’est l’amélioration recommandée pour le propriétaire.

#### Activer l’envoi Gmail

L’adresse d’envoi Gmail n’est pas l’identité du compte administrateur. Créer une boîte dédiée, activer la validation en deux étapes et générer un mot de passe d’application si cette option est disponible pour ce compte : https://support.google.com/accounts/answer/185833 .

Renseigner **uniquement dans le `.env` du serveur**, jamais dans le chat ni dans Git :

```ini
TOOLBOX_PUBLIC_URL=https://mytoolbox.duckdns.org
TOOLBOX_SMTP_HOST=smtp.gmail.com
TOOLBOX_SMTP_PORT=587
TOOLBOX_SMTP_USER=adresse-dediee@gmail.com
TOOLBOX_SMTP_FROM=adresse-dediee@gmail.com
TOOLBOX_SMTP_PASSWORD=mot-de-passe-application
```

Redémarrer `toolbox`, puis vérifier une inscription réelle sur une adresse de test avant d’inviter les personnes. TLS est obligatoire (STARTTLS 587 ou SSL 465). Sans ces paramètres, l’interface indique que Gmail doit être configuré, et les inscriptions/récupérations restent fermées. Un paramétrage présent ne garantit pas la délivrabilité : les échecs sont consignés dans le journal administrateur sans secret ni lien. Le renvoi est manuel et limité ; il n’existe pas encore de file d’e-mails durable.

Tests : `python -m unittest discover -s tests -v` après installation de `requirements-dev.txt`. Base temporaire, identifiants factices et SMTP simulé ; aucun e-mail réel envoyé. Les tests incluent la migration, vérification, approbation, droits, récupération, réutilisation/expiration des jetons, révocation des sessions et les conversions.


### Gestion de charge — test

Toutes les conversions PDF, images, Word/OCR et audio utilisent une file FIFO commune : un traitement actif et trois places d’attente, une seule demande par personne (identifiants insensibles à la casse), attente maximale de 30 s avant HTTP 429. Les traitements sont exécutés dans les threads de FastAPI pour laisser l’API et l’administration répondre. Ce mécanisme nécessite **un seul processus Uvicorn** comme dans le service fourni. Il ne constitue pas un système de tâches durable : les requêtes dépendent de leur connexion HTTP ; un redémarrage supprime la file.

Quotas persistants SQLite sur une heure glissante : 10 tentatives démarrées par utilisateur, 30 pour le propriétaire. Les erreurs de fichier et de validation après admission consomment un essai ; les refus de file et délais d’attente n’en consomment pas. Le quota limite les lancements, pas la durée totale de calcul. Les outils texte/calcul ne sont pas concernés. La limite d’upload MP3 est alignée à 50 Mo ; le rendu PDF en images limite également les pixels traités.

Le bouton propriétaire **Charge du site** actualise toutes les 5 s les CPU VM et site (ce dernier en proportion de son quota cgroup), mémoire VM et service, espace disque, tâches en cours/en attente et compteurs depuis le démarrage. La première mesure CPU est vide. Ces métriques nécessitent Linux et cgroup v2 pour les données du service ; une valeur absente est affichée indisponible. `/api/admin/load` exige le propriétaire et ne retourne ni jeton ni fichier. `/api/tools/workload` ne retourne à l’utilisateur que son état et sa place. La consultation ne demande aucune permission système supplémentaire.

La file sérialise les calculs lourds, sans garantir qu’un fichier individuel reste sous la limite mémoire du service ; il faut encore surveiller les cas réels et les éventuels arrêts mémoire. Une file durable, l’isolation des conversions dans des processus et des budgets de temps CPU seront les étapes suivantes si l’usage augmente.
