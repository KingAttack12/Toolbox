#!/usr/bin/env bash
# Setup serveur Oracle Cloud (Ubuntu 22.04/24.04) — à exécuter EN SSH sur la VM.
# Usage: sudo bash oracle-setup.sh
set -euo pipefail

APP_USER="${APP_USER:-ubuntu}"
APP_DIR="/home/${APP_USER}/toolbox"

echo "=== [1/6] Paquets système ==="
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx ufw

echo "=== [2/6] Firewall ==="
ufw allow OpenSSH || true
ufw allow 'Nginx Full' || true
ufw --force enable || true
# Image Ubuntu Oracle : une règle REJECT générique précède les chaînes ufw
# et rend ufw inopérant -> la supprimer pour que ufw s'applique vraiment.
iptables -D INPUT -j REJECT --reject-with icmp-host-prohibited 2>/dev/null || true
# IMPORTANT : dans la console Oracle (VCN > Security List), ouvrir aussi
# les ports 80 et 443 en ingress 0.0.0.0/0, sinon Nginx reste injoignable.

echo "=== [3/6] Dossier app (le code est déployé via scp/git séparément) ==="
mkdir -p "$APP_DIR/data/tmp"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "=== [4/6] venv + dépendances (à relancer après chaque déploiement de code) ==="
if [ -f "$APP_DIR/requirements.txt" ]; then
  sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv" || true
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
  sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
fi

echo "=== [5/6] systemd ==="
cp "$(dirname "$0")/toolbox.service" /etc/systemd/system/toolbox.service
# Adapte User/chemins si APP_USER != ubuntu :
sed -i "s|User=ubuntu|User=${APP_USER}|; s|/home/ubuntu|/home/${APP_USER}|g" /etc/systemd/system/toolbox.service
systemctl daemon-reload
systemctl enable --now toolbox

echo "=== [6/6] Nginx ==="
cp "$(dirname "$0")/nginx-toolbox.conf" /etc/nginx/sites-available/toolbox
ln -sf /etc/nginx/sites-available/toolbox /etc/nginx/sites-enabled/toolbox
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "OK. Testez : curl -s http://127.0.0.1:8000/api/health puis http://<IP_PUBLIQUE>/"
echo "Ensuite sur la VM : cd $APP_DIR && cp .env.example .env && python3 generate_password.py"
