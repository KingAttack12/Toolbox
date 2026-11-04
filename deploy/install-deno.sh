#!/usr/bin/env bash
# Installe le runtime Deno requis par yt-dlp pour YouTube.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Lancez ce script avec sudo." >&2
  exit 1
fi

DENO_VERSION="${DENO_VERSION:-2.9.8}"
case "$(dpkg --print-architecture)" in
  arm64) DENO_ARCH="aarch64" ;;
  amd64) DENO_ARCH="x86_64" ;;
  *) echo "Architecture non prise en charge par ce script." >&2; exit 1 ;;
esac

DENO_ASSET="deno-${DENO_ARCH}-unknown-linux-gnu.zip"
DENO_BASE="https://github.com/denoland/deno/releases/download/v${DENO_VERSION}"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

curl --fail --location --silent --show-error "${DENO_BASE}/${DENO_ASSET}" --output "${TEMP_DIR}/${DENO_ASSET}"
curl --fail --location --silent --show-error "${DENO_BASE}/${DENO_ASSET}.sha256sum" --output "${TEMP_DIR}/${DENO_ASSET}.sha256sum"
(cd "${TEMP_DIR}" && sha256sum --check "${DENO_ASSET}.sha256sum")
unzip -q "${TEMP_DIR}/${DENO_ASSET}" -d "${TEMP_DIR}"
install -o root -g root -m 0755 "${TEMP_DIR}/deno" /usr/local/bin/deno
/usr/local/bin/deno --version
