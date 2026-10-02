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
métadonnées (lecture + nettoyage), compression.

**Média** — conversion MP4→MP3.

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
