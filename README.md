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
  rien n'est conservé, rien n'est envoyé ailleurs.
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


### Comptes sur demande — test limité

Le propriétaire reste l’utilisateur défini par `TOOLBOX_USERNAME` et son mot de passe dans la configuration serveur. Aucun compte créé via l’interface ne devient administrateur.

1. Se connecter avec le compte propriétaire, puis ouvrir **Comptes · test**.
2. Cliquer sur **Ouvrir les demandes de test** pour afficher le formulaire sur la page de connexion. Les demandes sont fermées par défaut.
3. Les visiteurs choisissent uniquement un identifiant et un mot de passe (15 à 128 caractères). Les identifiants sont insensibles à la casse ; celui du propriétaire est réservé.
4. Approuver ou refuser chaque demande. Une approbation donne accès aux outils pendant 7 jours. Une demande non traitée expire après 7 jours. La suspension coupe l’accès dès la prochaine requête authentifiée.
5. Fermer les demandes termine la collecte ; suspendre individuellement les comptes actifs si nécessaire.

Le test accepte au maximum 20 comptes/demandes, et 5 tentatives d’inscription par minute et par IP. Les messages ne confirment pas la disponibilité d’un identifiant. Les mots de passe sont hachés par PBKDF2-SHA256 avec sel aléatoire et 600 000 itérations pour les nouveaux hashes ; le propriétaire conserve son hash compatible. Les décisions exigent une session propriétaire et un en-tête de requête même origine, sans CORS. Les cookies sont HttpOnly, SameSite=Strict et Secure sous HTTPS. La déconnexion invalide le jeton côté serveur.

La base `data/accounts.sqlite3` doit être sauvegardée et rester hors de tout répertoire web. Elle est indépendante du nettoyage des fichiers temporaires. Les demandes et comptes expirés sont supprimés lors du prochain accès à la base ; les mots de passe hachés des comptes refusés/suspendus sont effacés. Le journal des décisions est conservé 30 jours, avec les 30 dernières entrées visibles. Les sessions restent en mémoire : un redémarrage déconnecte tous les utilisateurs (un seul processus serveur).

Limites du test : aucun e-mail, vérification d’identité, récupération automatique, MFA ou quota de calcul par utilisateur. Vérifier l’identité des personnes par un autre moyen avant de valider ; choisir des mots de passe uniques. Les comptes approuvés utilisent les mêmes outils que le propriétaire et partagent les ressources de la VM. Avant une ouverture plus large : MFA pour le propriétaire, quotas de calcul, limites globales de requêtes et procédure de récupération.

Tests isolés : `pip install -r requirements-dev.txt`, puis `python -m unittest discover -s tests -v`. Ils utilisent une base temporaire et des identifiants factices, sans accéder aux comptes réels.


### Gestion de charge — test

Toutes les conversions PDF, images, Word/OCR et audio utilisent une file FIFO commune : un traitement actif et trois places d’attente, une seule demande par personne (identifiants insensibles à la casse), attente maximale de 30 s avant HTTP 429. Les traitements sont exécutés dans les threads de FastAPI pour laisser l’API et l’administration répondre. Ce mécanisme nécessite **un seul processus Uvicorn** comme dans le service fourni. Il ne constitue pas un système de tâches durable : les requêtes dépendent de leur connexion HTTP ; un redémarrage supprime la file.

Quotas persistants SQLite sur une heure glissante : 10 tentatives démarrées par utilisateur, 30 pour le propriétaire. Les erreurs de fichier et de validation après admission consomment un essai ; les refus de file et délais d’attente n’en consomment pas. Le quota limite les lancements, pas la durée totale de calcul. Les outils texte/calcul ne sont pas concernés. La limite d’upload MP3 est alignée à 50 Mo ; le rendu PDF en images limite également les pixels traités.

Le bouton propriétaire **Charge du site** actualise toutes les 5 s les CPU VM et site (ce dernier en proportion de son quota cgroup), mémoire VM et service, espace disque, tâches en cours/en attente et compteurs depuis le démarrage. La première mesure CPU est vide. Ces métriques nécessitent Linux et cgroup v2 pour les données du service ; une valeur absente est affichée indisponible. `/api/admin/load` exige le propriétaire et ne retourne ni jeton ni fichier. `/api/tools/workload` ne retourne à l’utilisateur que son état et sa place. La consultation ne demande aucune permission système supplémentaire.

La file sérialise les calculs lourds, sans garantir qu’un fichier individuel reste sous la limite mémoire du service ; il faut encore surveiller les cas réels et les éventuels arrêts mémoire. Une file durable, l’isolation des conversions dans des processus et des budgets de temps CPU seront les étapes suivantes si l’usage augmente.
