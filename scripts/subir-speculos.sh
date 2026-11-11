#!/usr/bin/env bash
# Sobe o emulador Speculos com o app Bitcoin Test para Nano S Plus.
# Usa Docker quando disponivel; senao, o pacote Python do Speculos (requer qemu-arm-static).
# A semente e a padrao do Speculos: publica, apenas para testes.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGEM="ghcr.io/ledgerhq/speculos@sha256:56c7ec84c903147dac28e68706d3241218a3d9beb9562dd4a8c02947b2a24f47"
APP="apps/nanosp/bitcoin-testnet-2.6.0.elf"
ARGS=(--model nanosp --display headless --api-port 5000 --apdu-port 9999)

if command -v docker >/dev/null 2>&1 && [ "${SPECULOS_MODO:-docker}" = "docker" ]; then
  docker rm -f speculos >/dev/null 2>&1 || true
  docker run -d --name speculos -v "$PWD/apps:/speculos/apps:ro" -p 5000:5000 -p 9999:9999 \
    "$IMAGEM" "${ARGS[@]}" "$APP" >/dev/null
  echo "Speculos em Docker iniciado (container 'speculos')."
else
  mkdir -p reports
  nohup speculos "${ARGS[@]}" "$APP" > reports/speculos.log 2>&1 &
  echo "Speculos local iniciado (pid $!). Log em reports/speculos.log."
fi

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:5000/events >/dev/null 2>&1; then
    echo "API do Speculos respondendo em http://127.0.0.1:5000"
    exit 0
  fi
  sleep 1
done
echo "Speculos nao respondeu em 60 s." >&2
exit 1
