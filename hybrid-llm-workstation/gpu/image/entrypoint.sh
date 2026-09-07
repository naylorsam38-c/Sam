#!/usr/bin/env bash
# Cloud pod entrypoint: start Ollama serving from the persistent network
# volume so models survive stop/start (spec: "persistent storage must be
# attached separately from ephemeral compute").
set -euo pipefail

mkdir -p "${OLLAMA_MODELS:-/workspace/ollama-models}"

echo "Starting Ollama on ${OLLAMA_HOST:-0.0.0.0:11434}, models at ${OLLAMA_MODELS}"
exec ollama serve
