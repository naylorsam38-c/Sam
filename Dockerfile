# Base image is CPU here so the repo builds anywhere; on a GPU host swap for
# nvidia/cuda:12.x-cudnn-runtime and install the GPU requirements block.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg espeak-ng curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── LICENCE + DEPENDENCY AUDIT GATE (spec §22–23 + correction) ───────────────
# The build FAILS here unless config/dependency_lock.yaml passes the audit
# (exit 0). Default state is FAIL/PENDING by design until you pin commits +
# SHA-256 and eliminate dynamic/unverified weight downloads on the build host.
# For the CPU fallback demo only, you may bypass at your own risk:
#   docker build --build-arg SKIP_LICENCE_AUDIT=1 .
ARG SKIP_LICENCE_AUDIT=0
RUN if [ "$SKIP_LICENCE_AUDIT" != "1" ]; then \
      python scripts/licence_audit.py ; \
    else \
      echo "WARNING: licence audit bypassed (demo build; NOT licensing-verified)"; \
    fi

EXPOSE 8080
CMD ["python", "scripts/run_service.py"]
