#!/usr/bin/env bash
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Executez avec sudo.'; exit 1; }
[[ $(uname -m) == aarch64 ]] || { echo 'Cet essai cible Oracle ARM64.'; exit 1; }
if [[ -e /opt/toolbox-ai && ! -f /opt/toolbox-ai/.toolbox-ai-owned ]]; then
  echo 'Installation existante non geree : arret sans changement.'; exit 1
fi
mkdir -p /opt/toolbox-ai
touch /opt/toolbox-ai/.toolbox-ai-owned
archive=$(mktemp /var/tmp/toolbox-ai-XXXXXX.tar.zst)
trap 'rm -f "$archive"' EXIT
echo 'Telechargement du paquet Ollama ARM64 officiel...'
curl -fL --retry 2 --connect-timeout 20 https://ollama.com/download/ollama-linux-arm64.tar.zst -o "$archive"
tar --zstd --no-same-owner -xf "$archive" -C /opt/toolbox-ai
install -m 644 "$(dirname "$0")/toolbox-ai.service" /etc/systemd/system/toolbox-ai.service
systemctl daemon-reload
systemctl enable --now toolbox-ai
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:11435/api/version >/dev/null; then break; fi
  sleep 1
done
echo 'Telechargement de Qwen3 1.7B...'
OLLAMA_HOST=127.0.0.1:11435 /opt/toolbox-ai/bin/ollama pull qwen3:1.7b
echo 'Modele installe. Interface encore desactivee : mesure de performance requise.'
