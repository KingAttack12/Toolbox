#!/usr/bin/env bash
# Removes only the dedicated runtime/model installed by install-local-ai.sh.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Executez avec sudo.'; exit 1; }
[[ -f /opt/toolbox-ai/.toolbox-ai-owned ]] || { echo 'Installation non reconnue : arret sans suppression.'; exit 1; }
python3 "$(dirname "$0")/local-ai-control.py" disable
if [[ -f /etc/systemd/system/toolbox-ai.service ]]; then
  systemctl disable --now toolbox-ai
  systemctl clean --what=state toolbox-ai
  rm -f -- /etc/systemd/system/toolbox-ai.service
fi
rm -rf -- /opt/toolbox-ai
systemctl daemon-reload
echo 'Moteur et modele supprimes. Les conversions et comptes Toolbox sont conserves.'
