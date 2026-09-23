# Guide VM Oracle Cloud Always Free (compte OK, pas de VM)

> Objectif : 1 VM gratuite pour la Toolbox, accès par IP publique en HTTP pour tester.
> Coût : 0 € si tu restes dans les limites Always Free. Ne crée rien d'autre (pas de DB payante, pas de LB).

## 1. Créer la VM (console Oracle Cloud)

1. Connecte-toi à https://cloud.oracle.com → **Compute > Instances > Create instance**.
2. **Name** : `toolbox` ; **Compartment** : le compartment par défaut.
3. **Image** : `Canonical Ubuntu 24.04` (ou 22.04).
4. **Shape** :clique **Change shape** → **Ampere** (ARM, `VM.Standard.A1.Flex`) :
   - OCPU : **4**, RAM : **24 GB** (= max Always Free ARM). Si indisponible dans ta région (« out of capacity »), prends **AMD** `VM.Standard.E2.1.Micro` (2 instances gratuites possibles) et réessaie l'ARM plus tard.
5. **Networking** : crée un VCN (défaut) + **cocher « Assign a public IPv4 address »**.
6. **Add SSH keys** : **Generate a key pair** → **télécharge la clé privée** (`.key`) et garde-la précieusement (chmod 600 sous Linux). Sans elle, plus d'accès.
7. **Boot volume** : 50 GB (défaut gratuit, ne pas augmenter).
8. **Create**. Note l'**IP publique** affichée une fois la VM `Running`.

## 2. Ouvrir le port 80 (sinon site injoignable)

Console Oracle → **Networking > Virtual Cloud Networks > (ton VCN) > Security Lists > Default Security List > Add Ingress Rules** :

| Source | Protocole | Port | Rôle |
|---|---|---|---|
| 0.0.0.0/0 | TCP | 22 | SSH |
| 0.0.0.0/0 | TCP | 80 | HTTP test |
| 0.0.0.0/0 | TCP | 443 | HTTPS futur |

(`::/0` en plus si IPv6 activé.)

## 3. Première connexion SSH

```bash
# Linux/WSL/macOS :
chmod 600 ~/toolbox.key
ssh -i ~/toolbox.key ubuntu@<IP_PUBLIQUE>

# Windows PowerShell (clé .key au format OpenSSH) :
ssh -i C:\chemin\toolbox.key ubuntu@<IP_PUBLIQUE>
```

Si « Permission denied » : vérifie le user (`ubuntu` pour Ubuntu, `opc` pour Oracle Linux) et le format de la clé (re-télécharge en OpenSSH si besoin).

## 4. Déposer le code

Option A — `scp` (simple) depuis ton PC :

```powershell
cd "C:\Users\lyesa\Desktop\Site web utile"
scp -i C:\chemin\toolbox.key -r toolbox ubuntu@<IP_PUBLIQUE>:/home/ubuntu/toolbox
```

Option B — `git` (si tu pousses `toolbox/` sur un dépôt privé) : `git clone` en SSH sur la VM.

## 5. Installer + lancer (sur la VM)

```bash
ssh -i ~/toolbox.key ubuntu@<IP_PUBLIQUE>
cd /home/ubuntu/toolbox
sudo bash deploy/oracle-setup.sh     # installe python/venv/nginx/ufw + service systemd
cp .env.example .env
python3 generate_password.py         # colle le hash dans .env
sudo nano /home/ubuntu/toolbox/.env  # vérifie USERNAME + SESSION_SECRET (mets une longue chaîne aléatoire)
sudo systemctl restart toolbox
curl -s http://127.0.0.1:8000/api/health
```

Puis sur ton PC : ouvre `http://<IP_PUBLIQUE>/` → login.

## 6. Dépannage rapide

```bash
sudo systemctl status toolbox --no-pager      # service HS ?
sudo journalctl -u toolbox -n 100 --no-pager  # logs
sudo nginx -t; sudo systemctl status nginx    # proxy HS ?
curl -s http://127.0.0.1:8000/api/health      # bypass Nginx
sudo ufw status                               # firewall local
```

## 7. Limites à connaître

- ARM Ampere gratuit : **4 OCPU / 24 GB max au total** (toutes les instances ARM combinées). 1 seule VM `toolbox` 4/24 = tu es au plafond, c'est normal.
- Région saturée → erreur « Out of capacity » : change de **domaine de disponibilité** (AD-1/2/3) ou de région, ou prends une Micro AMD en attendant.
- Compte **Free Trial** (30 jours, 300 $) : ne crée que des ressources « Always Free » éligibles, sinon le crédit fond.
- HTTPS : seulement quand tu auras un domaine (certbot). En attendant, ne t'envoie pas de fichiers ultra-sensibles en HTTP public — usage test.
