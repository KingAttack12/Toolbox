#!/usr/bin/env bash
# Backup hebdo de la config Toolbox (ROOT uniquement : contient le .env !).
# Contenu : .env + configs Nginx/systemd/fail2ban + data. Le CODE est sur GitHub.
# Restauration : extraire l'archive et recopier les fichiers à leur place.
set -euo pipefail

DEST="/home/ubuntu/backups"
mkdir -p "$DEST"
DATE="$(date +%F)"
ARCH="$DEST/toolbox-$DATE.tar.gz"

tar -czf "$ARCH" \
  /home/ubuntu/toolbox/.env \
  /home/ubuntu/toolbox/requirements.txt \
  /etc/nginx/sites-available/toolbox \
  /etc/systemd/system/toolbox.service \
  /etc/fail2ban/filter.d/toolbox-login.conf \
  /etc/fail2ban/jail.d/toolbox.conf \
  /home/ubuntu/toolbox/data 2>/dev/null || true

chmod 600 "$ARCH"
# Conservation 14 jours
find "$DEST" -name 'toolbox-*.tar.gz' -mtime +14 -delete || true
ls -la "$ARCH"

# Récupérer sur PC : scp -i cle ubuntu@IP:/home/ubuntu/backups/toolbox-DATE.tar.gz .
