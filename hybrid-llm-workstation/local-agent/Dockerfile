# OPTIONAL. The recommended way to run the local agent is as a native
# process on the laptop (see scripts/install and docs/OPERATIONS.md) so it
# has direct access to the real filesystem paths named in
# config/policies.yaml's allowed_paths. This Dockerfile exists for users
# who deliberately want an extra container boundary around it — bind-mount
# exactly the workspace directory named in policies.yaml and nothing else.
#
# Build context must be the repo root:
#   docker build -f local-agent/Dockerfile -t workstation-agent .
FROM python:3.11-slim

WORKDIR /app

COPY local-agent/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY local-agent/src ./local-agent/src

ENV PYTHONPATH=/app/local-agent/src
ENV POLICIES_PATH=/app/config/policies.yaml
ENV AUDIT_DB_PATH=/app/local-agent/data/audit.db

EXPOSE 8787

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8787"]
