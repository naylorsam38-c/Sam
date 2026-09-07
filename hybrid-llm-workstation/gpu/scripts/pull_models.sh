#!/usr/bin/env bash
# Run this once against a freshly-started cloud GPU pod (via the control
# API's cloud endpoint, or by SSH-ing into the pod directly) to pull the
# large models you want available in CLOUD environment onto the
# persistent volume, so subsequent GPU starts don't need to re-download
# them (spec: "verify persistent storage survives stop/start").
#
# Usage: OLLAMA_URL=http://<pod-ip>:<port> ./gpu/scripts/pull_models.sh model1 [model2 ...]
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

if [ "$#" -eq 0 ]; then
    echo "Usage: OLLAMA_URL=<cloud-ollama-url> $0 <model> [<model> ...]" >&2
    echo "Example: $0 qwen2.5:32b llama3.1:70b" >&2
    exit 1
fi

for model in "$@"; do
    echo "Pulling ${model} via ${OLLAMA_URL} ..."
    curl -fsS -X POST "${OLLAMA_URL}/api/pull" -d "{\"name\": \"${model}\"}" \
        | while read -r line; do echo "  ${line}"; done
done

echo "Done. Verify with: curl -s ${OLLAMA_URL}/api/tags"
