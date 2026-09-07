# Cloud GPU pod image (spec section 21, install Phase B steps 3-6).
#
# Built for RunPod (or any provider that runs a plain Docker image on a
# GPU instance and mounts a persistent volume at OLLAMA_MODELS). Ships
# Ollama as the inference engine; swap in vLLM by replacing this image and
# updating CLOUD_LLM_ENGINE=vllm in .env — nothing else in the codebase
# needs to change (workstation_core.cloud_client.CloudInferenceClient
# already speaks both protocols).
#
# Build:  docker build -t <your-registry>/workstation-cloud-gpu:latest gpu/image
# Push:   docker push <your-registry>/workstation-cloud-gpu:latest
# Then set GPU_TEMPLATE_ID in .env to a RunPod template built from this image.

FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    OLLAMA_HOST=0.0.0.0:11434 \
    OLLAMA_MODELS=/workspace/ollama-models

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://ollama.com/install.sh | sh

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 11434

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://localhost:11434/ || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
