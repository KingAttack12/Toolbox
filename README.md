# 🛠 Toolbox privée — Phase 1+2

Base FastAPI + frontend vanilla + auth + outils simples **100 % locaux** (aucune API externe, IA désactivée).

## Contenu

- `app/` : FastAPI modulaire (`routers/tools_*.py` = 1 fichier par catégorie, facile à étendre)
- `frontend/` : HTML/CSS/JS responsive, recherche, favoris, mode sombre, login
- `deploy/` : scripts Oracle Cloud (Nginx + systemd, sans Docker pour rester léger)
- `generate_password.py` : hash PBKDF2 du mot de passe admin
- `GUIDE_VM_ORACLE.md` : création de la VM Always Free + déploiement pas à pas

## ⚠️ Avant d'installer (autorisation demandée)

Sur **ton PC** (test local), je vais devoir lancer :

```powershell
pip install -r requirements.txt
```

Dépendances (toutes gratuites/open source) :
| Paquet | Licence | Pourquoi |
|---|---|---|
| fastapi | MIT | Backend API |
| uvicorn[standard] | BSD | Serveur ASGI |
| python-multipart | Apache-2.0 | Formulaires/fichiers (phases suivantes) |
| qrcode[pil] | BSD | QR codes locaux |
| Pillow | HPND (open source) | Images PNG du QR (+ Phase 4) |

Rien d'autre : pas de Docker sur ton PC (absent de toute façon), pas de service payant, pas d'API externe.

## Lancer en local (après `pip install`)

```powershell
cd "C:\Users\lyesa\Desktop\Site web utile\toolbox"
Copy-Item .env.example .env
python generate_password.py
# → colle la ligne TOOLBOX_PASSWORD_HASH=... dans .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# → ouvre http://127.0.0.1:8000 (login admin + mot de passe choisi)
```

## Outils inclus (Phase 2)

Texte/dev : compteur, nettoyeur, casse, base64, SHA-256/512, UUID, mots de passe (`secrets`), JSON format/validate, XML format, diff, CSV preview.
Calculatrices : scientifique (AST sûr), %, TVA, unités (longueur/masse/volume/vitesse/stockage), température, dates, moyenne pondérée + mention.
Bioinfo : GC%, transcription, traduction, motifs, FASTA stats.
QR : générateur PNG local.
Stubs grisés : PDF (Ph.3), Images (Ph.4), Média/yt-dlp (Ph.5), IA (Ph.6, `AI_API_KEY` vide = désactivée).

## Sécurité (conforme cahier des charges §5/§15)

- Login obligatoire (cookie HttpOnly, sessions 12h, PBKDF2 200k itérations).
- Secrets uniquement en `.env` (jamais dans le code/frontend) ; `.env` à ne jamais commiter.
- Limites : textes ≤ 500k caractères, QR ≤ 2000 caractères, uploads ≤ 50 Mo (Nginx 55m).
- Pas de `shell=True` / pas de commande construite depuis l'utilisateur (aucun subprocess en Phase 2).
- Évaluateur calculatrice via AST (pas d'`eval` libre) ; séquences bio validées par regex.
- Fichiers temporaires : `data/tmp/<job_id>/` + thread de nettoyage TTL 2h (`app/jobs.py`).
- Logs sans secrets.

## Déploiement Oracle (résumé)

1. Crée la VM (voir `GUIDE_VM_ORACLE.md`).
2. Dépose le code (`scp` ou `git`), puis en SSH : `sudo bash deploy/oracle-setup.sh`.
3. Sur la VM : `cp .env.example .env && python3 generate_password.py` → renseigne le hash.
4. Ouvre `http://<IP_PUBLIQUE>/`.

## Étapes suivantes

- Phase 3 : PDF (pypdf/PyMuPDF + LibreOffice/Ghostscript/Tesseract — à valider un par un).
- Phase 4 : Pillow (déjà installé) → conversions, resize, EXIF.
- Phase 5 : FFmpeg + yt-dlp (binaires système, commandes `subprocess` en liste d'args).
- Phase 6 : IA uniquement si tu fournis une clé à quota gratuit vérifié.
